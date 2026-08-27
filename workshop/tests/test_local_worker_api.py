from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "companion"))
import server  # noqa: E402


def api(
    base_url: str,
    path: str,
    method: str = "GET",
    data: dict | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict | list]:
    body = json.dumps(data).encode() if data is not None else None
    request_headers = {"Content-Type": "application/json"} if body is not None else {}
    request_headers.update(headers or {})
    request = urllib.request.Request(
        base_url + path,
        data=body,
        method=method,
        headers=request_headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read().decode())


@pytest.fixture()
def worker_api(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data = tmp_path / "data"
    projects = data / "projects"
    monkeypatch.setattr(server, "DATA", data)
    monkeypatch.setattr(server, "DB", data / "workshop.sqlite3")
    monkeypatch.setattr(server, "PROJECTS", projects)
    monkeypatch.setattr(server, "IMPORTS", data / "imports")
    monkeypatch.setattr(server, "BACKUPS", data / "backups")
    monkeypatch.setattr(server, "SOURCE_ARCHIVES", data / "source_archives")
    monkeypatch.setattr(server, "_initialized_database_path", None)
    monkeypatch.setattr(server, "_local_worker_kit_instance", None)
    monkeypatch.setattr(server, "_local_worker_startup_recovery_complete", False)
    for directory in (
        projects,
        server.IMPORTS,
        server.BACKUPS,
        server.SOURCE_ARCHIVES,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    project_root = projects / "daily" / "sources"
    project_root.mkdir(parents=True)
    raw = b"Alpha <script>not markup</script>\nBeta\n"
    source = project_root / "approved.txt"
    source.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest().upper()
    connection = server.connect()
    server.upsert_project(connection, "daily", "Daily work", "", "")
    now = server.utc()
    connection.execute(
        "INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            "approved-source",
            "daily",
            "source",
            "<Approved source>",
            "sources/approved.txt",
            "{}",
            "SOURCE",
            digest,
            now,
            now,
        ),
    )
    connection.execute(
        "INSERT INTO artifact_search VALUES(?,?,?,?,?)",
        (
            "approved-source",
            "daily",
            "<Approved source>",
            "source",
            "Alpha Beta",
        ),
    )
    connection.commit()
    connection.close()

    server_http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=server_http.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server_http.server_port}", server.DB
    finally:
        server_http.shutdown()
        server_http.server_close()
        thread.join(timeout=5)


def approve_plan(base_url: str, worker: str, **extra: object) -> dict:
    status, plan = api(
        base_url,
        "/api/local-worker-jobs/plan",
        "POST",
        {
            "projectId": "daily",
            "workerId": worker,
            "sourceArtifactId": "approved-source",
            **extra,
        },
    )
    assert status == 201
    status, approved = api(
        base_url,
        f"/api/local-worker-jobs/{plan['jobId']}/plan-decision",
        "POST",
        {"decision": "approve", "note": "API test approval"},
    )
    assert status == 200
    return approved


def test_http_contract_source_plan_execute_result_history_and_cleanup(
    worker_api,
) -> None:
    base_url, database = worker_api
    status, workers = api(base_url, "/api/local-workers")
    assert status == 200
    assert [worker["workerId"] for worker in workers] == [
        "approved-text-reader",
        "code-structure-inspector",
        "note-proposal-worker",
        "package-manifest-validator",
            "handoff-proposal-builder",
            "prompt-proposal-builder",
            "draft-workshop",
            "evidence-compare",
            "visual-brief-builder",
            "song-production-brief-builder",
            "video-production-brief-builder",
            "build-work-order-builder",
            "module-proposal-builder",
            "local-ai-rewrite",
        ]
    status, contract = api(
        base_url, "/api/local-workers/approved-text-reader"
    )
    assert status == 200
    assert contract["valid"] is True
    assert contract["networkPolicy"] == "denied"
    status, sources = api(
        base_url, "/api/local-worker-sources?projectId=daily"
    )
    assert status == 200
    assert sources[0]["artifactId"] == "approved-source"

    approved = approve_plan(base_url, "approved-text-reader")
    assert approved["status"] == "plan_approved"
    status, executed = api(
        base_url,
        f"/api/local-worker-jobs/{approved['jobId']}/execute",
        "POST",
        {},
    )
    assert status == 200
    assert executed["status"] == "awaiting_result_approval"
    assert executed["result"]["accepted"] is False
    assert executed["result"]["output"]["content"].startswith(
        "Alpha <script>"
    )
    status, blank = api(
        base_url,
        f"/api/local-worker-jobs/{approved['jobId']}/result-decision",
        "POST",
        {"decision": "approve", "note": " "},
    )
    assert status == 400
    assert blank["code"] == "approval_note_required"
    status, accepted = api(
        base_url,
        f"/api/local-worker-jobs/{approved['jobId']}/result-decision",
        "POST",
        {"decision": "approve", "note": "Read result reviewed"},
    )
    assert status == 200
    assert accepted["status"] == "result_approved"
    assert accepted["attachmentStatus"] == "unattached"
    assert accepted["activationStatus"] == "inactive"

    status, history = api(
        base_url, "/api/local-worker-jobs?projectId=daily"
    )
    assert status == 200
    assert history[0]["jobId"] == approved["jobId"]
    assert history[0]["evidence"]
    status, cleaned = api(
        base_url,
        f"/api/local-worker-jobs/{approved['jobId']}/delete",
        "POST",
        {"confirmed": True},
    )
    assert status == 200
    assert cleaned["receiptsPreserved"] is True

    connection = sqlite3.connect(database)
    assert connection.execute("PRAGMA user_version").fetchone()[0] == 13
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert connection.execute(
        "SELECT COUNT(*) FROM jobs WHERE operation LIKE 'local-worker:%'"
    ).fetchone()[0] == 0
    assert connection.execute(
        "SELECT COUNT(*) FROM receipts WHERE action LIKE 'local_worker.%'"
    ).fetchone()[0] >= 5
    connection.close()


