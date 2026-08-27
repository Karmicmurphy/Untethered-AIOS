from __future__ import annotations

import hashlib
import json
import shutil
import uuid
import zipfile
from pathlib import Path
from typing import Any

CORE_HANDOFF_DOCS = {
    "README.md", "README_START_HERE.md", "AGENT.md", "SKILLS.md", "CONTEXT.md", "HARNESS.md",
    "BUILD_PLAN.md", "ENGINEERING.md", "HANDOFF.md", "API_PLAN.md", "MCP_PLAN.md",
    "SECURITY_MODULE.md", "ARTIFACT_COMPASS_20_PASS_SALVAGE.md", "POSSIBILITIES.md",
    "PRODUCT_SPEC.md", "PLATFORM_MATRIX.md", "APP_IDEAS_AND_BUILDS.md", "TOOL_REGISTRY_SCHEMA.md",
    "KNOWN_LIMITS.md", "NEXT_PROMPT_FOR_CODEX.md", "FULL_DEBUG_REPORT.md", "FULL_DEBUG_REPORT_POST_PATCH.md",
}

PUBLIC_SAFE_EXTENSIONS = {".md", ".txt", ".json", ".csv"}
PRIVATE_SOURCE_EXTENSIONS = {".zip", ".7z", ".rar", ".tar", ".gz", ".tgz"}
VISUAL_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}
MAX_PUBLIC_TEXT_BYTES = 512 * 1024


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _common_root(names: list[str]) -> str:
    roots = {n.split("/", 1)[0] for n in names if n and not n.endswith("/")}
    return next(iter(roots)) if len(roots) == 1 else ""


def _relative_member_name(name: str, root: str) -> str:
    if root and name.startswith(root + "/"):
        return name[len(root) + 1:]
    return name


def _safe_join(base: Path, rel: str) -> Path:
    rel_path = Path(*[p for p in Path(rel).parts if p not in {"", "."}])
    if any(part == ".." for part in rel_path.parts):
        raise ValueError(f"unsafe archive path: {rel}")
    target = (base / rel_path).resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError(f"unsafe archive path: {rel}") from exc
    return target


def _classify(relative_name: str, size: int) -> str:
    path = Path(relative_name)
    suffix = path.suffix.lower()
    base = path.name
    parts = set(path.parts)
    if base in CORE_HANDOFF_DOCS and suffix in PUBLIC_SAFE_EXTENSIONS and size <= MAX_PUBLIC_TEXT_BYTES:
        return "core-doc"
    if suffix in PUBLIC_SAFE_EXTENSIONS and size <= MAX_PUBLIC_TEXT_BYTES:
        return "support-doc"
    if suffix in PRIVATE_SOURCE_EXTENSIONS or "source_artifacts" in parts:
        return "private-source"
    if suffix in VISUAL_EXTENSIONS or "visuals" in parts:
        return "visual"
    return "inventory-only"


def inspect_flashriver_package(zip_path: Path, expected_sha256: str | None = None) -> dict[str, Any]:
    zip_path = zip_path.expanduser().resolve()
    if not zip_path.exists() or not zip_path.is_file():
        raise ValueError(f"FlashRiver package not found: {zip_path}")
    if zip_path.suffix.lower() != ".zip":
        raise ValueError("FlashRiver intake requires a .zip package")
    package_sha = sha256_file(zip_path)
    if expected_sha256 and package_sha.lower() != expected_sha256.lower():
        raise ValueError(f"SHA-256 mismatch: expected {expected_sha256}, got {package_sha}")
    with zipfile.ZipFile(zip_path) as z:
        bad_file = z.testzip()
        names = [n for n in z.namelist() if not n.endswith("/")]
        root = _common_root(names)
        entries: list[dict[str, Any]] = []
        counts: dict[str, int] = {}
        core_docs_found: list[str] = []
        for info in z.infolist():
            if info.is_dir():
                continue
            rel = _relative_member_name(info.filename, root)
            kind = _classify(rel, info.file_size)
            counts[kind] = counts.get(kind, 0) + 1
            if kind == "core-doc":
                core_docs_found.append(Path(rel).name)
            entries.append({"name": info.filename, "relativeName": rel, "size": info.file_size, "class": kind})
    return {
        "artifact": zip_path.name,
        "path": str(zip_path),
        "sha256": package_sha,
        "size": zip_path.stat().st_size,
        "zipTest": "PASS" if bad_file is None else "FAIL",
        "badFile": bad_file,
        "commonRoot": root,
        "fileCount": len(entries),
        "counts": counts,
        "coreDocsFound": sorted(core_docs_found),
        "entries": entries,
    }


