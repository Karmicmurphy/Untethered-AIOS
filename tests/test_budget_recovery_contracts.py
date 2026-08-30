import json
from pathlib import Path
import unittest

from untethered_aios import BudgetGuard, ExecutionBudget


ROOT = Path(__file__).resolve().parents[1]


class BudgetRecoveryContractTests(unittest.TestCase):
    def test_schema_requires_every_budget_identity_and_limit(self):
        schema = json.loads(
            (
                ROOT
                / "contracts"
                / "cheap-execution-budget-recovery-v0.1.schema.json"
            ).read_text(encoding="utf-8")
        )
        required = set(schema["$defs"]["executionBudget"]["required"])
        self.assertEqual(
            required,
            {
                "budget_id",
                "owner_id",
                "task_id",
                "max_wall_ns",
                "max_cpu_ns",
                "max_ticks",
                "max_work_units",
                "max_recovery_attempts",
            },
        )

    def test_document_states_cooperative_and_non_sandbox_boundary(self):
        text = (
            ROOT / "docs" / "CHEAP_EXECUTION_BUDGET_RECOVERY_V0_1.md"
        ).read_text(encoding="utf-8")
        for phrase in (
            "Kernel owns the budget",
            "cooperative bounded execution",
            "not preemptive containment",
            "failed attempt writes a successful Computation Memory row",
            "OWNER_GATE",
        ):
            self.assertIn(phrase, text)

    def test_public_package_exports_budget_contract(self):
        self.assertIsNotNone(ExecutionBudget)
        self.assertIsNotNone(BudgetGuard)


if __name__ == "__main__":
    unittest.main()
