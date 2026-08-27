from __future__ import annotations

import json
import os
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def api(port: int, path: str, method: str = "GET", data: dict | None = None, *, headers: dict | None = None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request_headers = dict(headers or {})
    if data is not None:
        request_headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        method=method,
        headers=request_headers,
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def start_server(sandbox: Path, port: int) -> subprocess.Popen[str]:
    environment = os.environ.copy()
    environment["TWIS_HOLO_PORT"] = str(port)
    process = subprocess.Popen(
        [sys.executable, "companion/server.py"],
        cwd=sandbox,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    for _ in range(100):
        if process.poll() is not None:
            raise AssertionError(process.stderr.read() if process.stderr else "server exited")
        try:
            if api(port, "/api/health")["ok"]:
                return process
        except (OSError, urllib.error.URLError):
            time.sleep(0.05)
    process.terminate()
    raise AssertionError("isolated server did not start")


def stop_server(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def context(candidate: dict, *, actor: str = "pytest-owner") -> dict:
    return {
        "candidateHash": candidate["candidate_hash"],
        "workspaceGeneration": candidate["workspace_generation"],
        "actor": actor,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def test_isolated_http_plan_run_restart_approve_activate_and_rollback(tmp_path_factory) -> None:
    # Use a deliberately short basename so the nested transaction evidence
    # remains below legacy Windows MAX_PATH limits in deep staging workspaces.
    sandbox = tmp_path_factory.mktemp("wh") / "runtime"
    shutil.copytree(ROOT / "app", sandbox / "app")
    shutil.copytree(ROOT / "companion", sandbox / "companion", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(ROOT / "examples", sandbox / "examples")
    (sandbox / "data").mkdir()
    port = available_port()
    process = start_server(sandbox, port)
    try:
        capabilities = api(port, "/api/capabilities")
        assert capabilities["foundation"]["release"] == "0.5.0"
        assert capabilities["foundation"]["workerHarness"]["arbitraryWorkers"] is False
        assert capabilities["foundation"]["workerHarness"]["automaticActivation"] is False

        workers = api(port, "/api/workers")
        assert [worker["worker_id"] for worker in workers] == ["reference-metadata-worker"]
        assert not (sandbox / "data" / "worker_harness").exists()
        assert api(port, "/api/candidates") == []

        validation = api(port, "/api/workers/validate", "POST", {})
        assert validation["valid"] is True
        assert validation["enforcement"]["allowed"] is True

        plan = api(port, "/api/workers/reference-metadata-worker/plan", "POST", {"actor": "pytest-owner"})
        assert plan["auto_activate"] is False
        assert plan["requested_permissions"] == {
            "network": False,
            "shell": False,
            "destructive_actions": False,
            "approval_required": True,
        }
        candidate = api(
            port,
            "/api/workers/reference-metadata-worker/run",
            "POST",
            {"planId": plan["plan_id"], "actor": "pytest-owner"},
        )
        assert candidate["lifecycle_state"] == "awaiting_approval"
        assert candidate["activation"] is None
        assert candidate["output"]["worker_id"] == "reference-metadata-worker"
    finally:
        stop_server(process)

    # File-backed evidence survives a companion restart; Workshop SQLite is not
    # used for worker records.
    process = start_server(sandbox, port)
    try:
        refreshed = api(port, f"/api/candidates/{candidate['candidate_id']}")
        assert refreshed["candidate_hash"] == candidate["candidate_hash"]
        approval = context(refreshed)
        approval["note"] = "Harmless reference output reviewed locally."
        approved = api(port, f"/api/candidates/{candidate['candidate_id']}/approve", "POST", approval)
        assert approved["lifecycle_state"] == "approved"
        assert approved["approval"]["note"] == approval["note"]

        activated = api(port, f"/api/candidates/{candidate['candidate_id']}/activate", "POST", context(approved))
        assert activated["lifecycle_state"] == "active"
        assert activated["activation"]["executes_on_startup"] is False
        assert activated["activation"]["grants_permissions"] is False

        rolled_back = api(port, f"/api/candidates/{candidate['candidate_id']}/rollback", "POST", context(activated))
        assert rolled_back["lifecycle_state"] == "rolled_back"
        assert rolled_back["rollback"]["restored_sha256"] == rolled_back["rollback"]["expected_sha256"]

        registry = json.loads((sandbox / "data" / "worker_harness" / "activation-registry.json").read_text(encoding="utf-8"))
        assert registry["entries"][0]["status"] == "rolled_back"
        assert registry["entries"][0]["executes_on_startup"] is False

        receipt_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (sandbox / "data" / "worker_harness" / "transactions" / "receipts").glob("*.json")
        )
        assert approval["note"] not in receipt_text

        with sqlite3.connect(sandbox / "data" / "workshop.sqlite3") as connection:
            assert connection.execute("SELECT COUNT(*) FROM modules").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
        assert list((sandbox / "data" / "source_archives").iterdir()) == []
        assert list((sandbox / "data" / "projects").iterdir()) == []
    finally:
        stop_server(process)


def test_worker_api_rejects_cross_site_and_unexpected_run_fields(tmp_path_factory) -> None:
    sandbox = tmp_path_factory.mktemp("wa") / "runtime"
    shutil.copytree(ROOT / "app", sandbox / "app")
    shutil.copytree(ROOT / "companion", sandbox / "companion", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(ROOT / "examples", sandbox / "examples")
    (sandbox / "data").mkdir()
    port = available_port()
    process = start_server(sandbox, port)
    try:
        try:
            api(port, "/api/workers/validate", "POST", {}, headers={"Sec-Fetch-Site": "cross-site"})
            raise AssertionError("cross-site request unexpectedly succeeded")
        except urllib.error.HTTPError as error:
            payload = json.loads(error.read().decode("utf-8"))
            assert error.code == 400
            assert payload["code"] == "cross_site_request_denied"

        plan = api(port, "/api/workers/reference-metadata-worker/plan", "POST", {"actor": "pytest-owner"})
        try:
            api(
                port,
                "/api/workers/reference-metadata-worker/run",
                "POST",
                {"planId": plan["plan_id"], "actor": "pytest-owner", "faultMode": "worker_failure"},
            )
            raise AssertionError("unexpected run field was accepted")
        except urllib.error.HTTPError as error:
            payload = json.loads(error.read().decode("utf-8"))
            assert error.code == 400
            assert payload["code"] == "request_fields_invalid"
    finally:
        stop_server(process)
