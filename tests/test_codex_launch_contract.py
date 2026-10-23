"""Guard current Codex launch instructions against obsolete local-workstation bootstrap."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CodexLaunchContractTests(unittest.TestCase):
    def test_active_start_here_routes_to_current_harness_authority(self):
        guide = (ROOT / "CODEX_START_HERE.md").read_text(encoding="utf-8")
        self.assertIn("Harness-card/blob/main/state/CURRENT_PROJECT.json", guide)
        self.assertIn("FRIDAY_GOVERNED_INTEGRATION_PROOF_2026-10-22.md", guide)
        self.assertIn("Foundry", guide)
        self.assertIn("PR #35", guide)
        self.assertIn("merged into the existing development branch", guide)
        self.assertIn("read", guide.lower())
        self.assertIn("Stop", guide)
        self.assertIn("parked", guide.lower())
        self.assertIn("historical", guide.lower())
        self.assertNotIn("Execute Phase 0 exactly", guide)
        self.assertNotIn("### PHASE 0", guide)
        self.assertNotIn("Create a candidate branch in this AIOS repo", guide)
        self.assertNotIn("Continue automatically into KERNEL V0.2", guide)

    def test_local_agent_governance_cannot_supersede_global_harness(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("AIOS-local safety harness", agents)
        self.assertIn("Harness Card", agents)
        self.assertIn("parked lanes", agents)

    def test_root_readme_points_to_one_active_codex_entry(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("start with `CODEX_START_HERE.md`", readme)
        self.assertIn("merged on `software-builder-v0`", readme)
        self.assertIn("Do not promote authority automatically", readme)

    def test_historical_handoff_renders_as_actual_markdown(self):
        handoff = (ROOT / "docs/CODEX_HANDOFF.md").read_text(encoding="utf-8")
        self.assertIn("CURRENT GOVERNING CORRECTION", handoff)
        self.assertNotIn(r"\n\n## Context", handoff)
        self.assertIn("\n\n## Context", handoff)


if __name__ == "__main__":
    unittest.main()
