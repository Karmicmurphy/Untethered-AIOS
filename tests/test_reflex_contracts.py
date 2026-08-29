import json
from pathlib import Path
import unittest

from untethered_aios import (
    CHEAP_HANDLER_CAPABILITY,
    REQUEST_NORMALIZER_HANDLER_ID,
    KernelCheapExecutionBridge,
    build_default_cheap_handler_registry,
)


ROOT = Path(__file__).resolve().parents[1]


class ReflexContractTests(unittest.TestCase):
    def test_schema_declares_bounded_handler_and_outcome_contracts(self):
        schema = json.loads(
            (
                ROOT / "contracts" / "reflex-execution-bridge-v0.1.schema.json"
            ).read_text(encoding="utf-8")
        )
        handler = schema["$defs"]["cheapHandler"]
        outcome = schema["$defs"]["executionOutcome"]
        self.assertEqual(handler["properties"]["handler_id"]["const"], REQUEST_NORMALIZER_HANDLER_ID)
        self.assertEqual(
            handler["properties"]["required_capabilities"]["maxItems"], 1
        )
        self.assertEqual(
            schema["$defs"]["capabilityGrant"]["properties"]["name"]["const"],
            CHEAP_HANDLER_CAPABILITY,
        )
        self.assertIn("receipt_sha256", outcome["required"])
        self.assertIn("traced_memory_bytes", outcome["required"])

    def test_document_names_kernel_authority_and_registry_non_authority(self):
        text = (ROOT / "docs" / "REFLEX_EXECUTION_BRIDGE_V0_1.md").read_text(
            encoding="utf-8"
        )
        for statement in (
            "Kernel is the only execution authority",
            "registry cannot grant",
            "FakeModel",
            "OWNER_GATE",
            "Computation Memory",
        ):
            self.assertIn(statement, text)

    def test_default_registry_contains_exactly_one_deterministic_handler(self):
        registry = build_default_cheap_handler_registry()
        specs = registry.specs()
        self.assertEqual(len(specs), 1)
        self.assertEqual(specs[0].handler_id, REQUEST_NORMALIZER_HANDLER_ID)
        self.assertTrue(specs[0].deterministic)
        self.assertIsNotNone(KernelCheapExecutionBridge)


if __name__ == "__main__":
    unittest.main()
