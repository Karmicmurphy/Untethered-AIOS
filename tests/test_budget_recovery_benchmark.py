import tempfile
from pathlib import Path
import unittest

from untethered_aios.budget_recovery_benchmark import run_budget_recovery_benchmark


class BudgetRecoveryBenchmarkTests(unittest.TestCase):
    def test_permanent_campaign_three_benchmark(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = run_budget_recovery_benchmark(Path(temporary))

        self.assertEqual(
            result["schema"],
            "twis-cheap-execution-budget-recovery-benchmark-v0.1",
        )
        self.assertEqual(
            result["extends"],
            "twis-reflex-execution-benchmark-v0.1",
        )
        self.assertTrue(all(result["campaign_2"]["correctness"].values()))
        self.assertTrue(all(result["correctness"].values()))
        cases = result["execution_cases"]
        self.assertEqual(cases["success"]["status"], "EXECUTED")
        self.assertEqual(cases["identical_reuse"]["status"], "REUSED")
        self.assertEqual(cases["forced_failure"]["status"], "BUDGET_EXCEEDED")
        self.assertEqual(cases["cpu_failure"]["status"], "BUDGET_EXCEEDED")
        self.assertEqual(cases["recovered"]["status"], "RECOVERED")
        self.assertEqual(cases["recovered_reuse"]["status"], "REUSED")
        self.assertEqual(cases["terminal_failure"]["attempt_count"], 2)
        self.assertEqual(cases["terminal_failure"]["final_states"], ["FAILED", "FAILED"])
        self.assertEqual(cases["novel"]["status"], "CENTRAL_AI")
        self.assertEqual(cases["protected"]["status"], "OWNER_GATE")
        self.assertEqual(result["economy"]["failed_attempts"], 4)
        self.assertEqual(result["economy"]["recoveries_succeeded"], 1)
        self.assertEqual(result["economy"]["reuse_hits"], 2)
        self.assertEqual(result["economy"]["fake_model_calls"], 1)
        self.assertTrue(result["receipts"]["all_chains_valid"])
        self.assertEqual(
            result["receipts"]["total_count"],
            result["receipts"]["total_persisted_count"],
        )
        self.assertTrue(result["durability"]["prior_failure_visible_after_reopen"])
        self.assertEqual(result["durability"]["kernel_integrity"], "ok")
        self.assertEqual(result["durability"]["computation_integrity"], "ok")
        self.assertGreater(result["measurements"]["cpu_ns"], 0)
        self.assertGreater(result["measurements"]["wall_ns"], 0)
        self.assertGreater(result["measurements"]["peak_traced_memory_bytes"], 0)
        self.assertEqual(result["runtime"]["network_calls"], 0)
        self.assertEqual(result["runtime"]["provider_calls"], 0)


if __name__ == "__main__":
    unittest.main()
