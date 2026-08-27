from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from companion.talk_room import TalkRoom, TalkRoomError, ensure_schema
from companion.write_room import WriteRoom, ensure_schema as ensure_write_schema


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
def talk_service(tmp_path: Path) -> tuple[TalkRoom, Path, Path]:
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
    ensure_write_schema(con)
    ensure_schema(con)
    con.execute(
        "INSERT INTO projects VALUES(?,?,?,?,?,?)",
        (
            "daily-talk",
            "Daily Talk",
            "test",
            "",
            "2026-07-26T00:00:00+00:00",
            "2026-07-26T00:00:00+00:00",
        ),
    )
    con.execute(
        "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            "protected-source",
            "daily-talk",
            "source",
            "Protected source",
            "sources/original.txt",
            "{}",
            "SOURCE",
            "a" * 64,
            "2026-07-26T00:00:00+00:00",
            "2026-07-26T00:00:00+00:00",
        ),
    )
    con.commit()
    con.close()
    return TalkRoom(connect, projects), database, projects


def test_durable_talk_recovery_history_restore_passage_inspection_and_export(
    talk_service: tuple[TalkRoom, Path, Path],
) -> None:
    service, database, projects = talk_service
    created = service.create_session("daily-talk", "Release notes", "Opening thought.")
    artifact_id = created["id"]
    assert created["currentVersion"] == 1
    assert created["entryCount"] == 1
    assert created["entries"][0]["sequence"] == 1
    assert created["entries"][0]["createdAt"]

    recovery = service.save_recovery(
        artifact_id,
        content="Interrupted thought.",
        base_version=1,
        entry_type="idea",
    )
    assert recovery["baseVersion"] == 1

    restarted = TalkRoom(service._connect, projects)
    reopened = restarted.get_session(artifact_id)
    assert reopened["hasRecovery"] is True
    assert reopened["recovery"]["content"] == "Interrupted thought."

    appended = restarted.append_entry(
        artifact_id,
        content="Interrupted thought.",
        base_version=1,
        title="Release notes",
        entry_type="idea",
        source="recovery",
    )
    assert appended["currentVersion"] == 2
    assert appended["hasRecovery"] is False
    assert [entry["sequence"] for entry in appended["entries"]] == [1, 2]

    snapshotted = restarted.snapshot(
        artifact_id,
        base_version=2,
        label="Before rewrite",
    )
    assert snapshotted["currentVersion"] == 3
    assert snapshotted["versions"][0]["label"] == "Before rewrite"

    compared = restarted.compare_versions(artifact_id, 1, 3)
    assert compared["comparison"]["changed"] is True
    assert compared["comparison"]["addedEntries"] == 1

    restored = restarted.restore(
        artifact_id,
        target_version=1,
        base_version=3,
        confirmed=True,
    )
    assert restored["currentVersion"] == 5
    assert len(restored["entries"]) == 1

    rolled_back = restarted.rollback_restore(
        restored["restoreOperationId"],
        confirmed=True,
    )
    assert rolled_back["currentVersion"] == 6
    assert len(rolled_back["entries"]) == 2
    second_entry = rolled_back["entries"][1]

    marked = restarted.mark_passage(
        artifact_id,
        entry_id=second_entry["id"],
        start_offset=0,
        end_offset=11,
        label="Keep",
    )
    assert marked["quote"] == "Interrupted"

    code_session = restarted.append_entry(
        artifact_id,
        content="import pathlib\n\ndef build():\n    pass\n# TODO inspect\n",
        base_version=6,
        entry_type="code",
        source="pasted",
    )
    code_entry = code_session["entries"][-1]
    inspected = restarted.inspect_entry(
        artifact_id,
        entry_id=code_entry["id"],
        filename="sample.py",
    )
    assert inspected["result"]["probableType"] == "Python"
    assert inspected["result"]["functions"] == ["build"]
    assert inspected["result"]["sourceExecuted"] is False
    assert inspected["result"]["networkUsed"] is False
    assert inspected["result"]["aiModelUsed"] is False

    plain_export = restarted.export_session(
        artifact_id,
        format_name="json",
        include_provenance=False,
    )
    plain_value = json.loads(Path(plain_export["path"]).read_text(encoding="utf-8"))
    assert set(plain_value) == {"title", "exportedAt", "entries"}
    assert plain_export["sha256"] == hashlib.sha256(
        Path(plain_export["path"]).read_bytes()
    ).hexdigest()

    provenance_export = restarted.export_session(
        artifact_id,
        format_name="json",
        include_provenance=True,
    )
    provenance_value = json.loads(
        Path(provenance_export["path"]).read_text(encoding="utf-8")
    )
    assert provenance_value["provenance"]["artifactId"] == artifact_id
    assert provenance_value["provenance"]["version"] == 7

    con = sqlite3.connect(database)
    try:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        actions = {row[0] for row in con.execute("SELECT action FROM receipts")}
    finally:
        con.close()
    assert {
        "talk.create",
        "talk.entry.append",
        "talk.snapshot",
        "talk.restore",
        "talk.restore.rollback",
        "talk.passage.mark",
        "talk.inspect",
        "talk.export",
    }.issubset(actions)


