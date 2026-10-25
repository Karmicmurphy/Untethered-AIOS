from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from typing import Callable, Any
import itertools
from types import MappingProxyType

from .audit import AuditLog
from .capabilities import CapabilityGrant, CapabilityRegistry, PermissionDenied
from .events import Event, EventBus

class ProcessState(str, Enum):
    NEW = "NEW"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    SUSPENDED = "SUSPENDED"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

TERMINAL = {ProcessState.DONE, ProcessState.FAILED, ProcessState.CANCELLED}

def _process_detail(proc: "ProcessRecord", **extra: Any) -> dict[str, Any]:
    detail = dict(extra)
    foundry_job_id = proc.metadata.get("foundry_job_id")
    if isinstance(foundry_job_id, str) and foundry_job_id:
        detail["foundry_job_id"] = foundry_job_id
    return detail

@dataclass
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
    def done(cls, value: Any = None) -> "Step":
        return cls("done", value)

@dataclass
class ProcessRecord:
    pid: int
    name: str
    runner: Callable[["ProcessContext"], Step]
    grants: tuple[CapabilityGrant, ...] = ()
    parent_pid: int | None = None
    state: ProcessState = ProcessState.NEW
    result: Any = None
    error: str | None = None
    waiting_for: str | None = None
    ticks: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass(frozen=True)
class ProcessView:
    pid: int
    name: str
    grants: tuple[CapabilityGrant, ...]
    metadata: Any


@dataclass(frozen=True, slots=True)
class ProcessContext:
    """Restricted cooperative API; Python reflection is NOT a security sandbox."""
    process: ProcessView
    _invoke: Callable
    _spawn: Callable

    def call(self, capability: str, **kwargs: Any) -> Any:
        return self._invoke(capability, kwargs)

    def spawn(self, name, runner, grants=()):
        return self._spawn(name, runner, tuple(grants))


class Kernel:
    def __init__(self) -> None:
        self._pids = itertools.count(1)
        self._admissions = {}
        self.processes: dict[int, ProcessRecord] = {}
        self.ready: deque[int] = deque()
        self.waiting: dict[str, set[int]] = {}
        self.events = EventBus()
        self.capabilities = CapabilityRegistry()
        self.audit = AuditLog()

    def spawn(
        self,
        name: str,
        runner: Callable[[ProcessContext], Step],
        grants: tuple[CapabilityGrant, ...] = (),
        parent_pid: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        pid = next(self._pids)
        proc = ProcessRecord(
            pid=pid,
            name=name,
            runner=runner,
            grants=grants,
            parent_pid=parent_pid,
            state=ProcessState.READY,
            metadata=dict(metadata or {}),
        )
        self._admissions[pid] = tuple(grants)
        self.processes[pid] = proc
        self.ready.append(pid)
        self.audit.emit(
            "process.spawn",
            actor="kernel",
            action=name,
            detail=_process_detail(proc, pid=pid, parent_pid=parent_pid),
        )
        return pid

    def _context(self, proc):
        grants = self._admissions[proc.pid]
        def invoke(name, kwargs):
            try:
                result = self.capabilities.invoke(name, kwargs, grants)
            except PermissionDenied as exc:
                self.audit.emit("capability.denied", actor=f"pid:{proc.pid}", action=name,
                                detail=_process_detail(proc, error=str(exc)))
                raise
            self.audit.emit("capability.call", actor=f"pid:{proc.pid}", action=name,
                            detail=_process_detail(proc, args=sorted(kwargs)))
            return result
        def spawn(name, runner, requested):
            if not set(requested).issubset(set(grants)):
                raise PermissionDenied("child cannot receive capabilities not held by parent")
            return self.spawn(name, runner, grants=requested, parent_pid=proc.pid,
                              metadata=dict(proc.metadata))
        view = ProcessView(proc.pid, proc.name, grants, MappingProxyType(dict(proc.metadata)))
        return ProcessContext(view, invoke, spawn)

    def cancel(self, pid: int) -> None:
        proc = self.processes[pid]
        if proc.state in TERMINAL:
            return
        proc.state = ProcessState.CANCELLED
        proc.waiting_for = None
        self.audit.emit("process.cancel", actor="kernel", action=proc.name, detail=_process_detail(proc, pid=pid))

    def suspend(self, pid: int) -> None:
        proc = self.processes[pid]
        if proc.state in TERMINAL:
            return
        proc.state = ProcessState.SUSPENDED
        self.audit.emit("process.suspend", actor="kernel", action=proc.name, detail=_process_detail(proc, pid=pid))

    def resume(self, pid: int) -> None:
        proc = self.processes[pid]
        if proc.state != ProcessState.SUSPENDED:
            return
        proc.state = ProcessState.READY
        self.ready.append(pid)
        self.audit.emit("process.resume", actor="kernel", action=proc.name, detail=_process_detail(proc, pid=pid))

    def publish(self, event: Event) -> None:
        self.events.publish(event)
        for pid in list(self.waiting.get(event.topic, set())):
            proc = self.processes.get(pid)
            if proc and proc.state == ProcessState.WAITING:
                proc.state = ProcessState.READY
                proc.waiting_for = None
                self.ready.append(pid)
        self.waiting.pop(event.topic, None)
        self.audit.emit("event.publish", actor="kernel", action=event.topic, detail={"payload_keys": sorted(event.payload.keys())})

    def run(self, max_ticks: int = 1000) -> None:
        ticks = 0
        while self.ready and ticks < max_ticks:
            pid = self.ready.popleft()
            proc = self.processes[pid]
            if proc.state != ProcessState.READY:
                continue

            proc.state = ProcessState.RUNNING
            proc.ticks += 1
            ticks += 1

            try:
                step = proc.runner(self._context(proc))
                if not isinstance(step, Step):
                    raise TypeError("worker must return a Step")
            except Exception as exc:
                proc.state = ProcessState.FAILED
                proc.error = f"{type(exc).__name__}: {exc}"
                self.audit.emit("process.failed", actor=f"pid:{pid}", action=proc.name, detail=_process_detail(proc, error=proc.error))
                continue

            if step.kind == "yield":
                proc.state = ProcessState.READY
                self.ready.append(pid)
            elif step.kind == "wait":
                proc.state = ProcessState.WAITING
                proc.waiting_for = str(step.value)
                self.waiting.setdefault(proc.waiting_for, set()).add(pid)
            elif step.kind == "done":
                proc.state = ProcessState.DONE
                proc.result = step.value
                self.audit.emit("process.done", actor=f"pid:{pid}", action=proc.name, detail=_process_detail(proc, ticks=proc.ticks))
            else:
                proc.state = ProcessState.FAILED
                proc.error = f"invalid step kind: {step.kind}"
                self.audit.emit("process.failed", actor=f"pid:{pid}", action=proc.name, detail=_process_detail(proc, error=proc.error))

        if ticks >= max_ticks and self.ready:
            foundry_job_ids = sorted({
                str(self.processes[pid].metadata.get("foundry_job_id"))
                for pid in self.ready
                if self.processes[pid].metadata.get("foundry_job_id")
            })
            self.audit.emit(
                "kernel.tick_limit",
                actor="kernel",
                action="run",
                detail={"max_ticks": max_ticks, "foundry_job_ids": foundry_job_ids},
            )
