from __future__ import annotations

import difflib
import hashlib
import json
import os
import re
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


MAX_TITLE_CHARS = 300
MAX_CONTENT_BYTES = 5 * 1024 * 1024
WRITE_SCHEMA_VERSION = 1
SUPPORTED_ACTIONS = {
    "inspect",
    "summarize",
    "clean_formatting",
    "repeated_passages",
    "structure",
}


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS write_versions(
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  version_number INTEGER NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  label TEXT NOT NULL DEFAULT '',
  cause TEXT NOT NULL,
  actor TEXT NOT NULL,
  parent_version_id TEXT,
  created_at TEXT NOT NULL,
  UNIQUE(artifact_id, version_number)
);
CREATE INDEX IF NOT EXISTS write_versions_artifact_idx
  ON write_versions(artifact_id, version_number DESC);

CREATE TABLE IF NOT EXISTS write_recovery_drafts(
  artifact_id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL,
  base_version_number INTEGER NOT NULL,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  content_sha256 TEXT NOT NULL,
  state TEXT NOT NULL DEFAULT 'pending',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS write_recovery_project_idx
  ON write_recovery_drafts(project_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS write_proposals(
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  action TEXT NOT NULL,
  command TEXT NOT NULL DEFAULT '',
  plan_json TEXT NOT NULL,
  source_version_number INTEGER NOT NULL,
  source_sha256 TEXT NOT NULL,
  proposed_title TEXT NOT NULL,
  proposed_content TEXT NOT NULL,
  proposed_sha256 TEXT NOT NULL,
  comparison_json TEXT NOT NULL,
  findings_json TEXT NOT NULL,
  modifies_content INTEGER NOT NULL,
  status TEXT NOT NULL,
  decision_note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL,
  decided_at TEXT,
  applied_version_id TEXT,
  recovery_version_id TEXT,
  rollback_version_id TEXT
);
CREATE INDEX IF NOT EXISTS write_proposals_artifact_idx
  ON write_proposals(artifact_id, created_at DESC);

CREATE TABLE IF NOT EXISTS write_restore_operations(
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
CREATE INDEX IF NOT EXISTS write_restore_artifact_idx
  ON write_restore_operations(artifact_id, created_at DESC);

CREATE TABLE IF NOT EXISTS write_exports(
  id TEXT PRIMARY KEY,
  artifact_id TEXT NOT NULL,
  project_id TEXT NOT NULL,
  format TEXT NOT NULL,
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  include_provenance INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS write_exports_artifact_idx
  ON write_exports(artifact_id, created_at DESC);
"""


class WriteRoomError(Exception):
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


def content_sha256(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _title(value: Any) -> str:
    title = str(value or "Untitled").strip() or "Untitled"
    if len(title) > MAX_TITLE_CHARS:
        raise WriteRoomError("title_too_long", f"Title must be {MAX_TITLE_CHARS} characters or fewer")
    return title


def _content(value: Any) -> str:
    content = str(value or "")
    if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
        raise WriteRoomError("content_too_large", "Writing exceeds the 5 MiB local document limit")
    return content


def _json(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _safe_filename(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "-", value).strip(" .-")
    return (cleaned[:90] or "untitled").rstrip(" .")


def _comparison(left: str, right: str) -> dict[str, Any]:
    left_lines = left.splitlines()
    right_lines = right.splitlines()
    matcher = difflib.SequenceMatcher(None, left_lines, right_lines, autojunk=False)
    added = removed = changed = 0
    operations: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        if tag == "insert":
            added += j2 - j1
        elif tag == "delete":
            removed += i2 - i1
        else:
            changed += max(i2 - i1, j2 - j1)
        operations.append(
            {
                "kind": tag,
                "leftStart": i1 + 1,
                "leftEnd": i2,
                "rightStart": j1 + 1,
                "rightEnd": j2,
                "leftLines": left_lines[i1:i2],
                "rightLines": right_lines[j1:j2],
            }
        )
    unified = list(
        difflib.unified_diff(
            left_lines,
            right_lines,
            fromfile="before",
            tofile="after",
            lineterm="",
        )
    )
    return {
        "changed": left != right,
        "addedLines": added,
        "removedLines": removed,
        "changedLines": changed,
        "operations": operations,
        "unifiedDiff": unified,
    }


class WriteRoom:
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
            (receipt_id, project_id, action, actor, json.dumps(details, ensure_ascii=False), utc_now()),
        )
        return receipt_id

    def _project_exists(self, con: sqlite3.Connection, project_id: str) -> None:
        if not con.execute("SELECT 1 FROM projects WHERE id=?", (project_id,)).fetchone():
            raise WriteRoomError("project_not_found", "Project not found", status=404)

    def _artifact_row(self, con: sqlite3.Connection, artifact_id: str) -> sqlite3.Row:
        row = con.execute(
            "SELECT * FROM artifacts WHERE id=? AND kind='document'",
            (artifact_id,),
        ).fetchone()
        if not row:
            raise WriteRoomError("write_project_not_found", "Writing project not found", status=404)
        return row

    def _version_row(
        self,
        con: sqlite3.Connection,
        artifact_id: str,
        version_number: int,
    ) -> sqlite3.Row:
        row = con.execute(
            "SELECT * FROM write_versions WHERE artifact_id=? AND version_number=?",
            (artifact_id, version_number),
        ).fetchone()
        if not row:
            raise WriteRoomError("version_not_found", "Version not found", status=404)
        return row

    def _index(
        self,
        con: sqlite3.Connection,
        artifact_id: str,
        project_id: str,
        title: str,
        content: str,
    ) -> None:
        con.execute("DELETE FROM artifact_search WHERE id=?", (artifact_id,))
        con.execute(
            "INSERT INTO artifact_search(id,project_id,title,kind,content) VALUES(?,?,?,?,?)",
            (artifact_id, project_id, title, "document", f"{title} document {content}"),
        )

    def _payload(
        self,
        *,
        content: str,
        current_version: int,
        last_saved_at: str,
        version_count: int,
        origin: str,
    ) -> dict[str, Any]:
        return {
            "schemaVersion": "write-project-v1",
            "body": content,
            "currentVersion": current_version,
            "lastSavedAt": last_saved_at,
            "versionCount": version_count,
            "origin": origin,
        }

    def _insert_version(
        self,
        con: sqlite3.Connection,
        *,
        artifact_id: str,
        project_id: str,
        version_number: int,
        title: str,
        content: str,
        label: str,
        cause: str,
        actor: str,
        parent_version_id: str | None,
    ) -> sqlite3.Row:
        version_id = str(uuid.uuid4())
        con.execute(
            """INSERT INTO write_versions(
                 id,artifact_id,project_id,version_number,title,content,content_sha256,
                 label,cause,actor,parent_version_id,created_at
               ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                version_id,
                artifact_id,
                project_id,
                version_number,
                title,
                content,
                content_sha256(content),
                label,
                cause,
                actor,
                parent_version_id,
                utc_now(),
            ),
        )
        return con.execute("SELECT * FROM write_versions WHERE id=?", (version_id,)).fetchone()

    def _update_current(
        self,
        con: sqlite3.Connection,
        row: sqlite3.Row,
        version: sqlite3.Row,
        *,
        origin: str,
    ) -> None:
        now = version["created_at"]
        count = con.execute(
            "SELECT COUNT(*) FROM write_versions WHERE artifact_id=?",
            (row["id"],),
        ).fetchone()[0]
        payload = self._payload(
            content=version["content"],
            current_version=version["version_number"],
            last_saved_at=now,
            version_count=count,
            origin=origin,
        )
        con.execute(
            """UPDATE artifacts
               SET title=?,payload=?,sha256=?,updated_at=?,authority_state='DRAFT'
               WHERE id=?""",
            (
                version["title"],
                json.dumps(payload, ensure_ascii=False),
                version["content_sha256"],
                now,
                row["id"],
            ),
        )
        con.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, row["project_id"]))
        self._index(con, row["id"], row["project_id"], version["title"], version["content"])

    def _serialize_version(self, row: sqlite3.Row, *, include_content: bool = True) -> dict[str, Any]:
        result = {
            "id": row["id"],
            "number": row["version_number"],
            "title": row["title"],
            "sha256": row["content_sha256"],
            "label": row["label"],
            "cause": row["cause"],
            "actor": row["actor"],
            "parentVersionId": row["parent_version_id"],
            "createdAt": row["created_at"],
        }
        if include_content:
            result["content"] = row["content"]
        return result

    def _serialize_proposal(self, row: sqlite3.Row, *, include_content: bool = True) -> dict[str, Any]:
        result = {
            "id": row["id"],
            "artifactId": row["artifact_id"],
            "projectId": row["project_id"],
            "action": row["action"],
            "command": row["command"],
            "plan": _json(row["plan_json"], {}),
            "sourceVersion": row["source_version_number"],
            "sourceSha256": row["source_sha256"],
            "proposedTitle": row["proposed_title"],
            "proposedSha256": row["proposed_sha256"],
            "comparison": _json(row["comparison_json"], {}),
            "findings": _json(row["findings_json"], []),
            "modifiesContent": bool(row["modifies_content"]),
            "status": row["status"],
            "decisionNote": row["decision_note"],
            "createdAt": row["created_at"],
            "decidedAt": row["decided_at"],
            "appliedVersionId": row["applied_version_id"],
            "recoveryVersionId": row["recovery_version_id"],
            "rollbackVersionId": row["rollback_version_id"],
        }
        if include_content:
            result["proposedContent"] = row["proposed_content"]
        return result

    def _serialize_document(
        self,
        con: sqlite3.Connection,
        row: sqlite3.Row,
        *,
        full: bool,
    ) -> dict[str, Any]:
        payload = _json(row["payload"], {})
        recovery = con.execute(
            "SELECT * FROM write_recovery_drafts WHERE artifact_id=?",
            (row["id"],),
        ).fetchone()
        result = {
            "id": row["id"],
            "projectId": row["project_id"],
            "title": row["title"],
            "content": payload.get("body", "") if full else None,
            "sha256": row["sha256"],
            "currentVersion": int(payload.get("currentVersion") or 0),
            "versionCount": int(payload.get("versionCount") or 0),
            "lastSavedAt": payload.get("lastSavedAt") or row["updated_at"],
            "createdAt": row["created_at"],
            "updatedAt": row["updated_at"],
            "hasRecovery": bool(recovery),
            "recoveryUpdatedAt": recovery["updated_at"] if recovery else None,
        }
        if not full:
            result.pop("content")
            return result
        versions = con.execute(
            "SELECT * FROM write_versions WHERE artifact_id=? ORDER BY version_number DESC",
            (row["id"],),
        ).fetchall()
        result["versions"] = [self._serialize_version(version) for version in versions]
        result["recovery"] = (
            {
                "baseVersion": recovery["base_version_number"],
                "title": recovery["title"],
                "content": recovery["content"],
                "sha256": recovery["content_sha256"],
                "state": recovery["state"],
                "createdAt": recovery["created_at"],
                "updatedAt": recovery["updated_at"],
            }
            if recovery
            else None
        )
        proposals = con.execute(
            "SELECT * FROM write_proposals WHERE artifact_id=? ORDER BY created_at DESC LIMIT 20",
            (row["id"],),
        ).fetchall()
        result["proposals"] = [self._serialize_proposal(proposal) for proposal in proposals]
        return result

    def list_documents(self, project_id: str, search: str = "") -> list[dict[str, Any]]:
        with self._connect() as con:
            values: list[Any] = [project_id]
            sql = "SELECT * FROM artifacts WHERE kind='document' AND project_id=?"
            if search.strip():
                sql += " AND (title LIKE ? OR payload LIKE ?)"
                pattern = f"%{search.strip()}%"
                values.extend([pattern, pattern])
            sql += " ORDER BY updated_at DESC"
            rows = con.execute(sql, values).fetchall()
            return [self._serialize_document(con, row, full=False) for row in rows]

    def get_document(self, artifact_id: str) -> dict[str, Any]:
        with self._connect() as con:
            return self._serialize_document(con, self._artifact_row(con, artifact_id), full=True)

    def create_document(
        self,
        project_id: str,
        title: Any,
        content: Any = "",
        *,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        title_value = _title(title)
        content_value = _content(content)
        with self._connect() as con:
            self._project_exists(con, project_id)
            artifact_id = str(uuid.uuid4())
            now = utc_now()
            payload = self._payload(
                content=content_value,
                current_version=1,
                last_saved_at=now,
                version_count=1,
                origin="write-room",
            )
            con.execute(
                """INSERT INTO artifacts(
                     id,project_id,kind,title,path,payload,authority_state,sha256,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    artifact_id,
                    project_id,
                    "document",
                    title_value,
                    "",
                    json.dumps(payload, ensure_ascii=False),
                    "DRAFT",
                    content_sha256(content_value),
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
                content=content_value,
                label="Created",
                cause="created",
                actor=actor,
                parent_version_id=None,
            )
            self._index(con, artifact_id, project_id, title_value, content_value)
            self._receipt(
                con,
                project_id,
                "write.create",
                actor,
                {
                    "artifactId": artifact_id,
                    "version": 1,
                    "contentSha256": version["content_sha256"],
                },
            )
            con.execute("UPDATE projects SET updated_at=? WHERE id=?", (now, project_id))
            con.commit()
        return self.get_document(artifact_id)

    def save_document(
        self,
        artifact_id: str,
        *,
        title: Any,
        content: Any,
        base_version: Any,
        cause: str,
        label: Any = "",
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        title_value = _title(title)
        content_value = _content(content)
        if cause not in {"manual", "autosave", "recovery"}:
            raise WriteRoomError("save_cause_invalid", "Save cause is not supported")
        try:
            base = int(base_version)
        except (TypeError, ValueError) as exc:
            raise WriteRoomError("base_version_required", "Current version is required") from exc
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            payload = _json(row["payload"], {})
            current = int(payload.get("currentVersion") or 0)
            if base != current:
                raise WriteRoomError(
                    "write_version_conflict",
                    "This writing project changed after it was opened",
                    status=409,
                    details={"expectedVersion": base, "currentVersion": current},
                )
            current_version = self._version_row(con, artifact_id, current)
            if title_value == current_version["title"] and content_value == current_version["content"]:
                con.execute("DELETE FROM write_recovery_drafts WHERE artifact_id=?", (artifact_id,))
                con.commit()
                result = self._serialize_document(con, row, full=True)
                result["unchanged"] = True
                return result
            version = self._insert_version(
                con,
                artifact_id=artifact_id,
                project_id=row["project_id"],
                version_number=current + 1,
                title=title_value,
                content=content_value,
                label=str(label or ("Autosave" if cause == "autosave" else "Saved"))[:200],
                cause=cause,
                actor=actor,
                parent_version_id=current_version["id"],
            )
            self._update_current(con, row, version, origin="write-room")
            con.execute("DELETE FROM write_recovery_drafts WHERE artifact_id=?", (artifact_id,))
            receipt_id = self._receipt(
                con,
                row["project_id"],
                "write.autosave" if cause == "autosave" else "write.save",
                actor,
                {
                    "artifactId": artifact_id,
                    "version": version["version_number"],
                    "contentSha256": version["content_sha256"],
                    "cause": cause,
                },
            )
            con.commit()
        result = self.get_document(artifact_id)
        result["receiptId"] = receipt_id
        return result

    def snapshot(
        self,
        artifact_id: str,
        *,
        title: Any,
        content: Any,
        base_version: Any,
        label: Any,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        title_value = _title(title)
        content_value = _content(content)
        label_value = str(label or "").strip()
        if not label_value:
            raise WriteRoomError("snapshot_label_required", "Give this snapshot a name")
        if len(label_value) > 200:
            raise WriteRoomError("snapshot_label_too_long", "Snapshot name must be 200 characters or fewer")
        try:
            base = int(base_version)
        except (TypeError, ValueError) as exc:
            raise WriteRoomError("base_version_required", "Current version is required") from exc
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            payload = _json(row["payload"], {})
            current = int(payload.get("currentVersion") or 0)
            if base != current:
                raise WriteRoomError(
                    "write_version_conflict",
                    "This writing project changed after it was opened",
                    status=409,
                    details={"expectedVersion": base, "currentVersion": current},
                )
            parent = self._version_row(con, artifact_id, current)
            version = self._insert_version(
                con,
                artifact_id=artifact_id,
                project_id=row["project_id"],
                version_number=current + 1,
                title=title_value,
                content=content_value,
                label=label_value,
                cause="snapshot",
                actor=actor,
                parent_version_id=parent["id"],
            )
            self._update_current(con, row, version, origin="write-room")
            con.execute("DELETE FROM write_recovery_drafts WHERE artifact_id=?", (artifact_id,))
            receipt_id = self._receipt(
                con,
                row["project_id"],
                "write.snapshot",
                actor,
                {
                    "artifactId": artifact_id,
                    "version": version["version_number"],
                    "label": label_value,
                    "contentSha256": version["content_sha256"],
                },
            )
            con.commit()
        result = self.get_document(artifact_id)
        result["receiptId"] = receipt_id
        return result

    def save_recovery(
        self,
        artifact_id: str,
        *,
        title: Any,
        content: Any,
        base_version: Any,
    ) -> dict[str, Any]:
        title_value = _title(title)
        content_value = _content(content)
        try:
            base = int(base_version)
        except (TypeError, ValueError) as exc:
            raise WriteRoomError("base_version_required", "Current version is required") from exc
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            now = utc_now()
            existing = con.execute(
                "SELECT created_at FROM write_recovery_drafts WHERE artifact_id=?",
                (artifact_id,),
            ).fetchone()
            con.execute(
                """INSERT INTO write_recovery_drafts(
                     artifact_id,project_id,base_version_number,title,content,content_sha256,
                     state,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?)
                   ON CONFLICT(artifact_id) DO UPDATE SET
                     base_version_number=excluded.base_version_number,
                     title=excluded.title,content=excluded.content,
                     content_sha256=excluded.content_sha256,state='pending',
                     updated_at=excluded.updated_at""",
                (
                    artifact_id,
                    row["project_id"],
                    base,
                    title_value,
                    content_value,
                    content_sha256(content_value),
                    "pending",
                    existing["created_at"] if existing else now,
                    now,
                ),
            )
            con.commit()
            return {
                "ok": True,
                "artifactId": artifact_id,
                "baseVersion": base,
                "sha256": content_sha256(content_value),
                "updatedAt": now,
            }

    def discard_recovery(self, artifact_id: str, *, actor: str = "local-owner") -> dict[str, Any]:
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            found = con.execute(
                "SELECT 1 FROM write_recovery_drafts WHERE artifact_id=?",
                (artifact_id,),
            ).fetchone()
            con.execute("DELETE FROM write_recovery_drafts WHERE artifact_id=?", (artifact_id,))
            if found:
                self._receipt(
                    con,
                    row["project_id"],
                    "write.recovery.discard",
                    actor,
                    {"artifactId": artifact_id},
                )
            con.commit()
            return {"ok": True, "discarded": bool(found)}

    def compare_versions(
        self,
        artifact_id: str,
        left_version: Any,
        right_version: Any,
    ) -> dict[str, Any]:
        try:
            left_number = int(left_version)
            right_number = int(right_version)
        except (TypeError, ValueError) as exc:
            raise WriteRoomError("version_required", "Choose two versions to compare") from exc
        with self._connect() as con:
            self._artifact_row(con, artifact_id)
            left = self._version_row(con, artifact_id, left_number)
            right = self._version_row(con, artifact_id, right_number)
            return {
                "artifactId": artifact_id,
                "left": self._serialize_version(left),
                "right": self._serialize_version(right),
                "comparison": _comparison(left["content"], right["content"]),
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
            raise WriteRoomError("restore_confirmation_required", "Restore must be explicitly confirmed")
        try:
            target_number = int(target_version)
            base = int(base_version)
        except (TypeError, ValueError) as exc:
            raise WriteRoomError("version_required", "Target and current versions are required") from exc
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            payload = _json(row["payload"], {})
            current = int(payload.get("currentVersion") or 0)
            if current != base:
                raise WriteRoomError(
                    "write_version_conflict",
                    "This writing project changed before restore",
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
                content=current_row["content"],
                label=f"Before restore to v{target_number}",
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
                content=target["content"],
                label=f"Restored from v{target_number}",
                cause="restore",
                actor=actor,
                parent_version_id=recovery["id"],
            )
            self._update_current(con, row, restored, origin="write-restore")
            operation_id = str(uuid.uuid4())
            con.execute(
                """INSERT INTO write_restore_operations(
                     id,artifact_id,project_id,target_version_id,recovery_version_id,
                     restored_version_id,rollback_version_id,status,created_at,rolled_back_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,NULL)""",
                (
                    operation_id,
                    artifact_id,
                    row["project_id"],
                    target["id"],
                    recovery["id"],
                    restored["id"],
                    None,
                    "applied",
                    utc_now(),
                ),
            )
            self._receipt(
                con,
                row["project_id"],
                "write.restore",
                actor,
                {
                    "artifactId": artifact_id,
                    "operationId": operation_id,
                    "targetVersion": target_number,
                    "recoveryVersion": recovery["version_number"],
                    "restoredVersion": restored["version_number"],
                },
            )
            con.commit()
        result = self.get_document(artifact_id)
        result["restoreOperationId"] = operation_id
        return result

    def rollback_restore(
        self,
        operation_id: str,
        *,
        confirmed: Any,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        if confirmed is not True:
            raise WriteRoomError("rollback_confirmation_required", "Rollback must be explicitly confirmed")
        with self._connect() as con:
            operation = con.execute(
                "SELECT * FROM write_restore_operations WHERE id=?",
                (operation_id,),
            ).fetchone()
            if not operation:
                raise WriteRoomError("restore_operation_not_found", "Restore operation not found", status=404)
            if operation["status"] != "applied":
                raise WriteRoomError("restore_not_active", "This restore has already been rolled back", status=409)
            row = self._artifact_row(con, operation["artifact_id"])
            payload = _json(row["payload"], {})
            current = int(payload.get("currentVersion") or 0)
            restored = con.execute(
                "SELECT * FROM write_versions WHERE id=?",
                (operation["restored_version_id"],),
            ).fetchone()
            if not restored or current != restored["version_number"]:
                raise WriteRoomError(
                    "restore_rollback_stale",
                    "Newer writing changes prevent automatic restore rollback",
                    status=409,
                )
            recovery = con.execute(
                "SELECT * FROM write_versions WHERE id=?",
                (operation["recovery_version_id"],),
            ).fetchone()
            rollback = self._insert_version(
                con,
                artifact_id=row["id"],
                project_id=row["project_id"],
                version_number=current + 1,
                title=recovery["title"],
                content=recovery["content"],
                label="Rolled back restore",
                cause="restore-rollback",
                actor=actor,
                parent_version_id=restored["id"],
            )
            self._update_current(con, row, rollback, origin="write-restore-rollback")
            now = utc_now()
            con.execute(
                """UPDATE write_restore_operations
                   SET status='rolled_back',rollback_version_id=?,rolled_back_at=?
                   WHERE id=?""",
                (rollback["id"], now, operation_id),
            )
            self._receipt(
                con,
                row["project_id"],
                "write.restore.rollback",
                actor,
                {
                    "artifactId": row["id"],
                    "operationId": operation_id,
                    "rollbackVersion": rollback["version_number"],
                },
            )
            con.commit()
        result = self.get_document(row["id"])
        result["restoreOperationId"] = operation_id
        return result

    def _resolve_action(self, action: Any, command: Any) -> tuple[str, str]:
        requested = str(action or "").strip().lower().replace("-", "_").replace(" ", "_")
        command_value = str(command or "").strip()
        if requested:
            if requested not in SUPPORTED_ACTIONS:
                raise WriteRoomError("write_action_unsupported", "That writing action is not supported")
            return requested, command_value
        normalized = re.sub(r"\s+", " ", command_value.lower())
        mappings = (
            ("repeated_passages", ("repeat", "duplicate passage", "duplication")),
            ("clean_formatting", ("clean formatting", "clean this up", "formatting", "tidy", "whitespace")),
            ("structure", ("structure", "outline", "sections")),
            ("summarize", ("summarize", "summary")),
            ("inspect", ("inspect", "analyze", "check this", "review this")),
        )
        for candidate, phrases in mappings:
            if any(phrase in normalized for phrase in phrases):
                return candidate, command_value
        raise WriteRoomError(
            "write_command_unsupported",
            "Try: inspect, summarize, clean formatting, find repeated passages, or show structure",
        )

    def _plan_action(
        self,
        action: str,
        title: str,
        content: str,
    ) -> tuple[str, list[dict[str, Any]], bool]:
        lines = content.splitlines()
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", content) if part.strip()]
        words = re.findall(r"\b[\w'-]+\b", content)
        if action == "clean_formatting":
            cleaned_lines = [line.rstrip() for line in content.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
            cleaned = re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned_lines)).strip("\n")
            if content.endswith(("\n", "\r")) and cleaned:
                cleaned += "\n"
            findings = [
                {
                    "kind": "formatting",
                    "message": "Trailing spaces and runs of extra blank lines are normalized.",
                }
            ]
            return cleaned, findings, cleaned != content
        if action == "repeated_passages":
            buckets: dict[str, list[int]] = {}
            for index, paragraph in enumerate(paragraphs, start=1):
                key = re.sub(r"\s+", " ", paragraph).casefold()
                if len(key) >= 20:
                    buckets.setdefault(key, []).append(index)
            repeated = [positions for positions in buckets.values() if len(positions) > 1]
            findings = (
                [
                    {
                        "kind": "repeated-passage",
                        "message": f"Matching paragraph appears at positions {', '.join(map(str, positions))}.",
                        "paragraphs": positions,
                    }
                    for positions in repeated
                ]
                or [{"kind": "repeated-passage", "message": "No repeated passages were found."}]
            )
            return content, findings, False
        if action == "structure":
            headings = [
                {"line": index, "text": line.strip()}
                for index, line in enumerate(lines, start=1)
                if re.match(r"^\s{0,3}(#{1,6}\s+|[A-Z][A-Z0-9 '\-]{3,}:?\s*$)", line)
            ]
            findings = [
                {
                    "kind": "structure",
                    "message": f"{len(paragraphs)} paragraph(s), {len(headings)} visible heading(s).",
                    "headings": headings,
                }
            ]
            return content, findings, False
        if action == "summarize":
            sample = " ".join(paragraphs[:2])
            if len(sample) > 500:
                sample = sample[:497].rstrip() + "..."
            findings = [
                {
                    "kind": "summary",
                    "message": sample or "This writing project is empty.",
                    "source": "deterministic-first-paragraphs",
                }
            ]
            return content, findings, False
        findings = [
            {
                "kind": "inspection",
                "message": (
                    f"{len(words)} word(s), {len(lines)} line(s), {len(paragraphs)} paragraph(s); "
                    f"title: {title}."
                ),
            }
        ]
        return content, findings, False

    def create_proposal(
        self,
        artifact_id: str,
        *,
        action: Any = "",
        command: Any = "",
        base_version: Any,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        resolved_action, command_value = self._resolve_action(action, command)
        try:
            base = int(base_version)
        except (TypeError, ValueError) as exc:
            raise WriteRoomError("base_version_required", "Current version is required") from exc
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            payload = _json(row["payload"], {})
            current = int(payload.get("currentVersion") or 0)
            if current != base:
                raise WriteRoomError(
                    "write_version_conflict",
                    "This writing project changed before the writing action ran",
                    status=409,
                    details={"expectedVersion": base, "currentVersion": current},
                )
            source = self._version_row(con, artifact_id, current)
            proposed, findings, modifies = self._plan_action(
                resolved_action,
                source["title"],
                source["content"],
            )
            comparison = _comparison(source["content"], proposed)
            proposal_id = str(uuid.uuid4())
            plan = {
                "worker": "bounded-deterministic-write-worker",
                "action": resolved_action,
                "network": False,
                "aiModel": False,
                "shell": False,
                "sourceMutation": False,
                "requiresExplicitDecision": True,
            }
            now = utc_now()
            con.execute(
                """INSERT INTO write_proposals(
                     id,artifact_id,project_id,action,command,plan_json,source_version_number,
                     source_sha256,proposed_title,proposed_content,proposed_sha256,
                     comparison_json,findings_json,modifies_content,status,decision_note,
                     created_at,decided_at,applied_version_id,recovery_version_id,rollback_version_id
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NULL,NULL,NULL,NULL)""",
                (
                    proposal_id,
                    artifact_id,
                    row["project_id"],
                    resolved_action,
                    command_value,
                    json.dumps(plan, ensure_ascii=False),
                    current,
                    source["content_sha256"],
                    source["title"],
                    proposed,
                    content_sha256(proposed),
                    json.dumps(comparison, ensure_ascii=False),
                    json.dumps(findings, ensure_ascii=False),
                    int(modifies),
                    "awaiting_approval",
                    "",
                    now,
                ),
            )
            self._receipt(
                con,
                row["project_id"],
                "write.proposal.create",
                actor,
                {
                    "artifactId": artifact_id,
                    "proposalId": proposal_id,
                    "action": resolved_action,
                    "sourceVersion": current,
                    "sourceSha256": source["content_sha256"],
                    "modifiesContent": modifies,
                },
            )
            con.commit()
            proposal = con.execute("SELECT * FROM write_proposals WHERE id=?", (proposal_id,)).fetchone()
            return self._serialize_proposal(proposal)

    def decide_proposal(
        self,
        proposal_id: str,
        *,
        decision: Any,
        note: Any = "",
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        decision_value = str(decision or "").strip().lower()
        if decision_value not in {"approve", "reject"}:
            raise WriteRoomError("proposal_decision_invalid", "Choose approve or reject")
        note_value = str(note or "").strip()[:500]
        with self._connect() as con:
            proposal = con.execute(
                "SELECT * FROM write_proposals WHERE id=?",
                (proposal_id,),
            ).fetchone()
            if not proposal:
                raise WriteRoomError("proposal_not_found", "Proposal not found", status=404)
            if proposal["status"] != "awaiting_approval":
                raise WriteRoomError("proposal_already_decided", "This proposal was already decided", status=409)
            row = self._artifact_row(con, proposal["artifact_id"])
            now = utc_now()
            if decision_value == "reject":
                con.execute(
                    """UPDATE write_proposals
                       SET status='rejected',decision_note=?,decided_at=?
                       WHERE id=?""",
                    (note_value, now, proposal_id),
                )
                self._receipt(
                    con,
                    row["project_id"],
                    "write.proposal.reject",
                    actor,
                    {"artifactId": row["id"], "proposalId": proposal_id, "note": note_value},
                )
                con.commit()
                decided = con.execute("SELECT * FROM write_proposals WHERE id=?", (proposal_id,)).fetchone()
                return self._serialize_proposal(decided)
            payload = _json(row["payload"], {})
            current = int(payload.get("currentVersion") or 0)
            current_version = self._version_row(con, row["id"], current)
            if (
                current != proposal["source_version_number"]
                or current_version["content_sha256"] != proposal["source_sha256"]
            ):
                raise WriteRoomError(
                    "proposal_source_changed",
                    "The writing changed after this proposal was created",
                    status=409,
                )
            recovery_id = applied_id = None
            if proposal["modifies_content"]:
                recovery = self._insert_version(
                    con,
                    artifact_id=row["id"],
                    project_id=row["project_id"],
                    version_number=current + 1,
                    title=current_version["title"],
                    content=current_version["content"],
                    label=f"Before {proposal['action']}",
                    cause="worker-recovery",
                    actor=actor,
                    parent_version_id=current_version["id"],
                )
                applied = self._insert_version(
                    con,
                    artifact_id=row["id"],
                    project_id=row["project_id"],
                    version_number=current + 2,
                    title=proposal["proposed_title"],
                    content=proposal["proposed_content"],
                    label=f"Applied {proposal['action']}",
                    cause="worker-apply",
                    actor=actor,
                    parent_version_id=recovery["id"],
                )
                self._update_current(con, row, applied, origin="bounded-write-worker")
                recovery_id = recovery["id"]
                applied_id = applied["id"]
            con.execute(
                """UPDATE write_proposals
                   SET status='approved',decision_note=?,decided_at=?,
                       applied_version_id=?,recovery_version_id=?
                   WHERE id=?""",
                (note_value, now, applied_id, recovery_id, proposal_id),
            )
            self._receipt(
                con,
                row["project_id"],
                "write.proposal.approve",
                actor,
                {
                    "artifactId": row["id"],
                    "proposalId": proposal_id,
                    "action": proposal["action"],
                    "contentApplied": bool(proposal["modifies_content"]),
                    "note": note_value,
                },
            )
            con.commit()
            decided = con.execute("SELECT * FROM write_proposals WHERE id=?", (proposal_id,)).fetchone()
            result = self._serialize_proposal(decided)
            if proposal["modifies_content"]:
                result["document"] = self._serialize_document(con, self._artifact_row(con, row["id"]), full=True)
            return result

    def rollback_proposal(
        self,
        proposal_id: str,
        *,
        confirmed: Any,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        if confirmed is not True:
            raise WriteRoomError("rollback_confirmation_required", "Rollback must be explicitly confirmed")
        with self._connect() as con:
            proposal = con.execute(
                "SELECT * FROM write_proposals WHERE id=?",
                (proposal_id,),
            ).fetchone()
            if not proposal:
                raise WriteRoomError("proposal_not_found", "Proposal not found", status=404)
            if (
                proposal["status"] != "approved"
                or not proposal["applied_version_id"]
                or not proposal["recovery_version_id"]
            ):
                raise WriteRoomError("proposal_not_applied", "This proposal has no active content change", status=409)
            row = self._artifact_row(con, proposal["artifact_id"])
            payload = _json(row["payload"], {})
            current = int(payload.get("currentVersion") or 0)
            applied = con.execute(
                "SELECT * FROM write_versions WHERE id=?",
                (proposal["applied_version_id"],),
            ).fetchone()
            if not applied or current != applied["version_number"]:
                raise WriteRoomError(
                    "proposal_rollback_stale",
                    "Newer writing changes prevent automatic proposal rollback",
                    status=409,
                )
            recovery = con.execute(
                "SELECT * FROM write_versions WHERE id=?",
                (proposal["recovery_version_id"],),
            ).fetchone()
            rollback = self._insert_version(
                con,
                artifact_id=row["id"],
                project_id=row["project_id"],
                version_number=current + 1,
                title=recovery["title"],
                content=recovery["content"],
                label=f"Rolled back {proposal['action']}",
                cause="worker-rollback",
                actor=actor,
                parent_version_id=applied["id"],
            )
            self._update_current(con, row, rollback, origin="bounded-write-worker-rollback")
            now = utc_now()
            con.execute(
                """UPDATE write_proposals
                   SET status='rolled_back',rollback_version_id=?,decided_at=?
                   WHERE id=?""",
                (rollback["id"], now, proposal_id),
            )
            self._receipt(
                con,
                row["project_id"],
                "write.proposal.rollback",
                actor,
                {
                    "artifactId": row["id"],
                    "proposalId": proposal_id,
                    "rollbackVersion": rollback["version_number"],
                },
            )
            con.commit()
            result = self._serialize_proposal(
                con.execute("SELECT * FROM write_proposals WHERE id=?", (proposal_id,)).fetchone()
            )
            result["document"] = self._serialize_document(con, self._artifact_row(con, row["id"]), full=True)
            return result

    def export_document(
        self,
        artifact_id: str,
        *,
        format_name: Any,
        include_provenance: Any = False,
        actor: str = "local-owner",
    ) -> dict[str, Any]:
        export_format = str(format_name or "").strip().lower()
        if export_format not in {"txt", "md", "json"}:
            raise WriteRoomError("export_format_invalid", "Choose TXT, Markdown, or JSON")
        include = include_provenance is True
        with self._connect() as con:
            row = self._artifact_row(con, artifact_id)
            payload = _json(row["payload"], {})
            current = int(payload.get("currentVersion") or 0)
            version = self._version_row(con, artifact_id, current)
            if export_format == "txt":
                raw = version["content"].encode("utf-8")
            elif export_format == "md":
                raw = f"# {version['title']}\n\n{version['content']}".encode("utf-8")
            else:
                value: dict[str, Any] = {
                    "title": version["title"],
                    "content": version["content"],
                    "exportedAt": utc_now(),
                }
                if include:
                    value["provenance"] = {
                        "artifactId": artifact_id,
                        "projectId": row["project_id"],
                        "version": current,
                        "contentSha256": version["content_sha256"],
                        "savedAt": version["created_at"],
                    }
                raw = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            projects_root = self._projects_root.resolve()
            project_root = (projects_root / row["project_id"]).resolve()
            if project_root == projects_root or projects_root not in project_root.parents:
                raise WriteRoomError("export_path_invalid", "Writing project export path is invalid")
            exports = project_root / "exports"
            exports.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            suffix = f"-v{current}-{stamp}.{export_format}"
            # Keep the atomic temporary path below a conservative Windows
            # MAX_PATH boundary.  The deployed Workshop can live below a long
            # owner-selected directory, and the temporary name also carries a
            # UUID.  Fail clearly if the containing project path alone leaves
            # no useful title space.
            temporary_overhead = 1 + 1 + 32 + len(".tmp")
            title_limit = 240 - len(str(exports)) - 1 - temporary_overhead - len(suffix)
            if title_limit < 12:
                raise WriteRoomError(
                    "export_path_too_long",
                    "This project folder path is too long for a safe Windows export",
                )
            filename = f"{_safe_filename(version['title'])[:title_limit].rstrip(' .-')}{suffix}"
            destination = exports / filename
            temporary = exports / f".{filename}.{uuid.uuid4().hex}.tmp"
            temporary.write_bytes(raw)
            os.replace(temporary, destination)
            digest = hashlib.sha256(raw).hexdigest()
            export_id = str(uuid.uuid4())
            now = utc_now()
            con.execute(
                "INSERT INTO write_exports VALUES(?,?,?,?,?,?,?,?)",
                (
                    export_id,
                    artifact_id,
                    row["project_id"],
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
                "write.export",
                actor,
                {
                    "artifactId": artifact_id,
                    "exportId": export_id,
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
                "format": export_format,
                "filename": filename,
                "path": str(destination),
                "sha256": digest,
                "includeProvenance": include,
                "receiptId": receipt_id,
                "createdAt": now,
            }
