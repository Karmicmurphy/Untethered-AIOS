from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from copy import deepcopy
from pathlib import Path

import pytest

from companion.capability_inspection import CapabilityInspectionService, InspectionError, static_only_authority
from companion.background_removal_inspection import (
    CAPABILITY_ID as BACKGROUND_REMOVAL_CAPABILITY_ID,
    COMMAND_ID as BACKGROUND_REMOVAL_COMMAND_ID,
    authority_template as background_removal_authority,
    inspect_opencv_grabcut,
)
from companion.capability_registry import CapabilityRegistry


ROOT = Path(__file__).resolve().parents[1]


def database(path: Path):
    def connect():
        con = sqlite3.connect(path)
        con.row_factory = sqlite3.Row
        return con
    con = connect()
    con.executescript("""
    CREATE TABLE projects(id TEXT PRIMARY KEY);
    CREATE TABLE jobs(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,operation TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL DEFAULT '{}',result TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    CREATE TABLE receipts(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,action TEXT NOT NULL,actor TEXT NOT NULL,details TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL);
    INSERT INTO projects(id) VALUES('p');
    """)
    con.commit(); con.close()
    return connect


def source_pack(path: Path, *, current: bool = False, verdict: str = "NEEDS_REVIEW") -> Path:
    payload = json.loads((ROOT / "config" / "capability-inspection-sources.json").read_text(encoding="utf-8"))
    item = payload["capabilities"]["external.rembg-cpu-candidate"]
    if current: item["inspectedVersion"] = item["catalogVersionAtDiscovery"]
    item["staticVerdict"] = verdict
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def service(tmp_path: Path, *, adapter=None, current=False, verdict="NEEDS_REVIEW"):
    tmp_path.mkdir(parents=True, exist_ok=True)
    registry = CapabilityRegistry(ROOT / "config" / "capability-registry.json", root=ROOT)
    adapters = {"fixture.echo": adapter} if adapter else {}
    svc = CapabilityInspectionService(database(tmp_path / "test.sqlite3"), registry, ROOT, source_path=source_pack(tmp_path / "sources.json", current=current, verdict=verdict), temp_root=tmp_path / "disposable", functional_adapters=adapters)
    registry.set_verification_provider(svc.verification_overlays)
    return svc, registry


def functional_authority(svc: CapabilityInspectionService):
    value = static_only_authority(svc.temp_root)
    value.update({"writes": ["disposable workspace", "inspection job result", "receipt"], "commands": ["fixture.echo"], "functionalTest": True})
    return value


def approve(svc, value, authority):
    job = svc.create_plan({"projectId": "p", "capabilityId": "external.rembg-cpu-candidate", "authority": authority, "note": "bounded test"}, actor="owner")
    return svc.decide_plan(job["inspectionId"], "approve", "Approve exact plan for isolated test.", actor="owner")


def test_discovered_static_inspection_requires_plan_approval_and_records_real_rembg_uncertainty(tmp_path: Path):
    svc, registry = service(tmp_path)
    plan = svc.create_plan({"projectId": "p", "capabilityId": "external.rembg-cpu-candidate", "authority": static_only_authority(svc.temp_root), "note": "static only"}, actor="owner")
    assert plan["status"] == "inspection_plan_pending" and plan["plan"]["capabilityVersion"] == "2.0.81"
    assert len(plan["plan"]["inspectionSourceHash"]) == 64
    with pytest.raises(InspectionError) as denied: svc.execute(plan["inspectionId"], actor="owner")
    assert denied.value.code == "inspection_plan_approval_required"
    svc.decide_plan(plan["inspectionId"], "approve", "Approve static evidence only.", actor="owner")
    result = svc.execute(plan["inspectionId"], actor="owner")
    assert result["status"] == "needs_review"
    assert result["evidence"]["sourceEvidence"]["inspectedVersion"] == "2.0.81"
    assert result["evidence"]["sourceEvidence"]["versionMismatch"] is False
    assert result["evidence"]["functionalEvidence"]["executed"] is False
    assert result["evidence"]["networkActivity"] == [] and result["evidence"]["filesystemActivity"] == []
    assert next(row for row in registry.list() if row["capabilityId"] == "external.rembg-cpu-candidate")["status"] == "DISCOVERED"
    with pytest.raises(InspectionError) as no_self_promotion:
        svc.owner_decision(result["inspectionId"], "verify", "Do not permit this.", result["evidenceHash"], actor="owner")
    assert no_self_promotion.value.code == "inspection_verification_denied"


