from __future__ import annotations

import hashlib
import json
import threading
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

import companion.capability_registry as capability_registry_module

from companion.capability_registry import (
    MCP_PROTOCOL_VERSION,
    CapabilityError,
    CapabilityRegistry,
    McpCatalog,
    discover_skills,
    validate_a2a_descriptor,
    validate_capability,
    verification_age,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "config" / "capability-registry.json"


def registry() -> CapabilityRegistry:
    return CapabilityRegistry(REGISTRY_PATH, root=ROOT)


def test_registry_loads_canonical_truth_and_preserves_source_file():
    before = hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest()
    value = registry()
    rows = value.list()
    assert value.snapshot()["count"] == 20
    assert {row["capabilityType"] for row in rows} >= {"native", "agent-skill", "mcp", "a2a", "wasi-component", "comfy-workflow", "cloud-free-tier"}
    assert all(set(row["permissions"]) == {"reads", "writes", "network", "shell", "environment", "credentials", "models", "externalServices"} for row in rows)
    assert hashlib.sha256(REGISTRY_PATH.read_bytes()).hexdigest() == before


def test_malformed_duplicate_and_authority_elevation_fail_closed(tmp_path: Path):
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    malformed = deepcopy(payload["capabilities"][0])
    malformed.pop("permissions")
    with pytest.raises(CapabilityError) as missing:
        validate_capability(malformed)
    assert missing.value.code == "capability_schema_invalid"

    elevated = deepcopy(payload["capabilities"][8])
    elevated["authorityLevel"] = "execute-with-approval"
    with pytest.raises(CapabilityError) as denied:
        validate_capability(elevated)
    assert denied.value.code == "capability_authority_invalid"

    payload["capabilities"].append(deepcopy(payload["capabilities"][0]))
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(CapabilityError) as error:
        CapabilityRegistry(duplicate, root=ROOT)
    assert error.value.code == "capability_duplicate"


def test_status_transitions_are_bounded_and_retired_remains_auditable():
    value = registry()
    capability_id = "external.rembg-cpu-candidate"
    assert value.transition(capability_id, "INSPECTING")["status"] == "INSPECTING"
    assert value.transition(capability_id, "TESTING")["status"] == "TESTING"
    assert value.transition(capability_id, "VERIFICATION_CANDIDATE")["status"] == "VERIFICATION_CANDIDATE"
    with pytest.raises(CapabilityError) as unapproved:
        value.transition(capability_id, "VERIFIED")
    assert unapproved.value.code == "capability_owner_approval_required"
    changed = value.transition(capability_id, "VERIFIED", owner_evidence={"evidenceHash": "A" * 64, "capabilityVersion": "2.0.77", "hardwareProfileHash": value.profile["profileHash"], "approvedAt": datetime.now(timezone.utc).isoformat(), "approvedBy": "test-owner"})
    assert changed["status"] == "VERIFIED"
    with pytest.raises(CapabilityError) as invalid:
        value.transition(capability_id, "DISCOVERED")
    assert invalid.value.code == "capability_transition_invalid"
    retired = value.transition(capability_id, "RETIRED")
    assert retired["status"] == "RETIRED"
    assert next(row for row in value.list() if row["capabilityId"] == capability_id)["status"] == "RETIRED"


def test_free_first_recommendation_honors_specific_replacement_group_and_hardware_truth():
    value = registry()
    result = value.recommend("remove an image background")
    assert result["replacementGroup"] == "background-removal"
    assert result["recommended"]["capabilityId"] == "external.opencv-grabcut-cpu-candidate"
    assert result["createOurOwn"] is False
    opencv = next(row for row in result["matched"] if row["capabilityId"] == "external.opencv-grabcut-cpu-candidate")
    assert opencv["hardwareFit"]["state"] == "GOOD FIT"
    assert opencv["status"] == "VERIFIED"
    assert opencv["healthState"] == "HEALTHY"
    assert all(row["status"] not in {"APPROVED", "VERIFIED"} for row in result["discoveredCandidates"])
    rembg = next(row for row in result["discoveredCandidates"] if row["capabilityId"] == "external.rembg-cpu-candidate")
    assert "model-file provenance" in rembg["knownLimitations"]
    assert "BRIA" in rembg["license"]
    openvino = next(row for row in value.list() if row["capabilityId"] == "external.openvino-future")
    assert openvino["status"] == "INCOMPATIBLE"
    assert openvino["hardwareFit"]["state"] == "UNSUPPORTED"
    assert value.list(filters=["free", "local"])
    assert all(row["costClass"] != "paid-required" and row["networkRequirement"] == "none" for row in value.list(filters=["free", "local"]))


def test_verified_evidence_plus_installed_healthy_runtime_makes_capability_usable():
    value = registry()
    capability_id = "external.opencv-grabcut-cpu-candidate"
    registered = next(row for row in value.list() if row["capabilityId"] == capability_id)
    assert registered["status"] == "VERIFIED"
    assert registered["healthState"] == "HEALTHY"
    assert registered["lastVerifiedAt"] == "2026-08-25T00:47:51.501299+00:00"

    result = value.recommend("remove an image background")
    candidate = next(row for row in result["matched"] if row["capabilityId"] == capability_id)
    assert candidate["status"] == "VERIFIED"
    assert candidate["healthState"] == "HEALTHY"
    assert result["recommended"]["capabilityId"] == capability_id
    assert result["createOurOwn"] is False


def test_a2a_descriptor_remains_discovered_without_owner_evidence():
    value = registry()
    a2a = next(row for row in value.list() if row["capabilityId"] == "twis.a2a-descriptor")
    assert a2a["status"] == "DISCOVERED"
    assert a2a["lastVerifiedAt"] == ""
    assert a2a["lastHealthCheckAt"] == ""


def test_verification_age_is_visible():
    now = datetime(2026, 8, 23, tzinfo=timezone.utc)
    base = {"verificationPolicyDays": 30}
    assert verification_age({**base, "lastVerifiedAt": (now - timedelta(days=3)).isoformat()}, now) == "CURRENT"
    assert verification_age({**base, "lastVerifiedAt": (now - timedelta(days=20)).isoformat()}, now) == "AGING"
    assert verification_age({**base, "lastVerifiedAt": (now - timedelta(days=31)).isoformat()}, now) == "STALE"
    assert verification_age({**base, "lastVerifiedAt": ""}, now) == "UNKNOWN"


def test_hardware_binding_hash_excludes_volatile_free_memory_and_disk(monkeypatch):
    volatile = {"available": 1000, "load": 90, "free": 2000}
    monkeypatch.setattr(capability_registry_module, "_memory", lambda: {"totalBytes": 8_000_000_000, "availableBytes": volatile["available"], "loadPercent": volatile["load"]})
    usage = type("DiskUsage", (), {"total": 100_000, "used": 98_000, "free": volatile["free"]})
    monkeypatch.setattr(capability_registry_module.shutil, "disk_usage", lambda _root: usage)
    first = capability_registry_module.hardware_profile(ROOT)
    volatile.update({"available": 500, "load": 96, "free": 750})
    usage.free = volatile["free"]
    second = capability_registry_module.hardware_profile(ROOT)
    assert first["memory"]["availableBytes"] != second["memory"]["availableBytes"]
    assert first["disk"]["freeBytes"] != second["disk"]["freeBytes"]
    assert first["profileHash"] == second["profileHash"]


def test_agent_skill_discovery_is_metadata_only_and_scripts_remain_inactive(tmp_path: Path):
    root = tmp_path / "skills"
    skill = root / "safe-inspector"
    (skill / "scripts").mkdir(parents=True)
    (skill / "references").mkdir()
    (skill / "assets").mkdir()
    sentinel = tmp_path / "script-ran.txt"
    (skill / "SKILL.md").write_text("---\nname: safe-inspector\ndescription: Inspect a bounded source safely.\n---\n# Instructions\nRead only.\n", encoding="utf-8")
    (skill / "scripts" / "danger.py").write_text(f"from pathlib import Path\nPath({str(sentinel)!r}).write_text('ran')\n", encoding="utf-8")
    (skill / "references" / "guide.md").write_text("reference", encoding="utf-8")
    (skill / "assets" / "sample.txt").write_text("asset", encoding="utf-8")
    result = discover_skills([root])
    assert result["executedScripts"] == 0 and result["errors"] == []
    assert result["skills"][0]["resources"] == {"scripts": 1, "references": 1, "assets": 1}
    assert result["skills"][0]["authorityLevel"] == "read-only"
    assert result["skills"][0]["scriptExecution"] == "BLOCKED-PENDING-SEPARATE-INSPECTION"
    assert not sentinel.exists()


def test_agent_skill_invalid_frontmatter_and_malformed_metadata_are_reported(tmp_path: Path):
    root = tmp_path / "skills"
    bad_front = root / "bad-front"
    bad_front.mkdir(parents=True)
    (bad_front / "SKILL.md").write_text("name: bad-front\n", encoding="utf-8")
    malformed = root / "wrong-folder"
    malformed.mkdir()
    (malformed / "SKILL.md").write_text("---\nname: another-name\ndescription: Wrong directory.\n---\n", encoding="utf-8")
    result = discover_skills([root])
    assert result["skills"] == []
    assert {error["code"] for error in result["errors"]} == {"skill_frontmatter_invalid", "skill_metadata_invalid"}


class McpFixture(BaseHTTPRequestHandler):
    calls: list[str] = []
    headers_seen: list[tuple[str | None, str | None]] = []

    def do_POST(self):  # noqa: N802
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
        method = body["method"]
        type(self).calls.append(method)
        type(self).headers_seen.append((self.headers.get("MCP-Protocol-Version"), self.headers.get("Mcp-Method")))
        result = {
            "server/discover": {"name": "TWIS disposable fixture", "version": "1"},
            "tools/list": {"tools": [{"name": "inspect", "description": "Read metadata", "inputSchema": {"type": "object"}, "outputSchema": {"type": "object"}}]},
            "resources/list": {"resources": [{"uri": "twis://fixture", "name": "Fixture"}]},
        }[method]
        raw = json.dumps({"jsonrpc": "2.0", "id": body["id"], "result": result}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_args):
        return


def test_mcp_current_discovery_catalogs_schemas_without_enabling_or_executing_tools():
    McpFixture.calls = []
    McpFixture.headers_seen = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), McpFixture)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    endpoint = f"http://127.0.0.1:{server.server_address[1]}/mcp"
    try:
        result = McpCatalog([]).discover_local(endpoint)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
    assert McpFixture.calls == ["server/discover", "tools/list", "resources/list"]
    assert all(version == MCP_PROTOCOL_VERSION and method == call for (version, method), call in zip(McpFixture.headers_seen, McpFixture.calls))
    assert result["protocolVersion"] == "2026-07-28"
    assert result["toolCount"] == 1 and result["resourceCount"] == 1
    assert result["tools"][0]["inputSchema"]["type"] == "object"
    assert result["autoEnabledTools"] == 0 and result["executedTools"] == 0


def test_mcp_rejects_external_endpoints_and_reports_offline_truthfully():
    catalog = McpCatalog([])
    with pytest.raises(CapabilityError) as denied:
        catalog.discover_local("https://example.com/mcp")
    assert denied.value.code == "mcp_endpoint_denied"
    with pytest.raises(CapabilityError) as offline:
        catalog.discover_local("http://127.0.0.1:1/mcp")
    assert offline.value.code == "mcp_offline"


def test_a2a_agent_card_is_descriptor_only():
    card = {
        "name": "Fixture", "description": "Descriptor", "version": "1",
        "supportedInterfaces": [{"url": "https://invalid.example", "protocolBinding": "HTTP+JSON", "protocolVersion": "1.0"}],
        "capabilities": {}, "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain"], "skills": [],
    }
    result = validate_a2a_descriptor(card)
    assert result["valid"] is True and result["execution"] == "DEFERRED"
    assert result["interfaces"] == [{"url": "https://invalid.example", "protocolBinding": "HTTP+JSON", "protocolVersion": "1.0"}]
    assert result["authDeclared"] is False
    with pytest.raises(CapabilityError):
        validate_a2a_descriptor({"name": "missing fields"})
