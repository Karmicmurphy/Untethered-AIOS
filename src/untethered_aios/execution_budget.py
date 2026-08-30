from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Callable

from .audit import hash_value


_IDENTITY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


@dataclass(frozen=True)
class ExecutionBudget:
    budget_id: str
    owner_id: str
    task_id: str
    max_wall_ns: int
    max_cpu_ns: int
    max_ticks: int
    max_work_units: int
    max_recovery_attempts: int

    def __post_init__(self) -> None:
        for name in ("budget_id", "owner_id", "task_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not _IDENTITY.fullmatch(value):
                raise ValueError(f"{name} must be a stable bounded identity")
        for name in (
            "max_wall_ns",
            "max_cpu_ns",
            "max_ticks",
            "max_work_units",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if (
            isinstance(self.max_recovery_attempts, bool)
            or not isinstance(self.max_recovery_attempts, int)
            or not 0 <= self.max_recovery_attempts <= 16
        ):
            raise ValueError("max_recovery_attempts must be between 0 and 16")

    @property
    def max_attempts(self) -> int:
        return self.max_recovery_attempts + 1

    @property
    def contract_sha256(self) -> str:
        return hash_value(self.as_dict())

    def as_dict(self) -> dict[str, Any]:
        return {
            "budget_id": self.budget_id,
            "owner_id": self.owner_id,
            "task_id": self.task_id,
            "max_wall_ns": self.max_wall_ns,
            "max_cpu_ns": self.max_cpu_ns,
            "max_ticks": self.max_ticks,
            "max_work_units": self.max_work_units,
            "max_recovery_attempts": self.max_recovery_attempts,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "ExecutionBudget":
        return cls(
            budget_id=str(value["budget_id"]),
            owner_id=str(value["owner_id"]),
            task_id=str(value["task_id"]),
            max_wall_ns=int(value["max_wall_ns"]),
            max_cpu_ns=int(value["max_cpu_ns"]),
            max_ticks=int(value["max_ticks"]),
            max_work_units=int(value["max_work_units"]),
            max_recovery_attempts=int(value["max_recovery_attempts"]),
        )


@dataclass(frozen=True)
class BudgetSnapshot:
    budget_id: str
    attempt_id: str
    attempt_number: int
    pid: int
    elapsed_wall_ns: int
    elapsed_cpu_ns: int
    process_ticks: int
    work_units: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "budget_id": self.budget_id,
            "attempt_id": self.attempt_id,
            "attempt_number": self.attempt_number,
            "pid": self.pid,
            "elapsed_wall_ns": self.elapsed_wall_ns,
            "elapsed_cpu_ns": self.elapsed_cpu_ns,
            "process_ticks": self.process_ticks,
            "work_units": self.work_units,
        }


class BudgetExceeded(RuntimeError):
    def __init__(self, limit: str, snapshot: BudgetSnapshot) -> None:
        self.limit = limit
        self.snapshot = snapshot
        super().__init__(f"execution budget exceeded: {limit}")


class BudgetGuard:
    """Kernel-owned cooperative meter for one trusted process attempt."""

    def __init__(
        self,
        budget: ExecutionBudget,
        *,
        pid: int,
        attempt_id: str,
        attempt_number: int,
        wall_clock_ns: Callable[[], int],
        cpu_clock_ns: Callable[[], int],
    ) -> None:
        if not _IDENTITY.fullmatch(attempt_id):
            raise ValueError("attempt_id must be a stable bounded identity")
        if not 1 <= attempt_number <= budget.max_attempts:
            raise ValueError("attempt_number is outside the recovery policy")
        self.budget = budget
        self.pid = pid
        self.attempt_id = attempt_id
        self.attempt_number = attempt_number
        self._wall_clock_ns = wall_clock_ns
        self._cpu_clock_ns = cpu_clock_ns
        self._started = False
        self._wall_start = 0
        self._cpu_start = 0
        self._work_units = 0

    @property
    def started(self) -> bool:
        return self._started

    def start(self) -> BudgetSnapshot:
        if not self._started:
            self._wall_start = int(self._wall_clock_ns())
            self._cpu_start = int(self._cpu_clock_ns())
            self._started = True
        return BudgetSnapshot(
            budget_id=self.budget.budget_id,
            attempt_id=self.attempt_id,
            attempt_number=self.attempt_number,
            pid=self.pid,
            elapsed_wall_ns=0,
            elapsed_cpu_ns=0,
            process_ticks=0,
            work_units=self._work_units,
        )

    def checkpoint(self, *, process_ticks: int, work_units: int = 1) -> BudgetSnapshot:
        if isinstance(work_units, bool) or not isinstance(work_units, int) or work_units < 1:
            raise ValueError("checkpoint work_units must be a positive integer")
        if not self._started:
            self.start()
        self._work_units += work_units
        snapshot = self._snapshot(process_ticks=process_ticks)
        if snapshot.elapsed_wall_ns < 0:
            raise BudgetExceeded("wall_clock_regressed", snapshot)
        if snapshot.elapsed_cpu_ns < 0:
            raise BudgetExceeded("cpu_clock_regressed", snapshot)
        if snapshot.elapsed_wall_ns >= self.budget.max_wall_ns:
            raise BudgetExceeded("max_wall_ns", snapshot)
        if snapshot.elapsed_cpu_ns >= self.budget.max_cpu_ns:
            raise BudgetExceeded("max_cpu_ns", snapshot)
        if snapshot.process_ticks > self.budget.max_ticks:
            raise BudgetExceeded("max_ticks", snapshot)
        if snapshot.work_units > self.budget.max_work_units:
            raise BudgetExceeded("max_work_units", snapshot)
        return snapshot

    def _snapshot(self, *, process_ticks: int) -> BudgetSnapshot:
        if self._started:
            wall_now = int(self._wall_clock_ns())
            cpu_now = int(self._cpu_clock_ns())
            elapsed_wall = wall_now - self._wall_start
            elapsed_cpu = cpu_now - self._cpu_start
        else:
            elapsed_wall = 0
            elapsed_cpu = 0
        return BudgetSnapshot(
            budget_id=self.budget.budget_id,
            attempt_id=self.attempt_id,
            attempt_number=self.attempt_number,
            pid=self.pid,
            elapsed_wall_ns=elapsed_wall,
            elapsed_cpu_ns=elapsed_cpu,
            process_ticks=process_ticks,
            work_units=self._work_units,
        )
