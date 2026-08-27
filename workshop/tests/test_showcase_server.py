from __future__ import annotations

import threading
import urllib.error
import urllib.request
import os

from companion.showcase_control import process_alive
from companion.showcase_server import build_server


def request(url: str, method: str = "GET", data: bytes | None = None):
    return urllib.request.urlopen(urllib.request.Request(url, method=method, data=data), timeout=3)


def test_showcase_controller_detects_its_own_process():
    assert process_alive(os.getpid()) is True


def test_showcase_is_exactly_allowlisted_and_read_only():
    server = build_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with request(base + "/showcase") as response:
            html = response.read().decode("utf-8")
            assert response.status == 200
            assert "TWIS Holo Workshop — Showcase" in html
            assert "SHOWCASE MODE" in html and "VIEW ONLY" in html
            assert "Sanctuary" in html and "Crossroads" in html
            assert "Draft Workshop" in html and "Song Production Brief" in html
            assert "Visual Brief Builder" in html and "Evidence Compare" in html
            assert "Video · Production Brief Builder" in html
            assert "Set-Cookie" not in response.headers
            assert "connect-src 'none'" in response.headers["Content-Security-Policy"]
        for path in ("/api/health", "/api/projects", "/work", "/control", "/import", "/settings", "/My%20Work", "/showcase/../api/projects", "/showcase/%2e%2e/api/projects"):
            try:
                request(base + path)
                raise AssertionError(f"private path was reachable: {path}")
            except urllib.error.HTTPError as error:
                assert error.code == 403
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            try:
                request(base + "/showcase", method=method, data=b'{"role":"OWNER"}')
                raise AssertionError(f"write method was accepted: {method}")
            except urllib.error.HTTPError as error:
                assert error.code == 403
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


def test_showcase_files_contain_no_owner_runtime_data():
    server = build_server(0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    forbidden = ("Olli_Twis", "workshop.sqlite3", "127.0.0.1:8787", "receipt_id", "job_id", "sha256", "Cf-Access", "cert.pem")
    try:
        for path in ("/showcase", "/showcase/showcase.css", "/showcase/showcase.js", "/showcase/showcase-icon.svg"):
            with request(base + path) as response:
                body = response.read().decode("utf-8")
                for value in forbidden:
                    assert value not in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
