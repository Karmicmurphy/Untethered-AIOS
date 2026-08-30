from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import platform
import time
import tracemalloc

from .computation_memory import SQLiteComputationMemory
from .execution_budget import ExecutionBudget
from .fake_model import FakeModel
from .kernel import Kernel
from .process_table import ProcessState, SQLiteProcessTable
from .reflex_benchmark import _central_work, _cheap_work, run_reflex_execution_benchmark
from .reflex_execution import (
    KernelCheapExecutionBridge,
    build_default_cheap_handler_registry,
)


_FIXED_TIME = "2026-01-01T00:00:00+00:00"


class _SequenceClock:
    def __init__(self, values):
        self._values = list(values)
        self._index = 0

    def __call__(self) -> int:
        if not self._values:
            return 0
        value = self._values[min(self._index, len(self._values) - 1)]
        self._index += 1
        return int(value)


def _budget(task_id: str, *, recoveries: int = 0) -> ExecutionBudget:
    return ExecutionBudget(
        budget_id=f"benchmark-{task_id}",
        owner_id="kernel-benchmark",
        task_id=task_id,
        max_wall_ns=100,
        max_cpu_ns=100,
        max_ticks=1,
        max_work_units=64,
        max_recovery_attempts=recoveries,
    )


def _bridge(root: Path, wall_values, cpu_values, responses=("central",)):
    kernel = Kernel(
        process_table=SQLiteProcessTable(root / "kernel.sqlite3"),
        clock=lambda: _FIXED_TIME,
        wall_clock_ns=_SequenceClock(wall_values),
        cpu_clock_ns=_SequenceClock(cpu_values),
    )
    memory = SQLiteComputationMemory(
        root / "computations.sqlite3",
        audit=kernel.audit,
    )
    registry = build_default_cheap_handler_registry()
    model = FakeModel(list(responses))
    bridge = KernelCheapExecutionBridge(
        kernel=kernel,
        memory=memory,
        registry=registry,
        fake_model=model,
    )
    return kernel, memory, registry, model, bridge


def _chain_summary(kernel: Kernel) -> dict:
    valid, errors = kernel.audit.verify_chain()
    receipts = kernel.audit.as_dicts()
    return {
        "count": len(receipts),
        "persisted_count": len(kernel.process_table.list_receipts()),
        "valid": valid,
        "errors": list(errors),
        "head_sha256": receipts[-1]["sha256"] if receipts else None,
        "kinds": [receipt["kind"] for receipt in receipts],
    }


