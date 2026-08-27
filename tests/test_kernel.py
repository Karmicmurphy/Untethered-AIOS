import unittest

from untethered_aios import Kernel, CapabilityGrant, ProcessState, Event
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
