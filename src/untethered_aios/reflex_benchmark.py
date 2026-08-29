from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import platform
import time
import tracemalloc

from .audit import hash_value
from .cognitive_benchmark import run_benchmark
from .cognitive_contracts import Route, RouteEstimate, WorkItem
from .computation_memory import SQLiteComputationMemory
from .fake_model import FakeModel
from .kernel import Kernel
from .process_table import SQLiteProcessTable
from .reflex_execution import (
    REQUEST_NORMALIZER_HANDLER_ID,
    KernelCheapExecutionBridge,
    build_default_cheap_handler_registry,
)


_FIXED_TIME = "2026-01-01T00:00:00+00:00"


def _cheap_work(identifier: str) -> WorkItem:
    return WorkItem(
        work_item_id=identifier,
        task_class="request.normalize",
        urgency=0.5,
        owner_priority=0.5,
        novelty=0.05,
        uncertainty=0.05,
        risk=0.1,
        expected_benefit=20,
        cpu_budget_ms=100,
        available_memory_mb=128,
        memory_pressure=0.2,
        route_estimates=(
            RouteEstimate(
                route=Route.REFLEX,
                handler_id=REQUEST_NORMALIZER_HANDLER_ID,
                estimated_cost=0.1,
                success_probability=1.0,
                cpu_ms=2,
                memory_mb=2,
                deterministic=True,
            ),
            RouteEstimate(
                route=Route.CENTRAL_AI,
                handler_id="fake-central",
                estimated_cost=12,
                success_probability=0.95,
                cpu_ms=80,
                memory_mb=64,
                deterministic=False,
            ),
        ),
    )


def _central_work() -> WorkItem:
    return WorkItem(
        work_item_id="benchmark-novel",
        task_class="novel",
        urgency=0.8,
        owner_priority=0.8,
        novelty=0.9,
        uncertainty=0.9,
        risk=0.2,
        expected_benefit=60,
        cpu_budget_ms=100,
        available_memory_mb=128,
        memory_pressure=0.2,
        route_estimates=(
            RouteEstimate(
                route=Route.CENTRAL_AI,
                handler_id="fake-central",
                estimated_cost=12,
                success_probability=0.95,
                cpu_ms=80,
                memory_mb=64,
                deterministic=False,
            ),
        ),
    )


def _record_dependency(
    memory: SQLiteComputationMemory,
    identifier: str,
    value: str,
):
    result = {"value": value}
    return memory.record(
        computation_id=identifier,
        input_hashes={"input": hash_value(f"{identifier}-input")},
        dependency_hashes={},
        producer="benchmark-dependency",
        result_hash=hash_value(result),
        result_value=result,
        duration_ms=0.1,
        cpu_ms=0.1,
        memory_bytes=128,
        cost_units=0.1,
        invalidation_rule="stale when result hash changes",
        proof_reference=f"benchmark:{identifier}:{value}",
    )


