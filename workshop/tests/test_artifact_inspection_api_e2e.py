from __future__ import annotations

import hashlib
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
WORKER_ID = "artifact-compass-inspection-worker"


def available_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def api(port: int, path: str, method: str = "GET", data: dict | None = None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=body,
        method=method,
        headers=headers,
    )
    with urllib.request.urlopen(request, timeout=20) as response:
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
    for _ in range(150):
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


def promotion_context(candidate: dict) -> dict:
    return {
        "candidateHash": candidate["candidate_hash"],
        "workspaceGeneration": candidate["workspace_generation"],
        "sourceArtifactHash": candidate["source_artifact"]["sha256"],
        "workerCardHash": candidate["worker_card_hash"],
        "executionPlanHash": candidate["plan_hash"],
        "actor": "pytest-owner",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }


def test_isolated_artifact_selection_inspection_attachment_restart_and_rollback(tmp_path_factory) -> None:
    # Keep the fixture basename short: this flow intentionally creates deeply
    # nested, hash-bound transaction evidence on Windows.
    sandbox = tmp_path_factory.mktemp("ai") / "runtime"
    shutil.copytree(ROOT / "app", sandbox / "app")
    shutil.copytree(ROOT / "companion", sandbox / "companion", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(ROOT / "examples", sandbox / "examples")
    (sandbox / "data").mkdir()
    port = available_port()
    process = start_server(sandbox, port)
    try:
        api(port, "/api/projects", "POST", {"id": "public-project", "title": "Public Project"})
        public_relative = "public-project/sources/flashriver/publichash/docs/sample.md"
        public_content = "# Public API Guide\n\nTODO: document [route](https://example.invalid/api).\n"
        api(port, "/api/files", "POST", {"path": public_relative, "content": public_content})
        public_artifact = api(
            port,
            "/api/projects/public-project/artifacts",
            "POST",
            {
                "id": "public-artifact",
                "title": "sample.md",
                "kind": "flashriver-core-doc",
                "path": "sources/flashriver/publichash/docs/sample.md",
                "payload": {
                    "sourcePackage": "PUBLIC.zip",
                    "sourcePackageSha256": "A" * 64,
                    "archiveMember": "docs/sample.md",
                    "relativeName": "sample.md",
                },
                "authorityState": "SOURCE",
            },
        )["artifact"]

        private_relative = "public-project/sources/flashriver/publichash/private_source_artifacts/private.txt"
        api(port, "/api/files", "POST", {"path": private_relative, "content": "private"})
        api(
            port,
            "/api/projects/public-project/artifacts",
            "POST",
            {
                "id": "private-artifact",
                "title": "private.txt",
                "kind": "flashriver-private-source",
                "path": "sources/flashriver/publichash/private_source_artifacts/private.txt",
                "payload": {"private": True},
                "authorityState": "SOURCE_PRIVATE",
            },
        )

        options = api(port, "/api/artifacts/inspection-options")
        public_option = next(item for item in options if item["artifactId"] == "public-artifact")
        private_option = next(item for item in options if item["artifactId"] == "private-artifact")
        assert public_option["eligible"] is True
        assert private_option["eligible"] is False
        assert {"private_source", "outside_public_safe_roots"}.issubset(private_option["blockedReasons"])

        workers = api(port, "/api/workers")
        assert [worker["worker_id"] for worker in workers] == ["reference-metadata-worker", WORKER_ID]
        validation = api(port, "/api/workers/validate", "POST", {"workerId": WORKER_ID})
        assert validation["valid"] is True
        assert validation["enforcement"]["allowed"] is True
        plan = api(
            port,
            f"/api/workers/{WORKER_ID}/plan",
            "POST",
            {"actor": "pytest-owner", "artifactId": "public-artifact"},
        )
        assert plan["selected_artifact"]["artifact_id"] == "public-artifact"
        assert plan["auto_activate"] is False
        source_path = sandbox / "data" / "projects" / public_relative
        source_hash = hashlib.sha256(source_path.read_bytes()).hexdigest().upper()
        candidate = api(
            port,
            f"/api/workers/{WORKER_ID}/run",
            "POST",
            {"planId": plan["plan_id"], "actor": "pytest-owner"},
        )
        assert candidate["lifecycle_state"] == "awaiting_approval"
        assert candidate["source_artifact"]["sha256"] == source_hash
        assert hashlib.sha256(source_path.read_bytes()).hexdigest().upper() == source_hash
        assert api(port, "/api/artifacts/public-artifact/inspections") == []
    finally:
        stop_server(process)

    process = start_server(sandbox, port)
    try:
        refreshed = api(port, f"/api/candidates/{candidate['candidate_id']}")
        missing_note = promotion_context(refreshed)
        missing_note["note"] = "   "
        try:
            api(port, f"/api/candidates/{candidate['candidate_id']}/approve", "POST", missing_note)
            raise AssertionError("approval without a note unexpectedly succeeded")
        except urllib.error.HTTPError as error:
            payload = json.loads(error.read().decode("utf-8"))
            assert error.code == 400
            assert payload["code"] == "approval_note_required"
        approval = promotion_context(refreshed)
        approval["note"] = "Approved public-safe inspection."
        approved = api(port, f"/api/candidates/{candidate['candidate_id']}/approve", "POST", approval)
        assert approved["lifecycle_state"] == "approved"
        active = api(port, f"/api/candidates/{candidate['candidate_id']}/activate", "POST", promotion_context(approved))
        assert active["lifecycle_state"] == "active"
        assert active["activation"]["artifact_attachment"]["artifact_id"] == "public-artifact"
        inspections = api(port, "/api/artifacts/public-artifact/inspections")
        assert inspections[0]["attachment_status"] == "active"
        assert inspections[0]["report_valid"] is True
        rolled_back = api(port, f"/api/candidates/{candidate['candidate_id']}/rollback", "POST", promotion_context(active))
        assert rolled_back["lifecycle_state"] == "rolled_back"
        inspections = api(port, "/api/artifacts/public-artifact/inspections")
        assert inspections[0]["attachment_status"] == "rolled_back"

        source_path = sandbox / "data" / "projects" / public_relative
        assert hashlib.sha256(source_path.read_bytes()).hexdigest().upper() == candidate["source_artifact"]["sha256"]
        with sqlite3.connect(sandbox / "data" / "workshop.sqlite3") as connection:
            assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert connection.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] == 2
            assert connection.execute("SELECT COUNT(*) FROM modules").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 0
            assert connection.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
        receipt_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (sandbox / "data" / "worker_harness" / "transactions" / "receipts").glob("*.json")
        )
        assert approval["note"] not in receipt_text
    finally:
        stop_server(process)
