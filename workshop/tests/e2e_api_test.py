from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = ""


def request(path: str, method: str = "GET", data=None):
    body = None
    headers = {}
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=body, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=10) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else None


def wait_for_server(proc: subprocess.Popen):
    for _ in range(50):
        if proc.poll() is not None:
            raise RuntimeError(proc.stderr.read() if proc.stderr else "server exited")
        try:
            return request("/api/health")
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("server did not start")


def available_port() -> str:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return str(listener.getsockname()[1])


def main():
    global PORT
    PORT = available_port()
    with tempfile.TemporaryDirectory(prefix="twis-e2e-") as temp_dir:
        sandbox = Path(temp_dir)
        shutil.copytree(ROOT / "app", sandbox / "app")
        shutil.copytree(
            ROOT / "companion",
            sandbox / "companion",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        (sandbox / "data").mkdir()
        env = os.environ.copy()
        env["TWIS_HOLO_PORT"] = PORT
        proc = subprocess.Popen(
            [sys.executable, "companion/server.py"],
            cwd=sandbox,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            health = wait_for_server(proc)
            assert health["ok"] is True
            assert Path(health["sqlite"]).resolve().is_relative_to(sandbox.resolve()), {
                "sqlite": health["sqlite"],
                "sandbox": str(sandbox),
            }
            capabilities = request("/api/capabilities")
            assert capabilities["foundation"]["release"] == "0.5.0"
            assert capabilities["foundation"]["workerCards"]["hostEnforced"] is True
            assert capabilities["foundation"]["workerHarness"]["arbitraryWorkers"] is False
            assert capabilities["foundation"]["artifactCompass"]["liveIndexBuilt"] is False
            assert capabilities["foundation"]["artifactCompass"]["vectorSearch"] is False
            project = {"id": "e2e-test", "title": "E2E Test", "description": "runtime test", "nextAction": "verify API"}
            created = request("/api/projects", "POST", project)
            assert created["ok"] is True
            artifact = {"kind": "document", "title": "Smoke Document", "payload": {"body": "Still. Here."}, "authorityState": "DRAFT"}
            saved = request("/api/projects/e2e-test/artifacts", "POST", artifact)
            assert saved["ok"] is True
            artifacts = request("/api/projects/e2e-test/artifacts")
            assert any(item["title"] == "Smoke Document" for item in artifacts)
            session = request("/api/projects/e2e-test/sessions", "POST", {"room": "write", "summary": "tested", "nextAction": "ship"})
            assert session["ok"] is True
            capsule = request("/api/projects/e2e-test/capsule", "POST", {})
            assert capsule["ok"] is True and capsule["path"].endswith(".zip")
            assert Path(capsule["path"]).resolve().is_relative_to(sandbox.resolve())
            print("Twis Holo API E2E PASS (isolated temporary data)")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


if __name__ == "__main__":
    main()
