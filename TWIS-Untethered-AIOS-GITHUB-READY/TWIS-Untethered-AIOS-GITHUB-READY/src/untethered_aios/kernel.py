from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from typing import Callable, Any
import itertools

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

@dataclass
class ProcessContext:
    kernel: "Kernel"
    process: ProcessRecord

    def call(self, capability: str, **kwargs: Any) -> Any:
        try:
            result = self.kernel.capabilities.invoke(capability, kwargs, self.process.grants)
        except PermissionDenied as exc:
            self.kernel.audit.emit(
                "capability.denied",
                actor=f"pid:{self.process.pid}",
                action=capability,
                detail={"error": str(exc)},
            )
            raise
        self.kernel.audit.emit(
            "capability.call",
            actor=f"pid:{self.process.pid}",
            action=capability,
            detail={"args": sorted(kwargs.keys())},
        )
        return result

    def spawn(
        self,
        name: str,
        runner: Callable[["ProcessContext"], Step],
        grants: tuple[CapabilityGrant, ...] = (),
    ) -> int:
        # Child grants must be a subset of the parent's exact grants.
        parent = set(self.process.grants)
        requested = set(grants)
        if not requested.issubset(parent):
            raise PermissionDenied("child cannot receive capabilities not held by parent")
        return self.kernel.spawn(name, runner, grants=grants, parent_pid=self.process.pid)

class Kernel:
    def __init__(self) -> None:
        self._pids = itertools.count(1)
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
    ) -> int:
        pid = next(self._pids)
        proc = ProcessRecord(
            pid=pid,
            name=name,
            runner=runner,
            grants=grants,
            parent_pid=parent_pid,
            state=ProcessState.READY,
        )
        self.processes[pid] = proc
        self.ready.append(pid)
        self.audit.emit("process.spawn", actor="kernel", action=name, detail={"pid": pid, "parent_pid": parent_pid})
        return pid

    def cancel(self, pid: int) -> None:
        proc = self.processes[pid]
        if proc.state in TERMINAL:
            return
        proc.state = ProcessState.CANCELLED
        proc.waiting_for = None
        self.audit.emit("process.cancel", actor="kernel", action=proc.name, detail={"pid": pid})

    def suspend(self, pid: int) -> None:
        proc = self.processes[pid]
        if proc.state in TERMINAL:
            return
        proc.state = ProcessState.SUSPENDED
        self.audit.emit("process.suspend", actor="kernel", action=proc.name, detail={"pid": pid})

    def resume(self, pid: int) -> None:
        proc = self.processes[pid]
        if proc.state != ProcessState.SUSPENDED:
            return
        proc.state = ProcessState.READY
        self.ready.append(pid)
        self.audit.emit("process.resume", actor="kernel", action=proc.name, detail={"pid": pid})

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
                step = proc.runner(ProcessContext(self, proc))
            except Exception as exc:
                proc.state = ProcessState.FAILED
                proc.error = f"{type(exc).__name__}: {exc}"
                self.audit.emit("process.failed", actor=f"pid:{pid}", action=proc.name, detail={"error": proc.error})
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
                self.audit.emit("process.done", actor=f"pid:{pid}", action=proc.name, detail={"ticks": proc.ticks})
            else:
                proc.state = ProcessState.FAILED
                proc.error = f"invalid step kind: {step.kind}"
                self.audit.emit("process.failed", actor=f"pid:{pid}", action=proc.name, detail={"error": proc.error})

        if ticks >= max_ticks and self.ready:
            self.audit.emit("kernel.tick_limit", actor="kernel", action="run", detail={"max_ticks": max_ticks})
