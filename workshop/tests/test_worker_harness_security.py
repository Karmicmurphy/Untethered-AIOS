from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from companion.foundation.path_policy import WindowsPathPolicy
from companion.foundation.promotion import atomic_write_json, hash_json
from companion.foundation.reference_worker import main as reference_worker_main, run_request
from companion.foundation.transactions import TransactionManager
from companion.foundation.worker_harness import HarnessError, WorkerHarness

pytestmark = pytest.mark.skipif(os.name != "nt", reason="Worker Harness v0.1 is Windows-specific")
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "worker_harness" / "reference-input.md"


@pytest.fixture
def harness(tmp_path: Path) -> WorkerHarness:
    protected = tmp_path / "protected"
    protected.mkdir()
    (protected / "private.md").write_text("# Harmless-looking but blocked\n", encoding="utf-8")
    return WorkerHarness(tmp_path / "harness", fixture_source=FIXTURE, protected_roots=[protected], allow_test_faults=True)


def test_invalid_worker_card_and_unsupported_permissions_are_denied(harness: WorkerHarness) -> None:
    invalid = harness._expected_card()
    invalid.pop("purpose")
    result = harness.validate_card(invalid)
    assert result["valid"] is False
    network = harness._expected_card()
    network["network_allowed"] = True
    result = harness.validate_card(network)
    assert result["valid"] is True
    assert result["enforcement"]["allowed"] is False
    assert any("network" in reason for reason in result["enforcement"]["denied_reasons"])
    shell = harness._expected_card()
    shell["shell_allowed"] = True
    result = harness.validate_card(shell)
    assert result["enforcement"]["allowed"] is False
    destructive = harness._expected_card()
    destructive["destructive_actions_allowed"] = True
    result = harness.validate_card(destructive)
    assert result["enforcement"]["allowed"] is False


def test_validation_returns_the_exact_card_and_hash_for_truthful_ui(harness: WorkerHarness) -> None:
    card = harness._expected_card()
    result = harness.validate_card(worker_id="reference-metadata-worker")
    assert result["valid"] is True
    assert result["enforcement"]["allowed"] is True
    assert result["card"] == card
    assert result["worker_card_hash"] == hash_json(card)


def test_modified_card_after_planning_blocks_execution(harness: WorkerHarness) -> None:
    plan = harness.plan(worker_id="reference-metadata-worker", actor="pytest")
    card = json.loads(harness.card_path.read_text(encoding="utf-8"))
    card["purpose"] += " changed after plan"
    atomic_write_json(harness.card_path, card)
    with pytest.raises(HarnessError) as exc_info:
        harness.run(plan_id=plan["plan_id"], actor="pytest")
    assert exc_info.value.code == "worker_card_changed"


def test_modified_plan_hash_blocks_execution(harness: WorkerHarness) -> None:
    plan = harness.plan(worker_id="reference-metadata-worker", actor="pytest")
    path = harness.plans_dir / f"{plan['plan_id']}.json"
    changed = json.loads(path.read_text(encoding="utf-8"))
    changed["timeout_seconds"] += 1
    atomic_write_json(path, changed)
    with pytest.raises(HarnessError) as exc_info:
        harness.run(plan_id=plan["plan_id"], actor="pytest")
    assert exc_info.value.code == "plan_hash_mismatch"