def run_budget_recovery_benchmark(root: str | Path) -> dict:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    campaign_2 = run_reflex_execution_benchmark(root / "campaign-2")

    tracemalloc.start()
    wall_start = time.perf_counter_ns()
    cpu_start = time.process_time_ns()

    success_root = root / "success"
    success_root.mkdir()
    kernel_a, memory_a, registry_a, model_a, bridge_a = _bridge(
        success_root,
        [0] * 64,
        [0] * 64,
    )
    success_work = _cheap_work("budget-benchmark-success")
    success_budget = _budget(success_work.work_item_id)
    payload = {"title": " Budgeted ", "tags": ["ONE"]}
    first = bridge_a.execute(success_work, payload, budget=success_budget)
    repeated = bridge_a.execute(success_work, payload, budget=success_budget)
    novel = bridge_a.execute(
        _central_work(),
        {"question": "novel"},
        budget=_budget("benchmark-novel"),
    )
    protected_work = replace(
        _cheap_work("budget-benchmark-protected"),
        protected_operation=True,
    )
    protected = bridge_a.execute(
        protected_work,
        {"title": "Protected", "tags": []},
        budget=_budget(protected_work.work_item_id),
    )

    recovery_root = root / "recovery"
    recovery_root.mkdir()
    kernel_b, memory_b, registry_b1, model_b1, bridge_b = _bridge(
        recovery_root,
        [0, 200],
        [0, 0],
    )
    recovery_work = _cheap_work("budget-benchmark-recovery")
    recovery_budget = _budget(recovery_work.work_item_id, recoveries=1)
    recovery_payload = {"title": " Recovery ", "tags": ["ONE"]}
    failed = bridge_b.execute(
        recovery_work,
        recovery_payload,
        budget=recovery_budget,
        auto_recover=False,
    )
    failed_record_absent = memory_b.get(failed.computation_id) is None
    receipts_before_reopen = len(kernel_b.audit.receipts)
    memory_b.close()
    kernel_b.close()

    kernel_b, memory_b, registry_b, model_b, bridge_b = _bridge(
        recovery_root,
        [0] * 64,
        [0] * 64,
    )
    prior_failure_visible = (
        kernel_b.get_process(failed.pid).state is ProcessState.FAILED
        and any(
            receipt.sha256 == failed.receipt_sha256
            for receipt in kernel_b.audit.receipts
        )
    )
    recovered = bridge_b.recover(
        recovery_work,
        recovery_payload,
        budget=recovery_budget,
    )
    recovered_reuse = bridge_b.execute(
        recovery_work,
        recovery_payload,
        budget=recovery_budget,
    )

    terminal_root = root / "terminal"
    terminal_root.mkdir()
    kernel_c, memory_c, registry_c, model_c, bridge_c = _bridge(
        terminal_root,
        [0, 200, 300, 500],
        [0, 0, 0, 0],
    )
    terminal_work = _cheap_work("budget-benchmark-terminal")
    terminal_budget = _budget(terminal_work.work_item_id, recoveries=1)
    terminal = bridge_c.execute(
        terminal_work,
        {"title": "Terminal", "tags": []},
        budget=terminal_budget,
    )
    terminal_record_absent = memory_c.get(terminal.computation_id) is None
    terminal_states = [
        kernel_c.get_process(pid).state.value for pid in terminal.pids
    ]

    cpu_root = root / "cpu"
    cpu_root.mkdir()
    kernel_d, memory_d, registry_d, model_d, bridge_d = _bridge(
        cpu_root,
        [0, 0],
        [0, 200],
    )
    cpu_work = _cheap_work("budget-benchmark-cpu")
    cpu_budget = _budget(cpu_work.work_item_id)
    cpu_failed = bridge_d.execute(
        cpu_work,
        {"title": "CPU", "tags": []},
        budget=cpu_budget,
    )
    cpu_record_absent = memory_d.get(cpu_failed.computation_id) is None

    cpu_ns = time.process_time_ns() - cpu_start
    wall_ns = time.perf_counter_ns() - wall_start
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    chains = {
        "success": _chain_summary(kernel_a),
        "recovery": _chain_summary(kernel_b),
        "terminal": _chain_summary(kernel_c),
        "cpu": _chain_summary(kernel_d),
    }
    all_chains_valid = all(
        chain["valid"] and chain["count"] == chain["persisted_count"]
        for chain in chains.values()
    )
    all_kinds = [kind for chain in chains.values() for kind in chain["kinds"]]
    handler_executions = sum(
        registry.execution_count("request-normalizer-v1")
        for registry in (registry_a, registry_b, registry_c, registry_d)
    )
    fake_model_calls = (
        len(model_a.calls) + len(model_b.calls) + len(model_c.calls) + len(model_d.calls)
    )
    correctness = {
        "cheap_success_executed": first.status.value == "EXECUTED",
        "identical_success_reused": repeated.status.value == "REUSED",
        "forced_budget_exhaustion": failed.status.value == "BUDGET_EXCEEDED",
        "forced_cpu_budget_exhaustion": cpu_failed.status.value == "BUDGET_EXCEEDED",
        "cpu_failure_never_recorded": cpu_record_absent,
        "failed_result_never_recorded": failed_record_absent,
        "prior_failure_visible_after_reopen": prior_failure_visible,
        "bounded_recovery_succeeded": recovered.status.value == "RECOVERED",
        "recovered_result_reused": recovered_reuse.status.value == "REUSED",
        "repeated_failure_terminal": (
            terminal.status.value == "BUDGET_EXCEEDED"
            and terminal.attempt_count == terminal_budget.max_attempts
            and terminal_states == ["FAILED", "FAILED"]
        ),
        "terminal_failure_never_recorded": terminal_record_absent,
        "novel_used_fake_model": (
            novel.status.value == "CENTRAL_AI" and fake_model_calls == 1
        ),
        "protected_owner_gated": protected.status.value == "OWNER_GATE",
        "all_receipt_chains_valid": all_chains_valid,
    }
    result = {
        "schema": "twis-cheap-execution-budget-recovery-benchmark-v0.1",
        "extends": campaign_2["schema"],
        "campaign_2": campaign_2,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "logical_cpu_count": os.cpu_count(),
            "dependencies": "Python standard library and embedded SQLite only",
            "network_calls": 0,
            "provider_calls": 0,
            "model_runtime": "deterministic FakeModel only",
            "enforcement_boundary": "cooperative trusted Python checkpoints",
        },
        "execution_cases": {
            "success": {
                "route": first.route.value,
                "status": first.status.value,
                "pids": list(first.pids),
                "attempt_count": first.attempt_count,
                "cpu_ns": first.cpu_ns,
                "wall_ns": first.wall_ns,
                "traced_memory_bytes": first.traced_memory_bytes,
            },
            "identical_reuse": {
                "status": repeated.status.value,
                "pids": list(repeated.pids),
                "attempt_count": repeated.attempt_count,
                "cpu_ns": repeated.cpu_ns,
                "wall_ns": repeated.wall_ns,
                "traced_memory_bytes": repeated.traced_memory_bytes,
            },
            "forced_failure": {
                "status": failed.status.value,
                "pids": list(failed.pids),
                "attempt_count": failed.attempt_count,
                "final_state": "FAILED",
                "failure_kind": failed.failure_kind,
            },
            "recovered": {
                "status": recovered.status.value,
                "pids": list(recovered.pids),
                "attempt_count": recovered.attempt_count,
                "final_states": ["FAILED", "DONE"],
                "cpu_ns": recovered.cpu_ns,
                "wall_ns": recovered.wall_ns,
                "traced_memory_bytes": recovered.traced_memory_bytes,
            },
            "recovered_reuse": {
                "status": recovered_reuse.status.value,
                "pids": list(recovered_reuse.pids),
                "attempt_count": recovered_reuse.attempt_count,
            },
            "terminal_failure": {
                "status": terminal.status.value,
                "pids": list(terminal.pids),
                "attempt_count": terminal.attempt_count,
                "final_states": terminal_states,
                "failure_kind": terminal.failure_kind,
            },
            "cpu_failure": {
                "status": cpu_failed.status.value,
                "pids": list(cpu_failed.pids),
                "attempt_count": cpu_failed.attempt_count,
                "final_state": "FAILED",
                "failure_kind": cpu_failed.failure_kind,
            },
            "novel": {
                "route": novel.route.value,
                "status": novel.status.value,
            },
            "protected": {
                "route": protected.route.value,
                "status": protected.status.value,
            },
        },
        "economy": {
            "handler_executions": handler_executions,
            "reuse_hits": 2,
            "failed_attempts": 4,
            "recoveries_started": all_kinds.count("execution.recovery_started"),
            "recoveries_succeeded": all_kinds.count("execution.recovered"),
            "budget_exceeded_events": all_kinds.count("execution.budget_exceeded"),
            "fake_model_calls": fake_model_calls,
            "receipts_before_reopen": receipts_before_reopen,
        },
        "measurements": {
            "cpu_ns": cpu_ns,
            "wall_ns": wall_ns,
            "peak_traced_memory_bytes": peak_bytes,
        },
        "receipts": {
            "chains": chains,
            "all_chains_valid": all_chains_valid,
            "total_count": sum(chain["count"] for chain in chains.values()),
            "total_persisted_count": sum(
                chain["persisted_count"] for chain in chains.values()
            ),
            "budget_exceeded_events": all_kinds.count("execution.budget_exceeded"),
            "failure_events": all_kinds.count("execution.failed"),
            "recovery_started_events": all_kinds.count("execution.recovery_started"),
            "recovered_events": all_kinds.count("execution.recovered"),
        },
        "durability": {
            "failure_receipts_before_reopen": receipts_before_reopen,
            "prior_failed_pid": failed.pid,
            "prior_failure_receipt_sha256": failed.receipt_sha256,
            "prior_failure_visible_after_reopen": prior_failure_visible,
            "kernel_integrity": kernel_b.process_table.integrity_check(),
            "kernel_journal_mode": kernel_b.process_table.journal_mode(),
            "computation_integrity": memory_b.integrity_check(),
            "computation_journal_mode": memory_b.journal_mode(),
        },
        "correctness": correctness,
    }
    memory_a.close()
    kernel_a.close()
    memory_b.close()
    kernel_b.close()
    memory_c.close()
    kernel_c.close()
    memory_d.close()
    kernel_d.close()
    return result
