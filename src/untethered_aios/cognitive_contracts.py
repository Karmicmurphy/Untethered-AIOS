from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any

from .audit import hash_value


class Route(str, Enum):
    IGNORE = "IGNORE"
    DEFER = "DEFER"
    REFLEX = "REFLEX"
    RULE = "RULE"
    WORKER = "WORKER"
    CENTRAL_AI = "CENTRAL_AI"
    OWNER_GATE = "OWNER_GATE"


EXECUTION_ROUTES = frozenset(
    {Route.REFLEX, Route.RULE, Route.WORKER, Route.CENTRAL_AI}
)


def _probability(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")


@dataclass(frozen=True)
class RouteEstimate:
    """One available execution mechanism measured in common utility units."""

    route: Route
    handler_id: str
    estimated_cost: float
    success_probability: float
    cpu_ms: int
    memory_mb: float
    deterministic: bool

    def __post_init__(self) -> None:
        if self.route not in EXECUTION_ROUTES:
            raise ValueError("route estimate must name an execution route")
        if not self.handler_id:
            raise ValueError("handler_id is required")
        if self.estimated_cost < 0:
            raise ValueError("estimated_cost cannot be negative")
        _probability("success_probability", self.success_probability)
        if self.cpu_ms < 0 or self.memory_mb < 0:
            raise ValueError("resource estimates cannot be negative")


@dataclass(frozen=True)
class WorkItem:
    """Bounded, observable routing input; it contains no executable authority."""

    work_item_id: str
    task_class: str
    urgency: float
    owner_priority: float
    novelty: float
    uncertainty: float
    risk: float
    expected_benefit: float
    cpu_budget_ms: int
    available_memory_mb: float
    memory_pressure: float
    failure_history: tuple[bool, ...] = ()  # True means the attempt failed.
    route_estimates: tuple[RouteEstimate, ...] = ()
    protected_operation: bool = False

    def __post_init__(self) -> None:
        if not self.work_item_id or not self.task_class:
            raise ValueError("work_item_id and task_class are required")
        for name in (
            "urgency",
            "owner_priority",
            "novelty",
            "uncertainty",
            "risk",
            "memory_pressure",
        ):
            _probability(name, getattr(self, name))
        if self.expected_benefit < 0:
            raise ValueError("expected_benefit cannot be negative")
        if self.cpu_budget_ms < 0 or self.available_memory_mb < 0:
            raise ValueError("resource budgets cannot be negative")
        routes = [estimate.route for estimate in self.route_estimates]
        if len(routes) != len(set(routes)):
            raise ValueError("only one estimate per execution route is allowed")

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for estimate in value["route_estimates"]:
            estimate["route"] = estimate["route"].value
        return value

    @property
    def input_sha256(self) -> str:
        return hash_value(self.as_dict())


@dataclass(frozen=True)
class CandidateValue:
    route: Route
    handler_id: str
    eligible: bool
    expected_benefit: float
    expected_cost: float
    expected_net_value: float | None
    success_probability: float
    reason: str
    cpu_ms: int
    memory_mb: float

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["route"] = self.route.value
        return value


@dataclass(frozen=True)
class RouteDecision:
    work_item_id: str
    route: Route
    selected_handler: str | None
    expected_benefit: float
    expected_cost: float
    expected_net_value: float | None
    reason_code: str
    reason: str
    input_sha256: str
    candidate_values: tuple[CandidateValue, ...]
    resource_assumptions: dict[str, Any]
    receipt_sha256: str

    def as_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["route"] = self.route.value
        value["candidate_values"] = [
            candidate.as_dict() for candidate in self.candidate_values
        ]
        return value
