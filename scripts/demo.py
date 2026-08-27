from __future__ import annotations
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from untethered_aios import Kernel, CapabilityGrant
from untethered_aios.kernel import Step

def main() -> None:
    kernel = Kernel()

    kernel.capabilities.register(
        "demo.echo",
        lambda text: text,
    )

    state = {"turn": 0}

    def worker(ctx):
        state["turn"] += 1
        if state["turn"] == 1:
            value = ctx.call(
                "demo.echo",
                text="Synthetic capability reached through kernel; no Workshop adapter invoked.",
            )
            ctx.set_metadata("echo", value)
            return Step.yield_cpu()
        return Step.done(ctx.metadata["echo"])

    pid = kernel.spawn(
        "demo-worker",
        worker,
        grants=(CapabilityGrant("demo.echo", ("*",)),),
    )
    kernel.run()

    proc = kernel.processes[pid]
    print(f"pid={pid} state={proc.state.value} ticks={proc.ticks}")
    print(proc.result)
    print(f"receipts={len(kernel.audit.receipts)}")

if __name__ == "__main__":
    main()
