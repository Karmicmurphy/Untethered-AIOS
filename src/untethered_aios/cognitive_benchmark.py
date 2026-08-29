from __future__ import annotations

from dataclasses import asdict
import os
from pathlib import Path
import platform
import time
import tracemalloc

from .attention_governor import AttentionGovernor
from .audit import AuditLog, hash_value
from .cognitive_contracts import Route, RouteEstimate, WorkItem
from .computation_memory import ComputationState, SQLiteComputationMemory
from .fake_model import FakeModel


_FIXED_TIME = "2026-01-01T00:00:00+00:00"


def _estimate(
    route: Route,
    cost: float,
    probability: float,
    *,
    cpu_ms: int,
    memory_mb: float,
    deterministic: bool,
) -> RouteEstimate:
    return RouteEstimate(
        route=route,
        handler_id=f"benchmark-{route.value.lower()}",
        estimated_cost=cost,
        success_probability=probability,
        cpu_ms=cpu_ms,
        memory_mb=memory_mb,
        deterministic=deterministic,
    )


def benchmark_work_items() -> tuple[tuple[WorkItem, Route], ...]:
    reflex = _estimate(
        Route.REFLEX, 1, 1, cpu_ms=2, memory_mb=2, deterministic=True
    )
    rule = _estimate(
        Route.RULE, 2, 0.95, cpu_ms=5, memory_mb=4, deterministic=True
    )
    worker = _estimate(
        Route.WORKER, 8, 0.8, cpu_ms=30, memory_mb=24, deterministic=True
    )
    central = _estimate(
        Route.CENTRAL_AI,
        12,
        0.95,
        cpu_ms=80,
        memory_mb=64,
        deterministic=False,
    )
    common = {
        "urgency": 0.5,
        "owner_priority": 0.5,
        "risk": 0.1,
        "cpu_budget_ms": 100,
        "available_memory_mb": 128,
        "memory_pressure": 0.2,
    }
    return (
        (
            WorkItem(
                work_item_id="cheap-deterministic",
                task_class="cheap",
                novelty=0.05,
                uncertainty=0.05,
                expected_benefit=20,
                route_estimates=(reflex, central),
                **common,
            ),
            Route.REFLEX,
        ),
        (
            WorkItem(
                work_item_id="repeated-familiar",
                task_class="repeated",
                novelty=0.3,
                uncertainty=0.2,
                expected_benefit=20,
                route_estimates=(reflex, rule, central),
                **common,
            ),
            Route.RULE,
        ),
        (
            WorkItem(
                work_item_id="novel-ambiguous",
                task_class="novel",
                novelty=0.95,
                uncertainty=0.9,
                expected_benefit=60,
                route_estimates=(worker, central),
                **common,
            ),
            Route.CENTRAL_AI,
        ),
        (
            WorkItem(
                work_item_id="protected-operation",
                task_class="protected",
                novelty=0.1,
                uncertainty=0.1,
                expected_benefit=100,
                protected_operation=True,
                route_estimates=(reflex, worker, central),
                **common,
            ),
            Route.OWNER_GATE,
        ),
        (
            WorkItem(
                work_item_id="low-value",
                task_class="low-value",
                novelty=0.1,
                uncertainty=0.1,
                urgency=0.1,
                owner_priority=0.1,
                risk=0.1,
                expected_benefit=0.5,
                cpu_budget_ms=100,
                available_memory_mb=128,
                memory_pressure=0.2,
                route_estimates=(reflex,),
            ),
            Route.IGNORE,
        ),
        (
            WorkItem(
                work_item_id="high-value-uncertain",
                task_class="high-value",
                novelty=0.7,
                uncertainty=0.8,
                expected_benefit=80,
                route_estimates=(worker, central),
                **common,
            ),
            Route.CENTRAL_AI,
        ),
        (
            WorkItem(
                work_item_id="dependency-reuse",
                task_class="dependency-reuse",
                novelty=0.3,
                uncertainty=0.2,
                expected_benefit=30,
                route_estimates=(rule, worker),
                **common,
            ),
            Route.RULE,
        ),
        (
            WorkItem(
                work_item_id="changed-dependency",
                task_class="dependency-change",
                novelty=0.6,
                uncertainty=0.3,
                expected_benefit=35,
                route_estimates=(rule, worker),
                **common,
            ),
            Route.WORKER,
        ),
        (
            WorkItem(
                work_item_id="memory-pressure",
                task_class="resource-pressure",
                novelty=0.8,
                uncertainty=0.8,
                expected_benefit=40,
                memory_pressure=0.95,
                route_estimates=(worker, central),
                **{key: value for key, value in common.items() if key != "memory_pressure"},
            ),
            Route.DEFER,
        ),
    )


