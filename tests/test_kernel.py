import tempfile
import unittest
from pathlib import Path

from untethered_aios import (
    CapabilityGrant,
    CapabilityRequest,
    Event,
    Kernel,
    PermissionDenied,
    ProcessRecord,
    ProcessState,
    SQLiteProcessTable,
)
from untethered_aios.kernel import Step

class KernelTests(unittest.TestCase):
    def test_worker_yields_then_finishes(self):
        kernel = Kernel()
        state = {"n": 0}

        def worker(ctx):
            state["n"] += 1
            if state["n"] == 1:
                return Step.yield_cpu()
            return Step.done("ok")

        pid = kernel.spawn("worker", worker)
        kernel.run()

        proc = kernel.processes[pid]
        self.assertEqual(proc.state, ProcessState.DONE)
        self.assertEqual(proc.result, "ok")
        self.assertEqual(proc.ticks, 2)

    def test_wait_and_wake(self):
        kernel = Kernel()
        state = {"ready": False}

        received = []

        def worker(ctx):
            if not state["ready"]:
                state["ready"] = True
                return Step.wait("music.ready")
            received.append(ctx.event)
            return Step.done("awake")

        pid = kernel.spawn("music-worker", worker)
        kernel.run()
        self.assertEqual(kernel.processes[pid].state, ProcessState.WAITING)

        kernel.publish(Event("music.ready", {"ok": True}))
        kernel.run()
        self.assertEqual(kernel.processes[pid].state, ProcessState.DONE)
        self.assertEqual(kernel.processes[pid].result, "awake")
        self.assertEqual(received, [{"topic": "music.ready", "payload": {"ok": True}}])

    def test_child_cannot_escalate_grants(self):
        kernel = Kernel()
        allowed = CapabilityGrant("artifact.read", ("/safe",))
        forbidden = CapabilityGrant("process.exec", ("*",))

        def child(ctx):
            return Step.done()

        def parent(ctx):
            ctx.spawn("child", child, grants=(forbidden,))
            return Step.done()

        pid = kernel.spawn("parent", parent, grants=(allowed,))
        kernel.run()
        self.assertEqual(kernel.processes[pid].state, ProcessState.FAILED)
        self.assertIn("PermissionDenied", kernel.processes[pid].error)

    def test_child_can_receive_narrower_scope_but_not_broader_scope(self):
        kernel = Kernel()

        def child(ctx):
            return Step.done("child")

        spawned = []

        def parent(ctx):
            spawned.append(
                ctx.spawn(
                    "child",
                    child,
                    grants=(CapabilityGrant("artifact.read", ("C:\\safe\\project",)),),
                )
            )
            return Step.done()

        parent_pid = kernel.spawn(
            "parent",
            parent,
            grants=(CapabilityGrant("artifact.read", ("C:\\safe",)),),
        )
        kernel.run()
        self.assertEqual(kernel.processes[parent_pid].state, ProcessState.DONE)
        self.assertEqual(kernel.processes[spawned[0]].parent_pid, parent_pid)

        def escalating_parent(ctx):
            ctx.spawn(
                "bad-child",
                child,
                grants=(CapabilityGrant("artifact.read", ("C:\\outside",)),),
            )
            return Step.done()

        bad_pid = kernel.spawn(
            "bad-parent",
            escalating_parent,
            grants=(CapabilityGrant("artifact.read", ("C:\\safe",)),),
        )
        kernel.run()
        self.assertEqual(kernel.processes[bad_pid].state, ProcessState.FAILED)

    def test_worker_process_view_cannot_self_grant(self):
        kernel = Kernel()
        observed = []
        original = CapabilityGrant("artifact.read", ("C:\\safe",))

        def worker(ctx):
            view = ctx.process
            view.grants = (CapabilityGrant("process.exec", ("*",)),)
            observed.extend(view.grants)
            return Step.done()

        pid = kernel.spawn("worker", worker, grants=(original,))
        kernel.run()
        self.assertEqual(kernel.processes[pid].grants, (original,))
        self.assertEqual(observed[0].name, "process.exec")

    def test_suspend_wait_publish_then_resume_is_ready(self):
        kernel = Kernel()
        turns = []

        def worker(ctx):
            turns.append(ctx.event)
            if len(turns) == 1:
                return Step.wait("ready")
            return Step.done("woken")

        pid = kernel.spawn("worker", worker)
        kernel.run()
        kernel.suspend(pid)
        self.assertEqual(kernel.processes[pid].state, ProcessState.SUSPENDED)
        kernel.publish(Event("ready", {"value": 7}))
        self.assertEqual(kernel.processes[pid].state, ProcessState.SUSPENDED)
        kernel.resume(pid)
        self.assertEqual(kernel.processes[pid].state, ProcessState.READY)
        kernel.run()
        self.assertEqual(kernel.processes[pid].result, "woken")
        self.assertEqual(turns[-1]["payload"], {"value": 7})

    def test_cancelled_and_terminal_processes_do_not_run_again(self):
        kernel = Kernel()
        calls = []

        def worker(ctx):
            calls.append(1)
            return Step.done()

        cancelled = kernel.spawn("cancelled", worker)
        kernel.cancel(cancelled)
        kernel.run()
        self.assertEqual(calls, [])
        self.assertEqual(kernel.processes[cancelled].state, ProcessState.CANCELLED)
        kernel.resume(cancelled)
        self.assertEqual(kernel.processes[cancelled].state, ProcessState.CANCELLED)

    def test_runner_can_cooperatively_suspend_and_resume(self):
        kernel = Kernel()
        calls = []

        def worker(ctx):
            calls.append(ctx.process.state)
            if len(calls) == 1:
                return Step.suspend()
            return Step.done("resumed")

        pid = kernel.spawn("worker", worker)
        kernel.run()
        self.assertEqual(kernel.processes[pid].state, ProcessState.SUSPENDED)
        kernel.resume(pid)
        kernel.run()
        self.assertEqual(kernel.processes[pid].result, "resumed")

    def test_runner_exception_records_failure_evidence(self):
        kernel = Kernel()

        def worker(ctx):
            raise RuntimeError("boom")

        pid = kernel.spawn("crasher", worker)
        kernel.run()
        self.assertEqual(kernel.processes[pid].state, ProcessState.FAILED)
        self.assertEqual(kernel.processes[pid].error, "RuntimeError: boom")
        self.assertTrue(
            any(
                receipt.kind == "process.failed" and receipt.pid == pid
                for receipt in kernel.audit.receipts
            )
        )

    def test_capability_denial_is_receipted_before_process_failure(self):
        kernel = Kernel()
        kernel.capabilities.register("secret.read", lambda: "no")

        def worker(ctx):
            ctx.call("secret.read")
            return Step.done()

        pid = kernel.spawn("denied", worker)
        kernel.run()
        kinds = [receipt.kind for receipt in kernel.audit.receipts if receipt.pid == pid]
        self.assertIn("capability.denied", kinds)
        self.assertIn("process.failed", kinds)
        self.assertLess(kinds.index("capability.denied"), kinds.index("process.failed"))

    def test_retained_context_cannot_invoke_after_process_finishes(self):
        kernel = Kernel()
        retained = []
        kernel.capabilities.register("echo", lambda value: value)

        def worker(ctx):
            retained.append(ctx)
            return Step.done("finished")

        pid = kernel.spawn(
            "short-lived",
            worker,
            grants=(CapabilityGrant("echo", ("*",)),),
        )
        kernel.run()
        self.assertEqual(kernel.processes[pid].state, ProcessState.DONE)
        with self.assertRaises(PermissionDenied):
            retained[0].call("echo", value="too late")

    def test_deterministic_fifo_schedule(self):
        kernel = Kernel()
        order = []

        def make_worker(name):
            def worker(ctx):
                order.append(name)
                if order.count(name) == 1:
                    return Step.yield_cpu()
                return Step.done()
            return worker

        kernel.spawn("one", make_worker("one"))
        kernel.spawn("two", make_worker("two"))
        kernel.run()
        self.assertEqual(order, ["one", "two", "one", "two"])
        transitions = [
            receipt.detail["to"]
            for receipt in kernel.audit.receipts
            if receipt.kind == "process.transition"
        ]
        self.assertEqual(
            transitions,
            ["READY", "READY", "RUNNING", "READY", "RUNNING", "READY", "RUNNING", "DONE", "RUNNING", "DONE"],
        )

    def test_sqlite_reopen_resumes_ready_process_after_runner_bind(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "kernel.sqlite3"
            table = SQLiteProcessTable(path)
            kernel = Kernel(process_table=table)

            def worker(ctx):
                turn = int(ctx.metadata.get("turn", 0)) + 1
                ctx.set_metadata("turn", turn)
                if turn == 1:
                    return Step.yield_cpu()
                return Step.done("reopened")

            pid = kernel.spawn("durable", worker, runner_id="durable.v1")
            kernel.run(max_ticks=1)
            self.assertEqual(kernel.processes[pid].state, ProcessState.READY)
            kernel.close()

            reopened = Kernel(process_table=SQLiteProcessTable(path))
            reopened.bind_runner(pid, worker, runner_id="durable.v1")
            reopened.run()
            self.assertEqual(reopened.processes[pid].result, "reopened")
            self.assertEqual(reopened.processes[pid].ticks, 2)
            reopened.close()

    def test_sqlite_reopen_preserves_wait_and_wake(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "kernel.sqlite3"
            kernel = Kernel(process_table=SQLiteProcessTable(path))

            def worker(ctx):
                if ctx.event is None:
                    return Step.wait("go")
                return Step.done(ctx.event["payload"]["value"])

            pid = kernel.spawn("waiting", worker, runner_id="waiting.v1")
            kernel.run()
            self.assertEqual(kernel.processes[pid].state, ProcessState.WAITING)
            kernel.close()

            reopened = Kernel(process_table=SQLiteProcessTable(path))
            reopened.bind_runner(pid, worker, runner_id="waiting.v1")
            reopened.publish(Event("go", {"value": 42}))
            reopened.run()
            self.assertEqual(reopened.processes[pid].result, 42)
            reopened.close()

    def test_running_process_is_failed_with_crash_evidence_on_reopen(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "kernel.sqlite3"
            table = SQLiteProcessTable(path)
            pid = table.allocate_pid()
            table.put(
                ProcessRecord(
                    pid=pid,
                    name="crashed",
                    runner_id="crashed.v1",
                    state=ProcessState.RUNNING,
                )
            )
            table.close()

            kernel = Kernel(process_table=SQLiteProcessTable(path))
            proc = kernel.processes[pid]
            self.assertEqual(proc.state, ProcessState.FAILED)
            self.assertIn("KernelRestart", proc.error)
            self.assertTrue(any(r.kind == "process.crash_recovered" for r in kernel.audit.receipts))
            kernel.close()

    def test_mutation_receipt_is_structured_and_persistent(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            table = SQLiteProcessTable(root / "kernel.sqlite3")
            kernel = Kernel(process_table=table)
            kernel.capabilities.register(
                "artifact.write",
                lambda path, text: Path(path).write_text(text, encoding="utf-8"),
                scope_arg="path",
                mutation=True,
            )

            def worker(ctx):
                result = ctx.invoke(
                    CapabilityRequest(
                        "artifact.write",
                        {"path": str(root / "out.txt"), "text": "hello"},
                    )
                )
                return Step.done(result)

            pid = kernel.spawn(
                "writer",
                worker,
                grants=(CapabilityGrant("artifact.write", (str(root),)),),
            )
            kernel.run()
            receipts = [r for r in kernel.audit.receipts if r.kind == "capability.mutation"]
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0].pid, pid)
            self.assertEqual(Path(receipts[0].target), (root / "out.txt").resolve())
            self.assertEqual(len(receipts[0].detail["input_sha256"]), 64)
            self.assertEqual(len(receipts[0].detail["output_sha256"]), 64)
            kernel.close()

            reopened = SQLiteProcessTable(root / "kernel.sqlite3")
            self.assertTrue(any(r["kind"] == "capability.mutation" for r in reopened.list_receipts()))
            reopened.close()

if __name__ == "__main__":
    unittest.main()
