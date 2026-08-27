from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

CANDIDATE_ID_PATTERN = re.compile(r"^[a-f0-9]{32}$")

LIFECYCLE_TRANSITIONS: dict[str, set[str]] = {
    "draft": {"validated", "failed"},
    "validated": {"execution_planned", "failed"},
    "execution_planned": {"executed", "failed"},
    "executed": {"tests_passed", "failed"},
    "tests_passed": {"candidate", "failed"},
    "candidate": {"awaiting_approval", "failed"},
    "awaiting_approval": {"approved", "rejected", "failed"},
    "approved": {"active", "rejected", "failed"},
    "active": {"rolled_back", "revoked"},
    "rejected": set(),
    "failed": {"rolled_back"},
    "rolled_back": set(),
    "revoked": {"rolled_back"},
}


class PromotionError(RuntimeError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def hash_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest().upper()


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep the temporary basename short.  Deep, isolated Windows workspaces can
    # otherwise cross the legacy MAX_PATH boundary when the destination name is
    # repeated inside the temporary filename.
    descriptor, temporary_name = tempfile.mkstemp(prefix=".twis-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8"))
            handle.write(b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def validate_timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PromotionError("timestamp_required", "an explicit ISO-8601 approval timestamp is required")
    normalized = value.strip()
    try:
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PromotionError("timestamp_invalid", "approval timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise PromotionError("timestamp_invalid", "approval timestamp must include a timezone")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def candidate_material(record: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "candidate_id",
        "worker_id",
        "worker_version",
        "worker_card_hash",
        "plan_id",
        "plan_hash",
        "transaction_id",
        "recovery_point_hash",
        "output_hash",
        "test_evidence_hash",
        "workspace_generation",
    )
    material = {key: record[key] for key in keys}
    source_artifact = record.get("source_artifact")
    if isinstance(source_artifact, dict):
        material["source_artifact_id"] = source_artifact.get("artifact_id")
        material["source_artifact_sha256"] = source_artifact.get("sha256")
    return material


def calculate_candidate_hash(record: dict[str, Any]) -> str:
    return hash_json(candidate_material(record))


def transition(record: dict[str, Any], target: str, *, actor: str, reason: str) -> dict[str, Any]:
    current = record.get("lifecycle_state")
    if target not in LIFECYCLE_TRANSITIONS.get(str(current), set()):
        raise PromotionError("invalid_transition", f"invalid candidate lifecycle transition: {current} -> {target}")
    now = utc_now()
    record["lifecycle_state"] = target
    record.setdefault("history", []).append(
        {"from": current, "to": target, "actor": actor, "reason": reason, "at": now}
    )
    record["updated_at"] = now
    return record


class CandidateStore:
    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root).resolve(strict=False)

    def _path(self, candidate_id: str) -> Path:
        if not CANDIDATE_ID_PATTERN.fullmatch(candidate_id):
            raise PromotionError("candidate_id_invalid", "candidate ID must be 32 lowercase hexadecimal characters")
        return self.root / f"{candidate_id}.json"

    def save(self, record: dict[str, Any]) -> dict[str, Any]:
        candidate_id = str(record.get("candidate_id", ""))
        self.validate_integrity(record)
        atomic_write_json(self._path(candidate_id), record)
        return record

    def load(self, candidate_id: str) -> dict[str, Any]:
        path = self._path(candidate_id)
        if not path.is_file():
            raise PromotionError("candidate_not_found", "candidate does not exist")
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PromotionError("candidate_corrupt", "candidate record is not valid JSON") from exc
        self.validate_integrity(record)
        return record

    def list(self) -> list[dict[str, Any]]:
        if not self.root.exists():
            return []
        records = [self.load(path.stem) for path in sorted(self.root.glob("*.json"))]
        return sorted(records, key=lambda record: (record.get("created_at", ""), record["candidate_id"]), reverse=True)

    @staticmethod
    def validate_integrity(record: dict[str, Any]) -> None:
        try:
            calculated = calculate_candidate_hash(record)
        except KeyError as exc:
            raise PromotionError("candidate_corrupt", f"candidate is missing immutable field: {exc.args[0]}") from exc
        if record.get("candidate_hash") != calculated:
            raise PromotionError("candidate_hash_mismatch", "candidate record does not match its immutable-by-convention hash")
        if record.get("lifecycle_state") not in LIFECYCLE_TRANSITIONS:
            raise PromotionError("candidate_state_invalid", "candidate lifecycle state is unsupported")


