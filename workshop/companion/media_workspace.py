from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MEDIA_MAX_BYTES = 12 * 1024 * 1024
ROUTE_ROOMS = {"write", "image", "music", "video"}


class MediaWorkspaceError(ValueError):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class MediaWorkspace:
    """Bounded media operations implemented with existing TWIS artifacts and relationships."""

    def __init__(self, database: Path, projects: Path, contract: Path):
        self.database = database
        self.projects = projects.resolve()
        self.contract = contract

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.database)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _project_root(self, project_id: str) -> Path:
        if not project_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in project_id):
            raise MediaWorkspaceError("Invalid project identity")
        root = (self.projects / project_id).resolve()
        if self.projects not in root.parents:
            raise MediaWorkspaceError("Unsafe project path")
        root.mkdir(parents=True, exist_ok=True)
        return root

    def capabilities(self) -> dict[str, Any]:
        data = json.loads(self.contract.read_text(encoding="utf-8"))
        data["probes"] = {
            "ffmpeg": {"available": bool(shutil.which("ffmpeg")), "path": shutil.which("ffmpeg")},
            "comfyUI": {"available": False, "reason": "No registered ComfyUI runtime, model, or approved workflow is connected."},
        }
        return data

    def _artifact(self, con: sqlite3.Connection, project_id: str, artifact_id: str) -> sqlite3.Row:
        row = con.execute("SELECT * FROM artifacts WHERE id=? AND project_id=?", (artifact_id, project_id)).fetchone()
        if row is None:
            raise MediaWorkspaceError("Artifact is not registered in the active project", 404)
        return row

    @staticmethod
    def _receipt(con: sqlite3.Connection, project_id: str, action: str, details: dict[str, Any]) -> None:
        con.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?)", (str(uuid.uuid4()), project_id, action, "human", _json(details), _utc()))

    @staticmethod
    def _index(con: sqlite3.Connection, artifact: dict[str, Any]) -> None:
        content = f"{artifact['title']} {artifact['kind']} {_json(artifact['payload'])}"
        con.execute("DELETE FROM artifact_search WHERE id=?", (artifact["id"],))
        con.execute("INSERT INTO artifact_search(id,project_id,title,kind,content) VALUES(?,?,?,?,?)", (artifact["id"], artifact["projectId"], artifact["title"], artifact["kind"], content))

    def _insert_artifact(self, con: sqlite3.Connection, artifact: dict[str, Any]) -> None:
        con.execute("""INSERT INTO artifacts(id,project_id,kind,title,path,payload,authority_state,sha256,created_at,updated_at)
                       VALUES(?,?,?,?,?,?,?,?,?,?)""", (artifact["id"], artifact["projectId"], artifact["kind"], artifact["title"], artifact.get("path", ""), _json(artifact["payload"]), "DRAFT", artifact.get("sha256", ""), artifact["createdAt"], artifact["createdAt"]))
        self._index(con, artifact)

    def _verified_image_path(self, row: sqlite3.Row) -> tuple[Path, dict[str, Any]]:
        payload = json.loads(row["payload"] or "{}")
        if payload.get("schemaVersion") != "twis-media-asset-v1":
            raise MediaWorkspaceError("That visual source is not a governed media asset", 409)
        root = self._project_root(row["project_id"])
        path = (root / row["path"]).resolve()
        allowed = (root / "media" / "assets").resolve()
        if allowed not in path.parents or not path.is_file():
            raise MediaWorkspaceError("The visual source file is missing", 409)
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        if not row["sha256"] or actual_hash != row["sha256"]:
            raise MediaWorkspaceError("The visual source changed. Reopen it before creating a variation", 409)
        return path, payload

    def save_image(
        self,
        project_id: str,
        title: str,
        content_type: str,
        raw: bytes,
        width: int,
        height: int,
        source_artifact_id: str = "",
        original_sha256: str = "",
        *,
        provenance_operation: dict[str, Any] | None = None,
        relationship_type: str = "image-variation",
        receipt_action: str = "media.asset.saved",
        origin_override: str = "",
        expected_source_sha256: str = "",
        additional_sources: list[tuple[str, str, str]] | None = None,
    ) -> dict[str, Any]:
        signatures = {"image/png": (b"\x89PNG\r\n\x1a\n", ".png"), "image/jpeg": (b"\xff\xd8\xff", ".jpg"), "image/webp": (b"RIFF", ".webp")}
        if content_type not in signatures or not raw.startswith(signatures[content_type][0]):
            raise MediaWorkspaceError("Only valid PNG, JPEG, or WebP image bytes are accepted")
        if content_type == "image/webp" and raw[8:12] != b"WEBP":
            raise MediaWorkspaceError("Invalid WebP image")
        if not raw or len(raw) > MEDIA_MAX_BYTES or width < 1 or height < 1 or width > 16384 or height > 16384:
            raise MediaWorkspaceError("Image size or dimensions are outside the bounded media contract")
        original_sha256 = original_sha256.strip().lower()
        if original_sha256 and (len(original_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in original_sha256)):
            raise MediaWorkspaceError("Invalid original image hash")
        expected_source_sha256 = expected_source_sha256.strip().lower()
        if expected_source_sha256 and (len(expected_source_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in expected_source_sha256)):
            raise MediaWorkspaceError("Invalid expected source hash")
        source_records: list[dict[str, str]] = []
        with self._connect() as con:
            self._artifact_project(con, project_id)
            if source_artifact_id:
                source = self._artifact(con, project_id, source_artifact_id)
                if source["kind"] != "image":
                    raise MediaWorkspaceError("A visual variation requires a registered image source")
                self._verified_image_path(source)
                if expected_source_sha256 and source["sha256"] != expected_source_sha256:
                    raise MediaWorkspaceError("The selected source hash changed. Reopen it before continuing", 409)
                source_records.append({"id": source["id"], "sha256": source["sha256"], "relationship": relationship_type})
            for artifact_id, expected_hash, extra_relationship in additional_sources or []:
                if artifact_id == source_artifact_id or any(item["id"] == artifact_id for item in source_records):
                    raise MediaWorkspaceError("Each composite source must be a different registered image")
                source = self._artifact(con, project_id, artifact_id)
                if source["kind"] != "image":
                    raise MediaWorkspaceError("A composite background must be a registered image source")
                self._verified_image_path(source)
                expected_hash = expected_hash.strip().lower()
                if not expected_hash or source["sha256"] != expected_hash:
                    raise MediaWorkspaceError("The selected background hash changed. Reopen it before continuing", 409)
                source_records.append({"id": source["id"], "sha256": source["sha256"], "relationship": extra_relationship})
        sha = hashlib.sha256(raw).hexdigest()
        ext = signatures[content_type][1]
        root = self._project_root(project_id)
        folder = root / "media" / "assets"
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{sha}{ext}"
        already_present = target.exists()
        if not already_present:
            target.write_bytes(raw)
        now, aid = _utc(), str(uuid.uuid4())
        relative = target.relative_to(root).as_posix()
        provenance = {
            "origin": origin_override or ("owner-canvas-variation" if source_artifact_id else "owner-canvas"),
            "sourceArtifactIds": [item["id"] for item in source_records],
            "sourceHashes": [item["sha256"] for item in source_records],
            "originalInputSha256": original_sha256 or None,
        }
        if provenance_operation:
            provenance["operation"] = provenance_operation
        artifact = {"id": aid, "projectId": project_id, "kind": "image", "title": (title or "Untitled visual asset")[:300], "path": relative, "sha256": sha, "createdAt": now,
                    "payload": {"schemaVersion": "twis-media-asset-v1", "mediaType": "image", "mimeType": content_type, "width": width, "height": height, "size": len(raw), "sha256": sha, "status": "inactive-draft", "provenance": provenance}}
        try:
            with self._connect() as con:
                # Recheck every governed source in the same transaction that
                # records the derived artifact. A stale or missing source must
                # never be accepted because the browser already made a preview.
                for source_record in source_records:
                    source = self._artifact(con, project_id, source_record["id"])
                    self._verified_image_path(source)
                    if source["sha256"] != source_record["sha256"]:
                        raise MediaWorkspaceError("A selected source changed. Reopen it before continuing", 409)
                self._insert_artifact(con, artifact)
                for source_record in source_records:
                    con.execute("INSERT INTO artifact_relationships VALUES(?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), source_record["id"], aid, project_id, source_record["relationship"], aid, "active", now, now))
                self._receipt(con, project_id, receipt_action, {"artifactId": aid, "sha256": sha, "size": len(raw), "reusedExistingBytes": already_present, "sourceArtifactIds": provenance["sourceArtifactIds"], "sourceHashes": provenance["sourceHashes"], "sourceArtifactId": source_artifact_id or None, "sourceSha256": source_records[0]["sha256"] if source_artifact_id else None, "originalInputSha256": original_sha256 or None, "origin": provenance["origin"], "operation": provenance_operation})
        except Exception:
            if not already_present and target.is_file():
                target.unlink()
            raise
        return {"ok": True, "artifact": artifact}

    def save_background_composite(
        self,
        project_id: str,
        title: str,
        raw: bytes,
        width: int,
        height: int,
        source_artifact_id: str,
        expected_source_sha256: str,
        mode: str,
        color_a: str = "",
        color_b: str = "",
        direction: str = "vertical",
        background_artifact_id: str = "",
        expected_background_sha256: str = "",
    ) -> dict[str, Any]:
        mode = mode.strip().lower()
        direction = direction.strip().lower()
        if mode not in {"solid", "gradient", "image"}:
            raise MediaWorkspaceError("Choose a supported background mode")
        if direction not in {"vertical", "horizontal", "diagonal-down", "diagonal-up"}:
            raise MediaWorkspaceError("Choose a supported gradient direction")

        def valid_color(value: str) -> bool:
            return len(value) == 7 and value.startswith("#") and all(ch in "0123456789abcdefABCDEF" for ch in value[1:])

        if mode in {"solid", "gradient"} and not valid_color(color_a):
            raise MediaWorkspaceError("Choose a valid primary background color")
        if mode == "gradient" and not valid_color(color_b):
            raise MediaWorkspaceError("Choose a valid secondary background color")
        if mode == "image" and (not background_artifact_id or not expected_background_sha256):
            raise MediaWorkspaceError("Choose a registered background image")
        if mode != "image" and (background_artifact_id or expected_background_sha256):
            raise MediaWorkspaceError("A background image is only valid in registered-image mode")

        operation = {
            "schemaVersion": "twis-background-composition-v1",
            "kind": "background-composition",
            "mode": mode,
            "colorA": color_a.lower() if color_a else None,
            "colorB": color_b.lower() if mode == "gradient" else None,
            "direction": direction if mode == "gradient" else None,
            "backgroundArtifactId": background_artifact_id or None,
            "backgroundSha256": expected_background_sha256.lower() or None,
            "engine": "browser-canvas-2d",
            "proposalApproved": True,
            "sourcePreserved": True,
        }
        additional = []
        if mode == "image":
            additional.append((background_artifact_id, expected_background_sha256, "background-composition-backdrop"))
        return self.save_image(
            project_id,
            title,
            "image/png",
            raw,
            width,
            height,
            source_artifact_id,
            expected_source_sha256,
            provenance_operation=operation,
            relationship_type="background-composition-foreground",
            receipt_action="media.background-composition.approved",
            origin_override="owner-approved-background-composition",
            expected_source_sha256=expected_source_sha256,
            additional_sources=additional,
        )

    def verified_image_source(self, project_id: str, artifact_id: str, expected_sha256: str = "") -> tuple[Path, dict[str, Any]]:
        with self._connect() as con:
            row = self._artifact(con, project_id, artifact_id)
            if row["kind"] != "image":
                raise MediaWorkspaceError("Background removal requires a registered Images V2 source", 409)
            path, payload = self._verified_image_path(row)
            expected = expected_sha256.strip().lower()
            if expected and row["sha256"] != expected:
                raise MediaWorkspaceError("The selected source hash changed. Reopen it before continuing", 409)
            return path, {"id": row["id"], "projectId": row["project_id"], "title": row["title"], "path": row["path"], "sha256": row["sha256"], "payload": payload}

    def save_background_removal_result(
        self,
        project_id: str,
        title: str,
        raw: bytes,
        width: int,
        height: int,
        source_artifact_id: str,
        expected_source_sha256: str,
        operation: dict[str, Any],
    ) -> dict[str, Any]:
        self.verified_image_source(project_id, source_artifact_id, expected_source_sha256)
        return self.save_image(
            project_id,
            title,
            "image/png",
            raw,
            width,
            height,
            source_artifact_id,
            expected_source_sha256,
            provenance_operation=operation,
            relationship_type="background-removal-variation",
            receipt_action="media.background-removal.asset-saved",
            origin_override="opencv-grabcut-assisted-cutout",
        )

    @staticmethod
    def _artifact_project(con: sqlite3.Connection, project_id: str) -> None:
        if con.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone() is None:
            raise MediaWorkspaceError("Project is not registered", 404)

    def asset(self, artifact_id: str) -> tuple[Path, str]:
        with self._connect() as con:
            row = con.execute("SELECT * FROM artifacts WHERE id=? AND kind='image'", (artifact_id,)).fetchone()
        if row is None:
            raise MediaWorkspaceError("Image asset not found", 404)
        path, payload = self._verified_image_path(row)
        return path, payload.get("mimeType", "application/octet-stream")

    def create_scene(self, project_id: str, title: str, description: str = "") -> dict[str, Any]:
        now, aid = _utc(), str(uuid.uuid4())
        artifact = {"id": aid, "projectId": project_id, "kind": "scene", "title": (title or "Untitled scene")[:300], "path": "", "sha256": "", "createdAt": now,
                    "payload": {"schemaVersion": "twis-scene-v1", "description": description, "status": "inactive-draft"}}
        with self._connect() as con:
            self._artifact_project(con, project_id); self._insert_artifact(con, artifact)
            self._receipt(con, project_id, "media.scene.created", {"sceneId": aid})
        return {"ok": True, "artifact": artifact}

    def create_route(self, project_id: str, source_id: str, target_room: str, scene_id: str = "", notes: str = "") -> dict[str, Any]:
        if target_room not in ROUTE_ROOMS:
            raise MediaWorkspaceError("Unsupported target room")
        now, aid = _utc(), str(uuid.uuid4())
        with self._connect() as con:
            source = self._artifact(con, project_id, source_id)
            if scene_id:
                scene = self._artifact(con, project_id, scene_id)
                if scene["kind"] != "scene": raise MediaWorkspaceError("Target scene is not a registered scene")
            payload = {"schemaVersion": "twis-media-route-v1", "sourceArtifactId": source_id, "sourceSha256": source["sha256"], "sourceKind": source["kind"], "targetRoom": target_room, "sceneId": scene_id or None, "notes": notes, "status": "ready-for-owner"}
            artifact = {"id": aid, "projectId": project_id, "kind": "media-route", "title": f"{source['title']} to {target_room.title()}", "path": "", "sha256": hashlib.sha256(_json(payload).encode()).hexdigest(), "createdAt": now, "payload": payload}
            self._insert_artifact(con, artifact)
            for target, rel_type in ((aid, "media-route-source"), (scene_id, "scene-asset")):
                if target:
                    con.execute("INSERT INTO artifact_relationships VALUES(?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), source_id, target, project_id, rel_type, aid, "active", now, now))
            self._receipt(con, project_id, "media.route.created", {"routeId": aid, "sourceArtifactId": source_id, "targetRoom": target_room, "sceneId": scene_id or None})
        return {"ok": True, "artifact": artifact}

    def create_storyboard_item(self, project_id: str, scene_id: str, image_id: str, duration: float, transition: str) -> dict[str, Any]:
        duration = max(0.25, min(float(duration or 4), 3600))
        now, aid = _utc(), str(uuid.uuid4())
        with self._connect() as con:
            scene = self._artifact(con, project_id, scene_id)
            image = self._artifact(con, project_id, image_id)
            if scene["kind"] != "scene" or image["kind"] != "image": raise MediaWorkspaceError("Storyboard requires a scene and an image")
            existing = con.execute("SELECT payload FROM artifacts WHERE project_id=? AND kind='storyboard-item'", (project_id,)).fetchall()
            next_order = max((int(json.loads(row["payload"] or "{}").get("order", 0)) for row in existing), default=0) + 1
            payload = {"schemaVersion": "twis-storyboard-item-v1", "sceneId": scene_id, "primaryImageId": image_id, "durationSeconds": duration, "transitionNotes": transition[:500], "order": next_order, "status": "inactive-draft"}
            artifact = {"id": aid, "projectId": project_id, "kind": "storyboard-item", "title": f"Storyboard: {scene['title']}", "path": "", "sha256": hashlib.sha256(_json(payload).encode()).hexdigest(), "createdAt": now, "payload": payload}
            self._insert_artifact(con, artifact)
            for source_id, rel_type in ((scene_id, "storyboard-scene"), (image_id, "storyboard-image")):
                con.execute("INSERT INTO artifact_relationships VALUES(?,?,?,?,?,?,?,?,?)", (str(uuid.uuid4()), source_id, aid, project_id, rel_type, aid, "active", now, now))
            self._receipt(con, project_id, "media.storyboard.created", {"storyboardItemId": aid, "sceneId": scene_id, "imageId": image_id})
        return {"ok": True, "artifact": artifact}

    def reorder_storyboard_item(self, project_id: str, item_id: str, direction: str) -> dict[str, Any]:
        if direction not in {"earlier", "later"}:
            raise MediaWorkspaceError("Storyboard direction must be earlier or later")
        with self._connect() as con:
            target = self._artifact(con, project_id, item_id)
            if target["kind"] != "storyboard-item":
                raise MediaWorkspaceError("That record is not a storyboard frame")
            rows = con.execute("SELECT * FROM artifacts WHERE project_id=? AND kind='storyboard-item' ORDER BY created_at,id", (project_id,)).fetchall()
            rows = sorted(rows, key=lambda row: (int(json.loads(row["payload"] or "{}").get("order", 10**9)), row["created_at"], row["id"]))
            index = next(i for i, row in enumerate(rows) if row["id"] == item_id)
            other_index = index - 1 if direction == "earlier" else index + 1
            if other_index < 0 or other_index >= len(rows):
                return {"ok": True, "artifactId": item_id, "changed": False}
            first, second = rows[index], rows[other_index]
            first_payload, second_payload = json.loads(first["payload"] or "{}"), json.loads(second["payload"] or "{}")
            first_order, second_order = int(first_payload.get("order", index + 1)), int(second_payload.get("order", other_index + 1))
            first_payload["order"], second_payload["order"] = second_order, first_order
            now = _utc()
            for row, payload in ((first, first_payload), (second, second_payload)):
                digest = hashlib.sha256(_json(payload).encode()).hexdigest()
                con.execute("UPDATE artifacts SET payload=?,sha256=?,updated_at=? WHERE id=?", (_json(payload), digest, now, row["id"]))
                con.execute("DELETE FROM artifact_search WHERE id=?", (row["id"],))
                con.execute("INSERT INTO artifact_search(id,project_id,title,kind,content) VALUES(?,?,?,?,?)", (row["id"], project_id, row["title"], row["kind"], f"{row['title']} {row['kind']} {_json(payload)}"))
            self._receipt(con, project_id, "media.storyboard.reordered", {"storyboardItemId": item_id, "direction": direction})
        return {"ok": True, "artifactId": item_id, "changed": True}

    def remove_storyboard_item(self, project_id: str, item_id: str) -> dict[str, Any]:
        with self._connect() as con:
            target = self._artifact(con, project_id, item_id)
            if target["kind"] != "storyboard-item":
                raise MediaWorkspaceError("That record is not a storyboard frame")
            payload = json.loads(target["payload"] or "{}")
            con.execute("DELETE FROM artifact_relationships WHERE source_artifact_id=? OR target_artifact_id=?", (item_id, item_id))
            con.execute("DELETE FROM artifacts WHERE id=?", (item_id,))
            con.execute("DELETE FROM artifact_search WHERE id=?", (item_id,))
            self._receipt(con, project_id, "media.storyboard.removed", {"storyboardItemId": item_id, "imageId": payload.get("primaryImageId"), "sourcePreserved": True})
        return {"ok": True, "storyboardItemId": item_id, "sourcePreserved": True}

    def summary(self, project_id: str) -> dict[str, Any]:
        with self._connect() as con:
            self._artifact_project(con, project_id)
            rows = con.execute("SELECT * FROM artifacts WHERE project_id=? AND kind IN ('scene','image','document','writing-draft','music','music-render','video','storyboard-item','media-route') ORDER BY updated_at DESC", (project_id,)).fetchall()
        items = []
        for row in rows:
            item = dict(row); item["payload"] = json.loads(item["payload"] or "{}"); items.append(item)
        return {"ok": True, "projectId": project_id, "items": items}
