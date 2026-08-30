from __future__ import annotations

from collections import deque
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import time
from typing import Any, Callable

from .audit import AuditLog, hash_value
from .capabilities import (
    CapabilityFailed,
    CapabilityGrant,
    CapabilityRegistry,
    CapabilityRequest,
    PermissionDenied,
    grants_are_subset,
)
from .events import Event, EventBus
from .execution_budget import (
    BudgetExceeded,
    BudgetGuard,
    BudgetSnapshot,
    ExecutionBudget,
)
from .process_table import (
    InMemoryProcessTable,
    ProcessRecord,
    ProcessState,
    ProcessTable,
    TERMINAL_STATES,
)


TRANSITIONS: dict[ProcessState, set[ProcessState]] = {
    ProcessState.NEW: {ProcessState.READY, ProcessState.FAILED, ProcessState.CANCELLED},
    ProcessState.READY: {
        ProcessState.RUNNING,
        ProcessState.SUSPENDED,
        ProcessState.FAILED,
        ProcessState.CANCELLED,
    },
    ProcessState.RUNNING: {
        ProcessState.READY,
        ProcessState.WAITING,
        ProcessState.SUSPENDED,
        ProcessState.DONE,
        ProcessState.FAILED,
        ProcessState.CANCELLED,
    },
    ProcessState.WAITING: {
        ProcessState.READY,
        ProcessState.SUSPENDED,
        ProcessState.FAILED,
        ProcessState.CANCELLED,
    },
    ProcessState.SUSPENDED: {
        ProcessState.READY,
        ProcessState.WAITING,
        ProcessState.FAILED,
        ProcessState.CANCELLED,
    },
    ProcessState.DONE: set(),
    ProcessState.FAILED: set(),
    ProcessState.CANCELLED: set(),
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class Step:
    kind: str
    value: Any = None

    @classmethod
    def yield_cpu(cls) -> "Step":
        return cls("yield")

    @classmethod
    def wait(cls, topic: str) -> "Step":
        return cls("wait", topic)

    @classmethod
    def suspend(cls) -> "Step":
        return cls("suspend")

    @classmethod
    def done(cls, value: Any = None) -> "Step":
        return cls("done", value)


Runner = Callable[["ProcessContext"], Step]


@dataclass(frozen=True)
class ProcessContext:
    kernel: "Kernel"
    pid: int

    @property
    def process(self) -> ProcessRecord:
        return self.kernel.get_process(self.pid)

    @property
    def metadata(self) -> dict[str, Any]:
        return deepcopy(self.kernel._record(self.pid).metadata)

    @property
    def event(self) -> dict[str, Any] | None:
        return deepcopy(self.kernel._record(self.pid).last_event)

    def set_metadata(self, key: str, value: Any) -> None:
        self.kernel._set_metadata(self.pid, key, value)

    def checkpoint(self, work_units: int = 1) -> BudgetSnapshot:
        return self.kernel._checkpoint_budget(self.pid, work_units=work_units)

    def invoke(self, request: CapabilityRequest) -> Any:
        proc = self.kernel._record(self.pid)
        if proc.state != ProcessState.RUNNING:
            raise PermissionDenied(
                "capability invocation requires a RUNNING process"
            )
        actor = f"pid:{proc.pid}"
        input_hash = hash_value(request.arguments)
        try:
            outcome = self.kernel.capabilities.invoke_request(
                request,
                proc.grants,
                budget_checkpoint=self.checkpoint,
            )
        except PermissionDenied as exc:
            self.kernel.audit.emit(
                "capability.denied",
                actor=actor,
                action=request.name,
                target=exc.target,
                pid=proc.pid,
                parent_pid=proc.parent_pid,
                detail={
                    "argument_keys": sorted(request.arguments),
                    "input_sha256": input_hash,
                    "error": str(exc),
                },
            )
            raise
        except CapabilityFailed as exc:
            self.kernel.audit.emit(
                "capability.failed",
                actor=actor,
                action=request.name,
                target=exc.target,
                pid=proc.pid,
                parent_pid=proc.parent_pid,
                detail={
                    "argument_keys": sorted(request.arguments),
                    "input_sha256": input_hash,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
            raise
        except Exception as exc:
            self.kernel.audit.emit(
                "capability.failed",
                actor=actor,
                action=request.name,
                pid=proc.pid,
                parent_pid=proc.parent_pid,
                detail={
                    "argument_keys": sorted(request.arguments),
                    "input_sha256": input_hash,
                    "error": f"{type(exc).__name__}: {exc}",
                },
            )
            raise

        self.kernel.audit.emit(
            "capability.mutation" if outcome.mutation else "capability.call",
            actor=actor,
            action=request.name,
            target=outcome.target,
            pid=proc.pid,
            parent_pid=proc.parent_pid,
            detail={
                "argument_keys": sorted(request.arguments),
                "input_sha256": input_hash,
                "output_sha256": hash_value(outcome.value),
                "result_type": type(outcome.value).__name__,
                "mutation": outcome.mutation,
            },
        )
        return outcome.value

    def call(self, capability: str, **kwargs: Any) -> Any:
        return self.invoke(CapabilityRequest(capability, kwargs))

    def spawn(
        self,
        name: str,
        runner: Runner,
        grants: tuple[CapabilityGrant, ...] = (),
        *,
        runner_id: str | None = None,
    ) -> int:
        return self.kernel.spawn(
            name,
            runner,
            grants=grants,
            parent_pid=self.pid,
            runner_id=runner_id,
        )


class Kernel:
    def __init__(
        self,
        *,
        process_table: ProcessTable | None = None,
        clock: Callable[[], str] | None = None,
        wall_clock_ns: Callable[[], int] | None = None,
        cpu_clock_ns: Callable[[], int] | None = None,
    ) -> None:
        self.process_table = process_table or InMemoryProcessTable()
        self._clock = clock or _utc_now
        self._wall_clock_ns = wall_clock_ns or time.perf_counter_ns
        self._cpu_clock_ns = cpu_clock_ns or time.process_time_ns
        self.capabilities = CapabilityRegistry()
        self.events = EventBus()
        self.audit = AuditLog(sink=self.process_table, clock=self._clock)
        self._processes: dict[int, ProcessRecord] = {
            record.pid: record for record in self.process_table.list()
        }
        self._runners: dict[int, Runner] = {}
        self._budget_guards: dict[int, BudgetGuard] = {}
        self.ready: deque[int] = deque()
        self.waiting: dict[str, deque[int]] = {}
        self._restore_budget_guards()
        self._recover_queues()

    @property
    def processes(self) -> dict[int, ProcessRecord]:
        return {pid: record.clone() for pid, record in self._processes.items()}

    def get_process(self, pid: int) -> ProcessRecord:
        return self._record(pid).clone()

    def _record(self, pid: int) -> ProcessRecord:
        if pid not in self._processes:
            raise KeyError(pid)
        return self._processes[pid]

    def _persist(self, proc: ProcessRecord) -> None:
        proc.updated_at = self._clock()
        self.process_table.put(proc)

    def _transition(self, proc: ProcessRecord, target: ProcessState) -> None:
        current = proc.state
        if target not in TRANSITIONS[current]:
            raise RuntimeError(f"invalid process transition: {current.value} -> {target.value}")
        proc.state = target
        self._persist(proc)
        self.audit.emit(
            "process.transition",
            actor="kernel",
            action=proc.name,
            pid=proc.pid,
            parent_pid=proc.parent_pid,
            detail={"from": current.value, "to": target.value},
        )

    def _recover_queues(self) -> None:
        for proc in sorted(self._processes.values(), key=lambda item: item.pid):
            if proc.state == ProcessState.RUNNING:
                self._fail(
                    proc,
                    "KernelRestart: process was RUNNING when persistent state reopened",
                    kind="process.crash_recovered",
                )
            elif proc.state == ProcessState.READY:
                self.ready.append(proc.pid)
            elif proc.state == ProcessState.WAITING and proc.waiting_for:
                self.waiting.setdefault(proc.waiting_for, deque()).append(proc.pid)
            elif (
                proc.state == ProcessState.SUSPENDED
                and proc.suspended_from == ProcessState.WAITING
                and proc.waiting_for
            ):
                self.waiting.setdefault(proc.waiting_for, deque()).append(proc.pid)

    def _restore_budget_guards(self) -> None:
        for proc in self._processes.values():
            value = proc.metadata.get("execution_budget")
            if not isinstance(value, dict) or proc.state in TERMINAL_STATES:
                continue
            budget = ExecutionBudget.from_dict(value)
            attempt_id = str(proc.metadata.get("attempt_id", ""))
            attempt_number = int(proc.metadata.get("attempt_number", 0))
            self._budget_guards[proc.pid] = BudgetGuard(
                budget,
                pid=proc.pid,
                attempt_id=attempt_id,
                attempt_number=attempt_number,
                wall_clock_ns=self._wall_clock_ns,
                cpu_clock_ns=self._cpu_clock_ns,
            )

    @staticmethod
    def _default_runner_id(runner: Runner) -> str:
        return f"{runner.__module__}:{runner.__qualname__}"

    def spawn(
        self,
        name: str,
        runner: Runner,
        grants: tuple[CapabilityGrant, ...] = (),
        parent_pid: int | None = None,
        *,
        runner_id: str | None = None,
        execution_budget: ExecutionBudget | None = None,
        attempt_id: str | None = None,
        attempt_number: int = 1,
    ) -> int:
        if not name.strip():
            raise ValueError("process name is required")
        if parent_pid is not None:
            parent = self._record(parent_pid)
            if parent.state != ProcessState.RUNNING:
                raise PermissionDenied("child spawning requires a RUNNING parent")
            if not self.capabilities.grants_are_subset(grants, parent.grants):
                raise PermissionDenied("child cannot receive capabilities beyond parent grants")

        pid = self.process_table.allocate_pid()
        now = self._clock()
        metadata: dict[str, Any] = {}
        if execution_budget is not None:
            if attempt_id is None:
                raise ValueError("budgeted process requires an attempt_id")
            if not 1 <= attempt_number <= execution_budget.max_attempts:
                raise ValueError("attempt_number is outside the recovery policy")
            metadata = {
                "execution_budget": execution_budget.as_dict(),
                "budget_contract_sha256": execution_budget.contract_sha256,
                "attempt_id": attempt_id,
                "attempt_number": attempt_number,
            }
        proc = ProcessRecord(
            pid=pid,
            name=name,
            runner_id=runner_id or self._default_runner_id(runner),
            grants=tuple(grants),
            parent_pid=parent_pid,
            state=ProcessState.NEW,
            metadata=metadata,
            created_at=now,
            updated_at=now,
        )
        self._processes[pid] = proc
        self.process_table.put(proc)
        self._runners[pid] = runner
        if execution_budget is not None:
            self._budget_guards[pid] = BudgetGuard(
                execution_budget,
                pid=pid,
                attempt_id=attempt_id or "",
                attempt_number=attempt_number,
                wall_clock_ns=self._wall_clock_ns,
                cpu_clock_ns=self._cpu_clock_ns,
            )
        self.audit.emit(
            "process.spawn",
            actor="kernel",
            action=name,
            pid=pid,
            parent_pid=parent_pid,
            detail={
                "runner_id": proc.runner_id,
                "grants": [grant.name for grant in grants],
            },
        )
        self._transition(proc, ProcessState.READY)
        self.ready.append(pid)
        return pid

    def _checkpoint_budget(self, pid: int, *, work_units: int = 1) -> BudgetSnapshot:
        proc = self._record(pid)
        if proc.state != ProcessState.RUNNING:
            raise RuntimeError("budget checkpoint requires a RUNNING process")
        guard = self._budget_guards.get(pid)
        if guard is None:
            raise RuntimeError("process has no execution budget")
        try:
            return guard.checkpoint(
                process_ticks=proc.ticks,
                work_units=work_units,
            )
        except BudgetExceeded as exc:
            self.audit.emit(
                "execution.budget_exceeded",
                actor="kernel",
                action=proc.name,
                target=guard.budget.task_id,
                pid=pid,
                parent_pid=proc.parent_pid,
                detail={
                    **exc.snapshot.as_dict(),
                    "owner_id": guard.budget.owner_id,
                    "limit": exc.limit,
                    "budget_contract_sha256": guard.budget.contract_sha256,
                },
            )
            raise

    def bind_runner(self, pid: int, runner: Runner, *, runner_id: str | None = None) -> None:
        proc = self._record(pid)
        supplied_id = runner_id or self._default_runner_id(runner)
        if supplied_id != proc.runner_id:
            raise ValueError(
                f"runner identity mismatch: expected {proc.runner_id}, got {supplied_id}"
            )
        if proc.state in TERMINAL_STATES:
            raise RuntimeError("terminal process cannot bind a runner")
        self._runners[pid] = runner

    def _set_metadata(self, pid: int, key: str, value: Any) -> None:
        proc = self._record(pid)
        if proc.state != ProcessState.RUNNING:
            raise RuntimeError("process metadata can change only while RUNNING")
        if not key or not isinstance(key, str):
            raise ValueError("metadata key is required")
        updated = deepcopy(proc.metadata)
        updated[key] = value
        proc.metadata = updated
        self._persist(proc)

    def _fail(self, proc: ProcessRecord, error: str, *, kind: str = "process.failed") -> None:
        if proc.state in TERMINAL_STATES:
            return
        proc.error = error
        proc.waiting_for = None
        proc.suspended_from = None
        proc.wake_pending = False
        self._transition(proc, ProcessState.FAILED)
        self.audit.emit(
            kind,
            actor=f"pid:{proc.pid}",
            action=proc.name,
            pid=proc.pid,
            parent_pid=proc.parent_pid,
            detail={"error": error, "ticks": proc.ticks},
        )

    def cancel(self, pid: int) -> None:
        proc = self._record(pid)
        if proc.state in TERMINAL_STATES:
            return
        proc.waiting_for = None
        proc.suspended_from = None
        proc.wake_pending = False
        self._transition(proc, ProcessState.CANCELLED)
        self.audit.emit(
            "process.cancel",
            actor="kernel",
            action=proc.name,
            pid=pid,
            parent_pid=proc.parent_pid,
            detail={"ticks": proc.ticks},
        )

    def suspend(self, pid: int) -> None:
        proc = self._record(pid)
        if proc.state in TERMINAL_STATES or proc.state == ProcessState.SUSPENDED:
            return
        if proc.state not in {ProcessState.READY, ProcessState.WAITING}:
            raise RuntimeError(f"cannot suspend process in {proc.state.value}")
        proc.suspended_from = proc.state
        self._transition(proc, ProcessState.SUSPENDED)
        self.audit.emit(
            "process.suspend",
            actor="kernel",
            action=proc.name,
            pid=pid,
            parent_pid=proc.parent_pid,
            detail={"from": proc.suspended_from.value},
        )

    def resume(self, pid: int) -> None:
        proc = self._record(pid)
        if proc.state != ProcessState.SUSPENDED:
            return
        previous = proc.suspended_from
        if previous == ProcessState.WAITING and not proc.wake_pending:
            target = ProcessState.WAITING
        else:
            target = ProcessState.READY
        proc.suspended_from = None
        proc.wake_pending = False
        self._transition(proc, target)
        if target == ProcessState.READY:
            self.ready.append(pid)
        elif proc.waiting_for:
            queue = self.waiting.setdefault(proc.waiting_for, deque())
            if pid not in queue:
                queue.append(pid)
        self.audit.emit(
            "process.resume",
            actor="kernel",
            action=proc.name,
            pid=pid,
            parent_pid=proc.parent_pid,
            detail={"to": target.value},
        )

    def publish(self, event: Event) -> None:
        if not event.topic.strip():
            raise ValueError("event topic is required")
        self.events.publish(event)
        woken: list[int] = []
        deferred: list[int] = []
        for pid in list(self.waiting.pop(event.topic, deque())):
            proc = self._processes.get(pid)
            if proc is None:
                continue
            event_value = {"topic": event.topic, "payload": deepcopy(event.payload)}
            if proc.state == ProcessState.WAITING:
                proc.last_event = event_value
                proc.waiting_for = None
                self._transition(proc, ProcessState.READY)
                self.ready.append(pid)
                woken.append(pid)
            elif (
                proc.state == ProcessState.SUSPENDED
                and proc.suspended_from == ProcessState.WAITING
                and proc.waiting_for == event.topic
            ):
                proc.last_event = event_value
                proc.waiting_for = None
                proc.wake_pending = True
                self._persist(proc)
                deferred.append(pid)
        self.audit.emit(
            "event.publish",
            actor="kernel",
            action=event.topic,
            detail={
                "payload_keys": sorted(event.payload),
                "woken_pids": woken,
                "suspended_wake_pids": deferred,
            },
        )

    def run(self, max_ticks: int = 1000) -> None:
        if max_ticks < 1:
            raise ValueError("max_ticks must be positive")
        ticks = 0
        while self.ready and ticks < max_ticks:
            pid = self.ready.popleft()
            proc = self._record(pid)
            if proc.state != ProcessState.READY:
                continue

            proc.ticks += 1
            self._transition(proc, ProcessState.RUNNING)
            ticks += 1
            runner = self._runners.get(pid)
            if runner is None:
                self._fail(proc, f"RunnerUnavailable: {proc.runner_id}")
                continue

            try:
                guard = self._budget_guards.get(pid)
                if guard is not None and not guard.started:
                    started = guard.start()
                    self.audit.emit(
                        "execution.started",
                        actor="kernel",
                        action=proc.name,
                        target=guard.budget.task_id,
                        pid=pid,
                        parent_pid=proc.parent_pid,
                        detail={
                            **started.as_dict(),
                            "owner_id": guard.budget.owner_id,
                            "budget_contract_sha256": guard.budget.contract_sha256,
                            "max_attempts": guard.budget.max_attempts,
                        },
                    )
                step = runner(ProcessContext(self, pid))
                if not isinstance(step, Step):
                    raise TypeError("runner must return Step")
                if step.kind == "yield":
                    self._transition(proc, ProcessState.READY)
                    self.ready.append(pid)
                elif step.kind == "wait":
                    topic = str(step.value or "").strip()
                    if not topic:
                        raise ValueError("wait topic is required")
                    proc.waiting_for = topic
                    proc.last_event = None
                    self._transition(proc, ProcessState.WAITING)
                    self.waiting.setdefault(topic, deque()).append(pid)
                elif step.kind == "suspend":
                    proc.suspended_from = ProcessState.RUNNING
                    self._transition(proc, ProcessState.SUSPENDED)
                elif step.kind == "done":
                    proc.result = step.value
                    self._transition(proc, ProcessState.DONE)
                    self.audit.emit(
                        "process.done",
                        actor=f"pid:{pid}",
                        action=proc.name,
                        pid=pid,
                        parent_pid=proc.parent_pid,
                        detail={
                            "ticks": proc.ticks,
                            "result_sha256": hash_value(step.value),
                        },
                    )
                else:
                    raise ValueError(f"invalid step kind: {step.kind}")
            except Exception as exc:
                self._fail(proc, f"{type(exc).__name__}: {exc}")

        if ticks >= max_ticks and self.ready:
            self.audit.emit(
                "kernel.tick_limit",
                actor="kernel",
                action="run",
                detail={"max_ticks": max_ticks, "ready_pids": list(self.ready)},
            )

    def close(self) -> None:
        self.process_table.close()
