from __future__ import annotations

from importlib import import_module
from pathlib import Path
import re
from types import ModuleType
from typing import Any

from .capabilities import (
    CapabilityFailed,
    CapabilityRegistry,
    canonical_resource_scope,
)


CAPABILITY_NAME = "workshop.artifact.read"
WORKSHOP_PRIMITIVE = "workshop.companion.server.artifact_inspection_options"
RESULT_SCHEMA = "twis-workshop-artifact-read-v0.1"
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,127}$")
SHA256_PATTERN = re.compile(r"^[A-F0-9]{64}$")


def project_scope(project_id: str) -> str:
    if not isinstance(project_id, str) or not IDENTIFIER_PATTERN.fullmatch(project_id):
        raise ValueError("project_id_invalid")
    return canonical_resource_scope(f"project:{project_id}")


def _project_id(scope: str) -> str:
    canonical = canonical_resource_scope(scope)
    scheme, identifier = canonical.split(":", 1)
    if scheme != "project" or not IDENTIFIER_PATTERN.fullmatch(identifier):
        raise CapabilityFailed("project_scope_invalid", target=canonical)
    return identifier


def _workshop_server(scope: str) -> ModuleType:
    try:
        return import_module("workshop.companion.server")
    except Exception as exc:
        raise CapabilityFailed(
            f"workshop_primitive_unavailable: {type(exc).__name__}",
            target=scope,
        ) from exc


def _failure(code: str, scope: str) -> CapabilityFailed:
    return CapabilityFailed(code, target=scope)


class WorkshopArtifactReadAdapter:
    """Expose one authenticated Workshop metadata read through kernel authority."""

    def read(self, project_scope: str, artifact_id: str) -> dict[str, Any]:
        scope = canonical_resource_scope(project_scope)
        project_id = _project_id(scope)
        if not isinstance(artifact_id, str) or not IDENTIFIER_PATTERN.fullmatch(artifact_id):
            raise _failure("artifact_id_invalid", scope)

        server = _workshop_server(scope)
        try:
            options = server.artifact_inspection_options(project_id)
        except Exception as exc:
            raise _failure(
                f"workshop_primitive_failed: {type(exc).__name__}",
                scope,
            ) from exc

        if not isinstance(options, list):
            raise _failure("workshop_primitive_contract_invalid", scope)

        option = next(
            (
                item
                for item in options
                if isinstance(item, dict) and item.get("artifactId") == artifact_id
            ),
            None,
        )
        if option is None:
            raise _failure("artifact_not_found", scope)
        if option.get("eligible") is not True:
            raise _failure("artifact_ineligible", scope)
        if option.get("projectId") != project_id:
            raise _failure("artifact_project_mismatch", scope)

        try:
            projects_root = Path(server.PROJECTS).resolve(strict=False)
            source_path = Path(str(option["sourcePath"])).resolve(strict=False)
            relative_path = source_path.relative_to(projects_root)
        except (KeyError, OSError, RuntimeError, ValueError) as exc:
            raise _failure("artifact_path_invalid", scope) from exc
        if not relative_path.parts or relative_path.parts[0] != project_id:
            raise _failure("artifact_scope_escape", scope)

        sha256 = str(option.get("sha256", "")).upper()
        if not SHA256_PATTERN.fullmatch(sha256):
            raise _failure("artifact_hash_invalid", scope)
        byte_count = option.get("byteCount")
        if not isinstance(byte_count, int) or byte_count < 0:
            raise _failure("artifact_size_invalid", scope)

        file_type = str(option.get("fileType", ""))
        if file_type == "text/markdown":
            file_type = "markdown"

        return {
            "schema": RESULT_SCHEMA,
            "capability": CAPABILITY_NAME,
            "scope": scope,
            "primitive": WORKSHOP_PRIMITIVE,
            "artifact": {
                "artifact_id": artifact_id,
                "project_id": project_id,
                "title": str(option.get("title", "")),
                "kind": str(option.get("kind", "")),
                "path": relative_path.as_posix(),
                "sha256": sha256,
                "file_type": file_type,
                "byte_count": byte_count,
                "review_status": str(option.get("reviewStatus", "unreviewed")),
            },
            "trace": [
                "kernel.capability.invoke",
                "untethered_aios.workshop_read_adapter.WorkshopArtifactReadAdapter.read",
                WORKSHOP_PRIMITIVE,
            ],
        }


def register_workshop_artifact_read(
    registry: CapabilityRegistry,
) -> WorkshopArtifactReadAdapter:
    adapter = WorkshopArtifactReadAdapter()
    registry.register(
        CAPABILITY_NAME,
        adapter.read,
        scope_arg="project_scope",
        scope_kind="resource",
        allow_wildcard_scope=False,
        mutation=False,
    )
    return adapter
