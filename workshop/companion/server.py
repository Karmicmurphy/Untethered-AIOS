from __future__ import annotations
import base64, hashlib, json, mimetypes, os, shutil, sqlite3, stat, subprocess, sys, threading, time, urllib.parse, urllib.request, uuid, zipfile
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from companion.flashriver_intake import stage_flashriver_package
from companion.foundation.promotion import PromotionError, utc_now
from companion.foundation.worker_harness import HarnessError, WorkerHarness
from companion.foundation.artifact_inspection_worker import (
    FILE_TYPES as INSPECTION_FILE_TYPES,
    MAX_INPUT_BYTES as INSPECTION_MAX_INPUT_BYTES,
    SUPPORTED_EXTENSIONS as INSPECTION_EXTENSIONS,
    WORKER_ID as INSPECTION_WORKER_ID,
)
from companion.write_room import WriteRoom, WriteRoomError, ensure_schema as ensure_write_schema
from companion.talk_room import TalkRoom, TalkRoomError, ensure_schema as ensure_talk_schema
from companion.local_worker_kit import (
    MAX_REQUEST_BYTES as LOCAL_WORKER_REQUEST_BYTES,
    LocalWorkerError,
    LocalWorkerKit,
    ensure_schema as ensure_local_worker_schema,
)
from companion.model_bay import ModelBay, ModelBayError
from companion.media_workspace import MEDIA_MAX_BYTES, MediaWorkspace, MediaWorkspaceError
from companion.video_workstation import VideoWorkstation, VideoWorkstationError
from companion.remote_access import AccessDenied, GUEST_CREATOR, OWNER, authenticate, authorize_path
from companion.visitor_bench import VisitorBench, VisitorBenchError
from companion.capability_registry import (
    CapabilityRegistry,
    CapabilityError,
    McpCatalog,
    discover_skills,
)
from companion.capability_inspection import CapabilityInspectionService, InspectionError, static_only_authority
from companion.background_removal_inspection import COMMAND_ID as BACKGROUND_REMOVAL_INSPECTION_COMMAND, inspect_opencv_grabcut
from companion.background_removal_runtime import BackgroundRemovalRuntime, BackgroundRemovalError

APP = ROOT / "app"
DATA = ROOT / "data"
PROJECTS = DATA / "projects"
IMPORTS = DATA / "imports"
BACKUPS = DATA / "backups"
SOURCE_ARCHIVES = DATA / "source_archives"
WORKER_HARNESS_DATA = DATA / "worker_harness"
WORKER_FIXTURE = ROOT / "examples" / "worker_harness" / "reference-input.md"
DB = DATA / "workshop.sqlite3"
VISITOR_BENCH_DB = DATA / "visitor_bench.sqlite3"
HOST = "127.0.0.1"
PORT = int(os.environ.get("TWIS_HOLO_PORT", "8787"))

CAPABILITIES = {
    "name": "Twis Holo Local Companion",
    "version": "1.19.0-candidate",
    "workshopRelease": "0.17",
    "authoritative": True,
    "storage": ["local-project-folders", "sqlite", "fts5", "sha256", "local-source-archives", "content-addressed-media"],
    "rooms": ["talk", "write", "music", "image", "video", "research", "code", "import", "modules"],
    "capabilityBay": {
        "schema": "twis-capability-v1",
        "status": "governed-capability-inspection-v1",
        "automaticExecution": False,
        "automaticInstallation": False,
        "automaticActivation": False,
        "databaseMigration": False,
    },
    "adapters": {
        "ai": ["optional-registered-local-model-bay", "llama.cpp-loopback-only", "no-cloud-fallback"],
        "protocols": ["mcp-policy-gated", "ag-ui-event-contract", "a2ui-surface-contract"],
        "cloud": ["cloudflare-remote-hull-optional"],
        "sourceArchive": ["flashriver-intake-local"],
        "media": ["browser-canvas-2d", "twis-local-companion", "opencv-grabcut-fixed-adapter", "engine-neutral-workflow-contracts"]
    },
    "permissions": {
        "default": "deny-dangerous-actions",
        "requiresHumanApproval": [
            "delete-permanent-source",
            "publish",
            "spend-money",
            "run-shell-command",
            "invoke-external-tool",
            "send-private-memory",
            "approve-canon"
        ]
    },
    "foundation": {
        "release": "0.5.0",
        "workerCards": {
            "schema": "0.1",
            "status": "enforced-for-two-fixed-workers",
            "hostEnforced": True,
            "scope": "reference-metadata-worker-and-artifact-compass-inspection-worker"
        },
        "workerHarness": {
            "schema": "0.3",
            "status": "bounded-fixed-worker-harness",
            "arbitraryWorkers": False,
            "automaticActivation": False,
            "network": False,
            "shell": False,
            "hostileProcessIsolation": False
        },
        "guardedPromotion": {
            "status": "hash-and-generation-bound",
            "humanIdentityAuthenticated": False,
            "activationKind": "registry-only-or-artifact-report-attachment-no-startup-execution",
            "rollbackScope": "one-bounded-output-and-registry-or-attachment-entry"
        },
        "pathContainment": {
            "status": "enforcement-library-for-cooperating-callers",
            "operatingSystemSandbox": False
        },
        "transactions": {
            "status": "bounded-library",
            "recoveryScope": ["individual-files", "sqlite-backups"]
        },
        "artifactCompass": {
            "status": "separate-sqlite-fts5-library-with-read-only-inspection-worker",
            "liveIndexBuilt": False,
            "vectorSearch": False,
            "aiModelUsed": False
        },
        "writeRoom": {
            "schema": "write-project-v1",
            "status": "durable-local-daily-use-slice",
            "autosave": True,
            "recoveryDrafts": True,
            "versionHistory": True,
            "boundedDeterministicWorkers": True,
            "explicitProposalApproval": True,
            "automaticMutation": False,
            "network": False,
            "aiModelUsed": False
        },
        "talkRoom": {
            "schema": "talk-session-v1",
            "status": "durable-local-daily-use-slice",
            "orderedTranscript": True,
            "recoveryDrafts": True,
            "versionHistory": True,
            "markedPassages": True,
            "governedTalkToWrite": True,
            "deterministicCodeInspection": True,
            "networkSpeechRecognitionEnabled": False,
            "rawAudioRetained": False,
            "automaticMutation": False,
            "network": False,
            "aiModelUsed": False
        },
        "localApiWorkerKit": {
            "schema": "local-api-worker-kit-v1",
            "packetSchema": "worker-packet-v1",
            "status": "bounded-four-worker-kit",
            "workers": [
                "approved-text-reader",
                "code-structure-inspector",
                "note-proposal-worker",
                "package-manifest-validator"
            ],
            "registeredSourcesOnly": True,
            "planApprovalRequired": True,
            "resultApprovalRequired": True,
            "automaticAttachment": False,
            "automaticActivation": False,
            "arbitraryWorkers": False,
            "shell": False,
            "network": False,
            "aiModelUsed": False
        },
        "draftWorkshop": {
            "schema": "builder-output-v1",
            "status": "governed-writing-task-preparation",
            "worker": "draft-workshop",
            "operations": ["rewrite-clearly", "shorten", "expand-notes", "change-tone", "structure-document"],
            "registeredOrOwnerRoughText": True,
            "sourceHashBound": True,
            "inactiveDraftOnly": True,
            "externalProviderCalled": False,
            "automaticSourceMutation": False
        },
        "evidenceCompare": {
            "schema": "builder-output-v1",
            "status": "governed-deterministic-comparison-preparation",
            "worker": "evidence-compare",
            "registeredSourcesOnly": True,
            "minimumSources": 2,
            "maximumSources": 8,
            "sourceHashBound": True,
            "semanticConclusionsGenerated": False,
            "network": False,
            "externalProviderCalled": False,
            "automaticSourceMutation": False
        },
        "visualBriefBuilder": {
            "schema": "builder-output-v1",
            "status": "governed-deterministic-visual-brief-preparation",
            "worker": "visual-brief-builder",
            "minimumRegisteredSources": 0,
            "maximumRegisteredSources": 4,
            "ownerNotesHashBound": True,
            "sourceHashBound": True,
            "imageGenerated": False,
            "network": False,
            "externalProviderCalled": False,
            "automaticSourceMutation": False
        },
        "songProductionBriefBuilder": {
            "schema": "builder-output-v1",
            "status": "governed-deterministic-song-production-brief-preparation",
            "worker": "song-production-brief-builder",
            "minimumRegisteredSources": 0,
            "maximumRegisteredSources": 4,
            "temporaryMusicNotesHashBound": True,
            "temporaryLyricsHashBound": True,
            "ownerLyricsPreservedExactly": True,
            "sourceHashBound": True,
            "musicGenerated": False,
            "audioPlayback": False,
            "network": False,
            "externalProviderCalled": False,
            "automaticSourceMutation": False
        },
        "videoProductionBriefBuilder": {
            "schema": "builder-output-v1",
            "status": "governed-deterministic-video-production-brief-preparation",
            "worker": "video-production-brief-builder",
            "minimumRegisteredSources": 0,
            "maximumRegisteredSources": 4,
            "temporaryVideoNotesHashBound": True,
            "sourceHashBound": True,
            "videoGenerated": False,
            "videoRendered": False,
            "network": False,
            "externalProviderCalled": False,
            "automaticSourceMutation": False
        },
        "videoWorkstation": {
            "schema": "twis-video-composition-v1",
            "status": "bounded-local-video-assembly-and-rendering",
            "visualInputs": ["governed-image", "storyboard-item"],
            "audioInputs": ["governed-music-render"],
            "textInputs": ["owner-title", "explicit-writing-reference"],
            "motion": ["still", "zoom-in", "zoom-out", "pan-left", "pan-right", "pan-up", "pan-down"],
            "transitions": ["cut", "crossfade"],
            "output": "inactive-governed-mp4",
            "arbitraryShell": False,
            "generativeVideo": False,
            "network": False,
            "externalProviderCalled": False,
            "automaticSourceMutation": False
        },
        "buildWorkOrderBuilder": {
            "schema": "builder-output-v1", "status": "governed-deterministic-build-work-order-preparation",
            "worker": "build-work-order-builder", "minimumRegisteredSources": 0, "maximumRegisteredSources": 4,
            "temporaryBuildInputHashBound": True, "sourceHashBound": True, "codeExecuted": False,
            "shellExecuted": False, "filesModified": False, "network": False, "externalProviderCalled": False
        },
        "moduleProposalBuilder": {
            "schema": "builder-output-v1", "status": "governed-deterministic-module-proposal-preparation",
            "worker": "module-proposal-builder", "minimumRegisteredSources": 0, "maximumRegisteredSources": 4,
            "temporaryModuleInputHashBound": True, "sourceHashBound": True, "installed": False,
            "downloaded": False, "executed": False, "network": False, "externalProviderCalled": False
        }
    }
}

SECURITY_POLICY = {
    "mcp": {
        "mode": "deny-by-default",
        "toolMetadataTrusted": False,
        "requireStaticReview": True,
        "requireHumanApprovalForInvocation": True,
        "blockedByDefault": ["shell", "network-exfiltration", "credential-read", "filesystem-write-outside-project"],
        "receiptRequired": True
    },
    "cloudflare": {
        "authoritative": False,
        "writesRequireTokenWhenConfigured": True,
        "localProjectRemainsSourceOfTruth": True
    },
    "sourceArchives": {
        "rawArchivesStayLocal": True,
        "nestedSourceZipsStayLocal": True,
        "publicGitHubGetsOnlySafeCodeDocsTests": True,
        "cloudflareAuthority": False,
        "receiptRequired": True
    },
    "ai": {
        "advisoryOnly": True,
        "cannotApproveCanon": True,
        "cannotDeletePermanentSource": True,
        "cannotSpendMoney": True
    }
}

for p in (PROJECTS, IMPORTS, BACKUPS, SOURCE_ARCHIVES):
    p.mkdir(parents=True, exist_ok=True)

def utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def safe_id(value: str) -> str:
    out = "".join(c if c.isalnum() or c in "-_" else "-" for c in value.strip().lower())
    return out.strip("-") or str(uuid.uuid4())


_database_init_lock = threading.RLock()
_initialized_database_path: str | None = None
DB_WRITE_LOCK = threading.RLock()