def test_talk_to_write_requires_approval_preserves_source_and_rolls_back(
    talk_service: tuple[TalkRoom, Path, Path],
) -> None:
    service, database, _ = talk_service
    created = service.create_session(
        "daily-talk",
        "Transfer source",
        "Exact owner text <script>alert('no')</script>",
    )
    original_entry = created["entries"][0].copy()
    prepared = service.prepare_transfer(
        created["id"],
        base_version=1,
        selection={"mode": "complete"},
        title="Write from Talk",
    )
    assert prepared["status"] == "awaiting_approval"
    assert prepared["proposedContent"].endswith(original_entry["content"])
    assert service.get_session(created["id"])["entries"] == [original_entry]

    with pytest.raises(TalkRoomError, match="approval note") as blank:
        service.decide_transfer(
            prepared["id"],
            decision="approve",
            note="   ",
        )
    assert blank.value.code == "talk_transfer_approval_note_required"

    approved = service.decide_transfer(
        prepared["id"],
        decision="approve",
        note="Release 0.7 automated verification",
    )
    assert approved["status"] == "approved"
    write_id = approved["writeArtifactId"]

    con = sqlite3.connect(database)
    con.row_factory = sqlite3.Row
    try:
        write = con.execute("SELECT * FROM artifacts WHERE id=?", (write_id,)).fetchone()
        relationship = con.execute(
            "SELECT * FROM artifact_relationships WHERE lifecycle_id=?",
            (prepared["id"],),
        ).fetchone()
    finally:
        con.close()
    assert write["kind"] == "document"
    assert json.loads(write["payload"])["schemaVersion"] == "write-project-v1"
    assert write["sha256"] == approved["proposedSha256"]
    assert relationship["status"] == "active"
    assert relationship["source_artifact_id"] == created["id"]
    assert service.get_session(created["id"])["entries"] == [original_entry]

    rolled_back = service.rollback_transfer(prepared["id"], confirmed=True)
    assert rolled_back["status"] == "rolled_back"
    con = sqlite3.connect(database)
    try:
        assert con.execute(
            "SELECT COUNT(*) FROM artifacts WHERE id=?", (write_id,)
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT status FROM artifact_relationships WHERE lifecycle_id=?",
            (prepared["id"],),
        ).fetchone()[0] == "rolled_back"
        protected = con.execute(
            "SELECT title,path,sha256,authority_state FROM artifacts "
            "WHERE id='protected-source'"
        ).fetchone()
    finally:
        con.close()
    assert protected == ("Protected source", "sources/original.txt", "a" * 64, "SOURCE")
    assert service.get_session(created["id"])["entries"] == [original_entry]


