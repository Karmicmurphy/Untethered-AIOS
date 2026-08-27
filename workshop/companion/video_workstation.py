from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VIDEO_SCHEMA = "twis-video-composition-v1"
RENDER_SCHEMA = "twis-video-render-v1"
MAX_CLIPS = 24
MAX_TITLES = 8
MAX_DURATION = 300.0
MOTIONS = {"still", "zoom-in", "zoom-out", "pan-left", "pan-right", "pan-up", "pan-down"}
TRANSITIONS = {"cut", "crossfade"}
POSITIONS = {"top", "center", "bottom"}
QUALITIES = {"draft": 28, "standard": 23, "high": 19}
SIZES = {"720p": (1280, 720), "480p": (854, 480)}


class VideoWorkstationError(ValueError):
    def __init__(self, message: str, status: int = 400, code: str = "video_workstation_error"):
        super().__init__(message)
        self.status = status
        self.code = code


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_text(value: Any, limit: int) -> str:
    return str(value or "").replace("\x00", "").strip()[:limit]


class VideoWorkstation:
    """Bounded still-image video composition and FFmpeg rendering.

    TWIS artifacts remain authoritative. This adapter accepts registered IDs and
    fixed presets only; it never accepts a command, executable path, or filter
    expression from an HTTP client.
    """

    def __init__(self, database: Path, projects: Path, runtime_root: Path):
        self.database = database
        self.projects = projects.resolve()
        self.runtime_root = runtime_root.resolve()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.database, timeout=30)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _project_root(self, project_id: str) -> Path:
        if not project_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in project_id):
            raise VideoWorkstationError("Invalid project identity")
        root = (self.projects / project_id).resolve()
        if self.projects not in root.parents:
            raise VideoWorkstationError("Unsafe project path")
        if not root.is_dir():
            raise VideoWorkstationError("Project is not registered", 404)
        return root

    @staticmethod
    def _artifact(con: sqlite3.Connection, project_id: str, artifact_id: str) -> sqlite3.Row:
        row = con.execute("SELECT * FROM artifacts WHERE id=? AND project_id=?", (artifact_id, project_id)).fetchone()
        if row is None:
            raise VideoWorkstationError("A selected source is not registered in this project", 404)
        return row

    @staticmethod
    def _receipt(con: sqlite3.Connection, project_id: str, action: str, details: dict[str, Any]) -> str:
        receipt_id = str(uuid.uuid4())
        con.execute("INSERT INTO receipts VALUES(?,?,?,?,?,?)", (receipt_id, project_id, action, "human", _json(details), _utc()))
        return receipt_id

    @staticmethod
    def _index(con: sqlite3.Connection, artifact: dict[str, Any]) -> None:
        content = f"{artifact['title']} {artifact['kind']} {_json(artifact['payload'])}"
        con.execute("DELETE FROM artifact_search WHERE id=?", (artifact["id"],))
        con.execute(
            "INSERT INTO artifact_search(id,project_id,title,kind,content) VALUES(?,?,?,?,?)",
            (artifact["id"], artifact["projectId"], artifact["title"], artifact["kind"], content),
        )

    def _insert_artifact(self, con: sqlite3.Connection, artifact: dict[str, Any]) -> None:
        con.execute(
            """INSERT INTO artifacts(id,project_id,kind,title,path,payload,authority_state,sha256,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (
                artifact["id"], artifact["projectId"], artifact["kind"], artifact["title"], artifact.get("path", ""),
                _json(artifact["payload"]), "DRAFT", artifact.get("sha256", ""), artifact["createdAt"], artifact["createdAt"],
            ),
        )
        self._index(con, artifact)

    def _runtime(self) -> tuple[Path | None, Path | None]:
        explicit = os.environ.get("TWIS_FFMPEG_PATH", "").strip()
        candidates: list[Path] = []
        if explicit:
            candidates.append(Path(explicit))
        candidates.extend(sorted(self.runtime_root.glob("ffmpeg/*/bin/ffmpeg.exe"), reverse=True))
        on_path = shutil.which("ffmpeg")
        if on_path:
            candidates.append(Path(on_path))
        for ffmpeg in candidates:
            if ffmpeg.is_file():
                ffprobe = ffmpeg.with_name("ffprobe.exe")
                return ffmpeg.resolve(), ffprobe.resolve() if ffprobe.is_file() else None
        return None, None

    def runtime_status(self, verify: bool = False) -> dict[str, Any]:
        ffmpeg, ffprobe = self._runtime()
        result: dict[str, Any] = {
            "available": bool(ffmpeg and ffprobe),
            "state": "AVAILABLE" if ffmpeg and ffprobe else "UNAVAILABLE",
            "ffmpegPath": str(ffmpeg) if ffmpeg else None,
            "ffprobePath": str(ffprobe) if ffprobe else None,
            "network": False,
            "arbitraryShell": False,
        }
        if not ffmpeg or not ffprobe:
            result["reason"] = "The registered portable FFmpeg runtime is not present."
            return result
        result.update({"ffmpegSha256": _sha(ffmpeg), "ffprobeSha256": _sha(ffprobe)})
        if verify:
            try:
                probe = self._run([str(ffmpeg), "-hide_banner", "-version"], timeout=10)
                encoders = self._run([str(ffmpeg), "-hide_banner", "-encoders"], timeout=15)
                filters = self._run([str(ffmpeg), "-hide_banner", "-filters"], timeout=15)
                version_line = (probe.stdout or probe.stderr).splitlines()[0]
                required = {
                    "libx264": "libx264" in encoders.stdout,
                    "aac": " AAC " in encoders.stdout or " aac " in encoders.stdout,
                    "xfade": " xfade " in filters.stdout,
                    "zoompan": " zoompan " in filters.stdout,
                    "drawtext": " drawtext " in filters.stdout,
                    "afade": " afade " in filters.stdout,
                }
                result.update({"verified": all(required.values()), "version": version_line, "features": required})
                result["state"] = "READY" if result["verified"] else "ERROR"
            except (OSError, subprocess.SubprocessError) as error:
                result.update({"verified": False, "state": "ERROR", "reason": str(error)[:500]})
        return result

    @staticmethod
    def _run(command: list[str], timeout: float, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        return subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            timeout=timeout,
            creationflags=creationflags,
            check=True,
        )

    def _verified_media_path(self, row: sqlite3.Row, allowed_kind: str) -> Path:
        root = self._project_root(row["project_id"])
        relative = str(row["path"] or "")
        path = (root / relative).resolve()
        allowed_roots = (
            [(root / "media/assets").resolve()]
            if allowed_kind == "image"
            else [(root / "exports/music").resolve(), (root / "music/renders").resolve()]
        )
        if not any(allowed in path.parents for allowed in allowed_roots) or not path.is_file():
            raise VideoWorkstationError(f"The selected {allowed_kind} source file is missing", 409, "source_missing")
        actual = _sha(path)
        if not row["sha256"] or actual != row["sha256"]:
            raise VideoWorkstationError(f"The selected {allowed_kind} source changed. Reopen the composition.", 409, "source_hash_mismatch")
        return path

    def _normalize_composition(self, con: sqlite3.Connection, project_id: str, value: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Path]]:
        title = _clean_text(value.get("title"), 300) or "Untitled video composition"
        raw_clips = value.get("clips")
        if not isinstance(raw_clips, list) or not 1 <= len(raw_clips) <= MAX_CLIPS:
            raise VideoWorkstationError(f"Choose between 1 and {MAX_CLIPS} visual clips")
        paths: dict[str, Path] = {}
        clips: list[dict[str, Any]] = []
        for order, raw in enumerate(raw_clips):
            if not isinstance(raw, dict):
                raise VideoWorkstationError("Malformed visual clip")
            source_id = _clean_text(raw.get("sourceArtifactId"), 80)
            row = self._artifact(con, project_id, source_id)
            if row["kind"] != "image":
                raise VideoWorkstationError("Video V2 accepts registered image assets as visual clips")
            payload = json.loads(row["payload"] or "{}")
            if payload.get("schemaVersion") != "twis-media-asset-v1":
                raise VideoWorkstationError("The selected image is not a governed Images V2 asset", 409)
            paths[source_id] = self._verified_media_path(row, "image")
            supplied_hash = _clean_text(raw.get("sourceSha256"), 64).lower()
            if supplied_hash and supplied_hash != row["sha256"]:
                raise VideoWorkstationError("A selected image hash is stale", 409, "source_hash_mismatch")
            duration = max(0.5, min(float(raw.get("durationSeconds") or 4), 60.0))
            motion = _clean_text(raw.get("motion"), 20) or "still"
            transition = _clean_text(raw.get("transition"), 20) or "cut"
            if motion not in MOTIONS or transition not in TRANSITIONS:
                raise VideoWorkstationError("Unsupported motion or transition preset")
            storyboard_id = _clean_text(raw.get("storyboardItemId"), 80)
            if storyboard_id:
                storyboard = self._artifact(con, project_id, storyboard_id)
                board_payload = json.loads(storyboard["payload"] or "{}")
                if storyboard["kind"] != "storyboard-item" or board_payload.get("primaryImageId") != source_id:
                    raise VideoWorkstationError("Storyboard reference does not match its image", 409)
            clips.append({
                "order": order + 1,
                "sourceArtifactId": source_id,
                "sourceSha256": row["sha256"],
                "storyboardItemId": storyboard_id or None,
                "durationSeconds": round(duration, 3),
                "motion": motion,
                "transition": transition,
                "title": row["title"],
            })

        audio: dict[str, Any] | None = None
        raw_audio = value.get("audio")
        if isinstance(raw_audio, dict) and raw_audio.get("sourceArtifactId"):
            source_id = _clean_text(raw_audio.get("sourceArtifactId"), 80)
            row = self._artifact(con, project_id, source_id)
            if row["kind"] != "music-render":
                raise VideoWorkstationError("Audio must be a governed Music Studio render")
            paths[source_id] = self._verified_media_path(row, "audio")
            supplied_hash = _clean_text(raw_audio.get("sourceSha256"), 64).lower()
            if supplied_hash and supplied_hash != row["sha256"]:
                raise VideoWorkstationError("The selected audio hash is stale", 409, "source_hash_mismatch")
            audio = {
                "sourceArtifactId": source_id,
                "sourceSha256": row["sha256"],
                "title": row["title"],
                "startSeconds": max(0.0, min(float(raw_audio.get("startSeconds") or 0), MAX_DURATION)),
                "trimStartSeconds": max(0.0, min(float(raw_audio.get("trimStartSeconds") or 0), MAX_DURATION)),
                "volume": max(0.0, min(float(raw_audio.get("volume") if raw_audio.get("volume") is not None else 1), 2.0)),
                "fadeInSeconds": max(0.0, min(float(raw_audio.get("fadeInSeconds") or 0), 10.0)),
                "fadeOutSeconds": max(0.0, min(float(raw_audio.get("fadeOutSeconds") or 0), 10.0)),
                "muted": bool(raw_audio.get("muted", False)),
            }

        titles: list[dict[str, Any]] = []
        raw_titles = value.get("titles") or []
        if not isinstance(raw_titles, list) or len(raw_titles) > MAX_TITLES:
            raise VideoWorkstationError(f"Video supports at most {MAX_TITLES} title overlays")
        for raw in raw_titles:
            text = _clean_text(raw.get("text") if isinstance(raw, dict) else "", 500)
            if not text:
                continue
            position = _clean_text(raw.get("position"), 20) or "center"
            if position not in POSITIONS:
                raise VideoWorkstationError("Unsupported title position")
            source_id = _clean_text(raw.get("sourceArtifactId"), 80)
            source_hash = ""
            if source_id:
                source = self._artifact(con, project_id, source_id)
                if source["kind"] not in {"document", "writing-draft", "media-route"}:
                    raise VideoWorkstationError("Title writing reference is not eligible")
                source_hash = source["sha256"] or hashlib.sha256((source["payload"] or "").encode("utf-8")).hexdigest()
                supplied_hash = _clean_text(raw.get("sourceSha256"), 64).lower()
                if supplied_hash and supplied_hash != source_hash:
                    raise VideoWorkstationError("The selected title writing hash is stale", 409, "source_hash_mismatch")
            titles.append({
                "text": text,
                "startSeconds": max(0.0, min(float(raw.get("startSeconds") or 0), MAX_DURATION)),
                "durationSeconds": max(0.25, min(float(raw.get("durationSeconds") or 3), MAX_DURATION)),
                "position": position,
                "size": max(24, min(int(raw.get("size") or 52), 96)),
                "fade": bool(raw.get("fade", True)),
                "sourceArtifactId": source_id or None,
                "sourceSha256": source_hash or None,
            })

        scene_id = _clean_text(value.get("sceneId"), 80)
        if scene_id:
            scene = self._artifact(con, project_id, scene_id)
            if scene["kind"] != "scene":
                raise VideoWorkstationError("Selected scene is not registered")
        stored_render = value.get("render") if isinstance(value.get("render"), dict) else {}
        size = _clean_text(value.get("size") or stored_render.get("size"), 20) or "720p"
        quality = _clean_text(value.get("quality") or stored_render.get("quality"), 20) or "standard"
        if size not in SIZES or quality not in QUALITIES:
            raise VideoWorkstationError("Unsupported render preset")
        width, height = SIZES[size]
        total = sum(clip["durationSeconds"] for clip in clips)
        crossfades = sum(1 for clip in clips[1:] if clip["transition"] == "crossfade")
        total = round(total - (0.5 * crossfades), 3)
        if total <= 0 or total > MAX_DURATION:
            raise VideoWorkstationError("Composition duration is outside the five-minute bound")
        normalized = {
            "schemaVersion": VIDEO_SCHEMA,
            "title": title,
            "sceneId": scene_id or None,
            "clips": clips,
            "audio": audio,
            "titles": titles,
            "render": {"size": size, "width": width, "height": height, "fps": 30, "quality": quality, "format": "mp4"},
            "durationSeconds": total,
            "status": "inactive-draft",
        }
        return normalized, paths

    def save_composition(self, project_id: str, value: dict[str, Any]) -> dict[str, Any]:
        now, artifact_id = _utc(), str(uuid.uuid4())
        with self._connect() as con:
            if con.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone() is None:
                raise VideoWorkstationError("Project is not registered", 404)
            payload, _ = self._normalize_composition(con, project_id, value)
            digest = hashlib.sha256(_json(payload).encode("utf-8")).hexdigest()
            artifact = {"id": artifact_id, "projectId": project_id, "kind": "video-composition", "title": payload["title"], "path": "", "sha256": digest, "createdAt": now, "payload": payload}
            self._insert_artifact(con, artifact)
            source_ids = {clip["sourceArtifactId"] for clip in payload["clips"]}
            source_ids.update(filter(None, [payload.get("sceneId"), payload.get("audio", {}).get("sourceArtifactId") if payload.get("audio") else None]))
            source_ids.update(title["sourceArtifactId"] for title in payload["titles"] if title.get("sourceArtifactId"))
            source_ids.update(clip["storyboardItemId"] for clip in payload["clips"] if clip.get("storyboardItemId"))
            for source_id in sorted(source_ids):
                con.execute(
                    "INSERT INTO artifact_relationships VALUES(?,?,?,?,?,?,?,?,?)",
                    (str(uuid.uuid4()), source_id, artifact_id, project_id, "video-composition-source", artifact_id, "active", now, now),
                )
            receipt_id = self._receipt(con, project_id, "video.composition.saved", {"compositionId": artifact_id, "sha256": digest, "sourceArtifactIds": sorted(source_ids), "inactive": True})
        return {"ok": True, "artifact": artifact, "receiptId": receipt_id}

    def summary(self, project_id: str) -> dict[str, Any]:
        with self._connect() as con:
            if con.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone() is None:
                raise VideoWorkstationError("Project is not registered", 404)
            rows = con.execute(
                "SELECT * FROM artifacts WHERE project_id=? AND kind IN ('scene','image','document','writing-draft','music-render','storyboard-item','media-route','video-composition','video-render') ORDER BY updated_at DESC",
                (project_id,),
            ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload"] or "{}")
            items.append(item)
        return {"ok": True, "projectId": project_id, "runtime": self.runtime_status(), "items": items}

    def composition(self, project_id: str, composition_id: str) -> tuple[sqlite3.Row, dict[str, Any], dict[str, Path]]:
        with self._connect() as con:
            row = self._artifact(con, project_id, composition_id)
            if row["kind"] != "video-composition":
                raise VideoWorkstationError("That artifact is not a Video composition", 409)
            stored = json.loads(row["payload"] or "{}")
            normalized, paths = self._normalize_composition(con, project_id, stored)
            if hashlib.sha256(_json(stored).encode("utf-8")).hexdigest() != row["sha256"]:
                raise VideoWorkstationError("The saved composition record changed", 409, "composition_hash_mismatch")
        return row, normalized, paths

    @staticmethod
    def _filter_path(path: Path) -> str:
        return path.resolve().as_posix().replace(":", "\\:").replace("'", "\\'")

    @staticmethod
    def _motion_filter(motion: str, width: int, height: int, fps: int, duration: float) -> str:
        base = f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},setsar=1"
        frames = max(1, round(duration * fps))
        if motion == "still":
            return f"{base},fps={fps},trim=duration={duration},setpts=PTS-STARTPTS"
        zoom = "min(max(zoom,pzoom)+0.0008,1.10)" if motion == "zoom-in" else "if(eq(on,1),1.10,max(1.0,pzoom-0.0008))"
        x = "iw/2-(iw/zoom/2)"
        y = "ih/2-(ih/zoom/2)"
        if motion == "pan-left":
            zoom, x = "1.10", f"(iw-iw/zoom)*(1-on/{frames})"
        elif motion == "pan-right":
            zoom, x = "1.10", f"(iw-iw/zoom)*(on/{frames})"
        elif motion == "pan-up":
            zoom, y = "1.10", f"(ih-ih/zoom)*(1-on/{frames})"
        elif motion == "pan-down":
            zoom, y = "1.10", f"(ih-ih/zoom)*(on/{frames})"
        return f"{base},zoompan=z='{zoom}':x='{x}':y='{y}':d=1:s={width}x{height}:fps={fps},trim=duration={duration},setpts=PTS-STARTPTS"

    def _build_filter(self, payload: dict[str, Any], temp: Path) -> tuple[str, list[Path]]:
        width, height, fps = payload["render"]["width"], payload["render"]["height"], payload["render"]["fps"]
        lines: list[str] = []
        text_files: list[Path] = []
        for index, clip in enumerate(payload["clips"]):
            motion = self._motion_filter(clip["motion"], width, height, fps, clip["durationSeconds"])
            lines.append(f"[{index}:v]{motion},format=yuv420p[v{index}]")
        current = "v0"
        offset = payload["clips"][0]["durationSeconds"]
        for index in range(1, len(payload["clips"])):
            transition = payload["clips"][index]["transition"]
            fade = 0.5 if transition == "crossfade" else 0.001
            offset -= fade
            label = f"vx{index}"
            lines.append(f"[{current}][v{index}]xfade=transition=fade:duration={fade}:offset={max(0.0, offset):.3f}[{label}]")
            current = label
            offset += payload["clips"][index]["durationSeconds"]
        for index, title in enumerate(payload["titles"]):
            text_file = temp / f"title-{index}.txt"
            text_file.write_text(title["text"], encoding="utf-8")
            text_files.append(text_file)
            position = {"top": "h*0.10", "center": "(h-text_h)/2", "bottom": "h-text_h-h*0.10"}[title["position"]]
            start = title["startSeconds"]
            end = min(payload["durationSeconds"], start + title["durationSeconds"])
            alpha = (
                f"if(lt(t-{start:.3f},0.35),(t-{start:.3f})/0.35,"
                f"if(gt(t-{max(start, end - 0.35):.3f},0),({end:.3f}-t)/0.35,1))"
                if title["fade"] else "1"
            )
            font = Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts" / "segoeui.ttf"
            label = f"title{index}"
            lines.append(
                f"[{current}]drawtext=fontfile='{self._filter_path(font)}':textfile='{self._filter_path(text_file)}':"
                f"fontcolor=white:fontsize={title['size']}:x=(w-text_w)/2:y={position}:"
                f"borderw=2:bordercolor=black@0.75:alpha='{alpha}':enable='between(t,{start:.3f},{end:.3f})'[{label}]"
            )
            current = label
        lines.append(f"[{current}]format=yuv420p[vout]")
        return ";\n".join(lines), text_files

    def render(self, project_id: str, composition_id: str) -> dict[str, Any]:
        ffmpeg, ffprobe = self._runtime()
        status = self.runtime_status(verify=True)
        if not ffmpeg or not ffprobe or status.get("state") != "READY":
            raise VideoWorkstationError("FFmpeg is not available with the required Video V2 features", 503, "ffmpeg_unavailable")
        row, payload, paths = self.composition(project_id, composition_id)
        root = self._project_root(project_id)
        output_dir = root / "media" / "video"
        output_dir.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        render_id = str(uuid.uuid4())
        with tempfile.TemporaryDirectory(prefix="twis-video-", dir=str(root / "media")) as folder:
            temp = Path(folder)
            output = temp / "output.mp4"
            filter_text, _ = self._build_filter(payload, temp)
            script = temp / "filter.txt"
            script.write_text(filter_text, encoding="utf-8")
            command = [str(ffmpeg), "-hide_banner", "-nostdin", "-y"]
            for clip in payload["clips"]:
                command.extend(["-loop", "1", "-framerate", str(payload["render"]["fps"]), "-t", str(clip["durationSeconds"] + 1), "-i", str(paths[clip["sourceArtifactId"]])])
            audio = payload.get("audio")
            audio_label = None
            if audio and not audio["muted"]:
                command.extend(["-i", str(paths[audio["sourceArtifactId"]])])
                audio_index = len(payload["clips"])
                fade_out_start = max(0.0, payload["durationSeconds"] - audio["fadeOutSeconds"])
                audio_filter = (
                    f"[{audio_index}:a]atrim=start={audio['trimStartSeconds']:.3f},asetpts=PTS-STARTPTS,"
                    f"adelay={round(audio['startSeconds'] * 1000)}|{round(audio['startSeconds'] * 1000)},volume={audio['volume']:.3f}"
                )
                if audio["fadeInSeconds"]:
                    audio_filter += f",afade=t=in:st={audio['startSeconds']:.3f}:d={audio['fadeInSeconds']:.3f}"
                if audio["fadeOutSeconds"]:
                    audio_filter += f",afade=t=out:st={fade_out_start:.3f}:d={audio['fadeOutSeconds']:.3f}"
                audio_filter += f",apad,atrim=duration={payload['durationSeconds']:.3f}[aout]"
                filter_text = script.read_text(encoding="utf-8") + ";\n" + audio_filter
                script.write_text(filter_text, encoding="utf-8")
                audio_label = "[aout]"
            command.extend(["-filter_complex", script.read_text(encoding="utf-8"), "-map", "[vout]"])
            if audio_label:
                command.extend(["-map", audio_label, "-c:a", "aac", "-b:a", "160k"])
            command.extend([
                "-c:v", "libx264", "-preset", "veryfast", "-crf", str(QUALITIES[payload["render"]["quality"]]),
                "-r", str(payload["render"]["fps"]), "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                "-t", str(payload["durationSeconds"]), str(output),
            ])
            try:
                completed = self._run(command, timeout=max(120.0, payload["durationSeconds"] * 12), cwd=temp)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as error:
                detail = (getattr(error, "stderr", "") or str(error))[-2000:]
                with self._connect() as con:
                    receipt_id = self._receipt(con, project_id, "video.render.failed", {"compositionId": composition_id, "renderId": render_id, "error": detail})
                raise VideoWorkstationError("The render stopped before completion. See diagnostics for the bounded FFmpeg error.", 422, "render_failed") from error
            if not output.is_file() or output.stat().st_size < 1024:
                raise VideoWorkstationError("FFmpeg returned without a valid video file", 422, "render_output_missing")
            probe = self._run([str(ffprobe), "-v", "error", "-show_streams", "-show_format", "-of", "json", str(output)], timeout=30)
            metadata = json.loads(probe.stdout)
            streams = metadata.get("streams", [])
            video_stream = next((item for item in streams if item.get("codec_type") == "video"), None)
            audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
            if not video_stream:
                raise VideoWorkstationError("Rendered output has no video stream", 422, "render_invalid")
            duration = float(metadata.get("format", {}).get("duration") or video_stream.get("duration") or 0)
            if abs(duration - payload["durationSeconds"]) > 0.35:
                raise VideoWorkstationError("Rendered duration does not match the composition", 422, "render_duration_mismatch")
            digest = _sha(output)
            target = output_dir / f"{digest}.mp4"
            target_created = not target.exists()
            if target_created:
                shutil.move(str(output), target)
            elapsed = round(time.perf_counter() - started, 3)

        now = _utc()
        relative = target.relative_to(root).as_posix()
        source_refs = [{"artifactId": clip["sourceArtifactId"], "sha256": clip["sourceSha256"]} for clip in payload["clips"]]
        if payload.get("audio"):
            source_refs.append({"artifactId": payload["audio"]["sourceArtifactId"], "sha256": payload["audio"]["sourceSha256"]})
        result_payload = {
            "schemaVersion": RENDER_SCHEMA,
            "compositionId": composition_id,
            "compositionSha256": row["sha256"],
            "sourceRefs": source_refs,
            "format": "mp4",
            "videoCodec": video_stream.get("codec_name"),
            "audioCodec": audio_stream.get("codec_name") if audio_stream else None,
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "fps": payload["render"]["fps"],
            "durationSeconds": duration,
            "size": target.stat().st_size,
            "sha256": digest,
            "runtime": {"version": status.get("version"), "ffmpegSha256": status.get("ffmpegSha256"), "path": str(ffmpeg)},
            "renderSeconds": elapsed,
            "status": "inactive-draft",
            "generatedVideo": False,
        }
        artifact_id = str(uuid.uuid4())
        artifact = {"id": artifact_id, "projectId": project_id, "kind": "video-render", "title": f"{payload['title']} render", "path": relative, "sha256": digest, "createdAt": now, "payload": result_payload}
        try:
            with self._connect() as con:
                self._insert_artifact(con, artifact)
                for source_id in sorted({composition_id, *(item["artifactId"] for item in source_refs)}):
                    con.execute(
                        "INSERT INTO artifact_relationships VALUES(?,?,?,?,?,?,?,?,?)",
                        (str(uuid.uuid4()), source_id, artifact_id, project_id, "video-render-source", render_id, "active", now, now),
                    )
                receipt_id = self._receipt(con, project_id, "video.render.completed", {"renderId": render_id, "compositionId": composition_id, "artifactId": artifact_id, "sha256": digest, "durationSeconds": duration, "runtimeSha256": status.get("ffmpegSha256"), "renderSeconds": elapsed})
        except Exception:
            if target_created and target.is_file():
                target.unlink()
            raise
        return {"ok": True, "artifact": artifact, "receiptId": receipt_id, "renderSeconds": elapsed}

    def render_asset(self, artifact_id: str) -> tuple[Path, str]:
        with self._connect() as con:
            row = con.execute("SELECT * FROM artifacts WHERE id=? AND kind='video-render'", (artifact_id,)).fetchone()
        if row is None:
            raise VideoWorkstationError("Video render not found", 404)
        root = self._project_root(row["project_id"])
        path = (root / row["path"]).resolve()
        allowed = (root / "media" / "video").resolve()
        if allowed not in path.parents or not path.is_file():
            raise VideoWorkstationError("Rendered video file is missing", 409)
        if _sha(path) != row["sha256"]:
            raise VideoWorkstationError("Rendered video hash mismatch", 409)
        return path, "video/mp4"

    def delete_file_for_artifact(self, project_id: str, kind: str, relative: str) -> bool:
        if kind != "video-render":
            return False
        root = self._project_root(project_id)
        path = (root / relative).resolve()
        allowed = (root / "media" / "video").resolve()
        if allowed not in path.parents:
            raise VideoWorkstationError("Unsafe video render path", 409)
        if path.is_file():
            path.unlink()
            return True
        return False