def stage_flashriver_package(*, zip_path: Path, project_id: str, project_root: Path, archive_root: Path, expected_sha256: str | None = None, now: str) -> dict[str, Any]:
    manifest = inspect_flashriver_package(zip_path, expected_sha256)
    if manifest["zipTest"] != "PASS":
        raise ValueError(f"ZIP integrity failed: {manifest['badFile']}")
    package_sha = manifest["sha256"]
    package_stem = Path(manifest["artifact"]).stem
    archive_dir = archive_root / "flashriver" / package_sha[:16]
    archive_dir.mkdir(parents=True, exist_ok=True)
    archive_copy = archive_dir / manifest["artifact"]
    if not archive_copy.exists():
        shutil.copy2(zip_path, archive_copy)
    source_base = project_root / "sources" / "flashriver" / package_sha[:16]
    docs_dir = source_base / "docs"
    private_dir = source_base / "private_source_artifacts"
    visuals_dir = source_base / "visuals"
    docs_dir.mkdir(parents=True, exist_ok=True)
    private_dir.mkdir(parents=True, exist_ok=True)
    visuals_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []
    private_sources: list[dict[str, Any]] = []
    visuals: list[dict[str, Any]] = []
    with zipfile.ZipFile(zip_path) as z:
        for entry in manifest["entries"]:
            rel = entry["relativeName"]
            cls = entry["class"]
            src_name = entry["name"]
            if cls in {"core-doc", "support-doc"}:
                data = z.read(src_name)
                archive_member_sha256 = hashlib.sha256(data).hexdigest()
                text = data.decode("utf-8", errors="replace")
                target = _safe_join(docs_dir, rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text, encoding="utf-8")
                materialized_sha256 = sha256_file(target)
                rel_project_path = str(target.relative_to(project_root)).replace("\\", "/")
                aid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"flashriver:{package_sha}:{rel}"))
                artifacts.append({
                    "id": aid,
                    "projectId": project_id,
                    "kind": "flashriver-core-doc" if cls == "core-doc" else "flashriver-support-doc",
                    "title": Path(rel).name,
                    "path": rel_project_path,
                    "payload": {
                        "sourcePackageSha256": package_sha,
                        "sourcePackage": manifest["artifact"],
                        "archiveMember": src_name,
                        "archiveMemberSha256": archive_member_sha256,
                        "relativeName": rel,
                        "size": entry["size"],
                        "materializedSha256": materialized_sha256,
                        "contentPreview": text[:2000],
                    },
                    "authorityState": "SOURCE",
                    "hash": materialized_sha256,
                    "createdAt": now,
                    "updatedAt": now,
                })
            elif cls == "private-source":
                target = _safe_join(private_dir, rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(src_name) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                private_record = {
                    "archiveMember": src_name,
                    "relativeName": rel,
                    "localPath": str(target.relative_to(project_root)).replace("\\", "/"),
                    "size": target.stat().st_size,
                    "sha256": sha256_file(target),
                    "private": True,
                    "indexedAsText": False,
                }
                private_sources.append(private_record)
                artifacts.append({
                    "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"flashriver:{package_sha}:private:{rel}")),
                    "projectId": project_id,
                    "kind": "flashriver-private-source",
                    "title": Path(rel).name,
                    "path": private_record["localPath"],
                    "payload": {**private_record, "sourcePackageSha256": package_sha, "sourcePackage": manifest["artifact"]},
                    "authorityState": "SOURCE_PRIVATE",
                    "hash": private_record["sha256"],
                    "createdAt": now,
                    "updatedAt": now,
                })
            elif cls == "visual":
                target = _safe_join(visuals_dir, rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                with z.open(src_name) as src, target.open("wb") as dst:
                    shutil.copyfileobj(src, dst)
                visual_record = {
                    "archiveMember": src_name,
                    "relativeName": rel,
                    "localPath": str(target.relative_to(project_root)).replace("\\", "/"),
                    "size": target.stat().st_size,
                    "sha256": sha256_file(target),
                    "private": False,
                    "indexedAsText": False,
                }
                visuals.append(visual_record)
                artifacts.append({
                    "id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"flashriver:{package_sha}:visual:{rel}")),
                    "projectId": project_id,
                    "kind": "flashriver-visual",
                    "title": Path(rel).name,
                    "path": visual_record["localPath"],
                    "payload": {**visual_record, "sourcePackageSha256": package_sha, "sourcePackage": manifest["artifact"]},
                    "authorityState": "SOURCE",
                    "hash": visual_record["sha256"],
                    "createdAt": now,
                    "updatedAt": now,
                })
    manifest_out = {
        **manifest,
        "projectId": project_id,
        "stagedAt": now,
        "localArchiveCopy": str(archive_copy),
        "publicSafeDocsImported": sum(1 for artifact in artifacts if artifact["kind"] in {"flashriver-core-doc", "flashriver-support-doc"}),
        "privateSourcesCopied": private_sources,
        "visualsCopied": visuals,
        "boundary": {
            "rawPackageCommittedToGitHub": False,
            "nestedSourceZipsCommittedToGitHub": False,
            "cloudflareAuthority": False,
            "localPcAuthority": True,
        },
    }
    manifest_path = source_base / "FLASHRIVER_INTAKE_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest_out, indent=2), encoding="utf-8")
    manifest_aid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"flashriver:{package_sha}:manifest"))
    artifacts.insert(0, {
        "id": manifest_aid,
        "projectId": project_id,
        "kind": "flashriver-intake-manifest",
        "title": f"FlashRiver Intake Manifest — {package_stem}",
        "path": str(manifest_path.relative_to(project_root)).replace("\\", "/"),
        "payload": manifest_out,
        "authorityState": "SOURCE",
        "hash": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "createdAt": now,
        "updatedAt": now,
    })
    return {"ok": True, "manifest": manifest_out, "artifacts": artifacts}
