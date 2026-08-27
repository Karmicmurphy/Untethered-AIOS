import tempfile
import unittest
from pathlib import Path

from untethered_aios import (
    CapabilityGrant,
    CapabilityRegistry,
    CapabilityRequest,
    PermissionDenied,
)

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

    def test_structured_invocation_returns_canonical_target(self):
        registry = CapabilityRegistry()
        handled = []
        registry.register(
            "file.read",
            lambda path: handled.append(path) or Path(path).name,
            scope_arg="path",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "inside.txt"
            outcome = registry.invoke_request(
                CapabilityRequest("file.read", {"path": str(target)}),
                (CapabilityGrant("file.read", (str(root),)),),
            )
            self.assertEqual(outcome.value, "inside.txt")
            self.assertEqual(Path(outcome.target), target.resolve())
            self.assertEqual(handled, [str(target.resolve())])
            self.assertFalse(outcome.mutation)

    @unittest.skipUnless(__import__("os").name == "nt", "Windows path policy")
    def test_windows_unsafe_path_forms_are_denied(self):
        registry = CapabilityRegistry()
        registry.register("file.read", lambda path: path, scope_arg="path")
        grant = CapabilityGrant("file.read", ("C:\\safe",))
        for target in (
            "\\\\server\\share\\file.txt",
            "C:\\safe\\..\\escape.txt",
            "C:\\safe\\file.txt:stream",
            "C:\\safe\\CON",
            "C:\\safe\\trailing. ",
        ):
            with self.subTest(target=target), self.assertRaises(PermissionDenied):
                registry.invoke("file.read", {"path": target}, (grant,))

    def test_sibling_prefix_is_not_containment(self):
        registry = CapabilityRegistry()
        registry.register("file.read", lambda path: path, scope_arg="path")
        with tempfile.TemporaryDirectory() as tmp:
            safe = Path(tmp) / "safe"
            sibling = Path(tmp) / "safe-other" / "file.txt"
            with self.assertRaises(PermissionDenied):
                registry.invoke(
                    "file.read",
                    {"path": str(sibling)},
                    (CapabilityGrant("file.read", (str(safe),)),),
                )

if __name__ == "__main__":
    unittest.main()