class ActivationRegistry:
    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path).resolve(strict=False)
        self.pending_path = self.path.with_suffix(self.path.suffix + ".pending")

    def load(self) -> dict[str, Any]:
        if self.pending_path.exists():
            raise PromotionError(
                "registry_interrupted",
                "an interrupted activation-registry write requires review before activation",
                details={"pending_path": str(self.pending_path)},
            )
        if not self.path.exists():
            return {"schema_version": "0.3", "generation": 0, "entries": []}
        try:
            registry = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PromotionError("registry_corrupt", "activation registry is not valid JSON") from exc
        if registry.get("schema_version") != "0.3" or not isinstance(registry.get("entries"), list):
            raise PromotionError("registry_corrupt", "activation registry schema is unsupported")
        return registry

    def write(self, registry: dict[str, Any], *, interrupt_before_replace: bool = False) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(registry, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        with self.pending_path.open("wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if interrupt_before_replace:
            raise PromotionError("registry_write_interrupted", "test-only interruption before registry replacement")
        os.replace(self.pending_path, self.path)

    def activate(
        self,
        candidate: dict[str, Any],
        *,
        actor: str,
        timestamp: str,
        activation_record_path: str,
        interrupt_before_replace: bool = False,
    ) -> dict[str, Any]:
        registry = self.load()
        candidate_artifact = candidate.get("source_artifact")
        candidate_artifact_id = candidate_artifact.get("artifact_id") if isinstance(candidate_artifact, dict) else None
        for entry in registry["entries"]:
            if entry.get("candidate_id") == candidate["candidate_id"]:
                raise PromotionError("duplicate_activation", "candidate is already present in the activation registry")
            if entry.get("worker_id") == candidate["worker_id"] and entry.get("status") == "active":
                raise PromotionError("worker_already_active", "another candidate for this fixed worker is already active")
        entry = {
            "worker_id": candidate["worker_id"],
            "worker_version": candidate["worker_version"],
            "candidate_id": candidate["candidate_id"],
            "candidate_hash": candidate["candidate_hash"],
            "status": "active",
            "activated_by": actor,
            "activated_at": timestamp,
            "worker_card_path": candidate["worker_card_path"],
            "transaction_id": candidate["transaction_id"],
            "receipt_paths": candidate["receipt_paths"],
            "recovery_point": candidate["recovery_point"],
            "activation_record_path": activation_record_path,
            "executes_on_startup": False,
            "grants_permissions": False,
        }
        if candidate_artifact_id:
            entry["artifact_attachment"] = {
                "artifact_id": candidate_artifact_id,
                "source_sha256": candidate_artifact.get("sha256"),
                "report_path": candidate.get("candidate_output_path"),
                "report_sha256": candidate.get("output_hash"),
                "attachment_kind": "read_only_inspection_report",
            }
        registry["generation"] = int(registry.get("generation", 0)) + 1
        registry["entries"].append(entry)
        registry["entries"].sort(key=lambda item: (item["worker_id"], item["candidate_id"]))
        self.write(registry, interrupt_before_replace=interrupt_before_replace)
        return entry

    def mark_rolled_back(self, candidate_id: str, *, rollback_record_path: str, timestamp: str) -> dict[str, Any]:
        registry = self.load()
        entry = next((item for item in registry["entries"] if item.get("candidate_id") == candidate_id), None)
        if entry is None or entry.get("status") != "active":
            raise PromotionError("activation_not_active", "candidate has no active registry entry")
        entry["status"] = "rolled_back"
        entry["rolled_back_at"] = timestamp
        entry["rollback_record_path"] = rollback_record_path
        registry["generation"] = int(registry.get("generation", 0)) + 1
        self.write(registry)
        return entry

    def audit(self) -> dict[str, Any]:
        if self.pending_path.exists():
            return {"ok": False, "code": "registry_interrupted", "pending_path": str(self.pending_path)}
        registry = self.load()
        return {"ok": True, "generation": registry["generation"], "entry_count": len(registry["entries"])}
