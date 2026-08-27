from __future__ import annotations

import json
import sqlite3
import sys
import threading
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "companion"))
import server  # noqa: E402


def request(
    base_url: str,
    path: str,
    method: str = "GET",
    data: dict | list | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict | list]:
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request_headers = {"Content-Type": "application/json"} if body is not None else {}
    request_headers.update(headers or {})
    value = urllib.request.Request(
        base_url + path,
        data=body,
        method=method,
        headers=request_headers,
    )
    try:
        with urllib.request.urlopen(value, timeout=15) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


@pytest.fixture()
def talk_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
    server.upsert_project(con, "daily-talk", "Daily Talk", "test", "talk")
    con.commit()
    con.close()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}", server.DB
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=5)


def test_http_full_talk_lifecycle_and_cleanup(talk_api) -> None:
    base_url, database = talk_api
    status, created = request(
        base_url,
        "/api/talk-sessions",
        "POST",
        {
            "projectId": "daily-talk",
            "title": "API Talk",
            "initialContent": "Alpha <script>not markup</script>",
        },
    )
    assert status == 201
    artifact_id = created["id"]
    entry_id = created["entries"][0]["id"]

    status, renamed = request(
        base_url,
        f"/api/talk-sessions/{artifact_id}/title",
        "POST",
        {"title": "API Talk Renamed", "baseVersion": 1},
    )
    assert status == 200
    assert renamed["title"] == "API Talk Renamed"
    assert renamed["currentVersion"] == 2

    status, recovery = request(
        base_url,
        f"/api/talk-sessions/{artifact_id}/recovery",
        "POST",
        {"content": "Recovered thought", "baseVersion": 2, "entryType": "idea"},
    )
    assert status == 200
    assert recovery["baseVersion"] == 2

    status, reopened = request(base_url, f"/api/talk-sessions/{artifact_id}")
    assert status == 200
    assert reopened["recovery"]["content"] == "Recovered thought"

    status, appended = request(
        base_url,
        f"/api/talk-sessions/{artifact_id}/entries",
        "POST",
        {
            "content": "Recovered thought",
            "title": "API Talk",
            "baseVersion": 2,
            "entryType": "idea",
            "source": "recovery",
        },
    )
    assert status == 200
    assert appended["currentVersion"] == 3
    second_id = appended["entries"][1]["id"]

    status, snapshot = request(
        base_url,
        f"/api/talk-sessions/{artifact_id}/snapshot",
        "POST",
        {"baseVersion": 3, "label": "API checkpoint"},
    )
    assert status == 200
    assert snapshot["currentVersion"] == 4

    status, compared = request(
        base_url,
        f"/api/talk-sessions/{artifact_id}/compare?left=1&right=4",
    )
    assert status == 200
    assert compared["comparison"]["addedEntries"] == 1

    status, marked = request(
        base_url,
        f"/api/talk-sessions/{artifact_id}/passages",
        "POST",
        {
            "entryId": second_id,
            "startOffset": 0,
            "endOffset": 9,
            "label": "Keep",
        },
    )
    assert status == 200
    assert marked["quote"] == "Recovered"

    status, inspected = request(
        base_url,
        f"/api/talk-sessions/{artifact_id}/inspections",
        "POST",
        {"entryId": entry_id, "filename": "literal.html"},
    )
    assert status == 200
    assert inspected["result"]["sourceExecuted"] is False
    assert inspected["result"]["networkUsed"] is False

    status, transfer = request(
        base_url,
        f"/api/talk-sessions/{artifact_id}/transfers",
        "POST",
        {
            "baseVersion": 4,
            "selection": {"mode": "entries", "entryIds": [second_id]},
            "title": "API Write",
        },
    )
    assert status == 200
    assert transfer["status"] == "awaiting_approval"

    status, blank = request(
        base_url,
        f"/api/talk-transfers/{transfer['id']}/decision",
        "POST",
        {"decision": "approve", "note": " "},
    )
    assert status == 400
    assert blank["code"] == "talk_transfer_approval_note_required"

    status, approved = request(
        base_url,
        f"/api/talk-transfers/{transfer['id']}/decision",
        "POST",
        {"decision": "approve", "note": "Release 0.7 API verification"},
    )
    assert status == 200
    write_id = approved["writeArtifactId"]
    status, write = request(base_url, f"/api/write-projects/{write_id}")
    assert status == 200
    assert write["content"] == "Owner: Recovered thought"

    status, rolled_back = request(
        base_url,
        f"/api/talk-transfers/{transfer['id']}/rollback",
        "POST",
        {"confirmed": True},
    )
    assert status == 200
    assert rolled_back["status"] == "rolled_back"
    status, _ = request(base_url, f"/api/write-projects/{write_id}")
    assert status == 404

    status, voice = request(base_url, "/api/talk/voice-capabilities")
    assert status == 200
    assert voice["networkSpeechRecognitionEnabled"] is False
    assert voice["rawAudioRetained"] is False

    con = sqlite3.connect(database)
    try:
        assert con.execute("PRAGMA user_version").fetchone()[0] == 13
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        assert con.execute(
            "SELECT COUNT(*) FROM artifacts WHERE id=?", (artifact_id,)
        ).fetchone()[0] == 1
        assert con.execute(
            "SELECT COUNT(*) FROM artifacts WHERE id=?", (write_id,)
        ).fetchone()[0] == 0
    finally:
        con.close()


