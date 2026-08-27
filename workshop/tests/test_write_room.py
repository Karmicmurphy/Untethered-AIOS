from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from companion.write_room import WriteRoom, WriteRoomError, ensure_schema


BASE_SCHEMA = """
CREATE TABLE projects(
  id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
  next_action TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE artifacts(
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL,
  path TEXT NOT NULL DEFAULT '', payload TEXT NOT NULL DEFAULT '{}',
  authority_state TEXT NOT NULL DEFAULT 'DRAFT', sha256 TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE VIRTUAL TABLE artifact_search USING fts5(
  id UNINDEXED, project_id UNINDEXED, title, kind, content
);
CREATE TABLE receipts(
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, action TEXT NOT NULL,
  actor TEXT NOT NULL, details TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
);
"""


@pytest.fixture()
def write_service(tmp_path: Path) -> tuple[WriteRoom, Path, Path]:
    database = tmp_path / "data" / "workshop.sqlite3"
    projects = tmp_path / "data" / "projects"
    database.parent.mkdir(parents=True)
    projects.mkdir()

    def connect() -> sqlite3.Connection:
        con = sqlite3.connect(database, timeout=5.0)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA busy_timeout=5000")
        return con

    con = connect()
    con.executescript(BASE_SCHEMA)
    ensure_schema(con)
    con.execute(
        "INSERT INTO projects VALUES(?,?,?,?,?,?)",
        ("daily-writing", "Daily Writing", "test", "", "2026-07-23T00:00:00+00:00", "2026-07-23T00:00:00+00:00"),
    )
    con.execute(
        "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            "protected-source",
            "daily-writing",
            "source",
            "Protected source",
            "sources/original.txt",
            "{}",
            "SOURCE",
            "a" * 64,
            "2026-07-23T00:00:00+00:00",
            "2026-07-23T00:00:00+00:00",
        ),
    )
    con.commit()
    con.close()
    return WriteRoom(connect, projects), database, projects


def test_daily_save_recovery_history_restore_rollback_and_export(
    write_service: tuple[WriteRoom, Path, Path],
) -> None:
    service, database, projects = write_service
    created = service.create_document("daily-writing", "Morning pages", "First line.")
    assert created["currentVersion"] == 1
    assert created["versionCount"] == 1

    recovery = service.save_recovery(
        created["id"],
        title="Morning pages",
        content="First line.\nInterrupted thought.",
        base_version=1,
    )
    assert recovery["baseVersion"] == 1

    restarted = WriteRoom(service._connect, projects)
    reopened = restarted.get_document(created["id"])
    assert reopened["hasRecovery"] is True
    assert reopened["recovery"]["content"].endswith("Interrupted thought.")

    autosaved = restarted.save_document(
        created["id"],
        title="Morning pages",
        content="First line.\nInterrupted thought.",
        base_version=1,
        cause="autosave",
    )
    assert autosaved["currentVersion"] == 2
    assert autosaved["hasRecovery"] is False

    snapshot = restarted.snapshot(
        created["id"],
        title="Morning pages",
        content="First line.\nInterrupted thought.\nA third line.",
        base_version=2,
        label="Before revision",
    )
    assert snapshot["currentVersion"] == 3
    assert snapshot["versions"][0]["label"] == "Before revision"

    comparison = restarted.compare_versions(created["id"], 1, 3)
    assert comparison["comparison"]["changed"] is True
    assert comparison["comparison"]["addedLines"] == 2

    restored = restarted.restore(
        created["id"],
        target_version=1,
        base_version=3,
        confirmed=True,
    )
    assert restored["content"] == "First line."
    assert restored["currentVersion"] == 5
    operation_id = restored["restoreOperationId"]

    rolled_back = restarted.rollback_restore(operation_id, confirmed=True)
    assert rolled_back["content"].endswith("A third line.")
    assert rolled_back["currentVersion"] == 6

    exported = restarted.export_document(
        created["id"],
        format_name="json",
        include_provenance=False,
    )
    export_path = Path(exported["path"])
    assert export_path.is_file()
    exported_json = json.loads(export_path.read_text(encoding="utf-8"))
    assert set(exported_json) == {"title", "content", "exportedAt"}
    assert "artifactId" not in exported_json
    assert exported["sha256"] == hashlib.sha256(export_path.read_bytes()).hexdigest()

    con = sqlite3.connect(database)
    try:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        actions = {row[0] for row in con.execute("SELECT action FROM receipts")}
    finally:
        con.close()
    assert {
        "write.create",
        "write.autosave",
        "write.snapshot",
        "write.restore",
        "write.restore.rollback",
        "write.export",
    }.issubset(actions)


