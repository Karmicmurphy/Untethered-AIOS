from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from companion.media_workspace import MediaWorkspace, MediaWorkspaceError


class BackgroundRemovalError(ValueError):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


class BackgroundRemovalRuntime:
    """Fixed OpenCV GrabCut adapter. It accepts registered image IDs, never arbitrary paths or commands."""

    def __init__(self, database: Path, projects: Path, runtime_root: Path, config: Path, media: MediaWorkspace):
        self.database = database
        self.projects = projects.resolve()
        self.runtime_root = runtime_root.resolve()
        self.config_path = config.resolve()
        self.media = media
        self.lock = threading.Lock()
        self._verified_tree_hash = ""
        self._verified_manifest_mtime = 0

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _config(self) -> dict[str, Any]:
        try:
            value = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise BackgroundRemovalError("runtime_config_invalid", "The registered background-removal configuration is missing or invalid", 503) from exc
        required = {"schemaVersion", "runtimeId", "capabilityId", "version", "relativePath", "manifestSha256", "pythonVersion", "timeoutSeconds", "maxPixels"}
        if value.get("schemaVersion") != "twis-background-removal-runtime-config-v1" or required - set(value):
            raise BackgroundRemovalError("runtime_config_invalid", "The registered background-removal configuration is invalid", 503)
        return value

    def _paths(self) -> tuple[dict[str, Any], Path, Path, Path]:
        config = self._config()
        runtime = (self.runtime_root / str(config["relativePath"])).resolve()
        if self.runtime_root not in runtime.parents:
            raise BackgroundRemovalError("runtime_path_denied", "The registered runtime path is outside the TWIS runtime root", 503)
        site_packages = (runtime / "site-packages").resolve()
        manifest = (runtime / "runtime-manifest.json").resolve()
        worker = (self.config_path.parents[1] / "companion" / "background_removal_worker.py").resolve()
        return config, site_packages, manifest, worker

    def _manifest(self, config: dict[str, Any], manifest_path: Path) -> dict[str, Any]:
        if not manifest_path.is_file() or _sha256(manifest_path) != str(config["manifestSha256"]).upper():
            raise BackgroundRemovalError("runtime_manifest_mismatch", "The registered OpenCV runtime manifest is missing or does not match", 503)
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BackgroundRemovalError("runtime_manifest_invalid", "The registered OpenCV runtime manifest is invalid", 503) from exc
        if manifest.get("schemaVersion") != "twis-runtime-file-manifest-v1" or manifest.get("runtimeId") != config["runtimeId"] or manifest.get("version") != config["version"]:
            raise BackgroundRemovalError("runtime_manifest_invalid", "The registered OpenCV runtime identity does not match", 503)
        return manifest

    def _verify_files(self, site_packages: Path, manifest_path: Path, manifest: dict[str, Any]) -> str:
        current_mtime = manifest_path.stat().st_mtime_ns
        expected_tree = str(manifest.get("treeSha256") or "").upper()
        if expected_tree and self._verified_tree_hash == expected_tree and self._verified_manifest_mtime == current_mtime:
            return expected_tree
        rows = manifest.get("files")
        if not isinstance(rows, list) or not rows:
            raise BackgroundRemovalError("runtime_manifest_invalid", "The OpenCV runtime file manifest is empty", 503)
        tree = hashlib.sha256()
        total = 0
        for row in rows:
            if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
                raise BackgroundRemovalError("runtime_manifest_invalid", "The OpenCV runtime file manifest has an invalid entry", 503)
            path = (site_packages / str(row["path"])).resolve()
            if site_packages not in path.parents or not path.is_file() or path.stat().st_size != int(row["bytes"]):
                raise BackgroundRemovalError("runtime_file_mismatch", f"The registered runtime file is missing or changed: {row['path']}", 503)
            actual = _sha256(path)
            if actual != str(row["sha256"]).upper():
                raise BackgroundRemovalError("runtime_file_mismatch", f"The registered runtime file hash changed: {row['path']}", 503)
            tree.update(f"{row['path']}\0{row['bytes']}\0{actual}\n".encode("utf-8"))
            total += int(row["bytes"])
        actual_tree = tree.hexdigest().upper()
        if actual_tree != expected_tree or total != int(manifest.get("bytes") or -1):
            raise BackgroundRemovalError("runtime_tree_mismatch", "The registered OpenCV runtime tree does not match its manifest", 503)
        self._verified_tree_hash = actual_tree
        self._verified_manifest_mtime = current_mtime
        return actual_tree

    @staticmethod
    def _creation_flags() -> int:
        return int(getattr(subprocess, "CREATE_NO_WINDOW", 0))

    def health(self, *, verify_files: bool = False) -> dict[str, Any]:
        config, site_packages, manifest_path, worker = self._paths()
        try:
            manifest = self._manifest(config, manifest_path)
            if verify_files:
                self._verify_files(site_packages, manifest_path, manifest)
            if not worker.is_file() or not site_packages.is_dir():
                raise BackgroundRemovalError("runtime_missing", "The registered OpenCV runtime is not installed", 503)
            command = [sys.executable, "-I", "-S", str(worker), "--site-packages", str(site_packages), "--health"]
            completed = subprocess.run(command, cwd=str(worker.parent), capture_output=True, text=True, timeout=20, creationflags=self._creation_flags(), check=False)
            if completed.returncode != 0:
                raise BackgroundRemovalError("runtime_health_failed", "The registered OpenCV runtime failed its local health test", 503)
            result = json.loads(completed.stdout.strip())
            if result.get("ok") is not True or str(result.get("opencvVersion")) != "4.14.0":
                raise BackgroundRemovalError("runtime_health_failed", "The registered OpenCV runtime returned an unexpected version", 503)
            return {
                "ok": True,
                "state": "HEALTHY",
                "runtimeId": config["runtimeId"],
                "capabilityId": config["capabilityId"],
                "version": config["version"],
                "opencvVersion": result["opencvVersion"],
                "numpyVersion": result.get("numpyVersion"),
                "runtimeBytes": manifest.get("bytes"),
                "runtimeFiles": manifest.get("fileCount"),
                "runtimeTreeSha256": manifest.get("treeSha256"),
                "hashVerified": bool(verify_files),
                "network": "none",
                "persistentProcess": False,
            }
        except BackgroundRemovalError:
            raise
        except (OSError, subprocess.SubprocessError, json.JSONDecodeError) as exc:
            raise BackgroundRemovalError("runtime_health_failed", f"The registered OpenCV runtime is unavailable: {type(exc).__name__}", 503) from exc

    def _project_root(self, project_id: str) -> Path:
        if not project_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in project_id):
            raise BackgroundRemovalError("project_invalid", "Invalid project identity")
        root = (self.projects / project_id).resolve()
        if self.projects not in root.parents or not root.is_dir():
            raise BackgroundRemovalError("project_missing", "Project is not registered", 404)
        return root

    def _proposal_root(self, project_id: str) -> Path:
        root = self._project_root(project_id) / "media" / "background-removal" / "proposals"
        root.mkdir(parents=True, exist_ok=True)
        return root.resolve()

    def _receipt(self, project_id: str, action: str, details: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), project_id, action, "human", json.dumps(details, ensure_ascii=False, separators=(",", ":")), _utc()))

    @staticmethod
    def _normalize_rectangle(value: Any, width: int, height: int) -> dict[str, int]:
        if not isinstance(value, dict):
            raise BackgroundRemovalError("rectangle_required", "Draw a foreground rectangle before previewing the cutout")
        try:
            x = float(value["x"]); y = float(value["y"]); rect_width = float(value["width"]); rect_height = float(value["height"])
        except (KeyError, TypeError, ValueError) as exc:
            raise BackgroundRemovalError("rectangle_invalid", "The foreground rectangle is invalid") from exc
        if not all(0 <= number <= 1 for number in (x, y, rect_width, rect_height)) or rect_width <= 0 or rect_height <= 0 or x + rect_width > 1.001 or y + rect_height > 1.001:
            raise BackgroundRemovalError("rectangle_invalid", "The foreground rectangle must remain inside the image")
        result = {"x": round(x * width), "y": round(y * height), "width": max(2, round(rect_width * width)), "height": max(2, round(rect_height * height))}
        if result["width"] < 8 or result["height"] < 8:
            raise BackgroundRemovalError("rectangle_too_small", "Choose a larger foreground rectangle")
        return result

    @staticmethod
    def _normalize_strokes(value: Any, width: int, height: int) -> list[dict[str, Any]]:
        if value is None:
            return []
        if not isinstance(value, list) or len(value) > 2048:
            raise BackgroundRemovalError("strokes_invalid", "The keep/remove correction set is invalid or too large")
        result = []
        for stroke in value:
            if not isinstance(stroke, dict) or stroke.get("mode") not in {"keep", "remove"}:
                raise BackgroundRemovalError("strokes_invalid", "A keep/remove correction point is invalid")
            try:
                x = float(stroke["x"]); y = float(stroke["y"]); radius = float(stroke["radius"])
            except (KeyError, TypeError, ValueError) as exc:
                raise BackgroundRemovalError("strokes_invalid", "A keep/remove correction point is invalid") from exc
            if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < radius <= 0.25):
                raise BackgroundRemovalError("strokes_invalid", "A keep/remove correction point is outside the image")
            result.append({"mode": stroke["mode"], "x": round(x * width), "y": round(y * height), "radius": max(1, round(radius * max(width, height)))})
        return result

    def create_proposal(self, project_id: str, value: dict[str, Any]) -> dict[str, Any]:
        source_id = str(value.get("sourceArtifactId") or "").strip()
        expected_hash = str(value.get("sourceSha256") or "").strip().lower()
        if len(expected_hash) != 64 or any(ch not in "0123456789abcdef" for ch in expected_hash):
            raise BackgroundRemovalError("source_hash_required", "The exact registered source hash is required")
        try:
            source_path, source = self.media.verified_image_source(project_id, source_id, expected_hash)
        except MediaWorkspaceError as exc:
            raise BackgroundRemovalError("source_invalid", str(exc), exc.status) from exc
        width = int(source["payload"].get("width") or 0); height = int(source["payload"].get("height") or 0)
        if width * height > 8_388_608:
            raise BackgroundRemovalError("source_too_large", "Resize this image below 8.4 megapixels before using assisted background removal", 413)
        rectangle = self._normalize_rectangle(value.get("rectangle"), width, height)
        strokes = self._normalize_strokes(value.get("strokes"), width, height)
        proposal_root = self._proposal_root(project_id)
        if sum(1 for path in proposal_root.iterdir() if path.is_dir()) >= 8:
            raise BackgroundRemovalError("proposal_limit", "Finish or reject an existing background-removal proposal before creating another", 409)
        config, site_packages, manifest_path, worker = self._paths()
        manifest = self._manifest(config, manifest_path)
        runtime_hash = self._verify_files(site_packages, manifest_path, manifest)
        self.health(verify_files=False)
        proposal_id = str(uuid.uuid4())
        work = (proposal_root / proposal_id).resolve()
        if proposal_root not in work.parents:
            raise BackgroundRemovalError("proposal_path_denied", "Unsafe proposal path")
        work.mkdir(parents=True)
        request_path, result_path, output_path = work / "request.json", work / "result.json", work / "preview.png"
        request = {
            "schemaVersion": "twis-background-removal-request-v1",
            "sourcePath": str(source_path),
            "outputPath": str(output_path),
            "rectangle": rectangle,
            "strokes": strokes,
        }
        request_path.write_text(json.dumps(request, indent=2) + "\n", encoding="utf-8")
        command = [sys.executable, "-I", "-S", str(worker), "--site-packages", str(site_packages), "--request", str(request_path), "--result", str(result_path)]
        started = time.perf_counter()
        try:
            with self.lock:
                completed = subprocess.run(command, cwd=str(worker.parent), capture_output=True, text=True, timeout=int(config["timeoutSeconds"]), creationflags=self._creation_flags(), check=False)
            if completed.returncode != 0 or not output_path.is_file() or not result_path.is_file():
                detail = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "OpenCV did not return a proposal"
                raise BackgroundRemovalError("execution_failed", f"Background removal failed: {detail[:300]}", 422)
            result = json.loads(result_path.read_text(encoding="utf-8"))
            output_hash = _sha256(output_path)
            created = _utc()
            proposal = {
                "schemaVersion": "twis-background-removal-proposal-v1",
                "proposalId": proposal_id,
                "projectId": project_id,
                "state": "PROPOSED",
                "createdAt": created,
                "sourceArtifactId": source_id,
                "sourceSha256": expected_hash,
                "sourceTitle": source["title"],
                "sourcePath": source["path"],
                "rectangle": rectangle,
                "strokeCount": len(strokes),
                "runtime": {"runtimeId": config["runtimeId"], "version": config["version"], "manifestSha256": config["manifestSha256"], "treeSha256": runtime_hash, "opencvVersion": result.get("opencvVersion"), "numpyVersion": result.get("numpyVersion")},
                "outputSha256": output_hash,
                "outputBytes": output_path.stat().st_size,
                "width": result.get("width"),
                "height": result.get("height"),
                "metrics": {key: result.get(key) for key in ("foregroundPixels", "backgroundPixels", "foregroundRatio", "strokeCount", "elapsedSeconds")},
                "totalWallSeconds": round(time.perf_counter() - started, 6),
                "automaticSave": False,
                "sourcePreserved": True,
            }
            (work / "proposal.json").write_text(json.dumps(proposal, indent=2) + "\n", encoding="utf-8")
            request_path.unlink(missing_ok=True); result_path.unlink(missing_ok=True)
            self._receipt(project_id, "media.background-removal.proposed", {"proposalId": proposal_id, "sourceArtifactId": source_id, "sourceSha256": expected_hash, "outputSha256": output_hash, "runtimeTreeSha256": runtime_hash, "approved": False})
            return {"ok": True, "proposal": self._public(proposal), "previewUrl": self._preview_url(project_id, proposal_id)}
        except Exception as exc:
            shutil.rmtree(work, ignore_errors=True)
            if isinstance(exc, BackgroundRemovalError):
                raise
            if isinstance(exc, subprocess.TimeoutExpired):
                raise BackgroundRemovalError("execution_timeout", "Background removal exceeded the bounded local timeout", 504) from exc
            raise BackgroundRemovalError("execution_failed", f"Background removal failed: {type(exc).__name__}", 422) from exc

    @staticmethod
    def _public(proposal: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in proposal.items() if key != "sourcePath"}

    @staticmethod
    def _preview_url(project_id: str, proposal_id: str) -> str:
        return f"/api/background-removal/projects/{project_id}/proposals/{proposal_id}/preview"

    def _load_proposal(self, project_id: str, proposal_id: str) -> tuple[Path, dict[str, Any]]:
        if not proposal_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-" for ch in proposal_id):
            raise BackgroundRemovalError("proposal_invalid", "Invalid proposal identity")
        root = self._proposal_root(project_id)
        work = (root / proposal_id).resolve()
        if root not in work.parents:
            raise BackgroundRemovalError("proposal_path_denied", "Unsafe proposal path")
        metadata, preview = work / "proposal.json", work / "preview.png"
        if not metadata.is_file() or not preview.is_file():
            raise BackgroundRemovalError("proposal_missing", "Background-removal proposal was not found", 404)
        try:
            value = json.loads(metadata.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise BackgroundRemovalError("proposal_invalid", "Background-removal proposal metadata is invalid", 409) from exc
        if value.get("schemaVersion") != "twis-background-removal-proposal-v1" or value.get("proposalId") != proposal_id or value.get("projectId") != project_id or _sha256(preview) != str(value.get("outputSha256") or "").upper():
            raise BackgroundRemovalError("proposal_changed", "Background-removal proposal evidence changed and cannot be approved", 409)
        return work, value

    def list_proposals(self, project_id: str) -> dict[str, Any]:
        root = self._proposal_root(project_id)
        proposals = []
        for path in sorted(root.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
            if not path.is_dir():
                continue
            try:
                _, value = self._load_proposal(project_id, path.name)
                item = self._public(value); item["previewUrl"] = self._preview_url(project_id, path.name); proposals.append(item)
            except BackgroundRemovalError:
                continue
        return {"ok": True, "projectId": project_id, "proposals": proposals}

    def preview(self, project_id: str, proposal_id: str) -> Path:
        work, _ = self._load_proposal(project_id, proposal_id)
        return work / "preview.png"

    def decide(self, project_id: str, proposal_id: str, decision: str, title: str = "") -> dict[str, Any]:
        decision = decision.strip().lower()
        if decision not in {"approve", "reject"}:
            raise BackgroundRemovalError("decision_invalid", "Decision must be approve or reject")
        work, proposal = self._load_proposal(project_id, proposal_id)
        if decision == "reject":
            self._receipt(project_id, "media.background-removal.rejected", {"proposalId": proposal_id, "sourceArtifactId": proposal["sourceArtifactId"], "outputSha256": proposal["outputSha256"], "sourcePreserved": True})
            shutil.rmtree(work)
            return {"ok": True, "decision": "rejected", "proposalId": proposal_id, "sourcePreserved": True}
        try:
            self.media.verified_image_source(project_id, proposal["sourceArtifactId"], proposal["sourceSha256"])
            preview = work / "preview.png"
            result = self.media.save_background_removal_result(project_id, title or f"{proposal['sourceTitle']} cutout", preview.read_bytes(), int(proposal["width"]), int(proposal["height"]), proposal["sourceArtifactId"], proposal["sourceSha256"], {"proposalId": proposal_id, "runtime": proposal["runtime"], "rectangle": proposal["rectangle"], "strokeCount": proposal["strokeCount"], "outputSha256": proposal["outputSha256"], "metrics": proposal["metrics"]})
        except MediaWorkspaceError as exc:
            raise BackgroundRemovalError("source_stale", "The registered source changed before approval. Reject this proposal and create a new one", 409) from exc
        self._receipt(project_id, "media.background-removal.approved", {"proposalId": proposal_id, "artifactId": result["artifact"]["id"], "sourceArtifactId": proposal["sourceArtifactId"], "sourceSha256": proposal["sourceSha256"], "outputSha256": proposal["outputSha256"], "inactiveDraft": True})
        shutil.rmtree(work)
        return {"ok": True, "decision": "approved", "proposalId": proposal_id, "artifact": result["artifact"], "sourcePreserved": True, "inactiveDraft": True}
