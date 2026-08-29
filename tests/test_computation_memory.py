import sqlite3
import tempfile
from pathlib import Path
import unittest

from untethered_aios.audit import AuditLog, hash_value
from untethered_aios.computation_memory import (
    ComputationState,
    SQLiteComputationMemory,
)


class ComputationMemoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "computations.sqlite3"
        self.audit = AuditLog(clock=lambda: "2026-01-01T00:00:00+00:00")
        self.memory = SQLiteComputationMemory(self.path, audit=self.audit)

    def tearDown(self):
        self.memory.close()
        self.temp.cleanup()

    def record(self, identifier, value, dependencies=None, *, store_value=False):
        return self.memory.record(
            computation_id=identifier,
            input_hashes={"input": hash_value(f"{identifier}-input")},
            dependency_hashes=dependencies or {},
            producer="test-producer",
            result_hash=hash_value(value),
            duration_ms=1.5,
            cpu_ms=1.0,
            memory_bytes=1024,
            cost_units=0.25,
            invalidation_rule="stale when input or dependency result hash changes",
            proof_reference=f"test:{identifier}:{value}",
            **({"result_value": value} if store_value else {}),
        )

    def test_a_to_b_to_c_invalidation_preserves_unaffected_d(self):
        a = self.record("A", "a1")
        b = self.record("B", "b1", {"A": a.result_hash})
        self.record("C", "c1", {"B": b.result_hash})
        d = self.record("D", "d1")

        self.assertTrue(
            self.memory.check_reuse(
                "C",
                input_hashes={"input": hash_value("C-input")},
                dependency_hashes={"B": b.result_hash},
            ).reusable
        )
        self.record("A", "a2")

        self.assertEqual(self.memory.get("A").state, ComputationState.VALID)
        self.assertEqual(self.memory.get("B").state, ComputationState.STALE)
        self.assertEqual(self.memory.get("C").state, ComputationState.STALE)
        self.assertEqual(self.memory.get("D").state, ComputationState.VALID)
        self.assertTrue(
            self.memory.check_reuse(
                "D",
                input_hashes={"input": hash_value("D-input")},
                dependency_hashes={},
            ).reusable
        )
        invalidation = [
            receipt
            for receipt in self.audit.receipts
            if receipt.kind == "computation.invalidated"
        ][0]
        self.assertEqual(invalidation.detail["invalidated"], ["B", "C"])
        self.assertEqual(self.audit.verify_chain(), (True, ()))

    def test_reopen_preserves_records_and_rollback_journal(self):
        self.record("A", "a1")
        self.memory.close()
        reopened = SQLiteComputationMemory(self.path)
        try:
            self.assertEqual(reopened.get("A").result_hash, hash_value("a1"))
            self.assertEqual(reopened.integrity_check(), "ok")
            self.assertEqual(reopened.journal_mode(), "delete")
        finally:
            reopened.close()
        self.memory = SQLiteComputationMemory(self.path)

    def test_unknown_dependency_and_invalid_hash_fail_closed(self):
        with self.assertRaises(ValueError):
            self.memory.record(
                computation_id="bad",
                input_hashes={"input": "not-a-hash"},
                dependency_hashes={},
                producer="test",
                result_hash=hash_value("result"),
                duration_ms=0,
                cpu_ms=0,
                memory_bytes=0,
                cost_units=0,
                invalidation_rule="hash change",
                proof_reference="test:bad",
            )
        with self.assertRaises(sqlite3.IntegrityError):
            self.record("B", "b1", {"missing": hash_value("missing")})

    def test_result_value_round_trips_and_hash_mismatch_fails_closed(self):
        result = {"title": "Stable", "tags": ["one", "two"]}
        self.record("stored", result, store_value=True)
        self.memory.close()
        reopened = SQLiteComputationMemory(self.path)
        try:
            self.assertEqual(reopened.get("stored").result_value, result)
            decision = reopened.check_reuse(
                "stored",
                input_hashes={"input": hash_value("stored-input")},
                dependency_hashes={},
                require_result_value=True,
            )
            self.assertTrue(decision.reusable)
        finally:
            reopened.close()
        self.memory = SQLiteComputationMemory(self.path)

        with self.assertRaises(ValueError):
            self.memory.record(
                computation_id="mismatch",
                input_hashes={"input": hash_value("mismatch-input")},
                dependency_hashes={},
                producer="test-producer",
                result_hash=hash_value("expected"),
                duration_ms=0,
                cpu_ms=0,
                memory_bytes=0,
                cost_units=0,
                invalidation_rule="hash change",
                proof_reference="test:mismatch",
                result_value="different",
            )

    def test_reuse_requires_exact_producer_rule_proof_and_stored_value(self):
        self.record("exact", {"value": 1}, store_value=True)
        expected = {
            "input_hashes": {"input": hash_value("exact-input")},
            "dependency_hashes": {},
            "expected_producer": "test-producer",
            "expected_invalidation_rule": (
                "stale when input or dependency result hash changes"
            ),
            "require_proof": True,
            "require_result_value": True,
        }
        self.assertTrue(self.memory.check_reuse("exact", **expected).reusable)

        mutations = (
            {"expected_producer": "other-producer"},
            {"expected_invalidation_rule": "other-rule"},
        )
        for mutation in mutations:
            arguments = dict(expected)
            arguments.update(mutation)
            self.assertFalse(self.memory.check_reuse("exact", **arguments).reusable)

        self.record("legacy", "value")
        self.assertFalse(
            self.memory.check_reuse(
                "legacy",
                input_hashes={"input": hash_value("legacy-input")},
                dependency_hashes={},
                require_result_value=True,
            ).reusable
        )


if __name__ == "__main__":
    unittest.main()
