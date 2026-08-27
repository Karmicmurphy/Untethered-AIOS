from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest

from companion.foundation.path_policy import WindowsPathPolicy
from companion.foundation.transactions import TransactionManager, sha256_file

pytestmark = pytest.mark.skipif(os.name != "nt", reason="transaction path enforcement is Windows-specific")


@pytest.fixture
def transaction_fixture(tmp_path: Path) -> tuple[TransactionManager, Path, Path]:
    source = tmp_path / "source"
    transaction_root = tmp_path / "transactions"
    restore = tmp_path / "restore"
    for path in (source, transaction_root, restore):
        path.mkdir()
    policy = WindowsPathPolicy(
        read_roots=[source, transaction_root, restore],
        write_roots=[transaction_root, restore],
    )
    return TransactionManager(transaction_root, actor="pytest", path_policy=policy), source, restore


def prepare(manager: TransactionManager, *paths: Path) -> dict:
    return manager.prepare(
        action="fixture-test",
        paths=paths,
        permission_decision={"allowed": True, "component": "pytest", "reason": "temporary fixture"},
        commands=[],
        tests=["pytest"],
    )


def test_transaction_manifest_schema_is_machine_readable_and_matches_emitter(
    transaction_fixture: tuple[TransactionManager, Path, Path],
) -> None:
    manager, source, _ = transaction_fixture
    target = source / "schema-evidence.txt"
    target.write_text("evidence", encoding="utf-8")
    manifest = prepare(manager, target)
    root = Path(__file__).resolve().parents[1]
    schema = json.loads((root / "schemas" / "transaction-manifest-v0.2.schema.json").read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["properties"]["schema_version"]["const"] == manifest["schema_version"]
    assert set(schema["required"]) == set(manifest)


def test_manifest_lifecycle_and_hash_linked_receipts(transaction_fixture: tuple[TransactionManager, Path, Path]) -> None:
    manager, source, _ = transaction_fixture
    target = source / "evidence.txt"
    target.write_text("before", encoding="utf-8")
    first = prepare(manager, target)
    assert first["state"] == "prepared"
    manager.begin(first["transaction_id"])
    target.write_text("after", encoding="utf-8")
    committed = manager.commit(first["transaction_id"], result={"ok": True}, after_paths=[target])
    assert committed["state"] == "committed"
    assert committed["before_hashes"][str(target.resolve())] != committed["after_hashes"][str(target.resolve())]

    second = prepare(manager, target)
    manager.begin(second["transaction_id"])
    manager.fail(second["transaction_id"], result={"ok": False, "error": "fixture failure"})
    verification = manager.verify_receipt_chain()
    assert verification.valid
    assert verification.receipt_count == 2


def test_receipt_tampering_is_detected(transaction_fixture: tuple[TransactionManager, Path, Path]) -> None:
    manager, source, _ = transaction_fixture
    target = source / "evidence.txt"
    target.write_text("data", encoding="utf-8")
    manifest = prepare(manager, target)
    manager.begin(manifest["transaction_id"])
    manager.commit(manifest["transaction_id"], result={"ok": True}, after_paths=[target])
    receipt_path = next(manager.receipts_dir.glob("*.json"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["result"]["ok"] = False
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    verification = manager.verify_receipt_chain()
    assert not verification.valid
    assert any("receipt hash mismatch" in error for error in verification.errors)


def test_interrupted_transaction_is_detected_and_recovery_recorded(transaction_fixture: tuple[TransactionManager, Path, Path]) -> None:
    manager, source, _ = transaction_fixture
    target = source / "crash.txt"
    target.write_text("before crash", encoding="utf-8")
    manifest = prepare(manager, target)
    manager.begin(manifest["transaction_id"])
    interrupted = manager.detect_interrupted()
    assert [item["transaction_id"] for item in interrupted] == [manifest["transaction_id"]]
    pending = manager.mark_recovery_pending(manifest["transaction_id"], reason="simulated process interruption")
    assert pending["state"] == "recovery_pending"
    recovered = manager.mark_recovered(manifest["transaction_id"], result={"ok": True, "scope": "fixture"})
    assert recovered["state"] == "recovered"
    assert manager.verify_receipt_chain().valid


def test_bounded_file_snapshot_and_restore(transaction_fixture: tuple[TransactionManager, Path, Path]) -> None:
    manager, source, restore = transaction_fixture
    original = source / "original.txt"
    original.write_text("preserve me", encoding="utf-8")
    manifest = prepare(manager, original)
    recovery_point = manager.snapshot_file(manifest["transaction_id"], original)
    restored = restore / "restored.txt"
    restored_hash = manager.restore_file_snapshot(recovery_point, restored)
    assert restored.read_text(encoding="utf-8") == "preserve me"
    assert restored_hash == recovery_point["sha256"]
    with pytest.raises(FileExistsError):
        manager.restore_file_snapshot(recovery_point, restored)


def test_sqlite_backup_integrity_and_restore_to_new_fixture(transaction_fixture: tuple[TransactionManager, Path, Path]) -> None:
    manager, source, restore = transaction_fixture
    database = source / "fixture.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE evidence (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
        connection.execute("INSERT INTO evidence(value) VALUES ('preserved')")
    manifest = prepare(manager, database)
    recovery_point = manager.backup_sqlite(manifest["transaction_id"], database)
    assert recovery_point["integrity_check"] == "ok"
    restored = restore / "restored.sqlite3"
    restored_hash = manager.restore_sqlite_backup(recovery_point, restored)
    assert restored_hash == sha256_file(restored)
    with sqlite3.connect(restored) as connection:
        assert connection.execute("SELECT value FROM evidence").fetchone()[0] == "preserved"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_denied_permission_decision_cannot_prepare(transaction_fixture: tuple[TransactionManager, Path, Path]) -> None:
    manager, source, _ = transaction_fixture
    target = source / "denied.txt"
    target.write_text("data", encoding="utf-8")
    with pytest.raises(PermissionError):
        manager.prepare(
            action="denied",
            paths=[target],
            permission_decision={"allowed": False, "reason": "blocked"},
        )


def test_transaction_evidence_paths_cannot_bypass_path_policy(transaction_fixture: tuple[TransactionManager, Path, Path]) -> None:
    manager, source, _ = transaction_fixture
    outside = source.parent / "outside-evidence.txt"
    outside.write_text("private fixture", encoding="utf-8")
    with pytest.raises(PermissionError):
        prepare(manager, outside)
