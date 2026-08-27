from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator

SCHEMA_VERSION = "0.2"


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    project_id: str
    source_path: str
    sha256: str
    status: str
    provenance: dict[str, Any]
    content_text: str = ""
    size_bytes: int | None = None
    modified_ns: int | None = None

    @property
    def filename(self) -> str:
        return Path(self.source_path).name

    def fingerprint(self) -> str:
        payload = asdict(self)
        return hashlib.sha256(
            json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest().upper()


@dataclass(frozen=True)
class SyncResult:
    generation: int
    inserted: int
    changed: int
    unchanged: int
    tombstoned: int


@dataclass(frozen=True)
class StaleEntry:
    artifact_id: str
    reason: str


class ArtifactCompass:
    """Deterministic SQLite/FTS5 metadata index with provenance and tombstones."""

    def __init__(self, database_path: str | os.PathLike[str]) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.database_path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    def __enter__(self) -> "ArtifactCompass":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self.close()

    def close(self) -> None:
        self.connection.close()

    @property
    def generation(self) -> int:
        row = self.connection.execute("SELECT value FROM compass_meta WHERE key = 'generation'").fetchone()
        return int(row[0])

    def sync(self, records: Iterable[ArtifactRecord]) -> SyncResult:
        ordered = self._validate_records(records)
        next_generation = self.generation + 1
        inserted = changed = unchanged = tombstoned = 0
        seen: set[str] = set()
        with self.connection:
            for record in ordered:
                seen.add(record.artifact_id)
                existing = self.connection.execute(
                    "SELECT source_fingerprint, tombstoned FROM compass_artifacts WHERE artifact_id = ?",
                    (record.artifact_id,),
                ).fetchone()
                fingerprint = record.fingerprint()
                if existing is None:
                    inserted += 1
                    self._upsert_record(record, fingerprint, next_generation)
                elif existing["source_fingerprint"] != fingerprint or existing["tombstoned"]:
                    changed += 1
                    self._upsert_record(record, fingerprint, next_generation)
                else:
                    unchanged += 1
                    self.connection.execute(
                        "UPDATE compass_artifacts SET indexed_generation = ? WHERE artifact_id = ?",
                        (next_generation, record.artifact_id),
                    )

            active_rows = self.connection.execute(
                "SELECT artifact_id FROM compass_artifacts WHERE tombstoned = 0 ORDER BY artifact_id"
            ).fetchall()
            for row in active_rows:
                artifact_id = row["artifact_id"]
                if artifact_id not in seen:
                    tombstoned += 1
                    self.connection.execute(
                        "UPDATE compass_artifacts SET tombstoned = 1, indexed_generation = ? WHERE artifact_id = ?",
                        (next_generation, artifact_id),
                    )
            self.connection.execute(
                "UPDATE compass_meta SET value = ? WHERE key = 'generation'",
                (str(next_generation),),
            )
        return SyncResult(next_generation, inserted, changed, unchanged, tombstoned)

    def rebuild(self, records: Iterable[ArtifactRecord]) -> SyncResult:
        ordered = self._validate_records(records)
        with self.connection:
            self.connection.execute("DELETE FROM compass_fts")
            self.connection.execute("DELETE FROM compass_artifacts")
        return self.sync(ordered)

    def detect_stale(self, records: Iterable[ArtifactRecord]) -> tuple[StaleEntry, ...]:
        ordered = self._validate_records(records)
        supplied = {record.artifact_id: record for record in ordered}
        stale: list[StaleEntry] = []
        rows = self.connection.execute(
            "SELECT artifact_id, source_fingerprint, tombstoned FROM compass_artifacts ORDER BY artifact_id"
        ).fetchall()
        indexed_ids: set[str] = set()
        for row in rows:
            artifact_id = row["artifact_id"]
            indexed_ids.add(artifact_id)
            record = supplied.get(artifact_id)
            if record is None and not row["tombstoned"]:
                stale.append(StaleEntry(artifact_id, "missing_from_source"))
            elif record is not None and row["tombstoned"]:
                stale.append(StaleEntry(artifact_id, "source_returned_after_tombstone"))
            elif record is not None and record.fingerprint() != row["source_fingerprint"]:
                stale.append(StaleEntry(artifact_id, "source_changed"))
        for artifact_id in sorted(set(supplied) - indexed_ids):
            stale.append(StaleEntry(artifact_id, "not_indexed"))
        return tuple(sorted(stale, key=lambda item: (item.artifact_id, item.reason)))

    def search(
        self,
        query: str = "",
        *,
        field: str | None = None,
        exact_phrase: bool = False,
        project_id: str | None = None,
        status: str | None = None,
        provenance: str | None = None,
        include_tombstoned: bool = False,
    ) -> list[dict[str, Any]]:
        if field not in {None, "filename", "path"}:
            raise ValueError("field must be filename, path, or None")
        conditions = [] if include_tombstoned else ["a.tombstoned = 0"]
        parameters: list[Any] = []
        join = ""
        if query:
            if field == "filename":
                conditions.append("instr(lower(a.filename), lower(?)) > 0")
                parameters.append(query)
            elif field == "path":
                conditions.append("instr(lower(a.source_path), lower(?)) > 0")
                parameters.append(query)
            else:
                join = "JOIN compass_fts AS f ON f.artifact_id = a.artifact_id"
                conditions.append("compass_fts MATCH ?")
                parameters.append(self._fts_query(query, exact_phrase=exact_phrase))
        if project_id is not None:
            conditions.append("a.project_id = ?")
            parameters.append(project_id)
        if status is not None:
            conditions.append("a.status = ?")
            parameters.append(status)
        if provenance is not None:
            conditions.append("instr(lower(a.provenance_text), lower(?)) > 0")
            parameters.append(provenance)
        where = " AND ".join(conditions) if conditions else "1 = 1"
        rows = self.connection.execute(
            f"""
            SELECT a.artifact_id, a.project_id, a.source_path, a.filename, a.sha256,
                   a.status, a.provenance_json, a.size_bytes, a.modified_ns,
                   a.indexed_generation, a.tombstoned
            FROM compass_artifacts AS a
            {join}
            WHERE {where}
            ORDER BY lower(a.source_path), a.source_path, a.artifact_id
            """,
            parameters,
        ).fetchall()
        return [self._row_to_result(row) for row in rows]

    def duplicate_groups(self, *, project_id: str | None = None) -> list[dict[str, Any]]:
        parameters: list[Any] = []
        project_condition = ""
        if project_id is not None:
            project_condition = " AND project_id = ?"
            parameters.append(project_id)
        hashes = self.connection.execute(
            f"""
            SELECT sha256, COUNT(*) AS artifact_count
            FROM compass_artifacts
            WHERE tombstoned = 0 AND sha256 <> '' {project_condition}
            GROUP BY sha256
            HAVING COUNT(*) > 1
            ORDER BY sha256
            """,
            parameters,
        ).fetchall()
        groups: list[dict[str, Any]] = []
        for duplicate in hashes:
            row_parameters: list[Any] = [duplicate["sha256"]]
            row_project_condition = ""
            if project_id is not None:
                row_project_condition = " AND project_id = ?"
                row_parameters.append(project_id)
            rows = self.connection.execute(
                f"""
                SELECT artifact_id, project_id, source_path, filename, sha256, status,
                       provenance_json, size_bytes, modified_ns, indexed_generation, tombstoned
                FROM compass_artifacts
                WHERE tombstoned = 0 AND sha256 = ? {row_project_condition}
                ORDER BY lower(source_path), source_path, artifact_id
                """,
                row_parameters,
            ).fetchall()
            artifacts = [self._row_to_result(row) for row in rows]
            groups.append(
                {
                    "sha256": duplicate["sha256"],
                    "artifact_count": len(artifacts),
                    "all_source_paths": [artifact["source_path"] for artifact in artifacts],
                    "artifacts": artifacts,
                }
            )
        return groups

    def _initialize(self) -> None:
        with self.connection:
            self.connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS compass_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS compass_artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    source_path TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    sha256 TEXT NOT NULL,
                    status TEXT NOT NULL,
                    provenance_json TEXT NOT NULL,
                    provenance_text TEXT NOT NULL,
                    content_text TEXT NOT NULL,
                    size_bytes INTEGER,
                    modified_ns INTEGER,
                    source_fingerprint TEXT NOT NULL,
                    indexed_generation INTEGER NOT NULL,
                    tombstoned INTEGER NOT NULL DEFAULT 0 CHECK (tombstoned IN (0, 1))
                );
                CREATE INDEX IF NOT EXISTS idx_compass_project_status
                    ON compass_artifacts(project_id, status, tombstoned);
                CREATE INDEX IF NOT EXISTS idx_compass_sha
                    ON compass_artifacts(sha256, tombstoned);
                CREATE VIRTUAL TABLE IF NOT EXISTS compass_fts USING fts5(
                    artifact_id UNINDEXED,
                    filename,
                    source_path,
                    content_text,
                    provenance_text,
                    tokenize = 'unicode61'
                );
                """
            )
            self.connection.execute(
                "INSERT OR IGNORE INTO compass_meta(key, value) VALUES ('schema_version', ?)",
                (SCHEMA_VERSION,),
            )
            self.connection.execute("INSERT OR IGNORE INTO compass_meta(key, value) VALUES ('generation', '0')")
        version = self.connection.execute("SELECT value FROM compass_meta WHERE key = 'schema_version'").fetchone()[0]
        if version != SCHEMA_VERSION:
            raise ValueError(f"unsupported Artifact Compass schema: {version}")

    def _upsert_record(self, record: ArtifactRecord, fingerprint: str, generation: int) -> None:
        provenance_json = json.dumps(record.provenance, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        provenance_text = " ".join(self._flatten_strings(record.provenance))
        self.connection.execute(
            """
            INSERT INTO compass_artifacts(
                artifact_id, project_id, source_path, filename, sha256, status,
                provenance_json, provenance_text, content_text, size_bytes, modified_ns,
                source_fingerprint, indexed_generation, tombstoned
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(artifact_id) DO UPDATE SET
                project_id = excluded.project_id,
                source_path = excluded.source_path,
                filename = excluded.filename,
                sha256 = excluded.sha256,
                status = excluded.status,
                provenance_json = excluded.provenance_json,
                provenance_text = excluded.provenance_text,
                content_text = excluded.content_text,
                size_bytes = excluded.size_bytes,
                modified_ns = excluded.modified_ns,
                source_fingerprint = excluded.source_fingerprint,
                indexed_generation = excluded.indexed_generation,
                tombstoned = 0
            """,
            (
                record.artifact_id,
                record.project_id,
                record.source_path,
                record.filename,
                record.sha256.upper(),
                record.status,
                provenance_json,
                provenance_text,
                record.content_text,
                record.size_bytes,
                record.modified_ns,
                fingerprint,
                generation,
            ),
        )
        self.connection.execute("DELETE FROM compass_fts WHERE artifact_id = ?", (record.artifact_id,))
        self.connection.execute(
            "INSERT INTO compass_fts(artifact_id, filename, source_path, content_text, provenance_text) VALUES (?, ?, ?, ?, ?)",
            (record.artifact_id, record.filename, record.source_path, record.content_text, provenance_text),
        )

    @staticmethod
    def _validate_records(records: Iterable[ArtifactRecord]) -> list[ArtifactRecord]:
        ordered = sorted(records, key=lambda record: record.artifact_id)
        seen_ids: set[str] = set()
        for record in ordered:
            if not record.artifact_id or record.artifact_id in seen_ids:
                raise ValueError(f"artifact ids must be non-empty and unique: {record.artifact_id}")
            if not record.project_id or not record.source_path or not record.status:
                raise ValueError(f"artifact {record.artifact_id} is missing required metadata")
            if record.sha256 and (len(record.sha256) != 64 or any(character not in "0123456789abcdefABCDEF" for character in record.sha256)):
                raise ValueError(f"artifact {record.artifact_id} has an invalid SHA-256")
            seen_ids.add(record.artifact_id)
        return ordered

    @staticmethod
    def _flatten_strings(value: Any) -> Iterator[str]:
        if isinstance(value, dict):
            for key in sorted(value):
                yield str(key)
                yield from ArtifactCompass._flatten_strings(value[key])
        elif isinstance(value, list):
            for item in value:
                yield from ArtifactCompass._flatten_strings(item)
        elif value is not None:
            yield str(value)

    @staticmethod
    def _fts_query(query: str, *, exact_phrase: bool) -> str:
        normalized = query.strip()
        if not normalized:
            raise ValueError("FTS query must be non-empty")
        if exact_phrase:
            return '"' + normalized.replace('"', '""') + '"'
        tokens = [token for token in normalized.replace('"', " ").split() if token]
        return " AND ".join('"' + token.replace('"', '""') + '"' for token in tokens)

    @staticmethod
    def _row_to_result(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "artifact_id": row["artifact_id"],
            "project_id": row["project_id"],
            "source_path": row["source_path"],
            "filename": row["filename"],
            "sha256": row["sha256"],
            "status": row["status"],
            "provenance": json.loads(row["provenance_json"]),
            "size_bytes": row["size_bytes"],
            "modified_ns": row["modified_ns"],
            "indexed_generation": row["indexed_generation"],
            "tombstoned": bool(row["tombstoned"]),
        }
