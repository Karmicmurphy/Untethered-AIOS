from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import stat
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable

from companion.talk_room import inspect_code_text
from companion.builder_output import (
    BUILDER_SCHEMA_VERSION,
    BUILDER_WORKERS,
    build_output as build_builder_output,
    validate_output as validate_builder_output,
)
from companion.model_bay import ModelBay, ModelBayError, build_ai_builder_output, writing_action_task
from companion.capability_registry import CapabilityRegistry, CapabilityError


SCHEMA_VERSION = "local-api-worker-kit-v1"
PACKET_SCHEMA_VERSION = "worker-packet-v1"
JOB_SCHEMA_VERSION = "local-worker-job-v1"
MAX_REQUEST_BYTES = 256 * 1024
MAX_TEXT_BYTES = 512 * 1024
MAX_NOTE_BYTES = 256 * 1024
MAX_PACKAGE_BYTES = 16 * 1024 * 1024
MAX_ARCHIVE_EXPANDED_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 500
MAX_EXPECTED_MEMBERS = 500
PLAN_LIFETIME_HOURS = 24
APPROVAL_NOTE_MAX = 500
TITLE_MAX = 300

READ_ONLY_WORKERS = {
    "approved-text-reader",
    "code-structure-inspector",
    "package-manifest-validator",
}
WORKER_IDS = (
    "approved-text-reader",
    "code-structure-inspector",
    "note-proposal-worker",
    "package-manifest-validator",
    "handoff-proposal-builder",
    "prompt-proposal-builder",
    "draft-workshop",
    "evidence-compare",
    "visual-brief-builder",
    "song-production-brief-builder",
    "video-production-brief-builder",
    "build-work-order-builder",
    "module-proposal-builder",
    "local-ai-rewrite",
)
BUILDER_WORKER_IDS = frozenset(BUILDER_WORKERS)
TERMINAL_STATES = {
    "plan_rejected",
    "cancelled",
    "stale",
    "abandoned",
    "failed",
    "result_rejected",
    "result_approved",
    "draft_saved",
    "rolled_back",
}
SAFE_DELETE_STATES = TERMINAL_STATES
TEXT_SUFFIXES = {
    ".bat",
    ".c",
    ".cfg",
    ".conf",
    ".cpp",
    ".cs",
    ".css",
    ".csv",
    ".h",
    ".hpp",
    ".html",
    ".ini",
    ".java",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".mjs",
    ".ps1",
    ".py",
    ".rs",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
CODE_SUFFIXES = {
    ".bat",
    ".c",
    ".cpp",
    ".cs",
    ".css",
    ".h",
    ".hpp",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".mjs",
    ".ps1",
    ".py",
    ".rs",
    ".sh",
    ".sql",
    ".ts",
    ".tsx",
}
PACKAGE_SUFFIXES = {".json", ".zip"}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS worker_job_evidence(
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  details TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS worker_job_evidence_job_idx
  ON worker_job_evidence(job_id, created_at);
CREATE INDEX IF NOT EXISTS jobs_operation_status_idx
  ON jobs(operation, status, updated_at);
CREATE TABLE IF NOT EXISTS artifact_relationships(
  id TEXT PRIMARY KEY,
  source_artifact_id TEXT NOT NULL,
  target_artifact_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  relationship_type TEXT NOT NULL,
  lifecycle_id TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS artifact_relationship_source_idx
  ON artifact_relationships(source_artifact_id, created_at DESC);
CREATE INDEX IF NOT EXISTS artifact_relationship_target_idx
  ON artifact_relationships(target_artifact_id, created_at DESC);
"""


class LocalWorkerError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.details = details or {}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def _rebind_builder_output(output: dict[str, Any]) -> str:
    metadata = output["metadata"]
    metadata.pop("outputHash", None)
    digest = sha256_text(canonical_json({"text": output["text"], "metadata": metadata}))
    metadata["outputHash"] = digest
    output["outputHash"] = digest
    return digest


def json_value(value: str | None, fallback: Any) -> Any:
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(SCHEMA_SQL)


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _is_reparse(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return path.is_symlink() or bool(
        attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    )


def _contains_reparse(path: Path, root: Path) -> bool:
    current = path
    while True:
        if _is_reparse(current):
            return True
        if current == root or current.parent == current:
            return False
        current = current.parent


def _safe_member(value: Any) -> str:
    if not isinstance(value, str) or not value or len(value) > 500:
        raise LocalWorkerError(
            "package_member_invalid",
            "Expected package members must be bounded relative paths",
        )
    normalized = value.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if (
        pure.is_absolute()
        or not pure.parts
        or any(part in {"", ".", ".."} for part in pure.parts)
        or re.match(r"^[A-Za-z]:", normalized)
    ):
        raise LocalWorkerError(
            "package_member_unsafe",
            "Expected package members must be safe relative paths",
        )
    return pure.as_posix()


def _bounded_title(value: Any, fallback: str) -> str:
    title = str(value or "").strip()
    return (title or fallback)[:TITLE_MAX]


def _approval_note(value: Any) -> str:
    note = str(value or "").strip()
    if not note:
        raise LocalWorkerError(
            "approval_note_required",
            "Add a short approval note before approving this action",
        )
    if len(note) > APPROVAL_NOTE_MAX:
        raise LocalWorkerError(
            "approval_note_too_long",
            "Approval notes are limited to 500 characters",
        )
    return note


class LocalWorkerKit:
    def __init__(
        self,
        connect: Callable[[], sqlite3.Connection],
        projects_root: Path,
        *,
        clock: Callable[[], float] = time.monotonic,
        model_bay: ModelBay | None = None,
        capability_registry: CapabilityRegistry | None = None,
    ) -> None:
        self._connect = connect
        self.projects_root = projects_root.resolve(strict=False)
        self._clock = clock
        self._model_bay = model_bay
        self._capability_registry = capability_registry
        self.implementation_path = Path(__file__).resolve()
        self.implementation_hash = sha256_bytes(
            self.implementation_path.read_bytes()
        )
        connection = self._connect()
        try:
            ensure_schema(connection)
            connection.commit()
        finally:
            connection.close()

    def _contracts(self) -> dict[str, dict[str, Any]]:
        common_prohibited = [
            "network",
            "shell",
            "subprocess",
            "arbitrary-filesystem",
            "credentials",
            "private-project-history",
            "attachment",
            "activation",
            "module-promotion",
        ]
        raw: dict[str, dict[str, Any]] = {
            "approved-text-reader": {
                "workerId": "approved-text-reader",
                "name": "Approved Text Reader",
                "description": "Reads one explicitly selected registered text artifact and reports exact local facts.",
                "responsibility": "Read one approved text source without changing it.",
                "inputTypes": ["registered-text-artifact", "talk-session", "write-document"],
                "requiredPermissions": ["read-selected-source"],
                "prohibitedPermissions": common_prohibited,
                "limits": {
                    "inputBytes": MAX_TEXT_BYTES,
                    "runtimeSeconds": 2,
                    "outputBytes": 768 * 1024,
                },
                "classification": "deterministic",
                "networkPolicy": "denied",
                "outputSchema": "approved-text-reader-output-v1",
                "validationRules": [
                    "source identity exists",
                    "source hash is current",
                    "UTF-8 text only",
                    "bounded bytes",
                ],
                "mutationPolicy": "read-only",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": [
                    "plan",
                    "plan-decision",
                    "execution",
                    "result-decision",
                ],
                "rollbackBehavior": "No source mutation exists to roll back.",
                "version": "0.8.0",
                "implementationHash": self.implementation_hash,
            },
            "code-structure-inspector": {
                "workerId": "code-structure-inspector",
                "name": "Code Structure Inspector",
                "description": "Reports lexical code structure and clearly labels heuristic findings.",
                "responsibility": "Inspect structure without executing or semantically interpreting source.",
                "inputTypes": ["registered-code-artifact", "talk-code-entry", "write-document"],
                "requiredPermissions": ["read-selected-source"],
                "prohibitedPermissions": common_prohibited,
                "limits": {
                    "inputBytes": MAX_TEXT_BYTES,
                    "runtimeSeconds": 2,
                    "outputBytes": 512 * 1024,
                },
                "classification": "deterministic-with-labeled-heuristics",
                "networkPolicy": "denied",
                "outputSchema": "code-structure-inspection-v1",
                "validationRules": [
                    "source identity exists",
                    "source hash is current",
                    "supported text code type",
                    "no execution",
                    "bounded findings",
                ],
                "mutationPolicy": "read-only",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": [
                    "plan",
                    "plan-decision",
                    "execution",
                    "result-decision",
                ],
                "rollbackBehavior": "No source mutation exists to roll back.",
                "version": "0.8.0",
                "implementationHash": self.implementation_hash,
            },
            "note-proposal-worker": {
                "workerId": "note-proposal-worker",
                "name": "Note Proposal Worker",
                "description": "Turns selected existing content into a proposed note without rewriting the source.",
                "responsibility": "Propose one note and create it only after explicit result approval.",
                "inputTypes": ["selected-talk-content", "selected-write-content", "selected-artifact-content"],
                "requiredPermissions": [
                    "read-selected-source",
                    "create-one-note-after-approval",
                ],
                "prohibitedPermissions": common_prohibited,
                "limits": {
                    "inputBytes": MAX_NOTE_BYTES,
                    "runtimeSeconds": 2,
                    "outputBytes": 384 * 1024,
                },
                "classification": "deterministic",
                "networkPolicy": "denied",
                "outputSchema": "note-proposal-output-v1",
                "validationRules": [
                    "selected content belongs to current source",
                    "source hash is current",
                    "nonblank note",
                    "bounded output",
                ],
                "mutationPolicy": "create-one-new-note-after-result-approval",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": [
                    "plan",
                    "plan-decision",
                    "execution",
                    "result-decision",
                    "note-create",
                    "rollback",
                ],
                "rollbackBehavior": "Remove only the unchanged note created by this job; preserve the source and unrelated writing.",
                "version": "0.8.0",
                "implementationHash": self.implementation_hash,
            },
            "package-manifest-validator": {
                "workerId": "package-manifest-validator",
                "name": "Package Manifest Validator",
                "description": "Validates one registered JSON manifest or ZIP package without installing or executing it.",
                "responsibility": "Report path safety, members, hashes, missing entries, and unexpected entries where evidence permits.",
                "inputTypes": ["registered-json-manifest", "registered-zip-package"],
                "requiredPermissions": ["read-selected-package-metadata"],
                "prohibitedPermissions": common_prohibited
                + ["install", "import", "extract-to-filesystem"],
                "limits": {
                    "inputBytes": MAX_PACKAGE_BYTES,
                    "expandedBytes": MAX_ARCHIVE_EXPANDED_BYTES,
                    "members": MAX_ARCHIVE_MEMBERS,
                    "runtimeSeconds": 5,
                    "outputBytes": 1024 * 1024,
                },
                "classification": "deterministic",
                "networkPolicy": "denied",
                "outputSchema": "package-manifest-validation-v1",
                "validationRules": [
                    "source identity exists",
                    "container hash is current",
                    "safe relative member paths",
                    "bounded archive size and count",
                    "hash comparisons only where supplied or present",
                ],
                "mutationPolicy": "read-only",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": [
                    "plan",
                    "plan-decision",
                    "execution",
                    "result-decision",
                ],
                "rollbackBehavior": "No package mutation, install, import, extraction, or activation occurs.",
                "version": "0.8.0",
                "implementationHash": self.implementation_hash,
            },
            "handoff-proposal-builder": {
                "workerId": "handoff-proposal-builder",
                "name": "Handoff Proposal Builder",
                "description": "Builds one governed continuation handoff from explicitly selected registered sources.",
                "responsibility": "Prepare a local handoff proposal without sending, executing, attaching, or activating it.",
                "inputTypes": ["registered-text-artifacts", "talk-sessions", "write-documents", "approved-worker-results"],
                "requiredPermissions": ["read-selected-sources", "save-one-approved-inactive-draft", "export-approved-copy"],
                "prohibitedPermissions": common_prohibited + ["provider-call", "automatic-submission", "automatic-export"],
                "limits": {"inputBytes": MAX_TEXT_BYTES, "runtimeSeconds": 5, "outputBytes": 2 * 1024 * 1024},
                "classification": "deterministic",
                "networkPolicy": "denied",
                "outputSchema": BUILDER_SCHEMA_VERSION,
                "validationRules": ["one or more explicit sources", "all source hashes current", "supported profile", "nonblank goal", "all required sections", "output hash exact"],
                "mutationPolicy": "save-one-inactive-draft-only-after-result-approval",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": ["plan", "plan-decision", "execution", "validation", "result-decision", "save-or-export", "rollback"],
                "rollbackBehavior": "Remove only the unchanged draft created by this job; preserve every source and audit receipt.",
                "version": "0.9.0",
                "implementationHash": self.implementation_hash,
            },
            "prompt-proposal-builder": {
                "workerId": "prompt-proposal-builder",
                "name": "Prompt Proposal Builder",
                "description": "Builds one governed task prompt from explicitly selected registered sources and an owner goal.",
                "responsibility": "Prepare a local prompt proposal without sending, executing, attaching, or activating it.",
                "inputTypes": ["registered-text-artifacts", "talk-sessions", "write-documents", "approved-worker-results"],
                "requiredPermissions": ["read-selected-sources", "save-one-approved-inactive-draft", "export-approved-copy"],
                "prohibitedPermissions": common_prohibited + ["provider-call", "automatic-submission", "automatic-export"],
                "limits": {"inputBytes": MAX_TEXT_BYTES, "runtimeSeconds": 5, "outputBytes": 2 * 1024 * 1024},
                "classification": "deterministic",
                "networkPolicy": "denied",
                "outputSchema": BUILDER_SCHEMA_VERSION,
                "validationRules": ["one or more explicit sources", "all source hashes current", "supported profile", "nonblank goal", "all required sections", "output hash exact"],
                "mutationPolicy": "save-one-inactive-draft-only-after-result-approval",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": ["plan", "plan-decision", "execution", "validation", "result-decision", "save-or-export", "rollback"],
                "rollbackBehavior": "Remove only the unchanged draft created by this job; preserve every source and audit receipt.",
                "version": "0.9.0",
                "implementationHash": self.implementation_hash,
            },
            "draft-workshop": {
                "workerId": "draft-workshop",
                "name": "Draft Workshop",
                "description": "Prepares one governed writing task and inactive draft scaffold from one registered text source or owner-entered rough text.",
                "responsibility": "Prepare a source-bound writing proposal without pretending that model generation occurred.",
                "inputTypes": ["one-registered-text-source", "owner-entered-rough-text"],
                "requiredPermissions": ["read-one-selected-source", "save-one-approved-inactive-draft", "export-approved-copy"],
                "prohibitedPermissions": common_prohibited + ["provider-call", "automatic-submission", "automatic-export", "source-overwrite"],
                "limits": {"inputBytes": MAX_TEXT_BYTES, "runtimeSeconds": 5, "outputBytes": 2 * 1024 * 1024},
                "classification": "deterministic-preparation",
                "networkPolicy": "denied",
                "outputSchema": BUILDER_SCHEMA_VERSION,
                "validationRules": ["exactly one registered source or nonblank rough text", "source hash current", "supported writing operation", "all required sections", "output hash exact"],
                "mutationPolicy": "save-one-inactive-writing-draft-only-after-result-approval",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": ["plan", "plan-decision", "execution", "validation", "result-decision", "save-or-export", "rollback"],
                "rollbackBehavior": "Remove only the unchanged writing draft created by this job; preserve the registered source and receipts.",
                "version": "0.10.0",
                "implementationHash": self.implementation_hash,
            },
            "evidence-compare": {
                "workerId": "evidence-compare",
                "name": "Evidence Compare",
                "description": "Prepares one governed comparison workspace from two to eight explicitly selected registered text sources.",
                "responsibility": "Prepare exact textual comparison evidence and honest semantic review scaffolds without live research or model-generated conclusions.",
                "inputTypes": ["two-to-eight-registered-text-sources"],
                "requiredPermissions": ["read-selected-sources", "save-one-approved-inactive-research-draft", "export-approved-copy"],
                "prohibitedPermissions": common_prohibited + ["provider-call", "network-retrieval", "url-fetch", "semantic-conclusion-fabrication", "automatic-submission", "automatic-export", "source-overwrite"],
                "limits": {"inputBytes": MAX_TEXT_BYTES, "sources": 8, "runtimeSeconds": 5, "outputBytes": 2 * 1024 * 1024},
                "classification": "deterministic-comparison-preparation",
                "networkPolicy": "denied",
                "outputSchema": BUILDER_SCHEMA_VERSION,
                "validationRules": ["two to eight unique registered text sources", "all source hashes current", "supported comparison focus", "source order retained", "exact textual facts labeled", "semantic fields unassessed", "output hash exact"],
                "mutationPolicy": "save-one-inactive-research-comparison-draft-only-after-result-approval",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": ["plan", "plan-decision", "execution", "validation", "result-decision", "save-or-export", "rollback"],
                "rollbackBehavior": "Remove only the unchanged comparison draft created by this job; preserve every selected source and audit receipt.",
                "version": "0.11.0",
                "implementationHash": self.implementation_hash,
            },
            "visual-brief-builder": {
                "workerId": "visual-brief-builder",
                "name": "Visual Brief Builder",
                "description": "Prepares one governed visual-production brief from zero to four registered text sources and/or owner-entered visual notes.",
                "responsibility": "Organize owner-supplied visual direction into an honest inactive brief and manual-use prompt without generating an image.",
                "inputTypes": ["zero-to-four-registered-text-sources", "owner-entered-visual-notes"],
                "requiredPermissions": ["read-selected-sources", "hash-temporary-owner-notes", "save-one-approved-inactive-visual-brief", "export-approved-copy"],
                "prohibitedPermissions": common_prohibited + ["image-generation", "provider-call", "network-retrieval", "url-fetch", "automatic-submission", "automatic-export", "source-overwrite", "publication", "promotion"],
                "limits": {"inputBytes": MAX_TEXT_BYTES, "sources": 4, "runtimeSeconds": 5, "outputBytes": 2 * 1024 * 1024},
                "classification": "deterministic-visual-brief-preparation",
                "networkPolicy": "denied",
                "outputSchema": BUILDER_SCHEMA_VERSION,
                "validationRules": ["zero to four unique registered text sources", "registered source or nonblank owner notes required", "all source hashes current", "supported visual purpose", "allowlisted visual controls", "no image generated", "output hash exact"],
                "mutationPolicy": "save-one-inactive-visual-brief-draft-only-after-result-approval",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": ["plan", "plan-decision", "execution", "validation", "result-decision", "save-or-export", "rollback"],
                "rollbackBehavior": "Remove only the unchanged visual brief draft created by this job; preserve every registered source, temporary-note hash, and audit receipt.",
                "version": "0.12.0",
                "implementationHash": self.implementation_hash,
            },
            "song-production-brief-builder": {
                "workerId": "song-production-brief-builder",
                "name": "Song Production Brief Builder",
                "description": "Prepares one governed song-production brief from zero to four registered text sources and/or hash-identified owner music notes and lyrics.",
                "responsibility": "Organize owner-supplied music direction into an honest inactive brief and manual-use prompt without generating or playing music.",
                "inputTypes": ["zero-to-four-registered-text-sources", "owner-entered-music-notes", "owner-supplied-lyrics"],
                "requiredPermissions": ["read-selected-sources", "hash-temporary-music-input", "save-one-approved-inactive-song-brief", "export-approved-copy"],
                "prohibitedPermissions": common_prohibited + ["music-generation", "audio-playback", "audio-rendering", "provider-call", "network-retrieval", "automatic-submission", "automatic-export", "source-overwrite", "lyrics-overwrite", "publication", "promotion"],
                "limits": {"inputBytes": MAX_TEXT_BYTES, "sources": 4, "runtimeSeconds": 5, "outputBytes": 2 * 1024 * 1024},
                "classification": "deterministic-song-production-brief-preparation",
                "networkPolicy": "denied",
                "outputSchema": BUILDER_SCHEMA_VERSION,
                "validationRules": ["zero to four unique registered text sources", "source, nonblank notes, or nonblank lyrics required", "all source hashes current", "supported song purpose", "allowlisted production controls", "owner lyrics exact", "no music generated or played", "output hash exact"],
                "mutationPolicy": "save-one-inactive-song-production-brief-draft-only-after-result-approval",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": ["plan", "plan-decision", "execution", "validation", "result-decision", "save-or-export", "rollback"],
                "rollbackBehavior": "Remove only the unchanged song brief draft created by this job; preserve registered sources, exact owner lyrics, temporary-input hashes, and audit receipts.",
                "version": "0.13.0",
                "implementationHash": self.implementation_hash,
            },
            "video-production-brief-builder": {
                "workerId": "video-production-brief-builder",
                "name": "Video Production Brief Builder",
                "description": "Prepares one governed video-production brief from zero to four registered text sources and/or hash-identified owner video notes.",
                "responsibility": "Organize owner-supplied video direction into an honest inactive brief and manual-use handoff without generating or rendering video.",
                "inputTypes": ["zero-to-four-registered-text-sources", "owner-entered-video-notes"],
                "requiredPermissions": ["read-selected-sources", "hash-temporary-video-notes", "save-one-approved-inactive-video-brief", "export-approved-copy"],
                "prohibitedPermissions": common_prohibited + ["video-generation", "video-rendering", "provider-call", "network-retrieval", "automatic-submission", "automatic-export", "source-overwrite", "publication", "promotion"],
                "limits": {"inputBytes": MAX_TEXT_BYTES, "sources": 4, "runtimeSeconds": 5, "outputBytes": 2 * 1024 * 1024},
                "classification": "deterministic-video-production-brief-preparation",
                "networkPolicy": "denied",
                "outputSchema": BUILDER_SCHEMA_VERSION,
                "validationRules": ["zero to four unique registered text sources", "registered source or nonblank owner notes required", "all source hashes current", "supported video purpose", "allowlisted video controls", "no video generated or rendered", "output hash exact"],
                "mutationPolicy": "save-one-inactive-video-production-brief-draft-only-after-result-approval",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": ["plan", "plan-decision", "execution", "validation", "result-decision", "save-or-export", "rollback"],
                "rollbackBehavior": "Remove only the unchanged video brief draft created by this job; preserve registered sources, temporary-note hashes, and audit receipts.",
                "version": "0.15.0",
                "implementationHash": self.implementation_hash,
            },
            "build-work-order-builder": {
                "workerId": "build-work-order-builder",
                "name": "Build Work Order Builder",
                "description": "Prepares one governed technical work order from zero to four registered text sources and/or hash-identified owner build input.",
                "responsibility": "Organize owner requirements into an inactive implementation brief without executing code, commands, file changes, submissions, or deployments.",
                "inputTypes": ["zero-to-four-registered-text-sources", "owner-entered-build-input"],
                "requiredPermissions": ["read-selected-sources", "hash-temporary-build-input", "save-one-approved-inactive-work-order", "export-approved-copy"],
                "prohibitedPermissions": common_prohibited + ["code-execution", "shell-execution", "file-modification", "provider-call", "network-retrieval", "automatic-submission", "cloud-deployment", "source-overwrite", "publication", "activation"],
                "limits": {"inputBytes": MAX_TEXT_BYTES, "sources": 4, "runtimeSeconds": 5, "outputBytes": 2 * 1024 * 1024},
                "classification": "deterministic-build-work-order-preparation",
                "networkPolicy": "denied",
                "outputSchema": BUILDER_SCHEMA_VERSION,
                "validationRules": ["zero to four unique registered text sources", "source or meaningful owner input required", "all source hashes current", "supported work-order type", "allowlisted build controls", "no execution or file mutation", "output hash exact"],
                "mutationPolicy": "save-one-inactive-build-work-order-draft-only-after-result-approval",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": ["plan", "plan-decision", "execution", "validation", "result-decision", "save-or-export", "rollback"],
                "rollbackBehavior": "Remove only the unchanged work-order draft created by this job; preserve registered sources, temporary-input hashes, and audit receipts.",
                "version": "0.16.0",
                "implementationHash": self.implementation_hash,
            },
            "module-proposal-builder": {
                "workerId": "module-proposal-builder",
                "name": "Module Proposal Builder",
                "description": "Prepares one governed proposal for a future Workshop module from zero to four registered text sources and/or hash-identified owner module input.",
                "responsibility": "Document a proposed module and its boundaries without installing, downloading, executing, activating, or fetching anything.",
                "inputTypes": ["zero-to-four-registered-text-sources", "owner-entered-module-input"],
                "requiredPermissions": ["read-selected-sources", "hash-temporary-module-input", "save-one-approved-inactive-module-proposal", "export-approved-copy"],
                "prohibitedPermissions": common_prohibited + ["module-installation", "dependency-installation", "code-execution", "external-download", "provider-call", "network-retrieval", "dynamic-activation", "source-overwrite", "publication"],
                "limits": {"inputBytes": MAX_TEXT_BYTES, "sources": 4, "runtimeSeconds": 5, "outputBytes": 2 * 1024 * 1024},
                "classification": "deterministic-module-proposal-preparation",
                "networkPolicy": "denied",
                "outputSchema": BUILDER_SCHEMA_VERSION,
                "validationRules": ["zero to four unique registered text sources", "source or meaningful owner input required", "all source hashes current", "supported proposal type", "allowlisted module controls", "no installation download or execution", "output hash exact"],
                "mutationPolicy": "save-one-inactive-module-proposal-draft-only-after-result-approval",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": ["plan", "plan-decision", "execution", "validation", "result-decision", "save-or-export", "rollback"],
                "rollbackBehavior": "Remove only the unchanged module-proposal draft created by this job; preserve registered sources, temporary-input hashes, registry truth, and audit receipts.",
                "version": "0.16.0",
                "implementationHash": self.implementation_hash,
            },
            "local-ai-rewrite": {
                "workerId": "local-ai-rewrite",
                "name": "Creative Studio AI Actions",
                "description": "Runs one explicit bounded Write or Music Studio action through the enabled registered localhost model and returns proposed content.",
                "responsibility": "Assist one registered Write document or one exact temporary Music Studio state while preserving owner originals and retaining complete local-inference provenance.",
                "inputTypes": ["one-registered-write-source-or-one-temporary-music-state", "zero-to-three-explicit-write-context-sources"],
                "requiredPermissions": ["read-one-selected-write-source", "read-explicit-selected-context", "invoke-one-registered-local-model-on-loopback", "save-one-approved-inactive-draft", "export-approved-copy"],
                "prohibitedPermissions": [
                    "external-network", "cloud-provider", "arbitrary-runtime", "arbitrary-executable",
                    "shell", "arbitrary-filesystem", "credentials", "source-overwrite", "automatic-approval",
                    "automatic-save", "attachment", "activation", "publication", "module-promotion",
                ],
                "limits": {"inputBytes": MAX_TEXT_BYTES, "sources": 4, "runtimeSeconds": 130, "outputBytes": 2 * 1024 * 1024},
                "classification": "registered-local-model-proposal",
                "networkPolicy": "loopback-127.0.0.1-only; external denied",
                "outputSchema": BUILDER_SCHEMA_VERSION,
                "validationRules": [
                    "one registered current Write source or exact hash-bound Music Studio state", "zero to three explicit Write project context sources", "fixed deterministic model route",
                    "registered model and runtime hashes", "approved inference plan", "bounded parameters",
                    "loopback only", "proposed output hash exact", "original source unchanged",
                ],
                "mutationPolicy": "save-one-inactive-ai-writing-proposal-only-after-result-approval",
                "planApprovalRequired": True,
                "resultApprovalRequired": True,
                "receiptRequirements": ["plan", "plan-decision", "inference", "validation", "result-decision", "save-or-export", "rollback"],
                "rollbackBehavior": "Remove only the unchanged AI proposal draft created by this job; preserve the source, inference evidence, and receipts.",
                "version": "0.17.2",
                "implementationHash": self.implementation_hash,
            },
        }
        return raw

    def _validated_contract(self, worker_id: str) -> dict[str, Any]:
        contract = self._contracts().get(worker_id)
        if contract is None:
            raise LocalWorkerError(
                "worker_not_supported",
                "That worker is not in the fixed local allowlist",
                status=404,
            )
        required = {
            "workerId",
            "name",
            "description",
            "responsibility",
            "inputTypes",
            "requiredPermissions",
            "prohibitedPermissions",
            "limits",
            "classification",
            "networkPolicy",
            "outputSchema",
            "validationRules",
            "mutationPolicy",
            "planApprovalRequired",
            "resultApprovalRequired",
            "receiptRequirements",
            "rollbackBehavior",
            "version",
            "implementationHash",
        }
        if set(contract) != required:
            raise LocalWorkerError(
                "worker_contract_invalid",
                "The fixed worker contract is incomplete",
                status=500,
            )
        ai_contract = contract["workerId"] == "local-ai-rewrite"
        required_prohibited = (
            ("external-network", "shell", "arbitrary-filesystem", "attachment", "activation", "module-promotion")
            if ai_contract
            else ("network", "shell", "arbitrary-filesystem", "attachment", "activation", "module-promotion")
        )
        if (
            contract["workerId"] not in WORKER_IDS
            or (contract["networkPolicy"] != "loopback-127.0.0.1-only; external denied" if ai_contract else contract["networkPolicy"] != "denied")
            or contract["implementationHash"] != self.implementation_hash
            or any(
                permission not in contract["prohibitedPermissions"]
                for permission in required_prohibited
            )
            or contract["planApprovalRequired"] is not True
            or contract["resultApprovalRequired"] is not True
        ):
            raise LocalWorkerError(
                "worker_contract_invalid",
                "The fixed worker contract failed its safety invariants",
                status=500,
            )
        value = json.loads(json.dumps(contract))
        value["contractHash"] = sha256_text(canonical_json(contract))
        value["valid"] = True
        value["automaticAttachment"] = False
        value["automaticActivation"] = False
        return value

    def list_workers(self) -> list[dict[str, Any]]:
        return [
            {
                "workerId": contract["workerId"],
                "name": contract["name"],
                "description": contract["description"],
                "responsibility": contract["responsibility"],
                "reads": contract["requiredPermissions"],
                "mayCreate": (
                    ["One new note after result approval"]
                    if contract["workerId"] == "note-proposal-worker"
                    else (["One inactive approved draft"] if contract["workerId"] in BUILDER_WORKER_IDS else [])
                ),
                "cannotAccess": contract["prohibitedPermissions"],
                "runtimeLimitSeconds": contract["limits"]["runtimeSeconds"],
                "network": "denied",
                "approvalRequired": True,
                "contractHash": contract["contractHash"],
                "version": contract["version"],
            }
            for contract in (
                self._validated_contract(worker_id) for worker_id in WORKER_IDS
            )
        ]

    def inspect_worker(self, worker_id: str) -> dict[str, Any]:
        return self._validated_contract(worker_id)

    def _receipt(
        self,
        connection: sqlite3.Connection,
        project_id: str,
        action: str,
        actor: str,
        details: dict[str, Any],
    ) -> str:
        receipt_id = str(uuid.uuid4())
        connection.execute(
            "INSERT INTO receipts(id,project_id,action,actor,details,created_at) VALUES(?,?,?,?,?,?)",
            (
                receipt_id,
                project_id,
                action,
                actor[:100] or "local-owner",
                canonical_json(details),
                utc_now(),
            ),
        )
        return receipt_id

    def _evidence(
        self,
        connection: sqlite3.Connection,
        job_id: str,
        kind: str,
        details: dict[str, Any],
    ) -> dict[str, Any]:
        evidence_id = str(uuid.uuid4())
        digest = sha256_text(canonical_json(details))
        created = utc_now()
        connection.execute(
            "INSERT INTO worker_job_evidence(id,job_id,kind,sha256,details,created_at) VALUES(?,?,?,?,?,?)",
            (
                evidence_id,
                job_id,
                kind,
                digest,
                canonical_json(details),
                created,
            ),
        )
        return {
            "kind": kind,
            "sha256": digest,
            "createdAt": created,
        }

    def _artifact_row(
        self, connection: sqlite3.Connection, artifact_id: str
    ) -> sqlite3.Row:
        if (
            not isinstance(artifact_id, str)
            or not artifact_id.strip()
            or len(artifact_id) > 200
        ):
            raise LocalWorkerError(
                "source_artifact_invalid",
                "Choose a registered Workshop source",
            )
        row = connection.execute(
            "SELECT * FROM artifacts WHERE id=?", (artifact_id.strip(),)
        ).fetchone()
        if row is None:
            raise LocalWorkerError(
                "source_artifact_not_found",
                "The selected Workshop source no longer exists",
                status=404,
            )
        return row

    def _registered_file(
        self, row: sqlite3.Row
    ) -> tuple[Path, bytes, str]:
        project_relative = Path(str(row["project_id"] or ""))
        if (
            len(project_relative.parts) != 1
            or project_relative.is_absolute()
            or ".." in project_relative.parts
        ):
            raise LocalWorkerError(
                "source_project_path_invalid",
                "The registered source project boundary is invalid",
            )
        relative = Path(str(row["path"] or ""))
        if not relative.parts or relative.is_absolute() or ".." in relative.parts:
            raise LocalWorkerError(
                "source_path_invalid",
                "The registered source path is not a safe relative path",
            )
        project_root = (self.projects_root / project_relative).resolve(
            strict=False
        )
        if (
            not _is_within(project_root, self.projects_root)
            or _contains_reparse(project_root, self.projects_root)
        ):
            raise LocalWorkerError(
                "source_project_path_escape",
                "The registered source project cannot cross the Workshop boundary",
            )
        candidate = self.projects_root / row["project_id"] / relative
        resolved = candidate.resolve(strict=False)
        if (
            not _is_within(resolved, project_root)
            or _contains_reparse(candidate, self.projects_root)
        ):
            raise LocalWorkerError(
                "source_path_escape",
                "The registered source cannot cross the project boundary",
            )
        if not resolved.is_file():
            raise LocalWorkerError(
                "source_missing",
                "The registered source file is unavailable",
                status=404,
            )
        size = resolved.stat().st_size
        if size > MAX_PACKAGE_BYTES:
            raise LocalWorkerError(
                "source_too_large",
                "The selected source exceeds the largest worker input limit",
            )
        raw = resolved.read_bytes()
        digest = sha256_bytes(raw)
        stored = str(row["sha256"] or "").upper()
        if not stored or digest != stored:
            raise LocalWorkerError(
                "source_hash_mismatch",
                "The selected source changed after it was registered",
                status=409,
            )
        return resolved, raw, digest

    def _resolve_source(
        self,
        connection: sqlite3.Connection,
        artifact_id: str,
        *,
        worker_id: str,
        selection: Any = None,
    ) -> dict[str, Any]:
        if artifact_id.startswith("job-result:"):
            if worker_id not in BUILDER_WORKER_IDS:
                raise LocalWorkerError("source_not_supported_by_worker", "Approved worker results are supported only by the fixed proposal builders")
            job_id = artifact_id.removeprefix("job-result:").strip()
            job = self._job_row(connection, job_id)
            if job["status"] not in {"result_approved", "draft_saved"}:
                raise LocalWorkerError("source_result_not_approved", "Only an approved inactive worker result can be selected", status=409)
            job_plan = json_value(job["payload"], {})
            result = json_value(job["result"], {})
            output = result.get("output")
            if not isinstance(output, dict) or result.get("accepted") is not True:
                raise LocalWorkerError("source_result_invalid", "The approved worker result is unavailable", status=409)
            content = output.get("text") or output.get("content") or canonical_json(output)
            if not isinstance(content, str) or not content.strip():
                raise LocalWorkerError("source_blank", "Approved worker results must contain nonblank text")
            digest = sha256_text(content)
            return {
                "artifactId": artifact_id, "projectId": job["project_id"],
                "title": f"Approved {job_plan.get('workerName') or 'worker'} result · {job_id[:8]}",
                "kind": "approved-worker-result", "version": None, "sha256": digest,
                "bytes": len(content.encode("utf-8")), "suffix": ".txt", "encoding": "UTF-8",
                "content": content, "selection": None, "path": None,
            }
        row = self._artifact_row(connection, artifact_id)
        payload = json_value(row["payload"], {})
        kind = str(row["kind"])
        content: str | None = None
        path: Path | None = None
        suffix = ""
        source_version: int | None = None
        digest = str(row["sha256"] or "").upper()
        byte_count = 0
        encoding: str | None = None

        if kind == "document" and payload.get("schemaVersion") == "write-project-v1":
            content = str(payload.get("body") or "")
            source_version = int(payload.get("currentVersion") or 0)
            digest = sha256_text(content)
            byte_count = len(content.encode("utf-8"))
            suffix = ".md"
            encoding = "UTF-8"
        elif kind == "conversation" and payload.get("schemaVersion") == "talk-session-v1":
            source_version = int(payload.get("currentVersion") or 0)
            version = connection.execute(
                "SELECT transcript_json,transcript_sha256 FROM talk_versions WHERE artifact_id=? AND version_number=?",
                (row["id"], source_version),
            ).fetchone()
            if version is None:
                raise LocalWorkerError(
                    "source_version_missing",
                    "The current Talk version is unavailable",
                    status=409,
                )
            entries = json_value(version["transcript_json"], [])
            content = "\n\n".join(
                str(entry.get("content") or "")
                for entry in entries
                if isinstance(entry, dict)
            )
            digest = str(version["transcript_sha256"]).upper()
            byte_count = len(content.encode("utf-8"))
            suffix = ".txt"
            encoding = "UTF-8"
        else:
            path, raw, digest = self._registered_file(row)
            suffix = path.suffix.lower()
            byte_count = len(raw)
            if suffix in TEXT_SUFFIXES:
                if b"\x00" in raw:
                    raise LocalWorkerError(
                        "source_not_text",
                        "The selected source contains binary data",
                    )
                try:
                    content = raw.decode("utf-8", errors="strict")
                except UnicodeDecodeError as exc:
                    raise LocalWorkerError(
                        "source_encoding_unsupported",
                        "The selected text must be valid UTF-8",
                    ) from exc
                encoding = "UTF-8"

        if worker_id == "package-manifest-validator":
            if path is None or suffix not in PACKAGE_SUFFIXES:
                raise LocalWorkerError(
                    "package_source_required",
                    "Choose a registered JSON manifest or ZIP package",
                )
        else:
            if content is None:
                raise LocalWorkerError(
                    "text_source_required",
                    "Choose a registered text source",
                )
            limit = (
                MAX_NOTE_BYTES
                if worker_id == "note-proposal-worker"
                else MAX_TEXT_BYTES
            )
            if byte_count > limit:
                raise LocalWorkerError(
                    "source_too_large",
                    f"The selected text exceeds the {limit // 1024} KiB worker limit",
                )
            if worker_id in BUILDER_WORKER_IDS and not str(content or "").strip():
                raise LocalWorkerError(
                    "source_blank",
                    "Builder sources must contain nonblank text",
                )
            if worker_id == "code-structure-inspector" and (
                suffix not in CODE_SUFFIXES and kind not in {"document", "conversation"}
            ):
                raise LocalWorkerError(
                    "code_type_unsupported",
                    "The Code Structure Inspector supports registered text code",
                )

        selected: str | None = None
        if selection is not None:
            if not isinstance(selection, str):
                raise LocalWorkerError(
                    "selection_invalid",
                    "Selected content must be text",
                )
            selected = selection.strip()
            if not selected:
                raise LocalWorkerError(
                    "selection_blank",
                    "Select nonblank source content",
                )
            if content is None or selected not in content:
                raise LocalWorkerError(
                    "selection_not_in_source",
                    "The selected content is not present in the current source",
                    status=409,
                )
            if len(selected.encode("utf-8")) > MAX_NOTE_BYTES:
                raise LocalWorkerError(
                    "selection_too_large",
                    "Selected content exceeds the 256 KiB packet limit",
                )
        if worker_id == "note-proposal-worker" and selected is None:
            selected = content
            if not selected or not selected.strip():
                raise LocalWorkerError(
                    "selection_blank",
                    "The Note Proposal Worker requires nonblank source content",
                )

        allowed = self._allowed_workers(
            kind=kind,
            suffix=suffix,
            has_text=content is not None,
            size=byte_count,
        )
        if worker_id not in allowed:
            raise LocalWorkerError(
                "source_not_supported_by_worker",
                "The selected source is not supported by that worker",
            )
        return {
            "artifactId": row["id"],
            "projectId": row["project_id"],
            "title": row["title"],
            "kind": kind,
            "version": source_version,
            "sha256": digest,
            "bytes": byte_count,
            "suffix": suffix,
            "encoding": encoding,
            "content": content,
            "selection": selected,
            "path": path,
        }

    @staticmethod
    def _allowed_workers(
        *, kind: str, suffix: str, has_text: bool, size: int
    ) -> list[str]:
        allowed: list[str] = []
        if has_text and size <= MAX_TEXT_BYTES:
            allowed.append("approved-text-reader")
            allowed.append("note-proposal-worker")
            allowed.extend(sorted(BUILDER_WORKER_IDS))
        if has_text and size <= MAX_TEXT_BYTES and (
            suffix in CODE_SUFFIXES or kind in {"document", "conversation"}
        ):
            allowed.append("code-structure-inspector")
        if suffix in PACKAGE_SUFFIXES and size <= MAX_PACKAGE_BYTES:
            allowed.append("package-manifest-validator")
        return allowed

    def list_sources(self, project_id: str) -> list[dict[str, Any]]:
        project = str(project_id or "").strip()
        if not project:
            raise LocalWorkerError(
                "project_id_required",
                "Choose a project before selecting a worker source",
            )
        connection = self._connect()
        try:
            rows = connection.execute(
                "SELECT * FROM artifacts WHERE project_id=? ORDER BY lower(title),title,id",
                (project,),
            ).fetchall()
            values: list[dict[str, Any]] = []
            for row in rows:
                payload = json_value(row["payload"], {})
                kind = str(row["kind"])
                suffix = Path(str(row["path"] or "")).suffix.lower()
                size = 0
                has_text = False
                digest = str(row["sha256"] or "").upper()
                if kind == "document" and payload.get("schemaVersion") == "write-project-v1":
                    size = len(str(payload.get("body") or "").encode("utf-8"))
                    suffix = ".md"
                    has_text = True
                    digest = sha256_text(str(payload.get("body") or ""))
                elif kind == "conversation" and payload.get("schemaVersion") == "talk-session-v1":
                    current_version = int(payload.get("currentVersion") or 0)
                    version = connection.execute(
                        "SELECT transcript_json,transcript_sha256 FROM talk_versions WHERE artifact_id=? AND version_number=?",
                        (row["id"], current_version),
                    ).fetchone()
                    if version is None:
                        continue
                    entries = json_value(version["transcript_json"], [])
                    transcript = "\n\n".join(
                        str(entry.get("content") or "")
                        for entry in entries
                        if isinstance(entry, dict)
                    )
                    size = len(transcript.encode("utf-8"))
                    suffix = ".txt"
                    has_text = True
                    digest = str(version["transcript_sha256"] or "").upper()
                else:
                    try:
                        path, raw, digest = self._registered_file(row)
                        suffix = path.suffix.lower()
                        size = len(raw)
                        has_text = (
                            suffix in TEXT_SUFFIXES
                            and b"\x00" not in raw
                            and self._valid_utf8(raw)
                        )
                    except LocalWorkerError:
                        continue
                allowed = self._allowed_workers(
                    kind=kind,
                    suffix=suffix,
                    has_text=has_text,
                    size=size,
                )
                if allowed:
                    values.append(
                        {
                            "artifactId": row["id"],
                            "sourceId": row["id"],
                            "title": row["title"],
                            "kind": kind,
                            "sha256": digest,
                            "bytes": size,
                            "projectId": row["project_id"],
                            "authorityState": row["authority_state"],
                            "accessState": "public" if row["authority_state"] == "PUBLIC" else "protected",
                            "modifiedAt": row["updated_at"],
                            "allowedWorkers": allowed,
                            "sourceState": "current registered source",
                        }
                    )
            approved_rows = connection.execute(
                "SELECT * FROM jobs WHERE project_id=? AND operation LIKE 'local-worker:%' AND status IN ('result_approved','draft_saved') ORDER BY updated_at DESC,id",
                (project,),
            ).fetchall()
            for job in approved_rows:
                result = json_value(job["result"], {})
                output = result.get("output") if result.get("accepted") is True else None
                if not isinstance(output, dict):
                    continue
                content = output.get("text") or output.get("content") or canonical_json(output)
                if not isinstance(content, str) or not content.strip() or len(content.encode("utf-8")) > MAX_TEXT_BYTES:
                    continue
                job_plan = json_value(job["payload"], {})
                values.append({
                    "artifactId": f"job-result:{job['id']}", "sourceId": f"job-result:{job['id']}",
                    "title": f"Approved {job_plan.get('workerName') or 'worker'} result · {job['id'][:8]}",
                    "kind": "approved-worker-result", "sha256": sha256_text(content), "bytes": len(content.encode("utf-8")),
                    "projectId": project, "authorityState": "APPROVED-INACTIVE", "accessState": "protected",
                    "modifiedAt": job["updated_at"], "allowedWorkers": sorted(BUILDER_WORKER_IDS),
                    "sourceState": "current approved inactive worker result",
                })
            return values
        finally:
            connection.close()

    @staticmethod
    def _valid_utf8(raw: bytes) -> bool:
        try:
            raw.decode("utf-8", errors="strict")
            return True
        except UnicodeDecodeError:
            return False

    def _validate_expectations(
        self, expected_members: Any, expected_hashes: Any
    ) -> tuple[list[str], dict[str, str]]:
        members = expected_members if expected_members is not None else []
        hashes = expected_hashes if expected_hashes is not None else {}
        if not isinstance(members, list) or len(members) > MAX_EXPECTED_MEMBERS:
            raise LocalWorkerError(
                "expected_members_invalid",
                "Expected members must be a bounded list",
            )
        if not isinstance(hashes, dict) or len(hashes) > MAX_EXPECTED_MEMBERS:
            raise LocalWorkerError(
                "expected_hashes_invalid",
                "Expected hashes must be a bounded object",
            )
        clean_members = [_safe_member(member) for member in members]
        if len(set(clean_members)) != len(clean_members):
            raise LocalWorkerError(
                "expected_members_duplicate",
                "Expected package members must be unique",
            )
        clean_hashes: dict[str, str] = {}
        for key, value in hashes.items():
            member = _safe_member(key)
            digest = str(value or "").upper()
            if not re.fullmatch(r"[A-F0-9]{64}", digest):
                raise LocalWorkerError(
                    "expected_hash_invalid",
                    "Expected package hashes must be SHA-256 values",
                )
            clean_hashes[member] = digest
        return clean_members, clean_hashes

    def create_plan(self, request: dict[str, Any]) -> dict[str, Any]:
        allowed_fields = {
            "projectId",
            "workerId",
            "sourceArtifactId",
            "sourceArtifactIds",
            "destinationProfile",
            "goal",
            "selection",
            "purpose",
            "expectedMembers",
            "expectedHashes",
            "actor",
            "title",
            "roughText",
            "visualControls",
            "musicNotes",
            "musicLyrics",
            "productionControls",
            "videoNotes",
            "videoControls",
            "buildNotes",
            "buildControls",
            "moduleNotes",
            "moduleControls",
            "inferencePreset",
            "musicState",
        }
        if set(request) - allowed_fields:
            raise LocalWorkerError(
                "request_fields_invalid",
                "The worker plan request contains unsupported fields",
            )
        project_id = str(request.get("projectId") or "").strip()
        worker_id = str(request.get("workerId") or "").strip()
        artifact_id = str(request.get("sourceArtifactId") or "").strip()
        rough_text = ""
        music_notes = ""
        music_lyrics = ""
        video_notes = ""
        build_notes = ""
        module_notes = ""
        music_state: dict[str, Any] | None = None
        actor = str(request.get("actor") or "local-owner").strip()[:100]
        if not project_id:
            raise LocalWorkerError("project_id_required", "Choose a project")
        contract = self._validated_contract(worker_id)
        expected_members, expected_hashes = self._validate_expectations(
            request.get("expectedMembers"), request.get("expectedHashes")
        )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            project = connection.execute(
                "SELECT id FROM projects WHERE id=?", (project_id,)
            ).fetchone()
            if project is None:
                raise LocalWorkerError(
                    "project_not_found", "The selected project no longer exists", status=404
                )
            if worker_id in BUILDER_WORKER_IDS:
                raw_ids = request.get("sourceArtifactIds")
                rough_text = str(request.get("roughText") or "")
                visual_controls: dict[str, str] = {}
                production_controls: dict[str, str] = {}
                video_controls: dict[str, str] = {}
                build_controls: dict[str, str] = {}
                module_controls: dict[str, str] = {}
                inference: dict[str, Any] | None = None
                if worker_id == "draft-workshop":
                    if raw_ids is None:
                        raw_ids = []
                    if not isinstance(raw_ids, list) or len(raw_ids) > 1:
                        raise LocalWorkerError("builder_sources_invalid", "Choose one registered source or enter rough text")
                    if raw_ids and rough_text.strip():
                        raise LocalWorkerError("builder_sources_invalid", "Choose a registered source or rough text, not both")
                    if not raw_ids and (not rough_text.strip() or len(rough_text.encode("utf-8")) > MAX_TEXT_BYTES):
                        raise LocalWorkerError("builder_sources_invalid", "Enter nonblank rough text within the 512 KiB limit")
                elif worker_id == "evidence-compare":
                    if not isinstance(raw_ids, list) or not 2 <= len(raw_ids) <= 8:
                        raise LocalWorkerError("builder_sources_invalid", "Select 2 to 8 registered text sources")
                elif worker_id == "visual-brief-builder":
                    if raw_ids is None:
                        raw_ids = []
                    if not isinstance(raw_ids, list) or len(raw_ids) > 4:
                        raise LocalWorkerError("builder_sources_invalid", "Select no more than 4 registered text sources")
                    if not raw_ids and not rough_text.strip():
                        raise LocalWorkerError("builder_sources_invalid", "Select a registered source or enter nonblank visual notes")
                    if len(rough_text.encode("utf-8")) > MAX_TEXT_BYTES:
                        raise LocalWorkerError("builder_sources_invalid", "Visual notes exceed the 512 KiB limit")
                    raw_controls = request.get("visualControls") or {}
                    allowed_controls = {
                        "conceptTitle", "centralSubject", "setting", "moodEmotion",
                        "visualStyle", "composition", "cameraViewpoint", "lighting",
                        "colorDirection", "aspectRatio", "requiredText", "prohibitedText",
                        "requiredElements", "prohibitedElements", "realismLevel",
                        "referenceSourcePriority", "additionalInstructions",
                    }
                    if not isinstance(raw_controls, dict) or set(raw_controls) - allowed_controls:
                        raise LocalWorkerError("builder_controls_invalid", "Visual controls must use the fixed Visual Brief fields")
                    visual_controls = {key: str(raw_controls.get(key) or "").strip() for key in allowed_controls}
                    if any(len(value) > 4000 for value in visual_controls.values()) or len(canonical_json(visual_controls).encode("utf-8")) > 32000:
                        raise LocalWorkerError("builder_controls_invalid", "Visual controls exceed the bounded input limit")
                elif worker_id == "song-production-brief-builder":
                    if raw_ids is None:
                        raw_ids = []
                    music_notes = str(request.get("musicNotes") or "")
                    music_lyrics = str(request.get("musicLyrics") or "")
                    if not isinstance(raw_ids, list) or len(raw_ids) > 4:
                        raise LocalWorkerError("builder_sources_invalid", "Select no more than 4 registered text sources")
                    if not raw_ids and not music_notes.strip() and not music_lyrics.strip():
                        raise LocalWorkerError("builder_sources_invalid", "Select a source or enter meaningful music notes or lyrics")
                    if len(music_notes.encode("utf-8")) + len(music_lyrics.encode("utf-8")) > MAX_TEXT_BYTES:
                        raise LocalWorkerError("builder_sources_invalid", "Temporary music input exceeds the 512 KiB limit")
                    raw_controls = request.get("productionControls") or {}
                    allowed_controls = {
                        "workingTitle", "centralSubject", "emotionalArc", "genre", "subgenre",
                        "tempoBpm", "tonalCenter", "timeSignature", "vocalType", "vocalDelivery",
                        "instrumentation", "rhythmGroove", "songStructure", "intro", "verseTreatment",
                        "chorusTreatment", "bridgeBreakdown", "soloInstrumental", "ending",
                        "productionTexture", "recordingCharacter", "dynamicBuild", "referenceInfluences",
                        "requiredElements", "prohibitedElements", "lyricBoundaries",
                        "explicitLanguagePreference", "approximateDuration", "additionalInstructions",
                        "referenceSourcePriority",
                    }
                    if not isinstance(raw_controls, dict) or set(raw_controls) - allowed_controls:
                        raise LocalWorkerError("builder_controls_invalid", "Production controls must use the fixed Song Production Brief fields")
                    production_controls = {key: str(raw_controls.get(key) or "").strip() for key in allowed_controls}
                    if any(len(value) > 4000 for value in production_controls.values()) or len(canonical_json(production_controls).encode("utf-8")) > 48000:
                        raise LocalWorkerError("builder_controls_invalid", "Production controls exceed the bounded input limit")
                elif worker_id == "video-production-brief-builder":
                    if raw_ids is None:
                        raw_ids = []
                    video_notes = str(request.get("videoNotes") or "")
                    if not isinstance(raw_ids, list) or len(raw_ids) > 4:
                        raise LocalWorkerError("builder_sources_invalid", "Select no more than 4 registered text sources")
                    if not raw_ids and not video_notes.strip():
                        raise LocalWorkerError("builder_sources_invalid", "Select a source or enter meaningful video notes")
                    if len(video_notes.encode("utf-8")) > MAX_TEXT_BYTES:
                        raise LocalWorkerError("builder_sources_invalid", "Temporary video notes exceed the 512 KiB limit")
                    raw_controls = request.get("videoControls") or {}
                    allowed_controls = {
                        "workingTitle", "productionGoal", "coreConcept", "intendedAudience",
                        "targetDuration", "aspectRatio", "resolutionIntent", "visualStyle",
                        "pacing", "cameraLanguage", "environmentLocation", "subjectCharacterNotes",
                        "wardrobeAppearance", "propsObjects", "lighting", "colorPalette",
                        "composition", "lensFraming", "cameraMovement", "subjectMovement",
                        "shotIdeas", "transitionStyle", "storySequence", "openingBeat",
                        "mainProgression", "closingBeat", "audioDialogue", "narrationVoice",
                        "musicNotes", "soundDesignNotes", "onScreenText", "effectsCompositing",
                        "continuityRequirements", "productionConstraints", "safetyLegalConsent",
                        "referenceSourcePriority", "unresolvedDecisions", "additionalInstructions",
                    }
                    if not isinstance(raw_controls, dict) or set(raw_controls) - allowed_controls:
                        raise LocalWorkerError("builder_controls_invalid", "Video controls must use the fixed Video Production Brief fields")
                    video_controls = {key: str(raw_controls.get(key) or "").strip() for key in allowed_controls}
                    if any(len(value) > 4000 for value in video_controls.values()) or len(canonical_json(video_controls).encode("utf-8")) > 64000:
                        raise LocalWorkerError("builder_controls_invalid", "Video controls exceed the bounded input limit")
                elif worker_id == "build-work-order-builder":
                    if raw_ids is None:
                        raw_ids = []
                    build_notes = str(request.get("buildNotes") or "")
                    if not isinstance(raw_ids, list) or len(raw_ids) > 4:
                        raise LocalWorkerError("builder_sources_invalid", "Select no more than 4 registered text sources")
                    if len(build_notes.encode("utf-8")) > MAX_TEXT_BYTES:
                        raise LocalWorkerError("builder_sources_invalid", "Temporary build input exceeds the 512 KiB limit")
                    raw_controls = request.get("buildControls") or {}
                    allowed_controls = {
                        "workingTitle", "buildGoal", "existingContext", "desiredOutcome",
                        "requirements", "constraints", "relevantFilesComponents", "uiRequirements",
                        "backendRequirements", "dataPersistence", "externalDependencies",
                        "performanceLimits", "securitySafety", "failureBehavior", "acceptanceCriteria",
                        "testingExpectations", "deploymentExpectations", "rollbackExpectations",
                        "inScope", "outOfScope", "referenceSourcePriority", "unresolvedDecisions",
                        "additionalInstructions", "capabilityRequest",
                    }
                    if not isinstance(raw_controls, dict) or set(raw_controls) - allowed_controls:
                        raise LocalWorkerError("builder_controls_invalid", "Build controls must use the fixed Build Work Order fields")
                    build_controls = {key: str(raw_controls.get(key) or "").strip() for key in allowed_controls}
                    if not raw_ids and not build_notes.strip() and not any(build_controls.values()):
                        raise LocalWorkerError("builder_sources_invalid", "Select a source or enter meaningful build input")
                    if any(len(value) > 4000 for value in build_controls.values()) or len(canonical_json(build_controls).encode("utf-8")) > 64000:
                        raise LocalWorkerError("builder_controls_invalid", "Build controls exceed the bounded input limit")
                elif worker_id == "module-proposal-builder":
                    if raw_ids is None:
                        raw_ids = []
                    module_notes = str(request.get("moduleNotes") or "")
                    if not isinstance(raw_ids, list) or len(raw_ids) > 4:
                        raise LocalWorkerError("builder_sources_invalid", "Select no more than 4 registered text sources")
                    if len(module_notes.encode("utf-8")) > MAX_TEXT_BYTES:
                        raise LocalWorkerError("builder_sources_invalid", "Temporary module input exceeds the 512 KiB limit")
                    raw_controls = request.get("moduleControls") or {}
                    allowed_controls = {
                        "moduleName", "purpose", "problemSolved", "targetRoom", "inputs", "outputs",
                        "localCloudBoundary", "dependencies", "hardwareExpectations", "dataStorageNeeds",
                        "permissionsCapabilities", "uiNeeds", "risks", "licensingNotes", "integrationPoints",
                        "testingRequirements", "recoveryRequirements", "rollbackRequirements",
                        "acceptanceCriteria", "failureBehavior", "referenceSourcePriority",
                        "unresolvedDecisions", "additionalInstructions", "scaffoldType",
                    }
                    if not isinstance(raw_controls, dict) or set(raw_controls) - allowed_controls:
                        raise LocalWorkerError("builder_controls_invalid", "Module controls must use the fixed Module Proposal fields")
                    module_controls = {key: str(raw_controls.get(key) or "").strip() for key in allowed_controls}
                    if not raw_ids and not module_notes.strip() and not any(module_controls.values()):
                        raise LocalWorkerError("builder_sources_invalid", "Select a source or enter meaningful module input")
                    if any(len(value) > 4000 for value in module_controls.values()) or len(canonical_json(module_controls).encode("utf-8")) > 64000:
                        raise LocalWorkerError("builder_controls_invalid", "Module controls exceed the bounded input limit")
                elif worker_id == "local-ai-rewrite":
                    raw_music_state = request.get("musicState")
                    if raw_music_state is not None:
                        if raw_ids is None:
                            raw_ids = []
                        if raw_ids != [] or not isinstance(raw_music_state, dict):
                            raise LocalWorkerError("builder_sources_invalid", "Music Studio AI requires one temporary music state and no registered source IDs")
                        if str(raw_music_state.get("schemaVersion") or "") != "music-pattern-v2":
                            raise LocalWorkerError("builder_sources_invalid", "Music Studio state must use music-pattern-v2")
                        encoded = canonical_json(raw_music_state).encode("utf-8")
                        if len(encoded) > 128 * 1024:
                            raise LocalWorkerError("builder_sources_invalid", "Music Studio state exceeds the bounded 128 KiB limit")
                        music_state = raw_music_state
                    elif not isinstance(raw_ids, list) or not 1 <= len(raw_ids) <= 4:
                        raise LocalWorkerError("builder_sources_invalid", "Write Studio AI requires one Write source and no more than three explicit context sources")
                elif not isinstance(raw_ids, list) or not raw_ids or len(raw_ids) > 20:
                    raise LocalWorkerError("builder_sources_invalid", "Select 1 to 20 registered sources")
                artifact_ids = [str(value or "").strip() for value in raw_ids]
                if any(not value for value in artifact_ids) or len(set(artifact_ids)) != len(artifact_ids):
                    raise LocalWorkerError("builder_sources_invalid", "Selected source IDs must be nonblank and unique")
                profile = str(request.get("destinationProfile") or "").strip()
                if profile not in BUILDER_WORKERS[worker_id]["profiles"]:
                    raise LocalWorkerError("builder_profile_unsupported", "Choose a supported destination profile")
                goal = str(request.get("goal") or "").strip()
                if (worker_id not in {"draft-workshop", "evidence-compare", "visual-brief-builder", "song-production-brief-builder", "video-production-brief-builder", "build-work-order-builder", "module-proposal-builder", "local-ai-rewrite"} and not goal) or len(goal) > 8000:
                    raise LocalWorkerError("builder_goal_invalid", "Enter a nonblank goal of at most 8,000 characters")
                if worker_id == "local-ai-rewrite":
                    if self._model_bay is None:
                        raise LocalWorkerError("model_bay_unavailable", "The Local AI Model Bay is unavailable", status=503)
                    try:
                        inference = self._model_bay.inference_plan(writing_action_task(profile), str(request.get("inferencePreset") or "Balanced"), goal)
                    except ModelBayError as error:
                        raise LocalWorkerError(error.code, str(error), status=error.status, details=error.details) from error
            else:
                artifact_ids = [artifact_id]
                profile = ""
                goal = ""
            sources = [
                self._resolve_source(
                    connection,
                    value,
                    worker_id=worker_id,
                    selection=request.get("selection") if index == 0 else None,
                )
                for index, value in enumerate(artifact_ids)
            ]
            if worker_id == "draft-workshop" and not sources:
                raw = rough_text.encode("utf-8")
                digest = sha256_bytes(raw)
                sources = [{
                    "artifactId": f"rough-text:{digest}", "projectId": project_id,
                    "title": "Owner-entered rough text", "kind": "temporary-rough-text",
                    "version": None, "sha256": digest, "bytes": len(raw),
                    "suffix": ".txt", "encoding": "UTF-8", "content": rough_text,
                    "selection": None, "path": None,
                }]
            if worker_id == "local-ai-rewrite" and music_state is not None:
                content = canonical_json(music_state)
                raw = content.encode("utf-8")
                digest = sha256_bytes(raw)
                sources = [{
                    "artifactId": f"music-studio:{digest}", "projectId": project_id,
                    "title": "Current Music Studio state", "kind": "temporary-music-studio-state",
                    "version": None, "sha256": digest, "bytes": len(raw),
                    "suffix": ".json", "encoding": "UTF-8", "content": content,
                    "selection": None, "path": None,
                }]
            if worker_id == "visual-brief-builder" and rough_text.strip():
                raw = rough_text.encode("utf-8")
                digest = sha256_bytes(raw)
                sources.append({
                    "artifactId": f"visual-notes:{digest}", "projectId": project_id,
                    "title": "Owner-entered visual notes", "kind": "temporary-visual-notes",
                    "version": None, "sha256": digest, "bytes": len(raw),
                    "suffix": ".txt", "encoding": "UTF-8", "content": rough_text,
                    "selection": None, "path": None,
                })
            if worker_id == "song-production-brief-builder":
                for content, prefix, title, kind in (
                    (music_notes, "music-notes", "Owner-entered music notes", "temporary-music-notes"),
                    (music_lyrics, "music-lyrics", "Owner-supplied lyrics or lyric fragments", "temporary-music-lyrics"),
                ):
                    if content.strip():
                        raw = content.encode("utf-8")
                        digest = sha256_bytes(raw)
                        sources.append({
                            "artifactId": f"{prefix}:{digest}", "projectId": project_id,
                            "title": title, "kind": kind, "version": None,
                            "sha256": digest, "bytes": len(raw), "suffix": ".txt",
                            "encoding": "UTF-8", "content": content, "selection": None, "path": None,
                        })
            if worker_id == "video-production-brief-builder" and video_notes.strip():
                raw = video_notes.encode("utf-8")
                digest = sha256_bytes(raw)
                sources.append({
                    "artifactId": f"video-notes:{digest}", "projectId": project_id,
                    "title": "Owner-entered video notes", "kind": "temporary-video-notes",
                    "version": None, "sha256": digest, "bytes": len(raw),
                    "suffix": ".txt", "encoding": "UTF-8", "content": video_notes,
                    "selection": None, "path": None,
                })
            if worker_id in {"build-work-order-builder", "module-proposal-builder"}:
                notes = build_notes if worker_id == "build-work-order-builder" else module_notes
                controls = build_controls if worker_id == "build-work-order-builder" else module_controls
                prefix = "build-input" if worker_id == "build-work-order-builder" else "module-input"
                kind = "temporary-build-input" if worker_id == "build-work-order-builder" else "temporary-module-input"
                title = "Owner-entered build input" if worker_id == "build-work-order-builder" else "Owner-entered module input"
                canonical = canonical_json({"ownerNotes": notes, "controls": controls})
                raw = canonical.encode("utf-8")
                digest = sha256_bytes(raw)
                sources.append({
                    "artifactId": f"{prefix}:{digest}", "projectId": project_id,
                    "title": title, "kind": kind, "version": None,
                    "sha256": digest, "bytes": len(raw), "suffix": ".json",
                    "encoding": "UTF-8", "content": canonical, "ownerNotes": notes,
                    "selection": None, "path": None,
                })
            if any(source["projectId"] != project_id for source in sources):
                raise LocalWorkerError("source_project_mismatch", "Every selected source must belong to this project")
            if worker_id in BUILDER_WORKER_IDS and sum(source["bytes"] for source in sources) > MAX_TEXT_BYTES:
                raise LocalWorkerError("builder_sources_too_large", "Selected source text exceeds the 512 KiB builder limit")
            source = sources[0]
            purpose = str(request.get("purpose") or contract["responsibility"]).strip()
            if not purpose or len(purpose) > 500:
                raise LocalWorkerError(
                    "purpose_invalid", "Job purpose must be 1 to 500 characters"
                )
            packet_content = source["selection"]
            packet = {
                "schemaVersion": PACKET_SCHEMA_VERSION,
                "sourceReferences": [
                    {
                        "artifactId": source["artifactId"],
                        "title": source["title"],
                        "kind": source["kind"],
                        "version": source["version"],
                        "sha256": source["sha256"],
                    }
                    for source in sources
                ],
                "minimumContent": (
                    packet_content
                    if worker_id == "note-proposal-worker"
                    else None
                ),
                "jobPurpose": purpose,
                "permissions": contract["requiredPermissions"],
                "prohibitedPermissions": contract["prohibitedPermissions"],
                "expectedOutput": contract["outputSchema"],
                "limits": contract["limits"],
                "provenance": {
                    "sourceArtifactIds": [value["artifactId"] for value in sources],
                    "sourceSha256s": [value["sha256"] for value in sources],
                    "sourceVersions": [value["version"] for value in sources],
                    "workerContractHash": contract["contractHash"],
                },
                "validation": {
                    "sourceCurrent": True,
                    "sourceSelectionCurrent": True,
                    "contractValid": True,
                    "networkDenied": worker_id != "local-ai-rewrite",
                    "loopbackOnly": worker_id == "local-ai-rewrite",
                    "externalNetworkDenied": True,
                    "shellDenied": True,
                },
            }
            packet_hash = sha256_text(canonical_json(packet))
            job_id = str(uuid.uuid4())
            created = utc_now()
            expires = (
                datetime.now(timezone.utc) + timedelta(hours=PLAN_LIFETIME_HOURS)
            ).isoformat()
            capability_context = None
            if worker_id == "build-work-order-builder" and self._capability_registry is not None:
                capability_request = str(
                    build_controls.get("capabilityRequest")
                    or build_controls.get("buildGoal")
                    or goal
                    or ""
                ).strip()
                if capability_request:
                    try:
                        recommendation = self._capability_registry.recommend(capability_request)
                    except CapabilityError as error:
                        raise LocalWorkerError(error.code, str(error)) from error

                    def compact_capability(item: dict[str, Any] | None) -> dict[str, Any] | None:
                        if item is None:
                            return None
                        return {
                            "capabilityId": item["capabilityId"],
                            "name": item["name"],
                            "status": item["status"],
                            "healthState": item["healthState"],
                            "costClass": item["costClass"],
                            "networkRequirement": item["networkRequirement"],
                            "authorityLevel": item["authorityLevel"],
                            "hardwareFit": item["hardwareFit"],
                            "replacementGroup": item["replacementGroup"],
                            "knownLimitations": item["knownLimitations"],
                        }

                    capability_context = {
                        "schemaVersion": recommendation["schemaVersion"],
                        "registryHash": recommendation["registryHash"],
                        "hardwareProfileHash": self._capability_registry.profile["profileHash"],
                        "request": recommendation["request"],
                        "replacementGroup": recommendation["replacementGroup"],
                        "recommended": compact_capability(recommendation["recommended"]),
                        "matched": [compact_capability(item) for item in recommendation["matched"]],
                        "discoveredCandidates": [compact_capability(item) for item in recommendation["discoveredCandidates"]],
                        "createOurOwn": recommendation["createOurOwn"],
                        "decision": recommendation["decision"],
                    }
                    capability_context["contextHash"] = sha256_text(canonical_json(capability_context))
            plan = {
                "schemaVersion": JOB_SCHEMA_VERSION,
                "jobId": job_id,
                "projectId": project_id,
                "workerId": worker_id,
                "workerVersion": contract["version"],
                "workerName": contract["name"],
                "contractHash": contract["contractHash"],
                "implementationHash": contract["implementationHash"],
                "purpose": purpose,
                "planId": job_id,
                "source": {
                    "artifactId": source["artifactId"],
                    "title": source["title"],
                    "kind": source["kind"],
                    "version": source["version"],
                    "sha256": source["sha256"],
                    "bytes": source["bytes"],
                    "suffix": source["suffix"],
                },
                "sources": [
                    {
                        "artifactId": value["artifactId"], "projectId": value["projectId"],
                        "title": value["title"], "kind": value["kind"], "version": value["version"],
                        "sha256": value["sha256"], "bytes": value["bytes"], "suffix": value["suffix"],
                    }
                    for value in sources
                ],
                "destinationProfile": profile or None,
                "ownerGoal": goal if worker_id in {"draft-workshop", "evidence-compare", "visual-brief-builder", "song-production-brief-builder", "video-production-brief-builder", "build-work-order-builder", "module-proposal-builder", "local-ai-rewrite"} else (goal or None),
                "roughText": rough_text if (worker_id == "draft-workshop" and not artifact_ids) or worker_id == "visual-brief-builder" else None,
                "visualControls": visual_controls if worker_id == "visual-brief-builder" else None,
                "musicNotes": music_notes if worker_id == "song-production-brief-builder" else None,
                "musicLyrics": music_lyrics if worker_id == "song-production-brief-builder" else None,
                "productionControls": production_controls if worker_id == "song-production-brief-builder" else None,
                "videoNotes": video_notes if worker_id == "video-production-brief-builder" else None,
                "videoControls": video_controls if worker_id == "video-production-brief-builder" else None,
                "buildNotes": build_notes if worker_id == "build-work-order-builder" else None,
                "buildControls": build_controls if worker_id == "build-work-order-builder" else None,
                "capabilityRegistryContext": capability_context if worker_id == "build-work-order-builder" else None,
                "moduleNotes": module_notes if worker_id == "module-proposal-builder" else None,
                "moduleControls": module_controls if worker_id == "module-proposal-builder" else None,
                "musicState": music_state if worker_id == "local-ai-rewrite" else None,
                "inference": inference if worker_id == "local-ai-rewrite" else None,
                "selection": source["selection"],
                "noteTitle": _bounded_title(
                    request.get("title"), f"Note from {source['title']}"
                ),
                "expectedMembers": expected_members,
                "expectedHashes": expected_hashes,
                "packet": packet,
                "packetHash": packet_hash,
                "reads": [value["title"] for value in sources],
                "mayCreate": (
                    ["One new note, only after result approval"]
                    if worker_id == "note-proposal-worker"
                    else (["One inactive draft after separate result approval and save"] if worker_id in BUILDER_WORKER_IDS else [])
                ),
                "cannotAccess": contract["prohibitedPermissions"],
                "createdAt": created,
                "expiresAt": expires,
                "automaticAttachment": False,
                "automaticActivation": False,
                "modulePromotion": False,
            }
            plan_hash = sha256_text(canonical_json(plan))
            plan["planHash"] = plan_hash
            connection.execute(
                "INSERT INTO jobs(id,project_id,operation,status,payload,result,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    job_id,
                    project_id,
                    f"local-worker:{worker_id}",
                    "planned",
                    canonical_json(plan),
                    "{}",
                    created,
                    created,
                ),
            )
            receipt_id = self._receipt(
                connection,
                project_id,
                "local_worker.plan.create",
                actor,
                {
                    "jobId": job_id,
                    "workerId": worker_id,
                    "sourceArtifactIds": [value["artifactId"] for value in sources],
                    "sourceSha256s": [value["sha256"] for value in sources],
                    "contractHash": contract["contractHash"],
                    "packetHash": packet_hash,
                    "planHash": plan_hash,
                    "expiresAt": expires,
                },
            )
            self._evidence(
                connection,
                job_id,
                "validated-plan",
                {
                    "planHash": plan_hash,
                    "packetHash": packet_hash,
                    "contractHash": contract["contractHash"],
                    "sourceSha256s": [value["sha256"] for value in sources],
                    "receiptId": receipt_id,
                },
            )
            connection.commit()
            return self.get_job(job_id)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _job_row(
        self, connection: sqlite3.Connection, job_id: str
    ) -> sqlite3.Row:
        if (
            not isinstance(job_id, str)
            or not job_id.strip()
            or len(job_id) > 100
        ):
            raise LocalWorkerError("job_id_invalid", "Job identity is invalid")
        row = connection.execute(
            "SELECT * FROM jobs WHERE id=? AND operation LIKE 'local-worker:%'",
            (job_id.strip(),),
        ).fetchone()
        if row is None:
            raise LocalWorkerError(
                "job_not_found", "That worker job was not found", status=404
            )
        return row

    def _serialize_job(
        self, connection: sqlite3.Connection, row: sqlite3.Row
    ) -> dict[str, Any]:
        plan = json_value(row["payload"], {})
        result = json_value(row["result"], {})
        evidence_rows = connection.execute(
            "SELECT kind,sha256,details,created_at FROM worker_job_evidence WHERE job_id=? ORDER BY created_at,id",
            (row["id"],),
        ).fetchall()
        contract = self._validated_contract(plan.get("workerId", ""))
        state_labels = {
            "planned": "Plan awaiting decision",
            "plan_approved": "Plan approved and ready to run",
            "plan_rejected": "Plan rejected",
            "running": "Worker running",
            "interrupted": "Interrupted safely; recovery available",
            "awaiting_result_approval": "Result ready for review",
            "result_approved": "Result approved; no attachment or activation",
            "draft_saved": "Approved result saved as one inactive draft",
            "result_rejected": "Result rejected",
            "rolled_back": "Accepted note rolled back",
            "cancelled": "Job cancelled",
            "stale": "Plan stale; source changed",
            "abandoned": "Plan expired",
            "failed": "Job failed safely",
        }
        return {
            "jobId": row["id"],
            "projectId": row["project_id"],
            "status": row["status"],
            "statusLabel": state_labels.get(row["status"], row["status"]),
            "worker": {
                "workerId": plan.get("workerId"),
                "name": plan.get("workerName"),
                "description": contract["description"],
                "version": plan.get("workerVersion"),
            },
            "source": {
                "artifactId": plan.get("source", {}).get("artifactId"),
                "title": plan.get("source", {}).get("title"),
                "kind": plan.get("source", {}).get("kind"),
            },
            "sources": [
                {"artifactId": value.get("artifactId"), "title": value.get("title"), "kind": value.get("kind"), "sha256": value.get("sha256"), "bytes": value.get("bytes")}
                for value in (plan.get("sources") or [plan.get("source", {})])
            ],
            "plan": {
                "purpose": plan.get("purpose"),
                "reads": plan.get("reads", []),
                "mayCreate": plan.get("mayCreate", []),
                "cannotAccess": plan.get("cannotAccess", []),
                "expiresAt": plan.get("expiresAt"),
                "approval": plan.get("approval"),
                "destinationProfile": plan.get("destinationProfile"),
                "ownerGoal": plan.get("ownerGoal"),
                "visualControls": plan.get("visualControls"),
                "capabilityRegistryContext": plan.get("capabilityRegistryContext"),
                "source": dict(plan.get("source") or {}),
                "inference": dict(plan.get("inference") or {}),
            },
            "result": result,
            "evidence": [
                {
                    "kind": evidence["kind"],
                    "sha256": evidence["sha256"],
                    "createdAt": evidence["created_at"],
                    "receiptId": json_value(
                        evidence["details"], {}
                    ).get("receiptId"),
                }
                for evidence in evidence_rows
            ],
            "advanced": {
                "planHash": plan.get("planHash"),
                "packetHash": plan.get("packetHash"),
                "contractHash": plan.get("contractHash"),
                "implementationHash": plan.get("implementationHash"),
                "sourceSha256": plan.get("source", {}).get("sha256"),
                "packet": plan.get("packet"),
            },
            "actions": {
                "approvePlan": row["status"] == "planned",
                "rejectPlan": row["status"] == "planned",
                "execute": row["status"] == "plan_approved",
                "cancel": row["status"]
                in {"planned", "plan_approved", "interrupted"},
                "recover": row["status"] == "interrupted",
                "approveResult": row["status"] == "awaiting_result_approval",
                "rejectResult": row["status"] == "awaiting_result_approval",
                "rollback": row["status"] == "result_approved"
                and plan.get("workerId") == "note-proposal-worker"
                and bool(result.get("acceptance", {}).get("noteArtifactId")),
                "saveDraft": row["status"] == "result_approved"
                and plan.get("workerId") in BUILDER_WORKER_IDS
                and not bool(result.get("savedDraft")),
                "export": row["status"] in {"result_approved", "draft_saved"}
                and plan.get("workerId") in BUILDER_WORKER_IDS,
                "rollbackDraft": row["status"] == "draft_saved"
                and plan.get("workerId") in BUILDER_WORKER_IDS
                and bool(result.get("savedDraft", {}).get("artifactId")),
                "deleteHistory": row["status"] in SAFE_DELETE_STATES,
            },
            "attachmentStatus": "unattached",
            "activationStatus": "inactive",
            "modulePromotionStatus": "not-requested",
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
        }

    def get_job(self, job_id: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            return self._serialize_job(
                connection, self._job_row(connection, job_id)
            )
        finally:
            connection.close()

    def list_jobs(
        self, project_id: str | None = None, *, limit: int = 100
    ) -> list[dict[str, Any]]:
        bounded = min(max(int(limit), 1), 200)
        connection = self._connect()
        try:
            if project_id:
                rows = connection.execute(
                    "SELECT * FROM jobs WHERE operation LIKE 'local-worker:%' AND project_id=? ORDER BY updated_at DESC LIMIT ?",
                    (project_id, bounded),
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT * FROM jobs WHERE operation LIKE 'local-worker:%' ORDER BY updated_at DESC LIMIT ?",
                    (bounded,),
                ).fetchall()
            return [self._serialize_job(connection, row) for row in rows]
        finally:
            connection.close()

    def decide_plan(
        self, job_id: str, decision: Any, note: Any, *, actor: str
    ) -> dict[str, Any]:
        choice = str(decision or "").strip().lower()
        if choice not in {"approve", "reject"}:
            raise LocalWorkerError(
                "plan_decision_invalid", "Choose approve or reject"
            )
        approval_note = _approval_note(note) if choice == "approve" else str(note or "").strip()[:APPROVAL_NOTE_MAX]
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._job_row(connection, job_id)
            if row["status"] != "planned":
                raise LocalWorkerError(
                    "plan_already_decided",
                    "This plan is no longer awaiting a decision",
                    status=409,
                )
            plan = json_value(row["payload"], {})
            status = "plan_approved" if choice == "approve" else "plan_rejected"
            decided = utc_now()
            plan["approval"] = {
                "decision": choice,
                "note": approval_note,
                "actor": actor[:100] or "local-owner",
                "decidedAt": decided,
                "planHash": plan.get("planHash"),
            }
            connection.execute(
                "UPDATE jobs SET status=?,payload=?,updated_at=? WHERE id=?",
                (status, canonical_json(plan), decided, row["id"]),
            )
            receipt_id = self._receipt(
                connection,
                row["project_id"],
                f"local_worker.plan.{choice}",
                actor,
                {
                    "jobId": row["id"],
                    "workerId": plan.get("workerId"),
                    "planHash": plan.get("planHash"),
                    "decision": choice,
                    "note": approval_note,
                },
            )
            self._evidence(
                connection,
                row["id"],
                "plan-decision",
                {
                    "decision": choice,
                    "planHash": plan.get("planHash"),
                    "receiptId": receipt_id,
                },
            )
            connection.commit()
            return self._serialize_job(
                connection, self._job_row(connection, row["id"])
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _verify_current_source(
        self, connection: sqlite3.Connection, plan: dict[str, Any]
    ) -> dict[str, Any]:
        worker_id = str(plan.get("workerId") or "")
        planned_sources = plan.get("sources") or [plan.get("source", {})]
        sources = []
        for planned in planned_sources:
            if planned.get("kind") in {"temporary-rough-text", "temporary-visual-notes", "temporary-music-notes", "temporary-music-lyrics", "temporary-music-studio-state", "temporary-video-notes", "temporary-build-input", "temporary-module-input"} and worker_id in {"draft-workshop", "visual-brief-builder", "song-production-brief-builder", "video-production-brief-builder", "build-work-order-builder", "module-proposal-builder", "local-ai-rewrite"}:
                content = str(
                    canonical_json(plan.get("musicState") or {}) if planned.get("kind") == "temporary-music-studio-state"
                    else plan.get("musicNotes") if planned.get("kind") == "temporary-music-notes"
                    else plan.get("musicLyrics") if planned.get("kind") == "temporary-music-lyrics"
                    else plan.get("videoNotes") if planned.get("kind") == "temporary-video-notes"
                    else canonical_json({"ownerNotes": plan.get("buildNotes") or "", "controls": plan.get("buildControls") or {}}) if planned.get("kind") == "temporary-build-input"
                    else canonical_json({"ownerNotes": plan.get("moduleNotes") or "", "controls": plan.get("moduleControls") or {}}) if planned.get("kind") == "temporary-module-input"
                    else plan.get("roughText") or ""
                )
                raw = content.encode("utf-8")
                source = {
                    **planned, "projectId": plan.get("projectId"), "content": content,
                    "encoding": "UTF-8", "selection": None, "path": None,
                    "sha256": sha256_bytes(raw), "bytes": len(raw),
                }
                if planned.get("kind") == "temporary-build-input":
                    source["ownerNotes"] = str(plan.get("buildNotes") or "")
                if planned.get("kind") == "temporary-module-input":
                    source["ownerNotes"] = str(plan.get("moduleNotes") or "")
            else:
                source = self._resolve_source(
                    connection,
                    str(planned.get("artifactId") or ""),
                    worker_id=worker_id,
                    selection=plan.get("selection") if len(sources) == 0 else None,
                )
            expected = str(planned.get("sha256") or "").upper()
            if source["sha256"] != expected:
                raise LocalWorkerError(
                    "stale_plan",
                    "A selected source changed after this worker plan was created",
                    status=409,
                    details={"sourceArtifactId": source["artifactId"], "expectedSha256": expected, "currentSha256": source["sha256"]},
                )
            sources.append(source)
        if worker_id == "build-work-order-builder" and plan.get("capabilityRegistryContext"):
            if self._capability_registry is None:
                raise LocalWorkerError(
                    "capability_registry_unavailable",
                    "The capability registry used by this Build plan is unavailable",
                    status=409,
                )
            context = dict(plan["capabilityRegistryContext"])
            claimed_context_hash = context.pop("contextHash", None)
            if sha256_text(canonical_json(context)) != claimed_context_hash:
                raise LocalWorkerError(
                    "capability_context_hash_mismatch",
                    "The Build capability context no longer matches its hash",
                    status=409,
                )
            if (
                context.get("registryHash") != self._capability_registry.registry_hash
                or context.get("hardwareProfileHash") != self._capability_registry.profile.get("profileHash")
            ):
                raise LocalWorkerError(
                    "stale_capability_registry",
                    "The capability registry or hardware profile changed after this Build plan was created",
                    status=409,
                )
        contract = self._validated_contract(str(plan.get("workerId") or ""))
        if (
            contract["contractHash"] != plan.get("contractHash")
            or contract["implementationHash"] != plan.get("implementationHash")
        ):
            raise LocalWorkerError(
                "worker_contract_changed",
                "The worker implementation or contract changed after planning",
                status=409,
            )
        plan_without_hash = dict(plan)
        plan_hash = plan_without_hash.pop("planHash", None)
        plan_without_hash.pop("approval", None)
        if sha256_text(canonical_json(plan_without_hash)) != plan_hash:
            raise LocalWorkerError(
                "plan_hash_mismatch",
                "The worker plan no longer matches its validated hash",
                status=409,
            )
        if worker_id in BUILDER_WORKER_IDS:
            return {"sources": sources, **sources[0]}
        return sources[0]

    def _run_worker(
        self,
        worker_id: str,
        source: dict[str, Any],
        plan: dict[str, Any],
    ) -> dict[str, Any]:
        if worker_id == "approved-text-reader":
            text = str(source["content"])
            return {
                "schemaVersion": "approved-text-reader-output-v1",
                "encoding": source["encoding"] or "UTF-8",
                "bytes": len(text.encode("utf-8")),
                "characters": len(text),
                "lines": len(text.splitlines()),
                "content": text,
                "sourceSha256": source["sha256"],
                "sourceModified": False,
                "networkUsed": False,
                "shellUsed": False,
            }
        if worker_id == "code-structure-inspector":
            text = str(source["selection"] or source["content"])
            filename = source["title"]
            if "." not in filename and source["suffix"]:
                filename += source["suffix"]
            inspection = inspect_code_text(text, filename)
            inspection["schemaVersion"] = "code-structure-inspection-v1"
            inspection["facts"] = {
                "bytes": inspection["bytes"],
                "characters": inspection["characters"],
                "lines": inspection["lines"],
                "importsOrDependencies": inspection["importsOrDependencies"],
                "functions": inspection["functions"],
                "classes": inspection["classes"],
                "markers": inspection["markers"],
            }
            inspection["heuristicFindings"] = {
                "probableType": inspection["probableType"],
                "basis": inspection["probableTypeBasis"],
                "repeatedLines": inspection["repeatedLines"],
            }
            inspection["sourceSha256"] = source["sha256"]
            return inspection
        if worker_id == "note-proposal-worker":
            selected = str(source["selection"] or "").strip()
            title = _bounded_title(
                plan.get("noteTitle"), f"Note from {source['title']}"
            )
            content = f"# {title}\n\n{selected}\n"
            return {
                "schemaVersion": "note-proposal-output-v1",
                "title": title,
                "content": content,
                "contentSha256": sha256_text(content),
                "sourceTitle": source["title"],
                "sourceSha256": source["sha256"],
                "sourcePreserved": True,
                "mutationPerformed": False,
                "approvalRequiredBeforeCreation": True,
                "networkUsed": False,
                "shellUsed": False,
            }
        if worker_id == "package-manifest-validator":
            return self._validate_package(source, plan)
        if worker_id == "local-ai-rewrite":
            if self._model_bay is None:
                raise LocalWorkerError("model_bay_unavailable", "The Local AI Model Bay is unavailable", status=503)
            try:
                inference = self._model_bay.infer_rewrite(source, plan)
            except ModelBayError as error:
                raise LocalWorkerError(error.code, str(error), status=error.status, details=error.details) from error
            return build_ai_builder_output(
                worker_id=worker_id,
                worker_version=str(plan["workerVersion"]),
                job_id=str(plan["jobId"]),
                plan_id=str(plan.get("planId") or plan["jobId"]),
                profile=str(plan["destinationProfile"]),
                owner_instruction=str(plan.get("ownerGoal") or ""),
                sources=list(source["sources"]),
                inference=inference,
            )
        if worker_id in BUILDER_WORKER_IDS:
            builder_data = dict(
                plan.get("moduleControls")
                or plan.get("buildControls")
                or plan.get("videoControls")
                or plan.get("productionControls")
                or plan.get("visualControls")
                or {}
            )
            if worker_id == "build-work-order-builder":
                builder_data["_capabilityRegistryContext"] = dict(
                    plan.get("capabilityRegistryContext") or {}
                )
            return build_builder_output(
                worker_id=worker_id,
                worker_version=str(plan["workerVersion"]),
                job_id=str(plan["jobId"]),
                plan_id=str(plan.get("planId") or plan["jobId"]),
                profile=str(plan["destinationProfile"]),
                goal=str(plan["ownerGoal"]),
                sources=list(source["sources"]),
                created_at=utc_now(),
                builder_data=builder_data,
            )
        raise LocalWorkerError(
            "worker_not_supported",
            "That worker is not in the fixed local allowlist",
            status=404,
        )

    def _validate_package(
        self, source: dict[str, Any], plan: dict[str, Any]
    ) -> dict[str, Any]:
        path = source["path"]
        if not isinstance(path, Path):
            raise LocalWorkerError(
                "package_source_required",
                "A registered package source is required",
            )
        expected_members = set(plan.get("expectedMembers") or [])
        expected_hashes = dict(plan.get("expectedHashes") or {})
        members: dict[str, str | None] = {}
        unsafe: list[str] = []
        duplicates: list[str] = []
        facts: dict[str, Any] = {}
        if path.suffix.lower() == ".zip":
            try:
                with zipfile.ZipFile(path, "r") as archive:
                    infos = archive.infolist()
                    if len(infos) > MAX_ARCHIVE_MEMBERS:
                        raise LocalWorkerError(
                            "package_member_limit_exceeded",
                            "The package exceeds the 500-member validation limit",
                        )
                    expanded = sum(info.file_size for info in infos)
                    if expanded > MAX_ARCHIVE_EXPANDED_BYTES:
                        raise LocalWorkerError(
                            "package_expanded_size_exceeded",
                            "The package exceeds the 64 MiB expanded-size limit",
                        )
                    seen: set[str] = set()
                    encrypted = 0
                    symlinks = 0
                    for info in infos:
                        raw_name = info.filename.replace("\\", "/")
                        try:
                            name = _safe_member(raw_name.rstrip("/"))
                        except LocalWorkerError:
                            unsafe.append(raw_name)
                            continue
                        if name in seen:
                            duplicates.append(name)
                        seen.add(name)
                        if info.flag_bits & 0x1:
                            encrypted += 1
                        mode = (info.external_attr >> 16) & 0xFFFF
                        if stat.S_ISLNK(mode):
                            symlinks += 1
                            unsafe.append(name)
                        if info.is_dir():
                            members[name] = None
                            continue
                        with archive.open(info, "r") as handle:
                            digest = hashlib.sha256()
                            read = 0
                            for chunk in iter(
                                lambda: handle.read(1024 * 1024), b""
                            ):
                                read += len(chunk)
                                if read > MAX_ARCHIVE_EXPANDED_BYTES:
                                    raise LocalWorkerError(
                                        "package_member_too_large",
                                        "A package member exceeded its read limit",
                                    )
                                digest.update(chunk)
                        members[name] = digest.hexdigest().upper()
                    facts = {
                        "format": "ZIP",
                        "memberCount": len(infos),
                        "expandedBytes": expanded,
                        "encryptedMembers": encrypted,
                        "symlinkMembers": symlinks,
                    }
            except zipfile.BadZipFile as exc:
                raise LocalWorkerError(
                    "package_invalid_zip",
                    "The selected package is not a valid ZIP archive",
                ) from exc
        else:
            raw = path.read_bytes()
            try:
                document = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise LocalWorkerError(
                    "manifest_json_invalid",
                    "The selected manifest is not valid UTF-8 JSON",
                ) from exc
            package_members = (
                document.get("packageMembers", {})
                if isinstance(document, dict)
                else {}
            )
            if not isinstance(package_members, dict):
                raise LocalWorkerError(
                    "manifest_members_invalid",
                    "The manifest packageMembers value must be an object",
                )
            if len(package_members) > MAX_ARCHIVE_MEMBERS:
                raise LocalWorkerError(
                    "package_member_limit_exceeded",
                    "The manifest exceeds the 500-member validation limit",
                )
            for raw_name, details in package_members.items():
                try:
                    name = _safe_member(raw_name)
                except LocalWorkerError:
                    unsafe.append(str(raw_name))
                    continue
                digest = (
                    str(details.get("sha256") or "").upper()
                    if isinstance(details, dict)
                    else ""
                )
                members[name] = digest if re.fullmatch(r"[A-F0-9]{64}", digest) else None
            facts = {
                "format": "JSON manifest",
                "memberCount": len(package_members),
                "topLevelKeys": sorted(document) if isinstance(document, dict) else [],
            }
        actual = set(members)
        missing = sorted(expected_members - actual)
        unexpected = sorted(actual - expected_members) if expected_members else []
        hash_checks = {
            member: {
                "expected": digest,
                "current": members.get(member),
                "exact": members.get(member) == digest,
            }
            for member, digest in expected_hashes.items()
        }
        hash_mismatches = sorted(
            member
            for member, details in hash_checks.items()
            if not details["exact"]
        )
        valid = (
            not unsafe
            and not duplicates
            and not missing
            and not unexpected
            and not hash_mismatches
        )
        return {
            "schemaVersion": "package-manifest-validation-v1",
            "sourceTitle": source["title"],
            "containerSha256": source["sha256"],
            "facts": facts,
            "expectedMemberCount": len(expected_members),
            "members": [
                {"path": name, "sha256": digest}
                for name, digest in sorted(members.items())
            ],
            "missingMembers": missing,
            "unexpectedMembers": unexpected,
            "unsafeMembers": sorted(set(unsafe)),
            "duplicateMembers": sorted(set(duplicates)),
            "hashChecks": hash_checks,
            "hashMismatches": hash_mismatches,
            "validationPassed": valid,
            "evidenceLimits": (
                "Unexpected entries are reported only when an expected member list was supplied. "
                "JSON manifests validate declared hashes but do not imply the represented files were available."
            ),
            "installed": False,
            "executed": False,
            "imported": False,
            "activated": False,
            "networkUsed": False,
            "shellUsed": False,
        }

    def _validate_output(
        self, worker_id: str, output: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(output, dict):
            raise LocalWorkerError(
                "worker_output_invalid",
                "The worker output is not a structured object",
                status=500,
            )
        expected_schema = {
            "approved-text-reader": "approved-text-reader-output-v1",
            "code-structure-inspector": "code-structure-inspection-v1",
            "note-proposal-worker": "note-proposal-output-v1",
            "package-manifest-validator": "package-manifest-validation-v1",
            "handoff-proposal-builder": BUILDER_SCHEMA_VERSION,
            "prompt-proposal-builder": BUILDER_SCHEMA_VERSION,
            "draft-workshop": BUILDER_SCHEMA_VERSION,
            "evidence-compare": BUILDER_SCHEMA_VERSION,
            "visual-brief-builder": BUILDER_SCHEMA_VERSION,
            "song-production-brief-builder": BUILDER_SCHEMA_VERSION,
            "video-production-brief-builder": BUILDER_SCHEMA_VERSION,
            "build-work-order-builder": BUILDER_SCHEMA_VERSION,
            "module-proposal-builder": BUILDER_SCHEMA_VERSION,
            "local-ai-rewrite": BUILDER_SCHEMA_VERSION,
        }[worker_id]
        if output.get("schemaVersion") != expected_schema:
            raise LocalWorkerError(
                "worker_output_schema_invalid",
                "The worker output failed its declared schema",
                status=500,
            )
        if output.get("networkUsed") is not False or output.get("shellUsed") is not False:
            raise LocalWorkerError(
                "worker_output_policy_invalid",
                "The worker output did not prove the required local policy",
                status=500,
            )
        if worker_id in BUILDER_WORKER_IDS:
            try:
                validate_builder_output(worker_id, output)
            except (KeyError, TypeError, ValueError) as exc:
                raise LocalWorkerError(
                    "builder_output_invalid",
                    "The builder output failed its versioned section, metadata, or hash contract",
                    status=500,
                ) from exc
        encoded = canonical_json(output).encode("utf-8")
        limit = int(
            self._validated_contract(worker_id)["limits"]["outputBytes"]
        )
        if len(encoded) > limit:
            raise LocalWorkerError(
                "worker_output_too_large",
                "The worker output exceeded its contract limit",
                status=500,
            )
        return {
            "valid": True,
            "schema": expected_schema,
            "bytes": len(encoded),
            "sha256": sha256_bytes(encoded),
            "validatedAt": utc_now(),
            "claim": "Validated output is evidence, not owner approval.",
        }

    def execute(self, job_id: str, *, actor: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._job_row(connection, job_id)
            if row["status"] == "awaiting_result_approval":
                value = self._serialize_job(connection, row)
                value["idempotent"] = True
                connection.commit()
                return value
            if row["status"] == "running":
                raise LocalWorkerError(
                    "duplicate_execution",
                    "This job is already running",
                    status=409,
                )
            if row["status"] != "plan_approved":
                raise LocalWorkerError(
                    "job_not_executable",
                    "Only an explicitly approved current plan can run",
                    status=409,
                )
            plan = json_value(row["payload"], {})
            expires_at = datetime.fromisoformat(str(plan["expiresAt"]))
            if datetime.now(timezone.utc) > expires_at:
                now = utc_now()
                connection.execute(
                    "UPDATE jobs SET status='abandoned',updated_at=? WHERE id=?",
                    (now, row["id"]),
                )
                self._receipt(
                    connection,
                    row["project_id"],
                    "local_worker.plan.abandon",
                    actor,
                    {"jobId": row["id"], "expiresAt": plan["expiresAt"]},
                )
                connection.commit()
                raise LocalWorkerError(
                    "plan_abandoned",
                    "This plan expired; create a new current plan",
                    status=409,
                )
            try:
                source = self._verify_current_source(connection, plan)
            except LocalWorkerError as error:
                if error.code in {
                    "stale_plan",
                    "source_hash_mismatch",
                    "source_missing",
                    "source_version_missing",
                    "selection_not_in_source",
                }:
                    now = utc_now()
                    connection.execute(
                        "UPDATE jobs SET status='stale',updated_at=? WHERE id=?",
                        (now, row["id"]),
                    )
                    self._receipt(
                        connection,
                        row["project_id"],
                        "local_worker.plan.stale",
                        actor,
                        {
                            "jobId": row["id"],
                            "reason": error.code,
                            **error.details,
                        },
                    )
                    connection.commit()
                    raise LocalWorkerError(
                        "stale_plan",
                        "The approved plan is stale because its source is no longer current",
                        status=409,
                        details={"reason": error.code, **error.details},
                    ) from error
                raise
            running_at = utc_now()
            connection.execute(
                "UPDATE jobs SET status='running',updated_at=? WHERE id=?",
                (running_at, row["id"]),
            )
            connection.commit()

            started = self._clock()
            try:
                output = self._run_worker(plan["workerId"], source, plan)
                elapsed = self._clock() - started
                runtime_limit = float(
                    self._validated_contract(plan["workerId"])["limits"][
                        "runtimeSeconds"
                    ]
                )
                if elapsed > runtime_limit:
                    raise LocalWorkerError(
                        "worker_timeout",
                        "The worker exceeded its bounded runtime",
                        status=408,
                    )
                validation = self._validate_output(plan["workerId"], output)
            except Exception as error:
                failure = (
                    error
                    if isinstance(error, LocalWorkerError)
                    else LocalWorkerError(
                        "worker_runtime_failed",
                        "The worker failed safely",
                        status=500,
                    )
                )
                failed = self._connect()
                try:
                    failed.execute("BEGIN IMMEDIATE")
                    current = self._job_row(failed, row["id"])
                    if current["status"] == "running":
                        now = utc_now()
                        failed.execute(
                            "UPDATE jobs SET status='failed',result=?,updated_at=? WHERE id=?",
                            (
                                canonical_json(
                                    {
                                        "failure": {
                                            "code": failure.code,
                                            "message": str(failure),
                                        },
                                        "accepted": False,
                                    }
                                ),
                                now,
                                row["id"],
                            ),
                        )
                        receipt_id = self._receipt(
                            failed,
                            row["project_id"],
                            "local_worker.execute.fail",
                            actor,
                            {"jobId": row["id"], "code": failure.code},
                        )
                        self._evidence(
                            failed,
                            row["id"],
                            "execution-failure",
                            {"code": failure.code, "receiptId": receipt_id},
                        )
                    failed.commit()
                except Exception:
                    failed.rollback()
                    raise
                finally:
                    failed.close()
                raise failure

            completed = self._connect()
            try:
                completed.execute("BEGIN IMMEDIATE")
                current = self._job_row(completed, row["id"])
                if current["status"] != "running":
                    raise LocalWorkerError(
                        "job_state_changed",
                        "The job state changed during execution",
                        status=409,
                    )
                now = utc_now()
                result = {
                    "schemaVersion": "local-worker-result-v1",
                    "output": output,
                    "validation": validation,
                    "accepted": False,
                    "decision": None,
                    "attachmentStatus": "unattached",
                    "activationStatus": "inactive",
                    "modulePromotionStatus": "not-requested",
                    "completedAt": now,
                }
                completed.execute(
                    "UPDATE jobs SET status='awaiting_result_approval',result=?,updated_at=? WHERE id=?",
                    (canonical_json(result), now, row["id"]),
                )
                receipt_id = self._receipt(
                    completed,
                    row["project_id"],
                    "local_worker.execute.complete",
                    actor,
                    {
                        "jobId": row["id"],
                        "workerId": plan["workerId"],
                        "sourceSha256": source["sha256"],
                        "outputSha256": validation["sha256"],
                        "outputValidated": True,
                        "accepted": False,
                        "networkUsed": False,
                        "shellUsed": False,
                        "inference": output.get("metadata", {}).get("inference") if plan["workerId"] == "local-ai-rewrite" else None,
                    },
                )
                if plan["workerId"] == "local-ai-rewrite":
                    result["inferenceReceiptId"] = receipt_id
                    completed.execute(
                        "UPDATE jobs SET result=?,updated_at=? WHERE id=?",
                        (canonical_json(result), now, row["id"]),
                    )
                self._evidence(
                    completed,
                    row["id"],
                    "validated-output",
                    {
                        "outputSha256": validation["sha256"],
                        "validationSchema": validation["schema"],
                        "receiptId": receipt_id,
                    },
                )
                completed.commit()
                return self._serialize_job(
                    completed, self._job_row(completed, row["id"])
                )
            except Exception:
                completed.rollback()
                raise
            finally:
                completed.close()
        finally:
            connection.close()

    def decide_result(
        self, job_id: str, decision: Any, note: Any, *, actor: str
    ) -> dict[str, Any]:
        choice = str(decision or "").strip().lower()
        if choice not in {"approve", "reject"}:
            raise LocalWorkerError(
                "result_decision_invalid", "Choose approve or reject"
            )
        approval_note = _approval_note(note) if choice == "approve" else str(note or "").strip()[:APPROVAL_NOTE_MAX]
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._job_row(connection, job_id)
            if row["status"] != "awaiting_result_approval":
                raise LocalWorkerError(
                    "result_already_decided",
                    "This result is no longer awaiting a decision",
                    status=409,
                )
            plan = json_value(row["payload"], {})
            result = json_value(row["result"], {})
            if not result.get("validation", {}).get("valid"):
                raise LocalWorkerError(
                    "result_not_validated",
                    "Only validated worker output can be approved",
                    status=409,
                )
            decided_at = utc_now()
            acceptance: dict[str, Any] | None = None
            if choice == "approve" and plan["workerId"] == "note-proposal-worker":
                source = self._verify_current_source(connection, plan)
                output = result["output"]
                note_id = str(uuid.uuid4())
                note_payload = {
                    "schemaVersion": "local-worker-note-v1",
                    "body": output["content"],
                    "sourceArtifactId": source["artifactId"],
                    "sourceTitle": source["title"],
                    "sourceSha256": source["sha256"],
                    "jobId": row["id"],
                    "origin": "note-proposal-worker",
                }
                connection.execute(
                    """INSERT INTO artifacts(
                         id,project_id,kind,title,path,payload,authority_state,sha256,created_at,updated_at
                       ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                    (
                        note_id,
                        row["project_id"],
                        "note",
                        output["title"],
                        "",
                        canonical_json(note_payload),
                        "DRAFT",
                        output["contentSha256"],
                        decided_at,
                        decided_at,
                    ),
                )
                connection.execute(
                    "INSERT INTO artifact_search(id,project_id,title,kind,content) VALUES(?,?,?,?,?)",
                    (
                        note_id,
                        row["project_id"],
                        output["title"],
                        "note",
                        f"{output['title']} note {output['content']}",
                    ),
                )
                note_receipt = self._receipt(
                    connection,
                    row["project_id"],
                    "local_worker.note.create",
                    actor,
                    {
                        "jobId": row["id"],
                        "noteArtifactId": note_id,
                        "noteSha256": output["contentSha256"],
                        "sourceArtifactId": source["artifactId"],
                        "sourceSha256": source["sha256"],
                        "sourcePreserved": True,
                    },
                )
                acceptance = {
                    "noteArtifactId": note_id,
                    "noteTitle": output["title"],
                    "noteSha256": output["contentSha256"],
                    "createdAt": decided_at,
                    "rollbackAvailable": True,
                    "receiptId": note_receipt,
                }
            if plan["workerId"] in BUILDER_WORKER_IDS:
                if choice == "approve":
                    self._verify_current_source(connection, plan)
                output = result["output"]
                output["metadata"]["approvalState"] = "approved" if choice == "approve" else "rejected"
                _rebind_builder_output(output)
                validation = self._validate_output(plan["workerId"], output)
                result["validation"] = validation
            result["accepted"] = choice == "approve"
            result["decision"] = {
                "choice": choice,
                "note": approval_note,
                "actor": actor[:100] or "local-owner",
                "decidedAt": decided_at,
            }
            result["acceptance"] = acceptance
            result["attachmentStatus"] = "unattached"
            result["activationStatus"] = "inactive"
            result["modulePromotionStatus"] = "not-requested"
            status = "result_approved" if choice == "approve" else "result_rejected"
            connection.execute(
                "UPDATE jobs SET status=?,result=?,updated_at=? WHERE id=?",
                (status, canonical_json(result), decided_at, row["id"]),
            )
            receipt_id = self._receipt(
                connection,
                row["project_id"],
                f"local_worker.result.{choice}",
                actor,
                {
                    "jobId": row["id"],
                    "workerId": plan["workerId"],
                    "outputSha256": result["validation"]["sha256"],
                    "builderType": result.get("output", {}).get("metadata", {}).get("builderType"),
                    "destinationProfile": plan.get("destinationProfile"),
                    "sourceHashes": [value.get("sha256") for value in plan.get("sources", [])],
                    "decision": choice,
                    "note": approval_note,
                    "attachmentCreated": False,
                    "activationOccurred": False,
                    "modulePromotionOccurred": False,
                },
            )
            self._evidence(
                connection,
                row["id"],
                "result-decision",
                {
                    "decision": choice,
                    "outputSha256": result["validation"]["sha256"],
                    "receiptId": receipt_id,
                    "noteArtifactId": (
                        acceptance.get("noteArtifactId") if acceptance else None
                    ),
                },
            )
            connection.commit()
            return self._serialize_job(
                connection, self._job_row(connection, row["id"])
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def save_builder_draft(self, job_id: str, *, confirmed: Any, actor: str) -> dict[str, Any]:
        if confirmed is not True:
            raise LocalWorkerError("save_confirmation_required", "Saving an approved draft requires explicit confirmation")
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._job_row(connection, job_id)
            plan = json_value(row["payload"], {})
            result = json_value(row["result"], {})
            if plan.get("workerId") not in BUILDER_WORKER_IDS:
                raise LocalWorkerError("builder_job_required", "Only a builder result can be saved", status=409)
            if result.get("savedDraft"):
                raise LocalWorkerError("duplicate_save", "This approved result already has a saved draft", status=409)
            if row["status"] != "result_approved" or result.get("accepted") is not True:
                raise LocalWorkerError("save_requires_approval", "Approve the validated proposal before saving", status=409)
            self._verify_current_source(connection, plan)
            output = result["output"]
            metadata = output["metadata"]
            artifact_id = str(uuid.uuid4())
            now = utc_now()
            kind = {
                "handoff": "handoff-draft",
                "prompt": "prompt-draft",
                "writing-draft": "writing-draft",
                "research-comparison": "research-comparison-draft",
                "visual-brief": "visual-brief-draft",
                "song-production-brief": "song-production-brief-draft",
                "video-production-brief": "video-production-brief-draft",
                "build-work-order": "build-work-order-draft",
                "module-proposal": "module-proposal-draft",
                "local-ai-writing-proposal": "ai-writing-proposal-draft",
            }[metadata["builderType"]]
            owner_label = str(plan.get("ownerGoal") or "Prepared writing task")[:100]
            title = _bounded_title(None, f"{plan['destinationProfile']} — {owner_label}")
            draft_payload = {
                "schemaVersion": "builder-draft-v1", "builderOutput": output,
                "jobId": row["id"], "planId": plan.get("planId") or row["id"],
                "workerId": plan["workerId"], "workerVersion": plan["workerVersion"],
                "destinationProfile": plan["destinationProfile"],
                "sourceIds": metadata["sourceIds"], "sourceHashes": metadata["sourceHashes"],
                "approvalReceipt": result.get("decision"), "inactive": True,
                "attached": False, "executed": False, "published": False, "promoted": False,
                "writingOperation": metadata.get("writingOperation"),
                "ownerInstructions": metadata.get("ownerInstructions"),
                "comparisonFocus": metadata.get("comparisonFocus"),
                "visualPurpose": metadata.get("visualPurpose"),
                "visualControls": metadata.get("visualControls"),
                "sourcePriority": metadata.get("sourcePriority"),
                "ownerNotesHash": metadata.get("ownerNotesHash"),
                "songPurpose": metadata.get("songPurpose"),
                "productionControls": metadata.get("productionControls"),
                "musicNotesIdentity": metadata.get("musicNotesIdentity"),
                "musicLyricsIdentity": metadata.get("musicLyricsIdentity"),
                "videoPurpose": metadata.get("videoPurpose"),
                "videoControls": metadata.get("videoControls"),
                "videoNotesIdentity": metadata.get("videoNotesIdentity"),
                "workOrderType": metadata.get("workOrderType"),
                "buildControls": metadata.get("buildControls"),
                "buildInputIdentity": metadata.get("buildInputIdentity"),
                "moduleProposalType": metadata.get("moduleProposalType"),
                "moduleControls": metadata.get("moduleControls"),
                "moduleInputIdentity": metadata.get("moduleInputIdentity"),
                "inference": metadata.get("inference"),
                "inferenceReceiptId": result.get("inferenceReceiptId"),
                "exportHistory": [],
            }
            connection.execute(
                "INSERT INTO artifacts(id,project_id,kind,title,path,payload,authority_state,sha256,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (artifact_id, row["project_id"], kind, title, "", canonical_json(draft_payload), "DRAFT", output["outputHash"], now, now),
            )
            connection.execute(
                "INSERT INTO artifact_search(id,project_id,title,kind,content) VALUES(?,?,?,?,?)",
                (artifact_id, row["project_id"], title, kind, f"{title} {kind} {output['text']}"),
            )
            for source_id in metadata["sourceIds"]:
                if str(source_id).startswith(("rough-text:", "visual-notes:", "music-notes:", "music-lyrics:", "music-studio:", "video-notes:", "build-input:", "module-input:")):
                    continue
                connection.execute(
                    "INSERT INTO artifact_relationships VALUES(?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), source_id, artifact_id, row["project_id"], "builder-source", row["id"], "active", now, now),
                )
            result["savedDraft"] = {"artifactId": artifact_id, "kind": kind, "title": title, "sha256": output["outputHash"], "savedAt": now, "rollbackAvailable": True}
            result["output"]["metadata"]["savedArtifactId"] = artifact_id
            _rebind_builder_output(result["output"])
            result["savedDraft"]["sha256"] = result["output"]["outputHash"]
            connection.execute("UPDATE artifacts SET sha256=?,payload=? WHERE id=?", (result["output"]["outputHash"], canonical_json({**draft_payload, "builderOutput": result["output"]}), artifact_id))
            connection.execute("UPDATE jobs SET status='draft_saved',result=?,updated_at=? WHERE id=?", (canonical_json(result), now, row["id"]))
            receipt_id = self._receipt(connection, row["project_id"], "builder.draft.saved", actor, {
                "jobId": row["id"], "planId": plan.get("planId"), "workerId": plan["workerId"],
                "builderType": metadata["builderType"], "destinationProfile": plan["destinationProfile"],
                "sourceHashes": metadata["sourceHashes"], "draftArtifactId": artifact_id,
                "draftSha256": result["output"]["outputHash"], "inactive": True,
            })
            self._evidence(connection, row["id"], "builder-draft", {"draftArtifactId": artifact_id, "sha256": result["output"]["outputHash"], "receiptId": receipt_id})
            connection.commit()
            return self._serialize_job(connection, self._job_row(connection, row["id"]))
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def export_builder_result(self, job_id: str, export_format: Any, *, include_provenance: Any, confirmed: Any, actor: str) -> dict[str, Any]:
        if confirmed is not True:
            raise LocalWorkerError("export_confirmation_required", "Export requires an explicit owner action")
        fmt = str(export_format or "").strip().lower()
        connection = self._connect()
        path: Path | None = None
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._job_row(connection, job_id)
            plan = json_value(row["payload"], {})
            result = json_value(row["result"], {})
            allowed_formats = (
                {"txt", "md", "json"}
                if plan.get("workerId") in {"evidence-compare", "visual-brief-builder", "song-production-brief-builder", "video-production-brief-builder", "build-work-order-builder", "module-proposal-builder", "local-ai-rewrite"}
                else ({"txt", "md"} if plan.get("workerId") == "draft-workshop" else {"txt", "json"})
            )
            if fmt not in allowed_formats:
                raise LocalWorkerError("export_format_invalid", "Choose an export format supported by this fixed builder")
            if plan.get("workerId") not in BUILDER_WORKER_IDS or row["status"] not in {"result_approved", "draft_saved"} or result.get("accepted") is not True:
                raise LocalWorkerError("export_requires_approval", "Only an explicitly approved builder result can be exported", status=409)
            self._verify_current_source(connection, plan)
            output = result["output"]
            export_root = (self.projects_root.parent / "exports" / "builders").resolve(strict=False)
            export_root.mkdir(parents=True, exist_ok=True)
            stem = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{output['metadata']['builderType']}-{plan['destinationProfile']}").strip(".-")[:100] or "builder-export"
            path = export_root / f"{stem}-{row['id'][:8]}-{uuid.uuid4().hex[:8]}.{fmt}"
            if not _is_within(path.resolve(strict=False), export_root):
                raise LocalWorkerError("export_path_invalid", "Export path escaped the approved Workshop export location")
            if fmt in {"txt", "md"}:
                body = output["text"]
                if include_provenance is True:
                    body += "\n\n---\nProvenance\n" + canonical_json(output["metadata"])
            else:
                body = canonical_json(output if include_provenance is not False else {"schemaVersion": BUILDER_SCHEMA_VERSION, "text": output["text"], "outputHash": output["outputHash"]})
            raw = body.encode("utf-8")
            temp = path.with_suffix(path.suffix + ".tmp")
            temp.write_bytes(raw)
            os.replace(temp, path)
            record = {"format": fmt, "path": str(path), "sha256": sha256_bytes(raw), "bytes": len(raw), "exportedAt": utc_now(), "networkUsed": False, "executed": False, "providerSubmitted": False}
            result.setdefault("exports", []).append(record)
            draft_id = (result.get("savedDraft") or {}).get("artifactId")
            if draft_id:
                draft_row = connection.execute("SELECT payload FROM artifacts WHERE id=?", (draft_id,)).fetchone()
                if draft_row is not None:
                    draft_payload = json_value(draft_row["payload"], {})
                    draft_payload.setdefault("exportHistory", []).append(record)
                    connection.execute("UPDATE artifacts SET payload=?,updated_at=? WHERE id=?", (canonical_json(draft_payload), record["exportedAt"], draft_id))
            connection.execute("UPDATE jobs SET result=?,updated_at=? WHERE id=?", (canonical_json(result), record["exportedAt"], row["id"]))
            receipt_id = self._receipt(connection, row["project_id"], "builder.export.completed", actor, {
                "jobId": row["id"], "planId": plan.get("planId"), "workerId": plan["workerId"],
                "builderType": output["metadata"]["builderType"], "destinationProfile": plan["destinationProfile"],
                "sourceHashes": output["metadata"]["sourceHashes"], "format": fmt,
                "path": str(path), "sha256": record["sha256"], "networkUsed": False, "executed": False,
            })
            self._evidence(connection, row["id"], "builder-export", {"path": str(path), "sha256": record["sha256"], "receiptId": receipt_id})
            connection.commit()
            return self._serialize_job(connection, self._job_row(connection, row["id"]))
        except Exception:
            connection.rollback()
            if path is not None and path.exists():
                path.unlink()
            raise
        finally:
            connection.close()

    def rollback(self, job_id: str, *, confirmed: Any, actor: str) -> dict[str, Any]:
        if confirmed is not True:
            raise LocalWorkerError(
                "rollback_confirmation_required",
                "Rollback must be explicitly confirmed",
            )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._job_row(connection, job_id)
            plan = json_value(row["payload"], {})
            result = json_value(row["result"], {})
            acceptance = result.get("acceptance") or {}
            note_id = acceptance.get("noteArtifactId")
            if plan.get("workerId") in BUILDER_WORKER_IDS:
                draft = result.get("savedDraft") or {}
                draft_id = draft.get("artifactId")
                if row["status"] != "draft_saved" or not draft_id:
                    raise LocalWorkerError("rollback_not_available", "This builder job has no saved draft to roll back", status=409)
                artifact = connection.execute("SELECT * FROM artifacts WHERE id=?", (draft_id,)).fetchone()
                if artifact is None or artifact["kind"] not in {"handoff-draft", "prompt-draft", "writing-draft", "research-comparison-draft", "visual-brief-draft", "song-production-brief-draft", "video-production-brief-draft", "build-work-order-draft", "module-proposal-draft", "ai-writing-proposal-draft"} or json_value(artifact["payload"], {}).get("jobId") != row["id"] or str(artifact["sha256"]).upper() != str(draft.get("sha256") or "").upper():
                    raise LocalWorkerError("rollback_draft_changed", "The saved draft changed or is unrelated, so rollback stopped safely", status=409)
                connection.execute("DELETE FROM artifact_relationships WHERE target_artifact_id=? AND lifecycle_id=?", (draft_id, row["id"]))
                connection.execute("DELETE FROM artifact_search WHERE id=?", (draft_id,))
                connection.execute("DELETE FROM artifacts WHERE id=?", (draft_id,))
                rolled_at = utc_now()
                result["savedDraft"]["rollbackAvailable"] = False
                result["rollback"] = {"rolledBackAt": rolled_at, "draftArtifactId": draft_id, "draftSha256": artifact["sha256"], "sourcesPreserved": True, "unrelatedContentRemoved": False}
                result["output"]["metadata"]["rollbackState"] = "rolled-back"
                _rebind_builder_output(result["output"])
                connection.execute("UPDATE jobs SET status='rolled_back',result=?,updated_at=? WHERE id=?", (canonical_json(result), rolled_at, row["id"]))
                receipt_id = self._receipt(connection, row["project_id"], "builder.draft.rolled_back", actor, {"jobId": row["id"], "planId": plan.get("planId"), "workerId": plan["workerId"], "builderType": result["output"]["metadata"]["builderType"], "destinationProfile": plan["destinationProfile"], "sourceHashes": result["output"]["metadata"]["sourceHashes"], "draftArtifactId": draft_id, "sourcesPreserved": True})
                self._evidence(connection, row["id"], "builder-draft-rollback", {"draftArtifactId": draft_id, "sha256": artifact["sha256"], "receiptId": receipt_id})
                connection.commit()
                return self._serialize_job(connection, self._job_row(connection, row["id"]))
            if (
                row["status"] != "result_approved"
                or plan.get("workerId") != "note-proposal-worker"
                or not note_id
            ):
                raise LocalWorkerError(
                    "rollback_not_available",
                    "This job has no accepted note mutation to roll back",
                    status=409,
                )
            note = connection.execute(
                "SELECT * FROM artifacts WHERE id=?", (note_id,)
            ).fetchone()
            if note is None:
                raise LocalWorkerError(
                    "rollback_note_missing",
                    "The created note is unavailable, so rollback stopped safely",
                    status=409,
                )
            payload = json_value(note["payload"], {})
            if (
                note["kind"] != "note"
                or payload.get("schemaVersion") != "local-worker-note-v1"
                or payload.get("jobId") != row["id"]
                or str(note["sha256"]).upper()
                != str(acceptance.get("noteSha256") or "").upper()
            ):
                raise LocalWorkerError(
                    "rollback_note_changed",
                    "The created note changed, so automatic rollback was blocked",
                    status=409,
                )
            connection.execute(
                "DELETE FROM artifact_search WHERE id=?", (note_id,)
            )
            connection.execute("DELETE FROM artifacts WHERE id=?", (note_id,))
            rolled_at = utc_now()
            result["accepted"] = False
            result["rollback"] = {
                "rolledBackAt": rolled_at,
                "noteArtifactId": note_id,
                "noteSha256": note["sha256"],
                "sourcePreserved": True,
                "unrelatedWritingRemoved": False,
            }
            result["acceptance"]["rollbackAvailable"] = False
            connection.execute(
                "UPDATE jobs SET status='rolled_back',result=?,updated_at=? WHERE id=?",
                (canonical_json(result), rolled_at, row["id"]),
            )
            receipt_id = self._receipt(
                connection,
                row["project_id"],
                "local_worker.note.rollback",
                actor,
                {
                    "jobId": row["id"],
                    "noteArtifactId": note_id,
                    "noteSha256": note["sha256"],
                    "sourcePreserved": True,
                    "unrelatedWritingRemoved": False,
                },
            )
            self._evidence(
                connection,
                row["id"],
                "rollback",
                {
                    "noteArtifactId": note_id,
                    "noteSha256": note["sha256"],
                    "receiptId": receipt_id,
                },
            )
            connection.commit()
            return self._serialize_job(
                connection, self._job_row(connection, row["id"])
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def cancel(self, job_id: str, *, actor: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._job_row(connection, job_id)
            if row["status"] not in {"planned", "plan_approved", "interrupted"}:
                raise LocalWorkerError(
                    "job_not_cancellable",
                    "This job cannot be cancelled in its current state",
                    status=409,
                )
            now = utc_now()
            connection.execute(
                "UPDATE jobs SET status='cancelled',updated_at=? WHERE id=?",
                (now, row["id"]),
            )
            receipt_id = self._receipt(
                connection,
                row["project_id"],
                "local_worker.job.cancel",
                actor,
                {"jobId": row["id"], "previousStatus": row["status"]},
            )
            self._evidence(
                connection,
                row["id"],
                "cancellation",
                {"previousStatus": row["status"], "receiptId": receipt_id},
            )
            connection.commit()
            return self._serialize_job(
                connection, self._job_row(connection, row["id"])
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def recover(self, job_id: str, *, actor: str) -> dict[str, Any]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._job_row(connection, job_id)
            if row["status"] == "plan_approved":
                value = self._serialize_job(connection, row)
                value["idempotent"] = True
                connection.commit()
                return value
            if row["status"] != "interrupted":
                raise LocalWorkerError(
                    "job_not_recoverable",
                    "Only an interrupted unaccepted job can be recovered",
                    status=409,
                )
            plan = json_value(row["payload"], {})
            self._verify_current_source(connection, plan)
            now = utc_now()
            connection.execute(
                "UPDATE jobs SET status='plan_approved',result='{}',updated_at=? WHERE id=?",
                (now, row["id"]),
            )
            receipt_id = self._receipt(
                connection,
                row["project_id"],
                "local_worker.job.recover",
                actor,
                {
                    "jobId": row["id"],
                    "planHash": plan.get("planHash"),
                    "sourceSha256": plan.get("source", {}).get("sha256"),
                    "acceptedOutputRecovered": False,
                },
            )
            self._evidence(
                connection,
                row["id"],
                "recovery",
                {"status": "plan_approved", "receiptId": receipt_id},
            )
            connection.commit()
            return self._serialize_job(
                connection, self._job_row(connection, row["id"])
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def recover_interrupted_on_startup(self) -> int:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT * FROM jobs WHERE operation LIKE 'local-worker:%' AND status='running'"
            ).fetchall()
            now = utc_now()
            for row in rows:
                connection.execute(
                    "UPDATE jobs SET status='interrupted',result=?,updated_at=? WHERE id=?",
                    (
                        canonical_json(
                            {
                                "interruption": {
                                    "detectedAt": now,
                                    "accepted": False,
                                    "attachmentStatus": "unattached",
                                    "activationStatus": "inactive",
                                }
                            }
                        ),
                        now,
                        row["id"],
                    ),
                )
                receipt_id = self._receipt(
                    connection,
                    row["project_id"],
                    "local_worker.job.interrupted",
                    "local-companion-recovery",
                    {
                        "jobId": row["id"],
                        "previousStatus": "running",
                        "accepted": False,
                        "attachmentCreated": False,
                        "activationOccurred": False,
                    },
                )
                self._evidence(
                    connection,
                    row["id"],
                    "interruption",
                    {"receiptId": receipt_id, "accepted": False},
                )
            connection.commit()
            return len(rows)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def delete_history(
        self, job_id: str, *, confirmed: Any, actor: str
    ) -> dict[str, Any]:
        if confirmed is not True:
            raise LocalWorkerError(
                "history_delete_confirmation_required",
                "History cleanup must be explicitly confirmed",
            )
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = self._job_row(connection, job_id)
            if row["status"] not in SAFE_DELETE_STATES:
                raise LocalWorkerError(
                    "history_delete_blocked",
                    "Only terminal job history can be removed",
                    status=409,
                )
            plan = json_value(row["payload"], {})
            result = json_value(row["result"], {})
            note_id = (result.get("acceptance") or {}).get("noteArtifactId")
            if note_id and row["status"] != "rolled_back":
                raise LocalWorkerError(
                    "history_delete_mutation_active",
                    "Roll back the created note before removing this job history",
                    status=409,
                )
            evidence_count = connection.execute(
                "SELECT COUNT(*) FROM worker_job_evidence WHERE job_id=?",
                (row["id"],),
            ).fetchone()[0]
            self._receipt(
                connection,
                row["project_id"],
                "local_worker.job.history.delete",
                actor,
                {
                    "jobId": row["id"],
                    "workerId": plan.get("workerId"),
                    "terminalStatus": row["status"],
                    "evidenceRowsRemoved": evidence_count,
                    "receiptsPreserved": True,
                },
            )
            connection.execute(
                "DELETE FROM worker_job_evidence WHERE job_id=?", (row["id"],)
            )
            connection.execute("DELETE FROM jobs WHERE id=?", (row["id"],))
            connection.commit()
            return {
                "ok": True,
                "jobHistoryRemoved": True,
                "receiptsPreserved": True,
            }
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
