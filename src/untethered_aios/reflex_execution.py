from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
import re
import time
import tracemalloc
from typing import Any, Callable

from .attention_governor import AttentionGovernor
from .audit import hash_value
from .capabilities import CapabilityGrant, CapabilityRequest
from .cognitive_contracts import Route, RouteDecision, WorkItem
from .computation_memory import SQLiteComputationMemory
from .fake_model import FakeModel
from .execution_budget import ExecutionBudget
from .kernel import Kernel, Step
from .process_table import ProcessState


CHEAP_HANDLER_CAPABILITY = "cheap.handler.execute"
REQUEST_NORMALIZER_HANDLER_ID = "request-normalizer-v1"
REQUEST_NORMALIZER_SCOPE = f"handler:{REQUEST_NORMALIZER_HANDLER_ID}"
_HANDLER_ID = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ExecutionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    REUSED = "REUSED"
    CENTRAL_AI = "CENTRAL_AI"
    OWNER_GATE = "OWNER_GATE"
    NOT_EXECUTED = "NOT_EXECUTED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    FAILED = "FAILED"
    RECOVERED = "RECOVERED"


@dataclass(frozen=True)
class CheapHandlerSpec:
    handler_id: str
    supported_task_class: str
    required_capabilities: tuple[CapabilityGrant, ...]
    input_contract: dict[str, Any]
    output_contract: dict[str, Any]
    deterministic: bool
    version: str
    dependency_identity: str
    dependency_sha256: str
    expected_cost_units: float
    route: Route
    invalidation_rule: str

    def __post_init__(self) -> None:
        if not _HANDLER_ID.fullmatch(self.handler_id):
            raise ValueError("handler_id must be a stable lowercase identifier")
        if not self.supported_task_class or not self.version:
            raise ValueError("task class and version are required")
        if self.route not in {Route.REFLEX, Route.RULE}:
            raise ValueError("cheap handlers support only REFLEX or RULE")
        if not self.deterministic:
            raise ValueError("Campaign 2 cheap handlers must be deterministic")
        if not _SHA256.fullmatch(self.dependency_sha256):
            raise ValueError("dependency_sha256 must be a SHA-256 digest")
        if self.expected_cost_units < 0:
            raise ValueError("expected cost cannot be negative")
        expected_grant = CapabilityGrant(
            CHEAP_HANDLER_CAPABILITY,
            (self.handler_scope,),
        )
        if self.required_capabilities != (expected_grant,):
            raise ValueError("handler requires one exact Kernel capability grant")

    @property
    def handler_scope(self) -> str:
        return f"handler:{self.handler_id}"

    @property
    def producer_identity(self) -> str:
        return f"cheap-handler:{self.handler_id}@{self.version}"

    @property
    def contract_sha256(self) -> str:
        return hash_value(
            {
                "handler_id": self.handler_id,
                "supported_task_class": self.supported_task_class,
                "required_capabilities": [
                    {"name": grant.name, "scopes": list(grant.scopes)}
                    for grant in self.required_capabilities
                ],
                "input_contract": self.input_contract,
                "output_contract": self.output_contract,
                "deterministic": self.deterministic,
                "version": self.version,
                "dependency_identity": self.dependency_identity,
                "dependency_sha256": self.dependency_sha256,
                "expected_cost_units": self.expected_cost_units,
                "route": self.route.value,
                "invalidation_rule": self.invalidation_rule,
            }
        )


BudgetCheckpoint = Callable[[int], Any]
CheapHandler = Callable[[dict[str, Any], BudgetCheckpoint], dict[str, Any]]


