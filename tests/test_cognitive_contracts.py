import json
from pathlib import Path
import unittest

from untethered_aios import (
    AttentionGovernor,
    Route,
    RouteEstimate,
    SQLiteComputationMemory,
    WorkItem,
)


ROOT = Path(__file__).resolve().parents[1]


class CognitiveContractTests(unittest.TestCase):
    def test_contract_schema_has_exact_routes_and_ledger_shapes(self):
        schema = json.loads(
            (ROOT / "contracts" / "cognitive-substrate-v0.1.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            schema["$defs"]["route"]["enum"],
            [
                "IGNORE",
                "DEFER",
                "REFLEX",
                "RULE",
                "WORKER",
                "CENTRAL_AI",
                "OWNER_GATE",
            ],
        )
        self.assertEqual(
            set(schema["$defs"]["computationRecord"]["required"]),
            {
                "computation_id",
                "input_hashes",
                "dependency_hashes",
                "producer",
                "result_hash",
                "duration_ms",
                "cpu_ms",
                "memory_bytes",
                "cost_units",
                "invalidation_rule",
                "proof_reference",
                "state",
            },
        )
        self.assertIn(
            "result_value", schema["$defs"]["computationRecord"]["properties"]
        )

    def test_architecture_contract_names_every_bounded_interface(self):
        text = (ROOT / "docs" / "COGNITIVE_SUBSTRATE_V0_1.md").read_text(
            encoding="utf-8"
        )
        for name in (
            "WorkItem",
            "RouteDecision",
            "Attention Governor",
            "Computation Memory",
            "Reflex Handler",
            "Blackboard",
            "Memory interface",
            "Capability Cell",
            "Model Gateway",
            "Cognitive Downshift",
        ):
            self.assertIn(name, text)

    def test_public_package_exports_campaign_one_types(self):
        self.assertIsNotNone(AttentionGovernor)
        self.assertIsNotNone(RouteEstimate)
        self.assertIsNotNone(WorkItem)
        self.assertIsNotNone(SQLiteComputationMemory)
        self.assertEqual(len(Route), 7)


if __name__ == "__main__":
    unittest.main()
