from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath
from typing import Any

SUPPORTED_SCHEMA_VERSION = "0.1"
WORKER_ID_PATTERN = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
SEMVER_PATTERN = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")
SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")
LIFECYCLE_STATUSES = {"draft", "test", "active", "deprecated", "retired"}
PROVENANCE_KINDS = {"human-authored", "imported", "generated", "derived"}
REQUIRED_FIELDS = {
    "schema_version",
    "worker_id",
    "version",
    "lifecycle_status",
    "purpose",
    "accepted_input_types",
    "produced_output_types",
    "allowed_read_roots",
    "allowed_write_roots",
    "blocked_roots",
    "network_allowed",
    "shell_allowed",
    "destructive_actions_allowed",
    "approval_required",
    "timeout_seconds",
    "test_commands",
    "failure_policy",
    "receipt_required",
    "source_provenance",
}


@dataclass(frozen=True)
class ValidationIssue:
    path: str
    code: str
    message: str


@dataclass(frozen=True)
class WorkerCardValidationResult:
    valid: bool
    issues: tuple[ValidationIssue, ...]

    def require_valid(self) -> None:
        if self.valid:
            return
        details = "; ".join(f"{issue.path}: {issue.message}" for issue in self.issues)
        raise ValueError(f"invalid Worker Card: {details}")


def is_schema_compatible(version: Any) -> bool:
    return isinstance(version, str) and version == SUPPORTED_SCHEMA_VERSION


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_absolute_windows_path(value: Any) -> bool:
    if not _is_nonempty_string(value):
        return False
    path = PureWindowsPath(value)
    return path.is_absolute() and bool(path.anchor)


def _validate_string_array(card: dict[str, Any], field: str, issues: list[ValidationIssue], *, paths: bool = False) -> None:
    value = card.get(field)
    if not isinstance(value, list):
        issues.append(ValidationIssue(field, "type", "must be an array"))
        return
    if field in {"accepted_input_types", "produced_output_types", "test_commands"} and not value:
        issues.append(ValidationIssue(field, "minimum", "must contain at least one entry"))
    seen: set[str] = set()
    for index, item in enumerate(value):
        item_path = f"{field}[{index}]"
        if not _is_nonempty_string(item):
            issues.append(ValidationIssue(item_path, "type", "must be a non-empty string"))
            continue
        normalized = item.casefold()
        if normalized in seen:
            issues.append(ValidationIssue(item_path, "duplicate", "must not duplicate another entry"))
        seen.add(normalized)
        if paths and not _is_absolute_windows_path(item):
            issues.append(ValidationIssue(item_path, "absolute_path", "must be an absolute Windows drive or UNC path"))


