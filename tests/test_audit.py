import unittest

from untethered_aios import AuditLog, InMemoryProcessTable

class AuditTests(unittest.TestCase):
    def test_receipt_has_stable_shape_and_hash(self):
        audit = AuditLog(clock=lambda: "2026-01-01T00:00:00+00:00")
        receipt = audit.emit("test", "kernel", "demo", {"x": 1})
        self.assertEqual(len(receipt.sha256), 64)
        self.assertEqual(receipt.kind, "test")
        self.assertEqual(audit.receipts[0], receipt)
        self.assertEqual(receipt.sequence, 1)
        self.assertIsNone(receipt.previous_sha256)

    def test_receipt_chain_detects_tampering(self):
        table = InMemoryProcessTable()
        audit = AuditLog(
            sink=table,
            clock=lambda: "2026-01-01T00:00:00+00:00",
        )
        first = audit.emit("test", "kernel", "one")
        second = audit.emit("test", "kernel", "two")
        self.assertEqual(second.previous_sha256, first.sha256)
        self.assertEqual(audit.verify_chain(), (True, ()))

        audit.receipts[0] = audit.receipts[0].__class__(
            **{**audit.receipts[0].__dict__, "action": "tampered"}
        )
        valid, errors = audit.verify_chain()
        self.assertFalse(valid)
        self.assertTrue(errors)

    def test_persisted_chain_corruption_fails_closed(self):
        table = InMemoryProcessTable()
        table.append_receipt(
            {
                "sequence": 1,
                "kind": "test",
                "actor": "kernel",
                "action": "corrupt",
                "target": None,
                "pid": None,
                "parent_pid": None,
                "detail": {},
                "created_at": "2026-01-01T00:00:00+00:00",
                "previous_sha256": None,
                "sha256": "0" * 64,
            }
        )
        with self.assertRaises(ValueError):
            AuditLog(sink=table)

if __name__ == "__main__":
    unittest.main()
