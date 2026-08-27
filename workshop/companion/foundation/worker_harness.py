from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Any, BinaryIO

from companion.foundation.artifact_compass import ArtifactCompass, ArtifactRecord
from companion.foundation.artifact_inspection_worker import (
    FILE_TYPES as INSPECTION_FILE_TYPES,
    MAX_INPUT_BYTES as INSPECTION_MAX_INPUT_BYTES,
    MAX_OUTPUT_BYTES as INSPECTION_MAX_OUTPUT_BYTES,
    OUTPUT_SCHEMA_VERSION as INSPECTION_SCHEMA_VERSION,
    SUPPORTED_EXTENSIONS as INSPECTION_EXTENSIONS,
    WORKER_ID as INSPECTION_WORKER_ID,
    WORKER_VERSION as INSPECTION_WORKER_VERSION,
    inspect_content,
)
from companion.foundation.path_policy import WindowsPathPolicy
from companion.foundation.promotion import (
    ActivationRegistry,
    CandidateStore,
    PromotionError,
    atomic_write_json,
    calculate_candidate_hash,
    hash_json,
    transition,
    utc_now,
    validate_timestamp,
)
from companion.foundation.reference_worker import (
    MAX_OUTPUT_BYTES,
    OUTPUT_SCHEMA_VERSION,
    WORKER_ID,
    WORKER_VERSION,
    _metadata,
)
from companion.foundation.transactions import TransactionManager, sha256_file
from companion.foundation.worker_cards import validate_worker_card

HARNESS_SCHEMA_VERSION = "0.3"
SUPPORTED_TEST_ID = "reference-output-v0.1"
INSPECTION_TEST_ID = "artifact-inspection-output-v0.4"
MAX_CAPTURE_BYTES = 16 * 1024
PROJECT_ID = "worker-harness-prototype"


class HarnessError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


