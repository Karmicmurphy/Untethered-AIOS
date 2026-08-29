from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from untethered_aios.reflex_benchmark import run_reflex_execution_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the permanent Reflex Execution Bridge V0.1 benchmark."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evidence" / "reflex-execution-bridge-v0.1-benchmark.json",
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        result = run_reflex_execution_benchmark(temporary)
    if not all(result["correctness"].values()):
        raise RuntimeError("reflex execution benchmark correctness failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    economy = result["economy"]
    print(f"Wrote {args.output}")
    print(
        "Handler executions:",
        economy["handler_executions"],
        "Reuse hits:",
        economy["reuse_hits"],
        "FakeModel calls:",
        economy["fake_model_calls"],
        "Avoided:",
        economy["fake_model_calls_avoided"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
