import unittest

from untethered_aios.attention_governor import AttentionGovernor
from untethered_aios.audit import AuditLog
from untethered_aios.cognitive_contracts import (
    Route,
    RouteEstimate,
    WorkItem,
)


def estimate(
    route,
    cost,
    probability,
    *,
    cpu=10,
    memory=8,
    deterministic=True,
):
    return RouteEstimate(
        route=route,
        handler_id=f"{route.value.lower()}-handler",
        estimated_cost=cost,
        success_probability=probability,
        cpu_ms=cpu,
        memory_mb=memory,
        deterministic=deterministic,
    )


def item(**overrides):
    values = {
        "work_item_id": "task-1",
        "task_class": "synthetic",
        "urgency": 0.5,
        "owner_priority": 0.5,
        "novelty": 0.1,
        "uncertainty": 0.1,
        "risk": 0.1,
        "expected_benefit": 20.0,
        "cpu_budget_ms": 100,
        "available_memory_mb": 128,
        "memory_pressure": 0.2,
        "route_estimates": (),
    }
    values.update(overrides)
    return WorkItem(**values)


class AttentionGovernorTests(unittest.TestCase):
    def setUp(self):
        self.audit = AuditLog(clock=lambda: "2026-01-01T00:00:00+00:00")
        self.governor = AttentionGovernor(audit=self.audit)

    def test_cheap_familiar_work_uses_reflex(self):
        work = item(
            route_estimates=(
                estimate(Route.REFLEX, 1, 1),
                estimate(Route.CENTRAL_AI, 10, 0.95),
            )
        )
        decision = self.governor.decide(work)
        self.assertEqual(decision.route, Route.REFLEX)
        self.assertEqual(decision.expected_net_value, 19)

    def test_repeated_work_uses_rule_and_novel_work_uses_central_ai(self):
        repeated = item(
            novelty=0.3,
            route_estimates=(
                estimate(Route.REFLEX, 1, 1),
                estimate(Route.RULE, 2, 0.9),
                estimate(Route.WORKER, 5, 0.8),
            ),
        )
        self.assertEqual(self.governor.decide(repeated).route, Route.RULE)

        novel = item(
            work_item_id="novel",
            novelty=0.9,
            uncertainty=0.8,
            expected_benefit=50,
            route_estimates=(
                estimate(Route.WORKER, 10, 0.5),
                estimate(Route.CENTRAL_AI, 20, 0.9),
            ),
        )
        self.assertEqual(self.governor.decide(novel).route, Route.CENTRAL_AI)

    def test_worker_can_beat_central_ai_by_expected_net_value(self):
        work = item(
            novelty=0.6,
            uncertainty=0.5,
            expected_benefit=40,
            route_estimates=(
                estimate(Route.WORKER, 5, 0.85),
                estimate(Route.CENTRAL_AI, 20, 0.8),
            ),
        )
        self.assertEqual(self.governor.decide(work).route, Route.WORKER)

    def test_ignore_defer_and_owner_gate_are_explicit(self):
        self.assertEqual(
            self.governor.decide(
                item(
                    expected_benefit=0.5,
                    urgency=0.1,
                    owner_priority=0.1,
                )
            ).route,
            Route.IGNORE,
        )
        self.assertEqual(
            self.governor.decide(
                item(
                    work_item_id="defer",
                    memory_pressure=0.95,
                    route_estimates=(
                        estimate(Route.WORKER, 1, 1),
                        estimate(Route.CENTRAL_AI, 1, 1),
                    ),
                )
            ).route,
            Route.DEFER,
        )
        self.assertEqual(
            self.governor.decide(
                item(work_item_id="owner", protected_operation=True)
            ).route,
            Route.OWNER_GATE,
        )

    def test_receipt_is_explainable_and_deterministic(self):
        work = item(route_estimates=(estimate(Route.REFLEX, 1, 1),))
        first = self.governor.decide(work)
        other = AttentionGovernor(
            audit=AuditLog(clock=lambda: "2026-01-01T00:00:00+00:00")
        ).decide(work)
        self.assertEqual(first.as_dict(), other.as_dict())
        receipt = self.audit.receipts[-1]
        self.assertEqual(receipt.sha256, first.receipt_sha256)
        self.assertEqual(receipt.detail["input_sha256"], work.input_sha256)
        self.assertIn("resource_assumptions", receipt.detail)
        self.assertEqual(self.audit.verify_chain(), (True, ()))

    def test_observed_failures_reduce_expected_value(self):
        work = item(
            failure_history=(True, False),
            route_estimates=(estimate(Route.REFLEX, 5, 1),),
        )
        decision = self.governor.decide(work)
        self.assertEqual(decision.route, Route.REFLEX)
        self.assertEqual(decision.expected_benefit, 10)
        self.assertEqual(decision.expected_net_value, 5)

    def test_bad_input_and_duplicate_route_estimates_fail_closed(self):
        with self.assertRaises(ValueError):
            item(risk=1.1)
        with self.assertRaises(ValueError):
            item(
                route_estimates=(
                    estimate(Route.RULE, 1, 1),
                    estimate(Route.RULE, 2, 0.5),
                )
            )


if __name__ == "__main__":
    unittest.main()
