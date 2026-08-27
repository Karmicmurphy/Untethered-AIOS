from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from companion.foundation.path_policy import WindowsPathPolicy

TRANSACTION_STATES = {
    "prepared",
    "in_progress",
    "committed",
    "failed",
    "recovery_pending",
    "recovered",
}
TERMINAL_STATES = {"committed", "failed", "recovered"}


def _utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256_file(path: str | os.PathLike[str]) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _atomic_json_write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
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


@dataclass(frozen=True)
class ReceiptChainVerification:
    valid: bool
    receipt_count: int
    errors: tuple[str, ...]


class TransactionManager:
    """Bounded transaction evidence and recovery for cooperating callers.

    Receipts are hash-linked tamper evidence, not digital signatures or an
    immutable ledger. Recovery helpers deliberately operate on individual
    files and SQLite databases; they are not a general system rollback engine.
    """

    def __init__(self, root: str | os.PathLike[str], *, actor: str, path_policy: WindowsPathPolicy) -> None:
        if not actor.strip():
            raise ValueError("actor must be non-empty")
        self.root = path_policy.decide(root, mode="write").require_allowed()
        self.actor = actor
        self.path_policy = path_policy
        self.manifests_dir = self.root / "manifests"
        self.receipts_dir = self.root / "receipts"
        self.snapshots_dir = self.root / "snapshots"
        for directory in (self.manifests_dir, self.receipts_dir, self.snapshots_dir):
            self.path_policy.decide(directory, mode="write").require_allowed()
            directory.mkdir(parents=True, exist_ok=True)

    def prepare(
        self,
        *,
        action: str,
        paths: Iterable[str | os.PathLike[str]],
        permission_decision: dict[str, Any],
        commands: Iterable[str] = (),
        tests: Iterable[str] = (),
        approval: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not action.strip():
            raise ValueError("action must be non-empty")
        if permission_decision.get("allowed") is not True:
            raise PermissionError("transaction preparation requires an allowed permission decision")
        path_list = [str(self._resolve_evidence_path(path)) for path in paths]
        before_hashes = {
            path: sha256_file(path) if Path(path).is_file() else None
            for path in path_list
        }
        transaction_id = uuid.uuid4().hex
        now = _utc_now()
        manifest = {
            "schema_version": "0.2",
            "transaction_id": transaction_id,
            "generation": 1,
            "state": "prepared",
            "actor": self.actor,
            "action": action,
            "paths": path_list,
            "before_hashes": before_hashes,
            "after_hashes": {},
            "permission_decision": permission_decision,
            "commands": list(commands),
            "tests": list(tests),
            "approval": approval,
            "timestamps": {"prepared_at": now, "updated_at": now},
            "result": None,
            "recovery_point": None,
        }
        self._write_manifest(manifest)
        return manifest

    def begin(self, transaction_id: str) -> dict[str, Any]:
        return self._transition(transaction_id, "in_progress", timestamp_name="started_at")

    def commit(
        self,
        transaction_id: str,
        *,
        result: dict[str, Any],
        after_paths: Iterable[str | os.PathLike[str]] = (),
    ) -> dict[str, Any]:
        manifest = self._load_manifest(transaction_id)
        manifest["after_hashes"] = {
            str(resolved): sha256_file(resolved) if resolved.is_file() else None
            for resolved in (self._resolve_evidence_path(path) for path in after_paths)
        }
        manifest["result"] = result
        manifest = self._transition_manifest(manifest, "committed", "committed_at")
        self._append_receipt(manifest)
        return manifest

    def fail(self, transaction_id: str, *, result: dict[str, Any]) -> dict[str, Any]:
        manifest = self._load_manifest(transaction_id)
        manifest["result"] = result
        manifest = self._transition_manifest(manifest, "failed", "failed_at")
        self._append_receipt(manifest)
        return manifest

    def mark_recovery_pending(self, transaction_id: str, *, reason: str) -> dict[str, Any]:
        manifest = self._load_manifest(transaction_id)
        manifest["result"] = {"ok": False, "reason": reason}
        return self._transition_manifest(manifest, "recovery_pending", "recovery_pending_at")

    def mark_recovered(self, transaction_id: str, *, result: dict[str, Any]) -> dict[str, Any]:
        manifest = self._load_manifest(transaction_id)
        manifest["result"] = result
        manifest = self._transition_manifest(manifest, "recovered", "recovered_at")
        self._append_receipt(manifest)
        return manifest

    def detect_interrupted(self) -> list[dict[str, Any]]:
        interrupted: list[dict[str, Any]] = []
        for path in sorted(self.manifests_dir.glob("*.json")):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            if manifest.get("state") in {"prepared", "in_progress", "recovery_pending"}:
                interrupted.append(manifest)
        return interrupted

    def snapshot_file(self, transaction_id: str, source: str | os.PathLike[str]) -> dict[str, Any]:
        source_path = self.path_policy.decide(source, mode="read").require_allowed()
        if not source_path.is_file():
            raise ValueError("bounded snapshots support files only")
        source_hash = sha256_file(source_path)
        transaction_snapshot_dir = self.snapshots_dir / transaction_id
        self.path_policy.decide(transaction_snapshot_dir, mode="write").require_allowed()
        transaction_snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path = transaction_snapshot_dir / f"{source_hash[:16]}-{source_path.name}"
        self.path_policy.decide(snapshot_path, mode="write").require_allowed()
        shutil.copy2(source_path, snapshot_path)
        if sha256_file(snapshot_path) != source_hash:
            raise OSError("snapshot hash verification failed")
        recovery_point = {
            "kind": "file_snapshot",
            "source_path": str(source_path),
            "snapshot_path": str(snapshot_path),
            "sha256": source_hash,
            "created_at": _utc_now(),
        }
        manifest = self._load_manifest(transaction_id)
        manifest["recovery_point"] = recovery_point
        manifest["generation"] += 1
        manifest["timestamps"]["updated_at"] = _utc_now()
        self._write_manifest(manifest)
        return recovery_point

    def restore_file_snapshot(
        self,
        recovery_point: dict[str, Any],
        destination: str | os.PathLike[str],
        *,
        replace_existing: bool = False,
    ) -> str:
        if recovery_point.get("kind") != "file_snapshot":
            raise ValueError("unsupported recovery point kind")
        snapshot_path = self.path_policy.decide(recovery_point["snapshot_path"], mode="read").require_allowed()
        expected_hash = recovery_point["sha256"]
        if sha256_file(snapshot_path) != expected_hash:
            raise OSError("snapshot is corrupt or changed")
        destination_path = self.path_policy.decide(destination, mode="write").require_allowed()
        if destination_path.exists() and not replace_existing:
            raise FileExistsError(destination_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(snapshot_path, destination_path)
        restored_hash = sha256_file(destination_path)
        if restored_hash != expected_hash:
            raise OSError("restored file hash verification failed")
        return restored_hash

    def backup_sqlite(
        self,
        transaction_id: str,
        database: str | os.PathLike[str],
    ) -> dict[str, Any]:
        database_path = self.path_policy.decide(database, mode="read").require_allowed()
        if not database_path.is_file():
            raise ValueError("SQLite source must be a file")
        transaction_snapshot_dir = self.snapshots_dir / transaction_id
        self.path_policy.decide(transaction_snapshot_dir, mode="write").require_allowed()
        transaction_snapshot_dir.mkdir(parents=True, exist_ok=True)
        backup_path = transaction_snapshot_dir / f"{database_path.stem}.sqlite3.backup"
        self.path_policy.decide(backup_path, mode="write").require_allowed()
        source_uri = database_path.as_uri() + "?mode=ro"
        with sqlite3.connect(source_uri, uri=True) as source, sqlite3.connect(backup_path) as target:
            source.backup(target)
            integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise OSError(f"SQLite backup integrity check failed: {integrity}")
        recovery_point = {
            "kind": "sqlite_backup",
            "source_path": str(database_path),
            "backup_path": str(backup_path),
            "sha256": sha256_file(backup_path),
            "integrity_check": integrity,
            "created_at": _utc_now(),
        }
        manifest = self._load_manifest(transaction_id)
        manifest["recovery_point"] = recovery_point
        manifest["generation"] += 1
        manifest["timestamps"]["updated_at"] = _utc_now()
        self._write_manifest(manifest)
        return recovery_point

    def restore_sqlite_backup(
        self,
        recovery_point: dict[str, Any],
        destination: str | os.PathLike[str],
        *,
        replace_existing: bool = False,
    ) -> str:
        if recovery_point.get("kind") != "sqlite_backup":
            raise ValueError("unsupported recovery point kind")
        backup_path = self.path_policy.decide(recovery_point["backup_path"], mode="read").require_allowed()
        if sha256_file(backup_path) != recovery_point["sha256"]:
            raise OSError("SQLite backup is corrupt or changed")
        destination_path = self.path_policy.decide(destination, mode="write").require_allowed()
        if destination_path.exists() and not replace_existing:
            raise FileExistsError(destination_path)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        source_uri = backup_path.as_uri() + "?mode=ro"
        with sqlite3.connect(source_uri, uri=True) as source, sqlite3.connect(destination_path) as target:
            source.backup(target)
            integrity = target.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            raise OSError(f"restored SQLite integrity check failed: {integrity}")
        return sha256_file(destination_path)

    def verify_receipt_chain(self) -> ReceiptChainVerification:
        errors: list[str] = []
        previous_hash: str | None = None
        receipt_paths = sorted(self.receipts_dir.glob("*.json"))
        for expected_sequence, path in enumerate(receipt_paths, start=1):
            try:
                receipt = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"{path.name}: unreadable receipt: {exc}")
                continue
            claimed_hash = receipt.pop("receipt_hash", None)
            calculated_hash = hashlib.sha256(_canonical_json(receipt)).hexdigest().upper()
            if receipt.get("sequence") != expected_sequence:
                errors.append(f"{path.name}: non-contiguous sequence")
            if receipt.get("previous_receipt_hash") != previous_hash:
                errors.append(f"{path.name}: previous hash mismatch")
            if claimed_hash != calculated_hash:
                errors.append(f"{path.name}: receipt hash mismatch")
            previous_hash = claimed_hash
        return ReceiptChainVerification(not errors, len(receipt_paths), tuple(errors))

    def _manifest_path(self, transaction_id: str) -> Path:
        if not transaction_id or any(character not in "0123456789abcdef" for character in transaction_id):
            raise ValueError("invalid transaction id")
        path = self.manifests_dir / f"{transaction_id}.json"
        self.path_policy.decide(path, mode="write").require_allowed()
        return path

    def _resolve_evidence_path(self, path: str | os.PathLike[str]) -> Path:
        requested = Path(path)
        if requested.exists():
            return self.path_policy.decide(requested, mode="read").require_allowed()
        return self.path_policy.decide(requested, mode="write").require_allowed()

    def _write_manifest(self, manifest: dict[str, Any]) -> None:
        _atomic_json_write(self._manifest_path(manifest["transaction_id"]), manifest)

    def _load_manifest(self, transaction_id: str) -> dict[str, Any]:
        path = self._manifest_path(transaction_id)
        self.path_policy.decide(path, mode="read").require_allowed()
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("transaction_id") != transaction_id or manifest.get("state") not in TRANSACTION_STATES:
            raise ValueError("invalid transaction manifest")
        return manifest

    def _transition(self, transaction_id: str, state: str, *, timestamp_name: str) -> dict[str, Any]:
        return self._transition_manifest(self._load_manifest(transaction_id), state, timestamp_name)

    def _transition_manifest(self, manifest: dict[str, Any], state: str, timestamp_name: str) -> dict[str, Any]:
        current = manifest["state"]
        allowed = {
            "prepared": {"in_progress", "failed", "recovery_pending"},
            "in_progress": {"committed", "failed", "recovery_pending"},
            "recovery_pending": {"failed", "recovered"},
        }
        if state not in allowed.get(current, set()):
            raise ValueError(f"invalid transaction transition: {current} -> {state}")
        now = _utc_now()
        manifest["state"] = state
        manifest["generation"] += 1
        manifest["timestamps"][timestamp_name] = now
        manifest["timestamps"]["updated_at"] = now
        self._write_manifest(manifest)
        return manifest

    def _append_receipt(self, manifest: dict[str, Any]) -> dict[str, Any]:
        receipt_paths = sorted(self.receipts_dir.glob("*.json"))
        previous_hash = None
        if receipt_paths:
            previous = json.loads(receipt_paths[-1].read_text(encoding="utf-8"))
            previous_hash = previous.get("receipt_hash")
        sequence = len(receipt_paths) + 1
        receipt = {
            "schema_version": "0.2",
            "sequence": sequence,
            "previous_receipt_hash": previous_hash,
            "transaction_id": manifest["transaction_id"],
            "transaction_generation": manifest["generation"],
            "state": manifest["state"],
            "actor": manifest["actor"],
            "action": manifest["action"],
            "before_hashes": manifest["before_hashes"],
            "after_hashes": manifest["after_hashes"],
            "permission_decision": manifest["permission_decision"],
            "approval": manifest["approval"],
            "result": manifest["result"],
            "created_at": _utc_now(),
        }
        receipt["receipt_hash"] = hashlib.sha256(_canonical_json(receipt)).hexdigest().upper()
        receipt_path = self.receipts_dir / f"{sequence:08d}-{manifest['transaction_id']}.json"
        self.path_policy.decide(receipt_path, mode="write").require_allowed()
        _atomic_json_write(receipt_path, receipt)
        return receipt