def test_parent_traversal_and_blocked_root_are_rejected_by_child_policy(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    output = tmp_path / "output"
    blocked = tmp_path / "blocked"
    outside = tmp_path / "outside.md"
    for path in (allowed, output, blocked):
        path.mkdir()
    outside.write_text("outside", encoding="utf-8")
    blocked_file = blocked / "private.md"
    blocked_file.write_text("blocked", encoding="utf-8")
    base = {
        "read_roots": [str(tmp_path)],
        "write_roots": [str(output)],
        "blocked_roots": [str(blocked)],
        "output_path": str(output / "result.json"),
    }
    with pytest.raises(PermissionError, match="parent_traversal"):
        run_request({**base, "input_path": str(allowed / ".." / "outside.md")})
    with pytest.raises(PermissionError, match="blocked_root"):
        run_request({**base, "input_path": str(blocked_file)})


def test_malicious_output_filename_is_rejected(tmp_path: Path) -> None:
    source = tmp_path / "input.md"
    output = tmp_path / "output"
    output.mkdir()
    source.write_text("safe", encoding="utf-8")
    request = {
        "read_roots": [str(tmp_path)],
        "write_roots": [str(output)],
        "blocked_roots": [],
        "input_path": str(source),
        "output_path": str(output / "result.json") + ":stream",
    }
    with pytest.raises(PermissionError, match="unsafe_windows_component"):
        run_request(request)


def test_junction_root_substitution_after_planning_is_rejected(harness: WorkerHarness, tmp_path: Path) -> None:
    plan = harness.plan(worker_id="reference-metadata-worker", actor="pytest")
    original = harness.workspace / "output-original"
    harness.output_dir.rename(original)
    outside = tmp_path / "outside-output"
    outside.mkdir()
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", "mklink", "/J", str(harness.output_dir), str(outside)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        pytest.skip(f"junction creation unavailable: {result.stderr or result.stdout}")
    try:
        with pytest.raises(HarnessError) as exc_info:
            harness.run(plan_id=plan["plan_id"], actor="pytest")
        assert exc_info.value.code == "canonical_root_changed"
        assert not (outside / "reference-result.json").exists()
    finally:
        harness.output_dir.rmdir()
        original.rename(harness.output_dir)


def test_test_fault_injection_is_unavailable_in_production_harness(tmp_path: Path) -> None:
    harness = WorkerHarness(tmp_path / "harness", fixture_source=FIXTURE, allow_test_faults=False)
    plan = harness.plan(worker_id="reference-metadata-worker", actor="pytest")
    with pytest.raises(HarnessError) as exc_info:
        harness.run(plan_id=plan["plan_id"], actor="pytest", fault_mode="worker_failure")
    assert exc_info.value.code == "test_faults_disabled"


def test_fixed_worker_environment_does_not_inherit_credentials_or_proxies(
    harness: WorkerHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-reach-child")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "must-not-reach-child")
    monkeypatch.setenv("HTTPS_PROXY", "http://must-not-reach-child")
    environment = harness._worker_environment()
    assert "OPENAI_API_KEY" not in environment
    assert "AWS_SECRET_ACCESS_KEY" not in environment
    assert "HTTPS_PROXY" not in environment
    assert environment["PYTHONNOUSERSITE"] == "1"
    assert environment["PYTHONPATH"] == str(harness.runtime_root)


def test_child_rejects_request_file_that_does_not_match_parent_hash(tmp_path: Path) -> None:
    request_path = tmp_path / "request.json"
    request_path.write_text("{}", encoding="utf-8")
    result = reference_worker_main(
        ["--request", str(request_path), "--request-sha256", "0" * 64]
    )
    assert result == 2


def test_process_launch_error_fails_closed_restores_output_and_writes_terminal_receipt(
    harness: WorkerHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    plan = harness.plan(worker_id="reference-metadata-worker", actor="pytest")
    before = harness.output_path.read_bytes()

    def fail_launch(*args, **kwargs):
        raise OSError("test-only launch failure")

    monkeypatch.setattr(harness, "_execute_fixed_worker", fail_launch)
    with pytest.raises(HarnessError) as exc_info:
        harness.run(plan_id=plan["plan_id"], actor="pytest")
    assert exc_info.value.code == "harness_internal_failure"
    assert harness.output_path.read_bytes() == before
    assert harness.verify_receipts()["valid"] is True
    manifests = [json.loads(path.read_text(encoding="utf-8")) for path in harness.transactions_dir.joinpath("manifests").glob("*.json")]
    assert manifests[-1]["state"] == "failed"


def test_interrupted_transaction_is_detected_after_harness_restart(harness: WorkerHarness) -> None:
    plan = harness.plan(worker_id="reference-metadata-worker", actor="pytest")
    policy = harness._host_policy()
    first = TransactionManager(harness.transactions_dir, actor="pytest", path_policy=policy)
    manifest = first.prepare(
        action="test.interrupted",
        paths=[harness.input_path],
        permission_decision={"allowed": True, "component": "pytest"},
    )
    first.begin(manifest["transaction_id"])
    restarted = TransactionManager(harness.transactions_dir, actor="restart-auditor", path_policy=policy)
    interrupted = restarted.detect_interrupted()
    assert any(item["transaction_id"] == manifest["transaction_id"] for item in interrupted)


def test_worker_card_cannot_redirect_to_protected_root(harness: WorkerHarness) -> None:
    card = harness._expected_card()
    card["allowed_read_roots"] = card["blocked_roots"]
    result = harness.validate_card(card)
    assert result["enforcement"]["allowed"] is False
    assert any("allowed_read_roots" in reason for reason in result["enforcement"]["denied_reasons"])


def test_no_shell_or_eval_execution_surface_in_worker_sources() -> None:
    worker = (ROOT / "companion" / "foundation" / "reference_worker.py").read_text(encoding="utf-8")
    harness = (ROOT / "companion" / "foundation" / "worker_harness.py").read_text(encoding="utf-8")
    assert "shell=False" in harness
    assert "shell=True" not in harness + worker
    assert "eval(" not in harness + worker
    assert "exec(" not in harness + worker
    assert "urllib" not in worker
