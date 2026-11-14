import hashlib
import json
import unittest

from untethered_aios.capabilities import CapabilityGrant, PermissionDenied
from untethered_aios.friday_review_adapter import make_registry, run_approved_readonly


class FridayReviewAdapterTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.registry = make_registry(
            lambda: self.calls.append("inventory") or {"computer": "fixture"},
            lambda: self.calls.append("health") or {"ok": True},
        )
        self.request = {"action": "windows-inventory",
                        "request_id": "0123456789abcdef0123456789abcdef"}

    def test_receipt(self):
        result = run_approved_readonly(
            self.request, registry=self.registry,
            grant=CapabilityGrant("windows-inventory", ("read:inventory",)))
        digest = result.pop("receipt_sha256")
        expected = hashlib.sha256(json.dumps(result, sort_keys=True,
                               separators=(",", ":")).encode()).hexdigest()
        self.assertEqual(digest, expected)
        self.assertEqual(self.calls, ["inventory"])
        self.assertFalse(result["files_modified"])

    def test_health(self):
        result = run_approved_readonly(
            {"action": "workshop-health", "request_id": self.request["request_id"]},
            registry=self.registry,
            grant=CapabilityGrant("workshop-health", ("read:health",)))
        self.assertEqual(result["output"], {"ok": True})

    def test_unknown_task_does_not_run(self):
        with self.assertRaises(ValueError):
            run_approved_readonly(
                {**self.request, "action": "shell"},
                registry=self.registry, grant=CapabilityGrant("shell", ("*",)))
        self.assertEqual(self.calls, [])

    def test_wrong_grant_does_not_run(self):
        with self.assertRaises(ValueError):
            run_approved_readonly(
                self.request, registry=self.registry,
                grant=CapabilityGrant("workshop-health", ("read:inventory",)))
        self.assertEqual(self.calls, [])

    def test_missing_scope_does_not_run(self):
        with self.assertRaises(ValueError):
            run_approved_readonly(
                self.request, registry=self.registry,
                grant=CapabilityGrant("windows-inventory", ()))
        self.assertEqual(self.calls, [])

    def test_extra_request_fields_denied(self):
        with self.assertRaises(ValueError):
            run_approved_readonly(
                {**self.request, "command": "whoami"},
                registry=self.registry,
                grant=CapabilityGrant("windows-inventory", ("read:inventory",)))
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
