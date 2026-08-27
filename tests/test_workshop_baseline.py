import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.import_workshop_baseline import (
    ImportErrorSafe,
    copy_verified,
    tree_digest,
    verify_source,
)
from scripts.authenticate_workshop import safe_files, tree_digest as authentication_tree_digest


class WorkshopBaselineTests(unittest.TestCase):
    def _manifest(self, root: Path) -> dict:
        entries = []
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            rel = path.relative_to(root).as_posix()
            entries.append(
                {
                    "path": rel,
                    "size": path.stat().st_size,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
            )
        return {
            "format": "twis-untethered-workshop-baseline-v1",
            "source": str(root),
            "files": entries,
            "code_safe_tree_sha256": tree_digest(entries),
        }

    def test_verified_copy_matches_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "source"
            source.mkdir()
            (source / "app").mkdir()
            (source / "app" / "main.js").write_text("console.log('twis')", encoding="utf-8")
            (source / "README.md").write_text("workshop", encoding="utf-8")

            manifest = self._manifest(source)
            verified = verify_source(manifest, source)
            self.assertEqual(tree_digest(verified), manifest["code_safe_tree_sha256"])

            destination = base / "workshop"
            destination.mkdir()
            (destination / "README.md").write_text("placeholder", encoding="utf-8")

            copied = copy_verified(manifest, source, destination)
            self.assertEqual(tree_digest(copied), manifest["code_safe_tree_sha256"])
            self.assertEqual(
                (destination / "app" / "main.js").read_text(encoding="utf-8"),
                "console.log('twis')",
            )

    def test_source_mutation_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            source.mkdir()
            target = source / "a.txt"
            target.write_text("original", encoding="utf-8")
            manifest = self._manifest(source)

            target.write_text("changed", encoding="utf-8")
            with self.assertRaises(ImportErrorSafe):
                verify_source(manifest, source)

    def test_manifest_path_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            source.mkdir()
            outside = Path(temp) / "outside.txt"
            outside.write_text("nope", encoding="utf-8")
            entry = {
                "path": "../outside.txt",
                "size": outside.stat().st_size,
                "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
            }
            manifest = {
                "format": "twis-untethered-workshop-baseline-v1",
                "source": str(source),
                "files": [entry],
                "code_safe_tree_sha256": tree_digest([entry]),
            }
            with self.assertRaises(ImportErrorSafe):
                verify_source(manifest, source)

    def test_nonempty_destination_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "source"
            source.mkdir()
            (source / "a.txt").write_text("safe", encoding="utf-8")
            manifest = self._manifest(source)

            destination = base / "workshop"
            destination.mkdir()
            (destination / "unexpected.txt").write_text("existing", encoding="utf-8")

            with self.assertRaises(ImportErrorSafe):
                copy_verified(manifest, source, destination)

    def test_authentication_excludes_private_and_runtime_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            safe = root / "app" / "main.py"
            safe.parent.mkdir()
            safe.write_text("print('safe')", encoding="utf-8")

            excluded = [
                root / "data" / "projects" / "owner" / "project.json",
                root / ".pytest_cache" / "v" / "cache" / "nodeids",
                root / "private_source_artifacts" / "archive.zip",
                root / "bundle.zip",
                root / "desktop-launcher" / "TWIS Holo Workshop.exe",
                root / "desktop-launcher" / "TWIS Holo Workshop.pdb",
                root / "FLASHRIVER_RECEIPT.json",
                root / "runtime.sqlite3-wal",
                root / "runtime.sqlite3-shm",
                root / "runtime.db-journal",
                root / ".env.development",
            ]
            for path in excluded:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("private", encoding="utf-8")

            included_paths, excluded_paths = safe_files(root)
            included_rel = {path.relative_to(root).as_posix() for path in included_paths}
            excluded_rel = {Path(path).as_posix() for path, _ in excluded_paths}

            self.assertEqual(included_rel, {"app/main.py"})
            self.assertTrue(
                {path.relative_to(root).as_posix() for path in excluded}
                .issubset(excluded_rel)
            )

    def test_authentication_tree_digest_matches_import_contract(self):
        entries = [
            {"path": "z/file.txt", "size": 1, "sha256": "b" * 64},
            {"path": "A/file.txt", "size": 1, "sha256": "a" * 64},
        ]
        self.assertEqual(authentication_tree_digest(entries), tree_digest(entries))


if __name__ == "__main__":
    unittest.main()