def _safe_read_json(path: Path, *, code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessError(code, f"invalid JSON evidence: {path.name}") from exc
    if not isinstance(value, dict):
        raise HarnessError(code, f"JSON evidence must be an object: {path.name}")
    return value


def _bounded_pipe_reader(pipe: BinaryIO, limit: int, output: dict[str, Any], key: str) -> None:
    captured = bytearray()
    total = 0
    while True:
        chunk = pipe.read(4096)
        if not chunk:
            break
        total += len(chunk)
        remaining = max(0, limit - len(captured))
        if remaining:
            captured.extend(chunk[:remaining])
    output[key] = captured.decode("utf-8", errors="replace")
    output[f"{key}_bytes"] = total
    output[f"{key}_truncated"] = total > limit


class WorkerHarness:
    """Bounded harness for one fixed harmless reference worker.

    The parent enforces card compatibility, authority, path policy, plan/card
    hashes, timeout, output limits, effects, tests, approval, and lifecycle.
    The child rechecks paths and file types. This is not hostile-process
    isolation and does not load arbitrary workers.
    """

    def __init__(
        self,
        root: str | os.PathLike[str],
        *,
        fixture_source: str | os.PathLike[str],
        protected_roots: list[str | os.PathLike[str]] | None = None,
        public_artifact_roots: list[str | os.PathLike[str]] | None = None,
        allow_test_faults: bool = False,
    ) -> None:
        self.root = Path(root).resolve(strict=False)
        self.fixture_source = Path(fixture_source).resolve(strict=False)
        self.protected_roots = [str(Path(path).resolve(strict=False)) for path in (protected_roots or [])]
        self.public_artifact_roots = [
            str(Path(path).resolve(strict=False)) for path in (public_artifact_roots or [])
        ]
        self.allow_test_faults = allow_test_faults
        self.workspace = self.root / "workspace"
        self.input_dir = self.workspace / "input"
        self.output_dir = self.workspace / "output"
        self.input_path = self.input_dir / "reference-input.md"
        self.output_path = self.output_dir / "reference-result.json"
        self.inspection_output_dir = self.workspace / "inspection-output"
        self.inspection_output_path = self.inspection_output_dir / "artifact-inspection-result.json"
        self.state_path = self.workspace / "state.json"
        self.cards_dir = self.root / "worker-cards"
        self.card_path = self.cards_dir / f"{WORKER_ID}.json"
        self.inspection_card_path = self.cards_dir / f"{INSPECTION_WORKER_ID}.json"
        self.plans_dir = self.root / "plans"
        self.requests_dir = self.root / "requests"
        self.candidates_dir = self.root / "candidates"
        self.candidate_outputs_dir = self.root / "candidate-outputs"
        self.tests_dir = self.root / "test-results"
        self.runs_dir = self.root / "runs"
        self.decisions_dir = self.root / "approval-decisions"
        self.activations_dir = self.root / "activation-records"
        self.rollbacks_dir = self.root / "rollback-records"
        self.transactions_dir = self.root / "transactions"
        self.registry = ActivationRegistry(self.root / "activation-registry.json")
        self.candidates = CandidateStore(self.candidates_dir)
        self.provenance_path = self.root / "provenance-inventory.json"
        self.compass_path = self.root / "artifact-compass.sqlite3"
        self.runtime_root = Path(__file__).resolve().parents[2]
        self._canonical_anchors = {
            "root": str(self.root.resolve(strict=False)),
            "workspace": str(self.workspace.resolve(strict=False)),
            "input": str(self.input_dir.resolve(strict=False)),
            "output": str(self.output_dir.resolve(strict=False)),
            "inspection_output": str(self.inspection_output_dir.resolve(strict=False)),
        }
        for index, public_root in enumerate(self.public_artifact_roots):
            self._canonical_anchors[f"public_artifact_{index}"] = str(Path(public_root).resolve(strict=False))
        self._lock = threading.RLock()

    def list_workers(self) -> list[dict[str, Any]]:
        card = self._expected_card()
        result = validate_worker_card(card)
        workers = [
            {
                "worker_id": WORKER_ID,
                "version": WORKER_VERSION,
                "lifecycle_status": card["lifecycle_status"],
                "purpose": card["purpose"],
                "card_valid": result.valid,
                "execution_mechanism": "fixed-python-module-subprocess",
                "auto_activation": False,
                "network": "unsupported",
                "shell": "unsupported",
                "destructive_actions": "unsupported",
                "hostile_process_isolation": "unsupported",
                "workspace": str(self.workspace),
            }
        ]
        if self.public_artifact_roots:
            inspection_card = self._expected_inspection_card()
            inspection_result = validate_worker_card(inspection_card)
            workers.append(
                {
                    "worker_id": INSPECTION_WORKER_ID,
                    "version": INSPECTION_WORKER_VERSION,
                    "lifecycle_status": inspection_card["lifecycle_status"],
                    "purpose": inspection_card["purpose"],
                    "card_valid": inspection_result.valid,
                    "execution_mechanism": "fixed-python-module-subprocess",
                    "auto_activation": False,
                    "activation_kind": "artifact-inspection-report-attachment",
                    "network": "unsupported",
                    "shell": "unsupported",
                    "destructive_actions": "unsupported",
                    "hostile_process_isolation": "unsupported",
                    "workspace": str(self.workspace),
                }
            )
        return workers

    def validate_card(
        self,
        card: dict[str, Any] | None = None,
        *,
        worker_id: str = WORKER_ID,
    ) -> dict[str, Any]:
        if worker_id == INSPECTION_WORKER_ID:
            if not self.public_artifact_roots:
                raise HarnessError("public_roots_unavailable", "no approved public-safe artifact roots are available")
            supplied = card if card is not None else self._expected_inspection_card()
            evaluator = self._evaluate_inspection_permissions
        elif worker_id == WORKER_ID:
            supplied = card if card is not None else self._expected_card()
            evaluator = self._evaluate_permissions
        else:
            raise HarnessError("worker_unsupported", "worker ID is not supported by the fixed harness")
        result = validate_worker_card(supplied)
        issues = [issue.__dict__ for issue in result.issues]
        try:
            enforcement = evaluator(supplied)
        except (KeyError, TypeError, ValueError):
            enforcement = {"allowed": False, "denied_reasons": ["card authority fields are malformed"]}
        if not result.valid:
            enforcement["allowed"] = False
            enforcement.setdefault("denied_reasons", []).insert(0, "card validation failed")
        return {
            "valid": result.valid,
            "issues": issues,
            "enforcement": enforcement,
            "card": supplied,
            "worker_card_hash": hash_json(supplied),
        }

    def plan(
        self,
        *,
        worker_id: str,
        actor: str,
        artifact: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if worker_id == INSPECTION_WORKER_ID:
                return self._plan_artifact_inspection(actor=actor, artifact=artifact)
            if worker_id != WORKER_ID:
                raise HarnessError("worker_unsupported", "only the fixed harmless reference worker is supported")
            if not actor.strip():
                raise HarnessError("actor_required", "initiating actor is required")
            self._ensure_workspace()
            card = self._load_fixed_card()
            card_result = validate_worker_card(card)
            if not card_result.valid:
                raise HarnessError("worker_card_invalid", "Worker Card validation failed", details={"issues": [i.__dict__ for i in card_result.issues]})
            expected_card = self._expected_card()
            if hash_json(card) != hash_json(expected_card):
                raise HarnessError("worker_card_drift", "stored reference Worker Card differs from the fixed supported card")
            enforcement = self._evaluate_permissions(card)
            if not enforcement["allowed"]:
                raise HarnessError("authority_denied", "Worker Card requests unsupported authority", details=enforcement)
            generation = self._load_state()["generation"]
            plan_id = uuid.uuid4().hex
            plan: dict[str, Any] = {
                "schema_version": HARNESS_SCHEMA_VERSION,
                "plan_id": plan_id,
                "worker_id": card["worker_id"],
                "worker_version": card["version"],
                "lifecycle_status": card["lifecycle_status"],
                "purpose": card["purpose"],
                "initiating_actor": actor,
                "inputs": [{"path": str(self.input_path), "sha256": sha256_file(self.input_path), "size_bytes": self.input_path.stat().st_size}],
                "outputs": [{"path": str(self.output_path), "content_type": "application/json"}],
                "canonical_read_roots": [str(Path(path).resolve(strict=False)) for path in card["allowed_read_roots"]],
                "canonical_write_roots": [str(Path(path).resolve(strict=False)) for path in card["allowed_write_roots"]],
                "blocked_roots": [str(Path(path).resolve(strict=False)) for path in card["blocked_roots"]],
                "requested_permissions": {
                    "network": card["network_allowed"],
                    "shell": card["shell_allowed"],
                    "destructive_actions": card["destructive_actions_allowed"],
                    "approval_required": card["approval_required"],
                },
                "enforcement": enforcement,
                "callable_entry_point": "companion.foundation.reference_worker",
                "fixed_command_prefix": [
                    sys.executable, "-m", "companion.foundation.reference_worker", "--request",
                    "<runtime-request-json>", "--request-sha256", "<runtime-request-sha256>",
                ],
                "timeout_seconds": card["timeout_seconds"],
                "max_captured_stream_bytes": MAX_CAPTURE_BYTES,
                "max_output_bytes": MAX_OUTPUT_BYTES,
                "expected_file_effects": {"created": [], "changed": [str(self.output_path)], "unexpected_allowed": False},
                "required_tests": card["test_commands"],
                "recovery_point_plan": {"kind": "file_snapshot", "source": str(self.output_path), "restore_scope": "one bounded output file"},
                "worker_card_path": str(self.card_path),
                "worker_card_hash": hash_json(card),
                "workspace_generation": generation,
                "created_at": utc_now(),
                "auto_activate": False,
            }
            plan["plan_hash"] = hash_json(plan)
            atomic_write_json(self.plans_dir / f"{plan_id}.json", plan)
            self._record_evidence("execution-plan", self.plans_dir / f"{plan_id}.json", "execution_planned", plan_id=plan_id)
            return plan

    def _plan_artifact_inspection(
        self,
        *,
        actor: str,
        artifact: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if not actor.strip():
            raise HarnessError("actor_required", "initiating actor is required")
        if not self.public_artifact_roots:
            raise HarnessError("public_roots_unavailable", "no approved public-safe artifact roots are available")
        selected = self._validate_artifact_descriptor(artifact)
        self._ensure_inspection_workspace()
        card = self._load_inspection_card()
        card_result = validate_worker_card(card)
        if not card_result.valid:
            raise HarnessError(
                "worker_card_invalid",
                "Artifact Inspection Worker Card validation failed",
                details={"issues": [issue.__dict__ for issue in card_result.issues]},
            )
        expected_card = self._expected_inspection_card()
        if hash_json(card) != hash_json(expected_card):
            raise HarnessError("worker_card_drift", "stored Artifact Inspection Worker Card differs from the fixed supported card")
        enforcement = self._evaluate_inspection_permissions(card)
        if not enforcement["allowed"]:
            raise HarnessError("authority_denied", "Artifact Inspection Worker Card requests unsupported authority", details=enforcement)
        policy = WindowsPathPolicy(
            read_roots=card["allowed_read_roots"],
            write_roots=card["allowed_write_roots"],
            blocked_roots=card["blocked_roots"],
        )
        decision = policy.decide(selected["source_path"], mode="read")
        try:
            source_path = decision.require_allowed()
        except PermissionError as exc:
            raise HarnessError(
                "artifact_path_denied",
                "selected artifact is outside approved public-safe roots or inside a blocked root",
                details={"code": decision.code, "reason": decision.reason},
            ) from exc
        policy.decide(self.inspection_output_path, mode="write", require_exists=False).require_allowed()
        if source_path.suffix.lower() not in INSPECTION_EXTENSIONS:
            raise HarnessError("artifact_extension_unsupported", "selected artifact extension is not supported")
        if source_path.stat().st_size > INSPECTION_MAX_INPUT_BYTES:
            raise HarnessError("artifact_oversized", "selected artifact exceeds the 512 KiB input limit")
        current_hash = sha256_file(source_path)
        if current_hash != selected["sha256"]:
            raise HarnessError("artifact_hash_mismatch", "selected artifact bytes do not match the authoritative artifact hash")
        if source_path.stat().st_size != selected["byte_count"]:
            raise HarnessError("artifact_size_mismatch", "selected artifact size differs from the authoritative artifact record")
        selected["source_path"] = str(source_path)
        selected["public_read_root"] = decision.matched_root
        generation = self._load_state()["generation"]
        plan_id = uuid.uuid4().hex
        plan: dict[str, Any] = {
            "schema_version": INSPECTION_SCHEMA_VERSION,
            "plan_id": plan_id,
            "worker_id": INSPECTION_WORKER_ID,
            "worker_version": INSPECTION_WORKER_VERSION,
            "lifecycle_status": card["lifecycle_status"],
            "purpose": card["purpose"],
            "initiating_actor": actor,
            "selected_artifact": selected,
            "inputs": [
                {
                    "artifact_id": selected["artifact_id"],
                    "path": selected["source_path"],
                    "sha256": selected["sha256"],
                    "size_bytes": selected["byte_count"],
                    "file_type": selected["file_type"],
                }
            ],
            "outputs": [{"path": str(self.inspection_output_path), "content_type": "application/json"}],
            "requested_read_root": decision.matched_root,
            "canonical_read_roots": [str(Path(path).resolve(strict=False)) for path in card["allowed_read_roots"]],
            "canonical_write_roots": [str(Path(path).resolve(strict=False)) for path in card["allowed_write_roots"]],
            "blocked_roots": [str(Path(path).resolve(strict=False)) for path in card["blocked_roots"]],
            "requested_permissions": {
                "network": False,
                "shell": False,
                "destructive_actions": False,
                "read_only_source": True,
                "approval_required": True,
            },
            "enforcement": enforcement,
            "callable_entry_point": "companion.foundation.artifact_inspection_worker",
            "fixed_command_prefix": [
                sys.executable,
                "-m",
                "companion.foundation.artifact_inspection_worker",
                "--request",
                "<runtime-request-json>",
                "--request-sha256",
                "<runtime-request-sha256>",
            ],
            "timeout_seconds": card["timeout_seconds"],
            "max_input_bytes": INSPECTION_MAX_INPUT_BYTES,
            "max_captured_stream_bytes": MAX_CAPTURE_BYTES,
            "max_output_bytes": INSPECTION_MAX_OUTPUT_BYTES,
            "expected_file_effects": {
                "created": [],
                "changed": [str(self.inspection_output_path)],
                "source_changes": [],
                "unexpected_allowed": False,
            },
            "expected_output": {
                "schema": "schemas/artifact-inspection-output-v0.4.schema.json",
                "path": str(self.inspection_output_path),
                "content_type": "application/json",
            },
            "required_tests": card["test_commands"],
            "recovery_point_plan": {
                "kind": "file_snapshot",
                "source": str(self.inspection_output_path),
                "restore_scope": "one bounded candidate workspace output plus attachment registry status",
            },
            "worker_card_path": str(self.inspection_card_path),
            "worker_card_hash": hash_json(card),
            "workspace_generation": generation,
            "created_at": utc_now(),
            "auto_activate": False,
        }
        plan["plan_hash"] = hash_json(plan)
        plan_path = self.plans_dir / f"{plan_id}.json"
        atomic_write_json(plan_path, plan)
        self._record_evidence(
            "execution-plan",
            plan_path,
            "execution_planned",
            plan_id=plan_id,
            artifact_id=selected["artifact_id"],
        )
        return plan

    def _validate_artifact_descriptor(self, artifact: dict[str, Any] | None) -> dict[str, Any]:
        required = {
            "artifact_id",
            "project_id",
            "source_path",
            "sha256",
            "file_type",
            "byte_count",
            "review_status",
            "duplicate_hash_group",
            "provenance_references",
        }
        if not isinstance(artifact, dict) or set(artifact) != required:
            raise HarnessError("artifact_selection_invalid", "an exact server-resolved artifact descriptor is required")
        selected = json.loads(json.dumps(artifact, ensure_ascii=False))
        for field in ("artifact_id", "project_id", "source_path", "file_type", "review_status"):
            if not isinstance(selected[field], str) or not selected[field].strip():
                raise HarnessError("artifact_selection_invalid", f"selected artifact {field} is required")
        digest = selected["sha256"]
        if not isinstance(digest, str) or len(digest) != 64 or any(character not in "0123456789abcdefABCDEF" for character in digest):
            raise HarnessError("artifact_selection_invalid", "selected artifact SHA-256 is invalid")
        selected["sha256"] = digest.upper()
        if type(selected["byte_count"]) is not int or selected["byte_count"] < 0:
            raise HarnessError("artifact_selection_invalid", "selected artifact byte count is invalid")
        if not isinstance(selected["duplicate_hash_group"], list) or len(selected["duplicate_hash_group"]) > 100:
            raise HarnessError("artifact_selection_invalid", "duplicate-hash group metadata is invalid or excessive")
        if not isinstance(selected["provenance_references"], list) or len(selected["provenance_references"]) > 100:
            raise HarnessError("artifact_selection_invalid", "provenance references are invalid or excessive")
        source_path = Path(selected["source_path"])
        expected_file_type = INSPECTION_FILE_TYPES.get(source_path.suffix.lower())
        if expected_file_type is None or selected["file_type"] != expected_file_type:
            raise HarnessError("artifact_extension_unsupported", "selected artifact type or extension is not supported")
        return selected

    def run(
        self,
        *,
        plan_id: str,
        actor: str,
        fault_mode: str | None = None,
        worker_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if fault_mode and not self.allow_test_faults:
                raise HarnessError("test_faults_disabled", "test-only fault injection is not available in production flow")
            plan = self._load_plan(plan_id)
            if worker_id is not None and plan.get("worker_id") != worker_id:
                raise HarnessError("plan_worker_mismatch", "execution plan does not belong to the requested worker route")
            if plan.get("worker_id") == INSPECTION_WORKER_ID:
                return self._run_artifact_inspection(plan=plan, actor=actor, fault_mode=fault_mode)
            card = self._load_fixed_card()
            self._verify_plan_authority(plan, card)
            if not actor.strip():
                raise HarnessError("actor_required", "initiating actor is required")
            candidate_id = uuid.uuid4().hex
            host_policy = self._host_policy()
            manager = TransactionManager(self.transactions_dir, actor=actor, path_policy=host_policy)
            permission_decision = {
                "allowed": True,
                "component": "worker-harness-v0.1",
                "application_enforced": plan["enforcement"],
                "host_enforced": {"timeout": True, "fixed_argv_no_shell": True, "bounded_capture": True},
                "unsupported": ["network", "unrestricted-shell", "destructive-actions", "hostile-process-isolation"],
                "execution_plan": plan,
            }
            manifest = manager.prepare(
                action="worker.reference.execute",
                paths=[self.input_path, self.output_path, self.card_path, self.plans_dir / f"{plan_id}.json"],
                permission_decision=permission_decision,
                commands=["fixed module: companion.foundation.reference_worker"],
                tests=plan["required_tests"],
            )
            transaction_id = manifest["transaction_id"]
            manager.begin(transaction_id)
            recovery_point = manager.snapshot_file(transaction_id, self.output_path)
            before_inventory = self._workspace_inventory()
            request_path = self.requests_dir / f"{transaction_id}.json"
            request = {
                "schema_version": HARNESS_SCHEMA_VERSION,
                "input_path": str(self.input_path),
                "output_path": str(self.output_path),
                "read_roots": card["allowed_read_roots"],
                "write_roots": card["allowed_write_roots"],
                "blocked_roots": card["blocked_roots"],
            }
            if fault_mode:
                request["fault_mode"] = fault_mode
                if fault_mode == "sleep":
                    request["fault_seconds"] = max(2, plan["timeout_seconds"] + 2)
            process_result: dict[str, Any] = {}
            try:
                atomic_write_json(request_path, request)
                process_result = self._execute_fixed_worker(
                    request_path,
                    request_hash=sha256_file(request_path),
                    timeout_seconds=plan["timeout_seconds"],
                )
                if process_result["timed_out"]:
                    raise HarnessError("worker_timeout", "reference worker exceeded its enforced timeout", details=process_result)
                if process_result["return_code"] != 0:
                    raise HarnessError("worker_failed", "reference worker exited with failure", details=process_result)
                after_inventory = self._workspace_inventory()
                effects = self._compare_effects(before_inventory, after_inventory)
                if effects["unexpected_created"] or effects["unexpected_changed"] or effects["unexpected_removed"]:
                    raise HarnessError("unexpected_file_effect", "worker changed files outside its exact declared output", details=effects)
                output = self._validate_output()
                test_results = self._run_declared_tests(card, output)
                if not all(result["passed"] for result in test_results):
                    raise HarnessError("declared_test_failed", "a declared reference-worker validation test failed", details={"tests": test_results})

                new_generation = self._bump_generation("successful worker execution")
                output_copy = self.candidate_outputs_dir / f"{candidate_id}.json"
                output_copy.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(self.output_path, output_copy)
                test_path = self.tests_dir / f"{candidate_id}.json"
                atomic_write_json(test_path, {"schema_version": HARNESS_SCHEMA_VERSION, "candidate_id": candidate_id, "tests": test_results})
                test_evidence_hash = sha256_file(test_path)
                output_hash = sha256_file(output_copy)
                run_result = {
                    "ok": True,
                    "candidate_id": candidate_id,
                    "plan_id": plan_id,
                    "plan_hash": plan["plan_hash"],
                    "output_hash": output_hash,
                    "test_evidence_hash": test_evidence_hash,
                    "workspace_generation": new_generation,
                    "effects": effects,
                    "capture": self._capture_summary(process_result),
                    "auto_activated": False,
                }
                committed = manager.commit(
                    transaction_id,
                    result=run_result,
                    after_paths=[self.output_path, output_copy, test_path, request_path],
                )
                receipt_paths = self._receipt_paths_for(manager, transaction_id)
                now = utc_now()
                record: dict[str, Any] = {
                    "schema_version": HARNESS_SCHEMA_VERSION,
                    "candidate_id": candidate_id,
                    "candidate_hash": "",
                    "lifecycle_state": "draft",
                    "worker_id": WORKER_ID,
                    "worker_version": WORKER_VERSION,
                    "worker_card_path": str(self.card_path),
                    "worker_card_hash": plan["worker_card_hash"],
                    "plan_id": plan_id,
                    "plan_path": str(self.plans_dir / f"{plan_id}.json"),
                    "plan_hash": plan["plan_hash"],
                    "transaction_id": transaction_id,
                    "transaction_manifest_path": str(manager.manifests_dir / f"{transaction_id}.json"),
                    "receipt_paths": receipt_paths,
                    "recovery_point": recovery_point,
                    "recovery_point_hash": hash_json(recovery_point),
                    "workspace_output_path": str(self.output_path),
                    "candidate_output_path": str(output_copy),
                    "output_hash": output_hash,
                    "output": output,
                    "test_results_path": str(test_path),
                    "test_results": test_results,
                    "test_evidence_hash": test_evidence_hash,
                    "workspace_generation": new_generation,
                    "file_effects": effects,
                    "capture": process_result,
                    "approval": None,
                    "activation": None,
                    "rollback": None,
                    "provenance_index": {"status": "complete", "derived": True},
                    "history": [],
                    "created_at": now,
                    "updated_at": now,
                }
                record["candidate_hash"] = calculate_candidate_hash(record)
                for state, reason in (
                    ("validated", "Worker Card and authority validated"),
                    ("execution_planned", "execution plan hash verified"),
                    ("executed", "fixed harmless worker completed"),
                    ("tests_passed", "declared validation tests passed"),
                    ("candidate", "bounded output recorded as candidate"),
                    ("awaiting_approval", "automatic activation prohibited"),
                ):
                    transition(record, state, actor=actor, reason=reason)
                self.candidates.save(record)
                try:
                    self._record_success_evidence(record, committed, test_path, output_copy)
                except Exception as provenance_error:
                    # The Compass is a derived/rebuildable index. A sync error
                    # must not retroactively turn a committed, tested candidate
                    # into a failed execution or restore its live output.
                    record["provenance_index"] = {
                        "status": "failed",
                        "derived": True,
                        "error_type": type(provenance_error).__name__,
                    }
                    self.candidates.save(record)
                return record
            except Exception as original_error:
                if isinstance(original_error, (HarnessError, PromotionError)):
                    exc = original_error
                else:
                    exc = HarnessError(
                        "harness_internal_failure",
                        "bounded worker execution failed before completion",
                        details={"error_type": type(original_error).__name__},
                    )
                recovery = self._restore_after_failure(manager, recovery_point, before_inventory)
                error_result = {
                    "ok": False,
                    "candidate_id": candidate_id,
                    "code": getattr(exc, "code", "promotion_error"),
                    "error": str(exc),
                    "details": getattr(exc, "details", {}),
                    "capture": process_result,
                    "automatic_recovery": recovery,
                }
                try:
                    receipt_error = {**error_result, "capture": self._capture_summary(process_result)}
                    manager.fail(transaction_id, result=receipt_error)
                except ValueError:
                    pass
                failure_path = self.runs_dir / f"{candidate_id}.json"
                atomic_write_json(failure_path, {"schema_version": HARNESS_SCHEMA_VERSION, "lifecycle_state": "failed", **error_result})
                self._record_evidence("failed-run", failure_path, "failed", transaction_id=transaction_id)
                raise HarnessError(error_result["code"], str(exc), details=error_result) from original_error

    def _run_artifact_inspection(
        self,
        *,
        plan: dict[str, Any],
        actor: str,
        fault_mode: str | None,
    ) -> dict[str, Any]:
        if not actor.strip():
            raise HarnessError("actor_required", "initiating actor is required")
        card = self._load_inspection_card()
        self._verify_inspection_plan_authority(plan, card)
        source = plan["selected_artifact"]
        source_path = Path(source["source_path"])
        candidate_id = uuid.uuid4().hex
        manager = TransactionManager(self.transactions_dir, actor=actor, path_policy=self._host_policy())
        permission_decision = {
            "allowed": True,
            "component": "artifact-compass-inspection-worker-v0.4",
            "application_enforced": plan["enforcement"],
            "host_enforced": {"timeout": True, "fixed_argv_no_shell": True, "bounded_capture": True},
            "unsupported": ["network", "unrestricted-shell", "destructive-actions", "artifact-code-execution", "hostile-process-isolation"],
            "execution_plan": plan,
        }
        plan_path = self.plans_dir / f"{plan['plan_id']}.json"
        manifest = manager.prepare(
            action="worker.artifact-inspection.execute",
            paths=[source_path, self.inspection_output_path, self.inspection_card_path, plan_path],
            permission_decision=permission_decision,
            commands=["fixed module: companion.foundation.artifact_inspection_worker"],
            tests=plan["required_tests"],
        )
        transaction_id = manifest["transaction_id"]
        manager.begin(transaction_id)
        recovery_point = manager.snapshot_file(transaction_id, self.inspection_output_path)
        before_inventory = self._workspace_inventory()
        source_hash_before = sha256_file(source_path)
        request_path = self.requests_dir / f"{transaction_id}.json"
        request: dict[str, Any] = {
            "schema_version": INSPECTION_SCHEMA_VERSION,
            "artifact": {
                "artifact_id": source["artifact_id"],
                "source_sha256": source["sha256"],
                "review_status": source["review_status"],
                "duplicate_hash_group": source["duplicate_hash_group"],
                "provenance_references": source["provenance_references"],
            },
            "input_path": str(source_path),
            "output_path": str(self.inspection_output_path),
            "read_roots": card["allowed_read_roots"],
            "write_roots": card["allowed_write_roots"],
            "blocked_roots": card["blocked_roots"],
            "max_input_bytes": INSPECTION_MAX_INPUT_BYTES,
            "max_output_bytes": INSPECTION_MAX_OUTPUT_BYTES,
            "inspection_timestamp": plan["created_at"],
        }
        if fault_mode:
            request["fault_mode"] = fault_mode
            if fault_mode == "sleep_after_read":
                request["fault_seconds"] = 1.0
        process_result: dict[str, Any] = {}
        try:
            atomic_write_json(request_path, request)
            process_result = self._execute_fixed_worker(
                request_path,
                request_hash=sha256_file(request_path),
                timeout_seconds=plan["timeout_seconds"],
                module_name="companion.foundation.artifact_inspection_worker",
            )
            source_hash_after = sha256_file(source_path)
            if source_hash_before != source["sha256"] or source_hash_after != source["sha256"]:
                raise HarnessError(
                    "source_changed_during_inspection",
                    "selected artifact changed during inspection",
                    details={"before": source_hash_before, "after": source_hash_after, "expected": source["sha256"]},
                )
            if process_result["timed_out"]:
                raise HarnessError("worker_timeout", "artifact inspection worker exceeded its enforced timeout", details=process_result)
            if process_result["return_code"] != 0:
                raise HarnessError("worker_failed", "artifact inspection worker exited with failure", details=process_result)
            after_inventory = self._workspace_inventory()
            effects = self._compare_effects(
                before_inventory,
                after_inventory,
                expected_output_path=self.inspection_output_path,
            )
            if effects["unexpected_created"] or effects["unexpected_changed"] or effects["unexpected_removed"]:
                raise HarnessError("unexpected_file_effect", "inspection worker changed files outside its exact declared output", details=effects)
            output = self._validate_inspection_output(plan)
            test_results = self._run_inspection_tests(request["artifact"], source_path, plan["created_at"], output)
            if not all(result["passed"] for result in test_results):
                raise HarnessError("declared_test_failed", "artifact inspection output failed deterministic validation", details={"tests": test_results})

            new_generation = self._bump_generation("successful artifact inspection execution")
            output_copy = self.candidate_outputs_dir / f"{candidate_id}.json"
            output_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.inspection_output_path, output_copy)
            test_path = self.tests_dir / f"{candidate_id}.json"
            atomic_write_json(
                test_path,
                {"schema_version": INSPECTION_SCHEMA_VERSION, "candidate_id": candidate_id, "tests": test_results},
            )
            test_evidence_hash = sha256_file(test_path)
            output_hash = sha256_file(output_copy)
            run_result = {
                "ok": True,
                "candidate_id": candidate_id,
                "plan_id": plan["plan_id"],
                "plan_hash": plan["plan_hash"],
                "source_artifact_id": source["artifact_id"],
                "source_artifact_hash": source["sha256"],
                "source_artifact_unchanged": True,
                "output_hash": output_hash,
                "test_evidence_hash": test_evidence_hash,
                "workspace_generation": new_generation,
                "effects": effects,
                "capture": self._capture_summary(process_result),
                "auto_activated": False,
            }
            committed = manager.commit(
                transaction_id,
                result=run_result,
                after_paths=[self.inspection_output_path, output_copy, test_path, request_path, source_path],
            )
            receipt_paths = self._receipt_paths_for(manager, transaction_id)
            now = utc_now()
            record: dict[str, Any] = {
                "schema_version": INSPECTION_SCHEMA_VERSION,
                "candidate_id": candidate_id,
                "candidate_hash": "",
                "lifecycle_state": "draft",
                "worker_id": INSPECTION_WORKER_ID,
                "worker_version": INSPECTION_WORKER_VERSION,
                "worker_card_path": str(self.inspection_card_path),
                "worker_card_hash": plan["worker_card_hash"],
                "plan_id": plan["plan_id"],
                "plan_path": str(plan_path),
                "plan_hash": plan["plan_hash"],
                "transaction_id": transaction_id,
                "transaction_manifest_path": str(manager.manifests_dir / f"{transaction_id}.json"),
                "receipt_paths": receipt_paths,
                "recovery_point": recovery_point,
                "recovery_point_hash": hash_json(recovery_point),
                "workspace_output_path": str(self.inspection_output_path),
                "candidate_output_path": str(output_copy),
                "output_hash": output_hash,
                "output": output,
                "test_results_path": str(test_path),
                "test_results": test_results,
                "test_evidence_hash": test_evidence_hash,
                "workspace_generation": new_generation,
                "file_effects": effects,
                "capture": process_result,
                "source_artifact": {
                    "artifact_id": source["artifact_id"],
                    "project_id": source["project_id"],
                    "source_path": source["source_path"],
                    "sha256": source["sha256"],
                    "file_type": source["file_type"],
                    "review_status": source["review_status"],
                },
                "approval_binding": {
                    "candidate_hash": None,
                    "source_artifact_hash": source["sha256"],
                    "worker_card_hash": plan["worker_card_hash"],
                    "execution_plan_hash": plan["plan_hash"],
                    "workspace_generation": new_generation,
                },
                "approval": None,
                "activation": None,
                "rollback": None,
                "provenance_index": {"status": "complete", "derived": True},
                "history": [],
                "created_at": now,
                "updated_at": now,
            }
            record["candidate_hash"] = calculate_candidate_hash(record)
            record["approval_binding"]["candidate_hash"] = record["candidate_hash"]
            for state, reason in (
                ("validated", "Artifact Inspection Worker Card and read-only authority validated"),
                ("execution_planned", "execution plan and selected source hash verified"),
                ("executed", "fixed read-only artifact inspection worker completed"),
                ("tests_passed", "deterministic output and source immutability tests passed"),
                ("candidate", "structured inspection output recorded as candidate"),
                ("awaiting_approval", "candidate is not attached automatically"),
            ):
                transition(record, state, actor=actor, reason=reason)
            self.candidates.save(record)
            try:
                self._record_success_evidence(record, committed, test_path, output_copy)
                self._record_evidence(
                    "source-artifact-reference",
                    source_path,
                    "inspected_read_only",
                    candidate_id=candidate_id,
                    artifact_id=source["artifact_id"],
                    source_hash=source["sha256"],
                )
            except Exception as provenance_error:
                record["provenance_index"] = {
                    "status": "failed",
                    "derived": True,
                    "error_type": type(provenance_error).__name__,
                }
                self.candidates.save(record)
            return record
        except Exception as original_error:
            if isinstance(original_error, (HarnessError, PromotionError)):
                exc = original_error
            else:
                exc = HarnessError(
                    "harness_internal_failure",
                    "bounded artifact inspection failed before completion",
                    details={"error_type": type(original_error).__name__},
                )
            recovery = self._restore_after_failure(
                manager,
                recovery_point,
                before_inventory,
                output_dir=self.inspection_output_dir,
                output_path=self.inspection_output_path,
            )
            error_result = {
                "ok": False,
                "candidate_id": candidate_id,
                "code": getattr(exc, "code", "promotion_error"),
                "error": str(exc),
                "details": getattr(exc, "details", {}),
                "capture": process_result,
                "automatic_recovery": recovery,
            }
            try:
                manager.fail(
                    transaction_id,
                    result={**error_result, "capture": self._capture_summary(process_result)},
                )
            except ValueError:
                pass
            failure_path = self.runs_dir / f"{candidate_id}.json"
            atomic_write_json(
                failure_path,
                {"schema_version": INSPECTION_SCHEMA_VERSION, "lifecycle_state": "failed", **error_result},
            )
            self._record_evidence(
                "failed-run",
                failure_path,
                "failed",
                transaction_id=transaction_id,
                artifact_id=source["artifact_id"],
            )
            raise HarnessError(error_result["code"], str(exc), details=error_result) from original_error

    def approve(self, candidate_id: str, approval: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = self._verify_promotion_context(candidate_id, approval, expected_states={"awaiting_approval"})
            decision = approval.get("decision")
            if decision not in {"approve", "reject"}:
                raise PromotionError("approval_decision_invalid", "approval decision must be approve or reject")
            actor = self._validate_actor(approval.get("actor"))
            timestamp = validate_timestamp(approval.get("timestamp"))
            note = str(approval.get("note", ""))
            if decision == "approve" and not note.strip():
                raise PromotionError("approval_note_required", "an explicit approval note is required")
            if len(note) > 1000:
                raise PromotionError("approval_note_too_long", "approval note must not exceed 1000 characters")
            decision_record = {
                "schema_version": HARNESS_SCHEMA_VERSION,
                "candidate_id": candidate_id,
                "candidate_hash": record["candidate_hash"],
                "workspace_generation": record["workspace_generation"],
                "human_actor_assertion": actor,
                "decision": decision,
                "note": note,
                "timestamp": timestamp,
                "identity_authenticated": False,
            }
            if isinstance(record.get("source_artifact"), dict):
                decision_record["source_artifact_hash"] = record["source_artifact"]["sha256"]
                decision_record["worker_card_hash"] = record["worker_card_hash"]
                decision_record["execution_plan_hash"] = record["plan_hash"]
            receipt_decision = self._approval_receipt_evidence(decision_record)
            decision_path = self.decisions_dir / f"{candidate_id}-{decision}.json"
            manager = TransactionManager(self.transactions_dir, actor=actor, path_policy=self._host_policy())
            manifest = manager.prepare(
                action=f"candidate.{decision}",
                paths=[self.candidates_dir / f"{candidate_id}.json", Path(record["worker_card_path"]), Path(record["candidate_output_path"])],
                permission_decision={"allowed": True, "component": "guarded-promotion-v0.1", "candidate_hash_bound": True, "workspace_generation_bound": True},
                commands=[],
                tests=["candidate-integrity", "receipt-chain", "recovery-point", "worker-card-hash"],
                approval=receipt_decision,
            )
            manager.begin(manifest["transaction_id"])
            atomic_write_json(decision_path, decision_record)
            target = "approved" if decision == "approve" else "rejected"
            transition(record, target, actor=actor, reason=f"explicit human {decision} decision")
            record["approval"] = {**decision_record, "decision_record_path": str(decision_path), "transaction_id": manifest["transaction_id"]}
            self.candidates.save(record)
            manager.commit(manifest["transaction_id"], result={"ok": True, "decision": receipt_decision}, after_paths=[decision_path, self.candidates_dir / f"{candidate_id}.json"])
            record["receipt_paths"] = sorted(set(record["receipt_paths"] + self._receipt_paths_for(manager, manifest["transaction_id"])))
            self.candidates.save(record)
            self._record_evidence("approval-decision", decision_path, target, candidate_id=candidate_id, transaction_id=manifest["transaction_id"])
            self._record_transaction_evidence(manager, manifest["transaction_id"], target, candidate_id)
            self._record_evidence("candidate-record", self.candidates_dir / f"{candidate_id}.json", target, candidate_id=candidate_id)
            return record

    def activate(
        self,
        candidate_id: str,
        context: dict[str, Any],
        *,
        interrupt_registry_write: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            record = self._verify_promotion_context(candidate_id, context, expected_states={"approved"})
            actor = self._validate_actor(context.get("actor"))
            timestamp = validate_timestamp(context.get("timestamp"))
            activation_path = self.activations_dir / f"{candidate_id}.json"
            manager = TransactionManager(self.transactions_dir, actor=actor, path_policy=self._host_policy())
            manifest = manager.prepare(
                action="candidate.activate",
                paths=[self.candidates_dir / f"{candidate_id}.json", self.registry.path],
                permission_decision={
                    "allowed": True,
                    "component": "activation-registry-v0.1",
                    "executes_code": False,
                    "grants_permissions": False,
                    "attaches_read_only_report": isinstance(record.get("source_artifact"), dict),
                },
                commands=[],
                tests=["candidate-approved", "candidate-hash", "workspace-generation", "receipt-chain", "recovery-point"],
                approval=self._approval_receipt_evidence(record["approval"]),
            )
            manager.begin(manifest["transaction_id"])
            try:
                entry = self.registry.activate(
                    record,
                    actor=actor,
                    timestamp=timestamp,
                    activation_record_path=str(activation_path),
                    interrupt_before_replace=interrupt_registry_write,
                )
                activation_record = {
                    "schema_version": HARNESS_SCHEMA_VERSION,
                    "candidate_id": candidate_id,
                    "candidate_hash": record["candidate_hash"],
                    "workspace_generation": record["workspace_generation"],
                    "actor": actor,
                    "timestamp": timestamp,
                    "registry_entry": entry,
                    "executes_on_startup": False,
                    "grants_permissions": False,
                }
                if isinstance(record.get("source_artifact"), dict):
                    activation_record["artifact_attachment"] = entry["artifact_attachment"]
                atomic_write_json(activation_path, activation_record)
                transition(record, "active", actor=actor, reason="registered after separate explicit activation action")
                record["activation"] = {**activation_record, "transaction_id": manifest["transaction_id"], "activation_record_path": str(activation_path)}
                self.candidates.save(record)
                manager.commit(manifest["transaction_id"], result={"ok": True, "activation": activation_record}, after_paths=[self.registry.path, activation_path, self.candidates_dir / f"{candidate_id}.json"])
            except PromotionError as exc:
                manager.fail(manifest["transaction_id"], result={"ok": False, "code": exc.code, "error": str(exc)})
                raise
            record["receipt_paths"] = sorted(set(record["receipt_paths"] + self._receipt_paths_for(manager, manifest["transaction_id"])))
            self.candidates.save(record)
            self._record_evidence("activation-record", activation_path, "active", candidate_id=candidate_id, transaction_id=manifest["transaction_id"])
            if isinstance(record.get("source_artifact"), dict):
                self._record_evidence(
                    "artifact-inspection-attachment",
                    activation_path,
                    "active",
                    candidate_id=candidate_id,
                    transaction_id=manifest["transaction_id"],
                    artifact_id=record["source_artifact"]["artifact_id"],
                    source_hash=record["source_artifact"]["sha256"],
                )
            self._record_transaction_evidence(manager, manifest["transaction_id"], "active", candidate_id)
            self._record_evidence("candidate-record", self.candidates_dir / f"{candidate_id}.json", "active", candidate_id=candidate_id)
            return record

    def rollback(self, candidate_id: str, context: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            record = self._verify_promotion_context(candidate_id, context, expected_states={"active"})
            actor = self._validate_actor(context.get("actor"))
            timestamp = validate_timestamp(context.get("timestamp"))
            if sha256_file(record["workspace_output_path"]) != record["output_hash"]:
                raise PromotionError("rollback_current_hash_mismatch", "current bounded output no longer matches the activated candidate")
            recovery_point = record["recovery_point"]
            self._verify_recovery_point(record)
            rollback_path = self.rollbacks_dir / f"{candidate_id}.json"
            manager = TransactionManager(self.transactions_dir, actor=actor, path_policy=self._host_policy())
            manifest = manager.prepare(
                action="candidate.rollback",
                paths=[record["workspace_output_path"], self.registry.path, self.candidates_dir / f"{candidate_id}.json"],
                permission_decision={"allowed": True, "component": "bounded-rollback-v0.1", "scope": "one output file and one registry entry"},
                commands=[],
                tests=["current-output-hash", "recovery-snapshot-hash", "restored-output-hash"],
                approval={"actor": actor, "timestamp": timestamp, "candidate_hash": record["candidate_hash"]},
            )
            manager.begin(manifest["transaction_id"])
            manager.snapshot_file(manifest["transaction_id"], record["workspace_output_path"])
            restored_hash = manager.restore_file_snapshot(recovery_point, record["workspace_output_path"], replace_existing=True)
            if restored_hash != recovery_point["sha256"]:
                manager.fail(manifest["transaction_id"], result={"ok": False, "code": "rollback_verification_failed"})
                raise PromotionError("rollback_verification_failed", "restored output hash does not match the recovery point")
            rollback_record = {
                "schema_version": HARNESS_SCHEMA_VERSION,
                "candidate_id": candidate_id,
                "candidate_hash": record["candidate_hash"],
                "actor": actor,
                "timestamp": timestamp,
                "restored_path": record["workspace_output_path"],
                "restored_sha256": restored_hash,
                "expected_sha256": recovery_point["sha256"],
                "scope": (
                    "one bounded output file and artifact inspection attachment registry status"
                    if isinstance(record.get("source_artifact"), dict)
                    else "one bounded output file and activation registry status"
                ),
            }
            atomic_write_json(rollback_path, rollback_record)
            self.registry.mark_rolled_back(candidate_id, rollback_record_path=str(rollback_path), timestamp=timestamp)
            transition(record, "rolled_back", actor=actor, reason="owner-selected bounded rollback verified by hash")
            record["rollback"] = {**rollback_record, "transaction_id": manifest["transaction_id"], "rollback_record_path": str(rollback_path)}
            self._bump_generation("bounded rollback")
            self.candidates.save(record)
            manager.commit(manifest["transaction_id"], result={"ok": True, "rollback": rollback_record}, after_paths=[record["workspace_output_path"], self.registry.path, rollback_path, self.candidates_dir / f"{candidate_id}.json"])
            record["receipt_paths"] = sorted(set(record["receipt_paths"] + self._receipt_paths_for(manager, manifest["transaction_id"])))
            self.candidates.save(record)
            self._record_evidence("rollback-record", rollback_path, "rolled_back", candidate_id=candidate_id, transaction_id=manifest["transaction_id"])
            self._record_transaction_evidence(manager, manifest["transaction_id"], "rolled_back", candidate_id)
            self._record_evidence("candidate-record", self.candidates_dir / f"{candidate_id}.json", "rolled_back", candidate_id=candidate_id)
            return record

    def list_candidates(self) -> list[dict[str, Any]]:
        with self._lock:
            return self.candidates.list()

    def get_candidate(self, candidate_id: str) -> dict[str, Any]:
        with self._lock:
            return self.candidates.load(candidate_id)

    def artifact_inspections(self, artifact_id: str) -> list[dict[str, Any]]:
        if not isinstance(artifact_id, str) or not artifact_id.strip() or len(artifact_id) > 200:
            raise HarnessError("artifact_id_invalid", "artifact ID is invalid")
        with self._lock:
            registry = self.registry.load()
            reports: list[dict[str, Any]] = []
            for entry in registry.get("entries", []):
                attachment = entry.get("artifact_attachment")
                if not isinstance(attachment, dict) or attachment.get("artifact_id") != artifact_id:
                    continue
                candidate = self.candidates.load(entry["candidate_id"])
                report_path = Path(candidate["candidate_output_path"])
                report_valid = report_path.is_file() and sha256_file(report_path) == candidate["output_hash"]
                reports.append(
                    {
                        "artifact_id": artifact_id,
                        "candidate_id": candidate["candidate_id"],
                        "candidate_hash": candidate["candidate_hash"],
                        "lifecycle_state": candidate["lifecycle_state"],
                        "attachment_status": entry.get("status"),
                        "source_sha256": candidate["source_artifact"]["sha256"],
                        "report_sha256": candidate["output_hash"],
                        "report_valid": report_valid,
                        "report": candidate["output"] if report_valid else None,
                        "activation": candidate.get("activation"),
                        "rollback": candidate.get("rollback"),
                    }
                )
            return sorted(reports, key=lambda item: (item["attachment_status"], item["candidate_id"]))

    def verify_receipts(self) -> dict[str, Any]:
        self._ensure_workspace()
        verification = TransactionManager(self.transactions_dir, actor="receipt-auditor", path_policy=self._host_policy()).verify_receipt_chain()
        return {"valid": verification.valid, "receipt_count": verification.receipt_count, "errors": list(verification.errors)}

    def current_generation(self) -> int:
        self._ensure_workspace()
        return int(self._load_state()["generation"])

    def _expected_card(self) -> dict[str, Any]:
        implementation = Path(__file__).with_name("reference_worker.py")
        implementation_hash = sha256_file(implementation) if implementation.exists() else "0" * 64
        return {
            "schema_version": "0.1",
            "worker_id": WORKER_ID,
            "version": WORKER_VERSION,
            "lifecycle_status": "test",
            "purpose": "Read one harmless text fixture and write deterministic metadata JSON in a bounded workspace.",
            "accepted_input_types": ["text/markdown", "text/plain"],
            "produced_output_types": ["application/json"],
            "allowed_read_roots": [str(self.input_dir)],
            "allowed_write_roots": [str(self.output_dir)],
            "blocked_roots": self.protected_roots,
            "network_allowed": False,
            "shell_allowed": False,
            "destructive_actions_allowed": False,
            "approval_required": True,
            # Process startup on Windows can be delayed by filesystem and
            # antivirus scanning. Five seconds remains a strict bound while
            # avoiding false timeouts for this tiny fixed module.
            "timeout_seconds": 5,
            "test_commands": [SUPPORTED_TEST_ID],
            "failure_policy": {"on_validation_error": "reject", "on_runtime_error": "fail_closed", "retry_count": 0},
            "receipt_required": True,
            "source_provenance": {
                "kind": "human-authored",
                "source": "companion/foundation/reference_worker.py",
                "sha256": implementation_hash,
            },
        }

    def _expected_inspection_card(self) -> dict[str, Any]:
        implementation = Path(__file__).with_name("artifact_inspection_worker.py")
        implementation_hash = sha256_file(implementation) if implementation.exists() else "0" * 64
        return {
            "schema_version": "0.1",
            "worker_id": INSPECTION_WORKER_ID,
            "version": INSPECTION_WORKER_VERSION,
            "lifecycle_status": "active",
            "purpose": "Read one explicitly selected public-safe text artifact and produce one deterministic structured inspection candidate without modifying the artifact.",
            "accepted_input_types": sorted(set(INSPECTION_FILE_TYPES.values())),
            "produced_output_types": ["application/json"],
            "allowed_read_roots": self.public_artifact_roots,
            "allowed_write_roots": [str(self.inspection_output_dir)],
            "blocked_roots": self.protected_roots,
            "network_allowed": False,
            "shell_allowed": False,
            "destructive_actions_allowed": False,
            "approval_required": True,
            "timeout_seconds": 5,
            "test_commands": [INSPECTION_TEST_ID],
            "failure_policy": {"on_validation_error": "reject", "on_runtime_error": "fail_closed", "retry_count": 0},
            "receipt_required": True,
            "source_provenance": {
                "kind": "human-authored",
                "source": "companion/foundation/artifact_inspection_worker.py",
                "sha256": implementation_hash,
            },
        }

    def _ensure_inspection_workspace(self) -> None:
        self._ensure_workspace()
        self.inspection_output_dir.mkdir(parents=True, exist_ok=True)
        if not self.inspection_output_path.exists():
            atomic_write_json(
                self.inspection_output_path,
                {"schema_version": INSPECTION_SCHEMA_VERSION, "state": "not-run"},
            )
        if not self.inspection_card_path.exists():
            atomic_write_json(self.inspection_card_path, self._expected_inspection_card())

    def _load_inspection_card(self) -> dict[str, Any]:
        self._ensure_inspection_workspace()
        return _safe_read_json(self.inspection_card_path, code="worker_card_malformed")

    def _ensure_workspace(self) -> None:
        # Refuse reparse-point/root substitution before any initialization write.
        # The anchors are captured when the harness instance is constructed and
        # are also bound into each execution plan below.
        self._verify_canonical_anchors()
        for directory in (
            self.input_dir,
            self.output_dir,
            self.cards_dir,
            self.plans_dir,
            self.requests_dir,
            self.candidates_dir,
            self.candidate_outputs_dir,
            self.tests_dir,
            self.runs_dir,
            self.decisions_dir,
            self.activations_dir,
            self.rollbacks_dir,
            self.transactions_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)
        if not self.fixture_source.is_file():
            raise HarnessError("fixture_missing", "harmless reference fixture is missing")
        if not self.input_path.exists():
            shutil.copy2(self.fixture_source, self.input_path)
        if not self.output_path.exists():
            atomic_write_json(self.output_path, {"schema_version": HARNESS_SCHEMA_VERSION, "state": "not-run"})
        if not self.state_path.exists():
            atomic_write_json(self.state_path, {"schema_version": HARNESS_SCHEMA_VERSION, "generation": 0, "updated_at": utc_now()})
        if not self.card_path.exists():
            atomic_write_json(self.card_path, self._expected_card())

    def _load_fixed_card(self) -> dict[str, Any]:
        self._ensure_workspace()
        return _safe_read_json(self.card_path, code="worker_card_malformed")

    def _verify_canonical_anchors(self) -> None:
        current = {
            "root": str(self.root.resolve(strict=False)),
            "workspace": str(self.workspace.resolve(strict=False)),
            "input": str(self.input_dir.resolve(strict=False)),
            "output": str(self.output_dir.resolve(strict=False)),
            "inspection_output": str(self.inspection_output_dir.resolve(strict=False)),
        }
        for index, public_root in enumerate(self.public_artifact_roots):
            current[f"public_artifact_{index}"] = str(Path(public_root).resolve(strict=False))
        changed = {
            name: {"planned": self._canonical_anchors[name], "current": value}
            for name, value in current.items()
            if value != self._canonical_anchors[name]
        }
        if changed:
            raise HarnessError(
                "canonical_root_changed",
                "a harness root changed after initialization",
                details={"changed_roots": changed},
            )

    def _evaluate_permissions(self, card: dict[str, Any]) -> dict[str, Any]:
        denied: list[str] = []
        if card.get("network_allowed"):
            denied.append("network access is unsupported in Worker Harness v0.1")
        if card.get("shell_allowed"):
            denied.append("unrestricted shell access is unsupported")
        if card.get("destructive_actions_allowed"):
            denied.append("destructive actions are unsupported")
        if card.get("test_commands") != [SUPPORTED_TEST_ID]:
            denied.append("declared tests must use the single internal allowlisted test ID")
        expected = self._expected_card()
        for field in ("allowed_read_roots", "allowed_write_roots", "blocked_roots"):
            if [str(Path(path).resolve(strict=False)) for path in card.get(field, [])] != [str(Path(path).resolve(strict=False)) for path in expected[field]]:
                denied.append(f"{field} differs from the fixed reference-worker authority")
        return {
            "allowed": not denied,
            "denied_reasons": denied,
            "application_enforced": ["Worker Card validation", "path policy", "fixed worker ID", "fixed internal test ID", "file-effect validation", "hash/generation approval"],
            "host_enforced": ["fixed argv without shell", "child process timeout", "bounded stdout/stderr capture"],
            "declared_only": ["human actor string; identity is not authenticated"],
            "unsupported": ["network", "unrestricted shell", "destructive actions", "arbitrary code", "hostile-process isolation", "complete sandboxing"],
        }

    def _evaluate_inspection_permissions(self, card: dict[str, Any]) -> dict[str, Any]:
        denied: list[str] = []
        if card.get("network_allowed"):
            denied.append("network access is unsupported")
        if card.get("shell_allowed"):
            denied.append("unrestricted shell access is unsupported")
        if card.get("destructive_actions_allowed"):
            denied.append("destructive actions are unsupported")
        if card.get("approval_required") is not True:
            denied.append("explicit approval is required")
        if card.get("receipt_required") is not True:
            denied.append("a receipt is required")
        if card.get("test_commands") != [INSPECTION_TEST_ID]:
            denied.append("declared tests must use the fixed artifact inspection test ID")
        expected = self._expected_inspection_card()
        for field in ("allowed_read_roots", "allowed_write_roots", "blocked_roots"):
            supplied_roots = [str(Path(path).resolve(strict=False)) for path in card.get(field, [])]
            expected_roots = [str(Path(path).resolve(strict=False)) for path in expected[field]]
            if supplied_roots != expected_roots:
                denied.append(f"{field} differs from the fixed artifact-inspection authority")
        return {
            "allowed": not denied,
            "denied_reasons": denied,
            "application_enforced": [
                "Worker Card validation",
                "explicit artifact selection",
                "public-root and blocked-root path policy",
                "source hash before and after reading",
                "fixed worker ID and test ID",
                "file-effect and output-schema validation",
                "hash/generation/source approval binding",
            ],
            "host_enforced": ["fixed argv without shell", "child process timeout", "bounded stdout/stderr capture"],
            "declared_only": ["human actor string; identity is not authenticated", "network denial is not an OS firewall"],
            "unsupported": ["network", "unrestricted shell", "destructive actions", "arbitrary workers", "artifact code execution", "hostile-process isolation", "complete sandboxing"],
        }

    def _load_state(self) -> dict[str, Any]:
        state = _safe_read_json(self.state_path, code="workspace_state_invalid")
        if state.get("schema_version") != HARNESS_SCHEMA_VERSION or type(state.get("generation")) is not int:
            raise HarnessError("workspace_state_invalid", "workspace state schema is invalid")
        return state

    def _bump_generation(self, reason: str) -> int:
        state = self._load_state()
        state["generation"] += 1
        state["updated_at"] = utc_now()
        state["reason"] = reason
        atomic_write_json(self.state_path, state)
        return state["generation"]

    def _load_plan(self, plan_id: str) -> dict[str, Any]:
        if len(plan_id) != 32 or any(character not in "0123456789abcdef" for character in plan_id):
            raise HarnessError("plan_id_invalid", "plan ID is invalid")
        path = self.plans_dir / f"{plan_id}.json"
        if not path.is_file():
            raise HarnessError("plan_not_found", "execution plan does not exist")
        plan = _safe_read_json(path, code="plan_malformed")
        claimed = plan.pop("plan_hash", None)
        calculated = hash_json(plan)
        plan["plan_hash"] = claimed
        if claimed != calculated:
            raise HarnessError("plan_hash_mismatch", "execution plan changed after planning")
        return plan

    def _verify_plan_authority(self, plan: dict[str, Any], card: dict[str, Any]) -> None:
        if plan.get("worker_id") != WORKER_ID or plan.get("worker_version") != WORKER_VERSION:
            raise HarnessError("plan_worker_unsupported", "execution plan targets an unsupported worker")
        if plan.get("worker_card_hash") != hash_json(card):
            raise HarnessError("worker_card_changed", "Worker Card changed after planning")
        current_read_roots = [str(Path(path).resolve(strict=False)) for path in card["allowed_read_roots"]]
        current_write_roots = [str(Path(path).resolve(strict=False)) for path in card["allowed_write_roots"]]
        current_blocked_roots = [str(Path(path).resolve(strict=False)) for path in card["blocked_roots"]]
        if current_read_roots != plan.get("canonical_read_roots") or current_write_roots != plan.get("canonical_write_roots") or current_blocked_roots != plan.get("blocked_roots"):
            raise HarnessError("canonical_root_changed", "a canonical read, write, or blocked root changed after planning")
        if plan.get("workspace_generation") != self._load_state()["generation"]:
            raise HarnessError("plan_generation_stale", "workspace generation changed after planning")
        if plan.get("inputs", [{}])[0].get("sha256") != sha256_file(self.input_path):
            raise HarnessError("input_changed", "reference input changed after planning")
        enforcement = self._evaluate_permissions(card)
        if not enforcement["allowed"] or not plan.get("enforcement", {}).get("allowed"):
            raise HarnessError("authority_denied", "execution plan contains denied or ambiguous authority", details=enforcement)
        worker_policy = WindowsPathPolicy(
            read_roots=card["allowed_read_roots"],
            write_roots=card["allowed_write_roots"],
            blocked_roots=card["blocked_roots"],
        )
        worker_policy.decide(self.input_path, mode="read").require_allowed()
        worker_policy.decide(self.output_path, mode="write").require_allowed()

    def _verify_inspection_plan_authority(self, plan: dict[str, Any], card: dict[str, Any]) -> None:
        if plan.get("schema_version") != INSPECTION_SCHEMA_VERSION:
            raise HarnessError("plan_schema_unsupported", "artifact inspection plan schema is unsupported")
        if plan.get("worker_id") != INSPECTION_WORKER_ID or plan.get("worker_version") != INSPECTION_WORKER_VERSION:
            raise HarnessError("plan_worker_unsupported", "execution plan targets an unsupported worker")
        if plan.get("worker_card_hash") != hash_json(card):
            raise HarnessError("worker_card_changed", "Artifact Inspection Worker Card changed after planning")
        current_read_roots = [str(Path(path).resolve(strict=False)) for path in card["allowed_read_roots"]]
        current_write_roots = [str(Path(path).resolve(strict=False)) for path in card["allowed_write_roots"]]
        current_blocked_roots = [str(Path(path).resolve(strict=False)) for path in card["blocked_roots"]]
        if (
            current_read_roots != plan.get("canonical_read_roots")
            or current_write_roots != plan.get("canonical_write_roots")
            or current_blocked_roots != plan.get("blocked_roots")
        ):
            raise HarnessError("canonical_root_changed", "a canonical public read, candidate write, or blocked root changed after planning")
        if plan.get("workspace_generation") != self._load_state()["generation"]:
            raise HarnessError("plan_generation_stale", "workspace generation changed after planning")
        selected = plan.get("selected_artifact")
        if not isinstance(selected, dict):
            raise HarnessError("artifact_selection_invalid", "execution plan is missing its selected artifact")
        source_path = Path(str(selected.get("source_path", "")))
        if source_path.suffix.lower() not in INSPECTION_EXTENSIONS:
            raise HarnessError("artifact_extension_unsupported", "selected artifact extension is not supported")
        policy = WindowsPathPolicy(
            read_roots=card["allowed_read_roots"],
            write_roots=card["allowed_write_roots"],
            blocked_roots=card["blocked_roots"],
        )
        decision = policy.decide(source_path, mode="read")
        try:
            resolved_source = decision.require_allowed()
        except PermissionError as exc:
            raise HarnessError(
                "artifact_path_denied",
                "selected artifact is no longer inside an approved public-safe root",
                details={"code": decision.code, "reason": decision.reason},
            ) from exc
        resolved_output = policy.decide(self.inspection_output_path, mode="write").require_allowed()
        if str(resolved_output) != str(self.inspection_output_path.resolve(strict=False)):
            raise HarnessError("output_path_changed", "inspection output path changed after planning")
        if decision.matched_root != plan.get("requested_read_root") or decision.matched_root != selected.get("public_read_root"):
            raise HarnessError("requested_read_root_changed", "selected artifact public read root changed after planning")
        expected_hash = selected.get("sha256")
        if not isinstance(expected_hash, str) or sha256_file(resolved_source) != expected_hash:
            raise HarnessError("source_changed_before_inspection", "selected artifact hash changed after planning")
        if resolved_source.stat().st_size != selected.get("byte_count"):
            raise HarnessError("source_changed_before_inspection", "selected artifact size changed after planning")
        inputs = plan.get("inputs")
        if not isinstance(inputs, list) or len(inputs) != 1:
            raise HarnessError("plan_input_invalid", "artifact inspection plan must contain exactly one input")
        planned_input = inputs[0]
        if (
            planned_input.get("artifact_id") != selected.get("artifact_id")
            or planned_input.get("path") != str(resolved_source)
            or planned_input.get("sha256") != expected_hash
            or planned_input.get("size_bytes") != selected.get("byte_count")
            or planned_input.get("file_type") != selected.get("file_type")
        ):
            raise HarnessError("plan_input_changed", "selected artifact fields differ from the exact planned input")
        enforcement = self._evaluate_inspection_permissions(card)
        if not enforcement["allowed"] or not plan.get("enforcement", {}).get("allowed"):
            raise HarnessError("authority_denied", "execution plan contains denied or ambiguous inspection authority", details=enforcement)
        if (
            plan.get("max_input_bytes") != INSPECTION_MAX_INPUT_BYTES
            or plan.get("max_output_bytes") != INSPECTION_MAX_OUTPUT_BYTES
            or plan.get("required_tests") != [INSPECTION_TEST_ID]
            or plan.get("auto_activate") is not False
        ):
            raise HarnessError("plan_limits_changed", "inspection plan limits, tests, or activation policy changed")

    def _host_policy(self) -> WindowsPathPolicy:
        return WindowsPathPolicy(
            read_roots=[self.root, *self.public_artifact_roots],
            write_roots=[self.root],
            blocked_roots=self.protected_roots,
        )

    def _worker_environment(self) -> dict[str, str]:
        environment = {
            key: os.environ[key]
            for key in ("SYSTEMROOT", "WINDIR", "PATH", "PATHEXT", "TEMP", "TMP")
            if key in os.environ
        }
        environment.update(
            {
                "PYTHONPATH": str(self.runtime_root),
                "PYTHONNOUSERSITE": "1",
                "PYTHONSAFEPATH": "1",
                "PYTHONIOENCODING": "utf-8",
            }
        )
        return environment

    def _execute_fixed_worker(
        self,
        request_path: Path,
        *,
        request_hash: str,
        timeout_seconds: int,
        module_name: str = "companion.foundation.reference_worker",
    ) -> dict[str, Any]:
        command = [
            sys.executable,
            "-m",
            module_name,
            "--request",
            str(request_path),
            "--request-sha256",
            request_hash,
        ]
        environment = self._worker_environment()
        process = subprocess.Popen(
            command,
            cwd=self.runtime_root,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
        capture: dict[str, Any] = {}
        stdout_thread = threading.Thread(target=_bounded_pipe_reader, args=(process.stdout, MAX_CAPTURE_BYTES, capture, "stdout"), daemon=True)
        stderr_thread = threading.Thread(target=_bounded_pipe_reader, args=(process.stderr, MAX_CAPTURE_BYTES, capture, "stderr"), daemon=True)
        stdout_thread.start()
        stderr_thread.start()
        timed_out = False
        try:
            return_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            process.terminate()
            try:
                return_code = process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                return_code = process.wait(timeout=2)
        stdout_thread.join(timeout=2)
        stderr_thread.join(timeout=2)
        return {"return_code": return_code, "timed_out": timed_out, **capture}

    def _workspace_inventory(self) -> dict[str, str]:
        inventory: dict[str, str] = {}
        for root in (self.input_dir, self.output_dir, self.inspection_output_dir):
            for path in sorted(root.rglob("*")):
                if path.is_file():
                    inventory[str(path.resolve(strict=False))] = sha256_file(path)
        return inventory

    def _compare_effects(
        self,
        before: dict[str, str],
        after: dict[str, str],
        *,
        expected_output_path: Path | None = None,
    ) -> dict[str, Any]:
        expected_output = str((expected_output_path or self.output_path).resolve(strict=False))
        created = sorted(set(after) - set(before))
        removed = sorted(set(before) - set(after))
        changed = sorted(path for path in set(before) & set(after) if before[path] != after[path])
        return {
            "created": created,
            "changed": changed,
            "removed": removed,
            "unexpected_created": [path for path in created if path != expected_output],
            "unexpected_changed": [path for path in changed if path != expected_output],
            "unexpected_removed": removed,
            "expected_output_changed": expected_output in changed or expected_output in created,
            "before_hashes": before,
            "after_hashes": after,
        }

    def _validate_output(self) -> dict[str, Any]:
        if not self.output_path.is_file():
            raise HarnessError("output_missing", "reference worker did not create its declared output")
        size = self.output_path.stat().st_size
        if size > MAX_OUTPUT_BYTES:
            raise HarnessError("output_oversized", "reference worker output exceeds 32 KiB", details={"size_bytes": size})
        output = _safe_read_json(self.output_path, code="output_malformed_json")
        required = {
            "schema_version", "worker_id", "worker_version", "input_filename", "input_sha256",
            "size_bytes", "line_count", "word_count", "headings",
        }
        if set(output) != required:
            raise HarnessError("output_schema_invalid", "reference worker output fields do not match the fixed schema")
        if output["schema_version"] != OUTPUT_SCHEMA_VERSION or output["worker_id"] != WORKER_ID or output["worker_version"] != WORKER_VERSION:
            raise HarnessError("output_schema_invalid", "reference worker output identity/schema is invalid")
        if not isinstance(output["input_sha256"], str) or len(output["input_sha256"]) != 64:
            raise HarnessError("output_schema_invalid", "reference worker output hash is invalid")
        for field in ("size_bytes", "line_count", "word_count"):
            if type(output[field]) is not int or output[field] < 0:
                raise HarnessError("output_schema_invalid", f"reference worker output {field} is invalid")
        if not isinstance(output["headings"], list):
            raise HarnessError("output_schema_invalid", "reference worker headings must be an array")
        return output

    def _validate_inspection_output(self, plan: dict[str, Any]) -> dict[str, Any]:
        if not self.inspection_output_path.is_file():
            raise HarnessError("output_missing", "artifact inspection worker did not create its declared output")
        raw = self.inspection_output_path.read_bytes()
        if len(raw) > INSPECTION_MAX_OUTPUT_BYTES:
            raise HarnessError("output_oversized", "artifact inspection output exceeds 128 KiB", details={"size_bytes": len(raw)})
        output = _safe_read_json(self.inspection_output_path, code="output_malformed_json")
        required = {
            "schema_version",
            "artifact_id",
            "source_path",
            "source_sha256",
            "file_type",
            "byte_count",
            "line_count",
            "word_count",
            "headings",
            "code_symbols",
            "links",
            "likely_document_purpose",
            "todo_fixme_markers",
            "duplicate_hash_group",
            "provenance_references",
            "review_status",
            "warnings",
            "inspection_timestamp",
            "inspector_version",
        }
        if set(output) != required:
            raise HarnessError("output_schema_invalid", "artifact inspection output fields do not match the fixed schema")
        selected = plan["selected_artifact"]
        expected_identity = {
            "schema_version": INSPECTION_SCHEMA_VERSION,
            "artifact_id": selected["artifact_id"],
            "source_path": selected["source_path"],
            "source_sha256": selected["sha256"],
            "file_type": selected["file_type"],
            "duplicate_hash_group": selected["duplicate_hash_group"],
            "provenance_references": selected["provenance_references"],
            "review_status": selected["review_status"],
            "inspection_timestamp": plan["created_at"],
            "inspector_version": INSPECTION_WORKER_VERSION,
        }
        for field, expected in expected_identity.items():
            if output.get(field) != expected:
                raise HarnessError("output_schema_invalid", f"artifact inspection output {field} does not match its bound plan value")
        for field in ("byte_count", "line_count", "word_count"):
            if type(output[field]) is not int or output[field] < 0:
                raise HarnessError("output_schema_invalid", f"artifact inspection output {field} is invalid")
        if output["byte_count"] != selected["byte_count"]:
            raise HarnessError("output_schema_invalid", "artifact inspection byte count does not match the selected source")
        for field in ("headings", "code_symbols", "links", "todo_fixme_markers", "warnings"):
            if not isinstance(output[field], list) or len(output[field]) > 256:
                raise HarnessError("output_schema_invalid", f"artifact inspection output {field} is invalid or unbounded")
        purpose = output["likely_document_purpose"]
        if not isinstance(purpose, dict) or purpose.get("classification") != "heuristic_not_fact":
            raise HarnessError("output_schema_invalid", "likely document purpose must be a transparent heuristic, not a fact")
        canonical = json.dumps(output, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
        if raw != canonical:
            raise HarnessError("output_not_canonical", "artifact inspection output is not canonical JSON")
        return output

    def _run_inspection_tests(
        self,
        artifact: dict[str, Any],
        source_path: Path,
        inspection_timestamp: str,
        output: dict[str, Any],
    ) -> list[dict[str, Any]]:
        raw = source_path.read_bytes()
        source_hash_before = sha256_file(source_path)
        try:
            content = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return [{"test_id": INSPECTION_TEST_ID, "passed": False, "reason": "source is not valid UTF-8"}]
        expected = inspect_content(
            artifact=artifact,
            source_path=source_path,
            content=content,
            raw=raw,
            inspection_timestamp=inspection_timestamp,
        )
        source_hash_after = sha256_file(source_path)
        passed = source_hash_before == source_hash_after == artifact["source_sha256"] and output == expected
        return [
            {
                "test_id": INSPECTION_TEST_ID,
                "passed": passed,
                "source_unchanged": source_hash_before == source_hash_after == artifact["source_sha256"],
                "expected_hash": hash_json(expected),
                "actual_hash": hash_json(output),
            }
        ]

    def _run_declared_tests(self, card: dict[str, Any], output: dict[str, Any]) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for test_id in card["test_commands"]:
            if test_id != SUPPORTED_TEST_ID:
                results.append({"test_id": test_id, "passed": False, "reason": "test ID is not allowlisted"})
                continue
            raw = self.input_path.read_bytes()
            expected = _metadata(self.input_path, raw.decode("utf-8"), raw)
            results.append({"test_id": test_id, "passed": output == expected, "expected_hash": hash_json(expected), "actual_hash": hash_json(output)})
        return results

    def _restore_after_failure(
        self,
        manager: TransactionManager,
        recovery_point: dict[str, Any],
        before_inventory: dict[str, str],
        *,
        output_dir: Path | None = None,
        output_path: Path | None = None,
    ) -> dict[str, Any]:
        removed: list[str] = []
        try:
            bounded_output_dir = output_dir or self.output_dir
            bounded_output_path = output_path or self.output_path
            for path in sorted(bounded_output_dir.rglob("*"), reverse=True):
                resolved = path.resolve(strict=False)
                if path.is_file() and str(resolved) not in before_inventory:
                    self._host_policy().decide(resolved, mode="write").require_allowed()
                    path.unlink()
                    removed.append(str(resolved))
            restored_hash = manager.restore_file_snapshot(recovery_point, bounded_output_path, replace_existing=True)
            verified = self._workspace_inventory() == before_inventory
            return {"ok": verified, "restored_hash": restored_hash, "removed_unexpected": removed}
        except Exception as exc:
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "removed_unexpected": removed}

    def _verify_promotion_context(self, candidate_id: str, context: dict[str, Any], *, expected_states: set[str]) -> dict[str, Any]:
        record = self.candidates.load(candidate_id)
        if record["lifecycle_state"] not in expected_states:
            raise PromotionError("candidate_state_rejected", f"candidate state {record['lifecycle_state']} does not permit this action")
        if context.get("candidate_hash") != record["candidate_hash"]:
            raise PromotionError("candidate_hash_mismatch", "supplied candidate hash is stale or incorrect")
        if type(context.get("workspace_generation")) is not int or context["workspace_generation"] != record["workspace_generation"]:
            raise PromotionError("workspace_generation_mismatch", "supplied workspace generation does not match the candidate")
        if self._load_state()["generation"] != record["workspace_generation"]:
            raise PromotionError("workspace_generation_stale", "current workspace generation changed after candidate execution")
        source_artifact = record.get("source_artifact")
        if isinstance(source_artifact, dict):
            if context.get("source_artifact_hash") != source_artifact["sha256"]:
                raise PromotionError("source_artifact_hash_mismatch", "supplied source artifact hash is stale or incorrect")
            if context.get("worker_card_hash") != record["worker_card_hash"]:
                raise PromotionError("worker_card_hash_mismatch", "supplied Worker Card hash is stale or incorrect")
            if context.get("execution_plan_hash") != record["plan_hash"]:
                raise PromotionError("execution_plan_hash_mismatch", "supplied execution-plan hash is stale or incorrect")
            if expected_states != {"active"}:
                source_path = Path(source_artifact["source_path"])
                decision = self._host_policy().decide(source_path, mode="read")
                try:
                    resolved_source = decision.require_allowed()
                except PermissionError as exc:
                    raise PromotionError(
                        "source_artifact_unavailable",
                        "selected source artifact is no longer within approved public-safe roots",
                        details={"code": decision.code, "reason": decision.reason},
                    ) from exc
                if sha256_file(resolved_source) != source_artifact["sha256"]:
                    raise PromotionError("source_artifact_changed", "selected source artifact changed after inspection")
        if sha256_file(record["candidate_output_path"]) != record["output_hash"]:
            raise PromotionError("candidate_output_changed", "candidate output changed after testing")
        card = _safe_read_json(Path(record["worker_card_path"]), code="worker_card_malformed")
        if hash_json(card) != record["worker_card_hash"]:
            raise PromotionError("worker_card_changed", "Worker Card changed after execution")
        plan = self._load_plan(record["plan_id"])
        if plan["plan_hash"] != record["plan_hash"]:
            raise PromotionError("plan_hash_mismatch", "execution plan changed after execution")
        if sha256_file(record["test_results_path"]) != record["test_evidence_hash"] or not all(test.get("passed") for test in record["test_results"]):
            raise PromotionError("tests_no_longer_pass", "test evidence changed or tests no longer pass")
        self._verify_recovery_point(record)
        receipt_verification = self.verify_receipts()
        if not receipt_verification["valid"]:
            raise PromotionError("receipt_chain_invalid", "transaction receipt chain verification failed", details=receipt_verification)
        return record

    def _verify_recovery_point(self, record: dict[str, Any]) -> None:
        recovery = record["recovery_point"]
        if hash_json(recovery) != record["recovery_point_hash"]:
            raise PromotionError("recovery_point_changed", "recovery point descriptor changed")
        snapshot = Path(recovery.get("snapshot_path", ""))
        if not snapshot.is_file() or sha256_file(snapshot) != recovery.get("sha256"):
            raise PromotionError("recovery_point_unavailable", "recovery snapshot is missing or does not match its hash")

    @staticmethod
    def _validate_actor(value: Any) -> str:
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 100:
            raise PromotionError("actor_invalid", "human actor assertion must be 1-100 characters")
        return value.strip()

    @staticmethod
    def _receipt_paths_for(manager: TransactionManager, transaction_id: str) -> list[str]:
        paths: list[str] = []
        for path in manager.receipts_dir.glob("*.json"):
            try:
                receipt = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if receipt.get("transaction_id") == transaction_id:
                paths.append(str(path))
        return sorted(paths)

    @staticmethod
    def _capture_summary(capture: dict[str, Any]) -> dict[str, Any]:
        return {
            "return_code": capture.get("return_code"),
            "timed_out": capture.get("timed_out", False),
            "stdout_bytes": capture.get("stdout_bytes", 0),
            "stderr_bytes": capture.get("stderr_bytes", 0),
            "stdout_truncated": capture.get("stdout_truncated", False),
            "stderr_truncated": capture.get("stderr_truncated", False),
        }

    @staticmethod
    def _approval_receipt_evidence(decision: dict[str, Any]) -> dict[str, Any]:
        note = str(decision.get("note", ""))
        return {
            key: value
            for key, value in decision.items()
            if key not in {"note", "decision_record_path"}
        } | {"note_sha256": hashlib.sha256(note.encode("utf-8")).hexdigest().upper(), "note_stored_in_receipt": False}

    def _record_transaction_evidence(self, manager: TransactionManager, transaction_id: str, status: str, candidate_id: str) -> None:
        self._record_evidence(
            "transaction-manifest",
            manager.manifests_dir / f"{transaction_id}.json",
            status,
            candidate_id=candidate_id,
            transaction_id=transaction_id,
        )
        for receipt in self._receipt_paths_for(manager, transaction_id):
            self._record_evidence(
                "receipt",
                Path(receipt),
                status,
                candidate_id=candidate_id,
                transaction_id=transaction_id,
            )

    def _record_success_evidence(self, record: dict[str, Any], manifest: dict[str, Any], test_path: Path, output_path: Path) -> None:
        self._record_evidence("worker-card", Path(record["worker_card_path"]), "validated", candidate_id=record["candidate_id"])
        self._record_evidence("execution-plan", Path(record["plan_path"]), "execution_planned", candidate_id=record["candidate_id"])
        self._record_evidence("transaction-manifest", Path(record["transaction_manifest_path"]), manifest["state"], candidate_id=record["candidate_id"], transaction_id=record["transaction_id"])
        for receipt in record["receipt_paths"]:
            self._record_evidence("receipt", Path(receipt), "committed", candidate_id=record["candidate_id"], transaction_id=record["transaction_id"])
        self._record_evidence("test-result", test_path, "tests_passed", candidate_id=record["candidate_id"])
        self._record_evidence("candidate-output", output_path, "candidate", candidate_id=record["candidate_id"])
        self._record_evidence("candidate-record", self.candidates_dir / f"{record['candidate_id']}.json", "awaiting_approval", candidate_id=record["candidate_id"])

    def _record_evidence(self, kind: str, path: Path, status: str, **provenance: Any) -> None:
        if not path.is_file():
            return
        self.root.mkdir(parents=True, exist_ok=True)
        inventory = {"schema_version": HARNESS_SCHEMA_VERSION, "records": []}
        if self.provenance_path.exists():
            inventory = _safe_read_json(self.provenance_path, code="provenance_inventory_invalid")
        artifact_id = hashlib.sha256(f"{kind}\0{path.resolve(strict=False)}".encode("utf-8")).hexdigest()[:32]
        record = {
            "artifact_id": artifact_id,
            "project_id": PROJECT_ID,
            "source_path": str(path.resolve(strict=False)),
            "sha256": sha256_file(path),
            "status": status,
            "provenance": {"kind": kind, "source": "worker-harness-v0.1", **provenance},
            "content_text": f"{kind} {status} {provenance.get('candidate_id', '')} {provenance.get('transaction_id', '')}",
            "size_bytes": path.stat().st_size,
            "modified_ns": path.stat().st_mtime_ns,
        }
        records = [item for item in inventory.get("records", []) if item.get("artifact_id") != artifact_id]
        records.append(record)
        records.sort(key=lambda item: item["artifact_id"])
        inventory["records"] = records
        atomic_write_json(self.provenance_path, inventory)
        compass_records = [ArtifactRecord(**item) for item in records]
        with ArtifactCompass(self.compass_path) as compass:
            compass.sync(compass_records)
