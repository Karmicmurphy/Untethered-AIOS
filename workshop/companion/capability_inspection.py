from __future__ import annotations

import hashlib
import json
import shutil
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .capability_registry import CapabilityError, CapabilityRegistry, canonical_json, qualify_hardware, sha256_text


SCHEMA_VERSION = "twis-capability-inspection-v1"
OPERATION = "capability-inspection"
ACTIVE = {"inspection_plan_pending", "inspection_plan_approved", "inspection_running"}
TERMINAL = {"verification_candidate", "needs_review", "blocked", "incompatible", "failed", "verified", "cancelled", "plan_rejected"}
VERDICTS = {"VERIFICATION_CANDIDATE", "BLOCKED", "INCOMPATIBLE", "FAILED", "NEEDS_REVIEW"}
OVERLAY_STATUSES = {"VERIFICATION_CANDIDATE", "BLOCKED", "INCOMPATIBLE", "FAILED", "VERIFIED"}
AUTHORITY_FIELDS = {
    "reads", "writes", "network", "allowedDestinations", "downloads", "maxDownloadBytes",
    "runtime", "commands", "temporaryWorkspace", "credentials", "environment", "hardwareTest",
    "timeoutSeconds", "cleanup", "expectedEvidence", "functionalTest",
}


class InspectionError(ValueError):
    def __init__(self, code: str, message: str, *, status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash(value: Any) -> str:
    return sha256_text(canonical_json(value))


def _json(value: str | None) -> dict[str, Any]:
    try:
        parsed = json.loads(value or "{}")
    except json.JSONDecodeError as exc:
        raise InspectionError("inspection_record_invalid", "Stored inspection JSON is malformed", status=500) from exc
    if not isinstance(parsed, dict):
        raise InspectionError("inspection_record_invalid", "Stored inspection JSON must be an object", status=500)
    return parsed


def validate_authority(value: Any, *, root: Path, temp_root: Path) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != AUTHORITY_FIELDS:
        raise InspectionError("inspection_authority_invalid", "Inspection authority must use every fixed manifest field and no extras")
    result = deepcopy(value)
    for field in ("reads", "writes", "network", "allowedDestinations", "downloads", "commands", "credentials", "environment", "expectedEvidence"):
        if not isinstance(result[field], list) or any(not isinstance(item, str) or not item.strip() for item in result[field]):
            raise InspectionError("inspection_authority_invalid", f"authority.{field} must be a string array")
    for field in ("runtime", "temporaryWorkspace", "cleanup"):
        if not isinstance(result[field], str):
            raise InspectionError("inspection_authority_invalid", f"authority.{field} must be a string")
    for field in ("hardwareTest", "functionalTest"):
        if not isinstance(result[field], bool):
            raise InspectionError("inspection_authority_invalid", f"authority.{field} must be boolean")
    if not isinstance(result["maxDownloadBytes"], int) or result["maxDownloadBytes"] < 0:
        raise InspectionError("inspection_authority_invalid", "maxDownloadBytes must be a nonnegative integer")
    if not isinstance(result["timeoutSeconds"], int) or not 1 <= result["timeoutSeconds"] <= 900:
        raise InspectionError("inspection_authority_invalid", "timeoutSeconds must be between 1 and 900")
    if not result["network"] and (result["allowedDestinations"] or result["downloads"] or result["maxDownloadBytes"]):
        raise InspectionError("inspection_authority_invalid", "Network-disabled authority cannot declare destinations or downloads")
    allowed_reads = {"registered capability metadata", "measured hardware profile", "curated official-source evidence", "disposable synthetic input"}
    allowed_writes = {"inspection job result", "receipt", "disposable workspace"}
    if set(result["reads"]) - allowed_reads or set(result["writes"]) - allowed_writes:
        raise InspectionError("inspection_authority_invalid", "Inspection reads/writes must use the fixed bounded resource vocabulary")
    if result["credentials"] or result["environment"]:
        raise InspectionError("inspection_persistence_denied", "Capability inspections cannot access credentials or process environment")
    if not result["functionalTest"] and (result["network"] or result["commands"]):
        raise InspectionError("inspection_authority_invalid", "Static inspection cannot request network or command authority")
    if result["functionalTest"] and not result["commands"]:
        raise InspectionError("inspection_authority_invalid", "A functional test requires a fixed registered command identifier")
    workspace = Path(result["temporaryWorkspace"] or temp_root).resolve()
    allowed = temp_root.resolve()
    protected = root.resolve()
    if workspace != allowed and allowed not in workspace.parents:
        raise InspectionError("inspection_path_denied", "Temporary workspace must remain inside the inspection temp root")
    if workspace == protected or protected in workspace.parents or workspace in protected.parents:
        raise InspectionError("inspection_path_denied", "Inspection workspace cannot overlap the Workshop root")
    result["temporaryWorkspace"] = str(workspace)
    return result


def static_only_authority(temp_root: Path) -> dict[str, Any]:
    return {
        "reads": ["registered capability metadata", "measured hardware profile", "curated official-source evidence"],
        "writes": ["inspection job result", "receipt"],
        "network": [], "allowedDestinations": [], "downloads": [], "maxDownloadBytes": 0,
        "runtime": "TWIS Python standard-library static inspector", "commands": [],
        "temporaryWorkspace": str(temp_root), "credentials": [], "environment": [], "hardwareTest": True,
        "timeoutSeconds": 30, "cleanup": "remove disposable workspace; retain hash-addressed evidence in job result",
        "expectedEvidence": ["source", "dependencies", "permissions", "hardware", "security", "limitations"],
        "functionalTest": False,
    }


class InspectionGuard:
    """The only I/O surface passed to fixed functional adapters in V1."""
    def __init__(self, workspace: Path, authority: dict[str, Any]):
        self.workspace = workspace.resolve()
        self.authority = authority
        self.filesystem_activity: list[dict[str, Any]] = []
        self.network_activity: list[dict[str, Any]] = []

    def _path(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path or Path(relative_path).is_absolute():
            raise InspectionError("inspection_path_denied", "Adapter paths must be nonblank workspace-relative paths")
        path = (self.workspace / relative_path).resolve()
        if path != self.workspace and self.workspace not in path.parents:
            raise InspectionError("inspection_path_denied", "Adapter path traversal was blocked")
        return path

    def write_bytes(self, relative_path: str, content: bytes) -> Path:
        if "disposable workspace" not in self.authority["writes"]:
            raise InspectionError("inspection_write_denied", "Disposable writes were not approved")
        path = self._path(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        self.filesystem_activity.append({"operation": "write", "path": str(path), "bytes": len(content)})
        return path

    def read_bytes(self, relative_path: str) -> bytes:
        path = self._path(relative_path)
        if not path.is_file():
            raise InspectionError("inspection_read_denied", "Adapter requested an unavailable disposable file")
        data = path.read_bytes()
        self.filesystem_activity.append({"operation": "read", "path": str(path), "bytes": len(data)})
        return data

    def record_network(self, destination: str, downloaded_bytes: int = 0) -> None:
        if not self.authority["network"] or destination not in self.authority["allowedDestinations"]:
            raise InspectionError("inspection_network_denied", "Adapter network destination was not approved")
        if downloaded_bytes < 0 or downloaded_bytes > self.authority["maxDownloadBytes"]:
            raise InspectionError("inspection_download_denied", "Adapter download exceeds approved allowance")
        self.network_activity.append({"destination": destination, "downloadedBytes": downloaded_bytes})

    def record_workspace_summary(self, *, file_count: int, total_bytes: int) -> None:
        if "disposable workspace" not in self.authority["writes"]:
            raise InspectionError("inspection_write_denied", "Disposable writes were not approved")
        if not isinstance(file_count, int) or file_count < 0 or not isinstance(total_bytes, int) or total_bytes < 0:
            raise InspectionError("inspection_evidence_invalid", "Workspace summary values must be nonnegative integers")
        self.filesystem_activity.append({
            "operation": "bounded-workspace-summary",
            "path": str(self.workspace),
            "fileCount": file_count,
            "bytes": total_bytes,
        })


class CapabilityInspectionService:
    def __init__(
        self,
        connect: Callable[[], Any],
        registry: CapabilityRegistry,
        root: Path,
        *,
        source_path: Path | None = None,
        temp_root: Path | None = None,
        functional_adapters: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] | None = None,
    ):
        self.connect = connect
        self.registry = registry
        self.root = root.resolve()
        self.temp_root = (temp_root or root.parent / "capability-inspection-temp").resolve()
        path = source_path or root / "config" / "capability-inspection-sources.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schemaVersion") != "twis-capability-inspection-source-v1":
            raise InspectionError("inspection_source_invalid", "Inspection source envelope is invalid", status=500)
        self.sources = payload.get("capabilities") or {}
        self.type_depth = payload.get("typeDepth") or {}
        self.functional_adapters = functional_adapters or {}

    def _receipt(self, con: Any, project_id: str, action: str, actor: str, details: dict[str, Any]) -> str:
        receipt_id = str(uuid.uuid4())
        con.execute(
            "INSERT INTO receipts(id,project_id,action,actor,details,created_at) VALUES(?,?,?,?,?,?)",
            (receipt_id, project_id, action, actor, json.dumps(details, ensure_ascii=False, sort_keys=True), utc()),
        )
        return receipt_id

    def _job(self, con: Any, inspection_id: str) -> dict[str, Any]:
        row = con.execute("SELECT * FROM jobs WHERE id=? AND operation=?", (inspection_id, OPERATION)).fetchone()
        if not row:
            raise InspectionError("inspection_not_found", "Capability inspection was not found", status=404)
        keys = [column[0] for column in con.execute("SELECT * FROM jobs LIMIT 0").description]
        value = dict(zip(keys, row)) if not hasattr(row, "keys") else dict(row)
        value["payload"] = _json(value.get("payload"))
        value["result"] = _json(value.get("result"))
        return value

    def _public(self, job: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True, "inspectionId": job["id"], "projectId": job["project_id"], "status": job["status"],
            "plan": deepcopy(job["payload"].get("plan") or {}), "planApproval": deepcopy(job["payload"].get("planApproval") or {}),
            "evidence": deepcopy(job["result"].get("evidence") or {}), "evidenceHash": job["result"].get("evidenceHash"),
            "ownerDecision": deepcopy(job["result"].get("ownerDecision") or {}), "receipts": deepcopy(job["result"].get("receiptIds") or job["payload"].get("receiptIds") or []),
            "createdAt": job["created_at"], "updatedAt": job["updated_at"],
        }

    def create_plan(self, value: dict[str, Any], *, actor: str) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) - {"projectId", "capabilityId", "authority", "note"}:
            raise InspectionError("inspection_request_invalid", "Inspection plan fields are invalid")
        project_id = str(value.get("projectId") or "").strip()
        capability_id = str(value.get("capabilityId") or "").strip()
        if not project_id or not capability_id:
            raise InspectionError("inspection_request_invalid", "A real project and registered capability are required")
        record = self.registry.base_find(capability_id)
        inspection_source = deepcopy(self.sources.get(capability_id) or {})
        authority = validate_authority(value.get("authority"), root=self.root, temp_root=self.temp_root)
        if authority["functionalTest"]:
            if len(authority["commands"]) != 1 or authority["commands"][0] not in self.functional_adapters:
                raise InspectionError("inspection_adapter_unavailable", "The requested fixed functional adapter is not registered")
        con = self.connect()
        try:
            if not con.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                raise InspectionError("inspection_project_invalid", "Inspection must belong to a real Workshop project")
            if con.execute(
                f"SELECT 1 FROM jobs WHERE operation=? AND status IN ({','.join('?' for _ in ACTIVE)}) LIMIT 1",
                (OPERATION, *sorted(ACTIVE)),
            ).fetchone():
                raise InspectionError("inspection_busy", "Only one capability inspection may be active at a time", status=409)
            inspection_id = str(uuid.uuid4())
            trace_id = str(uuid.uuid4())
            created = utc()
            plan = {
                "schemaVersion": SCHEMA_VERSION, "inspectionId": inspection_id, "traceId": trace_id,
                "capabilityId": capability_id, "capabilityVersion": record["version"], "capabilityType": record["capabilityType"],
                "registryHash": self.registry.registry_hash, "hardwareProfileHash": self.registry.profile["profileHash"],
                "sourceHash": _hash(record), "inspectionSourceHash": _hash(inspection_source),
                "authority": authority, "authorityHash": _hash(authority),
                "inspectionDepth": self.type_depth.get(record["capabilityType"], "metadata only"),
                "ownerNote": str(value.get("note") or "")[:4000], "createdAt": created, "approvalState": "PENDING",
            }
            plan["planHash"] = _hash({key: val for key, val in plan.items() if key != "planHash"})
            receipt = self._receipt(con, project_id, "capability_inspection.plan_created", actor, {"inspectionId": inspection_id, "capabilityId": capability_id, "planHash": plan["planHash"]})
            payload = {"plan": plan, "planApproval": {}, "receiptIds": [receipt]}
            con.execute("INSERT INTO jobs(id,project_id,operation,status,payload,result,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)", (inspection_id, project_id, OPERATION, "inspection_plan_pending", json.dumps(payload, ensure_ascii=False), "{}", created, created))
            con.commit()
            return self._public(self._job(con, inspection_id))
        finally:
            con.close()

    def decide_plan(self, inspection_id: str, decision: str, note: str, *, actor: str) -> dict[str, Any]:
        if decision not in {"approve", "reject"} or not str(note or "").strip():
            raise InspectionError("inspection_plan_decision_invalid", "Approve or reject with a nonblank owner note")
        con = self.connect()
        try:
            job = self._job(con, inspection_id)
            if job["status"] != "inspection_plan_pending":
                raise InspectionError("inspection_state_invalid", "Inspection plan is not awaiting a decision", status=409)
            payload = job["payload"]
            plan = payload["plan"]
            expected = _hash({key: val for key, val in plan.items() if key != "planHash"})
            if expected != plan.get("planHash"):
                raise InspectionError("inspection_plan_stale", "Inspection plan hash does not match its contents", status=409)
            approval = {"decision": decision.upper(), "note": str(note).strip()[:4000], "actor": actor, "planHash": plan["planHash"], "decidedAt": utc()}
            payload["planApproval"] = approval
            status = "inspection_plan_approved" if decision == "approve" else "plan_rejected"
            receipt = self._receipt(con, job["project_id"], f"capability_inspection.plan_{decision}d", actor, {"inspectionId": inspection_id, **approval})
            payload.setdefault("receiptIds", []).append(receipt)
            con.execute("UPDATE jobs SET status=?,payload=?,updated_at=? WHERE id=?", (status, json.dumps(payload, ensure_ascii=False), utc(), inspection_id))
            con.commit()
            return self._public(self._job(con, inspection_id))
        finally:
            con.close()

    def execute(self, inspection_id: str, *, actor: str) -> dict[str, Any]:
        con = self.connect()
        workspace: Path | None = None
        try:
            job = self._job(con, inspection_id)
            if job["status"] != "inspection_plan_approved":
                raise InspectionError("inspection_plan_approval_required", "Inspection cannot run before exact plan approval", status=409)
            plan = job["payload"]["plan"]
            approval = job["payload"].get("planApproval") or {}
            if approval.get("decision") != "APPROVE" or approval.get("planHash") != plan.get("planHash"):
                raise InspectionError("inspection_plan_approval_required", "Approved plan hash does not match execution")
            if plan["registryHash"] != self.registry.registry_hash or plan["hardwareProfileHash"] != self.registry.profile["profileHash"]:
                raise InspectionError("inspection_plan_stale", "Registry or hardware changed; create a new inspection plan", status=409)
            record = self.registry.base_find(plan["capabilityId"])
            if record["version"] != plan["capabilityVersion"] or _hash(record) != plan["sourceHash"]:
                raise InspectionError("inspection_source_stale", "Capability source/version changed; create a new plan", status=409)
            source = deepcopy(self.sources.get(plan["capabilityId"]) or {})
            if plan.get("inspectionSourceHash") != _hash(source):
                raise InspectionError("inspection_source_stale", "Curated inspection-source evidence changed; create a new plan", status=409)
            authority = validate_authority(plan["authority"], root=self.root, temp_root=self.temp_root)
            con.execute("UPDATE jobs SET status=?,updated_at=? WHERE id=?", ("inspection_running", utc(), inspection_id)); con.commit()
            hardware = deepcopy(source.get("hardware") or qualify_hardware(record["hardwareRequirements"], self.registry.profile))
            workspace = Path(authority["temporaryWorkspace"]) / inspection_id
            functional = {"state": "NOT REQUESTED", "executed": False}
            performance = {"state": "NOT MEASURED", "elapsedSeconds": None, "peakRamBytes": None, "cpuObservation": "NOT MEASURED"}
            filesystem: list[dict[str, Any]] = []
            network: list[dict[str, Any]] = []
            started = time.monotonic()
            if authority["functionalTest"]:
                workspace.mkdir(parents=True, exist_ok=False)
                command_id = authority["commands"][0]
                adapter = self.functional_adapters[command_id]
                guard = InspectionGuard(workspace, authority)
                executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="twis-inspection")
                future = executor.submit(adapter, {"workspace": workspace, "authority": deepcopy(authority), "record": deepcopy(record), "guard": guard})
                try:
                    result = future.result(timeout=authority["timeoutSeconds"])
                except FutureTimeout as exc:
                    future.cancel()
                    raise InspectionError("inspection_timeout", "Functional inspection exceeded its approved timeout") from exc
                finally:
                    executor.shutdown(wait=False, cancel_futures=True)
                if not isinstance(result, dict) or set(result) - {"functionalEvidence", "performanceEvidence", "networkActivity", "filesystemActivity", "inputHashes", "outputHashes"}:
                    raise InspectionError("inspection_evidence_invalid", "Functional adapter returned malformed evidence")
                functional = deepcopy(result.get("functionalEvidence") or {})
                functional.update({"state": functional.get("state", "COMPLETED"), "executed": True, "adapter": command_id})
                performance = deepcopy(result.get("performanceEvidence") or performance)
                network = deepcopy(result.get("networkActivity") or guard.network_activity)
                filesystem = deepcopy(result.get("filesystemActivity") or guard.filesystem_activity)
                if network != guard.network_activity or filesystem != guard.filesystem_activity:
                    raise InspectionError("inspection_evidence_invalid", "Adapter activity evidence must come from the bounded inspection guard")
            elapsed = round(time.monotonic() - started, 6)
            if performance.get("elapsedSeconds") is None:
                performance["elapsedSeconds"] = elapsed
            version_mismatch = bool(source.get("inspectedVersion") and source.get("inspectedVersion") != plan["capabilityVersion"])
            verdict_key = "functionalVerdict" if functional.get("executed") else "staticVerdict"
            verdict = str(source.get(verdict_key) or ("VERIFICATION_CANDIDATE" if functional.get("executed") else "NEEDS_REVIEW"))
            if hardware.get("state") == "UNSUPPORTED": verdict = "INCOMPATIBLE"
            if hardware.get("state") == "TOO HEAVY": verdict = "INCOMPATIBLE"
            if version_mismatch: verdict = "NEEDS_REVIEW"
            if verdict not in VERDICTS:
                raise InspectionError("inspection_evidence_invalid", "Inspection verdict is invalid")
            cleanup = {"attempted": True, "complete": True, "workspace": str(workspace), "retained": "hash-addressed job evidence only"}
            if workspace.exists():
                shutil.rmtree(workspace)
            evidence = {
                "inspectionId": inspection_id, "capabilityId": plan["capabilityId"], "capabilityVersion": plan["capabilityVersion"],
                "registryHash": plan["registryHash"], "hardwareProfileHash": plan["hardwareProfileHash"], "inspectionPlanHash": plan["planHash"], "traceId": plan["traceId"],
                "sourceEvidence": {**deepcopy(source.get("source") or {"registryRecord": record["source"]}), "inspectionSourceHash": plan["inspectionSourceHash"], "inspectedVersion": source.get("inspectedVersion", plan["capabilityVersion"]), "versionMismatch": version_mismatch},
                "licenseEvidence": {"sourceLicense": (source.get("source") or {}).get("sourceLicense", record["license"]), "modelLicense": (source.get("model") or {}).get("license", "Not applicable or unknown")},
                "dependencyEvidence": deepcopy(source.get("dependencies") or {"state": "NOT EXPOSED"}),
                "permissionEvidence": {"approvedAuthority": authority, "authorityHash": plan["authorityHash"], "exceeded": False},
                "hardwareEvidence": {"profile": deepcopy(self.registry.profile), "qualification": hardware},
                "functionalEvidence": functional, "performanceEvidence": performance,
                "securityObservations": deepcopy(source.get("security") or [record["securityNotes"]]),
                "networkActivity": network, "filesystemActivity": filesystem,
                "inputHashes": deepcopy((result if authority["functionalTest"] else {}).get("inputHashes") or []),
                "outputHashes": deepcopy((result if authority["functionalTest"] else {}).get("outputHashes") or []),
                "cleanupResult": cleanup, "limitations": deepcopy(source.get("limitations") or [record["knownLimitations"]]),
                "finalInspectionVerdict": verdict,
            }
            evidence_hash = _hash(evidence)
            result_record = {"evidence": evidence, "evidenceHash": evidence_hash, "receiptIds": deepcopy(job["payload"].get("receiptIds") or [])}
            receipt = self._receipt(con, job["project_id"], "capability_inspection.evidence_recorded", actor, {"inspectionId": inspection_id, "capabilityId": plan["capabilityId"], "planHash": plan["planHash"], "evidenceHash": evidence_hash, "verdict": verdict})
            result_record["receiptIds"].append(receipt)
            status = verdict.lower()
            con.execute("UPDATE jobs SET status=?,result=?,updated_at=? WHERE id=?", (status, json.dumps(result_record, ensure_ascii=False), utc(), inspection_id)); con.commit()
            return self._public(self._job(con, inspection_id))
        except Exception as exc:
            if workspace and workspace.exists():
                shutil.rmtree(workspace, ignore_errors=True)
            if isinstance(exc, InspectionError):
                try:
                    job = self._job(con, inspection_id)
                    if job["status"] == "inspection_running":
                        receipt = self._receipt(con, job["project_id"], "capability_inspection.failed", actor, {"inspectionId": inspection_id, "code": exc.code, "cleanupComplete": not bool(workspace and workspace.exists())})
                        con.execute("UPDATE jobs SET status=?,result=?,updated_at=? WHERE id=?", ("failed", json.dumps({"error": str(exc)[:1000], "receiptIds": [receipt]}, ensure_ascii=False), utc(), inspection_id)); con.commit()
                except Exception:
                    pass
                raise
            try:
                job = self._job(con, inspection_id)
                receipt = self._receipt(con, job["project_id"], "capability_inspection.failed", actor, {"inspectionId": inspection_id, "error": type(exc).__name__, "cleanupComplete": not bool(workspace and workspace.exists())})
                con.execute("UPDATE jobs SET status=?,result=?,updated_at=? WHERE id=?", ("failed", json.dumps({"error": str(exc)[:1000], "receiptIds": [receipt]}, ensure_ascii=False), utc(), inspection_id)); con.commit()
            except Exception:
                pass
            raise InspectionError("inspection_failed", f"Inspection failed: {exc}", status=500) from exc
        finally:
            con.close()

    def owner_decision(self, inspection_id: str, decision: str, note: str, evidence_hash: str, *, actor: str) -> dict[str, Any]:
        mapping = {"verify": "verified", "block": "blocked", "incompatible": "incompatible", "fail": "failed"}
        if decision not in mapping or not str(note or "").strip():
            raise InspectionError("inspection_owner_decision_invalid", "Owner decision and nonblank note are required")
        con = self.connect()
        try:
            job = self._job(con, inspection_id)
            if job["status"] not in {"verification_candidate", "needs_review", "blocked", "incompatible", "failed"}:
                raise InspectionError("inspection_state_invalid", "Inspection evidence is not awaiting an owner decision", status=409)
            stored_hash = job["result"].get("evidenceHash")
            if not stored_hash or evidence_hash != stored_hash:
                raise InspectionError("inspection_evidence_stale", "Owner decision must bind the exact evidence hash", status=409)
            if decision == "verify" and job["status"] != "verification_candidate":
                raise InspectionError("inspection_verification_denied", "Only a VERIFICATION_CANDIDATE may become VERIFIED", status=409)
            plan = job["payload"]["plan"]
            if plan["capabilityVersion"] != self.registry.base_find(plan["capabilityId"])["version"] or plan["hardwareProfileHash"] != self.registry.profile["profileHash"]:
                raise InspectionError("inspection_evidence_stale", "Version or hardware changed; old evidence cannot be approved", status=409)
            decision_record = {"decision": decision.upper(), "note": str(note).strip()[:4000], "actor": actor, "evidenceHash": stored_hash, "capabilityVersion": plan["capabilityVersion"], "hardwareProfileHash": plan["hardwareProfileHash"], "decidedAt": utc()}
            result = job["result"]; result["ownerDecision"] = decision_record
            receipt = self._receipt(con, job["project_id"], f"capability_inspection.owner_{decision}", actor, {"inspectionId": inspection_id, **decision_record})
            result.setdefault("receiptIds", []).append(receipt)
            con.execute("UPDATE jobs SET status=?,result=?,updated_at=? WHERE id=?", (mapping[decision], json.dumps(result, ensure_ascii=False), utc(), inspection_id)); con.commit()
            return self._public(self._job(con, inspection_id))
        finally:
            con.close()

    def get(self, inspection_id: str) -> dict[str, Any]:
        con = self.connect()
        try: return self._public(self._job(con, inspection_id))
        finally: con.close()

    def list(self, capability_id: str = "") -> dict[str, Any]:
        con = self.connect()
        try:
            rows = con.execute("SELECT id FROM jobs WHERE operation=? ORDER BY created_at DESC LIMIT 100", (OPERATION,)).fetchall()
            values = [self._public(self._job(con, row[0])) for row in rows]
            if capability_id: values = [item for item in values if item["plan"].get("capabilityId") == capability_id]
            return {"ok": True, "schemaVersion": SCHEMA_VERSION, "inspections": values}
        finally: con.close()

    def verification_overlays(self) -> dict[str, dict[str, Any]]:
        con = self.connect()
        try:
            rows = con.execute("SELECT * FROM jobs WHERE operation=? ORDER BY updated_at DESC", (OPERATION,)).fetchall()
            keys = [column[0] for column in con.execute("SELECT * FROM jobs LIMIT 0").description]
            overlays: dict[str, dict[str, Any]] = {}
            for raw in rows:
                row = dict(raw) if hasattr(raw, "keys") else dict(zip(keys, raw))
                payload, result = _json(row.get("payload")), _json(row.get("result"))
                plan, evidence = payload.get("plan") or {}, result.get("evidence") or {}
                capability_id = plan.get("capabilityId")
                status = str(row.get("status") or "").upper()
                if capability_id in overlays or status not in OVERLAY_STATUSES or not result.get("evidenceHash"):
                    continue
                overlays[capability_id] = {"status": status, "capabilityVersion": plan.get("capabilityVersion"), "hardwareProfileHash": plan.get("hardwareProfileHash"), "evidenceHash": result.get("evidenceHash"), "inspectionId": row["id"], "limitations": evidence.get("limitations") or [], "ownerDecision": result.get("ownerDecision") or {}}
            return overlays
        finally: con.close()
