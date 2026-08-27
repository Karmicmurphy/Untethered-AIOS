from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import sqlite3
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


MAX_TITLE_CHARS = 300
MAX_ENTRY_BYTES = 1024 * 1024
MAX_TRANSCRIPT_BYTES = 5 * 1024 * 1024
MAX_LABEL_CHARS = 200
MAX_INSPECTION_BYTES = 512 * 1024
ALLOWED_SPEAKERS = {"owner", "companion", "note", "code", "system"}
ALLOWED_ENTRY_TYPES = {"text", "code", "question", "idea", "note", "voice-draft"}


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS talk_entries(
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  sequence_number INTEGER NOT NULL,
  speaker TEXT NOT NULL,
  entry_type TEXT NOT NULL,
  content TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  source TEXT NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE(artifact_id, sequence_number)
);
CREATE INDEX IF NOT EXISTS talk_entries_artifact_idx
  ON talk_entries(artifact_id, sequence_number);

CREATE TABLE IF NOT EXISTS talk_versions(
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  version_number INTEGER NOT NULL,
  title TEXT NOT NULL,
  transcript_json TEXT NOT NULL,
  transcript_sha256 TEXT NOT NULL,
  entry_count INTEGER NOT NULL,
  label TEXT NOT NULL DEFAULT '',
  cause TEXT NOT NULL,
  actor TEXT NOT NULL,
  parent_version_id TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(artifact_id, version_number)
);
CREATE INDEX IF NOT EXISTS talk_versions_artifact_idx
  ON talk_versions(artifact_id, version_number DESC);

