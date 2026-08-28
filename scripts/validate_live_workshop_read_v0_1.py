from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
from types import ModuleType
from typing import Any, Iterator


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from untethered_aios import CapabilityGrant, CapabilityRequest, Kernel, ProcessState
from untethered_aios.audit import hash_value
from untethered_aios.kernel import Step
from untethered_aios.workshop_read_adapter import (
    CAPABILITY_NAME,
    WORKSHOP_PRIMITIVE,
    project_scope,
    register_workshop_artifact_read,
)
from workshop.companion import server as workshop_server


LIVE_WORKSHOP = Path(r"C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS")
LIVE_DATABASE = LIVE_WORKSHOP / "data" / "workshop.sqlite3"
LIVE_PROJECTS = LIVE_WORKSHOP / "data" / "projects"
OUTPUT_PATH = REPOSITORY_ROOT / "evidence" / "workshop-read-adapter-v0.1-live-run.json"

STARTING_HEAD = "390e2cba9b4f1377642bcfe6fad9b47235fee556"
PROJECT_ID = "flashriver-source-archive"
ARTIFACT_ID = "9217e4a7-7254-53a6-a75e-1d20e0754d86"
EXPECTED_TITLE = "AGENT.md"
EXPECTED_SOURCE_SHA256 = (
    "E4EFEDCAB226193F35EAE9E1CB6070102D7FD336B70A5C3205D33976D48BB38A"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_snapshot(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    stat = path.stat()
    snapshot: dict[str, Any] = {
        "exists": True,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }
    try:
        snapshot["sha256"] = _sha256_file(path)
    except OSError as exc:
        snapshot["sha256"] = None
        snapshot["hash_status"] = f"unavailable:{type(exc).__name__}"
    return snapshot


def _runtime_snapshot() -> dict[str, dict[str, Any]]:
    return {
        "database": _file_snapshot(LIVE_DATABASE),
        "wal": _file_snapshot(Path(str(LIVE_DATABASE) + "-wal")),
        "shm": _file_snapshot(Path(str(LIVE_DATABASE) + "-shm")),
    }


@contextmanager
def _immutable_live_binding(
    proof: list[dict[str, Any]],
) -> Iterator[ModuleType]:
    original_database = workshop_server.DB
    original_projects = workshop_server.PROJECTS
    original_connect_read_only = workshop_server.connect_read_only

    def connect_immutable() -> sqlite3.Connection:
        if not LIVE_DATABASE.is_file():
            raise RuntimeError("live Workshop database is unavailable")
        uri = (
            f"file:{LIVE_DATABASE.resolve().as_posix()}"
            "?mode=ro&immutable=1"
        )
        connection = sqlite3.connect(uri, uri=True, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        query_only = int(connection.execute("PRAGMA query_only").fetchone()[0])
        if query_only != 1:
            connection.close()
            raise RuntimeError("immutable validation connection is not query-only")
        proof.append(
            {
                "mode": "ro",
                "immutable": True,
                "query_only": query_only,
                "database_name": LIVE_DATABASE.name,
            }
        )
        return connection

    workshop_server.DB = LIVE_DATABASE
    workshop_server.PROJECTS = LIVE_PROJECTS
    workshop_server.connect_read_only = connect_immutable
    try:
        yield workshop_server
    finally:
        workshop_server.connect_read_only = original_connect_read_only
        workshop_server.PROJECTS = original_projects
        workshop_server.DB = original_database


def validate() -> dict[str, Any]:
    if LIVE_WORKSHOP.resolve() == REPOSITORY_ROOT.resolve():
        raise RuntimeError("live Workshop and validation repository must be separate")
    if not LIVE_PROJECTS.is_dir():
        raise RuntimeError("live Workshop projects root is unavailable")
    if LIVE_WORKSHOP in OUTPUT_PATH.resolve().parents:
        raise RuntimeError("validation evidence must not be written into the Workshop")

    runtime_before = _runtime_snapshot()
    connection_proof: list[dict[str, Any]] = []
    kernel = Kernel()
    register_workshop_artifact_read(kernel.capabilities)
    scope = project_scope(PROJECT_ID)
    grant = CapabilityGrant(CAPABILITY_NAME, (scope,))

    def worker(context):
        return Step.done(
            context.invoke(
                CapabilityRequest(
                    CAPABILITY_NAME,
                    {
                        "project_scope": scope,
                        "artifact_id": ARTIFACT_ID,
                    },
                )
            )
        )

    with _immutable_live_binding(connection_proof):
        pid = kernel.spawn("live-workshop-artifact-reader", worker, grants=(grant,))
        kernel.run()

    process = kernel.get_process(pid)
    if process.state != ProcessState.DONE:
        raise RuntimeError(f"live read process failed: {process.error}")
    if process.grants != (grant,):
        raise RuntimeError("live read process grant changed")
    result = process.result
    if not isinstance(result, dict):
        raise RuntimeError("live read result is not structured")
    artifact = result.get("artifact")
    if not isinstance(artifact, dict):
        raise RuntimeError("live read artifact result is missing")
    if artifact.get("artifact_id") != ARTIFACT_ID:
        raise RuntimeError("live read returned a different artifact")
    if artifact.get("project_id") != PROJECT_ID:
        raise RuntimeError("live read returned a different project")
    if artifact.get("title") != EXPECTED_TITLE:
        raise RuntimeError("live read returned an unexpected public artifact title")
    if artifact.get("sha256") != EXPECTED_SOURCE_SHA256:
        raise RuntimeError("live public artifact hash differs from deployed evidence")
    if result.get("primitive") != WORKSHOP_PRIMITIVE:
        raise RuntimeError("live read trace names a different Workshop primitive")
    if len(connection_proof) != 1:
        raise RuntimeError("live read did not use exactly one immutable connection")

    capability_receipts = [
        receipt
        for receipt in kernel.audit.receipts
        if receipt.kind == "capability.call" and receipt.action == CAPABILITY_NAME
    ]
    if len(capability_receipts) != 1:
        raise RuntimeError("live read did not emit exactly one capability receipt")
    mutation_receipts = [
        receipt
        for receipt in kernel.audit.receipts
        if receipt.kind == "capability.mutation"
    ]
    if mutation_receipts:
        raise RuntimeError("read-only validation emitted a mutation receipt")
    chain_valid, chain_errors = kernel.audit.verify_chain()
    if not chain_valid:
        raise RuntimeError("receipt chain failed: " + "; ".join(chain_errors))

    runtime_after = _runtime_snapshot()
    if runtime_after != runtime_before:
        raise RuntimeError("Workshop database/runtime files changed during validation")

    result_sha256 = hash_value(result)
    capability_receipt = capability_receipts[0]
    if capability_receipt.detail.get("output_sha256") != result_sha256:
        raise RuntimeError("capability receipt output hash does not match live result")

    return {
        "schema": "untethered-workshop-read-live-validation-v0.1",
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "starting_head": STARTING_HEAD,
        "live_target": {
            "type": "existing-public-safe-artifact-metadata",
            "project_scope": scope,
            "artifact_id": ARTIFACT_ID,
            "title": EXPECTED_TITLE,
            "source_sha256": EXPECTED_SOURCE_SHA256,
        },
        "connection": connection_proof[0],
        "process": {
            "pid": pid,
            "state": process.state.value,
            "grant": {"name": grant.name, "scopes": list(grant.scopes)},
        },
        "result": result,
        "result_sha256": result_sha256,
        "capability_receipt": asdict(capability_receipt),
        "trace": result["trace"],
        "receipt_chain": {"valid": chain_valid, "errors": list(chain_errors)},
        "mutation_receipt_count": len(mutation_receipts),
        "runtime_files_before": runtime_before,
        "runtime_files_after": runtime_after,
        "runtime_files_unchanged": runtime_before == runtime_after,
    }


def main() -> int:
    evidence = validate()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"PASS: {OUTPUT_PATH}")
    print(f"RESULT_SHA256={evidence['result_sha256']}")
    print(f"RECEIPT_SHA256={evidence['capability_receipt']['sha256']}")
    print(f"RUNTIME_FILES_UNCHANGED={evidence['runtime_files_unchanged']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
