from __future__ import annotations

import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "companion"))
import server  # noqa: E402


def request_json(base_url: str, path: str, method: str = "GET", data: dict | None = None) -> dict:
    body = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    request = urllib.request.Request(base_url + path, data=body, method=method, headers=headers)
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


@pytest.fixture()
def review_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "data"
    projects_dir = data_dir / "projects"
    monkeypatch.setattr(server, "DATA", data_dir)
    monkeypatch.setattr(server, "DB", data_dir / "workshop.sqlite3")
    monkeypatch.setattr(server, "PROJECTS", projects_dir)
    monkeypatch.setattr(server, "IMPORTS", data_dir / "imports")
    monkeypatch.setattr(server, "BACKUPS", data_dir / "backups")
    monkeypatch.setattr(server, "SOURCE_ARCHIVES", data_dir / "source_archives")
    for directory in (projects_dir, server.IMPORTS, server.BACKUPS, server.SOURCE_ARCHIVES):
        directory.mkdir(parents=True, exist_ok=True)

    con = server.connect()
    server.upsert_project(con, "flashriver-source-archive", "FlashRiver Source Archive", "test", "review")
    now = "2026-07-16T00:00:00+00:00"
    for artifact_id, title, source_path, digest in (
        ("duplicate-one", "ONE.md", "FLASHRIVER/ONE.md", "a" * 64),
        ("duplicate-two", "TWO.md", "FLASHRIVER/nested/TWO.md", "a" * 64),
        ("singleton", "THREE.md", "FLASHRIVER/THREE.md", "b" * 64),
    ):
        server.save_artifact_row(con, {
            "id": artifact_id,
            "projectId": "flashriver-source-archive",
            "kind": "flashriver-core-doc",
            "title": title,
            "path": f"sources/{title}",
            "payload": {"archiveMember": source_path, "contentPreview": title},
            "authorityState": "SOURCE",
            "hash": digest,
            "createdAt": now,
            "updatedAt": now,
        })
    con.commit()
    con.close()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_review_status_and_note_persist_across_reload(review_api: str) -> None:
    saved = request_json(review_api, "/api/artifacts/duplicate-one/review", "POST", {
        "status": "current_candidate",
        "notes": "Keep this note after refresh.",
    })
    assert saved["status"] == "current_candidate"
    assert saved["notes"] == "Keep this note after refresh."

    for _ in range(2):
        refreshed = request_json(review_api, "/api/projects/flashriver-source-archive/flashriver-review")
        artifact = next(item for item in refreshed["artifacts"] if item["id"] == "duplicate-one")
        assert artifact["review_status"] == "current_candidate"
        assert artifact["review_notes"] == "Keep this note after refresh."


def test_exact_hash_duplicates_group_all_records_and_source_paths(review_api: str) -> None:
    refreshed = request_json(review_api, "/api/projects/flashriver-source-archive/flashriver-review")
    assert len(refreshed["artifacts"]) == 3
    assert len(refreshed["duplicateGroups"]) == 1
    duplicate = refreshed["duplicateGroups"][0]
    assert duplicate["sha256"] == "a" * 64
    assert duplicate["count"] == 2
    assert {member["artifactId"] for member in duplicate["members"]} == {"duplicate-one", "duplicate-two"}
    assert {member["sourcePath"] for member in duplicate["members"]} == {
        "FLASHRIVER/ONE.md",
        "FLASHRIVER/nested/TWO.md",
    }
