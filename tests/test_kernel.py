import unittest

from untethered_aios import Kernel, CapabilityGrant, ProcessState, Event
from untethered_aios.kernel import Step

class KernelTests(unittest.TestCase):
    def test_mutating_record_does_not_change_admission(self):
        kernel = Kernel()
        kernel.capabilities.register("secret", lambda: "leak")
        def worker(ctx):
            self.assertFalse(hasattr(ctx, "kernel"))
            with self.assertRaises((AttributeError, TypeError)):
                ctx.process.grants = (CapabilityGrant("secret", ()),)
            kernel.processes[ctx.process.pid].grants = (CapabilityGrant("secret", ()),)
            return Step.done(ctx.call("secret"))
        pid = kernel.spawn("worker", worker)
        kernel.run()
        self.assertEqual(kernel.processes[pid].state, ProcessState.FAILED)
        self.assertIn("PermissionDenied", kernel.processes[pid].error)

    def test_invalid_return_does_not_abort_healthy_worker(self):
        kernel = Kernel()
        bad = kernel.spawn("bad", lambda ctx: None)
        good = kernel.spawn("good", lambda ctx: Step.done("ok"))
        kernel.run()
        self.assertEqual(kernel.processes[bad].state, ProcessState.FAILED)
        self.assertEqual(kernel.processes[good].result, "ok")

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

        def worker(ctx):
            if not state["ready"]:
                state["ready"] = True
                return Step.wait("music.ready")
            return Step.done("awake")

        pid = kernel.spawn("music-worker", worker)
        kernel.run()
        self.assertEqual(kernel.processes[pid].state, ProcessState.WAITING)

        kernel.publish(Event("music.ready", {"ok": True}))
        kernel.run()
        self.assertEqual(kernel.processes[pid].state, ProcessState.DONE)
        self.assertEqual(kernel.processes[pid].result, "awake")

    def test_foundry_job_id_flows_through_runtime_audit(self):
        kernel = Kernel()
        kernel.capabilities.register("demo", lambda value: value)

        def worker(ctx):
            self.assertEqual(ctx.process.metadata["foundry_job_id"], "job:abc123")
            self.assertEqual(ctx.call("demo", value="ok"), "ok")
            return Step.done("done")

        grant = CapabilityGrant("demo", ())
        pid = kernel.spawn(
            "foundry-worker",
            worker,
            grants=(grant,),
            metadata={"foundry_job_id": "job:abc123"},
        )
        kernel.run()

        self.assertEqual(kernel.processes[pid].state, ProcessState.DONE)
        correlated = [
            receipt for receipt in kernel.audit.as_dicts()
            if receipt["kind"] in {"process.spawn", "capability.call", "process.done"}
        ]
        self.assertEqual(len(correlated), 3)
        self.assertTrue(all(
            receipt["detail"].get("foundry_job_id") == "job:abc123"
            for receipt in correlated
        ))

    def test_tick_limit_lists_correlated_foundry_job(self):
        kernel = Kernel()

        def worker(ctx):
            return Step.yield_cpu()

        kernel.spawn(
            "bounded-worker",
            worker,
            metadata={"foundry_job_id": "job:tick"},
        )
        kernel.run(max_ticks=1)

        tick_receipts = [
            receipt for receipt in kernel.audit.as_dicts()
            if receipt["kind"] == "kernel.tick_limit"
        ]
        self.assertEqual(len(tick_receipts), 1)
        self.assertEqual(
            tick_receipts[0]["detail"]["foundry_job_ids"],
            ["job:tick"],
        )

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

if __name__ == "__main__":
    unittest.main()