def test_exact_candidate_owner_verification_is_hash_version_and_hardware_bound(tmp_path: Path):
    def adapter(context):
        guard = context["guard"]
        data = b"TWIS inspection fixture"
        guard.write_bytes("output.bin", data)
        assert guard.read_bytes("output.bin") == data
        digest = hashlib.sha256(data).hexdigest().upper()
        return {"functionalEvidence": {"state": "PASSED", "validOutput": True}, "performanceEvidence": {"elapsedSeconds": 0.01, "peakRamBytes": None, "cpuObservation": "bounded fixture"}, "inputHashes": [], "outputHashes": [digest]}
    svc, registry = service(tmp_path, adapter=adapter, current=True, verdict="VERIFICATION_CANDIDATE")
    approved = approve(svc, {}, functional_authority(svc))
    result = svc.execute(approved["inspectionId"], actor="owner")
    assert result["status"] == "verification_candidate" and result["evidence"]["cleanupResult"]["complete"] is True
    row = next(row for row in registry.list() if row["capabilityId"] == "external.rembg-cpu-candidate")
    assert row["status"] == "VERIFICATION_CANDIDATE" and row["inspectionEvidence"]["evidenceHash"] == result["evidenceHash"]
    with pytest.raises(InspectionError) as stale: svc.owner_decision(result["inspectionId"], "verify", "Exact evidence accepted.", "0" * 64, actor="owner")
    assert stale.value.code == "inspection_evidence_stale"
    verified = svc.owner_decision(result["inspectionId"], "verify", "Exact evidence accepted.", result["evidenceHash"], actor="owner")
    assert verified["status"] == "verified"
    assert next(row for row in registry.list() if row["capabilityId"] == "external.rembg-cpu-candidate")["status"] == "VERIFIED"


@pytest.mark.parametrize("kind", ["write", "network", "traversal"])
def test_guard_denies_undeclared_write_network_and_path_traversal_with_cleanup(tmp_path: Path, kind: str):
    def adapter(context):
        guard = context["guard"]
        if kind == "write": guard.authority["writes"] = []; guard.write_bytes("x", b"x")
        if kind == "network": guard.record_network("evil.example", 1)
        if kind == "traversal": guard.write_bytes("../escape", b"x")
        return {"functionalEvidence": {"state": "PASSED"}}
    svc, _ = service(tmp_path, adapter=adapter, current=True, verdict="VERIFICATION_CANDIDATE")
    job = approve(svc, {}, functional_authority(svc))
    with pytest.raises(InspectionError) as error: svc.execute(job["inspectionId"], actor="owner")
    assert error.value.code in {"inspection_write_denied", "inspection_network_denied", "inspection_path_denied"}
    assert svc.get(job["inspectionId"])["status"] == "failed"
    assert not (svc.temp_root / job["inspectionId"]).exists()


def test_timeout_malformed_evidence_single_active_plan_and_stale_plan_fail_closed(tmp_path: Path):
    def slow(_context): time.sleep(1.2); return {"functionalEvidence": {"state": "PASSED"}}
    svc, _ = service(tmp_path, adapter=slow, current=True, verdict="VERIFICATION_CANDIDATE")
    authority = functional_authority(svc); authority["timeoutSeconds"] = 1
    job = approve(svc, {}, authority)
    with pytest.raises(InspectionError) as timeout: svc.execute(job["inspectionId"], actor="owner")
    assert timeout.value.code == "inspection_timeout" and svc.get(job["inspectionId"])["status"] == "failed"

    svc2, _ = service(tmp_path / "second", adapter=lambda _context: {"bad": True}, current=True, verdict="VERIFICATION_CANDIDATE")
    job2 = approve(svc2, {}, functional_authority(svc2))
    with pytest.raises(InspectionError) as malformed: svc2.execute(job2["inspectionId"], actor="owner")
    assert malformed.value.code == "inspection_evidence_invalid"

    svc3, _ = service(tmp_path / "third")
    pending = svc3.create_plan({"projectId": "p", "capabilityId": "external.rembg-cpu-candidate", "authority": static_only_authority(svc3.temp_root)}, actor="owner")
    with pytest.raises(InspectionError) as busy: svc3.create_plan({"projectId": "p", "capabilityId": "external.openvino-future", "authority": static_only_authority(svc3.temp_root)}, actor="owner")
    assert busy.value.code == "inspection_busy"
    con = svc3.connect(); row = con.execute("SELECT payload FROM jobs WHERE id=?", (pending["inspectionId"],)).fetchone(); payload = json.loads(row[0]); payload["plan"]["ownerNote"] = "tampered"; con.execute("UPDATE jobs SET payload=? WHERE id=?", (json.dumps(payload), pending["inspectionId"])); con.commit(); con.close()
    with pytest.raises(InspectionError) as stale_plan: svc3.decide_plan(pending["inspectionId"], "approve", "approve", actor="owner")
    assert stale_plan.value.code == "inspection_plan_stale"


