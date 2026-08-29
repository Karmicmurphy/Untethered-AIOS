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


CheapHandler = Callable[[dict[str, Any]], dict[str, Any]]


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
    ) -> dict[str, Any]:
        if not handler_scope.startswith("handler:"):
            raise ValueError("canonical handler scope is required")
        handler_id = handler_scope.partition(":")[2]
        spec = self.resolve(task_class, handler_id)
        if spec.handler_scope != handler_scope:
            raise ValueError("handler scope does not match resolved handler")
        _, handler = self._handlers[handler_id]
        result = handler(payload)
        self._execution_counts[handler_id] += 1
        return result

    def execution_count(self, handler_id: str) -> int:
        return self._execution_counts.get(handler_id, 0)


def normalize_request(payload: dict[str, Any]) -> dict[str, Any]:
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
    normalized_tags = sorted(
        {
            normalized
            for tag in tags
            if (normalized := tag.strip().lower())
        }
    )
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
        )

    def execute(
        self,
        work_item: WorkItem,
        payload: dict[str, Any],
        *,
        dependency_hashes: dict[str, str] | None = None,
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
                cpu_ns=0,
                wall_ns=0,
                traced_memory_bytes=0,
            )
        return self._execute_handler(
            decision,
            work_item,
            payload,
            dependencies,
            spec,
            computation_id,
            input_hashes,
            reuse.receipt_sha256,
        )

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
    ) -> ExecutionOutcome:
        was_tracing = tracemalloc.is_tracing()
        if not was_tracing:
            tracemalloc.start()
        _, peak_before = tracemalloc.get_traced_memory()
        wall_start = time.perf_counter_ns()
        cpu_start = time.process_time_ns()

        def runner(context):
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
            return Step.done(result)

        pid = self.kernel.spawn(
            f"cheap:{spec.handler_id}",
            runner,
            grants=spec.required_capabilities,
            runner_id=f"cheap-bridge:{spec.handler_id}@{spec.version}",
        )
        self.kernel.run()
        process = self.kernel.get_process(pid)
        if process.state is not ProcessState.DONE:
            raise RuntimeError(
                f"cheap handler process failed: {process.error or process.state.value}"
            )

        cpu_ns = time.process_time_ns() - cpu_start
        wall_ns = time.perf_counter_ns() - wall_start
        _, peak_after = tracemalloc.get_traced_memory()
        traced_memory = max(0, peak_after - peak_before)
        if not was_tracing:
            tracemalloc.stop()

        result = process.result
        result_hash = hash_value(result)
        capability_receipt = next(
            receipt
            for receipt in reversed(self.kernel.audit.receipts)
            if receipt.kind == "capability.call"
            and receipt.pid == pid
            and receipt.action == CHEAP_HANDLER_CAPABILITY
        )
        self.memory.record(
            computation_id=computation_id,
            input_hashes=input_hashes,
            dependency_hashes=dependencies,
            producer=spec.producer_identity,
            result_hash=result_hash,
            result_value=result,
            duration_ms=wall_ns / 1_000_000,
            cpu_ms=cpu_ns / 1_000_000,
            memory_bytes=traced_memory,
            cost_units=spec.expected_cost_units,
            invalidation_rule=spec.invalidation_rule,
            proof_reference=capability_receipt.sha256,
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
                "cpu_ns": cpu_ns,
                "wall_ns": wall_ns,
                "traced_memory_bytes": traced_memory,
            },
            target=computation_id,
            pid=pid,
            parent_pid=process.parent_pid,
        )
        return ExecutionOutcome(
            route=decision.route,
            status=ExecutionStatus.EXECUTED,
            result=result,
            result_hash=result_hash,
            computation_id=computation_id,
            handler_id=spec.handler_id,
            pid=pid,
            decision_receipt_sha256=decision.receipt_sha256,
            receipt_sha256=receipt.sha256,
            cpu_ns=cpu_ns,
            wall_ns=wall_ns,
            traced_memory_bytes=traced_memory,
        )

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
