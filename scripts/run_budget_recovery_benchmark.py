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

from untethered_aios.budget_recovery_benchmark import run_budget_recovery_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the permanent Campaign 3 budget/recovery benchmark."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=(
            ROOT
            / "evidence"
            / "cheap-execution-budget-recovery-v0.1-benchmark.json"
        ),
    )
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as temporary:
        result = run_budget_recovery_benchmark(temporary)
    if not all(result["correctness"].values()):
        raise RuntimeError("budget/recovery benchmark correctness failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")
    print(
        "Attempts failed:",
        result["economy"]["failed_attempts"],
        "Recoveries:",
        result["economy"]["recoveries_succeeded"],
        "Reuse hits:",
        result["economy"]["reuse_hits"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
