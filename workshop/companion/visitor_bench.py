from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_ROOMS = {"write", "music"}
MAX_CONTENT_BYTES = 256 * 1024


class VisitorBenchError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code = code
        self.status = status


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


class VisitorBench:
    def __init__(self, database: Path):
        self.database = database
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database, timeout=5.0)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        con = self._connect()
        con.executescript("""
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS guest_submissions(
          id TEXT PRIMARY KEY,
          guest_identity TEXT NOT NULL,
          room TEXT NOT NULL CHECK(room IN ('write','music')),
          operation TEXT NOT NULL,
          title TEXT NOT NULL,
          content TEXT NOT NULL,
          content_sha256 TEXT NOT NULL,
          authority_state TEXT NOT NULL DEFAULT 'GUEST_SANDBOX_DRAFT',
          owner_reviewed_at TEXT,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS guest_promotions(
          id TEXT PRIMARY KEY,
          submission_id TEXT NOT NULL UNIQUE,
          owner_artifact_id TEXT NOT NULL,
          receipt_id TEXT NOT NULL,
          promoted_by TEXT NOT NULL,
          created_at TEXT NOT NULL,
          FOREIGN KEY(submission_id) REFERENCES guest_submissions(id)
        );
        """)
        con.commit()
        con.close()

    def create(self, identity: str, value: dict[str, Any]) -> dict[str, Any]:
        room = str(value.get("room", "")).strip().lower()
        title = str(value.get("title", "")).strip()
        content = str(value.get("content", ""))
        operation = str(value.get("operation", "draft")).strip() or "draft"
        if room not in ALLOWED_ROOMS:
            raise VisitorBenchError("guest_room_denied", "Visitor's Bench supports Write and Music only")
        if not title or not content.strip():
            raise VisitorBenchError("guest_content_empty", "A title and non-empty content are required")
        if len(content.encode("utf-8")) > MAX_CONTENT_BYTES:
            raise VisitorBenchError("guest_content_too_large", "Visitor's Bench content exceeds 256 KiB", 413)
        submission_id = str(uuid.uuid4())
        created_at = utc()
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest().upper()
        con = self._connect()
        con.execute(
            "INSERT INTO guest_submissions VALUES(?,?,?,?,?,?,?,?,NULL,?)",
            (submission_id, identity, room, operation, title, content, digest, "GUEST_SANDBOX_DRAFT", created_at),
        )
        con.commit()
        con.close()
        return {"ok": True, "submission": self.get(submission_id, identity=identity)}

    def list(self, *, identity: str | None = None, owner: bool = False) -> list[dict[str, Any]]:
        con = self._connect()
        if owner:
            rows = con.execute("SELECT * FROM guest_submissions ORDER BY created_at DESC").fetchall()
        else:
            rows = con.execute(
                "SELECT * FROM guest_submissions WHERE guest_identity=? ORDER BY created_at DESC", (identity,)
            ).fetchall()
        result = [self._row(con, row) for row in rows]
        con.close()
        return result

    def get(self, submission_id: str, *, identity: str | None = None, owner: bool = False) -> dict[str, Any]:
        con = self._connect()
        row = con.execute("SELECT * FROM guest_submissions WHERE id=?", (submission_id,)).fetchone()
        if not row or (not owner and row["guest_identity"] != identity):
            con.close()
            raise VisitorBenchError("guest_submission_not_found", "Visitor's Bench submission was not found", 404)
        result = self._row(con, row)
        con.close()
        return result

    def _row(self, con: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        promotion = con.execute(
            "SELECT owner_artifact_id,receipt_id,created_at FROM guest_promotions WHERE submission_id=?", (row["id"],)
        ).fetchone()
        value = dict(row)
        value["promotion"] = dict(promotion) if promotion else None
        return value

    def record_promotion(self, submission_id: str, artifact_id: str, receipt_id: str, owner: str) -> None:
        con = self._connect()
        try:
            con.execute(
                "INSERT INTO guest_promotions VALUES(?,?,?,?,?,?)",
                (str(uuid.uuid4()), submission_id, artifact_id, receipt_id, owner, utc()),
            )
            con.execute("UPDATE guest_submissions SET owner_reviewed_at=? WHERE id=?", (utc(), submission_id))
            con.commit()
        except sqlite3.IntegrityError as exc:
            raise VisitorBenchError("guest_already_promoted", "This submission was already promoted", 409) from exc
        finally:
            con.close()