def test_http_note_proposal_approval_and_rollback(worker_api) -> None:
    base_url, database = worker_api
    approved = approve_plan(
        base_url,
        "note-proposal-worker",
        selection="Beta",
        title="<API note>",
    )
    status, proposed = api(
        base_url,
        f"/api/local-worker-jobs/{approved['jobId']}/execute",
        "POST",
        {},
    )
    assert status == 200
    assert proposed["result"]["output"]["content"] == "# <API note>\n\nBeta\n"
    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT COUNT(*) FROM artifacts WHERE kind='note'"
    ).fetchone()[0] == 0
    connection.close()
    status, accepted = api(
        base_url,
        f"/api/local-worker-jobs/{approved['jobId']}/result-decision",
        "POST",
        {"decision": "approve", "note": "Create one note"},
    )
    assert status == 200
    note_id = accepted["result"]["acceptance"]["noteArtifactId"]
    assert accepted["actions"]["rollback"] is True
    status, rolled = api(
        base_url,
        f"/api/local-worker-jobs/{approved['jobId']}/rollback",
        "POST",
        {"confirmed": True},
    )
    assert status == 200
    assert rolled["status"] == "rolled_back"
    connection = sqlite3.connect(database)
    assert connection.execute(
        "SELECT COUNT(*) FROM artifacts WHERE id=?", (note_id,)
    ).fetchone()[0] == 0
    connection.close()


@pytest.mark.parametrize(
    ("worker", "profile", "required_section"),
    [
        ("handoff-proposal-builder", "Project Recovery Handoff", "## Source record"),
        ("prompt-proposal-builder", "Local Model Task Prompt", "## Stop conditions"),
    ],
)
def test_http_builder_plan_generation_approval_save_export_and_rollback(worker_api, worker, profile, required_section) -> None:
    base_url, database = worker_api
    status, planned = api(base_url, "/api/local-worker-jobs/plan", "POST", {
        "projectId":"daily", "workerId":worker, "sourceArtifactIds":["approved-source"],
        "destinationProfile":profile, "goal":"Continue safely from exact evidence", "purpose":"Continue safely from exact evidence",
    })
    assert status == 201
    assert planned["plan"]["destinationProfile"] == profile
    status, approved_plan = api(base_url, f"/api/local-worker-jobs/{planned['jobId']}/plan-decision", "POST", {"decision":"approve", "note":"Approved builder plan"})
    assert status == 200
    status, generated = api(base_url, f"/api/local-worker-jobs/{planned['jobId']}/execute", "POST", {})
    assert status == 200
    assert required_section in generated["result"]["output"]["text"]
    assert generated["result"]["output"]["metadata"]["schemaVersion"] == "builder-output-v1"
    status, approved = api(base_url, f"/api/local-worker-jobs/{planned['jobId']}/result-decision", "POST", {"decision":"approve", "note":"Approved builder output"})
    assert status == 200 and approved["activationStatus"] == "inactive"
    status, exported = api(base_url, f"/api/local-worker-jobs/{planned['jobId']}/export", "POST", {"format":"json", "includeProvenance":True, "confirmed":True})
    assert status == 200
    export_path = Path(exported["result"]["exports"][-1]["path"])
    assert export_path.exists() and export_path.suffix == ".json"
    status, saved = api(base_url, f"/api/local-worker-jobs/{planned['jobId']}/save-draft", "POST", {"confirmed":True})
    assert status == 200 and saved["status"] == "draft_saved"
    draft_id = saved["result"]["savedDraft"]["artifactId"]
    status, rolled = api(base_url, f"/api/local-worker-jobs/{planned['jobId']}/rollback", "POST", {"confirmed":True})
    assert status == 200 and rolled["status"] == "rolled_back"
    connection = sqlite3.connect(database)
    assert connection.execute("SELECT count(*) FROM artifacts WHERE id=?", (draft_id,)).fetchone()[0] == 0
    assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    connection.close()