def run_benchmark(database_path: str | Path) -> dict:
    audit = AuditLog(clock=lambda: _FIXED_TIME)
    governor = AttentionGovernor(audit=audit)
    model = FakeModel(["synthetic-central-result"])
    tracemalloc.start()
    wall_start = time.perf_counter_ns()
    cpu_start = time.process_time_ns()

    routes = []
    expected = {}
    central_available = 0
    worker_calls = 0
    for work_item, expected_route in benchmark_work_items():
        decision = governor.decide(work_item)
        expected[work_item.work_item_id] = expected_route.value
        central_available += any(
            estimate.route is Route.CENTRAL_AI
            for estimate in work_item.route_estimates
        )
        if decision.route is Route.CENTRAL_AI:
            model.infer(work_item.work_item_id)
        if decision.route is Route.WORKER:
            worker_calls += 1
        routes.append(
            {
                "work_item_id": work_item.work_item_id,
                "task_class": work_item.task_class,
                "route": decision.route.value,
                "expected_route": expected_route.value,
                "correct": decision.route is expected_route,
                "reason_code": decision.reason_code,
                "receipt_sha256": decision.receipt_sha256,
            }
        )

    input_hash = lambda identifier: {"input": hash_value(f"{identifier}-input")}
    with SQLiteComputationMemory(database_path, audit=audit) as memory:
        a = memory.record(
            computation_id="A",
            input_hashes=input_hash("A"),
            dependency_hashes={},
            producer="benchmark",
            result_hash=hash_value("A:v1"),
            duration_ms=0.2,
            cpu_ms=0.1,
            memory_bytes=256,
            cost_units=0.1,
            invalidation_rule="stale dependents when result hash changes",
            proof_reference="benchmark:A:v1",
        )
        b = memory.record(
            computation_id="B",
            input_hashes=input_hash("B"),
            dependency_hashes={"A": a.result_hash},
            producer="benchmark",
            result_hash=hash_value("B:v1"),
            duration_ms=0.3,
            cpu_ms=0.2,
            memory_bytes=384,
            cost_units=0.2,
            invalidation_rule="stale when A result hash changes",
            proof_reference="benchmark:B:v1",
        )
        memory.record(
            computation_id="C",
            input_hashes=input_hash("C"),
            dependency_hashes={"B": b.result_hash},
            producer="benchmark",
            result_hash=hash_value("C:v1"),
            duration_ms=0.4,
            cpu_ms=0.3,
            memory_bytes=512,
            cost_units=0.3,
            invalidation_rule="stale when B result hash changes",
            proof_reference="benchmark:C:v1",
        )
        memory.record(
            computation_id="D",
            input_hashes=input_hash("D"),
            dependency_hashes={},
            producer="benchmark",
            result_hash=hash_value("D:v1"),
            duration_ms=0.1,
            cpu_ms=0.1,
            memory_bytes=128,
            cost_units=0.1,
            invalidation_rule="stale only when D inputs change",
            proof_reference="benchmark:D:v1",
        )
        reuse_before = memory.check_reuse(
            "C",
            input_hashes=input_hash("C"),
            dependency_hashes={"B": b.result_hash},
        )
        a2 = memory.record(
            computation_id="A",
            input_hashes=input_hash("A"),
            dependency_hashes={},
            producer="benchmark",
            result_hash=hash_value("A:v2"),
            duration_ms=0.2,
            cpu_ms=0.1,
            memory_bytes=256,
            cost_units=0.1,
            invalidation_rule="stale dependents when result hash changes",
            proof_reference="benchmark:A:v2",
        )
        invalidation_state = {
            identifier: memory.get(identifier).state.value
            for identifier in ("A", "B", "C", "D")
        }
        d_reuse = memory.check_reuse(
            "D", input_hashes=input_hash("D"), dependency_hashes={}
        )
        b2 = memory.record(
            computation_id="B",
            input_hashes=input_hash("B"),
            dependency_hashes={"A": a2.result_hash},
            producer="benchmark",
            result_hash=hash_value("B:v2"),
            duration_ms=0.3,
            cpu_ms=0.2,
            memory_bytes=384,
            cost_units=0.2,
            invalidation_rule="stale when A result hash changes",
            proof_reference="benchmark:B:v2",
        )
        memory.record(
            computation_id="C",
            input_hashes=input_hash("C"),
            dependency_hashes={"B": b2.result_hash},
            producer="benchmark",
            result_hash=hash_value("C:v2"),
            duration_ms=0.4,
            cpu_ms=0.3,
            memory_bytes=512,
            cost_units=0.3,
            invalidation_rule="stale when B result hash changes",
            proof_reference="benchmark:C:v2",
        )
        final_states = {
            record.computation_id: record.state.value
            for record in memory.list_records()
        }
        database_status = {
            "integrity_check": memory.integrity_check(),
            "journal_mode": memory.journal_mode(),
        }

    cpu_ns = time.process_time_ns() - cpu_start
    wall_ns = time.perf_counter_ns() - wall_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    chain_valid, chain_errors = audit.verify_chain()
    route_correct = all(row["correct"] for row in routes)
    invalidation_correct = invalidation_state == {
        "A": ComputationState.VALID.value,
        "B": ComputationState.STALE.value,
        "C": ComputationState.STALE.value,
        "D": ComputationState.VALID.value,
    }
    return {
        "schema": "twis-cognitive-substrate-benchmark-v0.1",
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "logical_cpu_count": os.cpu_count(),
            "dependencies": "Python standard library and embedded SQLite only",
            "network_calls": 0,
            "provider_calls": 0,
            "model_runtime": "deterministic FakeModel only",
        },
        "target_profile": {
            "cpu": "AMD A4-class, 4 logical processors",
            "ram_bytes": 7447904256,
            "gpu_required": False,
        },
        "routes": routes,
        "routing_metrics": {
            "work_items": len(routes),
            "central_ai_calls_required": len(model.calls),
            "central_ai_calls_avoided": central_available - len(model.calls),
            "fake_model_calls": list(model.calls),
            "worker_calls": worker_calls,
        },
        "computation_memory": {
            "reuse_before_dependency_change": reuse_before.reusable,
            "unaffected_d_reused_after_change": d_reuse.reusable,
            "state_after_a_changed": invalidation_state,
            "recomputed_dependents": ["B", "C"],
            "final_states": final_states,
            **database_status,
        },
        "measurements": {
            "cpu_ns": cpu_ns,
            "wall_ns": wall_ns,
            "peak_traced_memory_bytes": peak_bytes,
        },
        "receipts": {
            "count": len(audit.receipts),
            "chain_valid": chain_valid,
            "chain_errors": list(chain_errors),
            "head_sha256": audit.receipts[-1].sha256,
        },
        "correctness": {
            "routes_match_expected": route_correct,
            "dependency_invalidation": invalidation_correct,
            "unaffected_result_reused": d_reuse.reusable,
            "all_recomputed_records_valid": all(
                state == ComputationState.VALID.value
                for state in final_states.values()
            ),
        },
    }
