import tempfile
from pathlib import Path
import unittest

from untethered_aios import (
    CapabilityGrant,
    CapabilityRequest,
    Kernel,
    ProcessState,
    Route,
    RouteEstimate,
    SQLiteComputationMemory,
    SQLiteProcessTable,
    WorkItem,
)
from untethered_aios.audit import hash_value
from untethered_aios.computation_memory import ComputationState
from untethered_aios.fake_model import FakeModel
from untethered_aios.kernel import Step
from untethered_aios.reflex_execution import (
    CHEAP_HANDLER_CAPABILITY,
    REQUEST_NORMALIZER_HANDLER_ID,
    REQUEST_NORMALIZER_SCOPE,
    CheapHandlerRegistry,
    ExecutionStatus,
    KernelCheapExecutionBridge,
    build_default_cheap_handler_registry,
)


FIXED_TIME = "2026-01-01T00:00:00+00:00"


def cheap_work(identifier="cheap-1"):
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


def central_work():
    return WorkItem(
        work_item_id="novel-1",
        task_class="novel",
        urgency=0.7,
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


class ReflexExecutionBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.kernel_path = root / "kernel.sqlite3"
        self.kernel = Kernel(
            process_table=SQLiteProcessTable(self.kernel_path),
            clock=lambda: FIXED_TIME,
        )
        self.memory = SQLiteComputationMemory(
            root / "computations.sqlite3",
            audit=self.kernel.audit,
        )
        self.registry = build_default_cheap_handler_registry()
        self.model = FakeModel(["fake-central-result"])
        self.bridge = KernelCheapExecutionBridge(
            kernel=self.kernel,
            memory=self.memory,
            registry=self.registry,
            fake_model=self.model,
        )

    def tearDown(self):
        self.memory.close()
        self.kernel.close()
        self.temporary.cleanup()

    def _record_dependency(self, identifier, value):
        return self.memory.record(
            computation_id=identifier,
            input_hashes={"input": hash_value(f"{identifier}-input")},
            dependency_hashes={},
            producer="test-dependency",
            result_hash=hash_value({"value": value}),
            result_value={"value": value},
            duration_ms=0.1,
            cpu_ms=0.1,
            memory_bytes=128,
            cost_units=0.1,
            invalidation_rule="stale when result hash changes",
            proof_reference=f"test:{identifier}:{value}",
        )

    def test_registry_declares_bounded_handler_contract(self):
        registry = build_default_cheap_handler_registry()
        spec = registry.resolve("request.normalize", REQUEST_NORMALIZER_HANDLER_ID)
        self.assertEqual(spec.handler_id, REQUEST_NORMALIZER_HANDLER_ID)
        self.assertEqual(spec.supported_task_class, "request.normalize")
        self.assertEqual(
            spec.required_capabilities,
            (CapabilityGrant(CHEAP_HANDLER_CAPABILITY, (REQUEST_NORMALIZER_SCOPE,)),),
        )
        self.assertTrue(spec.deterministic)
        self.assertEqual(spec.version, "1.0.0")
        self.assertEqual(len(spec.dependency_sha256), 64)
        self.assertLess(spec.expected_cost_units, 1)
        with self.assertRaises(ValueError):
            registry.register(spec, lambda payload: payload)
        with self.assertRaises(KeyError):
            registry.resolve("different.task", REQUEST_NORMALIZER_HANDLER_ID)

    def test_first_run_executes_and_identical_repeat_reuses(self):
        payload = {"title": "  Ship It  ", "tags": ["FAST", "fast", " Local "]}
        first = self.bridge.execute(cheap_work(), payload)
        second = self.bridge.execute(cheap_work(), payload)

        self.assertEqual(first.status, ExecutionStatus.EXECUTED)
        self.assertEqual(second.status, ExecutionStatus.REUSED)
        self.assertEqual(first.result, {"title": "Ship It", "tags": ["fast", "local"]})
        self.assertEqual(second.result, first.result)
        self.assertEqual(self.registry.execution_count(REQUEST_NORMALIZER_HANDLER_ID), 1)
        self.assertEqual(self.model.calls, [])
        self.assertIsNotNone(first.pid)
        self.assertIsNone(second.pid)
        self.assertGreater(second.wall_ns, 0)
        self.assertGreaterEqual(second.cpu_ns, 0)
        self.assertGreaterEqual(second.traced_memory_bytes, 0)
        self.assertEqual(
            self.kernel.get_process(first.pid).state,
            ProcessState.DONE,
        )
        kinds = [receipt.kind for receipt in self.kernel.audit.receipts]
        self.assertIn("capability.call", kinds)
        self.assertIn("computation.executed", kinds)
        self.assertIn("computation.reused", kinds)
        self.assertEqual(self.kernel.audit.verify_chain(), (True, ()))

    def test_kernel_denies_missing_and_wrong_handler_grants(self):
        request = CapabilityRequest(
            CHEAP_HANDLER_CAPABILITY,
            {
                "handler_scope": REQUEST_NORMALIZER_SCOPE,
                "task_class": "request.normalize",
                "payload": {"title": "x", "tags": []},
            },
        )

        def runner(ctx):
            return Step.done(ctx.invoke(request))

        missing = self.kernel.spawn("missing-grant", runner)
        wrong = self.kernel.spawn(
            "wrong-grant",
            runner,
            grants=(
                CapabilityGrant(
                    CHEAP_HANDLER_CAPABILITY,
                    ("handler:different-handler-v1",),
                ),
            ),
        )
        self.kernel.run()
        self.assertEqual(self.kernel.get_process(missing).state, ProcessState.FAILED)
        self.assertEqual(self.kernel.get_process(wrong).state, ProcessState.FAILED)
        denied = [
            receipt
            for receipt in self.kernel.audit.receipts
            if receipt.kind == "capability.denied"
        ]
        self.assertEqual({receipt.pid for receipt in denied}, {missing, wrong})

    def test_dependency_change_recomputes_only_affected_work(self):
        a1 = self._record_dependency("A", "a1")
        self._record_dependency("U", "u1")
        payload = {"title": " Same ", "tags": ["ONE"]}

        first = self.bridge.execute(
            cheap_work("dependent"),
            payload,
            dependency_hashes={"A": a1.result_hash},
        )
        repeated = self.bridge.execute(
            cheap_work("dependent"),
            payload,
            dependency_hashes={"A": a1.result_hash},
        )
        a2 = self._record_dependency("A", "a2")
        stale = self.memory.get(first.computation_id)
        recomputed = self.bridge.execute(
            cheap_work("dependent"),
            payload,
            dependency_hashes={"A": a2.result_hash},
        )
        unrelated = self.memory.check_reuse(
            "U",
            input_hashes={"input": hash_value("U-input")},
            dependency_hashes={},
            expected_producer="test-dependency",
            expected_invalidation_rule="stale when result hash changes",
            require_proof=True,
        )

        self.assertEqual(repeated.status, ExecutionStatus.REUSED)
        self.assertEqual(stale.state, ComputationState.STALE)
        self.assertEqual(recomputed.status, ExecutionStatus.EXECUTED)
        self.assertEqual(self.registry.execution_count(REQUEST_NORMALIZER_HANDLER_ID), 2)
        self.assertTrue(unrelated.reusable)
        self.assertEqual(self.memory.get("U").state, ComputationState.VALID)

    def test_central_ai_and_owner_gate_do_not_run_cheap_handler(self):
        central = self.bridge.execute(central_work(), {"question": "novel"})
        protected = cheap_work("protected")
        protected = WorkItem(
            **{
                **protected.__dict__,
                "protected_operation": True,
            }
        )
        owner = self.bridge.execute(
            protected,
            {"title": "No", "tags": []},
        )

        self.assertEqual(central.route, Route.CENTRAL_AI)
        self.assertEqual(central.status, ExecutionStatus.CENTRAL_AI)
        self.assertEqual(self.model.calls, ['{"question":"novel"}'])
        self.assertEqual(owner.route, Route.OWNER_GATE)
        self.assertEqual(owner.status, ExecutionStatus.OWNER_GATE)
        self.assertEqual(self.registry.execution_count(REQUEST_NORMALIZER_HANDLER_ID), 0)
        self.assertEqual(len(self.model.calls), 1)
        kinds = [receipt.kind for receipt in self.kernel.audit.receipts]
        self.assertIn("execution.central_ai", kinds)
        self.assertIn("execution.owner_gate", kinds)

    def test_computation_receipts_persist_in_kernel_sink(self):
        payload = {"title": " Persist ", "tags": []}
        self.bridge.execute(cheap_work("persist"), payload)
        self.bridge.execute(cheap_work("persist"), payload)
        persisted = self.kernel.process_table.list_receipts()
        kinds = [receipt["kind"] for receipt in persisted]
        self.assertIn("computation.executed", kinds)
        self.assertIn("computation.reused", kinds)


if __name__ == "__main__":
    unittest.main()