def validate_worker_card(card: Any) -> WorkerCardValidationResult:
    issues: list[ValidationIssue] = []
    if not isinstance(card, dict):
        return WorkerCardValidationResult(False, (ValidationIssue("$", "type", "must be an object"),))

    for field in sorted(REQUIRED_FIELDS - card.keys()):
        issues.append(ValidationIssue(field, "required", "field is required"))
    for field in sorted(card.keys() - REQUIRED_FIELDS):
        issues.append(ValidationIssue(field, "unknown", "field is not allowed by Worker Card v0.1"))

    if not is_schema_compatible(card.get("schema_version")):
        issues.append(ValidationIssue("schema_version", "incompatible", f"only schema version {SUPPORTED_SCHEMA_VERSION} is supported"))
    worker_id = card.get("worker_id")
    if not isinstance(worker_id, str) or not WORKER_ID_PATTERN.fullmatch(worker_id) or not 3 <= len(worker_id) <= 80:
        issues.append(ValidationIssue("worker_id", "format", "must be a 3-80 character lowercase kebab-case identifier"))
    version = card.get("version")
    if not isinstance(version, str) or not SEMVER_PATTERN.fullmatch(version):
        issues.append(ValidationIssue("version", "format", "must be a three-part semantic version"))
    if card.get("lifecycle_status") not in LIFECYCLE_STATUSES:
        issues.append(ValidationIssue("lifecycle_status", "enum", "contains an unsupported lifecycle status"))
    if not _is_nonempty_string(card.get("purpose")) or len(str(card.get("purpose", ""))) > 500:
        issues.append(ValidationIssue("purpose", "length", "must be a non-empty string of at most 500 characters"))

    for field in ("accepted_input_types", "produced_output_types", "test_commands"):
        _validate_string_array(card, field, issues)
    for field in ("allowed_read_roots", "allowed_write_roots", "blocked_roots"):
        _validate_string_array(card, field, issues, paths=True)

    for field in ("network_allowed", "shell_allowed", "destructive_actions_allowed", "approval_required", "receipt_required"):
        if type(card.get(field)) is not bool:
            issues.append(ValidationIssue(field, "type", "must be a boolean"))
    timeout = card.get("timeout_seconds")
    if type(timeout) is not int or not 1 <= timeout <= 3600:
        issues.append(ValidationIssue("timeout_seconds", "range", "must be an integer from 1 through 3600"))

    failure_policy = card.get("failure_policy")
    if not isinstance(failure_policy, dict):
        issues.append(ValidationIssue("failure_policy", "type", "must be an object"))
    else:
        expected = {"on_validation_error", "on_runtime_error", "retry_count"}
        if set(failure_policy) != expected:
            issues.append(ValidationIssue("failure_policy", "fields", "must contain only on_validation_error, on_runtime_error, and retry_count"))
        if failure_policy.get("on_validation_error") != "reject":
            issues.append(ValidationIssue("failure_policy.on_validation_error", "enum", "must be reject"))
        if failure_policy.get("on_runtime_error") not in {"fail_closed", "record_failure"}:
            issues.append(ValidationIssue("failure_policy.on_runtime_error", "enum", "must be fail_closed or record_failure"))
        retry_count = failure_policy.get("retry_count")
        if type(retry_count) is not int or not 0 <= retry_count <= 3:
            issues.append(ValidationIssue("failure_policy.retry_count", "range", "must be an integer from 0 through 3"))

    provenance = card.get("source_provenance")
    if not isinstance(provenance, dict):
        issues.append(ValidationIssue("source_provenance", "type", "must be an object"))
    else:
        if set(provenance) - {"kind", "source", "sha256"} or not {"kind", "source"}.issubset(provenance):
            issues.append(ValidationIssue("source_provenance", "fields", "must contain kind and source, with optional sha256"))
        if provenance.get("kind") not in PROVENANCE_KINDS:
            issues.append(ValidationIssue("source_provenance.kind", "enum", "contains an unsupported provenance kind"))
        if not _is_nonempty_string(provenance.get("source")):
            issues.append(ValidationIssue("source_provenance.source", "length", "must be a non-empty string"))
        if "sha256" in provenance and (not isinstance(provenance["sha256"], str) or not SHA256_PATTERN.fullmatch(provenance["sha256"])):
            issues.append(ValidationIssue("source_provenance.sha256", "format", "must be a 64-character hexadecimal SHA-256"))

    allowed_roots = {
        str(PureWindowsPath(path)).casefold()
        for field in ("allowed_read_roots", "allowed_write_roots")
        for path in card.get(field, [])
        if _is_absolute_windows_path(path)
    }
    blocked_roots = {
        str(PureWindowsPath(path)).casefold()
        for path in card.get("blocked_roots", [])
        if _is_absolute_windows_path(path)
    }
    for overlap in sorted(allowed_roots & blocked_roots):
        issues.append(ValidationIssue("blocked_roots", "contradiction", f"root is both allowed and blocked: {overlap}"))
    if card.get("shell_allowed") is True and card.get("approval_required") is not True:
        issues.append(ValidationIssue("approval_required", "permission_dependency", "must be true when shell_allowed is true"))
    if card.get("destructive_actions_allowed") is True and card.get("approval_required") is not True:
        issues.append(ValidationIssue("approval_required", "permission_dependency", "must be true when destructive_actions_allowed is true"))
    if card.get("network_allowed") is True and card.get("approval_required") is not True:
        issues.append(ValidationIssue("approval_required", "permission_dependency", "must be true when network_allowed is true"))

    return WorkerCardValidationResult(not issues, tuple(issues))


def load_worker_card(path: str | Path) -> dict[str, Any]:
    card_path = Path(path)
    data = json.loads(card_path.read_text(encoding="utf-8"))
    result = validate_worker_card(data)
    result.require_valid()
    return data
