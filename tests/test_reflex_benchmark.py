import tempfile
from pathlib import Path
import unittest

from untethered_aios.reflex_benchmark import run_reflex_execution_benchmark


class ReflexExecutionBenchmarkTests(unittest.TestCase):
    def test_extended_cognitive_economy_benchmark(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_reflex_execution_benchmark(Path(temporary))

        self.assertEqual(
            result["schema"],
            "twis-reflex-execution-benchmark-v0.1",
        )
        self.assertEqual(
            result["extends"],
            "twis-cognitive-substrate-benchmark-v0.1",
        )
        self.assertTrue(all(result["campaign_1"]["correctness"].values()))
        self.assertTrue(all(result["correctness"].values()))
        self.assertEqual(
            result["execution_cases"]["first"]["status"],
            "EXECUTED",
        )
        self.assertEqual(
            result["execution_cases"]["identical_repeat"]["status"],
            "REUSED",
        )
        self.assertFalse(
            result["execution_cases"]["identical_repeat"]["handler_executed"]
        )
        self.assertEqual(
            result["execution_cases"]["dependency_changed"]["status"],
            "EXECUTED",
        )
        self.assertTrue(result["execution_cases"]["unrelated"]["reusable"])
        self.assertEqual(
            result["execution_cases"]["novel"]["route"],
            "CENTRAL_AI",
        )
        self.assertEqual(
            result["execution_cases"]["protected"]["route"],
            "OWNER_GATE",
        )
        self.assertEqual(result["economy"]["handler_executions"], 2)
        self.assertEqual(result["economy"]["reuse_hits"], 1)
        self.assertEqual(
            result["economy"]["handler_recomputations_avoided"],
            1,
        )
        self.assertEqual(result["economy"]["dependency_recomputations"], 1)
        self.assertEqual(result["economy"]["fake_model_calls"], 1)
        self.assertEqual(result["economy"]["fake_model_calls_avoided"], 4)
        self.assertEqual(result["economy"]["fake_calls_after_all_cheap"], 0)
        self.assertEqual(result["receipts"]["cheap_capability_calls"], 2)
        self.assertEqual(
            result["receipts"]["cheap_capability_target"],
            "handler:request-normalizer-v1",
        )
        self.assertTrue(result["receipts"]["chain_valid"])
        self.assertEqual(
            result["receipts"]["count"],
            result["receipts"]["persisted_count"],
        )
        self.assertEqual(result["databases"]["computation_integrity"], "ok")
        self.assertEqual(result["databases"]["computation_journal_mode"], "delete")
        self.assertEqual(result["databases"]["kernel_integrity"], "ok")
        self.assertEqual(result["databases"]["kernel_journal_mode"], "delete")
        self.assertGreater(result["measurements"]["cpu_ns"], 0)
        self.assertGreater(result["measurements"]["wall_ns"], 0)
        self.assertGreater(
            result["measurements"]["peak_traced_memory_bytes"],
            0,
        )
        self.assertEqual(result["runtime"]["network_calls"], 0)
        self.assertEqual(result["runtime"]["provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()