CREATE TABLE IF NOT EXISTS talk_recovery_drafts(
  artifact_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  base_version_number INTEGER NOT NULL,
  speaker TEXT NOT NULL,
  entry_type TEXT NOT NULL,
  content TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS talk_recovery_project_idx
  ON talk_recovery_drafts(project_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS talk_restore_operations(
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  target_version_id TEXT NOT NULL,
  recovery_version_id TEXT NOT NULL,
  restored_version_id TEXT NOT NULL,
  rollback_version_id TEXT,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  rolled_back_at TEXT
);
CREATE INDEX IF NOT EXISTS talk_restore_artifact_idx
  ON talk_restore_operations(artifact_id, created_at DESC);

CREATE TABLE IF NOT EXISTS talk_passages(
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  source_version_number INTEGER NOT NULL,
  entry_id TEXT NOT NULL,
  start_offset INTEGER NOT NULL,
  end_offset INTEGER NOT NULL,
  quoted_text TEXT NOT NULL,
  quoted_sha256 TEXT NOT NULL,
  label TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS talk_passages_artifact_idx
  ON talk_passages(artifact_id, created_at DESC);

CREATE TABLE IF NOT EXISTS talk_exports(
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  source_version_number INTEGER NOT NULL,
  format TEXT NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  include_provenance INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS talk_exports_artifact_idx
  ON talk_exports(artifact_id, created_at DESC);

CREATE TABLE IF NOT EXISTS talk_transfers(
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  source_version_number INTEGER NOT NULL,
  source_sha256 TEXT NOT NULL,
  selection_json TEXT NOT NULL,
  proposed_title TEXT NOT NULL,
  proposed_content TEXT NOT NULL,
  proposed_sha256 TEXT NOT NULL,
  recovery_version_id TEXT NOT NULL,
  status TEXT NOT NULL,
  decision_note TEXT NOT NULL DEFAULT '',
  write_artifact_id TEXT,
  write_version_number INTEGER,
  write_sha256 TEXT,
  created_at TEXT NOT NULL,
  decided_at TEXT,
  rolled_back_at TEXT
);
CREATE INDEX IF NOT EXISTS talk_transfers_artifact_idx
  ON talk_transfers(artifact_id, created_at DESC);

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

CREATE TABLE IF NOT EXISTS talk_inspections(
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  source_kind TEXT NOT NULL,
  source_entry_id TEXT,
  source_artifact_id TEXT,
  source_sha256 TEXT NOT NULL,
  filename TEXT NOT NULL,
  result_json TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS talk_inspections_artifact_idx
  ON talk_inspections(artifact_id, created_at DESC);
"""


class TalkRoomError(Exception):
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


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(SCHEMA_SQL)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _title(value: Any) -> str:
    title = str(value or "Untitled Talk").strip() or "Untitled Talk"
    if len(title) > MAX_TITLE_CHARS:
        raise TalkRoomError(
            "talk_title_too_long",
            f"Talk title must be {MAX_TITLE_CHARS} characters or fewer",
        )
    return title


def _content(value: Any) -> str:
    content = str(value or "")
    if not content.strip():
        raise TalkRoomError("talk_entry_empty", "Add something before saving this entry")
    if len(content.encode("utf-8")) > MAX_ENTRY_BYTES:
        raise TalkRoomError(
            "talk_entry_too_large",
            "One Talk entry cannot exceed 1 MiB",
        )
    return content


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", value).strip(" .-")
    return (cleaned[:90] or "untitled-talk").rstrip(" .")


def _speaker(value: Any) -> str:
    speaker = str(value or "owner").strip().lower()
    if speaker not in ALLOWED_SPEAKERS:
        raise TalkRoomError("talk_speaker_invalid", "Choose an available entry speaker")
    return speaker


def _entry_type(value: Any) -> str:
    entry_type = str(value or "text").strip().lower()
    if entry_type not in ALLOWED_ENTRY_TYPES:
        raise TalkRoomError("talk_entry_type_invalid", "Choose an available entry type")
    return entry_type


def _comparison(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> dict[str, Any]:
    def lines(entries: list[dict[str, Any]]) -> list[str]:
        return [
            f"{entry.get('speaker', 'owner')}: {entry.get('content', '')}"
            for entry in entries
        ]

    before = lines(left)
    after = lines(right)
    matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
    operations: list[dict[str, Any]] = []
    added = removed = replaced = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "insert":
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        else:
            replaced += max(i2 - i1, j2 - j1)
        operations.append(
            {
                "kind": tag,
                "beforeStart": i1 + 1,
                "beforeEnd": i2,
                "afterStart": j1 + 1,
                "afterEnd": j2,
                "before": before[i1:i2],
                "after": after[j1:j2],
            }
        )
    return {
        "changed": before != after,
        "addedEntries": added,
        "removedEntries": removed,
        "replacedEntries": replaced,
        "operations": operations,
    }


def inspect_code_text(text: str, filename: str) -> dict[str, Any]:
    raw = text.encode("utf-8")
    if len(raw) > MAX_INSPECTION_BYTES:
        raise TalkRoomError(
            "talk_inspection_input_too_large",
            "Deterministic inspection is limited to 512 KiB",
        )
    suffix = Path(filename).suffix.lower()
    lines = text.splitlines()
    probable = {
        ".py": "Python",
        ".js": "JavaScript",
        ".mjs": "JavaScript module",
        ".cjs": "CommonJS JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript JSX",
        ".jsx": "JavaScript JSX",
        ".html": "HTML",
        ".css": "CSS",
        ".json": "JSON",
        ".md": "Markdown",
        ".ps1": "PowerShell",
        ".bat": "Windows batch",
    }.get(suffix, "Plain text or unknown")
    imports: list[str] = []
    functions: list[str] = []
    classes: list[str] = []
    markers: list[dict[str, Any]] = []
    normalized: list[str] = []
    for number, line in enumerate(lines, start=1):
        stripped = line.strip()
        if re.match(r"^(?:from\s+\S+\s+import\s+|import\s+\S+)", stripped):
            imports.append(stripped)
        elif re.match(r"^(?:import\s+.+\s+from\s+|const\s+\S+\s*=\s*require\()", stripped):
            imports.append(stripped)
        match = re.match(
            r"^(?:async\s+)?(?:def|function)\s+([A-Za-z_$][\w$]*)|^([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(",
            stripped,
        )
        if match:
            functions.append(match.group(1) or match.group(2))
        match = re.match(r"^class\s+([A-Za-z_$][\w$]*)", stripped)
        if match:
            classes.append(match.group(1))
        for marker in re.finditer(r"\b(TODO|FIXME)\b", line, re.IGNORECASE):
            markers.append(
                {
                    "line": number,
                    "marker": marker.group(1).upper(),
                    "text": stripped[:240],
                }
            )
        if stripped and len(stripped) >= 8:
            normalized.append(stripped)
    repeated = [
        {"text": line[:240], "count": count}
        for line, count in Counter(normalized).most_common()
        if count > 1
    ][:50]
    return {
        "schemaVersion": "talk-deterministic-inspection-v1",
        "probableType": probable,
        "probableTypeBasis": "filename extension and lexical rules only",
        "filename": Path(filename).name or "pasted-code.txt",
        "bytes": len(raw),
        "characters": len(text),
        "lines": len(lines),
        "importsOrDependencies": imports[:100],
        "functions": functions[:100],
        "classes": classes[:100],
        "markers": markers[:100],
        "repeatedLines": repeated,
        "truncatedFindings": any(
            len(value) > 100 for value in (imports, functions, classes, markers)
        ),
        "semanticUnderstandingClaimed": False,
        "sourceExecuted": False,
        "networkUsed": False,
        "aiModelUsed": False,
        "shellUsed": False,
    }


class TalkRoom:
    def __init__(
        self,
        connection_factory: Callable[[], sqlite3.Connection],
        projects_root: Path,
    ) -> None:
        self._connect = connection_factory
        self._projects_root = projects_root

    def _receipt(
        self,
        con: sqlite3.Connection,
        project_id: str,
        action: str,
        actor: str,
        details: dict[str, Any],
    ) -> str:
        receipt_id = str(uuid.uuid4())
        con.execute(
            "INSERT INTO receipts VALUES(?,?,?,?,?,?)",
            (
                receipt_id,
                project_id,
                action,
                actor,
                json.dumps(details, ensure_ascii=False),
                utc_now(),
            ),
        )
        return receipt_id

    def _project_exists(self, con: sqlite3.Connection, project_id: str) -> None:
        if not con.execute(
            "SELECT 1 FROM projects WHERE id=?", (project_id,)
        ).fetchone():
            raise TalkRoomError("project_not_found", "Project not found", status=404)

    def _artifact_row(self, con: sqlite3.Connection, artifact_id: str) -> sqlite3.Row:
        row = con.execute(
            "SELECT * FROM artifacts WHERE id=? AND kind='conversation'",
            (artifact_id,),
        ).fetchone()
        if not row:
            raise TalkRoomError("talk_session_not_found", "Talk session not found", status=404)
        payload = _json(row["payload"], {})
        if payload.get("schemaVersion") != "talk-session-v1":
            raise TalkRoomError(
                "talk_session_legacy",
                "This older conversation is preserved but is not a durable Talk session",
                status=409,
            )
        return row

    def _version_row(
        self, con: sqlite3.Connection, artifact_id: str, version_number: int
    ) -> sqlite3.Row:
        row = con.execute(
            """
            SELECT * FROM talk_versions
            WHERE artifact_id=? AND version_number=?
            """,
            (artifact_id, version_number),
        ).fetchone()
        if not row:
            raise TalkRoomError("talk_version_not_found", "Talk version not found", status=404)
        return row

    def _entries(self, version: sqlite3.Row) -> list[dict[str, Any]]:
        entries = _json(version["transcript_json"], [])
        return entries if isinstance(entries, list) else []

    def _payload(
        self,
        *,
        current_version: int,
        version_count: int,
        entry_count: int,
        saved_at: str,
    ) -> dict[str, Any]:
        return {
            "schemaVersion": "talk-session-v1",
            "currentVersion": current_version,
            "versionCount": version_count,
            "entryCount": entry_count,
            "lastSavedAt": saved_at,
            "origin": "talk-room",
        }

    def _index(
        self,
        con: sqlite3.Connection,
        artifact_id: str,
        project_id: str,
        title: str,
        entries: list[dict[str, Any]],
    ) -> None:
        content = "\n".join(str(entry.get("content") or "") for entry in entries)
        con.execute("DELETE FROM artifact_search WHERE id=?", (artifact_id,))
        con.execute(
            """
            INSERT INTO artifact_search(id,project_id,title,kind,content)
            VALUES(?,?,?,?,?)
            """,
            (artifact_id, project_id, title, "conversation", f"{title} talk {content}"),
        )

    def _insert_version(
        self,
        con: sqlite3.Connection,
        *,
        artifact_id: str,
        project_id: str,
        version_number: int,
        title: str,
        entries: list[dict[str, Any]],
        label: str,
        cause: str,
        actor: str,
        parent_version_id: str | None,
    ) -> sqlite3.Row:
        transcript_json = canonical_json(entries)
        if len(transcript_json.encode("utf-8")) > MAX_TRANSCRIPT_BYTES:
            raise TalkRoomError(
                "talk_transcript_too_large",
                "This Talk transcript exceeds the 5 MiB local session limit",
            )
        version_id = str(uuid.uuid4())
        con.execute(
            """
            INSERT INTO talk_versions(
              id,artifact_id,project_id,version_number,title,transcript_json,
              transcript_sha256,entry_count,label,cause,actor,parent_version_id,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                version_id,
                artifact_id,
                project_id,
                version_number,
                title,
                transcript_json,
                sha256_text(transcript_json),
                len(entries),
                label[:MAX_LABEL_CHARS],
                cause,
                actor,
                parent_version_id,
                utc_now(),
            ),
        )
        return con.execute(
            "SELECT * FROM talk_versions WHERE id=?", (version_id,)
        ).fetchone()

    def _set_current(
        self,
        con: sqlite3.Connection,
        row: sqlite3.Row,
        version: sqlite3.Row,
    ) -> None:
        entries = self._entries(version)
        count = con.execute(
            "SELECT COUNT(*) FROM talk_versions WHERE artifact_id=?", (row["id"],)
        ).fetchone()[0]
        payload = self._payload(
            current_version=version["version_number"],
            version_count=count,
            entry_count=len(entries),
            saved_at=version["created_at"],
        )
        con.execute(
            """
            UPDATE artifacts
            SET title=?, payload=?, sha256=?, updated_at=?, authority_state='DRAFT'
            WHERE id=?
            """,
            (
                version["title"],
                json.dumps(payload, ensure_ascii=False),
                version["transcript_sha256"],
                version["created_at"],
                row["id"],
            ),
        )
        con.execute(
            "UPDATE projects SET updated_at=? WHERE id=?",
            (version["created_at"], row["project_id"]),
        )
        self._index(
            con,
            row["id"],
            row["project_id"],
            version["title"],
            entries,
        )

    def _serialize_version(
        self, row: sqlite3.Row, *, include_entries: bool = False
    ) -> dict[str, Any]:
        result = {
            "id": row["id"],
            "number": row["version_number"],
            "title": row["title"],
            "sha256": row["transcript_sha256"],
            "entryCount": row["entry_count"],
            "label": row["label"],
            "cause": row["cause"],
            "actor": row["actor"],
            "parentVersionId": row["parent_version_id"],
            "createdAt": row["created_at"],
        }
        if include_entries:
            result["entries"] = self._entries(row)
        return result

    def _serialize_transfer(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "artifactId": row["artifact_id"],
            "sourceVersion": row["source_version_number"],
            "sourceSha256": row["source_sha256"],
            "selection": _json(row["selection_json"], {}),
            "proposedTitle": row["proposed_title"],
            "proposedContent": row["proposed_content"],
            "proposedSha256": row["proposed_sha256"],
            "status": row["status"],
            "decisionNote": row["decision_note"],
            "writeArtifactId": row["write_artifact_id"],
            "createdAt": row["created_at"],
            "decidedAt": row["decided_at"],
            "rolledBackAt": row["rolled_back_at"],
        }

    def _serialize_session(
        self, con: sqlite3.Connection, row: sqlite3.Row, *, full: bool
    ) -> dict[str, Any]:
        payload = _json(row["payload"], {})
        recovery = con.execute(
            "SELECT * FROM talk_recovery_drafts WHERE artifact_id=?", (row["id"],)
        ).fetchone()
        result: dict[str, Any] = {
            "id": row["id"],
            "projectId": row["project_id"],
            "title": row["title"],
            "sha256": row["sha256"],
            "currentVersion": int(payload.get("currentVersion") or 0),
            "versionCount": int(payload.get("versionCount") or 0),
            "entryCount": int(payload.get("entryCount") or 0),
            "lastSavedAt": payload.get("lastSavedAt") or row["updated_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "hasRecovery": bool(recovery),
            "recoveryUpdatedAt": recovery["updated_at"] if recovery else None,
        }
        if not full:
            return result
        version = self._version_row(con, row["id"], result["currentVersion"])
        result["entries"] = self._entries(version)
        versions = con.execute(
            """
            SELECT * FROM talk_versions
            WHERE artifact_id=? ORDER BY version_number DESC
            """,
            (row["id"],),
        ).fetchall()
        result["versions"] = [self._serialize_version(value) for value in versions]
        result["recovery"] = (
            {
                "baseVersion": recovery["base_version_number"],
                "speaker": recovery["speaker"],
                "entryType": recovery["entry_type"],
                "content": recovery["content"],
                "sha256": recovery["content_sha256"],
                "createdAt": recovery["created_at"],
                "updatedAt": recovery["updated_at"],
            }
            if recovery
            else None
        )
        passages = con.execute(
            """
            SELECT * FROM talk_passages
            WHERE artifact_id=? ORDER BY created_at DESC LIMIT 100
            """,
            (row["id"],),
        ).fetchall()
        result["passages"] = [
            {
                "id": value["id"],
                "entryId": value["entry_id"],
                "sourceVersion": value["source_version_number"],
                "quote": value["quoted_text"],
                "label": value["label"],
                "createdAt": value["created_at"],
            }
            for value in passages
        ]
        transfers = con.execute(
            """
            SELECT * FROM talk_transfers
            WHERE artifact_id=? ORDER BY created_at DESC LIMIT 20
            """,
            (row["id"],),
        ).fetchall()
        result["transfers"] = [self._serialize_transfer(value) for value in transfers]
        return result

    def list_sessions(self, project_id: str, search: str = "") -> list[dict[str, Any]]:
        with self._connect() as con:
            values: list[Any] = [project_id, '%"talk-session-v1"%']
            sql = (
                "SELECT * FROM artifacts "
                "WHERE kind='conversation' AND project_id=? AND payload LIKE ?"
            )
            if search.strip():
                sql += " AND (title LIKE ? OR payload LIKE ?)"
                pattern = f"%{search.strip()}%"
                values.extend([pattern, pattern])
            sql += " ORDER BY updated_at DESC"
            rows = con.execute(sql, values).fetchall()
            return [
                self._serialize_session(con, row, full=False) for row in rows
            ]

    def get_session(self, artifact_id: str) -> dict[str, Any]:
        with self._connect() as con:
            return self._serialize_session(
                con, self._artifact_row(con, artifact_id), full=True
            )

    def create_session(
        self,
        project_id: str,
        title: Any,
        initial_content: Any = "",
        *,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        title_value = _title(title)
        with self._connect() as con:
            self._project_exists(con, project_id)
            artifact_id = str(uuid.uuid4())
            now = utc_now()
            entries: list[dict[str, Any]] = []
            initial = str(initial_content or "")
            if initial.strip():
                content = _content(initial)
                entry_id = str(uuid.uuid4())
                entry = {
                    "id": entry_id,
                    "sequence": 1,
                    "speaker": "owner",
                    "entryType": "text",
                    "content": content,
                    "sha256": sha256_text(content),
                    "source": "created",
                    "createdAt": now,
                }
                entries.append(entry)
                con.execute(
                    "INSERT INTO talk_entries VALUES(?,?,?,?,?,?,?,?,?,?)",
                    (
                        entry_id,
                        artifact_id,
                        project_id,
                        1,
                        "owner",
                        "text",
                        content,
                        entry["sha256"],
                        "created",
                        now,
                    ),
                )
            transcript_json = canonical_json(entries)
            con.execute(
                """
                INSERT INTO artifacts(
                  id,project_id,kind,title,path,payload,authority_state,sha256,
                  created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    artifact_id,
                    project_id,
                    "conversation",
                    title_value,
                    "",
                    json.dumps(
                        self._payload(
                            current_version=1,
                            version_count=1,
                            entry_count=len(entries),
                            saved_at=now,
                        ),
                        ensure_ascii=False,
                    ),
                    "DRAFT",
                    sha256_text(transcript_json),
                    now,
                    now,
                ),
            )
            version = self._insert_version(
                con,
                artifact_id=artifact_id,
                project_id=project_id,
                version_number=1,
                title=title_value,
                entries=entries,
                label="Created",
                cause="created",
                actor=actor,
                parent_version_id=None,
            )
            self._index(con, artifact_id, project_id, title_value, entries)
            self._receipt(
                con,
                project_id,
                "talk.create",
                actor,
                {
                    "artifactId": artifact_id,
                    "version": 1,
                    "transcriptSha256": version["transcript_sha256"],
                    "entryCount": len(entries),
                },
            )
            con.execute(
                "UPDATE projects SET updated_at=? WHERE id=?", (now, project_id)
            )
            con.commit()
        return self.get_session(artifact_id)

    def save_recovery(
        self,
        artifact_id: str,
        *,
        content: Any,
        base_version: Any,
        speaker: Any = "owner",
        entry_type: Any = "text",
    ) -> dict[str, Any]:
        content_value = _content(content)
        speaker_value = _speaker(speaker)
        entry_type_value = _entry_type(entry_type)
        try:
            base = int(base_version)
        except (TypeError, ValueError) as exc:
            raise TalkRoomError(
                "talk_base_version_required", "Current Talk version is required"
            ) from exc
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            payload = _json(row["payload"], {})
            current = int(payload.get("currentVersion") or 0)
            if base != current:
                raise TalkRoomError(
                    "talk_version_conflict",
                    "This Talk session changed after it was opened",
                    status=409,
                    details={"expectedVersion": base, "currentVersion": current},
                )
            now = utc_now()
            existing = con.execute(
                "SELECT created_at FROM talk_recovery_drafts WHERE artifact_id=?",
                (artifact_id,),
            ).fetchone()
            con.execute(
                """
                INSERT INTO talk_recovery_drafts(
                  artifact_id,project_id,base_version_number,speaker,entry_type,
                  content,content_sha256,created_at,updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(artifact_id) DO UPDATE SET
                  base_version_number=excluded.base_version_number,
                  speaker=excluded.speaker,
                  entry_type=excluded.entry_type,
                  content=excluded.content,
                  content_sha256=excluded.content_sha256,
                  updated_at=excluded.updated_at
                """,
                (
                    artifact_id,
                    row["project_id"],
                    base,
                    speaker_value,
                    entry_type_value,
                    content_value,
                    sha256_text(content_value),
                    existing["created_at"] if existing else now,
                    now,
                ),
            )
            con.commit()
            return {
                "ok": True,
                "artifactId": artifact_id,
                "baseVersion": base,
                "sha256": sha256_text(content_value),
                "updatedAt": now,
            }

    def discard_recovery(self, artifact_id: str) -> dict[str, Any]:
        with self._connect() as con:
            self._artifact_row(con, artifact_id)
            con.execute(
                "DELETE FROM talk_recovery_drafts WHERE artifact_id=?",
                (artifact_id,),
            )
            con.commit()
        return {"ok": True, "artifactId": artifact_id, "hasRecovery": False}

    def append_entry(
        self,
        artifact_id: str,
        *,
        content: Any,
        base_version: Any,
        title: Any = None,
        speaker: Any = "owner",
        entry_type: Any = "text",
        source: str = "typed",
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        content_value = _content(content)
        speaker_value = _speaker(speaker)
        entry_type_value = _entry_type(entry_type)
        if source not in {"typed", "pasted", "recovery", "voice-draft-approved"}:
            raise TalkRoomError("talk_entry_source_invalid", "Entry source is not supported")
        try:
            base = int(base_version)
        except (TypeError, ValueError) as exc:
            raise TalkRoomError(
                "talk_base_version_required", "Current Talk version is required"
            ) from exc
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            payload = _json(row["payload"], {})
            current = int(payload.get("currentVersion") or 0)
            if base != current:
                raise TalkRoomError(
                    "talk_version_conflict",
                    "This Talk session changed after it was opened",
                    status=409,
                    details={"expectedVersion": base, "currentVersion": current},
                )
            current_version = self._version_row(con, artifact_id, current)
            entries = self._entries(current_version)
            sequence = (
                con.execute(
                    "SELECT COALESCE(MAX(sequence_number),0)+1 FROM talk_entries WHERE artifact_id=?",
                    (artifact_id,),
                ).fetchone()[0]
            )
            now = utc_now()
            entry_id = str(uuid.uuid4())
            entry = {
                "id": entry_id,
                "sequence": sequence,
                "speaker": speaker_value,
                "entryType": entry_type_value,
                "content": content_value,
                "sha256": sha256_text(content_value),
                "source": source,
                "createdAt": now,
            }
            con.execute(
                "INSERT INTO talk_entries VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    entry_id,
                    artifact_id,
                    row["project_id"],
                    sequence,
                    speaker_value,
                    entry_type_value,
                    content_value,
                    entry["sha256"],
                    source,
                    now,
                ),
            )
            entries.append(entry)
            version = self._insert_version(
                con,
                artifact_id=artifact_id,
                project_id=row["project_id"],
                version_number=current + 1,
                title=_title(title if title is not None else row["title"]),
                entries=entries,
                label="Entry saved",
                cause="entry",
                actor=actor,
                parent_version_id=current_version["id"],
            )
            self._set_current(con, row, version)
            con.execute(
                "DELETE FROM talk_recovery_drafts WHERE artifact_id=?",
                (artifact_id,),
            )
            receipt_id = self._receipt(
                con,
                row["project_id"],
                "talk.entry.append",
                actor,
                {
                    "artifactId": artifact_id,
                    "entryId": entry_id,
                    "version": current + 1,
                    "contentSha256": entry["sha256"],
                    "source": source,
                },
            )
            con.commit()
        result = self.get_session(artifact_id)
        result["receiptId"] = receipt_id
        return result

    def rename_session(
        self,
        artifact_id: str,
        *,
        title: Any,
        base_version: Any,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        title_value = _title(title)
        try:
            base = int(base_version)
        except (TypeError, ValueError) as exc:
            raise TalkRoomError(
                "talk_base_version_required", "Current Talk version is required"
            ) from exc
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            current = int(_json(row["payload"], {}).get("currentVersion") or 0)
            if base != current:
                raise TalkRoomError(
                    "talk_version_conflict",
                    "This Talk session changed after it was opened",
                    status=409,
                    details={"expectedVersion": base, "currentVersion": current},
                )
            current_version = self._version_row(con, artifact_id, current)
            if current_version["title"] == title_value:
                result = self._serialize_session(con, row, full=True)
                result["changed"] = False
                return result
            version = self._insert_version(
                con,
                artifact_id=artifact_id,
                project_id=row["project_id"],
                version_number=current + 1,
                title=title_value,
                entries=self._entries(current_version),
                label="Title changed",
                cause="title",
                actor=actor,
                parent_version_id=current_version["id"],
            )
            self._set_current(con, row, version)
            receipt_id = self._receipt(
                con,
                row["project_id"],
                "talk.title",
                actor,
                {
                    "artifactId": artifact_id,
                    "version": current + 1,
                    "titleSha256": sha256_text(title_value),
                    "transcriptSha256": version["transcript_sha256"],
                },
            )
            con.commit()
        result = self.get_session(artifact_id)
        result["changed"] = True
        result["receiptId"] = receipt_id
        return result

    def snapshot(
        self,
        artifact_id: str,
        *,
        base_version: Any,
        label: Any,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        label_value = str(label or "").strip()
        if not label_value:
            raise TalkRoomError("talk_snapshot_label_required", "Give this snapshot a name")
        if len(label_value) > MAX_LABEL_CHARS:
            raise TalkRoomError(
                "talk_snapshot_label_too_long",
                f"Snapshot name must be {MAX_LABEL_CHARS} characters or fewer",
            )
        try:
            base = int(base_version)
        except (TypeError, ValueError) as exc:
            raise TalkRoomError(
                "talk_base_version_required", "Current Talk version is required"
            ) from exc
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            current = int(_json(row["payload"], {}).get("currentVersion") or 0)
            if base != current:
                raise TalkRoomError(
                    "talk_version_conflict",
                    "This Talk session changed after it was opened",
                    status=409,
                    details={"expectedVersion": base, "currentVersion": current},
                )
            parent = self._version_row(con, artifact_id, current)
            version = self._insert_version(
                con,
                artifact_id=artifact_id,
                project_id=row["project_id"],
                version_number=current + 1,
                title=parent["title"],
                entries=self._entries(parent),
                label=label_value,
                cause="snapshot",
                actor=actor,
                parent_version_id=parent["id"],
            )
            self._set_current(con, row, version)
            receipt_id = self._receipt(
                con,
                row["project_id"],
                "talk.snapshot",
                actor,
                {
                    "artifactId": artifact_id,
                    "version": current + 1,
                    "label": label_value,
                    "transcriptSha256": version["transcript_sha256"],
                },
            )
            con.commit()
        result = self.get_session(artifact_id)
        result["receiptId"] = receipt_id
        return result

    def compare_versions(
        self, artifact_id: str, left_version: Any, right_version: Any
    ) -> dict[str, Any]:
        try:
            left_number = int(left_version)
            right_number = int(right_version)
        except (TypeError, ValueError) as exc:
            raise TalkRoomError(
                "talk_versions_required", "Choose two Talk versions to compare"
            ) from exc
        with self._connect() as con:
            self._artifact_row(con, artifact_id)
            left = self._version_row(con, artifact_id, left_number)
            right = self._version_row(con, artifact_id, right_number)
            return {
                "artifactId": artifact_id,
                "left": self._serialize_version(left),
                "right": self._serialize_version(right),
                "comparison": _comparison(self._entries(left), self._entries(right)),
            }

    def restore(
        self,
        artifact_id: str,
        *,
        target_version: Any,
        base_version: Any,
        confirmed: Any,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        if confirmed is not True:
            raise TalkRoomError(
                "talk_restore_confirmation_required",
                "Restore must be explicitly confirmed",
            )
        try:
            target_number = int(target_version)
            base = int(base_version)
        except (TypeError, ValueError) as exc:
            raise TalkRoomError(
                "talk_versions_required", "Target and current versions are required"
            ) from exc
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            current = int(_json(row["payload"], {}).get("currentVersion") or 0)
            if base != current:
                raise TalkRoomError(
                    "talk_version_conflict",
                    "This Talk session changed after it was opened",
                    status=409,
                    details={"expectedVersion": base, "currentVersion": current},
                )
            current_row = self._version_row(con, artifact_id, current)
            target = self._version_row(con, artifact_id, target_number)
            recovery = self._insert_version(
                con,
                artifact_id=artifact_id,
                project_id=row["project_id"],
                version_number=current + 1,
                title=current_row["title"],
                entries=self._entries(current_row),
                label="Before restore",
                cause="restore-recovery",
                actor=actor,
                parent_version_id=current_row["id"],
            )
            restored = self._insert_version(
                con,
                artifact_id=artifact_id,
                project_id=row["project_id"],
                version_number=current + 2,
                title=target["title"],
                entries=self._entries(target),
                label=f"Restored version {target_number}",
                cause="restore",
                actor=actor,
                parent_version_id=recovery["id"],
            )
            self._set_current(con, row, restored)
            operation_id = str(uuid.uuid4())
            now = utc_now()
            con.execute(
                "INSERT INTO talk_restore_operations VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    operation_id,
                    artifact_id,
                    row["project_id"],
                    target["id"],
                    recovery["id"],
                    restored["id"],
                    None,
                    "active",
                    now,
                    None,
                ),
            )
            receipt_id = self._receipt(
                con,
                row["project_id"],
                "talk.restore",
                actor,
                {
                    "artifactId": artifact_id,
                    "operationId": operation_id,
                    "targetVersion": target_number,
                    "recoveryVersion": current + 1,
                    "restoredVersion": current + 2,
                },
            )
            con.commit()
        result = self.get_session(artifact_id)
        result["restoreOperationId"] = operation_id
        result["receiptId"] = receipt_id
        return result

    def rollback_restore(
        self,
        operation_id: str,
        *,
        confirmed: Any,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        if confirmed is not True:
            raise TalkRoomError(
                "talk_rollback_confirmation_required",
                "Rollback must be explicitly confirmed",
            )
        with self._connect() as con:
            operation = con.execute(
                "SELECT * FROM talk_restore_operations WHERE id=?", (operation_id,)
            ).fetchone()
            if not operation:
                raise TalkRoomError(
                    "talk_restore_operation_not_found",
                    "Restore operation not found",
                    status=404,
                )
            if operation["status"] != "active":
                raise TalkRoomError(
                    "talk_restore_not_active",
                    "This restore is no longer active",
                    status=409,
                )
            row = self._artifact_row(con, operation["artifact_id"])
            current = int(_json(row["payload"], {}).get("currentVersion") or 0)
            current_row = self._version_row(con, row["id"], current)
            if current_row["id"] != operation["restored_version_id"]:
                raise TalkRoomError(
                    "talk_restore_rollback_stale",
                    "Newer Talk work exists, so automatic rollback was blocked",
                    status=409,
                )
            recovery = con.execute(
                "SELECT * FROM talk_versions WHERE id=?",
                (operation["recovery_version_id"],),
            ).fetchone()
            rollback = self._insert_version(
                con,
                artifact_id=row["id"],
                project_id=row["project_id"],
                version_number=current + 1,
                title=recovery["title"],
                entries=self._entries(recovery),
                label="Restore undone",
                cause="restore-rollback",
                actor=actor,
                parent_version_id=current_row["id"],
            )
            self._set_current(con, row, rollback)
            now = utc_now()
            con.execute(
                """
                UPDATE talk_restore_operations
                SET rollback_version_id=?, status='rolled_back', rolled_back_at=?
                WHERE id=?
                """,
                (rollback["id"], now, operation_id),
            )
            receipt_id = self._receipt(
                con,
                row["project_id"],
                "talk.restore.rollback",
                actor,
                {
                    "artifactId": row["id"],
                    "operationId": operation_id,
                    "rollbackVersion": current + 1,
                },
            )
            con.commit()
        result = self.get_session(row["id"])
        result["receiptId"] = receipt_id
        return result

    def mark_passage(
        self,
        artifact_id: str,
        *,
        entry_id: Any,
        start_offset: Any,
        end_offset: Any,
        label: Any = "",
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        try:
            start = int(start_offset)
            end = int(end_offset)
        except (TypeError, ValueError) as exc:
            raise TalkRoomError(
                "talk_passage_range_invalid", "Select a valid passage"
            ) from exc
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            current = int(_json(row["payload"], {}).get("currentVersion") or 0)
            version = self._version_row(con, artifact_id, current)
            entry = next(
                (
                    value
                    for value in self._entries(version)
                    if value.get("id") == str(entry_id or "")
                ),
                None,
            )
            if not entry:
                raise TalkRoomError(
                    "talk_passage_entry_not_current",
                    "That entry is not in the current Talk transcript",
                    status=409,
                )
            text = str(entry.get("content") or "")
            if start < 0 or end <= start or end > len(text):
                raise TalkRoomError(
                    "talk_passage_range_invalid", "Select a valid passage"
                )
            quote = text[start:end]
            passage_id = str(uuid.uuid4())
            now = utc_now()
            con.execute(
                "INSERT INTO talk_passages VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    passage_id,
                    artifact_id,
                    row["project_id"],
                    current,
                    entry["id"],
                    start,
                    end,
                    quote,
                    sha256_text(quote),
                    str(label or "Important passage").strip()[:MAX_LABEL_CHARS]
                    or "Important passage",
                    now,
                ),
            )
            receipt_id = self._receipt(
                con,
                row["project_id"],
                "talk.passage.mark",
                actor,
                {
                    "artifactId": artifact_id,
                    "passageId": passage_id,
                    "entryId": entry["id"],
                    "quoteSha256": sha256_text(quote),
                },
            )
            con.commit()
            return {
                "ok": True,
                "passageId": passage_id,
                "quote": quote,
                "label": str(label or "Important passage").strip()
                or "Important passage",
                "receiptId": receipt_id,
                "createdAt": now,
            }

    def _selected_transfer_entries(
        self, entries: list[dict[str, Any]], selection: dict[str, Any]
    ) -> list[dict[str, Any]]:
        mode = str(selection.get("mode") or "complete")
        if mode == "complete":
            return entries
        if mode != "entries":
            raise TalkRoomError(
                "talk_transfer_selection_invalid",
                "Choose the complete transcript or selected entries",
            )
        selected_ids = selection.get("entryIds")
        if not isinstance(selected_ids, list) or not selected_ids:
            raise TalkRoomError(
                "talk_transfer_selection_required", "Select at least one Talk entry"
            )
        wanted = {str(value) for value in selected_ids}
        selected = [entry for entry in entries if str(entry.get("id")) in wanted]
        if len(selected) != len(wanted):
            raise TalkRoomError(
                "talk_transfer_selection_stale",
                "One or more selected entries are not in the current transcript",
                status=409,
            )
        return selected

    def prepare_transfer(
        self,
        artifact_id: str,
        *,
        base_version: Any,
        selection: Any,
        title: Any,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        try:
            base = int(base_version)
        except (TypeError, ValueError) as exc:
            raise TalkRoomError(
                "talk_base_version_required", "Current Talk version is required"
            ) from exc
        if not isinstance(selection, dict):
            raise TalkRoomError(
                "talk_transfer_selection_invalid",
                "Choose the complete transcript or selected entries",
            )
        proposed_title = _title(title)
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            current = int(_json(row["payload"], {}).get("currentVersion") or 0)
            if base != current:
                raise TalkRoomError(
                    "talk_version_conflict",
                    "This Talk session changed after it was opened",
                    status=409,
                    details={"expectedVersion": base, "currentVersion": current},
                )
            source = self._version_row(con, artifact_id, current)
            entries = self._entries(source)
            selected = self._selected_transfer_entries(entries, selection)
            if not selected:
                raise TalkRoomError(
                    "talk_transfer_empty", "There is no transcript content to copy"
                )
            proposed_content = "\n\n".join(
                f"{entry.get('speaker', 'owner').title()}: {entry.get('content', '')}"
                for entry in selected
            )
            recovery = self._insert_version(
                con,
                artifact_id=artifact_id,
                project_id=row["project_id"],
                version_number=current + 1,
                title=source["title"],
                entries=entries,
                label="Before Talk-to-Write",
                cause="transfer-recovery",
                actor=actor,
                parent_version_id=source["id"],
            )
            self._set_current(con, row, recovery)
            transfer_id = str(uuid.uuid4())
            now = utc_now()
            normalized_selection = {
                "mode": str(selection.get("mode") or "complete"),
                "entryCount": len(selected),
                "entryIds": [entry["id"] for entry in selected],
            }
            con.execute(
                """
                INSERT INTO talk_transfers(
                  id,artifact_id,project_id,source_version_number,source_sha256,
                  selection_json,proposed_title,proposed_content,proposed_sha256,
                  recovery_version_id,status,decision_note,write_artifact_id,
                  write_version_number,write_sha256,created_at,decided_at,rolled_back_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    transfer_id,
                    artifact_id,
                    row["project_id"],
                    current + 1,
                    recovery["transcript_sha256"],
                    json.dumps(normalized_selection, ensure_ascii=False),
                    proposed_title,
                    proposed_content,
                    sha256_text(proposed_content),
                    recovery["id"],
                    "awaiting_approval",
                    "",
                    None,
                    None,
                    None,
                    now,
                    None,
                    None,
                ),
            )
            receipt_id = self._receipt(
                con,
                row["project_id"],
                "talk.write.prepare",
                actor,
                {
                    "artifactId": artifact_id,
                    "transferId": transfer_id,
                    "sourceVersion": current + 1,
                    "sourceSha256": recovery["transcript_sha256"],
                    "proposedSha256": sha256_text(proposed_content),
                    "entryCount": len(selected),
                    "decisionRequired": True,
                },
            )
            con.commit()
            transfer = con.execute(
                "SELECT * FROM talk_transfers WHERE id=?", (transfer_id,)
            ).fetchone()
            result = self._serialize_transfer(transfer)
            result["receiptId"] = receipt_id
            return result

    def _create_write_in_transaction(
        self,
        con: sqlite3.Connection,
        *,
        project_id: str,
        title: str,
        content: str,
        actor: str,
    ) -> tuple[str, str, str]:
        if len(title) > 300:
            raise TalkRoomError("write_title_too_long", "Write title is too long")
        if len(content.encode("utf-8")) > 5 * 1024 * 1024:
            raise TalkRoomError("write_content_too_large", "Write content is too large")
        artifact_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        now = utc_now()
        digest = sha256_text(content)
        payload = {
            "schemaVersion": "write-project-v1",
            "body": content,
            "currentVersion": 1,
            "lastSavedAt": now,
            "versionCount": 1,
            "origin": "talk-to-write",
        }
        con.execute(
            """
            INSERT INTO artifacts(
              id,project_id,kind,title,path,payload,authority_state,sha256,
              created_at,updated_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?)
            """,
            (
                artifact_id,
                project_id,
                "document",
                title,
                "",
                json.dumps(payload, ensure_ascii=False),
                "DRAFT",
                digest,
                now,
                now,
            ),
        )
        con.execute(
            """
            INSERT INTO write_versions(
              id,artifact_id,project_id,version_number,title,content,content_sha256,
              label,cause,actor,parent_version_id,created_at
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                version_id,
                artifact_id,
                project_id,
                1,
                title,
                content,
                digest,
                "Created from Talk",
                "created",
                actor,
                None,
                now,
            ),
        )
        con.execute(
            """
            INSERT INTO artifact_search(id,project_id,title,kind,content)
            VALUES(?,?,?,?,?)
            """,
            (artifact_id, project_id, title, "document", f"{title} document {content}"),
        )
        self._receipt(
            con,
            project_id,
            "write.create",
            actor,
            {
                "artifactId": artifact_id,
                "version": 1,
                "contentSha256": digest,
                "origin": "talk-to-write",
            },
        )
        con.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
        return artifact_id, version_id, digest

    def decide_transfer(
        self,
        transfer_id: str,
        *,
        decision: Any,
        note: Any,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        decision_value = str(decision or "").strip().lower()
        if decision_value not in {"approve", "reject"}:
            raise TalkRoomError(
                "talk_transfer_decision_invalid", "Choose approve or reject"
            )
        note_value = str(note or "").strip()
        if decision_value == "approve" and not note_value:
            raise TalkRoomError(
                "talk_transfer_approval_note_required",
                "Add a short approval note before creating the Write document",
            )
        with self._connect() as con:
            transfer = con.execute(
                "SELECT * FROM talk_transfers WHERE id=?", (transfer_id,)
            ).fetchone()
            if not transfer:
                raise TalkRoomError(
                    "talk_transfer_not_found", "Talk-to-Write proposal not found", status=404
                )
            if transfer["status"] != "awaiting_approval":
                raise TalkRoomError(
                    "talk_transfer_already_decided",
                    "This Talk-to-Write proposal was already decided",
                    status=409,
                )
            talk = self._artifact_row(con, transfer["artifact_id"])
            current = int(_json(talk["payload"], {}).get("currentVersion") or 0)
            version = self._version_row(con, talk["id"], current)
            if (
                current != transfer["source_version_number"]
                or version["transcript_sha256"] != transfer["source_sha256"]
            ):
                raise TalkRoomError(
                    "talk_transfer_source_stale",
                    "The Talk session changed after this proposal was prepared",
                    status=409,
                )
            now = utc_now()
            if decision_value == "reject":
                con.execute(
                    """
                    UPDATE talk_transfers
                    SET status='rejected', decision_note=?, decided_at=?
                    WHERE id=?
                    """,
                    (note_value, now, transfer_id),
                )
                receipt_id = self._receipt(
                    con,
                    talk["project_id"],
                    "talk.write.reject",
                    actor,
                    {
                        "artifactId": talk["id"],
                        "transferId": transfer_id,
                        "sourcePreserved": True,
                    },
                )
            else:
                write_id, _, write_sha = self._create_write_in_transaction(
                    con,
                    project_id=talk["project_id"],
                    title=transfer["proposed_title"],
                    content=transfer["proposed_content"],
                    actor=actor,
                )
                con.execute(
                    """
                    UPDATE talk_transfers
                    SET status='approved', decision_note=?, write_artifact_id=?,
                        write_version_number=1, write_sha256=?, decided_at=?
                    WHERE id=?
                    """,
                    (note_value, write_id, write_sha, now, transfer_id),
                )
                relationship_id = str(uuid.uuid4())
                con.execute(
                    "INSERT INTO artifact_relationships VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        relationship_id,
                        talk["id"],
                        write_id,
                        talk["project_id"],
                        "talk-to-write",
                        transfer_id,
                        "active",
                        now,
                        now,
                    ),
                )
                receipt_id = self._receipt(
                    con,
                    talk["project_id"],
                    "talk.write.approve",
                    actor,
                    {
                        "artifactId": talk["id"],
                        "transferId": transfer_id,
                        "writeArtifactId": write_id,
                        "writeSha256": write_sha,
                        "sourcePreserved": True,
                        "relationshipId": relationship_id,
                    },
                )
            con.commit()
            updated = con.execute(
                "SELECT * FROM talk_transfers WHERE id=?", (transfer_id,)
            ).fetchone()
            result = self._serialize_transfer(updated)
            result["receiptId"] = receipt_id
            return result

    def rollback_transfer(
        self,
        transfer_id: str,
        *,
        confirmed: Any,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        if confirmed is not True:
            raise TalkRoomError(
                "talk_transfer_rollback_confirmation_required",
                "Rollback must be explicitly confirmed",
            )
        with self._connect() as con:
            transfer = con.execute(
                "SELECT * FROM talk_transfers WHERE id=?", (transfer_id,)
            ).fetchone()
            if not transfer:
                raise TalkRoomError(
                    "talk_transfer_not_found", "Talk-to-Write proposal not found", status=404
                )
            if transfer["status"] != "approved" or not transfer["write_artifact_id"]:
                raise TalkRoomError(
                    "talk_transfer_not_active",
                    "This Talk-to-Write transfer is not active",
                    status=409,
                )
            write = con.execute(
                "SELECT * FROM artifacts WHERE id=? AND kind='document'",
                (transfer["write_artifact_id"],),
            ).fetchone()
            if not write:
                raise TalkRoomError(
                    "talk_transfer_write_missing",
                    "The created Write document is missing; rollback was stopped",
                    status=409,
                )
            payload = _json(write["payload"], {})
            related_activity = sum(
                con.execute(
                    f"SELECT COUNT(*) FROM {table} WHERE artifact_id=?",
                    (write["id"],),
                ).fetchone()[0]
                for table in (
                    "write_recovery_drafts",
                    "write_proposals",
                    "write_restore_operations",
                    "write_exports",
                )
            )
            version_count = con.execute(
                "SELECT COUNT(*) FROM write_versions WHERE artifact_id=?",
                (write["id"],),
            ).fetchone()[0]
            if (
                int(payload.get("currentVersion") or 0) != 1
                or version_count != 1
                or related_activity
                or write["sha256"] != transfer["write_sha256"]
            ):
                raise TalkRoomError(
                    "talk_transfer_rollback_stale",
                    "The Write document has owner work or related activity; automatic deletion was blocked",
                    status=409,
                )
            con.execute(
                "DELETE FROM write_versions WHERE artifact_id=?", (write["id"],)
            )
            con.execute("DELETE FROM artifact_search WHERE id=?", (write["id"],))
            con.execute("DELETE FROM artifacts WHERE id=?", (write["id"],))
            now = utc_now()
            con.execute(
                """
                UPDATE artifact_relationships
                SET status='rolled_back', updated_at=? WHERE lifecycle_id=?
                """,
                (now, transfer_id),
            )
            con.execute(
                """
                UPDATE talk_transfers
                SET status='rolled_back', rolled_back_at=? WHERE id=?
                """,
                (now, transfer_id),
            )
            receipt_id = self._receipt(
                con,
                transfer["project_id"],
                "talk.write.rollback",
                actor,
                {
                    "artifactId": transfer["artifact_id"],
                    "transferId": transfer_id,
                    "writeArtifactId": write["id"],
                    "createdWriteRemoved": True,
                    "unrelatedWritingRemoved": False,
                    "talkSourcePreserved": True,
                },
            )
            con.commit()
            return {
                "ok": True,
                "transferId": transfer_id,
                "status": "rolled_back",
                "writeArtifactId": write["id"],
                "receiptId": receipt_id,
                "rolledBackAt": now,
            }

    def export_session(
        self,
        artifact_id: str,
        *,
        format_name: Any,
        include_provenance: Any = False,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        export_format = str(format_name or "").strip().lower()
        if export_format not in {"txt", "md", "json"}:
            raise TalkRoomError(
                "talk_export_format_invalid", "Choose TXT, Markdown, or JSON"
            )
        include = include_provenance is True
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            current = int(_json(row["payload"], {}).get("currentVersion") or 0)
            version = self._version_row(con, artifact_id, current)
            entries = self._entries(version)
            if export_format == "txt":
                raw_text = "\n\n".join(
                    f"[{entry['createdAt']}] {entry['speaker'].title()}\n{entry['content']}"
                    for entry in entries
                )
                raw = raw_text.encode("utf-8")
            elif export_format == "md":
                body = "\n\n".join(
                    f"## {entry['speaker'].title()} — {entry['createdAt']}\n\n{entry['content']}"
                    for entry in entries
                )
                raw = f"# {version['title']}\n\n{body}\n".encode("utf-8")
            else:
                value: dict[str, Any] = {
                    "title": version["title"],
                    "exportedAt": utc_now(),
                    "entries": [
                        {
                            "speaker": entry["speaker"],
                            "entryType": entry["entryType"],
                            "content": entry["content"],
                            "createdAt": entry["createdAt"],
                        }
                        for entry in entries
                    ],
                }
                if include:
                    relationships = con.execute(
                        """
                        SELECT source_artifact_id,target_artifact_id,relationship_type,
                               lifecycle_id,status,created_at,updated_at
                        FROM artifact_relationships
                        WHERE source_artifact_id=? ORDER BY created_at
                        """,
                        (artifact_id,),
                    ).fetchall()
                    value["provenance"] = {
                        "artifactId": artifact_id,
                        "projectId": row["project_id"],
                        "version": current,
                        "transcriptSha256": version["transcript_sha256"],
                        "savedAt": version["created_at"],
                        "relationships": [dict(item) for item in relationships],
                    }
                raw = (
                    json.dumps(value, ensure_ascii=False, indent=2) + "\n"
                ).encode("utf-8")
            projects_root = self._projects_root.resolve()
            project_root = (projects_root / row["project_id"]).resolve()
            if project_root == projects_root or projects_root not in project_root.parents:
                raise TalkRoomError(
                    "talk_export_path_invalid", "Talk export path is invalid"
                )
            exports = project_root / "exports"
            exports.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            suffix = f"-talk-v{current}-{stamp}.{export_format}"
            temporary_overhead = 1 + 1 + 32 + len(".tmp")
            title_limit = (
                240
                - len(str(exports))
                - 1
                - temporary_overhead
                - len(suffix)
            )
            if title_limit < 12:
                raise TalkRoomError(
                    "talk_export_path_too_long",
                    "This project folder path is too long for a safe Windows export",
                )
            filename = (
                f"{_safe_filename(version['title'])[:title_limit].rstrip(' .-')}{suffix}"
            )
            destination = exports / filename
            temporary = exports / f".{filename}.{uuid.uuid4().hex}.tmp"
            temporary.write_bytes(raw)
            os.replace(temporary, destination)
            digest = hashlib.sha256(raw).hexdigest()
            export_id = str(uuid.uuid4())
            now = utc_now()
            con.execute(
                "INSERT INTO talk_exports VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    export_id,
                    artifact_id,
                    row["project_id"],
                    current,
                    export_format,
                    str(destination),
                    digest,
                    int(include),
                    now,
                ),
            )
            receipt_id = self._receipt(
                con,
                row["project_id"],
                "talk.export",
                actor,
                {
                    "artifactId": artifact_id,
                    "exportId": export_id,
                    "sourceVersion": current,
                    "format": export_format,
                    "sha256": digest,
                    "includeProvenance": include,
                    "path": str(destination),
                },
            )
            con.commit()
            return {
                "ok": True,
                "exportId": export_id,
                "artifactId": artifact_id,
                "sourceVersion": current,
                "format": export_format,
                "filename": filename,
                "path": str(destination),
                "sha256": digest,
                "includeProvenance": include,
                "receiptId": receipt_id,
                "createdAt": now,
            }

    def inspect_entry(
        self,
        artifact_id: str,
        *,
        entry_id: Any,
        filename: Any,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            current = int(_json(row["payload"], {}).get("currentVersion") or 0)
            version = self._version_row(con, artifact_id, current)
            entry = next(
                (
                    value
                    for value in self._entries(version)
                    if value.get("id") == str(entry_id or "")
                ),
                None,
            )
            if not entry:
                raise TalkRoomError(
                    "talk_inspection_entry_not_current",
                    "Choose a current Talk entry to inspect",
                    status=409,
                )
            result = inspect_code_text(
                str(entry.get("content") or ""),
                str(filename or "pasted-code.txt"),
            )
            inspection_id = str(uuid.uuid4())
            now = utc_now()
            con.execute(
                "INSERT INTO talk_inspections VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    inspection_id,
                    artifact_id,
                    row["project_id"],
                    "talk-entry",
                    entry["id"],
                    None,
                    entry["sha256"],
                    result["filename"],
                    json.dumps(result, ensure_ascii=False),
                    now,
                ),
            )
            receipt_id = self._receipt(
                con,
                row["project_id"],
                "talk.inspect",
                actor,
                {
                    "artifactId": artifact_id,
                    "inspectionId": inspection_id,
                    "sourceEntryId": entry["id"],
                    "sourceSha256": entry["sha256"],
                    "networkUsed": False,
                    "aiModelUsed": False,
                    "shellUsed": False,
                },
            )
            con.commit()
            return {
                "ok": True,
                "inspectionId": inspection_id,
                "sourceEntryId": entry["id"],
                "result": result,
                "artifactInspectionLink": {
                    "routeTemplate": "/api/artifacts/{approved-public-artifact-id}/inspections",
                    "availableForPublicArtifactsOnly": True,
                },
                "receiptId": receipt_id,
                "createdAt": now,
            }

    def resolve_command(self, command: Any) -> dict[str, Any]:
        text = str(command or "").strip()
        normalized = re.sub(r"\s+", " ", text.lower()).strip(" .!?")
        rules = [
            (r"^start (?:a )?new talk$", "new_session"),
            (r"^save this$", "save_entry"),
            (r"^recover what i was saying$", "show_recovery"),
            (r"^(?:make|create) (?:a )?snapshot$", "snapshot"),
            (r"^show me what changed$", "compare"),
            (r"^read this aloud$", "speak"),
            (r"^stop reading$", "stop_speaking"),
            (r"^inspect this approved artifact$", "inspect"),
            (r"^(?:make|create) (?:a )?write document from this$", "talk_to_write"),
            (r"^export this conversation$", "export"),
        ]
        for pattern, action in rules:
            if re.match(pattern, normalized):
                return {
                    "ok": True,
                    "supported": True,
                    "action": action,
                    "command": text,
                    "automaticExecution": False,
                    "requiresOwnerReview": True,
                    "shell": False,
                    "network": False,
                }
        return {
            "ok": True,
            "supported": False,
            "action": None,
            "command": text,
            "message": (
                "That command is not available in this bounded Talk Room. "
                "Nothing was changed."
            ),
            "automaticExecution": False,
            "shell": False,
            "network": False,
        }

    @staticmethod
    def voice_contract() -> dict[str, Any]:
        return {
            "schemaVersion": "talk-voice-adapter-v1",
            "microphoneActivation": "explicit-owner-action-only",
            "rawAudioRetained": False,
            "networkSpeechRecognitionEnabled": False,
            "speechRecognition": {
                "status": "client-capability-check-required",
                "requiredProof": [
                    "SpeechRecognition.processLocally",
                    "SpeechRecognition.available",
                    "available local language pack",
                ],
                "fallback": "unavailable-text-remains-usable",
                "draftBeforePermanent": True,
            },
            "speechSynthesis": {
                "status": "client-capability-check-required",
                "requiredProof": "SpeechSynthesisVoice.localService is true",
                "visiblePlayStopFailure": True,
                "networkVoicesAllowed": False,
            },
            "aiModel": False,
            "shell": False,
            "hiddenNetwork": False,
        }