def _open_connection() -> sqlite3.Connection:
    con = sqlite3.connect(DB, timeout=5.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def _initialize_database() -> None:
    global _initialized_database_path
    database_path = str(DB.resolve())
    with _database_init_lock:
        if _initialized_database_path == database_path and DB.is_file():
            return
        con = _open_connection()
        con.executescript("""
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS projects(
      id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
      next_action TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS artifacts(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, kind TEXT NOT NULL, title TEXT NOT NULL,
      path TEXT NOT NULL DEFAULT '', payload TEXT NOT NULL DEFAULT '{}',
      authority_state TEXT NOT NULL DEFAULT 'DRAFT', sha256 TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE VIRTUAL TABLE IF NOT EXISTS artifact_search USING fts5(
      id UNINDEXED, project_id UNINDEXED, title, kind, content
    );
    CREATE TABLE IF NOT EXISTS sessions(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, room TEXT NOT NULL,
      summary TEXT NOT NULL DEFAULT '', active_constraints TEXT NOT NULL DEFAULT '[]',
      next_action TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, closed_at TEXT
    );
    CREATE TABLE IF NOT EXISTS receipts(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, action TEXT NOT NULL,
      actor TEXT NOT NULL, details TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS modules(
      id TEXT PRIMARY KEY, enabled INTEGER NOT NULL DEFAULT 1, settings TEXT NOT NULL DEFAULT '{}'
    );
    CREATE TABLE IF NOT EXISTS jobs(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, operation TEXT NOT NULL,
      status TEXT NOT NULL, payload TEXT NOT NULL DEFAULT '{}', result TEXT NOT NULL DEFAULT '{}',
      created_at TEXT NOT NULL, updated_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS artifact_reviews(
      artifact_id TEXT PRIMARY KEY, project_id TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'unreviewed', notes TEXT NOT NULL DEFAULT '',
      reviewed_at TEXT, updated_at TEXT NOT NULL
    );
    """)
        ensure_write_schema(con)
        ensure_talk_schema(con)
        ensure_local_worker_schema(con)
        if int(con.execute("PRAGMA user_version").fetchone()[0]) < 13:
            con.execute("BEGIN IMMEDIATE")
            con.execute("PRAGMA user_version=13")
            con.commit()
        else:
            con.commit()
        con.close()
        _initialized_database_path = database_path


def connect() -> sqlite3.Connection:
    _initialize_database()
    return _open_connection()


def connect_read_only() -> sqlite3.Connection:
    if not DB.is_file():
        raise HarnessError("workshop_database_missing", "Workshop database is unavailable")
    con = sqlite3.connect(f"file:{DB.resolve().as_posix()}?mode=ro", uri=True, timeout=5.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA busy_timeout=5000")
    return con


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _is_reparse_point(path: Path) -> bool:
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def _contains_reparse_point(path: Path, root: Path) -> bool:
    current = path
    while True:
        if current.is_symlink() or _is_reparse_point(current):
            return True
        if current == root or current.parent == current:
            return False
        current = current.parent


def public_artifact_roots() -> list[Path]:
    projects_root = PROJECTS.resolve(strict=False)
    roots: list[Path] = []
    if not PROJECTS.is_dir():
        return roots
    for candidate in PROJECTS.glob("*/sources/flashriver/*/docs"):
        if not candidate.is_dir() or candidate.is_symlink() or _is_reparse_point(candidate):
            continue
        resolved = candidate.resolve(strict=False)
        if _is_within(resolved, projects_root):
            roots.append(resolved)
    return sorted(set(roots), key=lambda path: str(path).casefold())


def blocked_artifact_roots() -> list[Path]:
    blocked = [DB, IMPORTS, BACKUPS, SOURCE_ARCHIVES, ROOT / "FLASHRIVER.zip", ROOT / "FLASHRIVER_RECEIPT.json"]
    if PROJECTS.is_dir():
        blocked.extend(PROJECTS.glob("*/sources/flashriver/*/private_source_artifacts"))
        blocked.extend(PROJECTS.glob("*/sources/flashriver/*/visuals"))
    return sorted({path.resolve(strict=False) for path in blocked}, key=lambda path: str(path).casefold())


def _text_block_reason(path: Path) -> str | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return "source_unreadable"
    if b"\x00" in raw:
        return "binary_content"
    if raw:
        controls = sum(byte < 32 and byte not in {9, 10, 13} for byte in raw)
        if controls / len(raw) > 0.01:
            return "binary_content"
    try:
        raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return "invalid_utf8"
    return None


def artifact_inspection_options(project_id: str | None = None) -> list[dict[str, Any]]:
    roots = public_artifact_roots()
    roots_resolved = [root.resolve(strict=False) for root in roots]
    connection = connect_read_only()
    try:
        parameters: tuple[Any, ...] = ()
        where = ""
        if project_id:
            where = "WHERE a.project_id = ?"
            parameters = (project_id,)
        rows = connection.execute(
            f"""
            SELECT a.id, a.project_id, a.kind, a.title, a.path, a.payload,
                   a.authority_state, a.sha256, COALESCE(r.status, 'unreviewed') AS review_status
            FROM artifacts AS a
            LEFT JOIN artifact_reviews AS r ON r.artifact_id = a.id
            {where}
            ORDER BY lower(a.title), a.title, a.id
            """,
            parameters,
        ).fetchall()
        duplicate_rows = connection.execute(
            "SELECT id, project_id, title, path, sha256 FROM artifacts WHERE sha256 <> '' ORDER BY lower(path), path, id"
        ).fetchall()
    finally:
        connection.close()
    duplicate_groups: dict[str, list[dict[str, Any]]] = {}
    for row in duplicate_rows:
        duplicate_groups.setdefault(str(row["sha256"]).upper(), []).append(
            {
                "artifact_id": row["id"],
                "project_id": row["project_id"],
                "title": row["title"],
                "source_path": row["path"],
            }
        )
    options: list[dict[str, Any]] = []
    projects_root = PROJECTS.resolve(strict=False)
    for row in rows:
        reasons: list[str] = []
        payload = json.loads(row["payload"] or "{}")
        relative = Path(str(row["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            reasons.append("path_traversal_or_absolute_path")
        source_candidate = PROJECTS / row["project_id"] / relative
        source_path = source_candidate.resolve(strict=False)
        if not _is_within(source_path, projects_root):
            reasons.append("outside_projects_root")
        matched_root = next((root for root in roots_resolved if _is_within(source_path, root)), None)
        if matched_root is None:
            reasons.append("outside_public_safe_roots")
        elif _contains_reparse_point(source_candidate, PROJECTS):
            reasons.append("symlink_or_junction_path")
        is_private = row["authority_state"] == "SOURCE_PRIVATE" or row["kind"] == "flashriver-private-source" or payload.get("private") is True
        if is_private:
            reasons.append("private_source")
        suffix = source_path.suffix.lower()
        if suffix not in INSPECTION_EXTENSIONS:
            reasons.append("unsupported_extension")
        structurally_public = matched_root is not None and not is_private and suffix in INSPECTION_EXTENSIONS and "symlink_or_junction_path" not in reasons
        if not source_path.is_file():
            reasons.append("source_missing")
            size = None
            current_hash = None
        else:
            size = source_path.stat().st_size
            if size > INSPECTION_MAX_INPUT_BYTES:
                reasons.append("oversized_input")
            if structurally_public and size <= INSPECTION_MAX_INPUT_BYTES:
                current_hash = hashlib.sha256(source_path.read_bytes()).hexdigest().upper()
                text_reason = _text_block_reason(source_path)
                if text_reason:
                    reasons.append(text_reason)
            else:
                current_hash = None
        stored_hash = str(row["sha256"] or "").upper()
        if not stored_hash or (current_hash is not None and current_hash != stored_hash):
            reasons.append("source_hash_mismatch")
        duplicate_group = duplicate_groups.get(stored_hash, [])
        provenance = [
            {"kind": key, "value": payload[key]}
            for key in ("sourcePackageSha256", "sourcePackage", "archiveMember", "relativeName")
            if isinstance(payload.get(key), (str, int, float, bool))
        ]
        options.append(
            {
                "artifactId": row["id"],
                "projectId": row["project_id"],
                "title": row["title"],
                "kind": row["kind"],
                "sourcePath": str(source_path),
                "sha256": stored_hash,
                "fileType": INSPECTION_FILE_TYPES.get(suffix),
                "byteCount": size,
                "reviewStatus": row["review_status"],
                "eligible": not reasons,
                "blockedReasons": sorted(set(reasons)),
                "duplicateHashGroup": duplicate_group if len(duplicate_group) > 1 else [],
                "provenanceReferences": provenance,
            }
        )
    return options


def resolve_inspection_artifact(artifact_id: str) -> dict[str, Any]:
    if not isinstance(artifact_id, str) or not artifact_id.strip() or len(artifact_id) > 200:
        raise HarnessError("artifact_id_invalid", "artifact ID is invalid")
    option = next((item for item in artifact_inspection_options() if item["artifactId"] == artifact_id), None)
    if option is None:
        raise HarnessError("artifact_not_found", "selected artifact does not exist")
    if not option["eligible"]:
        raise HarnessError(
            "artifact_ineligible",
            "selected artifact is not eligible for read-only inspection",
            details={"reasons": option["blockedReasons"]},
        )
    return {
        "artifact_id": option["artifactId"],
        "project_id": option["projectId"],
        "source_path": option["sourcePath"],
        "sha256": option["sha256"],
        "file_type": option["fileType"],
        "byte_count": option["byteCount"],
        "review_status": option["reviewStatus"],
        "duplicate_hash_group": option["duplicateHashGroup"],
        "provenance_references": option["provenanceReferences"],
    }

def json_response(handler, status: int, data: Any):
    body = json.dumps(data, ensure_ascii=False).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)

def body_json(handler) -> Any:
    n = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(n) if n else b"{}"
    return json.loads(raw.decode("utf-8"))


def background_removal_body_json(handler, *, limit: int = 512 * 1024) -> dict[str, Any]:
    if handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise BackgroundRemovalError("content_type_invalid", "Background-removal actions require application/json", 415)
    if handler.headers.get("Sec-Fetch-Site", "").strip().lower() == "cross-site":
        raise BackgroundRemovalError("cross_site_request_denied", "Cross-site background-removal actions are denied", 403)
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise BackgroundRemovalError("request_length_invalid", "Background-removal Content-Length is invalid") from exc
    if length < 2 or length > limit:
        raise BackgroundRemovalError("request_too_large", "Background-removal request is empty or exceeds 512 KiB", 413)
    try:
        value = json.loads(handler.rfile.read(length).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BackgroundRemovalError("request_json_invalid", "Background-removal request must be valid JSON") from exc
    if not isinstance(value, dict):
        raise BackgroundRemovalError("request_json_invalid", "Background-removal request must be a JSON object")
    return value


def visitor_bench_body_json(handler, *, limit: int = 300 * 1024) -> dict[str, Any]:
    if handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "application/json":
        raise VisitorBenchError("guest_content_type_invalid", "Visitor's Bench actions require application/json")
    if handler.headers.get("Sec-Fetch-Site", "").strip().lower() == "cross-site":
        raise VisitorBenchError("guest_cross_site_denied", "Cross-site Visitor's Bench actions are denied", 403)
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise VisitorBenchError("guest_request_length_invalid", "Visitor's Bench Content-Length is invalid") from exc
    if length < 0 or length > limit:
        raise VisitorBenchError("guest_request_too_large", "Visitor's Bench request exceeds 300 KiB", 413)
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise VisitorBenchError("guest_request_invalid", "Visitor's Bench request is invalid JSON") from exc
    if not isinstance(value, dict):
        raise VisitorBenchError("guest_request_invalid", "Visitor's Bench request must be an object")
    return value


def write_body_json(handler, *, limit: int = 6 * 1024 * 1024) -> dict[str, Any]:
    content_type = handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise WriteRoomError("content_type_invalid", "Writing actions require application/json")
    if handler.headers.get("Sec-Fetch-Site", "").lower() == "cross-site":
        raise WriteRoomError("cross_site_request_denied", "Cross-site writing actions are denied")
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise WriteRoomError("request_length_invalid", "Request Content-Length is invalid") from exc
    if length < 0 or length > limit:
        raise WriteRoomError("request_too_large", "Writing request exceeds 6 MiB")
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise WriteRoomError("request_json_invalid", "Writing request must be a JSON object") from exc
    if not isinstance(value, dict):
        raise WriteRoomError("request_json_invalid", "Writing request must be a JSON object")
    return value


def write_room() -> WriteRoom:
    return WriteRoom(connect, PROJECTS)


def media_workspace() -> MediaWorkspace:
    return MediaWorkspace(DB, PROJECTS, ROOT / "config" / "media-capabilities.json")


def video_workstation() -> VideoWorkstation:
    return VideoWorkstation(DB, PROJECTS, ROOT.parent / "runtime")


_background_removal_instance: BackgroundRemovalRuntime | None = None
_background_removal_lock = threading.Lock()


def background_removal() -> BackgroundRemovalRuntime:
    global _background_removal_instance
    with _background_removal_lock:
        if _background_removal_instance is None:
            _background_removal_instance = BackgroundRemovalRuntime(
                DB,
                PROJECTS,
                ROOT.parent / "runtime",
                ROOT / "config" / "background-removal-runtime.json",
                media_workspace(),
            )
        return _background_removal_instance


def write_error_response(handler, error: WriteRoomError) -> None:
    json_response(
        handler,
        error.status,
        {"ok": False, "code": error.code, "error": str(error), "details": error.details},
    )


def talk_body_json(handler, *, limit: int = 6 * 1024 * 1024) -> dict[str, Any]:
    content_type = handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise TalkRoomError("content_type_invalid", "Talk actions require application/json")
    if handler.headers.get("Sec-Fetch-Site", "").lower() == "cross-site":
        raise TalkRoomError("cross_site_request_denied", "Cross-site Talk actions are denied")
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise TalkRoomError("request_length_invalid", "Request Content-Length is invalid") from exc
    if length < 0 or length > limit:
        raise TalkRoomError("request_too_large", "Talk request exceeds 6 MiB")
    try:
        value = json.loads(handler.rfile.read(length).decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TalkRoomError("request_json_invalid", "Talk request must be a JSON object") from exc
    if not isinstance(value, dict):
        raise TalkRoomError("request_json_invalid", "Talk request must be a JSON object")
    return value


def talk_room() -> TalkRoom:
    return TalkRoom(connect, PROJECTS)


def talk_error_response(handler, error: TalkRoomError) -> None:
    json_response(
        handler,
        error.status,
        {
            "ok": False,
            "code": error.code,
            "message": str(error),
            "details": error.details,
        },
    )


_local_worker_kit_instance: LocalWorkerKit | None = None
_local_worker_kit_lock = threading.Lock()
_local_worker_startup_recovery_complete = False
_model_bay_instance: ModelBay | None = None
_model_bay_lock = threading.Lock()
_capability_registry_instance: CapabilityRegistry | None = None
_capability_registry_lock = threading.Lock()
_mcp_catalog_instance: McpCatalog | None = None
_capability_inspection_instance: CapabilityInspectionService | None = None
_capability_inspection_lock = threading.Lock()


def model_bay() -> ModelBay:
    global _model_bay_instance
    with _model_bay_lock:
        if _model_bay_instance is None:
            _model_bay_instance = ModelBay(ROOT)
        return _model_bay_instance


def capability_registry() -> CapabilityRegistry:
    global _capability_registry_instance
    with _capability_registry_lock:
        if _capability_registry_instance is None:
            _capability_registry_instance = CapabilityRegistry(
                ROOT / "config" / "capability-registry.json",
                root=ROOT,
            )
        return _capability_registry_instance


def capability_inspection() -> CapabilityInspectionService:
    global _capability_inspection_instance
    with _capability_inspection_lock:
        if _capability_inspection_instance is None:
            registry = capability_registry()
            _capability_inspection_instance = CapabilityInspectionService(
                connect,
                registry,
                ROOT,
                functional_adapters={BACKGROUND_REMOVAL_INSPECTION_COMMAND: inspect_opencv_grabcut},
            )
            registry.set_verification_provider(_capability_inspection_instance.verification_overlays)
        return _capability_inspection_instance


def mcp_catalog() -> McpCatalog:
    global _mcp_catalog_instance
    with _capability_registry_lock:
        if _mcp_catalog_instance is None:
            payload = json.loads((ROOT / "config" / "mcp-catalog.json").read_text(encoding="utf-8"))
            _mcp_catalog_instance = McpCatalog(list(payload.get("servers") or []))
        return _mcp_catalog_instance


def local_worker_kit() -> LocalWorkerKit:
    """Return the fixed local workers and perform one safe startup recovery pass."""
    global _local_worker_kit_instance, _local_worker_startup_recovery_complete
    with _local_worker_kit_lock:
        if _local_worker_kit_instance is None:
            _local_worker_kit_instance = LocalWorkerKit(
                connect,
                PROJECTS,
                model_bay=model_bay(),
                capability_registry=capability_inspection().registry,
            )
        if not _local_worker_startup_recovery_complete:
            _local_worker_kit_instance.recover_interrupted_on_startup()
            _local_worker_startup_recovery_complete = True
        return _local_worker_kit_instance


def local_worker_body_json(handler) -> dict[str, Any]:
    content_type = handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise LocalWorkerError(
            "content_type_invalid",
            "Local worker actions require application/json",
        )
    if handler.headers.get("Sec-Fetch-Site", "").lower() == "cross-site":
        raise LocalWorkerError(
            "cross_site_request_denied",
            "Cross-site local worker actions are denied",
            status=403,
        )
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise LocalWorkerError(
            "request_length_invalid",
            "Request Content-Length is invalid",
        ) from exc
    if length < 0 or length > LOCAL_WORKER_REQUEST_BYTES:
        raise LocalWorkerError(
            "request_too_large",
            "Local worker requests are limited to 256 KiB",
            status=413,
        )
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LocalWorkerError(
            "request_json_invalid",
            "Local worker requests must be JSON objects",
        ) from exc
    if not isinstance(value, dict):
        raise LocalWorkerError(
            "request_json_invalid",
            "Local worker requests must be JSON objects",
        )
    return value


def local_worker_fields(value: dict[str, Any], allowed: set[str]) -> None:
    unsupported = set(value) - allowed
    if unsupported:
        raise LocalWorkerError(
            "request_fields_invalid",
            "The local worker request contains unsupported fields",
            details={"unsupported": sorted(unsupported)},
        )


def local_worker_error_response(handler, error: LocalWorkerError) -> None:
    json_response(
        handler,
        error.status,
        {
            "ok": False,
            "code": error.code,
            "error": str(error),
            "details": error.details,
        },
    )


def model_bay_error_response(handler, error: ModelBayError) -> None:
    json_response(
        handler,
        error.status,
        {"ok": False, "code": error.code, "error": str(error), "details": error.details},
    )


_worker_harness_instance: WorkerHarness | None = None
_worker_harness_lock = threading.Lock()


def worker_harness() -> WorkerHarness:
    """Return the fixed-worker harness without writing Workshop SQLite."""
    global _worker_harness_instance
    with _worker_harness_lock:
        if _worker_harness_instance is None:
            protected = blocked_artifact_roots()
            _worker_harness_instance = WorkerHarness(
                WORKER_HARNESS_DATA,
                fixture_source=WORKER_FIXTURE,
                protected_roots=protected,
                public_artifact_roots=public_artifact_roots(),
                allow_test_faults=False,
            )
        return _worker_harness_instance


def worker_body_json(handler, *, limit: int = 16 * 1024) -> dict[str, Any]:
    content_type = handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json":
        raise HarnessError("content_type_invalid", "worker-harness actions require application/json")
    if handler.headers.get("Sec-Fetch-Site", "").lower() == "cross-site":
        raise HarnessError("cross_site_request_denied", "cross-site worker-harness actions are denied")
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise HarnessError("request_length_invalid", "request Content-Length is invalid") from exc
    if length < 0 or length > limit:
        raise HarnessError("request_too_large", "worker-harness request exceeds 16 KiB")
    raw = handler.rfile.read(length) if length else b"{}"
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HarnessError("request_json_invalid", "worker-harness request must be a JSON object") from exc
    if not isinstance(value, dict):
        raise HarnessError("request_json_invalid", "worker-harness request must be a JSON object")
    return value


def worker_error_response(handler, error: HarnessError | PromotionError) -> None:
    not_found = {"candidate_not_found", "plan_not_found", "artifact_not_found"}
    conflicts = {
        "candidate_hash_mismatch", "candidate_output_changed", "candidate_record_changed",
        "candidate_state_rejected", "workspace_generation_mismatch", "workspace_generation_stale",
        "plan_hash_mismatch", "worker_card_changed", "duplicate_activation", "worker_already_active",
        "registry_interrupted", "registry_write_interrupted", "activation_not_active",
        "rollback_current_hash_mismatch", "recovery_point_unavailable", "recovery_point_changed",
        "receipt_chain_invalid", "tests_no_longer_pass", "canonical_root_changed",
        "source_artifact_hash_mismatch", "source_artifact_changed", "source_artifact_unavailable",
        "worker_card_hash_mismatch", "execution_plan_hash_mismatch", "source_changed_before_inspection",
        "source_changed_during_inspection", "plan_worker_mismatch",
    }
    status = 404 if error.code in not_found else 409 if error.code in conflicts else 400
    json_response(handler, status, {"ok": False, "code": error.code, "error": str(error), "details": error.details})

def project_dir(project_id: str) -> Path:
    p = (PROJECTS / safe_id(project_id)).resolve()
    if PROJECTS.resolve() not in p.parents and p != PROJECTS.resolve():
        raise ValueError("unsafe path")
    p.mkdir(parents=True, exist_ok=True)
    for name in ("artifacts","media","sources","drafts","receipts","sessions","code","imports"):
        (p/name).mkdir(exist_ok=True)
    return p


MUSIC_RENDER_MAX_BYTES = 16 * 1024 * 1024
MUSIC_LOOP_MAX_BYTES = 16 * 1024 * 1024


def _music_render_body(handler) -> bytes:
    if handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "audio/wav":
        raise ValueError("Music renders require audio/wav")
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise ValueError("Music render Content-Length is invalid") from exc
    if length < 44 or length > MUSIC_RENDER_MAX_BYTES:
        raise ValueError("Music render must be a WAV file between 44 bytes and 16 MiB")
    return handler.rfile.read(length)


def _validate_music_wav(raw: bytes) -> dict[str, Any]:
    if len(raw) < 44 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise ValueError("Music render is not a RIFF/WAVE file")
    riff_size = int.from_bytes(raw[4:8], "little")
    if riff_size + 8 != len(raw):
        raise ValueError("Music render RIFF size does not match its content")
    cursor = 12
    fmt: bytes | None = None
    audio = b""
    while cursor + 8 <= len(raw):
        chunk_id = raw[cursor:cursor + 4]
        chunk_size = int.from_bytes(raw[cursor + 4:cursor + 8], "little")
        start = cursor + 8
        end = start + chunk_size
        if end > len(raw):
            raise ValueError("Music render contains a truncated WAV chunk")
        if chunk_id == b"fmt ":
            fmt = raw[start:end]
        elif chunk_id == b"data":
            audio = raw[start:end]
        cursor = end + (chunk_size % 2)
    if fmt is None or len(fmt) < 16 or not audio:
        raise ValueError("Music render is missing PCM format or audio data")
    audio_format = int.from_bytes(fmt[0:2], "little")
    channels = int.from_bytes(fmt[2:4], "little")
    sample_rate = int.from_bytes(fmt[4:8], "little")
    bits = int.from_bytes(fmt[14:16], "little")
    if audio_format != 1 or channels not in {1, 2} or bits != 16 or not 8000 <= sample_rate <= 192000:
        raise ValueError("Music render must be mono/stereo 16-bit PCM WAV audio")
    non_silent = any(audio[index:index + 2] not in {b"\x00\x00", b""} for index in range(0, len(audio), 2))
    if not non_silent:
        raise ValueError("Music render contains no audible waveform data")
    frames = len(audio) // (channels * (bits // 8))
    return {
        "channels": channels,
        "sampleRate": sample_rate,
        "bitsPerSample": bits,
        "audioBytes": len(audio),
        "frames": frames,
        "durationSeconds": round(frames / sample_rate, 6),
    }


def _music_render_path(project_id: str, relative: str) -> Path:
    root = (project_dir(project_id) / "exports" / "music").resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = (project_dir(project_id) / relative).resolve()
    if root not in target.parents or target.suffix.lower() != ".wav":
        raise ValueError("Music render path is outside the governed export directory")
    return target


def _music_loop_body(handler) -> bytes:
    if handler.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "audio/wav":
        raise ValueError("Music loops require audio/wav")
    try:
        length = int(handler.headers.get("Content-Length", "0"))
    except ValueError as exc:
        raise ValueError("Music loop Content-Length is invalid") from exc
    if length < 44 or length > MUSIC_LOOP_MAX_BYTES:
        raise ValueError("Music loop must be a WAV file between 44 bytes and 16 MiB")
    return handler.rfile.read(length)


def _music_loop_path(project_id: str, relative: str) -> Path:
    root = (project_dir(project_id) / "media" / "audio" / "loops").resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = (project_dir(project_id) / relative).resolve()
    if root not in target.parents or target.suffix.lower() != ".wav":
        raise ValueError("Music loop path is outside the governed loop directory")
    return target

def index_artifact(con, a):
    content = f'{a["title"]} {a["kind"]} {json.dumps(a.get("payload",{}), ensure_ascii=False)}'
    con.execute("DELETE FROM artifact_search WHERE id=?", (a["id"],))
    con.execute("INSERT INTO artifact_search(id,project_id,title,kind,content) VALUES(?,?,?,?,?)",
                (a["id"],a["projectId"],a["title"],a["kind"],content))

def add_receipt(con, project_id, action, actor, details):
    con.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?)",
                (str(uuid.uuid4()),project_id,action,actor,json.dumps(details,ensure_ascii=False),utc()))


def upsert_project(con, pid: str, title: str, description: str, next_action: str) -> None:
    now = utc()
    con.execute("""INSERT INTO projects(id,title,description,next_action,created_at,updated_at)
                   VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                   title=excluded.title,description=excluded.description,next_action=excluded.next_action,updated_at=excluded.updated_at""",
                (pid, title, description, next_action, now, now))


def save_artifact_row(con, a: dict[str, Any]) -> None:
    con.execute("""INSERT INTO artifacts(id,project_id,kind,title,path,payload,authority_state,sha256,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                   kind=excluded.kind,title=excluded.title,path=excluded.path,payload=excluded.payload,
                   authority_state=excluded.authority_state,sha256=excluded.sha256,updated_at=excluded.updated_at""",
                (a["id"], a["projectId"], a["kind"], a["title"], a.get("path", ""), json.dumps(a.get("payload", {}), ensure_ascii=False), a.get("authorityState", "SOURCE"), a.get("hash", ""), a.get("createdAt", utc()), a.get("updatedAt", utc())))
    index_artifact(con, a)


def artifact_source_path(artifact: dict[str, Any]) -> str:
    payload = artifact.get("payload") or {}
    return str(
        payload.get("archiveMember")
        or payload.get("relativeName")
        or artifact.get("path")
        or payload.get("localPath")
        or ""
    )


def duplicate_artifact_groups(artifacts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for artifact in artifacts:
        digest = str(artifact.get("sha256") or "").strip().lower()
        if digest:
            buckets.setdefault(digest, []).append(artifact)
    groups = []
    for digest, members in buckets.items():
        if len(members) < 2:
            continue
        member_rows = [
            {
                "artifactId": member["id"],
                "title": member["title"],
                "sourcePath": artifact_source_path(member),
            }
            for member in members
        ]
        member_rows.sort(key=lambda member: (member["sourcePath"].lower(), member["title"].lower(), member["artifactId"]))
        groups.append({"sha256": digest, "count": len(member_rows), "members": member_rows})
    groups.sort(key=lambda group: (-group["count"], group["sha256"]))
    return groups

class Handler(SimpleHTTPRequestHandler):
    server_version = "TwisHoloCompanion/1.0"

    def translate_path(self, path):
        clean = urllib.parse.urlparse(path).path
        if clean.startswith("/api/"):
            return str(APP / "__api__")
        if clean == "/":
            clean = "/index.html"
        return str(APP / clean.lstrip("/"))

    def _principal(self):
        principal = getattr(self, "_twis_principal", None)
        if principal is None:
            principal = authenticate(self.headers, self.client_address[0])
            authorize_path(principal, self.command, urllib.parse.urlparse(self.path).path)
            self._twis_principal = principal
        return principal

    def _authorize_or_deny(self) -> bool:
        try:
            self._principal()
            return True
        except AccessDenied as error:
            json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})
            return False

    def do_GET(self):
        if not self._authorize_or_deny():
            return
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if u.path == "/api/session":
            principal = self._principal()
            json_response(self, 200, {"ok": True, "role": principal.role, "identity": principal.identity, "remote": principal.remote, "authType": principal.auth_type})
            return
        if u.path == "/api/visitor-bench/submissions":
            principal = self._principal()
            if principal.role not in {OWNER, GUEST_CREATOR}:
                json_response(self, 403, {"ok": False, "code": "visitor_read_only", "error": "Visitor access has no saved work"})
                return
            rows = VisitorBench(VISITOR_BENCH_DB).list(identity=principal.identity, owner=principal.role == OWNER)
            json_response(self, 200, {"ok": True, "submissions": rows})
            return
        if u.path.startswith("/api/visitor-bench/submissions/"):
            principal = self._principal()
            submission_id = u.path.rsplit("/", 1)[-1]
            try:
                row = VisitorBench(VISITOR_BENCH_DB).get(submission_id, identity=principal.identity, owner=principal.role == OWNER)
                json_response(self, 200, {"ok": True, "submission": row})
            except VisitorBenchError as error:
                json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})
            return
        if u.path == "/api/health":
            json_response(self,200,{"ok":True,"mode":"local-companion","sqlite":str(DB),"projects":str(PROJECTS),"version":CAPABILITIES["version"],"workshopRelease":CAPABILITIES["workshopRelease"]})
            return
        if u.path == "/api/capabilities":
            json_response(self,200,CAPABILITIES)
            return
        if u.path == "/api/capability-registry":
            filters = []
            for value in q.get("filter", []):
                filters.extend(part for part in value.split(",") if part.strip())
            try:
                capability_inspection()
                registry = capability_registry()
                json_response(self, 200, {
                    "ok": True,
                    **registry.snapshot(),
                    "hardwareProfileHash": registry.profile["profileHash"],
                    "capabilities": registry.list(filters=filters, query=(q.get("query") or [""])[0]),
                })
            except CapabilityError as error:
                json_response(self, 400, {"ok": False, "code": error.code, "error": str(error)})
            return
        if u.path == "/api/capability-registry/recommend":
            try:
                capability_inspection()
                json_response(self, 200, {"ok": True, **capability_registry().recommend((q.get("request") or [""])[0])})
            except CapabilityError as error:
                json_response(self, 400, {"ok": False, "code": error.code, "error": str(error)})
            return
        if u.path == "/api/hardware-profile":
            json_response(self, 200, {"ok": True, **capability_registry().profile})
            return
        if u.path == "/api/capability-inspections":
            if self._principal().role != OWNER:
                json_response(self, 403, {"ok": False, "code": "owner_required", "error": "OWNER authority is required"}); return
            json_response(self, 200, capability_inspection().list((q.get("capabilityId") or [""])[0]))
            return
        if u.path == "/api/capability-inspections/authority-template":
            if self._principal().role != OWNER:
                json_response(self, 403, {"ok": False, "code": "owner_required", "error": "OWNER authority is required"}); return
            json_response(self, 200, {"ok": True, "authority": static_only_authority(capability_inspection().temp_root)})
            return
        inspection_parts = [part for part in u.path.split("/") if part]
        if len(inspection_parts) == 3 and inspection_parts[:2] == ["api", "capability-inspections"]:
            if self._principal().role != OWNER:
                json_response(self, 403, {"ok": False, "code": "owner_required", "error": "OWNER authority is required"}); return
            try: json_response(self, 200, capability_inspection().get(inspection_parts[2]))
            except InspectionError as error: json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})
            return
        if u.path == "/api/agent-skills":
            json_response(self, 200, {"ok": True, **discover_skills([ROOT / "skills"])})
            return
        if u.path == "/api/mcp-catalog":
            json_response(self, 200, {"ok": True, **mcp_catalog().list()})
            return
        if u.path == "/api/media-capabilities":
            result = media_workspace().capabilities()
            result["videoRuntime"] = video_workstation().runtime_status(verify=(q.get("verify") or [""])[0].lower() in {"1", "true", "yes"})
            json_response(self, 200, result)
            return
        if u.path.startswith("/api/video-renders/"):
            try:
                path, content_type = video_workstation().render_asset(u.path.rsplit("/", 1)[-1])
                size = path.stat().st_size
                self.send_response(200); self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(size)); self.send_header("Cache-Control", "private, no-store")
                self.send_header("Content-Disposition", f'inline; filename="{path.name}"')
                self.end_headers()
                with path.open("rb") as source:
                    while chunk := source.read(1024 * 1024):
                        self.wfile.write(chunk)
            except VideoWorkstationError as error:
                json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})
            return
        if u.path.startswith("/api/video-workstation/projects/"):
            try:
                project_id = u.path.split("/")[4]
                json_response(self, 200, video_workstation().summary(project_id))
            except VideoWorkstationError as error:
                json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})
            return
        if u.path.startswith("/api/media-assets/"):
            try:
                path, content_type = media_workspace().asset(u.path.rsplit("/", 1)[-1])
                body = path.read_bytes()
                self.send_response(200); self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "private, no-store")
                self.end_headers(); self.wfile.write(body)
            except MediaWorkspaceError as error:
                json_response(self, error.status, {"ok": False, "error": str(error)})
            return
        background_parts = [part for part in u.path.split("/") if part]
        if u.path == "/api/background-removal/health":
            try:
                verify = (q.get("verify") or [""])[0].strip().lower() in {"1", "true", "yes"}
                json_response(self, 200, background_removal().health(verify_files=verify))
            except BackgroundRemovalError as error:
                json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})
            return
        if len(background_parts) == 5 and background_parts[:3] == ["api", "background-removal", "projects"] and background_parts[4] == "proposals":
            try:
                json_response(self, 200, background_removal().list_proposals(background_parts[3]))
            except BackgroundRemovalError as error:
                json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})
            return
        if len(background_parts) == 7 and background_parts[:3] == ["api", "background-removal", "projects"] and background_parts[4] == "proposals" and background_parts[6] == "preview":
            try:
                path = background_removal().preview(background_parts[3], background_parts[5])
                body = path.read_bytes()
                self.send_response(200); self.send_header("Content-Type", "image/png")
                self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "private, no-store")
                self.end_headers(); self.wfile.write(body)
            except BackgroundRemovalError as error:
                json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})
            return
        if u.path.startswith("/api/media-workspace/projects/"):
            try:
                project_id = u.path.split("/")[4]
                json_response(self, 200, media_workspace().summary(project_id))
            except MediaWorkspaceError as error:
                json_response(self, error.status, {"ok": False, "error": str(error)})
            return
        if u.path == "/api/security-policy":
            json_response(self,200,SECURITY_POLICY)
            return
        if u.path == "/api/local-ai/status":
            try:
                verify = (q.get("verify") or [""])[0].strip().lower() in {"1", "true", "yes"}
                json_response(self, 200, model_bay().status(verify_hash=verify))
            except ModelBayError as error:
                model_bay_error_response(self, error)
            return
        local_worker_parts = [part for part in u.path.split("/") if part]
        if u.path == "/api/local-workers":
            try:
                json_response(self, 200, local_worker_kit().list_workers())
            except LocalWorkerError as error:
                local_worker_error_response(self, error)
            return
        if (
            len(local_worker_parts) == 3
            and local_worker_parts[:2] == ["api", "local-workers"]
        ):
            try:
                json_response(
                    self,
                    200,
                    local_worker_kit().inspect_worker(local_worker_parts[2]),
                )
            except LocalWorkerError as error:
                local_worker_error_response(self, error)
            return
        if u.path == "/api/local-worker-sources":
            try:
                project_id = (q.get("projectId") or [""])[0].strip()
                json_response(
                    self,
                    200,
                    local_worker_kit().list_sources(project_id),
                )
            except LocalWorkerError as error:
                local_worker_error_response(self, error)
            return
        if u.path == "/api/local-worker-jobs":
            try:
                project_id = (q.get("projectId") or [""])[0].strip() or None
                raw_limit = (q.get("limit") or ["100"])[0]
                try:
                    limit = int(raw_limit)
                except ValueError as exc:
                    raise LocalWorkerError(
                        "limit_invalid",
                        "Job history limit must be an integer",
                    ) from exc
                json_response(
                    self,
                    200,
                    local_worker_kit().list_jobs(project_id, limit=limit),
                )
            except LocalWorkerError as error:
                local_worker_error_response(self, error)
            return
        if (
            len(local_worker_parts) == 3
            and local_worker_parts[:2] == ["api", "local-worker-jobs"]
        ):
            try:
                json_response(
                    self,
                    200,
                    local_worker_kit().get_job(local_worker_parts[2]),
                )
            except LocalWorkerError as error:
                local_worker_error_response(self, error)
            return
        talk_parts = [part for part in u.path.split("/") if part]
        if u.path == "/api/talk/voice-capabilities":
            json_response(self, 200, TalkRoom.voice_contract())
            return
        if u.path == "/api/talk-sessions":
            try:
                project_id = (q.get("projectId") or [""])[0].strip()
                if not project_id:
                    raise TalkRoomError("project_id_required", "Choose a project")
                search = (q.get("q") or [""])[0]
                json_response(self, 200, talk_room().list_sessions(project_id, search))
            except TalkRoomError as error:
                talk_error_response(self, error)
            return
        if len(talk_parts) == 3 and talk_parts[:2] == ["api", "talk-sessions"]:
            try:
                json_response(self, 200, talk_room().get_session(talk_parts[2]))
            except TalkRoomError as error:
                talk_error_response(self, error)
            return
        if (
            len(talk_parts) == 4
            and talk_parts[:2] == ["api", "talk-sessions"]
            and talk_parts[3] == "compare"
        ):
            try:
                json_response(
                    self,
                    200,
                    talk_room().compare_versions(
                        talk_parts[2],
                        (q.get("left") or [""])[0],
                        (q.get("right") or [""])[0],
                    ),
                )
            except TalkRoomError as error:
                talk_error_response(self, error)
            return
        write_parts = [part for part in u.path.split("/") if part]
        if u.path == "/api/write-projects":
            try:
                project_id = (q.get("projectId") or [""])[0].strip()
                if not project_id:
                    raise WriteRoomError("project_id_required", "Choose a project")
                search = (q.get("q") or [""])[0]
                json_response(self, 200, write_room().list_documents(project_id, search))
            except WriteRoomError as error:
                write_error_response(self, error)
            return
        if len(write_parts) == 3 and write_parts[:2] == ["api", "write-projects"]:
            try:
                json_response(self, 200, write_room().get_document(write_parts[2]))
            except WriteRoomError as error:
                write_error_response(self, error)
            return
        if (
            len(write_parts) == 4
            and write_parts[:2] == ["api", "write-projects"]
            and write_parts[3] == "compare"
        ):
            try:
                json_response(
                    self,
                    200,
                    write_room().compare_versions(
                        write_parts[2],
                        (q.get("left") or [""])[0],
                        (q.get("right") or [""])[0],
                    ),
                )
            except WriteRoomError as error:
                write_error_response(self, error)
            return
        music_render_parts = [part for part in u.path.split("/") if part]
        if len(music_render_parts) == 3 and music_render_parts[:2] == ["api", "music-renders"]:
            artifact_id = music_render_parts[2]
            con = connect()
            row = con.execute(
                "SELECT project_id,kind,path FROM artifacts WHERE id=?",
                (artifact_id,),
            ).fetchone()
            con.close()
            if not row or row["kind"] != "music-render":
                json_response(self, 404, {"error": "music render not found"})
                return
            try:
                render_path = _music_render_path(row["project_id"], row["path"])
            except ValueError as exc:
                json_response(self, 409, {"error": str(exc)})
                return
            if not render_path.is_file():
                json_response(self, 404, {"error": "music render file is unavailable"})
                return
            body = render_path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "private, no-store")
            self.send_header("Content-Disposition", f'inline; filename="{render_path.name}"')
            self.end_headers()
            self.wfile.write(body)
            return
        music_loop_parts = [part for part in u.path.split("/") if part]
        if len(music_loop_parts) == 3 and music_loop_parts[:2] == ["api", "music-loops"]:
            artifact_id = music_loop_parts[2]
            con = connect()
            row = con.execute(
                "SELECT project_id,kind,path,sha256 FROM artifacts WHERE id=?",
                (artifact_id,),
            ).fetchone()
            con.close()
            if not row or row["kind"] != "music-loop":
                json_response(self, 404, {"error": "music loop not found"})
                return
            try:
                loop_path = _music_loop_path(row["project_id"], row["path"])
            except ValueError as exc:
                json_response(self, 409, {"error": str(exc)})
                return
            if not loop_path.is_file():
                json_response(self, 404, {"error": "music loop file is unavailable"})
                return
            body = loop_path.read_bytes()
            if hashlib.sha256(body).hexdigest() != row["sha256"]:
                json_response(self, 409, {"error": "Music loop hash no longer matches its registered source"})
                return
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "private, no-store")
            self.send_header("Content-Disposition", f'inline; filename="{loop_path.name}"')
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/api/projects":
            con=connect(); rows=con.execute("SELECT * FROM projects ORDER BY updated_at DESC").fetchall(); con.close()
            json_response(self,200,[dict(r) for r in rows]); return
        if u.path.startswith("/api/projects/") and u.path.endswith("/artifacts"):
            pid=u.path.split("/")[3]; search=(q.get("q") or [""])[0].strip()
            con=connect()
            if search:
                rows=con.execute("""SELECT a.* FROM artifacts a JOIN artifact_search s ON s.id=a.id
                                    WHERE a.project_id=? AND artifact_search MATCH ?
                                    ORDER BY a.updated_at DESC""",(pid,search)).fetchall()
            else:
                rows=con.execute("SELECT * FROM artifacts WHERE project_id=? ORDER BY updated_at DESC",(pid,)).fetchall()
            con.close()
            out=[]
            for r in rows:
                d=dict(r); d["payload"]=json.loads(d["payload"]); out.append(d)
            json_response(self,200,out); return
        if u.path.startswith("/api/projects/") and u.path.endswith("/flashriver-review"):
            pid=u.path.split("/")[3]
            con=connect()
            project=con.execute("SELECT * FROM projects WHERE id=?",(pid,)).fetchone()
            rows=con.execute("""SELECT a.*, COALESCE(r.status,'unreviewed') review_status,
                                      COALESCE(r.notes,'') review_notes, r.reviewed_at
                               FROM artifacts a LEFT JOIN artifact_reviews r ON r.artifact_id=a.id
                               WHERE a.project_id=? ORDER BY a.kind,a.title""",(pid,)).fetchall()
            receipts=con.execute("SELECT * FROM receipts WHERE project_id=? ORDER BY created_at DESC LIMIT 100",(pid,)).fetchall()
            con.close()
            artifacts=[]
            for row in rows:
                d=dict(row); d["payload"]=json.loads(d["payload"]); artifacts.append(d)
            manifest=next((a for a in artifacts if a["kind"]=="flashriver-intake-manifest"),None)
            json_response(self,200,{"project":dict(project) if project else None,"manifest":manifest,"artifacts":artifacts,"duplicateGroups":duplicate_artifact_groups(artifacts),"receipts":[dict(r) for r in receipts]}); return
        if u.path.startswith("/api/projects/") and u.path.endswith("/sessions/latest"):
            pid=u.path.split("/")[3]; con=connect()
            r=con.execute("SELECT * FROM sessions WHERE project_id=? ORDER BY created_at DESC LIMIT 1",(pid,)).fetchone(); con.close()
            json_response(self,200,dict(r) if r else None); return
        if u.path.startswith("/api/projects/") and u.path.endswith("/receipts"):
            pid=u.path.split("/")[3]; con=connect()
            rows=con.execute("SELECT * FROM receipts WHERE project_id=? ORDER BY created_at DESC LIMIT 200",(pid,)).fetchall(); con.close()
            json_response(self,200,[dict(r) for r in rows]); return
        if u.path.startswith("/api/files"):
            rel=(q.get("path") or [""])[0]
            p=(PROJECTS/rel).resolve()
            if PROJECTS.resolve() not in p.parents:
                json_response(self,400,{"error":"unsafe path"}); return
            if not p.exists() or not p.is_file():
                json_response(self,404,{"error":"not found"}); return
            try:
                text=p.read_text(encoding="utf-8")
                json_response(self,200,{"path":rel,"content":text})
            except UnicodeDecodeError:
                json_response(self,415,{"error":"not text"}); return
            return
        if u.path == "/api/tree":
            pid=(q.get("projectId") or [""])[0]
            p=project_dir(pid)
            files=[]
            for f in p.rglob("*"):
                if f.is_file():
                    files.append(str(f.relative_to(PROJECTS)).replace("\\","/"))
            json_response(self,200,files); return
        if u.path == "/api/workers":
            try:
                json_response(self,200,worker_harness().list_workers())
            except (HarnessError, PromotionError) as error:
                worker_error_response(self,error)
            return
        if u.path == "/api/artifacts/inspection-options":
            try:
                project_id=(q.get("projectId") or [None])[0]
                json_response(self,200,artifact_inspection_options(project_id))
            except (HarnessError, PromotionError) as error:
                worker_error_response(self,error)
            return
        artifact_parts = [part for part in u.path.split("/") if part]
        if len(artifact_parts) == 4 and artifact_parts[:2] == ["api", "artifacts"] and artifact_parts[3] == "inspections":
            try:
                json_response(self,200,worker_harness().artifact_inspections(artifact_parts[2]))
            except (HarnessError, PromotionError) as error:
                worker_error_response(self,error)
            return
        if u.path == "/api/candidates":
            try:
                json_response(self,200,worker_harness().list_candidates())
            except (HarnessError, PromotionError) as error:
                worker_error_response(self,error)
            return
        candidate_parts = [part for part in u.path.split("/") if part]
        if len(candidate_parts) == 3 and candidate_parts[:2] == ["api", "candidates"]:
            try:
                json_response(self,200,worker_harness().get_candidate(candidate_parts[2]))
            except (HarnessError, PromotionError) as error:
                worker_error_response(self,error)
            return
        if u.path == "/api/modules":
            p=APP/"modules"/"modules.json"
            json_response(self,200,json.loads(p.read_text(encoding="utf-8"))); return
        if u.path == "/api/jobs":
            json_response(
                self,
                410,
                {
                    "ok": False,
                    "code": "legacy_job_api_retired",
                    "error": "Use the bounded local worker job history API.",
                },
            )
            return
        super().do_GET()

    def do_POST(self):
        if not self._authorize_or_deny():
            return
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/visitor-bench/submissions":
            self._do_visitor_bench_create()
            return
        if path.startswith("/api/visitor-bench/submissions/") and path.endswith("/promote"):
            with DB_WRITE_LOCK:
                self._do_visitor_bench_promote(path.split("/")[-2])
            return
        if urllib.parse.urlparse(self.path).path.startswith("/api/local-ai/"):
            self._do_local_ai_POST()
            return
        with DB_WRITE_LOCK:
            self._do_POST()

    def _do_visitor_bench_create(self):
        principal = self._principal()
        if principal.role != GUEST_CREATOR:
            json_response(self, 403, {"ok": False, "code": "guest_creator_required", "error": "GUEST_CREATOR authority is required"})
            return
        try:
            value = visitor_bench_body_json(self)
            json_response(self, 201, VisitorBench(VISITOR_BENCH_DB).create(principal.identity, value))
        except VisitorBenchError as error:
            json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})

    def _do_visitor_bench_promote(self, submission_id: str):
        principal = self._principal()
        if principal.role != OWNER:
            json_response(self, 403, {"ok": False, "code": "owner_required", "error": "OWNER authority is required"})
            return
        try:
            value = visitor_bench_body_json(self)
            project_id = str(value.get("projectId", "")).strip()
            bench = VisitorBench(VISITOR_BENCH_DB)
            submission = bench.get(submission_id, owner=True)
            con = connect()
            if not con.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
                con.close()
                raise VisitorBenchError("promotion_project_invalid", "A real owner project is required")
            artifact_id = str(uuid.uuid4())
            receipt_id = str(uuid.uuid4())
            now = utc()
            payload = {
                "schemaVersion": "visitor-bench-promotion-v1",
                "sourceSubmissionId": submission_id,
                "guestIdentity": submission["guest_identity"],
                "originatingRoom": submission["room"],
                "operation": submission["operation"],
                "sourceContentSha256": submission["content_sha256"],
                "content": submission["content"],
                "inactive": True,
            }
            con.execute(
                "INSERT INTO artifacts(id,project_id,kind,title,path,payload,authority_state,sha256,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (artifact_id, project_id, "visitor-bench-import", submission["title"], "", json.dumps(payload, ensure_ascii=False), "DRAFT", submission["content_sha256"], now, now),
            )
            index_artifact(con, {"id": artifact_id, "projectId": project_id, "title": submission["title"], "kind": "visitor-bench-import", "payload": payload})
            con.execute(
                "INSERT INTO receipts VALUES(?,?,?,?,?,?)",
                (receipt_id, project_id, "visitor_bench.promoted", principal.identity, json.dumps({"submissionId": submission_id, "artifactId": artifact_id, "guestIdentity": submission["guest_identity"], "sourceContentSha256": submission["content_sha256"]}, ensure_ascii=False), now),
            )
            con.commit()
            con.close()
            try:
                bench.record_promotion(submission_id, artifact_id, receipt_id, principal.identity)
            except Exception:
                rollback = connect()
                rollback.execute("DELETE FROM artifact_search WHERE id=?", (artifact_id,))
                rollback.execute("DELETE FROM artifacts WHERE id=?", (artifact_id,))
                rollback.execute("DELETE FROM receipts WHERE id=?", (receipt_id,))
                rollback.commit()
                rollback.close()
                raise
            json_response(self, 201, {"ok": True, "artifactId": artifact_id, "receiptId": receipt_id, "authorityState": "DRAFT"})
        except VisitorBenchError as error:
            json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})

    def _do_local_ai_POST(self):
        path = urllib.parse.urlparse(self.path).path
        try:
            value = local_worker_body_json(self)
            if path == "/api/local-ai/runtime/start":
                local_worker_fields(value, set())
                result = model_bay().start()
            elif path == "/api/local-ai/runtime/stop":
                local_worker_fields(value, set())
                result = model_bay().stop()
            elif path == "/api/local-ai/health-test":
                local_worker_fields(value, set())
                result = model_bay().health_test()
            elif path == "/api/local-ai/settings":
                local_worker_fields(value, {"localAiEnabled"})
                result = model_bay().update_settings(value)
            else:
                raise ModelBayError("local_ai_action_not_found", "That Local AI action does not exist", status=404)
            json_response(self, 200, result)
        except LocalWorkerError as error:
            local_worker_error_response(self, error)
        except ModelBayError as error:
            model_bay_error_response(self, error)

    def _do_POST(self):
        u=urllib.parse.urlparse(self.path)
        inspection_parts = [part for part in u.path.split("/") if part]
        if u.path == "/api/capability-inspections/plan" or (len(inspection_parts) == 4 and inspection_parts[:2] == ["api", "capability-inspections"]):
            if self._principal().role != OWNER:
                json_response(self, 403, {"ok": False, "code": "owner_required", "error": "OWNER authority is required"}); return
            try:
                value = local_worker_body_json(self)
                actor = self._principal().identity or "local-owner"
                if u.path == "/api/capability-inspections/plan":
                    result = capability_inspection().create_plan(value, actor=actor); status = 201
                else:
                    inspection_id, action = inspection_parts[2], inspection_parts[3]
                    if action == "plan-decision": result = capability_inspection().decide_plan(inspection_id, str(value.get("decision") or ""), str(value.get("note") or ""), actor=actor)
                    elif action == "execute": result = capability_inspection().execute(inspection_id, actor=actor)
                    elif action == "owner-decision": result = capability_inspection().owner_decision(inspection_id, str(value.get("decision") or ""), str(value.get("note") or ""), str(value.get("evidenceHash") or ""), actor=actor)
                    else: raise InspectionError("inspection_action_not_found", "Capability inspection action was not found", status=404)
                    status = 200
                json_response(self, status, result)
            except LocalWorkerError as error:
                local_worker_error_response(self, error)
            except InspectionError as error:
                json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})
            return
        media_parts = [part for part in u.path.split("/") if part]
        if len(media_parts) == 5 and media_parts[:3] == ["api", "background-removal", "projects"] and media_parts[4] == "proposals":
            try:
                result = background_removal().create_proposal(media_parts[3], background_removal_body_json(self))
                json_response(self, 201, result)
            except BackgroundRemovalError as error:
                json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})
            return
        if len(media_parts) == 7 and media_parts[:3] == ["api", "background-removal", "projects"] and media_parts[4] == "proposals" and media_parts[6] == "decision":
            try:
                value = background_removal_body_json(self)
                result = background_removal().decide(media_parts[3], media_parts[5], str(value.get("decision") or ""), str(value.get("title") or ""))
                json_response(self, 200, result)
            except BackgroundRemovalError as error:
                json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})
            return
        if len(media_parts) >= 5 and media_parts[:3] == ["api", "video-workstation", "projects"]:
            project_id, action = media_parts[3], media_parts[4]
            try:
                value = body_json(self)
                if action == "compositions":
                    result = video_workstation().save_composition(project_id, value)
                    status = 201
                elif action == "renders":
                    result = video_workstation().render(project_id, str(value.get("compositionId", "")))
                    status = 201
                else:
                    raise VideoWorkstationError("Unknown Video workstation action", 404)
                json_response(self, status, result)
            except VideoWorkstationError as error:
                json_response(self, error.status, {"ok": False, "code": error.code, "error": str(error)})
            return
        if len(media_parts) >= 5 and media_parts[:3] == ["api", "media-workspace", "projects"]:
            project_id, action = media_parts[3], media_parts[4]
            try:
                if action in {"image-assets", "background-composites"}:
                    try: length = int(self.headers.get("Content-Length", "0"))
                    except ValueError as exc: raise MediaWorkspaceError("Invalid image Content-Length") from exc
                    if length < 1 or length > MEDIA_MAX_BYTES: raise MediaWorkspaceError("Image exceeds the 12 MiB media limit", 413)
                    raw = self.rfile.read(length)
                    if action == "image-assets":
                        result = media_workspace().save_image(
                            project_id,
                            self.headers.get("X-TWIS-Title", "")[:300],
                            self.headers.get("Content-Type", "").split(";",1)[0].strip().lower(),
                            raw,
                            int(self.headers.get("X-TWIS-Width", "0")),
                            int(self.headers.get("X-TWIS-Height", "0")),
                            self.headers.get("X-TWIS-Source-Artifact", "")[:100],
                            self.headers.get("X-TWIS-Original-SHA256", "")[:64],
                        )
                    else:
                        if self.headers.get("Content-Type", "").split(";",1)[0].strip().lower() != "image/png":
                            raise MediaWorkspaceError("Background composites must be submitted as PNG")
                        result = media_workspace().save_background_composite(
                            project_id,
                            self.headers.get("X-TWIS-Title", "")[:300],
                            raw,
                            int(self.headers.get("X-TWIS-Width", "0")),
                            int(self.headers.get("X-TWIS-Height", "0")),
                            self.headers.get("X-TWIS-Source-Artifact", "")[:100],
                            self.headers.get("X-TWIS-Source-SHA256", "")[:64],
                            self.headers.get("X-TWIS-Background-Mode", "")[:20],
                            self.headers.get("X-TWIS-Background-Color-A", "")[:7],
                            self.headers.get("X-TWIS-Background-Color-B", "")[:7],
                            self.headers.get("X-TWIS-Background-Direction", "vertical")[:20],
                            self.headers.get("X-TWIS-Background-Artifact", "")[:100],
                            self.headers.get("X-TWIS-Background-SHA256", "")[:64],
                        )
                else:
                    value = body_json(self)
                    if action == "scenes": result = media_workspace().create_scene(project_id, str(value.get("title", "")), str(value.get("description", "")))
                    elif action == "routes": result = media_workspace().create_route(project_id, str(value.get("sourceArtifactId", "")), str(value.get("targetRoom", "")), str(value.get("sceneId", "")), str(value.get("notes", "")))
                    elif action == "storyboard-items": result = media_workspace().create_storyboard_item(project_id, str(value.get("sceneId", "")), str(value.get("imageId", "")), float(value.get("durationSeconds", 4)), str(value.get("transitionNotes", "")))
                    elif action == "storyboard-order": result = media_workspace().reorder_storyboard_item(project_id, str(value.get("itemId", "")), str(value.get("direction", "")))
                    elif action == "storyboard-remove": result = media_workspace().remove_storyboard_item(project_id, str(value.get("itemId", "")))
                    else: raise MediaWorkspaceError("Unknown media action", 404)
                json_response(self, 201, result)
            except (MediaWorkspaceError, ValueError) as error:
                json_response(self, getattr(error, "status", 400), {"ok": False, "error": str(error)})
            return
        local_worker_parts=[part for part in u.path.split("/") if part]
        try:
            if u.path == "/api/local-worker-jobs/plan":
                x=local_worker_body_json(self)
                local_worker_fields(
                    x,
                    {
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
                    },
                )
                json_response(self, 201, local_worker_kit().create_plan(x))
                return
            if (
                len(local_worker_parts) == 4
                and local_worker_parts[:2] == ["api", "local-worker-jobs"]
            ):
                job_id=local_worker_parts[2]
                action=local_worker_parts[3]
                x=local_worker_body_json(self)
                actor=str(x.get("actor") or "local-owner").strip()[:100]
                kit=local_worker_kit()
                if action == "plan-decision":
                    local_worker_fields(x, {"decision", "note", "actor"})
                    value=kit.decide_plan(
                        job_id,
                        x.get("decision"),
                        x.get("note"),
                        actor=actor,
                    )
                elif action == "execute":
                    local_worker_fields(x, {"actor"})
                    value=kit.execute(job_id, actor=actor)
                elif action == "cancel":
                    local_worker_fields(x, {"actor"})
                    value=kit.cancel(job_id, actor=actor)
                elif action == "recover":
                    local_worker_fields(x, {"actor"})
                    value=kit.recover(job_id, actor=actor)
                elif action == "result-decision":
                    local_worker_fields(x, {"decision", "note", "actor"})
                    value=kit.decide_result(
                        job_id,
                        x.get("decision"),
                        x.get("note"),
                        actor=actor,
                    )
                elif action == "rollback":
                    local_worker_fields(x, {"confirmed", "actor"})
                    value=kit.rollback(
                        job_id,
                        confirmed=x.get("confirmed"),
                        actor=actor,
                    )
                elif action == "save-draft":
                    local_worker_fields(x, {"confirmed", "actor"})
                    value=kit.save_builder_draft(job_id, confirmed=x.get("confirmed"), actor=actor)
                elif action == "export":
                    local_worker_fields(x, {"format", "includeProvenance", "confirmed", "actor"})
                    value=kit.export_builder_result(job_id, x.get("format"), include_provenance=x.get("includeProvenance"), confirmed=x.get("confirmed"), actor=actor)
                elif action == "delete":
                    local_worker_fields(x, {"confirmed", "actor"})
                    value=kit.delete_history(
                        job_id,
                        confirmed=x.get("confirmed"),
                        actor=actor,
                    )
                else:
                    raise LocalWorkerError(
                        "worker_action_not_found",
                        "That local worker action does not exist",
                        status=404,
                    )
                json_response(self, 200, value)
                return
        except LocalWorkerError as error:
            local_worker_error_response(self, error)
            return
        talk_parts=[part for part in u.path.split("/") if part]
        try:
            if u.path == "/api/talk-sessions":
                x=talk_body_json(self)
                json_response(
                    self,
                    201,
                    talk_room().create_session(
                        str(x.get("projectId") or ""),
                        x.get("title"),
                        x.get("initialContent", ""),
                        actor=str(x.get("actor") or "local-owner"),
                    ),
                )
                return
            if u.path == "/api/talk/commands":
                x=talk_body_json(self, limit=16 * 1024)
                if set(x)-{"command"}:
                    raise TalkRoomError(
                        "request_fields_invalid",
                        "Talk command accepts only command text",
                    )
                json_response(self, 200, talk_room().resolve_command(x.get("command")))
                return
            if len(talk_parts)==4 and talk_parts[:2]==["api","talk-sessions"]:
                artifact_id=talk_parts[2]
                action=talk_parts[3]
                x=talk_body_json(self)
                service=talk_room()
                if action=="recovery":
                    result=service.save_recovery(
                        artifact_id,
                        content=x.get("content", ""),
                        base_version=x.get("baseVersion"),
                        speaker=x.get("speaker", "owner"),
                        entry_type=x.get("entryType", "text"),
                    )
                elif action=="title":
                    result=service.rename_session(
                        artifact_id,
                        title=x.get("title"),
                        base_version=x.get("baseVersion"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif action=="entries":
                    result=service.append_entry(
                        artifact_id,
                        content=x.get("content", ""),
                        base_version=x.get("baseVersion"),
                        title=x.get("title"),
                        speaker=x.get("speaker", "owner"),
                        entry_type=x.get("entryType", "text"),
                        source=str(x.get("source") or "typed"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif action=="snapshot":
                    result=service.snapshot(
                        artifact_id,
                        base_version=x.get("baseVersion"),
                        label=x.get("label"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif action=="restore":
                    result=service.restore(
                        artifact_id,
                        target_version=x.get("targetVersion"),
                        base_version=x.get("baseVersion"),
                        confirmed=x.get("confirmed"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif action=="passages":
                    result=service.mark_passage(
                        artifact_id,
                        entry_id=x.get("entryId"),
                        start_offset=x.get("startOffset"),
                        end_offset=x.get("endOffset"),
                        label=x.get("label", ""),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif action=="exports":
                    result=service.export_session(
                        artifact_id,
                        format_name=x.get("format"),
                        include_provenance=x.get("includeProvenance"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif action=="transfers":
                    result=service.prepare_transfer(
                        artifact_id,
                        base_version=x.get("baseVersion"),
                        selection=x.get("selection"),
                        title=x.get("title"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif action=="inspections":
                    result=service.inspect_entry(
                        artifact_id,
                        entry_id=x.get("entryId"),
                        filename=x.get("filename"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                else:
                    raise TalkRoomError(
                        "talk_action_not_found", "Talk action not found", status=404
                    )
                json_response(self, 200, result)
                return
            if (
                len(talk_parts)==4
                and talk_parts[:2]==["api","talk-restore-operations"]
                and talk_parts[3]=="rollback"
            ):
                x=talk_body_json(self)
                json_response(
                    self,
                    200,
                    talk_room().rollback_restore(
                        talk_parts[2],
                        confirmed=x.get("confirmed"),
                        actor=str(x.get("actor") or "local-owner"),
                    ),
                )
                return
            if len(talk_parts)==4 and talk_parts[:2]==["api","talk-transfers"]:
                x=talk_body_json(self)
                if talk_parts[3]=="decision":
                    result=talk_room().decide_transfer(
                        talk_parts[2],
                        decision=x.get("decision"),
                        note=x.get("note", ""),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif talk_parts[3]=="rollback":
                    result=talk_room().rollback_transfer(
                        talk_parts[2],
                        confirmed=x.get("confirmed"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                else:
                    raise TalkRoomError(
                        "talk_transfer_action_not_found",
                        "Talk-to-Write action not found",
                        status=404,
                    )
                json_response(self, 200, result)
                return
        except TalkRoomError as error:
            talk_error_response(self,error)
            return
        write_parts=[part for part in u.path.split("/") if part]
        try:
            if u.path == "/api/write-projects":
                x=write_body_json(self)
                json_response(
                    self,
                    201,
                    write_room().create_document(
                        str(x.get("projectId") or ""),
                        x.get("title"),
                        x.get("content", ""),
                        actor=str(x.get("actor") or "local-owner"),
                    ),
                )
                return
            if len(write_parts)==4 and write_parts[:2]==["api","write-projects"]:
                artifact_id=write_parts[2]
                action=write_parts[3]
                x=write_body_json(self)
                service=write_room()
                if action=="recovery":
                    result=service.save_recovery(
                        artifact_id,
                        title=x.get("title"),
                        content=x.get("content", ""),
                        base_version=x.get("baseVersion"),
                    )
                elif action=="save":
                    result=service.save_document(
                        artifact_id,
                        title=x.get("title"),
                        content=x.get("content", ""),
                        base_version=x.get("baseVersion"),
                        cause=str(x.get("cause") or "manual"),
                        label=x.get("label", ""),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif action=="snapshot":
                    result=service.snapshot(
                        artifact_id,
                        title=x.get("title"),
                        content=x.get("content", ""),
                        base_version=x.get("baseVersion"),
                        label=x.get("label"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif action=="restore":
                    result=service.restore(
                        artifact_id,
                        target_version=x.get("targetVersion"),
                        base_version=x.get("baseVersion"),
                        confirmed=x.get("confirmed"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif action=="proposals":
                    result=service.create_proposal(
                        artifact_id,
                        action=x.get("action"),
                        command=x.get("command"),
                        base_version=x.get("baseVersion"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif action=="exports":
                    result=service.export_document(
                        artifact_id,
                        format_name=x.get("format"),
                        include_provenance=x.get("includeProvenance"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                else:
                    raise WriteRoomError("write_action_not_found", "Writing action not found", status=404)
                json_response(self,200,result)
                return
            if (
                len(write_parts)==4
                and write_parts[:2]==["api","write-restore-operations"]
                and write_parts[3]=="rollback"
            ):
                x=write_body_json(self)
                json_response(
                    self,
                    200,
                    write_room().rollback_restore(
                        write_parts[2],
                        confirmed=x.get("confirmed"),
                        actor=str(x.get("actor") or "local-owner"),
                    ),
                )
                return
            if len(write_parts)==4 and write_parts[:2]==["api","write-proposals"]:
                x=write_body_json(self)
                if write_parts[3]=="decision":
                    result=write_room().decide_proposal(
                        write_parts[2],
                        decision=x.get("decision"),
                        note=x.get("note", ""),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                elif write_parts[3]=="rollback":
                    result=write_room().rollback_proposal(
                        write_parts[2],
                        confirmed=x.get("confirmed"),
                        actor=str(x.get("actor") or "local-owner"),
                    )
                else:
                    raise WriteRoomError("proposal_action_not_found", "Proposal action not found", status=404)
                json_response(self,200,result)
                return
        except WriteRoomError as error:
            write_error_response(self,error)
            return
        if u.path == "/api/workers/validate":
            try:
                x=worker_body_json(self)
                if set(x)-{"card","workerId"}:
                    raise HarnessError("request_fields_invalid", "validation accepts only card and workerId")
                card=x.get("card")
                if card is not None and not isinstance(card,dict):
                    raise HarnessError("worker_card_invalid", "card must be a JSON object")
                worker_id=x.get("workerId") if isinstance(x.get("workerId"),str) else "reference-metadata-worker"
                json_response(self,200,worker_harness().validate_card(card,worker_id=worker_id))
            except (HarnessError, PromotionError) as error:
                worker_error_response(self,error)
            return
        worker_parts=[part for part in u.path.split("/") if part]
        if len(worker_parts)==4 and worker_parts[:2]==["api","workers"] and worker_parts[3] in {"plan","run"}:
            try:
                x=worker_body_json(self)
                harness=worker_harness()
                actor=x.get("actor") if isinstance(x.get("actor"),str) else ""
                if worker_parts[3]=="plan":
                    allowed_fields={"actor","artifactId"} if worker_parts[2]==INSPECTION_WORKER_ID else {"actor"}
                    if set(x)-allowed_fields:
                        raise HarnessError("request_fields_invalid", "plan request contains unsupported fields")
                    artifact=None
                    if worker_parts[2]==INSPECTION_WORKER_ID:
                        artifact_id=x.get("artifactId") if isinstance(x.get("artifactId"),str) else ""
                        artifact=resolve_inspection_artifact(artifact_id)
                    result=harness.plan(worker_id=worker_parts[2],actor=actor,artifact=artifact)
                else:
                    if set(x)-{"planId","actor"}:
                        raise HarnessError("request_fields_invalid", "run accepts only planId and actor")
                    plan_id=x.get("planId") if isinstance(x.get("planId"),str) else ""
                    result=harness.run(plan_id=plan_id,actor=actor,worker_id=worker_parts[2])
                json_response(self,200,result)
            except (HarnessError, PromotionError) as error:
                worker_error_response(self,error)
            return
        candidate_parts=[part for part in u.path.split("/") if part]
        candidate_actions={"approve","reject","activate","rollback"}
        if len(candidate_parts)==4 and candidate_parts[:2]==["api","candidates"] and candidate_parts[3] in candidate_actions:
            try:
                x=worker_body_json(self)
                harness=worker_harness()
                candidate_id=candidate_parts[2]
                action=candidate_parts[3]
                allowed={
                    "candidateHash","workspaceGeneration","actor","timestamp",
                    "sourceArtifactHash","workerCardHash","executionPlanHash",
                }
                if action in {"approve","reject"}:
                    allowed.add("note")
                if set(x)-allowed:
                    raise HarnessError("request_fields_invalid", "candidate action contains unsupported fields")
                context={
                    "candidate_hash": x.get("candidateHash"),
                    "workspace_generation": x.get("workspaceGeneration"),
                    "actor": x.get("actor"),
                    "timestamp": x.get("timestamp"),
                    "source_artifact_hash": x.get("sourceArtifactHash"),
                    "worker_card_hash": x.get("workerCardHash"),
                    "execution_plan_hash": x.get("executionPlanHash"),
                }
                if action in {"approve","reject"}:
                    context["decision"]="approve" if action=="approve" else "reject"
                    context["note"]=x.get("note", "")
                    result=harness.approve(candidate_id,context)
                elif action=="activate":
                    result=harness.activate(candidate_id,context)
                else:
                    result=harness.rollback(candidate_id,context)
                json_response(self,200,result)
            except (HarnessError, PromotionError) as error:
                worker_error_response(self,error)
            return
        if u.path == "/api/projects":
            x=body_json(self); pid=safe_id(x.get("id") or x.get("title") or str(uuid.uuid4())); now=utc()
            con=connect()
            con.execute("""INSERT INTO projects(id,title,description,next_action,created_at,updated_at)
                           VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                           title=excluded.title,description=excluded.description,next_action=excluded.next_action,updated_at=excluded.updated_at""",
                        (pid,x.get("title","Untitled"),x.get("description",""),x.get("nextAction",""),x.get("createdAt",now),now))
            add_receipt(con,pid,"project.upsert","human",x); con.commit(); con.close()
            pd=project_dir(pid)
            (pd/"project.json").write_text(json.dumps({"id":pid,"title":x.get("title","Untitled"),"description":x.get("description",""),"nextAction":x.get("nextAction",""),"updatedAt":now},indent=2),encoding="utf-8")
            json_response(self,200,{"ok":True,"id":pid}); return
        if u.path.startswith("/api/music-loops/"):
            pid = safe_id(u.path.rsplit("/", 1)[-1])
            con = connect()
            project = con.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone()
            if not project:
                con.close()
                json_response(self, 404, {"error": "project not found"})
                return
            try:
                raw = _music_loop_body(self)
                wav_evidence = _validate_music_wav(raw)
                title = urllib.parse.unquote(self.headers.get("X-TWIS-Title", "Imported music loop")).strip()[:160]
                try:
                    bpm = float(self.headers.get("X-TWIS-BPM", "0"))
                    bars = int(self.headers.get("X-TWIS-Bars", "0"))
                except ValueError as exc:
                    raise ValueError("Music loop BPM or bar count is invalid") from exc
                if not 30 <= bpm <= 300:
                    raise ValueError("Music loop BPM must be between 30 and 300")
                if bars not in {1, 2, 4, 8}:
                    raise ValueError("Music loop must be registered as 1, 2, 4, or 8 bars")
                expected_duration = bars * 4 * 60 / bpm
                duration = float(wav_evidence["durationSeconds"])
                grid_error = duration - expected_duration
                tolerance = max(0.05, expected_duration * 0.02)
                artifact_id = str(uuid.uuid4())
                stem = safe_id(title)[:80] or "music-loop"
                relative = f"media/audio/loops/{stem}-{artifact_id[:8]}.wav"
                loop_path = _music_loop_path(pid, relative)
                loop_path.write_bytes(raw)
                loop_sha = hashlib.sha256(raw).hexdigest()
                now = utc()
                payload = {
                    "schemaVersion": "music-loop-v1",
                    "bpm": bpm,
                    "bars": bars,
                    "durationSeconds": duration,
                    "expectedDurationSeconds": round(expected_duration, 6),
                    "gridErrorSeconds": round(grid_error, 6),
                    "gridAligned": abs(grid_error) <= tolerance,
                    "wavEvidence": wav_evidence,
                    "inactive": True,
                    "localOnly": True,
                }
                artifact = {
                    "id": artifact_id,
                    "projectId": pid,
                    "kind": "music-loop",
                    "title": title or "Imported music loop",
                    "path": relative,
                    "payload": payload,
                    "authorityState": "DRAFT",
                    "hash": loop_sha,
                    "createdAt": now,
                    "updatedAt": now,
                }
                save_artifact_row(con, artifact)
                add_receipt(
                    con,
                    pid,
                    "music.loop.imported",
                    "human",
                    {
                        "artifactId": artifact_id,
                        "sha256": loop_sha,
                        "bpm": bpm,
                        "bars": bars,
                        "durationSeconds": duration,
                        "gridAligned": payload["gridAligned"],
                    },
                )
                con.commit()
                con.close()
                json_response(self, 201, {"ok": True, "artifact": artifact})
                return
            except ValueError as exc:
                con.close()
                json_response(self, 400, {"error": str(exc)})
                return
        if u.path.startswith("/api/music-renders/"):
            pid = safe_id(u.path.rsplit("/", 1)[-1])
            con = connect()
            project = con.execute("SELECT id FROM projects WHERE id=?", (pid,)).fetchone()
            if not project:
                con.close()
                json_response(self, 404, {"error": "project not found"})
                return
            try:
                raw = _music_render_body(self)
                wav_evidence = _validate_music_wav(raw)
                title = urllib.parse.unquote(self.headers.get("X-TWIS-Title", "Music Studio render")).strip()[:160]
                parent_id = self.headers.get("X-TWIS-Parent-Artifact", "").strip()
                music_sha = self.headers.get("X-TWIS-Music-SHA256", "").strip().lower()
                if len(music_sha) != 64 or any(char not in "0123456789abcdef" for char in music_sha):
                    raise ValueError("Music state SHA-256 is invalid")
                parent = con.execute(
                    "SELECT id FROM artifacts WHERE id=? AND project_id=? AND kind='music'",
                    (parent_id, pid),
                ).fetchone()
                if not parent:
                    raise ValueError("Parent Music Studio artifact is not available in this project")
                encoded_evidence = self.headers.get("X-TWIS-Render-Evidence", "")
                if len(encoded_evidence) > 8192:
                    raise ValueError("Music render evidence header is too large")
                try:
                    client_evidence = json.loads(base64.b64decode(encoded_evidence, validate=True).decode("utf-8"))
                except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ValueError("Music render evidence is invalid") from exc
                if not isinstance(client_evidence, dict) or client_evidence.get("header") != "RIFF" or not client_evidence.get("nonSilent"):
                    raise ValueError("Music render evidence does not prove a non-silent RIFF render")
                artifact_id = str(uuid.uuid4())
                stem = safe_id(title)[:80] or "music-studio-render"
                relative = f"exports/music/{stem}-{artifact_id[:8]}.wav"
                render_path = _music_render_path(pid, relative)
                render_path.write_bytes(raw)
                render_sha = hashlib.sha256(raw).hexdigest()
                now = utc()
                payload = {
                    "schemaVersion": "music-render-v1",
                    "parentArtifactId": parent_id,
                    "musicSha256": music_sha,
                    "renderEvidence": {**client_evidence, **wav_evidence},
                    "inactive": True,
                    "localOnly": True,
                }
                artifact = {
                    "id": artifact_id,
                    "projectId": pid,
                    "kind": "music-render",
                    "title": title or "Music Studio render",
                    "path": relative,
                    "payload": payload,
                    "authorityState": "DRAFT",
                    "hash": render_sha,
                    "createdAt": now,
                    "updatedAt": now,
                }
                save_artifact_row(con, artifact)
                add_receipt(
                    con,
                    pid,
                    "music.render.saved",
                    "human",
                    {"artifactId": artifact_id, "parentArtifactId": parent_id, "sha256": render_sha, "musicSha256": music_sha},
                )
                con.commit()
                con.close()
                json_response(self, 201, {"ok": True, "artifactId": artifact_id, "path": relative, "sha256": render_sha})
                return
            except ValueError as exc:
                con.close()
                json_response(self, 400, {"error": str(exc)})
                return
        if u.path.startswith("/api/projects/") and u.path.endswith("/artifacts"):
            pid=u.path.split("/")[3]; x=body_json(self); now=utc()
            aid=x.get("id") or str(uuid.uuid4()); payload=x.get("payload",{})
            rel=x.get("path","")
            sha=""
            if rel:
                p=(project_dir(pid)/rel).resolve()
                if p.exists() and p.is_file():
                    sha=hashlib.sha256(p.read_bytes()).hexdigest()
            a={"id":aid,"projectId":pid,"kind":x.get("kind","note"),"title":x.get("title","Untitled"),
               "path":rel,"payload":payload,"authorityState":x.get("authorityState","DRAFT"),
               "hash":sha,"createdAt":x.get("createdAt",now),"updatedAt":now}
            con=connect()
            con.execute("""INSERT INTO artifacts(id,project_id,kind,title,path,payload,authority_state,sha256,created_at,updated_at)
                           VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                           kind=excluded.kind,title=excluded.title,path=excluded.path,payload=excluded.payload,
                           authority_state=excluded.authority_state,sha256=excluded.sha256,updated_at=excluded.updated_at""",
                        (aid,pid,a["kind"],a["title"],rel,json.dumps(payload,ensure_ascii=False),a["authorityState"],sha,a["createdAt"],now))
            index_artifact(con,a); add_receipt(con,pid,"artifact.upsert","human-or-tool",a); con.commit(); con.close()
            json_response(self,200,{"ok":True,"artifact":a}); return
        if u.path.startswith("/api/projects/") and u.path.endswith("/sessions"):
            pid=u.path.split("/")[3]; x=body_json(self); sid=x.get("id") or str(uuid.uuid4()); now=utc()
            con=connect()
            con.execute("INSERT OR REPLACE INTO sessions VALUES(?,?,?,?,?,?,?,?)",
                        (sid,pid,x.get("room","home"),x.get("summary",""),json.dumps(x.get("activeConstraints",[]),ensure_ascii=False),x.get("nextAction",""),x.get("createdAt",now),x.get("closedAt")))
            add_receipt(con,pid,"session.save","human",x); con.commit(); con.close()
            json_response(self,200,{"ok":True,"id":sid}); return
        if u.path == "/api/files":
            x=body_json(self); rel=x.get("path",""); content=x.get("content","")
            p=(PROJECTS/rel).resolve()
            if PROJECTS.resolve() not in p.parents:
                json_response(self,400,{"error":"unsafe path"}); return
            p.parent.mkdir(parents=True,exist_ok=True); p.write_text(content,encoding="utf-8")
            json_response(self,200,{"ok":True,"path":rel}); return
        if u.path == "/api/import-flashriver":
            x=body_json(self)
            source=Path(str(x.get("path","")).strip().strip('"').strip("'")).expanduser().resolve()
            pid=safe_id(x.get("projectId") or "flashriver-source-archive")
            title=x.get("title") or "FlashRiver Source Archive"
            expected=x.get("expectedSha256") or x.get("expected_sha256") or ""
            pd=project_dir(pid)
            now=utc()
            result=stage_flashriver_package(zip_path=source, project_id=pid, project_root=pd, archive_root=SOURCE_ARCHIVES, expected_sha256=expected or None, now=now)
            con=connect()
            upsert_project(con, pid, title, "Private/local FlashRiver source archive intake", "Review imported source docs in My Work and Artifact Compass")
            for artifact in result["artifacts"]:
                save_artifact_row(con, artifact)
            add_receipt(con, pid, "flashriver.package.import", "human", {
                "sourcePath": str(source),
                "sha256": result["manifest"]["sha256"],
                "zipTest": result["manifest"]["zipTest"],
                "publicSafeDocsImported": result["manifest"]["publicSafeDocsImported"],
                "privateSourcesCopied": len(result["manifest"]["privateSourcesCopied"]),
                "visualsCopied": len(result["manifest"]["visualsCopied"]),
                "rawPackageCommittedToGitHub": False,
                "cloudflareAuthority": False
            })
            con.commit(); con.close()
            json_response(self,200,{"ok":True,"projectId":pid,"manifest":result["manifest"],"artifactCount":len(result["artifacts"])}); return
        if u.path.startswith("/api/artifacts/") and u.path.endswith("/review"):
            aid=u.path.split("/")[3]; x=body_json(self)
            allowed={"unreviewed","reviewed","current_candidate","superseded","conflicted","private_source","do_not_use"}
            status=x.get("status","unreviewed")
            if status not in allowed:
                json_response(self,400,{"error":"invalid review status"}); return
            notes=str(x.get("notes","")).strip(); now=utc(); con=connect()
            row=con.execute("SELECT project_id FROM artifacts WHERE id=?",(aid,)).fetchone()
            if not row:
                con.close(); json_response(self,404,{"error":"artifact not found"}); return
            reviewed_at=now if status!="unreviewed" else None
            con.execute("""INSERT INTO artifact_reviews(artifact_id,project_id,status,notes,reviewed_at,updated_at)
                           VALUES(?,?,?,?,?,?) ON CONFLICT(artifact_id) DO UPDATE SET
                           status=excluded.status,notes=excluded.notes,reviewed_at=excluded.reviewed_at,updated_at=excluded.updated_at""",
                        (aid,row["project_id"],status,notes,reviewed_at,now))
            add_receipt(con,row["project_id"],"artifact.review","human",{"artifactId":aid,"status":status,"notes":notes})
            con.commit(); con.close(); json_response(self,200,{"ok":True,"artifactId":aid,"status":status,"notes":notes,"reviewedAt":reviewed_at}); return
        if u.path == "/api/import-folder":
            x=body_json(self); source=Path(str(x.get("path","")).strip().strip('"').strip("'")).expanduser().resolve(); pid=safe_id(x.get("projectId","imported-project"))
            if not source.exists() or not source.is_dir():
                json_response(self,400,{"error":"folder not found"}); return
            dest=project_dir(pid)/"imports"/source.name; dest.parent.mkdir(exist_ok=True)
            if dest.exists(): shutil.rmtree(dest)
            shutil.copytree(source,dest)
            con=connect(); count=0
            for f in dest.rglob("*"):
                if f.is_file():
                    rel=str(f.relative_to(project_dir(pid))).replace("\\","/")
                    aid=str(uuid.uuid4()); now=utc(); kind=f.suffix.lower().lstrip(".") or "file"
                    sha=hashlib.sha256(f.read_bytes()).hexdigest()
                    payload={"size":f.stat().st_size,"sourcePath":str(source),"importedPath":rel}
                    con.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)",
                                (aid,pid,kind,f.name,rel,json.dumps(payload), "SOURCE",sha,now,now))
                    index_artifact(con,{"id":aid,"projectId":pid,"title":f.name,"kind":kind,"payload":payload})
                    count+=1
            add_receipt(con,pid,"folder.import","human",{"source":str(source),"count":count}); con.commit(); con.close()
            json_response(self,200,{"ok":True,"count":count,"destination":str(dest)}); return
        if u.path.startswith("/api/projects/") and u.path.endswith("/capsule"):
            pid=u.path.split("/")[3]; p=project_dir(pid); out=BACKUPS/f"{pid}-{int(time.time())}.zip"
            with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
                for f in p.rglob("*"):
                    if f.is_file(): z.write(f,f.relative_to(p.parent))
                con=connect()
                snapshot={
                    "project":[dict(r) for r in con.execute("SELECT * FROM projects WHERE id=?",(pid,)).fetchall()],
                    "artifacts":[dict(r) for r in con.execute("SELECT * FROM artifacts WHERE project_id=?",(pid,)).fetchall()],
                    "sessions":[dict(r) for r in con.execute("SELECT * FROM sessions WHERE project_id=?",(pid,)).fetchall()],
                    "receipts":[dict(r) for r in con.execute("SELECT * FROM receipts WHERE project_id=?",(pid,)).fetchall()]
                }; con.close()
                z.writestr(f"{pid}/database-snapshot.json",json.dumps(snapshot,indent=2))
            json_response(self,200,{"ok":True,"path":str(out)}); return
        if u.path == "/api/ai/chat":
            json_response(self,410,{"ok":False,"code":"arbitrary_ai_endpoint_retired","error":"Release 0.17 accepts only the registered localhost Model Bay route."}); return
        if u.path == "/api/jobs":
            json_response(
                self,
                410,
                {
                    "ok": False,
                    "code": "arbitrary_jobs_disabled",
                    "error": "Arbitrary job creation is disabled. Use one of the six fixed local workers.",
                },
            )
            return
        json_response(self,404,{"error":"not found"})

    def do_DELETE(self):
        if not self._authorize_or_deny():
            return
        with DB_WRITE_LOCK:
            self._do_DELETE()

    def _do_DELETE(self):
        u=urllib.parse.urlparse(self.path)
        talk_parts=[part for part in u.path.split("/") if part]
        if (
            len(talk_parts)==4
            and talk_parts[:2]==["api","talk-sessions"]
            and talk_parts[3]=="recovery"
        ):
            try:
                talk_body_json(self)
                json_response(self,200,talk_room().discard_recovery(talk_parts[2]))
            except TalkRoomError as error:
                talk_error_response(self,error)
            return
        write_parts=[part for part in u.path.split("/") if part]
        if (
            len(write_parts)==4
            and write_parts[:2]==["api","write-projects"]
            and write_parts[3]=="recovery"
        ):
            try:
                write_body_json(self)
                json_response(self,200,write_room().discard_recovery(write_parts[2]))
            except WriteRoomError as error:
                write_error_response(self,error)
            return
        if u.path.startswith("/api/artifacts/"):
            aid=u.path.rsplit("/",1)[-1]; con=connect()
            r=con.execute("SELECT project_id,kind,path,payload FROM artifacts WHERE id=?",(aid,)).fetchone()
            if r:
                add_receipt(con,r["project_id"],"artifact.delete","human",{"id":aid})
                if r["kind"]=="image" and json.loads(r["payload"] or "{}").get("schemaVersion")=="twis-media-asset-v1":
                    remaining=con.execute("SELECT count(1) FROM artifacts WHERE project_id=? AND path=? AND id<>?",(r["project_id"],r["path"],aid)).fetchone()[0]
                    if remaining==0:
                        image_root=(project_dir(r["project_id"])/"media"/"assets").resolve()
                        image_path=(project_dir(r["project_id"])/r["path"]).resolve()
                        if image_root in image_path.parents and image_path.is_file():
                            image_path.unlink()
                if r["kind"]=="music-render":
                    try:
                        render_path=_music_render_path(r["project_id"],r["path"])
                    except ValueError as exc:
                        con.close(); json_response(self,409,{"error":str(exc)}); return
                    if render_path.exists():
                        render_path.unlink()
                if r["kind"]=="music-loop":
                    try:
                        loop_path=_music_loop_path(r["project_id"],r["path"])
                    except ValueError as exc:
                        con.close(); json_response(self,409,{"error":str(exc)}); return
                    if loop_path.exists():
                        loop_path.unlink()
                if r["kind"]=="video-render":
                    remaining=con.execute("SELECT count(1) FROM artifacts WHERE project_id=? AND path=? AND id<>?",(r["project_id"],r["path"],aid)).fetchone()[0]
                    if remaining==0:
                        try:
                            video_workstation().delete_file_for_artifact(r["project_id"], r["kind"], r["path"])
                        except VideoWorkstationError as exc:
                            con.close(); json_response(self,exc.status,{"ok":False,"code":exc.code,"error":str(exc)}); return
                if r["kind"]=="document":
                    con.execute("DELETE FROM write_recovery_drafts WHERE artifact_id=?",(aid,))
                    con.execute("DELETE FROM write_proposals WHERE artifact_id=?",(aid,))
                    con.execute("DELETE FROM write_restore_operations WHERE artifact_id=?",(aid,))
                    con.execute("DELETE FROM write_exports WHERE artifact_id=?",(aid,))
                    con.execute("DELETE FROM write_versions WHERE artifact_id=?",(aid,))
                if r["kind"]=="conversation" and json.loads(r["payload"] or "{}").get("schemaVersion")=="talk-session-v1":
                    con.execute("DELETE FROM talk_recovery_drafts WHERE artifact_id=?",(aid,))
                    con.execute("DELETE FROM talk_restore_operations WHERE artifact_id=?",(aid,))
                    con.execute("DELETE FROM talk_passages WHERE artifact_id=?",(aid,))
                    con.execute("DELETE FROM talk_exports WHERE artifact_id=?",(aid,))
                    con.execute("DELETE FROM talk_transfers WHERE artifact_id=?",(aid,))
                    con.execute("DELETE FROM talk_inspections WHERE artifact_id=?",(aid,))
                    con.execute("DELETE FROM artifact_relationships WHERE source_artifact_id=? OR target_artifact_id=?",(aid,aid))
                    con.execute("DELETE FROM talk_versions WHERE artifact_id=?",(aid,))
                    con.execute("DELETE FROM talk_entries WHERE artifact_id=?",(aid,))
            con.execute("DELETE FROM artifact_relationships WHERE source_artifact_id=? OR target_artifact_id=?",(aid,aid))
            con.execute("DELETE FROM artifacts WHERE id=?",(aid,)); con.execute("DELETE FROM artifact_search WHERE id=?",(aid,)); con.commit(); con.close()
            json_response(self,200,{"ok":True}); return
        json_response(self,404,{"error":"not found"})

if __name__ == "__main__":
    connect().close()
    print(f"Twis Holo Workshop: http://{HOST}:{PORT}")
    print(f"Local projects: {PROJECTS}")
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