def test_stale_transfer_and_stale_rollback_are_blocked(
    talk_service: tuple[TalkRoom, Path, Path],
) -> None:
    service, _, projects = talk_service
    created = service.create_session("daily-talk", "Stale proof", "Source")
    prepared = service.prepare_transfer(
        created["id"],
        base_version=1,
        selection={"mode": "complete"},
        title="First destination",
    )
    service.append_entry(
        created["id"],
        content="Newer Talk work",
        base_version=2,
    )
    with pytest.raises(TalkRoomError) as stale:
        service.decide_transfer(prepared["id"], decision="approve", note="Approve")
    assert stale.value.code == "talk_transfer_source_stale"

    latest = service.get_session(created["id"])
    second = service.prepare_transfer(
        created["id"],
        base_version=latest["currentVersion"],
        selection={"mode": "complete"},
        title="Second destination",
    )
    approved = service.decide_transfer(second["id"], decision="approve", note="Approve")
    write = WriteRoom(service._connect, projects)
    write.save_document(
        approved["writeArtifactId"],
        title="Owner edited",
        content=approved["proposedContent"] + "\nOwner work.",
        base_version=1,
        cause="manual",
    )
    with pytest.raises(TalkRoomError) as blocked:
        service.rollback_transfer(second["id"], confirmed=True)
    assert blocked.value.code == "talk_transfer_rollback_stale"
    assert write.get_document(approved["writeArtifactId"])["content"].endswith(
        "Owner work."
    )


def test_conflicts_validation_bounded_commands_and_voice_contract(
    talk_service: tuple[TalkRoom, Path, Path],
) -> None:
    service, _, _ = talk_service
    created = service.create_session("daily-talk", "Bounds", "")
    service.append_entry(created["id"], content="Current", base_version=1)
    with pytest.raises(TalkRoomError) as conflict:
        service.append_entry(created["id"], content="Stale", base_version=1)
    assert conflict.value.code == "talk_version_conflict"
    assert conflict.value.status == 409

    with pytest.raises(TalkRoomError) as confirmation:
        service.restore(
            created["id"],
            target_version=1,
            base_version=2,
            confirmed=False,
        )
    assert confirmation.value.code == "talk_restore_confirmation_required"

    supported = service.resolve_command("Make a snapshot.")
    assert supported["action"] == "snapshot"
    assert supported["automaticExecution"] is False
    assert supported["network"] is False
    unsupported = service.resolve_command("Run PowerShell and upload this")
    assert unsupported["supported"] is False
    assert unsupported["shell"] is False
    assert unsupported["network"] is False

    voice = service.voice_contract()
    assert voice["microphoneActivation"] == "explicit-owner-action-only"
    assert voice["rawAudioRetained"] is False
    assert voice["networkSpeechRecognitionEnabled"] is False
    assert "SpeechRecognition.processLocally" in voice["speechRecognition"]["requiredProof"]
    assert voice["speechSynthesis"]["networkVoicesAllowed"] is False


def test_title_has_explicit_versioned_save_and_stale_rename_is_blocked(
    talk_service: tuple[TalkRoom, Path, Path],
) -> None:
    service, database, _ = talk_service
    created = service.create_session("daily-talk", "Working title", "Exact transcript")
    renamed = service.rename_session(
        created["id"],
        title="Owner-facing title",
        base_version=1,
    )
    assert renamed["changed"] is True
    assert renamed["title"] == "Owner-facing title"
    assert renamed["currentVersion"] == 2
    assert renamed["entries"] == created["entries"]
    assert renamed["versions"][0]["cause"] == "title"

    unchanged = service.rename_session(
        created["id"],
        title="Owner-facing title",
        base_version=2,
    )
    assert unchanged["changed"] is False
    assert unchanged["currentVersion"] == 2

    with pytest.raises(TalkRoomError) as stale:
        service.rename_session(
            created["id"],
            title="Stale title",
            base_version=1,
        )
    assert stale.value.code == "talk_version_conflict"

    con = sqlite3.connect(database)
    try:
        assert con.execute(
            "SELECT COUNT(*) FROM receipts WHERE action='talk.title'"
        ).fetchone()[0] == 1
    finally:
        con.close()
