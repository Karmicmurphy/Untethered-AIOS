from __future__ import annotations

from dataclasses import replace

from .audit import AuditLog
from .cognitive_contracts import (
    CandidateValue,
    Route,
    RouteDecision,
    RouteEstimate,
    WorkItem,
)


class AttentionGovernor:
    """Deterministic local router using expected benefit minus measured cost."""

    _TIE_ORDER = {
        Route.REFLEX: 0,
        Route.RULE: 1,
        Route.WORKER: 2,
        Route.CENTRAL_AI: 3,
    }

    def __init__(
        self,
        *,
        audit: AuditLog | None = None,
        ignore_benefit: float = 1.0,
        owner_gate_risk: float = 0.8,
    ) -> None:
        self.audit = audit or AuditLog()
        self.ignore_benefit = ignore_benefit
        self.owner_gate_risk = owner_gate_risk

    def decide(self, item: WorkItem) -> RouteDecision:
        candidates = tuple(
            self._value_candidate(item, estimate)
            for estimate in item.route_estimates
        )
        assumptions = {
            "utility_model": (
                "expected_benefit * empirical_success_probability "
                "- estimated_cost"
            ),
            "benefit_and_cost_unit": "caller-supplied utility points",
            "cpu_budget_ms": item.cpu_budget_ms,
            "available_memory_mb": item.available_memory_mb,
            "memory_pressure": item.memory_pressure,
            "failure_observations": len(item.failure_history),
            "historical_success_rate": self._historical_success_rate(item),
            "tie_order": ["REFLEX", "RULE", "WORKER", "CENTRAL_AI"],
        }

        if item.protected_operation or item.risk >= self.owner_gate_risk:
            decision = self._terminal_decision(
                item,
                candidates,
                assumptions,
                Route.OWNER_GATE,
                "OWNER_AUTHORITY_REQUIRED",
                "The operation is protected or exceeds the risk boundary.",
            )
        elif (
            item.expected_benefit <= self.ignore_benefit
            and item.urgency < 0.5
            and item.owner_priority < 0.5
        ):
            decision = self._terminal_decision(
                item,
                candidates,
                assumptions,
                Route.IGNORE,
                "BENEFIT_BELOW_FLOOR",
                "Benefit is at or below the ignore floor and the item is "
                "neither urgent nor owner-prioritized.",
            )
        else:
            eligible = [
                candidate
                for candidate in candidates
                if candidate.eligible
                and candidate.expected_net_value is not None
                and candidate.expected_net_value > 0
            ]
            if not eligible:
                decision = self._terminal_decision(
                    item,
                    candidates,
                    assumptions,
                    Route.DEFER,
                    "NO_POSITIVE_FEASIBLE_ROUTE",
                    "No mechanism fits the resource and uncertainty boundaries "
                    "with positive expected net value.",
                )
            else:
                selected = sorted(
                    eligible,
                    key=lambda candidate: (
                        -float(candidate.expected_net_value),
                        self._TIE_ORDER[candidate.route],
                        candidate.handler_id,
                    ),
                )[0]
                decision = RouteDecision(
                    work_item_id=item.work_item_id,
                    route=selected.route,
                    selected_handler=selected.handler_id,
                    expected_benefit=selected.expected_benefit,
                    expected_cost=selected.expected_cost,
                    expected_net_value=selected.expected_net_value,
                    reason_code="MAXIMUM_POSITIVE_EXPECTED_NET_VALUE",
                    reason=(
                        f"{selected.route.value} has the greatest positive "
                        "feasible expected benefit minus cost; stable route "
                        "order resolves exact ties toward local mechanisms."
                    ),
                    input_sha256=item.input_sha256,
                    candidate_values=candidates,
                    resource_assumptions=assumptions,
                    receipt_sha256="",
                )

        receipt = self.audit.emit(
            "cognitive.route",
            "attention-governor",
            decision.route.value,
            {
                "input_sha256": decision.input_sha256,
                "selected_handler": decision.selected_handler,
                "reason_code": decision.reason_code,
                "reason": decision.reason,
                "expected_benefit": decision.expected_benefit,
                "expected_cost": decision.expected_cost,
                "expected_net_value": decision.expected_net_value,
                "resource_assumptions": decision.resource_assumptions,
                "candidate_values": [
                    candidate.as_dict() for candidate in candidates
                ],
            },
            target=item.work_item_id,
        )
        return replace(decision, receipt_sha256=receipt.sha256)

    def _value_candidate(
        self, item: WorkItem, estimate: RouteEstimate
    ) -> CandidateValue:
        eligible, reason = self._eligibility(item, estimate)
        probability = (
            estimate.success_probability
            * self._historical_success_rate(item)
        )
        expected_benefit = item.expected_benefit * probability
        net_value = expected_benefit - estimate.estimated_cost if eligible else None
        return CandidateValue(
            route=estimate.route,
            handler_id=estimate.handler_id,
            eligible=eligible,
            expected_benefit=round(expected_benefit, 6),
            expected_cost=estimate.estimated_cost,
            expected_net_value=round(net_value, 6) if net_value is not None else None,
            success_probability=round(probability, 6),
            reason=reason,
            cpu_ms=estimate.cpu_ms,
            memory_mb=estimate.memory_mb,
        )

    def _eligibility(
        self, item: WorkItem, estimate: RouteEstimate
    ) -> tuple[bool, str]:
        if estimate.cpu_ms > item.cpu_budget_ms:
            return False, "estimated CPU exceeds the item budget"
        if estimate.memory_mb > item.available_memory_mb:
            return False, "estimated memory exceeds the item budget"
        if item.memory_pressure >= 0.9 and estimate.route in {
            Route.WORKER,
            Route.CENTRAL_AI,
        }:
            return False, "memory pressure blocks nonessential heavy routes"
        if estimate.route is Route.REFLEX:
            if not estimate.deterministic:
                return False, "reflex handlers must be deterministic"
            if item.novelty > 0.2 or item.uncertainty > 0.2:
                return False, "reflex requires familiar, low-uncertainty work"
        if estimate.route is Route.RULE:
            if not estimate.deterministic:
                return False, "rule handlers must be deterministic"
            if item.novelty > 0.4 or item.uncertainty > 0.4:
                return False, "rule boundary rejects novel or ambiguous work"
        if (
            estimate.route is Route.CENTRAL_AI
            and item.novelty < 0.4
            and item.uncertainty < 0.4
        ):
            return False, "central AI is reserved for novel or uncertain work"
        return True, "fits route, resource, novelty, and uncertainty boundaries"

    @staticmethod
    def _historical_success_rate(item: WorkItem) -> float:
        if not item.failure_history:
            return 1.0
        failure_rate = sum(item.failure_history) / len(item.failure_history)
        return 1.0 - failure_rate

    @staticmethod
    def _terminal_decision(
        item: WorkItem,
        candidates: tuple[CandidateValue, ...],
        assumptions: dict,
        route: Route,
        reason_code: str,
        reason: str,
    ) -> RouteDecision:
        return RouteDecision(
            work_item_id=item.work_item_id,
            route=route,
            selected_handler=None,
            expected_benefit=item.expected_benefit,
            expected_cost=0.0,
            expected_net_value=None,
            reason_code=reason_code,
            reason=reason,
            input_sha256=item.input_sha256,
            candidate_values=candidates,
            resource_assumptions=assumptions,
            receipt_sha256="",
        )
