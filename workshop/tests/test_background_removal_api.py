from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from companion.background_removal_runtime import BackgroundRemovalRuntime
from companion import server
from test_background_removal_runtime import RUNTIME_CONFIG, RUNTIME_ROOT, registered_source, workspace


def _get_json(base: str, path: str) -> tuple[int, dict]:
    with urllib.request.urlopen(base + path, timeout=30) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def _post(base: str, path: str, value: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        base + path,
        data=json.dumps(value).encode("utf-8"),
        headers={"Content-Type": "application/json", "Sec-Fetch-Site": "same-origin"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=150) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_background_removal_http_lifecycle_is_bounded_and_owner_decided(tmp_path, monkeypatch):
    _, media, database = workspace(tmp_path)
    source, source_path, source_bytes = registered_source(media)
    service = BackgroundRemovalRuntime(database, tmp_path / "projects", RUNTIME_ROOT, RUNTIME_CONFIG, media)
    monkeypatch.setattr(server, "_background_removal_instance", service)

    http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{http.server_port}"
    proposal_id = ""
    try:
        status, health = _get_json(base, "/api/background-removal/health")
        assert status == 200 and health["state"] == "HEALTHY"

        status, created = _post(
            base,
            "/api/background-removal/projects/p1/proposals",
            {
                "sourceArtifactId": source["id"],
                "sourceSha256": source["sha256"],
                "rectangle": {"x": 0.18, "y": 0.08, "width": 0.64, "height": 0.86},
                "strokes": [],
            },
        )
        assert status == 201 and created["proposal"]["state"] == "PROPOSED"
        proposal_id = created["proposal"]["proposalId"]
        with urllib.request.urlopen(base + created["previewUrl"], timeout=30) as preview:
            assert preview.status == 200 and preview.headers.get_content_type() == "image/png"
            assert preview.read().startswith(b"\x89PNG")

        status, listed = _get_json(base, "/api/background-removal/projects/p1/proposals")
        assert status == 200 and listed["proposals"][0]["proposalId"] == proposal_id
        status, rejected = _post(base, f"/api/background-removal/projects/p1/proposals/{proposal_id}/decision", {"decision": "reject"})
        assert status == 200 and rejected["decision"] == "rejected"
        proposal_id = ""
        assert source_path.read_bytes() == source_bytes
    finally:
        if proposal_id:
            service.decide("p1", proposal_id, "reject")
        http.shutdown()
        http.server_close()
        thread.join(timeout=5)


def test_background_removal_http_rejects_cross_site_and_wrong_content_type(tmp_path, monkeypatch):
    _, media, database = workspace(tmp_path)
    service = BackgroundRemovalRuntime(database, tmp_path / "projects", RUNTIME_ROOT, RUNTIME_CONFIG, media)
    monkeypatch.setattr(server, "_background_removal_instance", service)
    http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{http.server_port}"
    try:
        for headers, expected in [
            ({"Content-Type": "text/plain", "Sec-Fetch-Site": "same-origin"}, 415),
            ({"Content-Type": "application/json", "Sec-Fetch-Site": "cross-site"}, 403),
        ]:
            request = urllib.request.Request(base + "/api/background-removal/projects/p1/proposals", data=b"{}", headers=headers, method="POST")
            with pytest.raises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request, timeout=10)
            assert error.value.code == expected
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=5)
