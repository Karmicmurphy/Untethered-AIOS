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
    data: dict | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict]:
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


def raw_request(
    base_url: str,
    path: str,
    method: str,
    body: bytes,
    headers: dict[str, str],
) -> tuple[int, dict]:
    value = urllib.request.Request(
        base_url + path,
        data=body,
        method=method,
        headers=headers,
    )
    try:
        with urllib.request.urlopen(value, timeout=15) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


@pytest.fixture()
def write_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
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
    server.upsert_project(con, "daily-writing", "Daily Writing", "test", "write")
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


def test_http_daily_lifecycle_and_restart_visible_recovery(write_api) -> None:
    base_url, _ = write_api
    status, created = request(
        base_url,
        "/api/write-projects",
        "POST",
        {"projectId": "daily-writing", "title": "API draft", "content": "Alpha"},
    )
    assert status == 201
    artifact_id = created["id"]

    status, recovery = request(
        base_url,
        f"/api/write-projects/{artifact_id}/recovery",
        "POST",
        {
            "title": "API draft",
            "content": "Alpha\nRecovered",
            "baseVersion": 1,
        },
    )
    assert status == 200
    assert recovery["baseVersion"] == 1

    # A fresh HTTP read reconstructs the editor from durable state, as a process restart does.
    status, reopened = request(base_url, f"/api/write-projects/{artifact_id}")
    assert status == 200
    assert reopened["content"] == "Alpha"
    assert reopened["recovery"]["content"] == "Alpha\nRecovered"

    status, saved = request(
        base_url,
        f"/api/write-projects/{artifact_id}/save",
        "POST",
        {
            "title": "API draft",
            "content": "Alpha\nRecovered",
            "baseVersion": 1,
            "cause": "recovery",
        },
    )
    assert status == 200
    assert saved["currentVersion"] == 2
    assert saved["hasRecovery"] is False

    status, snapshot = request(
        base_url,
        f"/api/write-projects/{artifact_id}/snapshot",
        "POST",
        {
            "title": "API draft",
            "content": "Alpha\nRecovered\nSnapshot",
            "baseVersion": 2,
            "label": "API checkpoint",
        },
    )
    assert status == 200
    assert snapshot["currentVersion"] == 3

    status, compared = request(
        base_url,
        f"/api/write-projects/{artifact_id}/compare?left=1&right=3",
    )
    assert status == 200
    assert compared["comparison"]["changed"] is True


def test_http_security_conflict_and_explicit_proposal_gate(write_api) -> None:
    base_url, _ = write_api
    _, created = request(
        base_url,
        "/api/write-projects",
        "POST",
        {"projectId": "daily-writing", "title": "Gate", "content": "Line.   \n\n\n\nNext."},
    )
    artifact_id = created["id"]

    status, cross_site = request(
        base_url,
        f"/api/write-projects/{artifact_id}/recovery",
        "POST",
        {"title": "Gate", "content": "x", "baseVersion": 1},
        headers={"Sec-Fetch-Site": "cross-site"},
    )
    assert status == 400
    assert cross_site["code"] == "cross_site_request_denied"

    status, proposal = request(
        base_url,
        f"/api/write-projects/{artifact_id}/proposals",
        "POST",
        {"action": "clean_formatting", "baseVersion": 1},
    )
    assert status == 200
    assert proposal["status"] == "awaiting_approval"

    _, unchanged = request(base_url, f"/api/write-projects/{artifact_id}")
    assert unchanged["currentVersion"] == 1
    assert unchanged["content"].endswith("Next.")

    status, approved = request(
        base_url,
        f"/api/write-proposals/{proposal['id']}/decision",
        "POST",
        {"decision": "approve", "note": "Explicit API approval"},
    )
    assert status == 200
    assert approved["document"]["currentVersion"] == 3

    status, stale = request(
        base_url,
        f"/api/write-projects/{artifact_id}/save",
        "POST",
        {"title": "Gate", "content": "stale", "baseVersion": 1, "cause": "manual"},
    )
    assert status == 409
    assert stale["code"] == "write_version_conflict"

    status, rolled_back = request(
        base_url,
        f"/api/write-proposals/{proposal['id']}/rollback",
        "POST",
        {"confirmed": True},
    )
    assert status == 200
    assert rolled_back["status"] == "rolled_back"
    assert rolled_back["document"]["content"].endswith("Next.")


def test_threaded_recovery_writes_are_serialized_and_database_remains_sound(write_api) -> None:
    base_url, database = write_api
    _, created = request(
        base_url,
        "/api/write-projects",
        "POST",
        {"projectId": "daily-writing", "title": "Concurrent recovery", "content": ""},
    )
    artifact_id = created["id"]

    def write_recovery(index: int) -> int:
        status, _ = request(
            base_url,
            f"/api/write-projects/{artifact_id}/recovery",
            "POST",
            {
                "title": "Concurrent recovery",
                "content": f"Recovery {index}",
                "baseVersion": 1,
            },
        )
        return status

    with ThreadPoolExecutor(max_workers=8) as pool:
        statuses = list(pool.map(write_recovery, range(24)))
    assert statuses == [200] * 24

    con = sqlite3.connect(database)
    try:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute(
            "SELECT COUNT(*) FROM write_recovery_drafts WHERE artifact_id=?",
            (artifact_id,),
        ).fetchone()[0] == 1
    finally:
        con.close()