class CheapHandlerRegistry:
    """Descriptor and resolver only; Kernel capability grants remain authority."""

    def __init__(self) -> None:
        self._handlers: dict[str, tuple[CheapHandlerSpec, CheapHandler]] = {}
        self._execution_counts: dict[str, int] = {}

    def register(self, spec: CheapHandlerSpec, handler: CheapHandler) -> None:
        if spec.handler_id in self._handlers:
            raise ValueError(f"handler already registered: {spec.handler_id}")
        if any(
            existing.supported_task_class == spec.supported_task_class
            and existing.route is spec.route
            for existing, _ in self._handlers.values()
        ):
            raise ValueError("task class and route already have a handler")
        self._handlers[spec.handler_id] = (spec, handler)
        self._execution_counts[spec.handler_id] = 0

    def resolve(self, task_class: str, handler_id: str) -> CheapHandlerSpec:
        entry = self._handlers.get(handler_id)
        if entry is None:
            raise KeyError(f"unknown cheap handler: {handler_id}")
        spec = entry[0]
        if spec.supported_task_class != task_class:
            raise KeyError(
                f"handler {handler_id} does not support task class {task_class}"
            )
        return spec

    def specs(self) -> tuple[CheapHandlerSpec, ...]:
        """Return immutable declarations; this conveys no execution authority."""
        return tuple(spec for spec, _ in self._handlers.values())

    def execute(
        self,
        *,
        handler_scope: str,
        task_class: str,
        payload: dict[str, Any],
        budget_checkpoint: BudgetCheckpoint,
    ) -> dict[str, Any]:
        if not handler_scope.startswith("handler:"):
            raise ValueError("canonical handler scope is required")
        handler_id = handler_scope.partition(":")[2]
        spec = self.resolve(task_class, handler_id)
        if spec.handler_scope != handler_scope:
            raise ValueError("handler scope does not match resolved handler")
        _, handler = self._handlers[handler_id]
        result = handler(payload, budget_checkpoint)
        self._execution_counts[handler_id] += 1
        return result

    def execution_count(self, handler_id: str) -> int:
        return self._execution_counts.get(handler_id, 0)


def normalize_request(
    payload: dict[str, Any],
    budget_checkpoint: BudgetCheckpoint,
) -> dict[str, Any]:
    budget_checkpoint(1)
    if not isinstance(payload, dict) or set(payload) != {"title", "tags"}:
        raise ValueError("request normalization requires exactly title and tags")
    title = payload["title"]
    tags = payload["tags"]
    if not isinstance(title, str) or len(title) > 256:
        raise ValueError("title must be a string of at most 256 characters")
    if not isinstance(tags, list) or len(tags) > 32:
        raise ValueError("tags must be a list with at most 32 entries")
    if any(not isinstance(tag, str) or len(tag) > 64 for tag in tags):
        raise ValueError("each tag must be a string of at most 64 characters")
    normalized_values: set[str] = set()
    for tag in tags:
        budget_checkpoint(1)
        normalized = tag.strip().lower()
        if normalized:
            normalized_values.add(normalized)
    normalized_tags = sorted(normalized_values)
    budget_checkpoint(1)
    return {"title": title.strip(), "tags": normalized_tags}


def build_default_cheap_handler_registry() -> CheapHandlerRegistry:
    registry = CheapHandlerRegistry()
    dependency_identity = "python-stdlib:string-strip-lower-sort"
    dependency_sha256 = hash_value(
        {
            "identity": dependency_identity,
            "algorithm": "trim title; trim/lower/deduplicate/sort tags",
            "version": "1.0.0",
        }
    )
    spec = CheapHandlerSpec(
        handler_id=REQUEST_NORMALIZER_HANDLER_ID,
        supported_task_class="request.normalize",
        required_capabilities=(
            CapabilityGrant(
                CHEAP_HANDLER_CAPABILITY,
                (REQUEST_NORMALIZER_SCOPE,),
            ),
        ),
        input_contract={
            "type": "object",
            "required": ["title", "tags"],
            "additionalProperties": False,
        },
        output_contract={
            "type": "object",
            "required": ["title", "tags"],
            "additionalProperties": False,
        },
        deterministic=True,
        version="1.0.0",
        dependency_identity=dependency_identity,
        dependency_sha256=dependency_sha256,
        expected_cost_units=0.1,
        route=Route.REFLEX,
        invalidation_rule=(
            "reuse only when handler identity/version/contract, inputs, "
            "dependency results, proof, and stored result hash remain valid"
        ),
    )
    registry.register(spec, normalize_request)
    return registry


@dataclass(frozen=True)
class ExecutionOutcome:
    route: Route
    status: ExecutionStatus
    result: Any
    result_hash: str | None
    computation_id: str | None
    handler_id: str | None
    pid: int | None
    decision_receipt_sha256: str
    receipt_sha256: str
    cpu_ns: int
    wall_ns: int
    traced_memory_bytes: int
    attempt_count: int = 0
    pids: tuple[int, ...] = ()
    budget_id: str | None = None
    failure_kind: str | None = None