def test_registry_cannot_self_promote_without_owner_evidence():
    registry = CapabilityRegistry(ROOT / "config" / "capability-registry.json", root=ROOT)
    capability_id = "external.rembg-cpu-candidate"
    registry.transition(capability_id, "INSPECTING")
    registry.transition(capability_id, "TESTING")
    registry.transition(capability_id, "VERIFICATION_CANDIDATE")
    with pytest.raises(Exception) as denied: registry.transition(capability_id, "VERIFIED")
    assert getattr(denied.value, "code", "") == "capability_owner_approval_required"


def test_opencv_grabcut_candidate_creates_exact_pending_plan_without_execution(tmp_path: Path):
    registry = CapabilityRegistry(ROOT / "config" / "capability-registry.json", root=ROOT)
    source_path = ROOT / "config" / "capability-inspection-sources.json"
    temp_root = tmp_path / "disposable"
    svc = CapabilityInspectionService(
        database(tmp_path / "test.sqlite3"),
        registry,
        ROOT,
        source_path=source_path,
        temp_root=temp_root,
        functional_adapters={BACKGROUND_REMOVAL_COMMAND_ID: inspect_opencv_grabcut},
    )
    authority = background_removal_authority(temp_root)
    plan = svc.create_plan(
        {
            "projectId": "p",
            "capabilityId": BACKGROUND_REMOVAL_CAPABILITY_ID,
            "authority": authority,
            "note": "Create the exact synthetic inspection plan; do not execute.",
        },
        actor="owner",
    )
    assert plan["status"] == "inspection_plan_pending"
    assert plan["plan"]["approvalState"] == "PENDING"
    assert len(plan["plan"]["inspectionSourceHash"]) == 64
    assert plan["plan"]["authority"] == authority
    assert plan["plan"]["authority"]["commands"] == [BACKGROUND_REMOVAL_COMMAND_ID]
    assert plan["plan"]["authority"]["credentials"] == []
    assert plan["plan"]["authority"]["environment"] == []
    assert not temp_root.exists()
    with pytest.raises(InspectionError) as blocked:
        svc.execute(plan["inspectionId"], actor="owner")
    assert blocked.value.code == "inspection_plan_approval_required"
    assert not temp_root.exists()


def test_opencv_grabcut_candidate_rejects_unregistered_command(tmp_path: Path):
    registry = CapabilityRegistry(ROOT / "config" / "capability-registry.json", root=ROOT)
    temp_root = tmp_path / "disposable"
    svc = CapabilityInspectionService(
        database(tmp_path / "test.sqlite3"),
        registry,
        ROOT,
        source_path=ROOT / "config" / "capability-inspection-sources.json",
        temp_root=temp_root,
        functional_adapters={BACKGROUND_REMOVAL_COMMAND_ID: inspect_opencv_grabcut},
    )
    authority = background_removal_authority(temp_root)
    authority["commands"] = ["owner-supplied-shell"]
    with pytest.raises(InspectionError) as denied:
        svc.create_plan({"projectId": "p", "capabilityId": BACKGROUND_REMOVAL_CAPABILITY_ID, "authority": authority}, actor="owner")
    assert denied.value.code == "inspection_adapter_unavailable"