def test_http_security_rejects_unknown_workers_fields_cross_site_and_legacy_jobs(
    worker_api,
) -> None:
    base_url, _ = worker_api
    status, unknown = api(
        base_url,
        "/api/local-worker-jobs/plan",
        "POST",
        {
            "projectId": "daily",
            "workerId": "../../shell",
            "sourceArtifactId": "approved-source",
        },
    )
    assert status == 404
    assert unknown["code"] == "worker_not_supported"
    status, fields = api(
        base_url,
        "/api/local-worker-jobs/plan",
        "POST",
        {
            "projectId": "daily",
            "workerId": "approved-text-reader",
            "sourceArtifactId": "approved-source",
            "command": "whoami",
        },
    )
    assert status == 400
    assert fields["code"] == "request_fields_invalid"
    status, cross_site = api(
        base_url,
        "/api/local-worker-jobs/plan",
        "POST",
        {
            "projectId": "daily",
            "workerId": "approved-text-reader",
            "sourceArtifactId": "approved-source",
        },
        {"Sec-Fetch-Site": "cross-site"},
    )
    assert status == 403
    assert cross_site["code"] == "cross_site_request_denied"
    status, retired = api(base_url, "/api/jobs")
    assert status == 410
    assert retired["code"] == "legacy_job_api_retired"
    status, disabled = api(base_url, "/api/jobs", "POST", {"operation": "x"})
    assert status == 410
    assert disabled["code"] == "arbitrary_jobs_disabled"


def test_visual_brief_http_accepts_allowlisted_controls_and_temporary_notes(worker_api) -> None:
    base_url, _ = worker_api
    status, value = api(
        base_url,
        "/api/local-worker-jobs/plan",
        "POST",
        {
            "projectId": "daily",
            "workerId": "visual-brief-builder",
            "sourceArtifactIds": [],
            "roughText": "A small workshop light above a river.",
            "visualControls": {"conceptTitle": "River Light", "aspectRatio": "1:1"},
            "destinationProfile": "General image concept",
            "goal": "",
            "purpose": "Prepare General image concept",
            "actor": "owner",
        },
    )
    assert status == 201
    assert value["worker"]["workerId"] == "visual-brief-builder"
    assert value["sources"][0]["kind"] == "temporary-visual-notes"
    assert value["plan"]["visualControls"]["conceptTitle"] == "River Light"


def test_song_brief_http_accepts_exact_temporary_music_inputs(worker_api) -> None:
    base_url, _ = worker_api
    lyrics = "Hold the river light\nKeep this exact: <river & sky>"
    status, value = api(base_url, "/api/local-worker-jobs/plan", "POST", {
        "projectId": "daily", "workerId": "song-production-brief-builder",
        "sourceArtifactIds": [], "musicNotes": "Warm acoustic production.",
        "musicLyrics": lyrics, "productionControls": {"workingTitle": "River Light", "tempoBpm": "84"},
        "destinationProfile": "Full original song", "goal": "", "purpose": "Prepare Full original song", "actor": "owner",
    })
    assert status == 201
    assert value["worker"]["workerId"] == "song-production-brief-builder"
    assert [source["kind"] for source in value["sources"]] == ["temporary-music-notes", "temporary-music-lyrics"]
    assert value["sources"][1]["artifactId"] == "music-lyrics:" + hashlib.sha256(lyrics.encode()).hexdigest().upper()


def test_video_brief_http_accepts_exact_temporary_video_notes(worker_api) -> None:
    base_url, _ = worker_api
    notes = "A still opening frame, three practical shots, and a quiet close."
    status, value = api(base_url, "/api/local-worker-jobs/plan", "POST", {
        "projectId": "daily", "workerId": "video-production-brief-builder",
        "sourceArtifactIds": [], "videoNotes": notes,
        "videoControls": {"workingTitle": "Quiet Workshop", "targetDuration": "30 seconds"},
        "destinationProfile": "Cinematic scene", "goal": "", "purpose": "Prepare Cinematic scene", "actor": "owner",
    })
    assert status == 201
    assert value["worker"]["workerId"] == "video-production-brief-builder"
    assert value["sources"][0]["kind"] == "temporary-video-notes"
    assert value["sources"][0]["artifactId"] == "video-notes:" + hashlib.sha256(notes.encode()).hexdigest().upper()
