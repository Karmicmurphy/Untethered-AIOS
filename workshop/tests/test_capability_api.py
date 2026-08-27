from __future__ import annotations

import json
import sys
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "companion"))
import server  # noqa: E402


def get(base: str, path: str) -> tuple[int, dict]:
    with urllib.request.urlopen(base + path, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def post(base: str, path: str, value: dict) -> tuple[int, dict]:
    request = urllib.request.Request(base + path, data=json.dumps(value).encode("utf-8"), headers={"Content-Type": "application/json", "Sec-Fetch-Site": "same-origin"}, method="POST")
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def test_capability_bay_owner_read_api_is_truthful_and_side_effect_free():
    before = (ROOT / "config" / "capability-registry.json").read_bytes()
    http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{http.server_port}"
    try:
        status, registry = get(base, "/api/capability-registry")
        assert status == 200 and registry["ok"] is True and registry["count"] == 20
        assert len(registry["capabilities"]) == 20
        assert all("hardwareFit" in item and "verificationAge" in item for item in registry["capabilities"])
        status, recommendation = get(base, "/api/capability-registry/recommend?request=remove%20an%20image%20background")
        assert status == 200 and recommendation["replacementGroup"] == "background-removal"
        assert recommendation["recommended"]["capabilityId"] == "external.opencv-grabcut-cpu-candidate"
        assert recommendation["createOurOwn"] is False
        status, hardware = get(base, "/api/hardware-profile")
        assert status == 200 and hardware["profileHash"] == registry["hardwareProfileHash"]
        status, skills = get(base, "/api/agent-skills")
        assert status == 200 and skills["executedScripts"] == 0 and skills["count"] == len(skills["skills"])
        status, mcp = get(base, "/api/mcp-catalog")
        assert status == 200 and mcp["protocolVersion"] == "2026-07-28"
        assert mcp["autoEnabledTools"] == 0 and mcp["executedTools"] == 0
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=5)
    assert (ROOT / "config" / "capability-registry.json").read_bytes() == before


def test_capability_inspection_api_has_separate_plan_and_owner_evidence_gates():
    con = server.connect()
    con.execute("INSERT OR IGNORE INTO projects(id,title,description,next_action,created_at,updated_at) VALUES(?,?,?,?,?,?)", ("inspection-api-fixture", "Inspection API fixture", "Disposable", "", "2026-08-24T00:00:00+00:00", "2026-08-24T00:00:00+00:00"))
    con.commit(); con.close()
    http = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True); thread.start()
    base = f"http://127.0.0.1:{http.server_port}"
    inspection_id = ""
    try:
        status, template = get(base, "/api/capability-inspections/authority-template")
        assert status == 200 and template["authority"]["functionalTest"] is False and template["authority"]["network"] == []
        status, plan = post(base, "/api/capability-inspections/plan", {"projectId": "inspection-api-fixture", "capabilityId": "external.rembg-cpu-candidate", "authority": template["authority"], "note": "API static proof"})
        inspection_id = plan["inspectionId"]
        assert status == 201 and plan["status"] == "inspection_plan_pending"
        status, approved = post(base, f"/api/capability-inspections/{inspection_id}/plan-decision", {"decision": "approve", "note": "Approve static-only exact plan."})
        assert status == 200 and approved["status"] == "inspection_plan_approved"
        status, evidence = post(base, f"/api/capability-inspections/{inspection_id}/execute", {})
        assert status == 200 and evidence["status"] == "needs_review" and evidence["evidence"]["functionalEvidence"]["executed"] is False
        status, listed = get(base, "/api/capability-inspections?capabilityId=external.rembg-cpu-candidate")
        assert status == 200 and listed["inspections"][0]["inspectionId"] == inspection_id
    finally:
        http.shutdown(); http.server_close(); thread.join(timeout=5)
        con = server.connect()
        if inspection_id:
            con.execute("DELETE FROM receipts WHERE project_id='inspection-api-fixture'")
            con.execute("DELETE FROM jobs WHERE project_id='inspection-api-fixture'")
        con.execute("DELETE FROM projects WHERE id='inspection-api-fixture'")
        con.commit(); con.close()
