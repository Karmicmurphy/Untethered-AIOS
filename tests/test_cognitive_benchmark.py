import tempfile
from pathlib import Path
import unittest

from untethered_aios.cognitive_benchmark import run_benchmark


class CognitiveBenchmarkTests(unittest.TestCase):
    def test_permanent_synthetic_benchmark(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_benchmark(Path(temporary) / "computations.sqlite3")

        self.assertEqual(result["schema"], "twis-cognitive-substrate-benchmark-v0.1")
        self.assertEqual(len(result["routes"]), 9)
        self.assertTrue(all(result["correctness"].values()))
        self.assertEqual(
            {row["task_class"] for row in result["routes"]},
            {
                "cheap",
                "repeated",
                "novel",
                "protected",
                "low-value",
                "high-value",
                "dependency-reuse",
                "dependency-change",
                "resource-pressure",
            },
        )
        self.assertEqual(
            result["routing_metrics"]["fake_model_calls"],
            ["novel-ambiguous", "high-value-uncertain"],
        )
        self.assertEqual(result["routing_metrics"]["central_ai_calls_required"], 2)
        self.assertEqual(result["routing_metrics"]["central_ai_calls_avoided"], 4)
        self.assertEqual(result["routing_metrics"]["worker_calls"], 1)
        self.assertEqual(
            result["computation_memory"]["state_after_a_changed"],
            {"A": "VALID", "B": "STALE", "C": "STALE", "D": "VALID"},
        )
        self.assertEqual(
            result["computation_memory"]["recomputed_dependents"], ["B", "C"]
        )
        self.assertEqual(result["computation_memory"]["integrity_check"], "ok")
        self.assertEqual(result["computation_memory"]["journal_mode"], "delete")
        self.assertTrue(result["receipts"]["chain_valid"])
        self.assertGreater(result["measurements"]["wall_ns"], 0)
        self.assertGreater(result["measurements"]["peak_traced_memory_bytes"], 0)
        self.assertEqual(result["runtime"]["network_calls"], 0)
        self.assertEqual(result["runtime"]["provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()
