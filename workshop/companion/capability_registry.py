from __future__ import annotations

import ctypes
import hashlib
import json
import os
import re
import shutil
import socket
import urllib.error
import urllib.parse
import urllib.request
import winreg
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


SCHEMA_VERSION = "twis-capability-v1"
MCP_PROTOCOL_VERSION = "2026-07-28"
CAPABILITY_TYPES = {
    "native", "agent-skill", "local-worker", "disposable-worker", "mcp", "a2a",
    "wasi-component", "comfy-workflow", "local-model-engine", "browser-engine",
    "cloud-free-tier", "media-runtime", "external-optional",
}
STATUSES = {
    "DISCOVERED", "INSPECTING", "TESTING", "VERIFICATION_CANDIDATE", "VERIFIED",
    "APPROVED", "DEGRADED", "OFFLINE", "INCOMPATIBLE", "RETIRED", "BLOCKED", "FAILED",
}
COST_CLASSES = {
    "local-free", "open-source-free", "free-tier", "free-with-account",
    "paid-optional", "paid-required",
}
AUTHORITY_LEVELS = {
    "read-only", "proposal-only", "write-with-approval", "execute-with-approval",
    "external-submit-with-approval", "blocked",
}
HEALTH_STATES = {"HEALTHY", "DEGRADED", "OFFLINE", "ERROR", "UNKNOWN", "NOT-INSTALLED"}
COMPATIBILITY_STATES = {"GOOD FIT", "MAY WORK", "TOO HEAVY", "UNSUPPORTED", "UNKNOWN"}
NETWORK_REQUIREMENTS = {"none", "optional", "required"}
TRANSITIONS = {
    "DISCOVERED": {"INSPECTING", "BLOCKED", "RETIRED"},
    "INSPECTING": {"TESTING", "BLOCKED", "INCOMPATIBLE", "RETIRED"},
    "TESTING": {"VERIFICATION_CANDIDATE", "DEGRADED", "OFFLINE", "INCOMPATIBLE", "BLOCKED", "FAILED", "RETIRED"},
    "VERIFICATION_CANDIDATE": {"VERIFIED", "BLOCKED", "INCOMPATIBLE", "FAILED", "RETIRED"},
    "VERIFIED": {"APPROVED", "DEGRADED", "OFFLINE", "BLOCKED", "RETIRED"},
    "APPROVED": {"DEGRADED", "OFFLINE", "BLOCKED", "RETIRED"},
    "DEGRADED": {"TESTING", "VERIFIED", "OFFLINE", "BLOCKED", "RETIRED"},
    "OFFLINE": {"TESTING", "VERIFIED", "DEGRADED", "BLOCKED", "RETIRED"},
    "INCOMPATIBLE": {"INSPECTING", "TESTING", "RETIRED"},
    "BLOCKED": {"INSPECTING", "TESTING", "RETIRED"},
    "FAILED": {"INSPECTING", "TESTING", "RETIRED"},
    "RETIRED": set(),
}
ELEVATED_AUTHORITY = {
    "write-with-approval", "execute-with-approval", "external-submit-with-approval",
}
WORD = re.compile(r"[a-z0-9][a-z0-9.+_-]*")
SKILL_NAME = re.compile(r"^[a-z0-9-]{1,64}$")


class CapabilityError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _registry_value(key_path: str, name: str) -> object | None:
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


