from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request

from companion import server
from companion.remote_access import GUEST_CREATOR, OWNER, VISITOR, Principal


def _request(base: str, path: str, *, role: str, method: str = "GET", value=None):
    body = json.dumps(value).encode() if value is not None else None
    request = urllib.request.Request(
        base + path,
        data=body,
        method=method,
        headers={"Content-Type": "application/json", "X-Test-Role": role},
    )
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_guest_create_owner_promote_and_backend_denials(monkeypatch, tmp_path):
    monkeypatch.setattr(server, "DB", tmp_path / "owner.sqlite3")
    monkeypatch.setattr(server, "VISITOR_BENCH_DB", tmp_path / "visitor.sqlite3")
    monkeypatch.setattr(server, "_initialized_database_path", None)
    server._initialize_database()
    con = server.connect()
    server.upsert_project(con, "owner-project", "Owner Project", "", "")
    con.commit()
    con.close()

    identities = {
        OWNER: "owner@example.com",
        GUEST_CREATOR: "guest@example.com",
        VISITOR: "visitor@example.com",
    }
    monkeypatch.setattr(
        server,
        "authenticate",
        lambda headers, client_ip: Principal(headers["X-Test-Role"], identities[headers["X-Test-Role"]], True, "test-only"),
    )

    httpd = server.ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        content = "Exact guest text\nSecond line."
        status, created = _request(base, "/api/visitor-bench/submissions", role=GUEST_CREATOR, method="POST", value={"room":"write","title":"Guest draft","content":content,"operation":"draft"})
        assert status == 201
        submission = created["submission"]
        status, _ = _request(base, "/api/projects", role=GUEST_CREATOR)
        assert status == 403
        status, _ = _request(base, "/api/visitor-bench/submissions", role=VISITOR, method="POST", value={"room":"write","title":"No","content":"No"})
        assert status == 403

        status, promoted = _request(base, f"/api/visitor-bench/submissions/{submission['id']}/promote", role=OWNER, method="POST", value={"projectId":"owner-project"})
        assert status == 201
        con = server.connect()
        artifact = con.execute("SELECT authority_state,payload FROM artifacts WHERE id=?", (promoted["artifactId"],)).fetchone()
        receipt = con.execute("SELECT action FROM receipts WHERE id=?", (promoted["receiptId"],)).fetchone()
        con.close()
        assert artifact["authority_state"] == "DRAFT"
        assert json.loads(artifact["payload"])["content"] == content
        assert receipt["action"] == "visitor_bench.promoted"
        original = server.VisitorBench(server.VISITOR_BENCH_DB).get(submission["id"], owner=True)
        assert original["content"] == content
        assert original["authority_state"] == "GUEST_SANDBOX_DRAFT"
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join(timeout=3)