def test_near_simultaneous_saves_allow_one_version_and_reject_the_stale_peer(write_api) -> None:
    base_url, database = write_api
    _, created = request(
        base_url,
        "/api/write-projects",
        "POST",
        {"projectId": "daily-writing", "title": "Simultaneous saves", "content": "Base"},
    )
    artifact_id = created["id"]
    barrier = threading.Barrier(2)

    def save(content: str) -> tuple[int, dict]:
        barrier.wait(timeout=5)
        return request(
            base_url,
            f"/api/write-projects/{artifact_id}/save",
            "POST",
            {
                "title": "Simultaneous saves",
                "content": content,
                "baseVersion": 1,
                "cause": "manual",
            },
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(save, ("First contender", "Second contender")))
    assert sorted(status for status, _ in results) == [200, 409]
    conflict = next(value for status, value in results if status == 409)
    assert conflict["code"] == "write_version_conflict"
    _, current = request(base_url, f"/api/write-projects/{artifact_id}")
    assert current["currentVersion"] == 2
    assert current["content"] in {"First contender", "Second contender"}

    con = sqlite3.connect(database)
    try:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert con.execute(
            "SELECT COUNT(*) FROM write_versions WHERE artifact_id=?",
            (artifact_id,),
        ).fetchone()[0] == 2
    finally:
        con.close()


def test_malformed_requests_recovery_delete_security_and_safe_exports(write_api) -> None:
    base_url, database = write_api
    source_text = '<script>alert("source text only")</script>\n<img src=x onerror=alert(1)>'
    _, created = request(
        base_url,
        "/api/write-projects",
        "POST",
        {
            "projectId": "daily-writing",
            "title": '<b>Owner title</b> : "safe"',
            "content": source_text,
        },
    )
    artifact_id = created["id"]
    assert created["content"] == source_text

    status, invalid_type = raw_request(
        base_url,
        f"/api/write-projects/{artifact_id}/save",
        "POST",
        b"{}",
        {"Content-Type": "text/plain"},
    )
    assert status == 400
    assert invalid_type["code"] == "content_type_invalid"

    status, invalid_json = raw_request(
        base_url,
        f"/api/write-projects/{artifact_id}/save",
        "POST",
        b"{",
        {"Content-Type": "application/json"},
    )
    assert status == 400
    assert invalid_json["code"] == "request_json_invalid"

    _, recovery = request(
        base_url,
        f"/api/write-projects/{artifact_id}/recovery",
        "POST",
        {"title": "Recovery", "content": "keep this", "baseVersion": 1},
    )
    assert recovery["ok"] is True
    status, denied_delete = raw_request(
        base_url,
        f"/api/write-projects/{artifact_id}/recovery",
        "DELETE",
        b"{}",
        {
            "Content-Type": "application/json",
            "Sec-Fetch-Site": "cross-site",
        },
    )
    assert status == 400
    assert denied_delete["code"] == "cross_site_request_denied"
    _, reopened = request(base_url, f"/api/write-projects/{artifact_id}")
    assert reopened["hasRecovery"] is True

    _, default_export = request(
        base_url,
        f"/api/write-projects/{artifact_id}/exports",
        "POST",
        {"format": "json", "includeProvenance": False},
    )
    _, advanced_export = request(
        base_url,
        f"/api/write-projects/{artifact_id}/exports",
        "POST",
        {"format": "json", "includeProvenance": True},
    )
    default_value = json.loads(Path(default_export["path"]).read_text(encoding="utf-8"))
    advanced_value = json.loads(Path(advanced_export["path"]).read_text(encoding="utf-8"))
    assert set(default_value) == {"title", "content", "exportedAt"}
    assert default_value["content"] == source_text
    assert set(advanced_value["provenance"]) == {
        "artifactId",
        "projectId",
        "version",
        "contentSha256",
        "savedAt",
    }
    assert advanced_value["provenance"]["artifactId"] == artifact_id

    con = sqlite3.connect(database)
    try:
        assert con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        export_receipts = con.execute(
            "SELECT details FROM receipts WHERE action='write.export'"
        ).fetchall()
    finally:
        con.close()
    assert len(export_receipts) == 2
    recorded_hashes = {json.loads(row[0])["sha256"] for row in export_receipts}
    assert recorded_hashes == {default_export["sha256"], advanced_export["sha256"]}


def test_export_rejects_a_project_identifier_that_escapes_projects_root(write_api) -> None:
    base_url, database = write_api
    con = sqlite3.connect(database)
    try:
        con.execute(
            "INSERT INTO projects VALUES(?,?,?,?,?,?)",
            ("../../outside", "Unsafe legacy ID", "", "", "2026-07-23", "2026-07-23"),
        )
        con.commit()
    finally:
        con.close()
    _, created = request(
        base_url,
        "/api/write-projects",
        "POST",
        {"projectId": "../../outside", "title": "Blocked export", "content": "Text"},
    )
    status, blocked = request(
        base_url,
        f"/api/write-projects/{created['id']}/exports",
        "POST",
        {"format": "txt"},
    )
    assert status == 400
    assert blocked["code"] == "export_path_invalid"
