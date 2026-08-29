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

from untethered_aios.cognitive_benchmark import run_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the permanent Cognitive Substrate V0.1 benchmark."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "evidence" / "cognitive-substrate-v0.1-benchmark.json",
    )
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()

    if args.database is None:
        with tempfile.TemporaryDirectory() as temporary:
            result = run_benchmark(Path(temporary) / "computations.sqlite3")
    else:
        result = run_benchmark(args.database)
    if not all(result["correctness"].values()):
        raise RuntimeError("benchmark correctness assertion failed")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {args.output}")
    print(
        "Routes:",
        len(result["routes"]),
        "Central AI:",
        result["routing_metrics"]["central_ai_calls_required"],
        "Avoided:",
        result["routing_metrics"]["central_ai_calls_avoided"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