def run_reflex_execution_benchmark(root: str | Path) -> dict:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    campaign_1 = run_benchmark(root / "campaign-1-computations.sqlite3")
    kernel = Kernel(
        process_table=SQLiteProcessTable(root / "kernel.sqlite3"),
        clock=lambda: _FIXED_TIME,
    )
    memory = SQLiteComputationMemory(
        root / "bridge-computations.sqlite3",
        audit=kernel.audit,
    )
    registry = build_default_cheap_handler_registry()
    model = FakeModel(["synthetic-central-result"])
    bridge = KernelCheapExecutionBridge(
        kernel=kernel,
        memory=memory,
        registry=registry,
        fake_model=model,
    )

    tracemalloc.start()
    wall_start = time.perf_counter_ns()
    cpu_start = time.process_time_ns()
    a1 = _record_dependency(memory, "A", "v1")
    _record_dependency(memory, "U", "stable")
    payload = {
        "title": "  Local Request  ",
        "tags": ["FAST", "local", "fast"],
    }
    work = _cheap_work("benchmark-dependent")
    first = bridge.execute(
        work,
        payload,
        dependency_hashes={"A": a1.result_hash},
    )
    repeat = bridge.execute(
        work,
        payload,
        dependency_hashes={"A": a1.result_hash},
    )
    fake_calls_after_cheap_repeat = len(model.calls)

    a2 = _record_dependency(memory, "A", "v2")
    state_after_change = memory.get(first.computation_id).state.value
    recomputed = bridge.execute(
        work,
        payload,
        dependency_hashes={"A": a2.result_hash},
    )
    unrelated = memory.check_reuse(
        "U",
        input_hashes={"input": hash_value("U-input")},
        dependency_hashes={},
        expected_producer="benchmark-dependency",
        expected_invalidation_rule="stale when result hash changes",
        require_proof=True,
        require_result_value=True,
    )
    fake_calls_after_all_cheap = len(model.calls)
    central = bridge.execute(_central_work(), {"question": "novel"})
    protected = bridge.execute(
        replace(_cheap_work("benchmark-protected"), protected_operation=True),
        {"title": "Protected", "tags": []},
    )

    cpu_ns = time.process_time_ns() - cpu_start
    wall_ns = time.perf_counter_ns() - wall_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    chain_valid, chain_errors = kernel.audit.verify_chain()
    receipts = kernel.audit.as_dicts()
    invalidations = [
        receipt["detail"]
        for receipt in receipts
        if receipt["kind"] == "computation.invalidated"
    ]
    execution_receipts = [
        receipt
        for receipt in receipts
        if receipt["kind"]
        in {
            "computation.executed",
            "computation.reused",
            "execution.central_ai",
            "execution.owner_gate",
        }
    ]
    capability_receipts = [
        receipt
        for receipt in receipts
        if receipt["kind"] == "capability.call"
        and receipt["action"] == "cheap.handler.execute"
    ]
    persisted_receipt_count = len(kernel.process_table.list_receipts())
    database_status = {
        "computation_integrity": memory.integrity_check(),
        "computation_journal_mode": memory.journal_mode(),
        "kernel_integrity": kernel.process_table.integrity_check(),
        "kernel_journal_mode": kernel.process_table.journal_mode(),
    }
    handler_executions = registry.execution_count(
        REQUEST_NORMALIZER_HANDLER_ID
    )
    correctness = {
        "first_run_executed": first.status.value == "EXECUTED",
        "identical_repeat_reused": repeat.status.value == "REUSED",
        "repeat_skipped_handler": handler_executions == 2,
        "cheap_path_zero_fake_calls": fake_calls_after_all_cheap == 0,
        "dependency_change_recomputed": recomputed.status.value == "EXECUTED",
        "affected_work_was_stale": state_after_change == "STALE",
        "unrelated_computation_reused": unrelated.reusable,
        "novel_escalated_to_fake_model": (
            central.route is Route.CENTRAL_AI and len(model.calls) == 1
        ),
        "protected_reached_owner_gate": (
            protected.route is Route.OWNER_GATE
            and protected.result is None
        ),
        "receipt_chain_valid": chain_valid,
    }
    result = {
        "schema": "twis-reflex-execution-benchmark-v0.1",
        "extends": campaign_1["schema"],
        "campaign_1": campaign_1,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "logical_cpu_count": os.cpu_count(),
            "dependencies": "Python standard library and embedded SQLite only",
            "network_calls": 0,
            "provider_calls": 0,
            "model_runtime": "deterministic FakeModel only",
        },
        "execution_cases": {
            "first": {
                "route": first.route.value,
                "status": first.status.value,
                "handler_executed": True,
                "cpu_ns": first.cpu_ns,
                "wall_ns": first.wall_ns,
                "traced_memory_bytes": first.traced_memory_bytes,
                "result_sha256": first.result_hash,
            },
            "identical_repeat": {
                "route": repeat.route.value,
                "status": repeat.status.value,
                "handler_executed": False,
                "cpu_ns": repeat.cpu_ns,
                "wall_ns": repeat.wall_ns,
                "traced_memory_bytes": repeat.traced_memory_bytes,
                "result_sha256": repeat.result_hash,
            },
            "dependency_changed": {
                "route": recomputed.route.value,
                "status": recomputed.status.value,
                "handler_executed": True,
                "state_before_recompute": state_after_change,
                "result_sha256": recomputed.result_hash,
            },
            "unrelated": {
                "computation_id": "U",
                "reusable": unrelated.reusable,
            },
            "novel": {
                "route": central.route.value,
                "status": central.status.value,
                "fake_model_called": True,
            },
            "protected": {
                "route": protected.route.value,
                "status": protected.status.value,
                "handler_executed": False,
                "fake_model_called": False,
            },
        },
        "economy": {
            "handler_executions": handler_executions,
            "reuse_hits": 1,
            "handler_recomputations_avoided": 1,
            "dependency_recomputations": 1,
            "fake_model_calls": len(model.calls),
            "fake_model_calls_avoided": 4,
            "fake_calls_after_cheap_repeat": fake_calls_after_cheap_repeat,
            "fake_calls_after_all_cheap": fake_calls_after_all_cheap,
            "invalidations": invalidations,
        },
        "measurements": {
            "cpu_ns": cpu_ns,
            "wall_ns": wall_ns,
            "peak_traced_memory_bytes": peak_bytes,
        },
        "receipts": {
            "count": len(receipts),
            "persisted_count": persisted_receipt_count,
            "chain_valid": chain_valid,
            "chain_errors": list(chain_errors),
            "head_sha256": receipts[-1]["sha256"],
            "execution_kinds": [
                receipt["kind"] for receipt in execution_receipts
            ],
            "cheap_capability_calls": len(capability_receipts),
            "cheap_capability_target": (
                capability_receipts[0]["target"]
                if capability_receipts
                else None
            ),
        },
        "databases": database_status,
        "correctness": correctness,
    }
    memory.close()
    kernel.close()
    return result
