from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

from .audit import AuditLog, hash_value


_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_UNSET = object()


class ComputationState(str, Enum):
    VALID = "VALID"
    STALE = "STALE"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ComputationRecord:
    computation_id: str
    input_hashes: dict[str, str]
    dependency_hashes: dict[str, str]
    producer: str
    result_hash: str
    result_value: Any | None
    duration_ms: float
    cpu_ms: float
    memory_bytes: int
    cost_units: float
    invalidation_rule: str
    proof_reference: str
    state: ComputationState


@dataclass(frozen=True)
class ReuseDecision:
    computation_id: str
    reusable: bool
    reason: str
    receipt_sha256: str


class SQLiteComputationMemory:
    """Small persistent computation ledger with dependency invalidation."""

    def __init__(
        self,
        path: str | Path,
        *,
        audit: AuditLog | None = None,
    ) -> None:
        self.path = Path(path)
        self.audit = audit or AuditLog()
        self._connection = sqlite3.connect(self.path)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute("PRAGMA journal_mode=DELETE")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS computations (
                computation_id TEXT PRIMARY KEY,
                input_hashes_json TEXT NOT NULL,
                producer TEXT NOT NULL,
                result_hash TEXT NOT NULL,
                result_json TEXT,
                duration_ms REAL NOT NULL,
                cpu_ms REAL NOT NULL,
                memory_bytes INTEGER NOT NULL,
                cost_units REAL NOT NULL,
                invalidation_rule TEXT NOT NULL,
                proof_reference TEXT NOT NULL,
                state TEXT NOT NULL
                    CHECK (state IN ('VALID', 'STALE', 'FAILED'))
            );
            CREATE TABLE IF NOT EXISTS computation_dependencies (
                computation_id TEXT NOT NULL,
                dependency_id TEXT NOT NULL,
                expected_result_hash TEXT NOT NULL,
                PRIMARY KEY (computation_id, dependency_id),
                FOREIGN KEY (computation_id)
                    REFERENCES computations(computation_id) ON DELETE CASCADE,
                FOREIGN KEY (dependency_id)
                    REFERENCES computations(computation_id)
            );
            CREATE INDEX IF NOT EXISTS idx_computation_dependency
                ON computation_dependencies(dependency_id);
            """
        )
        columns = {
            row["name"]
            for row in self._connection.execute(
                "PRAGMA table_info(computations)"
            ).fetchall()
        }
        if "result_json" not in columns:
            self._connection.execute(
                "ALTER TABLE computations ADD COLUMN result_json TEXT"
            )
        self._connection.commit()

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SQLiteComputationMemory":
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        self.close()

    def record(
        self,
        *,
        computation_id: str,
        input_hashes: dict[str, str],
        dependency_hashes: dict[str, str],
        producer: str,
        result_hash: str,
        duration_ms: float,
        cpu_ms: float,
        memory_bytes: int,
        cost_units: float,
        invalidation_rule: str,
        proof_reference: str,
        result_value: Any = _UNSET,
        state: ComputationState = ComputationState.VALID,
    ) -> ComputationRecord:
        self._validate_record(
            computation_id,
            input_hashes,
            dependency_hashes,
            producer,
            result_hash,
            result_value,
            duration_ms,
            cpu_ms,
            memory_bytes,
            cost_units,
            invalidation_rule,
            proof_reference,
        )
        previous = self._connection.execute(
            "SELECT result_hash FROM computations WHERE computation_id=?",
            (computation_id,),
        ).fetchone()
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO computations (
                    computation_id, input_hashes_json, producer, result_hash, result_json,
                    duration_ms, cpu_ms, memory_bytes, cost_units,
                    invalidation_rule, proof_reference, state
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(computation_id) DO UPDATE SET
                    input_hashes_json=excluded.input_hashes_json,
                    producer=excluded.producer,
                    result_hash=excluded.result_hash,
                    result_json=excluded.result_json,
                    duration_ms=excluded.duration_ms,
                    cpu_ms=excluded.cpu_ms,
                    memory_bytes=excluded.memory_bytes,
                    cost_units=excluded.cost_units,
                    invalidation_rule=excluded.invalidation_rule,
                    proof_reference=excluded.proof_reference,
                    state=excluded.state
                """,
                (
                    computation_id,
                    self._json(input_hashes),
                    producer,
                    result_hash,
                    (
                        None
                        if result_value is _UNSET
                        else json.dumps(
                            result_value,
                            ensure_ascii=False,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                    ),
                    duration_ms,
                    cpu_ms,
                    memory_bytes,
                    cost_units,
                    invalidation_rule,
                    proof_reference,
                    state.value,
                ),
            )
            self._connection.execute(
                "DELETE FROM computation_dependencies WHERE computation_id=?",
                (computation_id,),
            )
            self._connection.executemany(
                """
                INSERT INTO computation_dependencies (
                    computation_id, dependency_id, expected_result_hash
                ) VALUES (?, ?, ?)
                """,
                [
                    (computation_id, dependency_id, digest)
                    for dependency_id, digest in sorted(dependency_hashes.items())
                ],
            )
            invalidated = ()
            if previous is not None and previous["result_hash"] != result_hash:
                invalidated = self._invalidate_dependents(computation_id)

        if invalidated:
            self.audit.emit(
                "computation.invalidated",
                "computation-memory",
                "dependency-result-changed",
                {
                    "changed_computation_id": computation_id,
                    "invalidated": list(invalidated),
                    "mutation": True,
                },
                target=computation_id,
            )
        self.audit.emit(
            "computation.recorded",
            "computation-memory",
            producer,
            {
                "input_hashes": input_hashes,
                "dependency_hashes": dependency_hashes,
                "result_hash": result_hash,
                "result_value_stored": result_value is not _UNSET,
                "duration_ms": duration_ms,
                "cpu_ms": cpu_ms,
                "memory_bytes": memory_bytes,
                "cost_units": cost_units,
                "state": state.value,
                "proof_reference": proof_reference,
                "mutation": True,
            },
            target=computation_id,
        )
        record = self.get(computation_id)
        assert record is not None
        return record

    def get(self, computation_id: str) -> ComputationRecord | None:
        row = self._connection.execute(
            "SELECT * FROM computations WHERE computation_id=?",
            (computation_id,),
        ).fetchone()
        if row is None:
            return None
        dependencies = self._connection.execute(
            """
            SELECT dependency_id, expected_result_hash
            FROM computation_dependencies
            WHERE computation_id=?
            ORDER BY dependency_id
            """,
            (computation_id,),
        ).fetchall()
        return ComputationRecord(
            computation_id=row["computation_id"],
            input_hashes=json.loads(row["input_hashes_json"]),
            dependency_hashes={
                item["dependency_id"]: item["expected_result_hash"]
                for item in dependencies
            },
            producer=row["producer"],
            result_hash=row["result_hash"],
            result_value=(
                None
                if row["result_json"] is None
                else json.loads(row["result_json"])
            ),
            duration_ms=row["duration_ms"],
            cpu_ms=row["cpu_ms"],
            memory_bytes=row["memory_bytes"],
            cost_units=row["cost_units"],
            invalidation_rule=row["invalidation_rule"],
            proof_reference=row["proof_reference"],
            state=ComputationState(row["state"]),
        )

    def check_reuse(
        self,
        computation_id: str,
        *,
        input_hashes: dict[str, str],
        dependency_hashes: dict[str, str],
        expected_producer: str | None = None,
        expected_invalidation_rule: str | None = None,
        require_proof: bool = False,
        require_result_value: bool = False,
    ) -> ReuseDecision:
        record = self.get(computation_id)
        if record is None:
            reusable, reason = False, "computation is absent"
        elif record.state is not ComputationState.VALID:
            reusable, reason = False, f"computation state is {record.state.value}"
        elif expected_producer is not None and record.producer != expected_producer:
            reusable, reason = False, "producer or handler version changed"
        elif (
            expected_invalidation_rule is not None
            and record.invalidation_rule != expected_invalidation_rule
        ):
            reusable, reason = False, "invalidation rule changed"
        elif require_proof and not record.proof_reference:
            reusable, reason = False, "proof reference is absent"
        elif require_result_value and record.result_value is None:
            reusable, reason = False, "reusable result value is absent"
        elif (
            record.result_value is not None
            and hash_value(record.result_value) != record.result_hash
        ):
            reusable, reason = False, "stored result value does not match result hash"
        elif record.input_hashes != input_hashes:
            reusable, reason = False, "input hashes changed"
        elif record.dependency_hashes != dependency_hashes:
            reusable, reason = False, "dependency hashes changed"
        else:
            reusable, reason = True, "inputs and valid dependency results match"
            for dependency_id, expected_hash in dependency_hashes.items():
                dependency = self.get(dependency_id)
                if (
                    dependency is None
                    or dependency.state is not ComputationState.VALID
                    or dependency.result_hash != expected_hash
                ):
                    reusable = False
                    reason = f"dependency {dependency_id} is absent, stale, or changed"
                    break
        receipt = self.audit.emit(
            "computation.reuse-checked",
            "computation-memory",
            "reuse" if reusable else "recompute",
            {
                "input_hashes": input_hashes,
                "dependency_hashes": dependency_hashes,
                "expected_producer": expected_producer,
                "expected_invalidation_rule": expected_invalidation_rule,
                "require_proof": require_proof,
                "require_result_value": require_result_value,
                "reusable": reusable,
                "reason": reason,
                "mutation": False,
            },
            target=computation_id,
        )
        return ReuseDecision(
            computation_id=computation_id,
            reusable=reusable,
            reason=reason,
            receipt_sha256=receipt.sha256,
        )

    def list_records(self) -> tuple[ComputationRecord, ...]:
        rows = self._connection.execute(
            "SELECT computation_id FROM computations ORDER BY computation_id"
        ).fetchall()
        return tuple(
            record
            for row in rows
            if (record := self.get(row["computation_id"])) is not None
        )

    def integrity_check(self) -> str:
        return self._connection.execute("PRAGMA integrity_check").fetchone()[0]

    def journal_mode(self) -> str:
        return self._connection.execute("PRAGMA journal_mode").fetchone()[0]

    def _invalidate_dependents(self, computation_id: str) -> tuple[str, ...]:
        rows = self._connection.execute(
            """
            WITH RECURSIVE dependents(computation_id) AS (
                SELECT computation_id
                FROM computation_dependencies
                WHERE dependency_id=?
                UNION
                SELECT edge.computation_id
                FROM computation_dependencies AS edge
                JOIN dependents
                  ON edge.dependency_id=dependents.computation_id
            )
            SELECT computation_id FROM dependents ORDER BY computation_id
            """,
            (computation_id,),
        ).fetchall()
        identifiers = tuple(row["computation_id"] for row in rows)
        self._connection.executemany(
            """
            UPDATE computations SET state='STALE'
            WHERE computation_id=? AND state='VALID'
            """,
            [(identifier,) for identifier in identifiers],
        )
        return identifiers

    @staticmethod
    def _json(value: dict[str, str]) -> str:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def _validate_digest(name: str, value: str) -> None:
        if not _DIGEST.fullmatch(value):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest")

    @classmethod
    def _validate_record(
        cls,
        computation_id: str,
        input_hashes: dict[str, str],
        dependency_hashes: dict[str, str],
        producer: str,
        result_hash: str,
        result_value: Any,
        duration_ms: float,
        cpu_ms: float,
        memory_bytes: int,
        cost_units: float,
        invalidation_rule: str,
        proof_reference: str,
    ) -> None:
        required = {
            "computation_id": computation_id,
            "producer": producer,
            "invalidation_rule": invalidation_rule,
            "proof_reference": proof_reference,
        }
        if any(not value for value in required.values()):
            raise ValueError("ledger identity, producer, rule, and proof are required")
        cls._validate_digest("result_hash", result_hash)
        if result_value is not _UNSET and hash_value(result_value) != result_hash:
            raise ValueError("result_value does not match result_hash")
        for name, digest in {**input_hashes, **dependency_hashes}.items():
            cls._validate_digest(name, digest)
        if duration_ms < 0 or cpu_ms < 0 or memory_bytes < 0 or cost_units < 0:
            raise ValueError("resource and cost measurements cannot be negative")