def test_stale_save_and_unconfirmed_restore_are_blocked(
    write_service: tuple[WriteRoom, Path, Path],
) -> None:
    service, _, _ = write_service
    created = service.create_document("daily-writing", "Conflict proof", "A")
    saved = service.save_document(
        created["id"],
        title="Conflict proof",
        content="B",
        base_version=1,
        cause="manual",
    )
    assert saved["currentVersion"] == 2

    with pytest.raises(WriteRoomError, match="changed") as conflict:
        service.save_document(
            created["id"],
            title="Conflict proof",
            content="stale",
            base_version=1,
            cause="manual",
        )
    assert conflict.value.code == "write_version_conflict"
    assert conflict.value.status == 409

    with pytest.raises(WriteRoomError, match="confirmed") as unconfirmed:
        service.restore(
            created["id"],
            target_version=1,
            base_version=2,
            confirmed=False,
        )
    assert unconfirmed.value.code == "restore_confirmation_required"
    assert service.get_document(created["id"])["content"] == "B"


def test_proposal_reject_approve_and_rollback_preserve_source(
    write_service: tuple[WriteRoom, Path, Path],
) -> None:
    service, database, _ = write_service
    created = service.create_document(
        "daily-writing",
        "Formatting",
        "Line with space.   \n\n\n\nSecond line.",
    )
    rejected = service.create_proposal(
        created["id"],
        action="clean_formatting",
        base_version=1,
    )
    assert rejected["status"] == "awaiting_approval"
    assert rejected["modifiesContent"] is True
    rejected = service.decide_proposal(rejected["id"], decision="reject", note="Keep it")
    assert rejected["status"] == "rejected"
    assert service.get_document(created["id"])["content"].endswith("Second line.")

    proposal = service.create_proposal(
        created["id"],
        command="Please clean formatting",
        base_version=1,
    )
    approved = service.decide_proposal(proposal["id"], decision="approve", note="Apply")
    assert approved["status"] == "approved"
    assert approved["document"]["currentVersion"] == 3
    assert "\n\n\n" not in approved["document"]["content"]

    rolled_back = service.rollback_proposal(proposal["id"], confirmed=True)
    assert rolled_back["status"] == "rolled_back"
    assert rolled_back["document"]["content"] == "Line with space.   \n\n\n\nSecond line."

    con = sqlite3.connect(database)
    try:
        source = con.execute(
            "SELECT title,path,sha256,authority_state FROM artifacts WHERE id='protected-source'"
        ).fetchone()
    finally:
        con.close()
    assert source == ("Protected source", "sources/original.txt", "a" * 64, "SOURCE")


def test_findings_only_actions_never_mutate_content(
    write_service: tuple[WriteRoom, Path, Path],
) -> None:
    service, _, _ = write_service
    text = "Repeat this complete paragraph.\n\nRepeat this complete paragraph."
    created = service.create_document("daily-writing", "Inspection", text)
    proposal = service.create_proposal(
        created["id"],
        command="Find repeated passages",
        base_version=1,
    )
    assert proposal["action"] == "repeated_passages"
    assert proposal["modifiesContent"] is False
    assert proposal["comparison"]["changed"] is False
    assert "positions 1, 2" in proposal["findings"][0]["message"]

    approved = service.decide_proposal(proposal["id"], decision="approve")
    assert approved["appliedVersionId"] is None
    reopened = service.get_document(created["id"])
    assert reopened["currentVersion"] == 1
    assert reopened["content"] == text

    with pytest.raises(WriteRoomError) as unsupported:
        service.create_proposal(
            created["id"],
            command="Publish this on the internet",
            base_version=1,
        )
    assert unsupported.value.code == "write_command_unsupported"


def test_export_filename_is_windows_safe(write_service: tuple[WriteRoom, Path, Path]) -> None:
    service, _, _ = write_service
    created = service.create_document(
        "daily-writing",
        'A: title? with <unsafe> "characters" / and \\ separators',
        "Exact export text.",
    )
    exported = service.export_document(created["id"], format_name="txt")
    assert not any(character in exported["filename"] for character in '<>:"/\\|?*')
    assert Path(exported["path"]).read_text(encoding="utf-8") == "Exact export text."
    assert len(str(Path(exported["path"]))) <= 240

    second = service.export_document(created["id"], format_name="txt")
    assert second["path"] != exported["path"]
    assert Path(second["path"]).read_text(encoding="utf-8") == "Exact export text."
