from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from companion import server
from test_media_workspace import PNG, workspace


def post_png(base: str, project_id: str, headers: dict[str, str], body: bytes = PNG) -> tuple[int, dict]:
    request = urllib.request.Request(
        f"{base}/api/media-workspace/projects/{project_id}/background-composites",
        data=body,
        headers={"Content-Type": "image/png", "Sec-Fetch-Site": "same-origin", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_background_composite_http_save_is_source_bound_and_inactive(tmp_path, monkeypatch):
    media, _ = workspace(tmp_path)
    foreground = media.save_image("p1", "Foreground", "image/png", PNG, 1, 1)["artifact"]
    backdrop = media.save_image("p1", "Backdrop", "image/png", PNG, 1, 1)["artifact"]
    monkeypatch.setattr(server, "media_workspace", lambda: media)
    http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{http.server_port}"
    try:
        status, value = post_png(base, "p1", {
            "X-TWIS-Title": "Governed composite",
            "X-TWIS-Width": "1",
            "X-TWIS-Height": "1",
            "X-TWIS-Source-Artifact": foreground["id"],
            "X-TWIS-Source-SHA256": foreground["sha256"],
            "X-TWIS-Background-Mode": "image",
            "X-TWIS-Background-Artifact": backdrop["id"],
            "X-TWIS-Background-SHA256": backdrop["sha256"],
            "X-TWIS-Background-Direction": "vertical",
        })
        assert status == 201
        artifact = value["artifact"]
        assert artifact["payload"]["status"] == "inactive-draft"
        assert artifact["payload"]["provenance"]["sourceArtifactIds"] == [foreground["id"], backdrop["id"]]

        with pytest.raises(urllib.error.HTTPError) as error:
            post_png(base, "p1", {
                "X-TWIS-Title": "Stale composite",
                "X-TWIS-Width": "1",
                "X-TWIS-Height": "1",
                "X-TWIS-Source-Artifact": foreground["id"],
                "X-TWIS-Source-SHA256": "0" * 64,
                "X-TWIS-Background-Mode": "solid",
                "X-TWIS-Background-Color-A": "#07131b",
            })
        assert error.value.code == 409
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=5)
