from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Protocol

from .capabilities import CapabilityGrant


class ProcessState(str, Enum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    SUSPENDED = "SUSPENDED"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


TERMINAL_STATES = {
    ProcessState.DONE,
    ProcessState.FAILED,
    ProcessState.CANCELLED,
}


@dataclass
class ProcessRecord:
    pid: int
    name: str
    runner_id: str
    grants: tuple[CapabilityGrant, ...] = ()
    parent_pid: int | None = None
    state: ProcessState = ProcessState.NEW
    result: Any = None
    error: str | None = None
    waiting_for: str | None = None
    suspended_from: ProcessState | None = None
    wake_pending: bool = False
    last_event: dict[str, Any] | None = None
    ticks: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "pid": self.pid,
            "name": self.name,
            "runner_id": self.runner_id,
            "grants": [
                {"name": grant.name, "scopes": list(grant.scopes)}
                for grant in self.grants
            ],
            "parent_pid": self.parent_pid,
            "state": self.state.value,
            "result": self.result,
            "error": self.error,
            "waiting_for": self.waiting_for,
            "suspended_from": self.suspended_from.value if self.suspended_from else None,
            "wake_pending": self.wake_pending,
            "last_event": self.last_event,
            "ticks": self.ticks,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ProcessRecord":
        return cls(
            pid=int(value["pid"]),
            name=str(value["name"]),
            runner_id=str(value["runner_id"]),
            grants=tuple(
                CapabilityGrant(str(grant["name"]), tuple(str(scope) for scope in grant["scopes"]))
                for grant in value.get("grants", [])
            ),
            parent_pid=value.get("parent_pid"),
            state=ProcessState(value["state"]),
            result=value.get("result"),
            error=value.get("error"),
            waiting_for=value.get("waiting_for"),
            suspended_from=(
                ProcessState(value["suspended_from"])
                if value.get("suspended_from")
                else None
            ),
            wake_pending=bool(value.get("wake_pending", False)),
            last_event=value.get("last_event"),
            ticks=int(value.get("ticks", 0)),
            metadata=dict(value.get("metadata", {})),
            created_at=str(value.get("created_at", "")),
            updated_at=str(value.get("updated_at", "")),
        )

    def clone(self) -> "ProcessRecord":
        return ProcessRecord.from_dict(json.loads(_canonical_json(self.as_dict())))


class ProcessTable(Protocol):
    def allocate_pid(self) -> int: ...

    def put(self, record: ProcessRecord) -> None: ...

    def get(self, pid: int) -> ProcessRecord: ...

    def list(self) -> list[ProcessRecord]: ...

    def append_receipt(self, receipt: dict[str, Any]) -> None: ...

    def list_receipts(self) -> list[dict[str, Any]]: ...

    def integrity_check(self) -> str: ...

    def close(self) -> None: ...


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class InMemoryProcessTable:
    def __init__(self) -> None:
        self._next_pid = 1
        self._records: dict[int, ProcessRecord] = {}
        self._receipts: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def allocate_pid(self) -> int:
        with self._lock:
            pid = self._next_pid
            self._next_pid += 1
            return pid

    def put(self, record: ProcessRecord) -> None:
        with self._lock:
            _canonical_json(record.as_dict())
            self._records[record.pid] = record.clone()
            self._next_pid = max(self._next_pid, record.pid + 1)

    def get(self, pid: int) -> ProcessRecord:
        with self._lock:
            if pid not in self._records:
                raise KeyError(pid)
            return self._records[pid].clone()

    def list(self) -> list[ProcessRecord]:
        with self._lock:
            return [self._records[pid].clone() for pid in sorted(self._records)]

    def append_receipt(self, receipt: dict[str, Any]) -> None:
        with self._lock:
            self._receipts.append(json.loads(_canonical_json(receipt)))

    def list_receipts(self) -> list[dict[str, Any]]:
        with self._lock:
            return json.loads(_canonical_json(self._receipts))

    def integrity_check(self) -> str:
        return "ok"

    def journal_mode(self) -> str:
        return "memory"

    def close(self) -> None:
        return None


class SQLiteProcessTable:
    """Transactional local process table using SQLite rollback journaling.

    V0.2 deliberately does not enable WAL. The kernel serializes its writes and
    uses SQLite's rollback journal for the smallest crash-recoverable contract.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve(strict=False)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(
            self.path,
            timeout=5.0,
            isolation_level="IMMEDIATE",
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute("PRAGMA busy_timeout=5000")
        self._connection.execute("PRAGMA journal_mode=DELETE")
        self._create_schema()

    def _create_schema(self) -> None:
        states = ",".join(f"'{state.value}'" for state in ProcessState)
        with self._connection:
            self._connection.executescript(
                f"""
                CREATE TABLE IF NOT EXISTS kernel_meta (
                    key TEXT PRIMARY KEY,
                    value INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS processes (
                    pid INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    runner_id TEXT NOT NULL,
                    grants_json TEXT NOT NULL,
                    parent_pid INTEGER REFERENCES processes(pid),
                    state TEXT NOT NULL CHECK(state IN ({states})),
                    result_json TEXT,
                    error TEXT,
                    waiting_for TEXT,
                    suspended_from TEXT,
                    wake_pending INTEGER NOT NULL CHECK(wake_pending IN (0, 1)),
                    last_event_json TEXT,
                    ticks INTEGER NOT NULL CHECK(ticks >= 0),
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS receipts (
                    sequence INTEGER PRIMARY KEY,
                    sha256 TEXT NOT NULL UNIQUE,
                    receipt_json TEXT NOT NULL
                );
                """
            )
            row = self._connection.execute(
                "SELECT COALESCE(MAX(pid), 0) + 1 FROM processes"
            ).fetchone()
            next_pid = int(row[0])
            self._connection.execute(
                "INSERT OR IGNORE INTO kernel_meta(key, value) VALUES('next_pid', ?)",
                (next_pid,),
            )
            self._connection.execute(
                "UPDATE kernel_meta SET value = MAX(value, ?) WHERE key='next_pid'",
                (next_pid,),
            )

    def allocate_pid(self) -> int:
        with self._lock, self._connection:
            row = self._connection.execute(
                "SELECT value FROM kernel_meta WHERE key='next_pid'"
            ).fetchone()
            if row is None:
                raise RuntimeError("kernel PID sequence is missing")
            pid = int(row[0])
            self._connection.execute(
                "UPDATE kernel_meta SET value=? WHERE key='next_pid'",
                (pid + 1,),
            )
            return pid

    def put(self, record: ProcessRecord) -> None:
        value = record.as_dict()
        grants_json = _canonical_json(value["grants"])
        result_json = _canonical_json(value["result"]) if value["result"] is not None else None
        last_event_json = (
            _canonical_json(value["last_event"]) if value["last_event"] is not None else None
        )
        metadata_json = _canonical_json(value["metadata"])
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO processes(
                    pid, name, runner_id, grants_json, parent_pid, state,
                    result_json, error, waiting_for, suspended_from,
                    wake_pending, last_event_json, ticks, metadata_json,
                    created_at, updated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(pid) DO UPDATE SET
                    name=excluded.name,
                    runner_id=excluded.runner_id,
                    grants_json=excluded.grants_json,
                    parent_pid=excluded.parent_pid,
                    state=excluded.state,
                    result_json=excluded.result_json,
                    error=excluded.error,
                    waiting_for=excluded.waiting_for,
                    suspended_from=excluded.suspended_from,
                    wake_pending=excluded.wake_pending,
                    last_event_json=excluded.last_event_json,
                    ticks=excluded.ticks,
                    metadata_json=excluded.metadata_json,
                    created_at=excluded.created_at,
                    updated_at=excluded.updated_at
                """,
                (
                    record.pid,
                    record.name,
                    record.runner_id,
                    grants_json,
                    record.parent_pid,
                    record.state.value,
                    result_json,
                    record.error,
                    record.waiting_for,
                    record.suspended_from.value if record.suspended_from else None,
                    int(record.wake_pending),
                    last_event_json,
                    record.ticks,
                    metadata_json,
                    record.created_at,
                    record.updated_at,
                ),
            )
            self._connection.execute(
                "UPDATE kernel_meta SET value = MAX(value, ?) WHERE key='next_pid'",
                (record.pid + 1,),
            )

    @staticmethod
    def _record_from_row(row: sqlite3.Row) -> ProcessRecord:
        return ProcessRecord.from_dict(
            {
                "pid": row["pid"],
                "name": row["name"],
                "runner_id": row["runner_id"],
                "grants": json.loads(row["grants_json"]),
                "parent_pid": row["parent_pid"],
                "state": row["state"],
                "result": json.loads(row["result_json"]) if row["result_json"] is not None else None,
                "error": row["error"],
                "waiting_for": row["waiting_for"],
                "suspended_from": row["suspended_from"],
                "wake_pending": bool(row["wake_pending"]),
                "last_event": (
                    json.loads(row["last_event_json"])
                    if row["last_event_json"] is not None
                    else None
                ),
                "ticks": row["ticks"],
                "metadata": json.loads(row["metadata_json"]),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
            }
        )

    def get(self, pid: int) -> ProcessRecord:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM processes WHERE pid=?",
                (pid,),
            ).fetchone()
            if row is None:
                raise KeyError(pid)
            return self._record_from_row(row)

    def list(self) -> list[ProcessRecord]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM processes ORDER BY pid"
            ).fetchall()
            return [self._record_from_row(row) for row in rows]

    def append_receipt(self, receipt: dict[str, Any]) -> None:
        payload = _canonical_json(receipt)
        with self._lock, self._connection:
            self._connection.execute(
                "INSERT INTO receipts(sequence, sha256, receipt_json) VALUES(?,?,?)",
                (int(receipt["sequence"]), str(receipt["sha256"]), payload),
            )

    def list_receipts(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT receipt_json FROM receipts ORDER BY sequence"
            ).fetchall()
            return [json.loads(row[0]) for row in rows]

    def integrity_check(self) -> str:
        with self._lock:
            return str(self._connection.execute("PRAGMA integrity_check").fetchone()[0])

    def journal_mode(self) -> str:
        with self._lock:
            return str(self._connection.execute("PRAGMA journal_mode").fetchone()[0]).lower()

    def close(self) -> None:
        with self._lock:
            self._connection.close()
