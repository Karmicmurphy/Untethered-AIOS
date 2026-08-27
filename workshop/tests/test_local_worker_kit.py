from __future__ import annotations

import hashlib
import io
import json
import sqlite3
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from companion.local_worker_kit import (
    WORKER_IDS,
    LocalWorkerError,
    LocalWorkerKit,
)


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
CREATE TABLE jobs(
  id TEXT PRIMARY KEY, project_id TEXT NOT NULL, operation TEXT NOT NULL,
  status TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}', result TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
"""


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


@pytest.fixture()
def worker_service(
    tmp_path: Path,
) -> tuple[LocalWorkerKit, Path, Path, callable]:
    database = tmp_path / "data" / "workshop.sqlite3"
    projects = tmp_path / "data" / "projects"
    source_root = projects / "daily" / "sources"
    source_root.mkdir(parents=True)

    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(database, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    connection = connect()
    connection.executescript(BASE_SCHEMA)
    now = "2026-07-26T00:00:00+00:00"
    connection.execute(
        "INSERT INTO projects VALUES(?,?,?,?,?,?)",
        ("daily", "Daily work", "", "", now, now),
    )

    def register(
        artifact_id: str,
        title: str,
        relative_path: str,
        raw: bytes,
        *,
        kind: str = "source",
    ) -> Path:
        path = projects / "daily" / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        connection.execute(
            "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                artifact_id,
                "daily",
                kind,
                title,
                relative_path,
                "{}",
                "SOURCE",
                digest(raw),
                now,
                now,
            ),
        )
        connection.execute(
            "INSERT INTO artifact_search VALUES(?,?,?,?,?)",
            (artifact_id, "daily", title, kind, title),
        )
        return path

    register(
        "text-source",
        "Approved notes.txt",
        "sources/approved.txt",
        b"First line.\nSecond line.\n",
    )
    register(
        "code-source",
        "example.py",
        "sources/example.py",
        b"import pathlib\n\nclass Example:\n    pass\n\ndef build():\n    pass\n# TODO inspect\n",
    )
    package = io.BytesIO()
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("docs/readme.md", "hello")
        archive.writestr("src/app.py", "print('safe')\n")
    register(
        "package-source",
        "release.zip",
        "sources/release.zip",
        package.getvalue(),
    )
    unsafe_package = io.BytesIO()
    with zipfile.ZipFile(unsafe_package, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("../escape.txt", "blocked")
    register(
        "unsafe-package",
        "unsafe.zip",
        "sources/unsafe.zip",
        unsafe_package.getvalue(),
    )
    manifest = {
        "packageMembers": {
            "docs/readme.md": {"sha256": digest(b"hello")},
            "src/app.py": {"sha256": digest(b"print('safe')\n")},
        }
    }
    register(
        "manifest-source",
        "manifest.json",
        "sources/manifest.json",
        json.dumps(manifest).encode(),
    )
    connection.commit()
    connection.close()
    return LocalWorkerKit(connect, projects), database, projects, connect


def approved_plan(
    service: LocalWorkerKit,
    worker_id: str,
    artifact_id: str,
    **extra: object,
) -> dict[str, object]:
    plan = service.create_plan(
        {
            "projectId": "daily",
            "workerId": worker_id,
            "sourceArtifactId": artifact_id,
            "actor": "test-owner",
            **extra,
        }
    )
    return service.decide_plan(
        plan["jobId"],
        "approve",
        "Approved for bounded test",
        actor="test-owner",
    )


def test_fixed_contracts_are_complete_and_deny_unsafe_capabilities(
    worker_service: tuple[LocalWorkerKit, Path, Path, callable],
) -> None:
    service, _, _, _ = worker_service
    workers = service.list_workers()
    assert tuple(worker["workerId"] for worker in workers) == WORKER_IDS
    assert all(worker["network"] == "denied" for worker in workers)
    assert all(worker["approvalRequired"] is True for worker in workers)
    for worker_id in WORKER_IDS:
        contract = service.inspect_worker(worker_id)
        assert contract["valid"] is True
        assert contract["implementationHash"] == service.implementation_hash
        assert contract["networkPolicy"] == (
            "loopback-127.0.0.1-only; external denied"
            if worker_id == "local-ai-rewrite"
            else "denied"
        )
        assert {
            "shell",
            "arbitrary-filesystem",
            "attachment",
            "activation",
            "module-promotion",
        }.issubset(contract["prohibitedPermissions"])
    with pytest.raises(LocalWorkerError, match="fixed local allowlist") as error:
        service.inspect_worker("../../shell")
    assert error.value.code == "worker_not_supported"


def test_text_reader_requires_plan_and_result_approval_and_preserves_source(
    worker_service: tuple[LocalWorkerKit, Path, Path, callable],
) -> None:
    service, database, projects, _ = worker_service
    source = projects / "daily" / "sources" / "approved.txt"
    before = digest(source.read_bytes())
    plan = service.create_plan(
        {
            "projectId": "daily",
            "workerId": "approved-text-reader",
            "sourceArtifactId": "text-source",
        }
    )
    assert plan["status"] == "planned"
    with pytest.raises(LocalWorkerError) as blank:
        service.decide_plan(plan["jobId"], "approve", " ", actor="test-owner")
    assert blank.value.code == "approval_note_required"
    with pytest.raises(LocalWorkerError) as unapproved:
        service.execute(plan["jobId"], actor="test-owner")
    assert unapproved.value.code == "job_not_executable"

    service.decide_plan(
        plan["jobId"], "approve", "Read only", actor="test-owner"
    )
    result = service.execute(plan["jobId"], actor="test-owner")
    assert result["status"] == "awaiting_result_approval"
    assert result["result"]["output"]["content"] == "First line.\nSecond line.\n"
    assert result["result"]["validation"]["valid"] is True
    assert result["result"]["accepted"] is False
    assert result["attachmentStatus"] == "unattached"
    assert digest(source.read_bytes()) == before
    with pytest.raises(LocalWorkerError) as blank_result:
        service.decide_result(
            plan["jobId"], "approve", "", actor="test-owner"
        )
    assert blank_result.value.code == "approval_note_required"
    accepted = service.decide_result(
        plan["jobId"],
        "approve",
        "Facts reviewed",
        actor="test-owner",
    )
    assert accepted["status"] == "result_approved"
    assert accepted["activationStatus"] == "inactive"
    assert accepted["actions"]["rollback"] is False
    assert digest(source.read_bytes()) == before

    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT COUNT(*) FROM artifacts WHERE id='text-source'"
    ).fetchone()[0] == 1
    assert connection.execute(
        "SELECT COUNT(*) FROM receipts WHERE action LIKE 'local_worker.%'"
    ).fetchone()[0] >= 4
    connection.close()


def test_code_inspector_reports_facts_and_labeled_heuristics_without_execution(
    worker_service: tuple[LocalWorkerKit, Path, Path, callable],
) -> None:
    service, _, _, _ = worker_service
    job = approved_plan(service, "code-structure-inspector", "code-source")
    complete = service.execute(job["jobId"], actor="test-owner")
    output = complete["result"]["output"]
    assert output["facts"]["functions"] == ["build"]
    assert output["facts"]["classes"] == ["Example"]
    assert output["heuristicFindings"]["probableType"] == "Python"
    assert output["sourceExecuted"] is False
    assert output["networkUsed"] is False
    rejected = service.decide_result(
        job["jobId"], "reject", "Not needed", actor="test-owner"
    )
    assert rejected["status"] == "result_rejected"


def test_note_proposal_is_created_only_after_approval_and_exactly_rolled_back(
    worker_service: tuple[LocalWorkerKit, Path, Path, callable],
) -> None:
    service, database, projects, _ = worker_service
    source = projects / "daily" / "sources" / "approved.txt"
    source_hash = digest(source.read_bytes())
    job = approved_plan(
        service,
        "note-proposal-worker",
        "text-source",
        selection="Second line.",
        title="<Owner note>",
    )
    proposed = service.execute(job["jobId"], actor="test-owner")
    assert proposed["result"]["output"]["content"] == "# <Owner note>\n\nSecond line.\n"
    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT COUNT(*) FROM artifacts WHERE kind='note'"
    ).fetchone()[0] == 0
    connection.close()

    accepted = service.decide_result(
        job["jobId"],
        "approve",
        "Create this note",
        actor="test-owner",
    )
    note_id = accepted["result"]["acceptance"]["noteArtifactId"]
    assert accepted["actions"]["rollback"] is True
    assert accepted["attachmentStatus"] == "unattached"
    connection = sqlite3.connect(database)
    note = connection.execute(
        "SELECT title,authority_state FROM artifacts WHERE id=?", (note_id,)
    ).fetchone()
    connection.close()
    assert note == ("<Owner note>", "DRAFT")
    assert digest(source.read_bytes()) == source_hash

    rolled = service.rollback(
        job["jobId"], confirmed=True, actor="test-owner"
    )
    assert rolled["status"] == "rolled_back"
    assert rolled["actions"]["rollback"] is False
    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT COUNT(*) FROM artifacts WHERE id=?", (note_id,)
    ).fetchone()[0] == 0
    assert connection.execute(
        "SELECT COUNT(*) FROM receipts WHERE action='local_worker.note.rollback'"
    ).fetchone()[0] == 1
    connection.close()
    assert digest(source.read_bytes()) == source_hash


def test_note_rejection_creates_nothing(
    worker_service: tuple[LocalWorkerKit, Path, Path, callable],
) -> None:
    service, database, _, _ = worker_service
    job = approved_plan(
        service,
        "note-proposal-worker",
        "text-source",
        selection="First line.",
    )
    service.execute(job["jobId"], actor="test-owner")
    rejected = service.decide_result(
        job["jobId"], "reject", "Skip it", actor="test-owner"
    )
    assert rejected["status"] == "result_rejected"
    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT COUNT(*) FROM artifacts WHERE kind='note'"
    ).fetchone()[0] == 0
    connection.close()


def test_package_validator_reports_exact_safe_members_and_rejects_unexpected(
    worker_service: tuple[LocalWorkerKit, Path, Path, callable],
) -> None:
    service, _, _, _ = worker_service
    expected_hashes = {
        "docs/readme.md": digest(b"hello"),
        "src/app.py": digest(b"print('safe')\n"),
    }
    job = approved_plan(
        service,
        "package-manifest-validator",
        "package-source",
        expectedMembers=["docs/readme.md", "src/app.py"],
        expectedHashes=expected_hashes,
    )
    complete = service.execute(job["jobId"], actor="test-owner")
    output = complete["result"]["output"]
    assert output["validationPassed"] is True
    assert output["missingMembers"] == []
    assert output["unexpectedMembers"] == []
    assert output["hashMismatches"] == []
    assert output["installed"] is False
    assert output["executed"] is False

    extra_job = approved_plan(
        service,
        "package-manifest-validator",
        "package-source",
        expectedMembers=["docs/readme.md"],
    )
    extra = service.execute(extra_job["jobId"], actor="test-owner")
    assert extra["result"]["output"]["unexpectedMembers"] == ["src/app.py"]
    assert extra["result"]["output"]["validationPassed"] is False


def test_package_validator_reports_unsafe_paths_without_extracting(
    worker_service: tuple[LocalWorkerKit, Path, Path, callable],
) -> None:
    service, _, projects, _ = worker_service
    escape = projects / "daily" / "escape.txt"
    job = approved_plan(
        service,
        "package-manifest-validator",
        "unsafe-package",
        expectedMembers=["safe.txt"],
    )
    complete = service.execute(job["jobId"], actor="test-owner")
    output = complete["result"]["output"]
    assert output["validationPassed"] is False
    assert output["unsafeMembers"] == ["../escape.txt"]
    assert output["imported"] is False
    assert output["activated"] is False
    assert escape.exists() is False


def test_stale_plan_duplicate_execution_expiration_and_timeout_fail_closed(
    worker_service: tuple[LocalWorkerKit, Path, Path, callable],
) -> None:
    service, database, projects, _ = worker_service
    stale = approved_plan(service, "approved-text-reader", "text-source")
    source = projects / "daily" / "sources" / "approved.txt"
    source.write_text("Changed after approval.", encoding="utf-8")
    with pytest.raises(LocalWorkerError) as error:
        service.execute(stale["jobId"], actor="test-owner")
    assert error.value.code == "stale_plan"
    assert service.get_job(stale["jobId"])["status"] == "stale"

    source.write_bytes(b"First line.\nSecond line.\n")
    duplicate = approved_plan(service, "approved-text-reader", "text-source")
    connection = sqlite3.connect(database)
    connection.execute(
        "UPDATE jobs SET status='running' WHERE id=?", (duplicate["jobId"],)
    )
    connection.commit()
    connection.close()
    with pytest.raises(LocalWorkerError) as duplicate_error:
        service.execute(duplicate["jobId"], actor="test-owner")
    assert duplicate_error.value.code == "duplicate_execution"

    expired = approved_plan(service, "approved-text-reader", "text-source")
    connection = sqlite3.connect(database)
    payload = json.loads(
        connection.execute(
            "SELECT payload FROM jobs WHERE id=?", (expired["jobId"],)
        ).fetchone()[0]
    )
    payload["expiresAt"] = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
    ).isoformat()
    connection.execute(
        "UPDATE jobs SET payload=? WHERE id=?",
        (json.dumps(payload), expired["jobId"]),
    )
    connection.commit()
    connection.close()
    with pytest.raises(LocalWorkerError) as expired_error:
        service.execute(expired["jobId"], actor="test-owner")
    assert expired_error.value.code == "plan_abandoned"
    assert service.get_job(expired["jobId"])["status"] == "abandoned"

    timed = approved_plan(service, "approved-text-reader", "text-source")
    ticks = iter((0.0, 3.0))
    service._clock = lambda: next(ticks)
    with pytest.raises(LocalWorkerError) as timeout:
        service.execute(timed["jobId"], actor="test-owner")
    assert timeout.value.code == "worker_timeout"
    failed = service.get_job(timed["jobId"])
    assert failed["status"] == "failed"
    assert failed["result"]["accepted"] is False


def test_restart_recovery_is_safe_idempotent_and_never_accepts_output(
    worker_service: tuple[LocalWorkerKit, Path, Path, callable],
) -> None:
    service, database, _, connect = worker_service
    job = approved_plan(service, "approved-text-reader", "text-source")
    connection = sqlite3.connect(database)
    connection.execute(
        "UPDATE jobs SET status='running' WHERE id=?", (job["jobId"],)
    )
    connection.commit()
    connection.close()

    restarted = LocalWorkerKit(connect, service.projects_root)
    assert restarted.recover_interrupted_on_startup() == 1
    interrupted = restarted.get_job(job["jobId"])
    assert interrupted["status"] == "interrupted"
    assert interrupted["result"]["interruption"]["accepted"] is False
    recovered = restarted.recover(job["jobId"], actor="test-owner")
    assert recovered["status"] == "plan_approved"
    repeated = restarted.recover(job["jobId"], actor="test-owner")
    assert repeated["idempotent"] is True
    assert restarted.recover_interrupted_on_startup() == 0


def test_cancellation_and_terminal_cleanup_preserve_receipts(
    worker_service: tuple[LocalWorkerKit, Path, Path, callable],
) -> None:
    service, database, _, _ = worker_service
    plan = service.create_plan(
        {
            "projectId": "daily",
            "workerId": "approved-text-reader",
            "sourceArtifactId": "text-source",
        }
    )
    cancelled = service.cancel(plan["jobId"], actor="test-owner")
    assert cancelled["status"] == "cancelled"
    connection = sqlite3.connect(database)
    receipts_before = connection.execute(
        "SELECT COUNT(*) FROM receipts"
    ).fetchone()[0]
    connection.close()
    cleaned = service.delete_history(
        plan["jobId"], confirmed=True, actor="test-owner"
    )
    assert cleaned == {
        "ok": True,
        "jobHistoryRemoved": True,
        "receiptsPreserved": True,
    }
    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT COUNT(*) FROM jobs WHERE id=?", (plan["jobId"],)
    ).fetchone()[0] == 0
    assert connection.execute(
        "SELECT COUNT(*) FROM receipts"
    ).fetchone()[0] == receipts_before + 1
    connection.close()


def test_request_shapes_paths_selection_and_sizes_are_bounded(
    worker_service: tuple[LocalWorkerKit, Path, Path, callable],
) -> None:
    service, database, projects, _ = worker_service
    with pytest.raises(LocalWorkerError) as fields:
        service.create_plan(
            {
                "projectId": "daily",
                "workerId": "approved-text-reader",
                "sourceArtifactId": "text-source",
                "command": "whoami",
            }
        )
    assert fields.value.code == "request_fields_invalid"
    with pytest.raises(LocalWorkerError) as selection:
        service.create_plan(
            {
                "projectId": "daily",
                "workerId": "note-proposal-worker",
                "sourceArtifactId": "text-source",
                "selection": "not in the source",
            }
        )
    assert selection.value.code == "selection_not_in_source"

    connection = sqlite3.connect(database)
    connection.execute(
        "INSERT INTO projects VALUES(?,?,?,?,?,?)",
        (
            "../escaped",
            "Malformed project",
            "",
            "",
            "2026-07-26T00:00:00+00:00",
            "2026-07-26T00:00:00+00:00",
        ),
    )
    connection.execute(
        "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            "project-escape-source",
            "../escaped",
            "source",
            "outside.txt",
            "outside.txt",
            "{}",
            "SOURCE",
            "A" * 64,
            "2026-07-26T00:00:00+00:00",
            "2026-07-26T00:00:00+00:00",
        ),
    )
    connection.execute(
        "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            "escape-source",
            "daily",
            "source",
            "escape.txt",
            "../outside.txt",
            "{}",
            "SOURCE",
            "A" * 64,
            "2026-07-26T00:00:00+00:00",
            "2026-07-26T00:00:00+00:00",
        ),
    )
    oversized = b"x" * (512 * 1024 + 1)
    path = projects / "daily" / "sources" / "oversized.txt"
    path.write_bytes(oversized)
    connection.execute(
        "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            "oversized-source",
            "daily",
            "source",
            "oversized.txt",
            "sources/oversized.txt",
            "{}",
            "SOURCE",
            digest(oversized),
            "2026-07-26T00:00:00+00:00",
            "2026-07-26T00:00:00+00:00",
        ),
    )
    connection.commit()
    connection.close()

    with pytest.raises(LocalWorkerError) as escape:
        service.create_plan(
            {
                "projectId": "daily",
                "workerId": "approved-text-reader",
                "sourceArtifactId": "escape-source",
            }
        )
    assert escape.value.code == "source_path_invalid"
    with pytest.raises(LocalWorkerError) as project_escape:
        service.create_plan(
            {
                "projectId": "../escaped",
                "workerId": "approved-text-reader",
                "sourceArtifactId": "project-escape-source",
            }
        )
    assert project_escape.value.code == "source_project_path_invalid"
    with pytest.raises(LocalWorkerError) as too_large:
        service.create_plan(
            {
                "projectId": "daily",
                "workerId": "approved-text-reader",
                "sourceArtifactId": "oversized-source",
            }
        )
    assert too_large.value.code == "source_too_large"