class _MemoryStatus(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _memory() -> dict[str, int | None]:
    state = _MemoryStatus()
    state.dwLength = ctypes.sizeof(_MemoryStatus)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
        return {"totalBytes": None, "availableBytes": None, "loadPercent": None}
    return {
        "totalBytes": int(state.ullTotalPhys),
        "availableBytes": int(state.ullAvailPhys),
        "loadPercent": int(state.dwMemoryLoad),
    }


def _instruction_sets() -> list[str]:
    # Values are documented PROCESSOR_FEATURE_ID constants exposed by Kernel32.
    features = {3: "MMX", 6: "SSE", 10: "SSE2", 13: "SSE3", 17: "XSAVE", 18: "AVX", 40: "AVX2"}
    return [name for identifier, name in features.items() if ctypes.windll.kernel32.IsProcessorFeaturePresent(identifier)]


def hardware_profile(root: Path) -> dict[str, Any]:
    cpu_key = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
    os_key = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
    memory = _memory()
    disk = shutil.disk_usage(root)
    cpu_name = str(_registry_value(cpu_key, "ProcessorNameString") or "UNKNOWN").strip()
    gpu = "AMD Radeon R3 Graphics" if "Radeon R3" in cpu_name else "UNKNOWN"
    profile = {
        "schemaVersion": "twis-hardware-profile-v1",
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "cpu": {
            "name": cpu_name,
            "identifier": _registry_value(cpu_key, "Identifier") or "UNKNOWN",
            "vendor": _registry_value(cpu_key, "VendorIdentifier") or "UNKNOWN",
            "mhz": _registry_value(cpu_key, "~MHz"),
            "logicalProcessors": os.cpu_count(),
            "instructionSets": _instruction_sets(),
        },
        "memory": memory,
        "architecture": os.environ.get("PROCESSOR_ARCHITECTURE", "UNKNOWN"),
        "os": {
            "product": _registry_value(os_key, "ProductName") or "UNKNOWN",
            "build": _registry_value(os_key, "CurrentBuildNumber") or "UNKNOWN",
        },
        "gpu": {"name": gpu, "dedicatedMemoryBytes": None, "evidence": "processor identity" if gpu != "UNKNOWN" else "not exposed"},
        "disk": {"root": str(root.anchor), "totalBytes": disk.total, "freeBytes": disk.free},
    }
    identity = deepcopy({k: v for k, v in profile.items() if k not in {"capturedAt", "profileHash"}})
    identity["memory"].pop("availableBytes", None)
    identity["memory"].pop("loadPercent", None)
    identity["disk"].pop("freeBytes", None)
    profile["profileHash"] = sha256_text(canonical_json(identity))
    return profile


def qualify_hardware(requirements: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    vendor = str(profile["cpu"].get("vendor") or "").lower()
    allowed_vendors = [str(value).lower() for value in requirements.get("cpuVendors", [])]
    if allowed_vendors and not any(value in vendor for value in allowed_vendors):
        return {"state": "UNSUPPORTED", "reasons": ["Detected CPU vendor is outside the declared supported vendors."]}
    required_sets = {str(value).upper() for value in requirements.get("instructionSets", [])}
    available_sets = {str(value).upper() for value in profile["cpu"].get("instructionSets", [])}
    missing_sets = sorted(required_sets - available_sets)
    if missing_sets:
        return {"state": "UNSUPPORTED", "reasons": [f"Missing required instruction sets: {', '.join(missing_sets)}."]}
    if requirements.get("gpuRequired") is True:
        allowed_gpu = [str(value).lower() for value in requirements.get("gpuFamilies", [])]
        detected = str(profile["gpu"].get("name") or "").lower()
        if detected == "unknown" or allowed_gpu and not any(value in detected for value in allowed_gpu):
            return {"state": "UNSUPPORTED", "reasons": ["A compatible GPU is required and was not detected."]}
    total = profile["memory"].get("totalBytes")
    ram_mib = requirements.get("ramMiB")
    if isinstance(ram_mib, (int, float)) and total:
        required_bytes = int(ram_mib * 1024 * 1024)
        if required_bytes > total:
            return {"state": "TOO HEAVY", "reasons": [f"Declared RAM need {ram_mib} MiB exceeds installed memory."]}
        if required_bytes > total * 0.55:
            reasons.append(f"Declared RAM need {ram_mib} MiB is more than 55% of installed memory.")
            return {"state": "MAY WORK", "reasons": reasons}
    disk_mib = requirements.get("diskMiB")
    if isinstance(disk_mib, (int, float)) and disk_mib * 1024 * 1024 > profile["disk"]["freeBytes"]:
        return {"state": "TOO HEAVY", "reasons": ["Declared disk need exceeds current free space."]}
    if requirements.get("unknown") is True:
        return {"state": "UNKNOWN", "reasons": ["Capability requirements are not yet measured."]}
    return {"state": "GOOD FIT", "reasons": reasons or ["Declared requirements fit the measured local profile."]}


def _require_string(record: dict[str, Any], name: str, *, allow_empty: bool = False) -> str:
    value = record.get(name)
    if not isinstance(value, str) or (not allow_empty and not value.strip()):
        raise CapabilityError("capability_schema_invalid", f"{name} must be a nonblank string")
    return value.strip()


def validate_capability(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise CapabilityError("capability_schema_invalid", "Capability must be an object")
    required = {
        "capabilityId", "name", "version", "description", "status", "source", "sourceUrl",
        "license", "lastVerifiedAt", "lastHealthCheckAt", "capabilityType", "inputTypes",
        "outputTypes", "engine", "runtime", "protocol", "adapter", "hardwareRequirements",
        "networkRequirement", "accountRequirement", "credentialRequirement", "costClass",
        "permissions", "authorityLevel", "provenanceSupport", "receiptSupport", "rollbackSupport",
        "healthState", "compatibilityState", "securityNotes", "knownLimitations",
        "replacementGroup", "preferredRank", "tags", "taskKeywords", "verificationPolicyDays",
        "evidence",
    }
    missing = sorted(required - set(record))
    if missing:
        raise CapabilityError("capability_schema_invalid", f"Capability fields missing: {', '.join(missing)}")
    optional = {"freeTierNotes", "quota", "quotaReset", "currentAvailability", "provider", "fallbackAvailable"}
    extras = sorted(set(record) - required - optional)
    if extras:
        raise CapabilityError("capability_schema_invalid", f"Unknown capability fields: {', '.join(extras)}")
    result = deepcopy(record)
    capability_id = _require_string(result, "capabilityId")
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{1,99}", capability_id):
        raise CapabilityError("capability_schema_invalid", "capabilityId is invalid")
    for name in ("name", "version", "description", "source", "license", "engine", "runtime", "securityNotes", "knownLimitations", "replacementGroup"):
        _require_string(result, name)
    for name in ("sourceUrl", "lastVerifiedAt", "lastHealthCheckAt", "protocol", "adapter", "credentialRequirement"):
        _require_string(result, name, allow_empty=True)
    if result["status"] not in STATUSES or result["capabilityType"] not in CAPABILITY_TYPES:
        raise CapabilityError("capability_schema_invalid", "Capability status or type is invalid")
    if result["costClass"] not in COST_CLASSES or result["authorityLevel"] not in AUTHORITY_LEVELS:
        raise CapabilityError("capability_schema_invalid", "Capability cost or authority is invalid")
    if result["healthState"] not in HEALTH_STATES or result["compatibilityState"] not in COMPATIBILITY_STATES:
        raise CapabilityError("capability_schema_invalid", "Capability health or compatibility is invalid")
    if result["networkRequirement"] not in NETWORK_REQUIREMENTS:
        raise CapabilityError("capability_schema_invalid", "networkRequirement is invalid")
    if result["status"] in {"DISCOVERED", "INSPECTING", "TESTING", "VERIFICATION_CANDIDATE", "INCOMPATIBLE", "BLOCKED", "FAILED", "RETIRED"} and result["authorityLevel"] in ELEVATED_AUTHORITY:
        raise CapabilityError("capability_authority_invalid", "Unapproved capability cannot receive execution, write, or external-submit authority")
    for name in ("inputTypes", "outputTypes", "tags", "taskKeywords", "evidence"):
        if not isinstance(result[name], list) or any(not isinstance(value, str) for value in result[name]):
            raise CapabilityError("capability_schema_invalid", f"{name} must be a string array")
    if not isinstance(result["permissions"], dict) or set(result["permissions"]) != {"reads", "writes", "network", "shell", "environment", "credentials", "models", "externalServices"}:
        raise CapabilityError("capability_schema_invalid", "permissions must use the fixed manifest fields")
    for name, value in result["permissions"].items():
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise CapabilityError("capability_schema_invalid", f"permissions.{name} must be a string array")
    if not isinstance(result["hardwareRequirements"], dict):
        raise CapabilityError("capability_schema_invalid", "hardwareRequirements must be an object")
    for name in ("accountRequirement", "provenanceSupport", "receiptSupport", "rollbackSupport"):
        if not isinstance(result[name], bool):
            raise CapabilityError("capability_schema_invalid", f"{name} must be boolean")
    for name in ("freeTierNotes", "quota", "quotaReset", "currentAvailability", "provider"):
        if name in result and not isinstance(result[name], str):
            raise CapabilityError("capability_schema_invalid", f"{name} must be a string")
    if "fallbackAvailable" in result and not isinstance(result["fallbackAvailable"], bool):
        raise CapabilityError("capability_schema_invalid", "fallbackAvailable must be boolean")
    if not isinstance(result["preferredRank"], int) or result["preferredRank"] < 0:
        raise CapabilityError("capability_schema_invalid", "preferredRank must be a nonnegative integer")
    if not isinstance(result["verificationPolicyDays"], int) or result["verificationPolicyDays"] < 1:
        raise CapabilityError("capability_schema_invalid", "verificationPolicyDays must be positive")
    return result


def verification_age(record: dict[str, Any], now: datetime | None = None) -> str:
    value = str(record.get("lastVerifiedAt") or "").strip()
    if not value:
        return "UNKNOWN"
    try:
        checked = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return "UNKNOWN"
    current = now or datetime.now(timezone.utc)
    days = max(0, (current - checked.astimezone(timezone.utc)).days)
    policy = int(record.get("verificationPolicyDays") or 30)
    if days <= max(1, policy // 2):
        return "CURRENT"
    if days <= policy:
        return "AGING"
    return "STALE"


class CapabilityRegistry:
    def __init__(self, path: Path, *, root: Path):
        self.path = path
        self.root = root
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schemaVersion") != SCHEMA_VERSION or not isinstance(payload.get("capabilities"), list):
            raise CapabilityError("capability_registry_invalid", "Capability registry envelope is invalid")
        self.profile = hardware_profile(root)
        self._records: dict[str, dict[str, Any]] = {}
        self._verification_provider: Callable[[], dict[str, dict[str, Any]]] | None = None
        for item in payload["capabilities"]:
            self.register(item)
        self._refresh_hash()

    def _refresh_hash(self) -> None:
        self.registry_hash = sha256_text(canonical_json([self._records[key] for key in sorted(self._records)]))

    def register(self, record: dict[str, Any]) -> dict[str, Any]:
        item = validate_capability(record)
        capability_id = item["capabilityId"]
        if capability_id in self._records:
            raise CapabilityError("capability_duplicate", f"Capability {capability_id} is already registered")
        self._records[capability_id] = item
        if hasattr(self, "registry_hash"):
            self._refresh_hash()
        return deepcopy(item)

    def transition(self, capability_id: str, status: str, *, owner_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
        if capability_id not in self._records:
            raise CapabilityError("capability_not_found", "Capability is not registered")
        current = self._records[capability_id]["status"]
        if status not in TRANSITIONS[current]:
            raise CapabilityError("capability_transition_invalid", f"Cannot transition {current} to {status}")
        if status == "VERIFIED":
            required = {"evidenceHash", "capabilityVersion", "hardwareProfileHash", "approvedAt", "approvedBy"}
            if not isinstance(owner_evidence, dict) or required - set(owner_evidence):
                raise CapabilityError("capability_owner_approval_required", "VERIFIED requires exact owner-approved evidence, version, and hardware bindings")
        self._records[capability_id]["status"] = status
        self._refresh_hash()
        return deepcopy(self._records[capability_id])

    def set_verification_provider(self, provider: Callable[[], dict[str, dict[str, Any]]] | None) -> None:
        self._verification_provider = provider

    def base_find(self, capability_id: str) -> dict[str, Any]:
        if capability_id not in self._records:
            raise CapabilityError("capability_not_found", "Capability is not registered")
        return deepcopy(self._records[capability_id])

    def _effective_records(self) -> dict[str, dict[str, Any]]:
        rows = deepcopy(self._records)
        overlays = self._verification_provider() if self._verification_provider else {}
        for capability_id, overlay in overlays.items():
            if capability_id not in rows or not isinstance(overlay, dict):
                continue
            if overlay.get("capabilityVersion") != rows[capability_id]["version"]:
                continue
            if overlay.get("hardwareProfileHash") != self.profile["profileHash"]:
                continue
            status = overlay.get("status")
            if status not in {"VERIFICATION_CANDIDATE", "VERIFIED", "BLOCKED", "INCOMPATIBLE", "FAILED"}:
                continue
            rows[capability_id]["status"] = status
            rows[capability_id]["inspectionEvidence"] = deepcopy(overlay)
        return rows

    def snapshot(self) -> dict[str, Any]:
        return {"schemaVersion": SCHEMA_VERSION, "registryHash": self.registry_hash, "count": len(self._records)}

    def list(self, *, filters: Iterable[str] = (), query: str = "") -> list[dict[str, Any]]:
        requested = {value.strip().lower() for value in filters if value.strip()}
        query_tokens = set(WORD.findall(query.lower()))
        rows: list[dict[str, Any]] = []
        for record in self._effective_records().values():
            fit = qualify_hardware(record["hardwareRequirements"], self.profile)
            fit_order = {"GOOD FIT": 0, "MAY WORK": 1, "UNKNOWN": 2, "TOO HEAVY": 3, "UNSUPPORTED": 4}
            declared_fit = record["compatibilityState"]
            if fit_order[declared_fit] > fit_order[fit["state"]]:
                fit = {
                    "state": declared_fit,
                    "reasons": [
                        "Registry compatibility remains conservative until this capability is measured on the current machine."
                    ],
                }
            haystack = " ".join([
                record["name"], record["description"], record["capabilityType"], record["replacementGroup"],
                *record["tags"], *record["taskKeywords"], record["status"], record["costClass"],
            ]).lower()
            categories = {
                record["status"].lower(), record["capabilityType"].lower(), record["costClass"].lower(),
                record["replacementGroup"].lower(), *(value.lower() for value in record["tags"]),
            }
            if "installed" in requested and record["healthState"] == "NOT-INSTALLED":
                continue
            if "free" in requested and record["costClass"] not in {"local-free", "open-source-free", "free-tier", "free-with-account"}:
                continue
            if "local" in requested and record["networkRequirement"] != "none":
                continue
            if "offline" in requested and record["networkRequirement"] != "none":
                continue
            if requested - {"installed", "free", "local", "offline"} and not (requested - {"installed", "free", "local", "offline"}).issubset(categories):
                continue
            if query_tokens and not all(token in haystack for token in query_tokens):
                continue
            item = deepcopy(record)
            item["hardwareFit"] = fit
            item["verificationAge"] = verification_age(record)
            rows.append(item)
        rows.sort(key=lambda item: (item["preferredRank"], item["name"].casefold(), item["capabilityId"]))
        return rows

    def recommend(self, request: str) -> dict[str, Any]:
        text = request.strip()
        if not text or len(text) > 2000:
            raise CapabilityError("capability_request_invalid", "Capability request must contain 1 to 2000 characters")
        tokens = set(WORD.findall(text.lower()))
        scored: list[tuple[int, dict[str, Any]]] = []
        for record in self.list():
            words = set(WORD.findall(" ".join([record["replacementGroup"], record["name"], record["description"], *record["taskKeywords"]]).lower()))
            score = len(tokens & words) * 10
            for keyword in record["taskKeywords"]:
                keyword_tokens = set(WORD.findall(keyword.lower()))
                if keyword.lower() in text.lower() or (keyword_tokens and keyword_tokens.issubset(tokens)):
                    # Specific capability phrases outrank generic one-word matches.
                    score += 25 * len(keyword_tokens)
            if score:
                scored.append((score, record))
        status_rank = {"APPROVED": 0, "VERIFIED": 1, "VERIFICATION_CANDIDATE": 2, "TESTING": 3, "DISCOVERED": 4, "DEGRADED": 5, "OFFLINE": 6, "INCOMPATIBLE": 7, "BLOCKED": 8, "FAILED": 9, "RETIRED": 10}
        cost_rank = {"local-free": 0, "open-source-free": 1, "free-tier": 2, "free-with-account": 3, "paid-optional": 4, "paid-required": 5}
        fit_rank = {"GOOD FIT": 0, "MAY WORK": 1, "UNKNOWN": 2, "TOO HEAVY": 3, "UNSUPPORTED": 4}
        scored.sort(key=lambda pair: (-pair[0], status_rank[pair[1]["status"]], cost_rank[pair[1]["costClass"]], fit_rank[pair[1]["hardwareFit"]["state"]], pair[1]["preferredRank"]))
        matches = [item for _, item in scored[:8]]
        target_group = matches[0]["replacementGroup"] if matches else ""
        same_group = [item for item in matches if item["replacementGroup"] == target_group]
        usable = [
            item
            for item in same_group
            if item["status"] in {"APPROVED", "VERIFIED"}
            and item["healthState"] == "HEALTHY"
            and item["hardwareFit"]["state"] in {"GOOD FIT", "MAY WORK"}
            and item["costClass"] != "paid-required"
        ]
        discovered = [item for item in same_group if item["status"] in {"DISCOVERED", "INSPECTING", "TESTING", "VERIFICATION_CANDIDATE"}]
        return {
            "schemaVersion": "twis-capability-recommendation-v1",
            "request": text,
            "registryHash": self.registry_hash,
            "replacementGroup": target_group or None,
            "matched": matches,
            "recommended": usable[0] if usable else None,
            "discoveredCandidates": discovered,
            "createOurOwn": not usable,
            "decision": "Use the highest-ranked verified healthy free option." if usable else "No verified healthy free fit exists. A verified evidence record may still be unavailable or not installed. Inspect discovered candidates or create a governed capability proposal; do not execute automatically.",
        }


@dataclass(frozen=True)
class SkillMetadata:
    name: str
    description: str
    path: str
    source_hash: str
    resources: dict[str, int]
    has_scripts: bool
    status: str = "DISCOVERED"
    authority_level: str = "read-only"


def _parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = path.read_text(encoding="utf-8")
    if len(text.encode("utf-8")) > 512 * 1024 or not text.startswith("---\n"):
        raise CapabilityError("skill_frontmatter_invalid", "SKILL.md requires bounded YAML frontmatter")
    marker = text.find("\n---\n", 4)
    if marker < 0:
        raise CapabilityError("skill_frontmatter_invalid", "SKILL.md frontmatter is not closed")
    metadata: dict[str, str] = {}
    for raw in text[4:marker].splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw or raw.startswith((" ", "\t")):
            raise CapabilityError("skill_frontmatter_invalid", "Only flat metadata is accepted during discovery")
        key, value = raw.split(":", 1)
        metadata[key.strip()] = value.strip().strip("\"'")
    return metadata, text[marker + 5:]


def inspect_skill(skill_dir: Path, allowed_root: Path) -> SkillMetadata:
    root = allowed_root.resolve()
    directory = skill_dir.resolve()
    if directory != root and root not in directory.parents:
        raise CapabilityError("skill_path_denied", "Skill path is outside the registered root")
    skill_file = directory / "SKILL.md"
    if not skill_file.is_file():
        raise CapabilityError("skill_missing", "Skill folder has no SKILL.md")
    metadata, _instructions = _parse_frontmatter(skill_file)
    name = metadata.get("name", "")
    description = metadata.get("description", "")
    if not SKILL_NAME.fullmatch(name) or not description or len(description) > 1024:
        raise CapabilityError("skill_metadata_invalid", "Skill name or description is invalid")
    if directory.name != name:
        raise CapabilityError("skill_metadata_invalid", "Skill folder must match the declared name")
    resources = {}
    for kind in ("scripts", "references", "assets"):
        folder = directory / kind
        resources[kind] = sum(1 for path in folder.rglob("*") if path.is_file()) if folder.is_dir() else 0
    return SkillMetadata(
        name=name, description=description, path=str(directory),
        source_hash=hashlib.sha256(skill_file.read_bytes()).hexdigest().upper(),
        resources=resources, has_scripts=resources["scripts"] > 0,
    )


def discover_skills(roots: Iterable[Path]) -> dict[str, Any]:
    skills: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*/SKILL.md"), key=lambda item: str(item).casefold()):
            try:
                item = inspect_skill(path.parent, root)
                skills.append({
                    "name": item.name, "description": item.description, "path": item.path,
                    "sourceHash": item.source_hash, "resources": item.resources,
                    "hasScripts": item.has_scripts, "status": item.status,
                    "authorityLevel": item.authority_level,
                    "scriptExecution": "BLOCKED-PENDING-SEPARATE-INSPECTION" if item.has_scripts else "NOT-PRESENT",
                })
            except CapabilityError as error:
                errors.append({"path": str(path.parent), "code": error.code, "error": str(error)})
    return {"schemaVersion": "twis-agent-skill-catalog-v1", "count": len(skills), "skills": skills, "errors": errors, "executedScripts": 0}


def validate_a2a_descriptor(card: dict[str, Any]) -> dict[str, Any]:
    required = {"name", "description", "version", "supportedInterfaces", "capabilities", "defaultInputModes", "defaultOutputModes", "skills"}
    if not isinstance(card, dict) or required - set(card):
        raise CapabilityError("a2a_descriptor_invalid", "A2A Agent Card descriptor is incomplete")
    if not isinstance(card["supportedInterfaces"], list) or not card["supportedInterfaces"]:
        raise CapabilityError("a2a_descriptor_invalid", "A2A descriptor requires supported interfaces")
    interfaces: list[dict[str, str]] = []
    for item in card["supportedInterfaces"]:
        if not isinstance(item, dict) or not all(isinstance(item.get(name), str) and item[name].strip() for name in ("url", "protocolBinding", "protocolVersion")):
            raise CapabilityError("a2a_descriptor_invalid", "Every A2A interface requires URL, protocol binding, and protocol version")
        interfaces.append({name: item[name].strip() for name in ("url", "protocolBinding", "protocolVersion")})
    return {
        "valid": True,
        "execution": "DEFERRED",
        "interfaces": interfaces,
        "protocolVersions": [item["protocolVersion"] for item in interfaces],
        "inputModes": [str(value) for value in card["defaultInputModes"]],
        "outputModes": [str(value) for value in card["defaultOutputModes"]],
        "authDeclared": bool(card.get("security") or card.get("securitySchemes")),
    }


class McpCatalog:
    def __init__(self, descriptors: list[dict[str, Any]]):
        self.descriptors = deepcopy(descriptors)

    def list(self) -> dict[str, Any]:
        return {"schemaVersion": "twis-mcp-catalog-v1", "protocolVersion": MCP_PROTOCOL_VERSION, "count": len(self.descriptors), "servers": deepcopy(self.descriptors), "autoEnabledTools": 0, "executedTools": 0}

    @staticmethod
    def _post_local(endpoint: str, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        parsed = urllib.parse.urlparse(endpoint)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password:
            raise CapabilityError("mcp_endpoint_denied", "MCP discovery proof permits loopback HTTP only")
        try:
            addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 80, type=socket.SOCK_STREAM)}
        except socket.gaierror as exc:
            raise CapabilityError("mcp_offline", "MCP endpoint could not be resolved") from exc
        if not addresses or any(address not in {"127.0.0.1", "::1"} for address in addresses):
            raise CapabilityError("mcp_endpoint_denied", "MCP discovery resolved outside loopback")
        payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}, "_meta": {"io.modelcontextprotocol/clientInfo": {"name": "twis-capability-bay", "version": "1.0"}}}).encode("utf-8")
        request = urllib.request.Request(endpoint, data=payload, method="POST", headers={"Content-Type": "application/json", "MCP-Protocol-Version": MCP_PROTOCOL_VERSION, "Mcp-Method": method})
        try:
            with urllib.request.urlopen(request, timeout=2.0) as response:
                value = json.loads(response.read(1024 * 1024).decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise CapabilityError("mcp_offline", "MCP discovery fixture is offline or malformed") from exc
        if not isinstance(value, dict) or "result" not in value:
            raise CapabilityError("mcp_response_invalid", "MCP discovery response is invalid")
        return value["result"]

    def discover_local(self, endpoint: str) -> dict[str, Any]:
        server = self._post_local(endpoint, "server/discover")
        tools = self._post_local(endpoint, "tools/list")
        resources = self._post_local(endpoint, "resources/list")
        tool_rows = tools.get("tools", []) if isinstance(tools, dict) else []
        resource_rows = resources.get("resources", []) if isinstance(resources, dict) else []
        if not isinstance(tool_rows, list) or not isinstance(resource_rows, list):
            raise CapabilityError("mcp_response_invalid", "MCP list result is invalid")
        return {
            "protocolVersion": MCP_PROTOCOL_VERSION, "server": server,
            "tools": tool_rows, "resources": resource_rows,
            "toolCount": len(tool_rows), "resourceCount": len(resource_rows),
            "autoEnabledTools": 0, "executedTools": 0, "status": "INSPECTING",
        }