class KernelCheapExecutionBridge:
    def __init__(
        self,
        *,
        kernel: Kernel,
        memory: SQLiteComputationMemory,
        registry: CheapHandlerRegistry,
        fake_model: FakeModel,
    ) -> None:
        if memory.audit is not kernel.audit:
            raise ValueError(
                "Kernel and Computation Memory must share one receipt chain"
            )
        self.kernel = kernel
        self.memory = memory
        self.registry = registry
        self.fake_model = fake_model
        self.governor = AttentionGovernor(audit=kernel.audit)
        self.kernel.capabilities.register(
            CHEAP_HANDLER_CAPABILITY,
            self.registry.execute,
            scope_arg="handler_scope",
            scope_kind="resource",
            allow_wildcard_scope=False,
            mutation=False,
            inject_budget_checkpoint=True,
        )

    def execute(
        self,
        work_item: WorkItem,
        payload: dict[str, Any],
        *,
        dependency_hashes: dict[str, str] | None = None,
        budget: ExecutionBudget | None = None,
        auto_recover: bool = True,
    ) -> ExecutionOutcome:
        dependencies = dict(dependency_hashes or {})
        decision = self.governor.decide(work_item)
        if decision.route is Route.CENTRAL_AI:
            return self._central_ai(decision, payload)
        if decision.route is Route.OWNER_GATE:
            return self._owner_gate(decision)
        if decision.route not in {Route.REFLEX, Route.RULE}:
            receipt = self.kernel.audit.emit(
                "execution.not_executed",
                "kernel-execution-bridge",
                decision.route.value,
                {
                    "decision_receipt_sha256": decision.receipt_sha256,
                    "handler_executed": False,
                    "fake_model_called": False,
                },
                target=work_item.work_item_id,
            )
            return ExecutionOutcome(
                route=decision.route,
                status=ExecutionStatus.NOT_EXECUTED,
                result=None,
                result_hash=None,
                computation_id=None,
                handler_id=None,
                pid=None,
                decision_receipt_sha256=decision.receipt_sha256,
                receipt_sha256=receipt.sha256,
                cpu_ns=0,
                wall_ns=0,
                traced_memory_bytes=0,
            )

        spec = self.registry.resolve(
            work_item.task_class,
            decision.selected_handler or "",
        )
        if spec.route is not decision.route:
            raise ValueError("Governor route does not match handler contract")
        computation_id = (
            f"cheap:{spec.handler_id}:{work_item.work_item_id}"
        )
        input_hashes = {
            "handler_contract": spec.contract_sha256,
            "payload": hash_value(payload),
            "work_item": work_item.input_sha256,
        }
        current_budget = budget or self._default_budget(work_item)
        self._validate_budget(current_budget, work_item)
        was_tracing = tracemalloc.is_tracing()
        if not was_tracing:
            tracemalloc.start()
        _, reuse_peak_before = tracemalloc.get_traced_memory()
        reuse_wall_start = time.perf_counter_ns()
        reuse_cpu_start = time.process_time_ns()
        reuse = self.memory.check_reuse(
            computation_id,
            input_hashes=input_hashes,
            dependency_hashes=dependencies,
            expected_producer=spec.producer_identity,
            expected_invalidation_rule=spec.invalidation_rule,
            require_proof=True,
            require_result_value=True,
        )
        if reuse.reusable:
            record = self.memory.get(computation_id)
            assert record is not None
            receipt = self.kernel.audit.emit(
                "computation.reused",
                "kernel-execution-bridge",
                spec.handler_id,
                {
                    "handler_id": spec.handler_id,
                    "handler_version": spec.version,
                    "handler_executed": False,
                    "fake_model_called": False,
                    "result_sha256": record.result_hash,
                    "proof_reference": record.proof_reference,
                    "decision_receipt_sha256": decision.receipt_sha256,
                    "reuse_check_receipt_sha256": reuse.receipt_sha256,
                    "dependency_hashes": dependencies,
                },
                target=computation_id,
            )
            reuse_cpu_ns = time.process_time_ns() - reuse_cpu_start
            reuse_wall_ns = time.perf_counter_ns() - reuse_wall_start
            _, reuse_peak_after = tracemalloc.get_traced_memory()
            reuse_traced_memory = max(0, reuse_peak_after - reuse_peak_before)
            if not was_tracing:
                tracemalloc.stop()
            return ExecutionOutcome(
                route=decision.route,
                status=ExecutionStatus.REUSED,
                result=record.result_value,
                result_hash=record.result_hash,
                computation_id=computation_id,
                handler_id=spec.handler_id,
                pid=None,
                decision_receipt_sha256=decision.receipt_sha256,
                receipt_sha256=receipt.sha256,
                cpu_ns=reuse_cpu_ns,
                wall_ns=reuse_wall_ns,
                traced_memory_bytes=reuse_traced_memory,
                budget_id=current_budget.budget_id,
            )
        if not was_tracing:
            tracemalloc.stop()
        history = self._failure_history(
            current_budget,
            computation_id,
            spec,
            input_hashes,
        )
        if history:
            raise ValueError("prior failed budget requires recover()")
        return self._execute_handler(
            decision,
            work_item,
            payload,
            dependencies,
            spec,
            computation_id,
            input_hashes,
            reuse.receipt_sha256,
            current_budget,
            history=(),
            auto_recover=auto_recover,
        )

    def recover(
        self,
        work_item: WorkItem,
        payload: dict[str, Any],
        *,
        budget: ExecutionBudget,
        dependency_hashes: dict[str, str] | None = None,
    ) -> ExecutionOutcome:
        dependencies = dict(dependency_hashes or {})
        decision = self.governor.decide(work_item)
        if decision.route is Route.OWNER_GATE:
            return self._owner_gate(decision)
        if decision.route not in {Route.REFLEX, Route.RULE}:
            raise ValueError("only a cheap REFLEX/RULE failure can be recovered")
        spec = self.registry.resolve(
            work_item.task_class,
            decision.selected_handler or "",
        )
        if spec.route is not decision.route:
            raise ValueError("Governor route does not match handler contract")
        self._validate_budget(budget, work_item)
        computation_id = f"cheap:{spec.handler_id}:{work_item.work_item_id}"
        input_hashes = {
            "handler_contract": spec.contract_sha256,
            "payload": hash_value(payload),
            "work_item": work_item.input_sha256,
        }
        reuse = self.memory.check_reuse(
            computation_id,
            input_hashes=input_hashes,
            dependency_hashes=dependencies,
            expected_producer=spec.producer_identity,
            expected_invalidation_rule=spec.invalidation_rule,
            require_proof=True,
            require_result_value=True,
        )
        if reuse.reusable:
            raise ValueError("successful computation does not require recovery")
        history = self._failure_history(
            budget,
            computation_id,
            spec,
            input_hashes,
        )
        if not history:
            raise ValueError("no persistent failed attempt exists for this budget")
        if len(history) >= budget.max_attempts:
            raise ValueError("recovery attempt limit is already exhausted")
        return self._execute_handler(
            decision,
            work_item,
            payload,
            dependencies,
            spec,
            computation_id,
            input_hashes,
            reuse.receipt_sha256,
            budget,
            history=history,
            auto_recover=True,
        )

    @staticmethod
    def _default_budget(work_item: WorkItem) -> ExecutionBudget:
        identity = hash_value(
            {"owner": "kernel", "task_id": work_item.work_item_id}
        )[:24]
        return ExecutionBudget(
            budget_id=f"budget-{identity}",
            owner_id="kernel",
            task_id=work_item.work_item_id,
            max_wall_ns=10_000_000_000,
            max_cpu_ns=10_000_000_000,
            max_ticks=1,
            max_work_units=64,
            max_recovery_attempts=0,
        )

    @staticmethod
    def _validate_budget(budget: ExecutionBudget, work_item: WorkItem) -> None:
        if budget.task_id != work_item.work_item_id:
            raise ValueError("execution budget task identity does not match WorkItem")

    @staticmethod
    def _grant_sha256(spec: CheapHandlerSpec) -> str:
        return hash_value(
            [
                {"name": grant.name, "scopes": list(grant.scopes)}
                for grant in spec.required_capabilities
            ]
        )

    def _failure_history(
        self,
        budget: ExecutionBudget,
        computation_id: str,
        spec: CheapHandlerSpec,
        input_hashes: dict[str, str],
    ) -> tuple[Any, ...]:
        execution_input_sha256 = hash_value(input_hashes)
        input_history = tuple(
            receipt
            for receipt in self.kernel.audit.receipts
            if receipt.kind == "execution.failed"
            and receipt.target == computation_id
            and receipt.detail.get("execution_input_sha256")
            == execution_input_sha256
        )
        if any(
            receipt.detail.get("budget_id") != budget.budget_id
            for receipt in input_history
        ):
            raise ValueError("budget identity changed for prior failed inputs")
        history = tuple(
            receipt
            for receipt in input_history
            if receipt.detail.get("budget_id") == budget.budget_id
        )
        expected_attempts = list(range(1, len(history) + 1))
        actual_attempts = [
            int(receipt.detail.get("attempt_number", 0)) for receipt in history
        ]
        if actual_attempts != expected_attempts:
            raise ValueError("persistent recovery attempt sequence is invalid")
        for receipt in history:
            detail = receipt.detail
            if detail.get("budget_contract_sha256") != budget.contract_sha256:
                raise ValueError("recovery budget contract changed")
            if detail.get("handler_id") != spec.handler_id:
                raise ValueError("recovery handler identity changed")
            if detail.get("handler_version") != spec.version:
                raise ValueError("recovery handler version changed")
            if detail.get("handler_contract_sha256") != spec.contract_sha256:
                raise ValueError("recovery handler contract changed")
            if detail.get("grant_sha256") != self._grant_sha256(spec):
                raise ValueError("recovery capability authority changed")
        return history

    def _execute_handler(
        self,
        decision: RouteDecision,
        work_item: WorkItem,
        payload: dict[str, Any],
        dependencies: dict[str, str],
        spec: CheapHandlerSpec,
        computation_id: str,
        input_hashes: dict[str, str],
        reuse_receipt_sha256: str,
        budget: ExecutionBudget,
        *,
        history: tuple[Any, ...],
        auto_recover: bool,
    ) -> ExecutionOutcome:
        previous_failure_sha256 = history[-1].sha256 if history else None
        pids = [int(receipt.pid) for receipt in history if receipt.pid is not None]
        total_cpu_ns = 0
        total_wall_ns = 0
        peak_memory = 0
        starting_attempt = len(history) + 1
        final_attempt = budget.max_attempts if auto_recover else starting_attempt
        for attempt_number in range(starting_attempt, final_attempt + 1):
            attempt_id = "attempt-" + hash_value(
                {
                    "budget_id": budget.budget_id,
                    "execution_input_sha256": hash_value(input_hashes),
                    "attempt": attempt_number,
                }
            )[:24]
            if attempt_number > 1:
                self.kernel.audit.emit(
                    "execution.recovery_started",
                    "kernel-execution-bridge",
                    spec.handler_id,
                    {
                        "budget_id": budget.budget_id,
                        "budget_contract_sha256": budget.contract_sha256,
                        "attempt_id": attempt_id,
                        "attempt_number": attempt_number,
                        "previous_failure_receipt_sha256": previous_failure_sha256,
                        "handler_id": spec.handler_id,
                        "handler_version": spec.version,
                        "handler_contract_sha256": spec.contract_sha256,
                        "grant_sha256": self._grant_sha256(spec),
                        "execution_input_sha256": hash_value(input_hashes),
                    },
                    target=computation_id,
                )
            attempt = self._run_attempt(
                work_item,
                payload,
                spec,
                budget,
                attempt_id,
                attempt_number,
            )
            pid = attempt["pid"]
            process = attempt["process"]
            pids.append(pid)
            total_cpu_ns += attempt["cpu_ns"]
            total_wall_ns += attempt["wall_ns"]
            peak_memory = max(peak_memory, attempt["traced_memory_bytes"])
            if process.state is ProcessState.DONE:
                result = process.result
                result_hash = hash_value(result)
                capability_receipt = attempt["capability_receipt"]
                status = ExecutionStatus.EXECUTED
                proof_reference = capability_receipt.sha256
                if attempt_number > 1:
                    recovered = self.kernel.audit.emit(
                        "execution.recovered",
                        "kernel-execution-bridge",
                        spec.handler_id,
                        {
                            "budget_id": budget.budget_id,
                            "budget_contract_sha256": budget.contract_sha256,
                            "attempt_id": attempt_id,
                            "attempt_number": attempt_number,
                            "previous_failure_receipt_sha256": previous_failure_sha256,
                            "result_sha256": result_hash,
                            "handler_id": spec.handler_id,
                            "handler_version": spec.version,
                            "handler_contract_sha256": spec.contract_sha256,
                            "grant_sha256": self._grant_sha256(spec),
                            "execution_input_sha256": hash_value(input_hashes),
                        },
                        target=computation_id,
                        pid=pid,
                        parent_pid=process.parent_pid,
                    )
                    proof_reference = recovered.sha256
                    status = ExecutionStatus.RECOVERED
                self.memory.record(
                    computation_id=computation_id,
                    input_hashes=input_hashes,
                    dependency_hashes=dependencies,
                    producer=spec.producer_identity,
                    result_hash=result_hash,
                    result_value=result,
                    duration_ms=total_wall_ns / 1_000_000,
                    cpu_ms=total_cpu_ns / 1_000_000,
                    memory_bytes=peak_memory,
                    cost_units=spec.expected_cost_units * attempt_number,
                    invalidation_rule=spec.invalidation_rule,
                    proof_reference=proof_reference,
                )
                receipt = self.kernel.audit.emit(
                    "computation.executed",
                    "kernel-execution-bridge",
                    spec.handler_id,
                    {
                        "handler_id": spec.handler_id,
                        "handler_version": spec.version,
                        "handler_executed": True,
                        "fake_model_called": False,
                        "result_sha256": result_hash,
                        "decision_receipt_sha256": decision.receipt_sha256,
                        "reuse_check_receipt_sha256": reuse_receipt_sha256,
                        "capability_receipt_sha256": capability_receipt.sha256,
                        "dependency_hashes": dependencies,
                        "budget_id": budget.budget_id,
                        "budget_contract_sha256": budget.contract_sha256,
                        "attempt_count": attempt_number,
                        "pids": pids,
                        "cpu_ns": total_cpu_ns,
                        "wall_ns": total_wall_ns,
                        "traced_memory_bytes": peak_memory,
                    },
                    target=computation_id,
                    pid=pid,
                    parent_pid=process.parent_pid,
                )
                return ExecutionOutcome(
                    route=decision.route,
                    status=status,
                    result=result,
                    result_hash=result_hash,
                    computation_id=computation_id,
                    handler_id=spec.handler_id,
                    pid=pid,
                    decision_receipt_sha256=decision.receipt_sha256,
                    receipt_sha256=receipt.sha256,
                    cpu_ns=total_cpu_ns,
                    wall_ns=total_wall_ns,
                    traced_memory_bytes=peak_memory,
                    attempt_count=attempt_number,
                    pids=tuple(pids),
                    budget_id=budget.budget_id,
                )
            budget_exceeded = any(
                receipt.kind == "execution.budget_exceeded" and receipt.pid == pid
                for receipt in self.kernel.audit.receipts
            )
            failure_kind = "budget_exceeded" if budget_exceeded else "handler_failed"
            failed = self.kernel.audit.emit(
                "execution.failed",
                "kernel-execution-bridge",
                spec.handler_id,
                {
                    "budget_id": budget.budget_id,
                    "budget_contract_sha256": budget.contract_sha256,
                    "attempt_id": attempt_id,
                    "attempt_number": attempt_number,
                    "failure_kind": failure_kind,
                    "process_state": process.state.value,
                    "error": process.error,
                    "handler_id": spec.handler_id,
                    "handler_version": spec.version,
                    "handler_contract_sha256": spec.contract_sha256,
                    "grant_sha256": self._grant_sha256(spec),
                    "execution_input_sha256": hash_value(input_hashes),
                    "successful_result_published": False,
                },
                target=computation_id,
                pid=pid,
                parent_pid=process.parent_pid,
            )
            previous_failure_sha256 = failed.sha256
            if attempt_number == final_attempt:
                return ExecutionOutcome(
                    route=decision.route,
                    status=(
                        ExecutionStatus.BUDGET_EXCEEDED
                        if budget_exceeded
                        else ExecutionStatus.FAILED
                    ),
                    result=None,
                    result_hash=None,
                    computation_id=computation_id,
                    handler_id=spec.handler_id,
                    pid=pid,
                    decision_receipt_sha256=decision.receipt_sha256,
                    receipt_sha256=failed.sha256,
                    cpu_ns=total_cpu_ns,
                    wall_ns=total_wall_ns,
                    traced_memory_bytes=peak_memory,
                    attempt_count=attempt_number,
                    pids=tuple(pids),
                    budget_id=budget.budget_id,
                    failure_kind=failure_kind,
                )
        raise RuntimeError("execution attempt loop ended without an outcome")

    def _run_attempt(
        self,
        work_item: WorkItem,
        payload: dict[str, Any],
        spec: CheapHandlerSpec,
        budget: ExecutionBudget,
        attempt_id: str,
        attempt_number: int,
    ) -> dict[str, Any]:
        was_tracing = tracemalloc.is_tracing()
        if not was_tracing:
            tracemalloc.start()
        _, peak_before = tracemalloc.get_traced_memory()
        wall_start = time.perf_counter_ns()
        cpu_start = time.process_time_ns()

        def runner(context):
            context.checkpoint(1)
            result = context.invoke(
                CapabilityRequest(
                    CHEAP_HANDLER_CAPABILITY,
                    {
                        "handler_scope": spec.handler_scope,
                        "task_class": work_item.task_class,
                        "payload": payload,
                    },
                )
            )
            context.checkpoint(1)
            return Step.done(result)

        pid = self.kernel.spawn(
            f"cheap:{spec.handler_id}",
            runner,
            grants=spec.required_capabilities,
            runner_id=f"cheap-bridge:{spec.handler_id}@{spec.version}",
            execution_budget=budget,
            attempt_id=attempt_id,
            attempt_number=attempt_number,
        )
        self.kernel.run()
        process = self.kernel.get_process(pid)
        cpu_ns = time.process_time_ns() - cpu_start
        wall_ns = time.perf_counter_ns() - wall_start
        _, peak_after = tracemalloc.get_traced_memory()
        traced_memory = max(0, peak_after - peak_before)
        if not was_tracing:
            tracemalloc.stop()
        capability_receipt = None
        if process.state is ProcessState.DONE:
            capability_receipt = next(
                receipt
                for receipt in reversed(self.kernel.audit.receipts)
                if receipt.kind == "capability.call"
                and receipt.pid == pid
                and receipt.action == CHEAP_HANDLER_CAPABILITY
            )
        return {
            "pid": pid,
            "process": process,
            "cpu_ns": cpu_ns,
            "wall_ns": wall_ns,
            "traced_memory_bytes": traced_memory,
            "capability_receipt": capability_receipt,
        }

    def _central_ai(
        self,
        decision: RouteDecision,
        payload: dict[str, Any],
    ) -> ExecutionOutcome:
        prompt = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        wall_start = time.perf_counter_ns()
        cpu_start = time.process_time_ns()
        result = self.fake_model.infer(prompt)
        cpu_ns = time.process_time_ns() - cpu_start
        wall_ns = time.perf_counter_ns() - wall_start
        result_hash = hash_value(result)
        receipt = self.kernel.audit.emit(
            "execution.central_ai",
            "kernel-execution-bridge",
            "FakeModel",
            {
                "decision_receipt_sha256": decision.receipt_sha256,
                "prompt_sha256": hash_value(prompt),
                "result_sha256": result_hash,
                "handler_executed": False,
                "fake_model_called": True,
                "cpu_ns": cpu_ns,
                "wall_ns": wall_ns,
            },
            target=decision.work_item_id,
        )
        return ExecutionOutcome(
            route=decision.route,
            status=ExecutionStatus.CENTRAL_AI,
            result=result,
            result_hash=result_hash,
            computation_id=None,
            handler_id=None,
            pid=None,
            decision_receipt_sha256=decision.receipt_sha256,
            receipt_sha256=receipt.sha256,
            cpu_ns=cpu_ns,
            wall_ns=wall_ns,
            traced_memory_bytes=0,
        )

    def _owner_gate(self, decision: RouteDecision) -> ExecutionOutcome:
        receipt = self.kernel.audit.emit(
            "execution.owner_gate",
            "kernel-execution-bridge",
            Route.OWNER_GATE.value,
            {
                "decision_receipt_sha256": decision.receipt_sha256,
                "handler_executed": False,
                "fake_model_called": False,
            },
            target=decision.work_item_id,
        )
        return ExecutionOutcome(
            route=decision.route,
            status=ExecutionStatus.OWNER_GATE,
            result=None,
            result_hash=None,
            computation_id=None,
            handler_id=None,
            pid=None,
            decision_receipt_sha256=decision.receipt_sha256,
            receipt_sha256=receipt.sha256,
            cpu_ns=0,
            wall_ns=0,
            traced_memory_bytes=0,
        )
