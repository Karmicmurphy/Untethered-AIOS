"""Ensure FRIDAY's artifact discovery skill cannot silently authorize imports."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/artifact-compass/SKILL.md"


class CompassFrontierSafetyTests(unittest.TestCase):
    def test_freshness_does_not_mean_installation(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("evidence of change", text)
        self.assertIn("not integrated services or upgrades", text)
        self.assertIn("quarantine code reuse", text)
        self.assertIn("STOP_AND_TEST", text)
        self.assertIn("unclear", text)

    def test_warehouse_lineage_and_harness_approval_are_preserved(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("2026-10-25-frontier-salvage/manifest.json", text)
        self.assertIn("candidate until its code is merged", text)
        self.assertIn("owner/Harness authority", text)
        self.assertIn("independently certified improvement", text)

    def test_existing_original_ten_pass_method_stays_present(self):
        text = SKILL.read_text(encoding="utf-8")
        self.assertIn("Pass 1 — Reality baseline", text)
        self.assertIn("Pass 10 — Successor synthesis", text)
        self.assertIn("no silent installation or activation", text)


if __name__ == "__main__":
    unittest.main()
