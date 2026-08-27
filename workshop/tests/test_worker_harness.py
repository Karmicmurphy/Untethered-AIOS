from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from companion.foundation.artifact_compass import ArtifactCompass
from companion.foundation.promotion import PromotionError
from companion.foundation.transactions import sha256_file
from companion.foundation.worker_harness import HarnessError, WorkerHarness

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Worker Harness v0.1 is Windows-specific")
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "worker_harness" / "reference-input.md"


@pytest.fixture
def harness(tmp_path: Path) -> WorkerHarness:
    protected = tmp_path / "protected-private"
    protected.mkdir()
    return WorkerHarness(tmp_path / "harness", fixture_source=FIXTURE, protected_roots=[protected], allow_test_faults=True)


def approval_context(candidate: dict, *, decision: str = "approve", actor: str = "pytest-owner") -> dict:
    return {
        "candidate_hash": candidate["candidate_hash"],
        "workspace_generation": candidate["workspace_generation"],
        "actor": actor,
        "decision": decision,
        "note": "explicit fixture decision",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def activation_context(candidate: dict, *, actor: str = "pytest-owner") -> dict:
    return {
        "candidate_hash": candidate["candidate_hash"],
        "workspace_generation": candidate["workspace_generation"],
        "actor": actor,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def execute_candidate(harness: WorkerHarness) -> tuple[dict, dict, str]:
    plan = harness.plan(worker_id="reference-metadata-worker", actor="pytest-initiator")
    baseline_hash = sha256_file(harness.output_path)
    candidate = harness.run(plan_id=plan["plan_id"], actor="pytest-initiator")
    return plan, candidate, baseline_hash


def test_execution_plan_displays_exact_authority_and_no_automatic_activation(harness: WorkerHarness) -> None:
    plan, candidate, _ = execute_candidate(harness)
    assert plan["requested_permissions"] == {
        "network": False,
        "shell": False,
        "destructive_actions": False,
        "approval_required": True,
    }
    assert plan["enforcement"]["allowed"] is True
    assert plan["fixed_command_prefix"][1:4] == ["-m", "companion.foundation.reference_worker", "--request"]
    assert plan["expected_file_effects"]["changed"] == [str(harness.output_path)]
    assert plan["recovery_point_plan"]["kind"] == "file_snapshot"
    assert candidate["lifecycle_state"] == "awaiting_approval"
    assert candidate["output"]["worker_id"] == "reference-metadata-worker"
    assert candidate["output"]["headings"][0]["text"] == "Harmless Worker Fixture"
    assert all(test["passed"] for test in candidate["test_results"])
    assert candidate["file_effects"]["unexpected_created"] == []
    assert candidate["activation"] is None
    assert not harness.registry.path.exists()
    assert harness.verify_receipts()["valid"] is True


def test_output_is_deterministic_across_fresh_bounded_workspaces(tmp_path: Path) -> None:
    outputs = []
    for index in range(2):
        worker = WorkerHarness(tmp_path / f"harness-{index}", fixture_source=FIXTURE, allow_test_faults=True)
        plan = worker.plan(worker_id="reference-metadata-worker", actor="pytest")
        outputs.append(worker.run(plan_id=plan["plan_id"], actor="pytest")["output"])
    assert outputs[0] == outputs[1]


@pytest.mark.parametrize(
    ("fault_mode", "expected_code"),
    [
        ("sleep", "worker_timeout"),
        ("worker_failure", "worker_failed"),
        ("invalid_output", "output_schema_invalid"),
        ("declared_test_failure", "declared_test_failed"),
        ("malformed_json", "output_malformed_json"),
        ("oversized_output", "output_oversized"),
        ("unexpected_file", "unexpected_file_effect"),
    ],
)
def test_failure_modes_fail_closed_and_restore_previous_output(
    harness: WorkerHarness,
    fault_mode: str,
    expected_code: str,
) -> None:
    plan = harness.plan(worker_id="reference-metadata-worker", actor="pytest")
    baseline_hash = sha256_file(harness.output_path)
    with pytest.raises(HarnessError) as exc_info:
        harness.run(plan_id=plan["plan_id"], actor="pytest", fault_mode=fault_mode)
    assert exc_info.value.code == expected_code
    assert sha256_file(harness.output_path) == baseline_hash
    assert not (harness.output_dir / "unexpected.txt").exists()
    assert harness.verify_receipts()["valid"] is True


def test_captured_streams_are_bounded_without_failing_harmless_output(harness: WorkerHarness) -> None:
    plan = harness.plan(worker_id="reference-metadata-worker", actor="pytest")
    candidate = harness.run(plan_id=plan["plan_id"], actor="pytest", fault_mode="oversized_capture")
    assert candidate["capture"]["stdout_truncated"] is True
    assert len(candidate["capture"]["stdout"].encode("utf-8")) <= 16 * 1024
    receipt = json.loads(Path(candidate["receipt_paths"][0]).read_text(encoding="utf-8"))
    serialized = json.dumps(receipt)
    assert "reference worker completed" not in serialized
    assert "stdout_bytes" in serialized


def test_full_approval_activation_and_hash_verified_rollback(harness: WorkerHarness) -> None:
    _, candidate, baseline_hash = execute_candidate(harness)
    approved = harness.approve(candidate["candidate_id"], approval_context(candidate))
    assert approved["lifecycle_state"] == "approved"
    assert not harness.registry.path.exists()
    active = harness.activate(candidate["candidate_id"], activation_context(approved))
    assert active["lifecycle_state"] == "active"
    registry = harness.registry.load()
    assert registry["entries"][0]["status"] == "active"
    assert registry["entries"][0]["executes_on_startup"] is False
    assert registry["entries"][0]["grants_permissions"] is False
    rolled_back = harness.rollback(candidate["candidate_id"], activation_context(active))
    assert rolled_back["lifecycle_state"] == "rolled_back"
    assert sha256_file(harness.output_path) == baseline_hash
    assert harness.registry.load()["entries"][0]["status"] == "rolled_back"
    assert harness.verify_receipts()["valid"] is True


def test_artifact_compass_links_full_safe_provenance_flow(harness: WorkerHarness) -> None:
    _, candidate, _ = execute_candidate(harness)
    approved = harness.approve(candidate["candidate_id"], approval_context(candidate))
    active = harness.activate(candidate["candidate_id"], activation_context(approved))
    harness.rollback(candidate["candidate_id"], activation_context(active))
    with ArtifactCompass(harness.compass_path) as compass:
        records = compass.search(project_id="worker-harness-prototype")
    kinds = {record["provenance"]["kind"] for record in records}
    assert {
        "worker-card", "execution-plan", "transaction-manifest", "receipt", "test-result",
        "candidate-output", "candidate-record", "approval-decision", "activation-record", "rollback-record",
    }.issubset(kinds)


def test_approval_note_is_not_written_to_receipts(harness: WorkerHarness) -> None:
    _, candidate, _ = execute_candidate(harness)
    context = approval_context(candidate)
    context["note"] = "LOCAL-NOTE-MUST-NOT-ENTER-RECEIPTS"
    harness.approve(candidate["candidate_id"], context)
    for receipt_path in harness.transactions_dir.joinpath("receipts").glob("*.json"):
        assert context["note"] not in receipt_path.read_text(encoding="utf-8")


def test_approval_requires_an_explicit_nonempty_note(harness: WorkerHarness) -> None:
    _, candidate, _ = execute_candidate(harness)
    context = approval_context(candidate)
    context["note"] = "   "
    with pytest.raises(PromotionError) as exc_info:
        harness.approve(candidate["candidate_id"], context)
    assert exc_info.value.code == "approval_note_required"
    assert harness.get_candidate(candidate["candidate_id"])["lifecycle_state"] == "awaiting_approval"
