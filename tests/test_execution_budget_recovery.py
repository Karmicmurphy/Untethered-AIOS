from dataclasses import replace
import tempfile
from pathlib import Path
import unittest

from untethered_aios import (
    BudgetExceeded,
    BudgetGuard,
    CapabilityGrant,
    CapabilityRequest,
    ExecutionBudget,
    ExecutionStatus,
    Kernel,
    KernelCheapExecutionBridge,
    ProcessState,
    SQLiteComputationMemory,
    SQLiteProcessTable,
    build_default_cheap_handler_registry,
)
from untethered_aios.fake_model import FakeModel
from untethered_aios.kernel import Step
from untethered_aios.reflex_execution import (
    CHEAP_HANDLER_CAPABILITY,
    REQUEST_NORMALIZER_SCOPE,
)
from tests.test_reflex_execution_bridge import cheap_work, central_work


FIXED_TIME = "2026-01-01T00:00:00+00:00"


class SequenceClock:
    def __init__(self, values):
        self.values = list(values)
        self.index = 0

    def __call__(self):
        if not self.values:
            return 0
        value = self.values[min(self.index, len(self.values) - 1)]
        self.index += 1
        return value


def budget(task_id, *, recoveries=0, wall_ns=100, cpu_ns=100):
    return ExecutionBudget(
        budget_id=f"budget-{task_id}",
        owner_id="kernel-test-owner",
        task_id=task_id,
        max_wall_ns=wall_ns,
        max_cpu_ns=cpu_ns,
        max_ticks=1,
        max_work_units=64,
        max_recovery_attempts=recoveries,
    )


class ExecutionBudgetRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def build_bridge(self, wall_values, cpu_values, *, model_responses=None):
        kernel = Kernel(
            process_table=SQLiteProcessTable(self.root / "kernel.sqlite3"),
            clock=lambda: FIXED_TIME,
            wall_clock_ns=SequenceClock(wall_values),
            cpu_clock_ns=SequenceClock(cpu_values),
        )
        memory = SQLiteComputationMemory(
            self.root / "computations.sqlite3",
            audit=kernel.audit,
        )
        registry = build_default_cheap_handler_registry()
        model = FakeModel(model_responses or ["central"])
        bridge = KernelCheapExecutionBridge(
            kernel=kernel,
            memory=memory,
            registry=registry,
            fake_model=model,
        )
        return kernel, memory, registry, model, bridge

    def test_budget_contract_is_explicit_stable_and_fail_closed(self):
        current = budget("budget-contract", recoveries=2)
        self.assertEqual(current.max_attempts, 3)
        self.assertEqual(len(current.contract_sha256), 64)
        self.assertEqual(current, budget("budget-contract", recoveries=2))
        with self.assertRaises(ValueError):
            replace(current, max_wall_ns=0)
        with self.assertRaises(ValueError):
            replace(current, max_recovery_attempts=-1)
        with self.assertRaises(ValueError):
            replace(current, task_id="")
        guard = BudgetGuard(
            current,
            pid=1,
            attempt_id="attempt-tick-test",
            attempt_number=1,
            wall_clock_ns=SequenceClock([0, 0]),
            cpu_clock_ns=SequenceClock([0, 0]),
        )
        guard.start()
        with self.assertRaises(BudgetExceeded) as raised:
            guard.checkpoint(process_ticks=2)
        self.assertEqual(raised.exception.limit, "max_ticks")

    def test_success_and_repeat_reuse_remain_budgeted(self):
        kernel, memory, registry, model, bridge = self.build_bridge(
            range(0, 30),
            range(0, 30),
        )
        try:
            work = cheap_work("budget-success")
            current = budget(work.work_item_id, wall_ns=1_000, cpu_ns=1_000)
            first = bridge.execute(
                work,
                {"title": "  Budgeted ", "tags": ["ONE"]},
                budget=current,
            )
            repeated = bridge.execute(
                work,
                {"title": "  Budgeted ", "tags": ["ONE"]},
                budget=current,
            )
            self.assertEqual(first.status, ExecutionStatus.EXECUTED)
            self.assertEqual(first.attempt_count, 1)
            self.assertEqual(repeated.status, ExecutionStatus.REUSED)
            self.assertEqual(repeated.attempt_count, 0)
            self.assertEqual(len(first.pids), 1)
            self.assertEqual(registry.execution_count(first.handler_id), 1)
            self.assertEqual(model.calls, [])
        finally:
            memory.close()
            kernel.close()

    def test_wall_budget_exhaustion_fails_process_and_never_records_result(self):
        kernel, memory, registry, model, bridge = self.build_bridge(
            [0, 200],
            [0, 0],
        )
        try:
            work = cheap_work("budget-exhausted")
            outcome = bridge.execute(
                work,
                {"title": "No result", "tags": []},
                budget=budget(work.work_item_id),
            )
            self.assertEqual(outcome.status, ExecutionStatus.BUDGET_EXCEEDED)
            self.assertEqual(outcome.attempt_count, 1)
            self.assertEqual(kernel.get_process(outcome.pid).state, ProcessState.FAILED)
            self.assertIsNone(memory.get(outcome.computation_id))
            self.assertFalse(
                memory.check_reuse(
                    outcome.computation_id,
                    input_hashes={},
                    dependency_hashes={},
                ).reusable
            )
            self.assertEqual(registry.execution_count(outcome.handler_id), 0)
            kinds = [receipt.kind for receipt in kernel.audit.receipts]
            self.assertIn("execution.started", kinds)
            self.assertIn("execution.budget_exceeded", kinds)
            self.assertIn("execution.failed", kinds)
            self.assertNotIn("computation.executed", kinds)
        finally:
            memory.close()
            kernel.close()

    def test_cpu_and_work_unit_exhaustion_are_distinct_fail_closed_limits(self):
        kernel, memory, registry, model, bridge = self.build_bridge(
            [0, 0],
            [0, 200],
        )
        try:
            work = cheap_work("cpu-exhausted")
            cpu_failed = bridge.execute(
                work,
                {"title": "CPU", "tags": []},
                budget=budget(work.work_item_id),
            )
            receipt = next(
                item
                for item in kernel.audit.receipts
                if item.kind == "execution.budget_exceeded"
            )
            self.assertEqual(cpu_failed.status, ExecutionStatus.BUDGET_EXCEEDED)
            self.assertEqual(receipt.detail["limit"], "max_cpu_ns")
        finally:
            memory.close()
            kernel.close()

        work_root = self.root / "work-units"
        work_root.mkdir()
        original_root = self.root
        self.root = work_root
        kernel, memory, registry, model, bridge = self.build_bridge(
            [0] * 10,
            [0] * 10,
        )
        try:
            work = cheap_work("work-units-exhausted")
            limited = replace(budget(work.work_item_id), max_work_units=1)
            work_failed = bridge.execute(
                work,
                {"title": "Work", "tags": []},
                budget=limited,
            )
            receipt = next(
                item
                for item in kernel.audit.receipts
                if item.kind == "execution.budget_exceeded"
            )
            self.assertEqual(work_failed.status, ExecutionStatus.BUDGET_EXCEEDED)
            self.assertEqual(receipt.detail["limit"], "max_work_units")
        finally:
            memory.close()
            kernel.close()
            self.root = original_root

    def test_worker_cannot_supply_or_replace_kernel_budget_checkpoint(self):
        kernel, memory, registry, model, bridge = self.build_bridge(
            [0] * 10,
            [0] * 10,
        )
        try:
            work = cheap_work("checkpoint-injection")
            current = budget(work.work_item_id)

            def runner(context):
                return Step.done(
                    context.invoke(
                        CapabilityRequest(
                            CHEAP_HANDLER_CAPABILITY,
                            {
                                "handler_scope": REQUEST_NORMALIZER_SCOPE,
                                "task_class": "request.normalize",
                                "payload": {"title": "forged", "tags": []},
                                "budget_checkpoint": "worker-forged",
                            },
                        )
                    )
                )

            pid = kernel.spawn(
                "forged-checkpoint",
                runner,
                grants=(
                    CapabilityGrant(
                        CHEAP_HANDLER_CAPABILITY,
                        (REQUEST_NORMALIZER_SCOPE,),
                    ),
                ),
                execution_budget=current,
                attempt_id="attempt-forged-checkpoint",
                attempt_number=1,
            )
            kernel.run()
            self.assertEqual(kernel.get_process(pid).state, ProcessState.FAILED)
            self.assertIn("Kernel-injected", kernel.get_process(pid).error)
            self.assertTrue(
                any(
                    receipt.kind == "capability.denied" and receipt.pid == pid
                    for receipt in kernel.audit.receipts
                )
            )
        finally:
            memory.close()
            kernel.close()

    def test_handler_failure_is_terminal_and_not_reusable(self):
        kernel, memory, registry, model, bridge = self.build_bridge(
            [0] * 20,
            [0] * 20,
        )
        try:
            work = cheap_work("handler-failed")
            outcome = bridge.execute(
                work,
                {"title": "missing-tags"},
                budget=budget(work.work_item_id),
            )
            self.assertEqual(outcome.status, ExecutionStatus.FAILED)
            self.assertEqual(kernel.get_process(outcome.pid).state, ProcessState.FAILED)
            self.assertIsNone(memory.get(outcome.computation_id))
            self.assertIn("CapabilityFailed", kernel.get_process(outcome.pid).error)
        finally:
            memory.close()
            kernel.close()

    def test_bounded_recovery_succeeds_with_same_grants_and_version(self):
        wall = [0, 200, 300, 300, 301, 302, 303, 304, 305]
        kernel, memory, registry, model, bridge = self.build_bridge(
            wall,
            [0] * len(wall),
        )
        try:
            work = cheap_work("recovery-success")
            outcome = bridge.execute(
                work,
                {"title": " Recover ", "tags": ["ONE"]},
                budget=budget(work.work_item_id, recoveries=1),
            )
            self.assertEqual(outcome.status, ExecutionStatus.RECOVERED)
            self.assertEqual(outcome.attempt_count, 2)
            self.assertEqual(len(outcome.pids), 2)
            failed, succeeded = [kernel.get_process(pid) for pid in outcome.pids]
            self.assertEqual(failed.state, ProcessState.FAILED)
            self.assertEqual(succeeded.state, ProcessState.DONE)
            self.assertEqual(failed.grants, succeeded.grants)
            self.assertEqual(failed.runner_id, succeeded.runner_id)
            self.assertIsNotNone(memory.get(outcome.computation_id))
            kinds = [receipt.kind for receipt in kernel.audit.receipts]
            self.assertIn("execution.recovery_started", kinds)
            self.assertIn("execution.recovered", kinds)
        finally:
            memory.close()
            kernel.close()

    def test_repeated_budget_failure_stops_at_finite_attempt_limit(self):
        kernel, memory, registry, model, bridge = self.build_bridge(
            [0, 200, 300, 500],
            [0, 0, 0, 0],
        )
        try:
            work = cheap_work("recovery-terminal")
            outcome = bridge.execute(
                work,
                {"title": "No", "tags": []},
                budget=budget(work.work_item_id, recoveries=1),
            )
            self.assertEqual(outcome.status, ExecutionStatus.BUDGET_EXCEEDED)
            self.assertEqual(outcome.attempt_count, 2)
            self.assertEqual(len(outcome.pids), 2)
            self.assertTrue(
                all(
                    kernel.get_process(pid).state is ProcessState.FAILED
                    for pid in outcome.pids
                )
            )
            self.assertIsNone(memory.get(outcome.computation_id))
            starts = [
                receipt
                for receipt in kernel.audit.receipts
                if receipt.kind == "execution.started"
            ]
            self.assertEqual(len(starts), 2)
        finally:
            memory.close()
            kernel.close()

    def test_reopen_preserves_failure_then_recovery_becomes_reusable(self):
        work = cheap_work("reopen-recovery")
        current = budget(work.work_item_id, recoveries=1)
        payload = {"title": " Reopen ", "tags": ["ONE"]}
        kernel, memory, registry, model, bridge = self.build_bridge(
            [0, 200],
            [0, 0],
        )
        failed = bridge.execute(
            work,
            payload,
            budget=current,
            auto_recover=False,
        )
        failed_pid = failed.pid
        failed_receipt = failed.receipt_sha256
        memory.close()
        kernel.close()

        kernel, memory, registry, model, bridge = self.build_bridge(
            [0, 0, 1, 2, 3, 4, 5],
            [0] * 7,
        )
        try:
            self.assertEqual(kernel.get_process(failed_pid).state, ProcessState.FAILED)
            self.assertTrue(
                any(receipt.sha256 == failed_receipt for receipt in kernel.audit.receipts)
            )
            recovered = bridge.recover(work, payload, budget=current)
            reused = bridge.execute(work, payload, budget=current)
            self.assertEqual(recovered.status, ExecutionStatus.RECOVERED)
            self.assertEqual(recovered.attempt_count, 2)
            self.assertEqual(reused.status, ExecutionStatus.REUSED)
            self.assertEqual(reused.result, recovered.result)
            self.assertEqual(registry.execution_count(recovered.handler_id), 1)
            self.assertEqual(kernel.audit.verify_chain(), (True, ()))
            self.assertEqual(
                len(kernel.audit.receipts),
                len(kernel.process_table.list_receipts()),
            )
        finally:
            memory.close()
            kernel.close()

    def test_recovery_rejects_changed_budget_and_protected_stays_gated(self):
        work = cheap_work("recovery-authority")
        current = budget(work.work_item_id, recoveries=1)
        kernel, memory, registry, model, bridge = self.build_bridge(
            [0, 200],
            [0, 0],
        )
        try:
            bridge.execute(
                work,
                {"title": "Fail", "tags": []},
                budget=current,
                auto_recover=False,
            )
            with self.assertRaises(ValueError):
                bridge.recover(
                    work,
                    {"title": "Fail", "tags": []},
                    budget=replace(current, max_wall_ns=101),
                )
            with self.assertRaises(ValueError):
                bridge.execute(
                    work,
                    {"title": "Fail", "tags": []},
                    budget=replace(current, budget_id="different-budget-id"),
                )
            protected = bridge.execute(
                replace(work, protected_operation=True),
                {"title": "Protected", "tags": []},
                budget=current,
            )
            central = bridge.execute(
                central_work(),
                {"question": "novel"},
                budget=budget("novel-1"),
            )
            self.assertEqual(protected.status, ExecutionStatus.OWNER_GATE)
            self.assertEqual(central.status, ExecutionStatus.CENTRAL_AI)
            self.assertEqual(len(model.calls), 1)
        finally:
            memory.close()
            kernel.close()


if __name__ == "__main__":
    unittest.main()
