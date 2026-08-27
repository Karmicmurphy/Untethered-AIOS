from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from companion.foundation.promotion import ActivationRegistry, PromotionError, atomic_write_json
from companion.foundation.worker_harness import WorkerHarness

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Worker Harness v0.1 is Windows-specific")
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "worker_harness" / "reference-input.md"


@pytest.fixture
def harness(tmp_path: Path) -> WorkerHarness:
    return WorkerHarness(tmp_path / "harness", fixture_source=FIXTURE, allow_test_faults=True)


def execute(harness: WorkerHarness) -> dict:
    plan = harness.plan(worker_id="reference-metadata-worker", actor="pytest")
    return harness.run(plan_id=plan["plan_id"], actor="pytest")


def context(candidate: dict, *, decision: str = "approve") -> dict:
    return {
        "candidate_hash": candidate["candidate_hash"],
        "workspace_generation": candidate["workspace_generation"],
        "actor": "pytest-owner",
        "decision": decision,
        "note": "fixture",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def activation_context(candidate: dict) -> dict:
    value = context(candidate)
    value.pop("decision")
    value.pop("note")
    return value


def test_candidate_output_change_blocks_approval(harness: WorkerHarness) -> None:
    candidate = execute(harness)
    Path(candidate["candidate_output_path"]).write_text("{}", encoding="utf-8")
    with pytest.raises(PromotionError) as exc_info:
        harness.approve(candidate["candidate_id"], context(candidate))
    assert exc_info.value.code == "candidate_output_changed"


def test_candidate_record_change_is_detected_before_approval(harness: WorkerHarness) -> None:
    candidate = execute(harness)
    path = harness.candidates_dir / f"{candidate['candidate_id']}.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["transaction_id"] = "0" * 32
    atomic_write_json(path, record)
    with pytest.raises(PromotionError) as exc_info:
        harness.approve(candidate["candidate_id"], context(candidate))
    assert exc_info.value.code == "candidate_hash_mismatch"


def test_stale_workspace_generation_blocks_approval(harness: WorkerHarness) -> None:
    candidate = execute(harness)
    harness._bump_generation("test-only concurrent workspace change")
    with pytest.raises(PromotionError) as exc_info:
        harness.approve(candidate["candidate_id"], context(candidate))
    assert exc_info.value.code == "workspace_generation_stale"


def test_incorrect_expected_hash_or_generation_blocks_approval(harness: WorkerHarness) -> None:
    candidate = execute(harness)
    wrong_hash = context(candidate)
    wrong_hash["candidate_hash"] = "0" * 64
    with pytest.raises(PromotionError) as exc_info:
        harness.approve(candidate["candidate_id"], wrong_hash)
    assert exc_info.value.code == "candidate_hash_mismatch"
    wrong_generation = context(candidate)
    wrong_generation["workspace_generation"] += 1
    with pytest.raises(PromotionError) as exc_info:
        harness.approve(candidate["candidate_id"], wrong_generation)
    assert exc_info.value.code == "workspace_generation_mismatch"


def test_modified_worker_card_after_execution_blocks_approval(harness: WorkerHarness) -> None:
    candidate = execute(harness)
    card = json.loads(harness.card_path.read_text(encoding="utf-8"))
    card["purpose"] += " changed"
    atomic_write_json(harness.card_path, card)
    with pytest.raises(PromotionError) as exc_info:
        harness.approve(candidate["candidate_id"], context(candidate))
    assert exc_info.value.code == "worker_card_changed"


def test_replayed_approval_is_rejected(harness: WorkerHarness) -> None:
    candidate = execute(harness)
    approved = harness.approve(candidate["candidate_id"], context(candidate))
    with pytest.raises(PromotionError) as exc_info:
        harness.approve(candidate["candidate_id"], context(approved))
    assert exc_info.value.code == "candidate_state_rejected"


def test_explicit_rejection_cannot_activate(harness: WorkerHarness) -> None:
    candidate = execute(harness)
    rejected = harness.approve(candidate["candidate_id"], context(candidate, decision="reject"))
    assert rejected["lifecycle_state"] == "rejected"
    with pytest.raises(PromotionError) as exc_info:
        harness.activate(candidate["candidate_id"], activation_context(rejected))
    assert exc_info.value.code == "candidate_state_rejected"


def test_duplicate_activation_is_rejected(harness: WorkerHarness) -> None:
    candidate = execute(harness)
    approved = harness.approve(candidate["candidate_id"], context(candidate))
    active = harness.activate(candidate["candidate_id"], activation_context(approved))
    with pytest.raises(PromotionError) as exc_info:
        harness.activate(candidate["candidate_id"], activation_context(active))
    assert exc_info.value.code == "candidate_state_rejected"


def test_interrupted_activation_registry_write_is_detected_and_does_not_activate(harness: WorkerHarness) -> None:
    candidate = execute(harness)
    approved = harness.approve(candidate["candidate_id"], context(candidate))
    with pytest.raises(PromotionError) as exc_info:
        harness.activate(candidate["candidate_id"], activation_context(approved), interrupt_registry_write=True)
    assert exc_info.value.code == "registry_write_interrupted"
    assert harness.get_candidate(candidate["candidate_id"])["lifecycle_state"] == "approved"
    audit = harness.registry.audit()
    assert audit["ok"] is False
    assert audit["code"] == "registry_interrupted"
    assert not harness.registry.path.exists()


def test_rollback_rejects_modified_current_output(harness: WorkerHarness) -> None:
    candidate = execute(harness)
    approved = harness.approve(candidate["candidate_id"], context(candidate))
    active = harness.activate(candidate["candidate_id"], activation_context(approved))
    harness.output_path.write_text("changed after activation", encoding="utf-8")
    with pytest.raises(PromotionError) as exc_info:
        harness.rollback(candidate["candidate_id"], activation_context(active))
    assert exc_info.value.code == "rollback_current_hash_mismatch"


def test_missing_or_changed_recovery_point_blocks_approval(harness: WorkerHarness) -> None:
    candidate = execute(harness)
    Path(candidate["recovery_point"]["snapshot_path"]).write_text("tampered", encoding="utf-8")
    with pytest.raises(PromotionError) as exc_info:
        harness.approve(candidate["candidate_id"], context(candidate))
    assert exc_info.value.code == "recovery_point_unavailable"


def test_receipt_chain_tamper_blocks_approval(harness: WorkerHarness) -> None:
    candidate = execute(harness)
    receipt_path = Path(candidate["receipt_paths"][0])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["result"]["ok"] = False
    atomic_write_json(receipt_path, receipt)
    with pytest.raises(PromotionError) as exc_info:
        harness.approve(candidate["candidate_id"], context(candidate))
    assert exc_info.value.code == "receipt_chain_invalid"


def test_registry_directly_rejects_duplicate_candidate(tmp_path: Path) -> None:
    registry = ActivationRegistry(tmp_path / "registry.json")
    candidate = {
        "candidate_id": "a" * 32,
        "candidate_hash": "B" * 64,
        "worker_id": "reference-metadata-worker",
        "worker_version": "0.1.0",
        "worker_card_path": "card.json",
        "transaction_id": "c" * 32,
        "receipt_paths": [],
        "recovery_point": {},
    }
    registry.activate(candidate, actor="owner", timestamp="2026-07-16T00:00:00Z", activation_record_path="activation.json")
    with pytest.raises(PromotionError) as exc_info:
        registry.activate(candidate, actor="owner", timestamp="2026-07-16T00:00:01Z", activation_record_path="activation.json")
    assert exc_info.value.code == "duplicate_activation"
