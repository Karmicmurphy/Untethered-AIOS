import unittest

from untethered_aios import AuditLog

class AuditTests(unittest.TestCase):
    def test_receipt_has_stable_shape_and_hash(self):
        audit = AuditLog()
        receipt = audit.emit("test", "kernel", "demo", {"x": 1})
        self.assertEqual(len(receipt.sha256), 64)
        self.assertEqual(receipt.kind, "test")
        self.assertEqual(audit.receipts[0], receipt)

if __name__ == "__main__":
    unittest.main()
