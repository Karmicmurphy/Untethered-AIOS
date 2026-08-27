from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import zipfile
from pathlib import Path

import pytest

from companion import server
from companion.flashriver_intake import stage_flashriver_package


pytestmark = pytest.mark.skipif(os.name != "nt", reason="Artifact root policy is Windows-specific")


def create_database(path: Path, rows: list[dict]) -> None:
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE artifacts(
              id TEXT PRIMARY KEY, project_id TEXT, kind TEXT, title TEXT, path TEXT,
              payload TEXT, authority_state TEXT, sha256 TEXT, created_at TEXT, updated_at TEXT
            );
            CREATE TABLE artifact_reviews(
              artifact_id TEXT PRIMARY KEY, project_id TEXT, status TEXT, notes TEXT,
              reviewed_at TEXT, updated_at TEXT
            );
            """
        )
        for row in rows:
            connection.execute(
                "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    row["id"], "project", row["kind"], row["title"], row["path"],
                    json.dumps(row.get("payload", {})), row["authority"], row["sha256"],
                    "2026-07-21T00:00:00Z", "2026-07-21T00:00:00Z",
                ),
            )


def test_private_artifact_is_rejected_without_opening_contents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    projects = tmp_path / "projects"
    docs = projects / "project" / "sources" / "flashriver" / "hash" / "docs"
    private_root = projects / "project" / "sources" / "flashriver" / "hash" / "private_source_artifacts"
    docs.mkdir(parents=True)
    private_root.mkdir()
    public = docs / "public.md"
    private = private_root / "private.zip"
    public.write_text("# Public\n", encoding="utf-8")
    private.write_bytes(b"PK\x03\x04PRIVATE-CONTENT-MUST-NOT-BE-OPENED")
    database = tmp_path / "workshop.sqlite3"
    create_database(
        database,
        [
            {
                "id": "public", "kind": "flashriver-core-doc", "title": "public.md",
                "path": "sources/flashriver/hash/docs/public.md", "payload": {}, "authority": "SOURCE",
                "sha256": hashlib.sha256(public.read_bytes()).hexdigest(),
            },
            {
                "id": "private", "kind": "flashriver-private-source", "title": "private.zip",
                "path": "sources/flashriver/hash/private_source_artifacts/private.zip",
                "payload": {"private": True}, "authority": "SOURCE_PRIVATE",
                "sha256": hashlib.sha256(private.read_bytes()).hexdigest(),
            },
        ],
    )
    monkeypatch.setattr(server, "PROJECTS", projects)
    monkeypatch.setattr(server, "DB", database)
    original_read_bytes = Path.read_bytes

    def guarded_read_bytes(path: Path) -> bytes:
        if path.resolve(strict=False) == private.resolve(strict=False):
            raise AssertionError("private artifact content was opened")
        return original_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", guarded_read_bytes)
    options = server.artifact_inspection_options()
    public_option = next(item for item in options if item["artifactId"] == "public")
    private_option = next(item for item in options if item["artifactId"] == "private")
    assert public_option["eligible"] is True
    assert private_option["eligible"] is False
    assert {"private_source", "outside_public_safe_roots", "unsupported_extension"}.issubset(private_option["blockedReasons"])


def test_binary_invalid_utf8_and_hash_mismatch_are_ineligible(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    projects = tmp_path / "projects"
    docs = projects / "project" / "sources" / "flashriver" / "hash" / "docs"
    docs.mkdir(parents=True)
    binary = docs / "binary.txt"
    invalid = docs / "invalid.txt"
    changed = docs / "changed.md"
    binary.write_bytes(b"text\x00binary")
    invalid.write_bytes(b"\xff\xfe")
    changed.write_text("current", encoding="utf-8")
    database = tmp_path / "workshop.sqlite3"
    create_database(
        database,
        [
            {"id": "binary", "kind": "flashriver-support-doc", "title": "binary.txt", "path": "sources/flashriver/hash/docs/binary.txt", "authority": "SOURCE", "sha256": hashlib.sha256(binary.read_bytes()).hexdigest()},
            {"id": "invalid", "kind": "flashriver-support-doc", "title": "invalid.txt", "path": "sources/flashriver/hash/docs/invalid.txt", "authority": "SOURCE", "sha256": hashlib.sha256(invalid.read_bytes()).hexdigest()},
            {"id": "changed", "kind": "flashriver-core-doc", "title": "changed.md", "path": "sources/flashriver/hash/docs/changed.md", "authority": "SOURCE", "sha256": "0" * 64},
        ],
    )
    monkeypatch.setattr(server, "PROJECTS", projects)
    monkeypatch.setattr(server, "DB", database)
    options = {item["artifactId"]: item for item in server.artifact_inspection_options()}
    assert "binary_content" in options["binary"]["blockedReasons"]
    assert "invalid_utf8" in options["invalid"]["blockedReasons"]
    assert "source_hash_mismatch" in options["changed"]["blockedReasons"]


def test_imported_public_document_hash_matches_materialized_file_and_is_eligible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "FLASHRIVER_SAMPLE.zip"
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("FLASHRIVER_SAMPLE/README.md", "# Public\n\nTwo lines.\n")
    projects = tmp_path / "projects"
    project_root = projects / "project"
    project_root.mkdir(parents=True)
    result = stage_flashriver_package(
        zip_path=package,
        project_id="project",
        project_root=project_root,
        archive_root=tmp_path / "archives",
        now="2026-07-21T00:00:00Z",
    )
    document = next(
        artifact
        for artifact in result["artifacts"]
        if artifact["kind"] == "flashriver-core-doc"
    )
    database = tmp_path / "workshop.sqlite3"
    create_database(
        database,
        [
            {
                "id": document["id"],
                "kind": document["kind"],
                "title": document["title"],
                "path": document["path"],
                "payload": document["payload"],
                "authority": document["authorityState"],
                "sha256": document["hash"],
            }
        ],
    )
    monkeypatch.setattr(server, "PROJECTS", projects)
    monkeypatch.setattr(server, "DB", database)

    [option] = server.artifact_inspection_options()
    materialized = project_root / document["path"]
    assert option["eligible"] is True
    assert option["blockedReasons"] == []
    assert option["sha256"] == hashlib.sha256(materialized.read_bytes()).hexdigest().upper()
