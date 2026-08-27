import tempfile
import unittest
from pathlib import Path

from untethered_aios import CapabilityRegistry, CapabilityGrant, PermissionDenied

class CapabilityTests(unittest.TestCase):
    def test_ungranted_capability_denied(self):
        registry = CapabilityRegistry()
        registry.register("demo", lambda: "ok")
        with self.assertRaises(PermissionDenied):
            registry.invoke("demo", {}, ())

    def test_path_scope_allows_inside_and_denies_outside(self):
        registry = CapabilityRegistry()
        registry.register("file.read", lambda path: Path(path).name, scope_arg="path")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "safe"
            root.mkdir()
            inside = root / "a.txt"
            outside = Path(tmp) / "outside.txt"

            grant = CapabilityGrant("file.read", (str(root),))
            self.assertEqual(
                registry.invoke("file.read", {"path": str(inside)}, (grant,)),
                "a.txt",
            )
            with self.assertRaises(PermissionDenied):
                registry.invoke("file.read", {"path": str(outside)}, (grant,))

    def test_traversal_is_denied_after_resolution(self):
        registry = CapabilityRegistry()
        registry.register("file.read", lambda path: str(path), scope_arg="path")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "safe"
            root.mkdir()
            target = root / ".." / "escape.txt"
            grant = CapabilityGrant("file.read", (str(root),))

            with self.assertRaises(PermissionDenied):
                registry.invoke("file.read", {"path": str(target)}, (grant,))

if __name__ == "__main__":
    unittest.main()