def test_http_security_content_validation_and_stale_gate(talk_api) -> None:
    base_url, _ = talk_api
    _, created = request(
        base_url,
        "/api/talk-sessions",
        "POST",
        {"projectId": "daily-talk", "title": "Security", "initialContent": "One"},
    )
    artifact_id = created["id"]

    status, cross_site = request(
        base_url,
        f"/api/talk-sessions/{artifact_id}/entries",
        "POST",
        {"content": "Blocked", "baseVersion": 1},
        headers={"Sec-Fetch-Site": "cross-site"},
    )
    assert status == 400
    assert cross_site["code"] == "cross_site_request_denied"

    raw = urllib.request.Request(
        base_url + f"/api/talk-sessions/{artifact_id}/entries",
        data=b"not json",
        method="POST",
        headers={"Content-Type": "text/plain"},
    )
    with pytest.raises(urllib.error.HTTPError) as content_error:
        urllib.request.urlopen(raw, timeout=15)
    assert content_error.value.code == 400

    status, not_object = request(
        base_url,
        f"/api/talk-sessions/{artifact_id}/entries",
        "POST",
        ["not", "an", "object"],
    )
    assert status == 400
    assert not_object["code"] == "request_json_invalid"

    status, current = request(
        base_url,
        f"/api/talk-sessions/{artifact_id}/entries",
        "POST",
        {"content": "Current", "baseVersion": 1},
    )
    assert status == 200
    status, stale = request(
        base_url,
        f"/api/talk-sessions/{artifact_id}/entries",
        "POST",
        {"content": "Stale", "baseVersion": 1},
    )
    assert status == 409
    assert stale["code"] == "talk_version_conflict"
    _, reopened = request(base_url, f"/api/talk-sessions/{artifact_id}")
    assert [entry["content"] for entry in reopened["entries"]] == ["One", "Current"]

    status, command = request(
        base_url,
        "/api/talk/commands",
        "POST",
        {"command": "Execute an unrestricted shell"},
    )
    assert status == 200
    assert command["supported"] is False
    assert command["automaticExecution"] is False
    assert command["shell"] is False
    assert command["network"] is False


def test_http_concurrent_recovery_and_append_are_serialized(talk_api) -> None:
    base_url, database = talk_api
    _, created = request(
        base_url,
        "/api/talk-sessions",
        "POST",
        {"projectId": "daily-talk", "title": "Concurrency"},
    )
    artifact_id = created["id"]

    def recovery(index: int) -> int:
        status, _ = request(
            base_url,
            f"/api/talk-sessions/{artifact_id}/recovery",
            "POST",
            {"content": f"Recovery {index}", "baseVersion": 1},
        )
        return status

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(recovery, range(20)))
    assert statuses == [200] * 20

    barrier = threading.Barrier(2)

    def append(content: str) -> tuple[int, dict | list]:
        barrier.wait(timeout=5)
        return request(
            base_url,
            f"/api/talk-sessions/{artifact_id}/entries",
            "POST",
            {"content": content, "baseVersion": 1},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(append, ["First contender", "Second contender"]))
    assert sorted(status for status, _ in results) == [200, 409]

    con = sqlite3.connect(database)
    try:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute(
            "SELECT COUNT(*) FROM talk_recovery_drafts WHERE artifact_id=?",
            (artifact_id,),
        ).fetchone()[0] == 0
        assert con.execute(
            "SELECT COUNT(*) FROM talk_entries WHERE artifact_id=?",
            (artifact_id,),
        ).fetchone()[0] == 1
    finally:
        con.close()
