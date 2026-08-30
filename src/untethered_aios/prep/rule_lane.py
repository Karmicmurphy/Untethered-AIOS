from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Callable

_RULE_ID = re.compile(r"^[a-z][a-z0-9-]{0,63}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")

class RuleError(RuntimeError):
    pass
class NoRuleMatch(RuleError):
    pass
class RuleConflict(RuleError):
    pass

def stable_hash(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

Predicate = Callable[[dict[str, Any]], bool]
Action = Callable[[dict[str, Any]], dict[str, Any]]

@dataclass(frozen=True)
class RuleSpec:
    rule_id: str
    version: str
    task_class: str
    predicate_name: str
    action_name: str
    required_capabilities: tuple[str, ...]
    input_contract: dict[str, Any]
    output_contract: dict[str, Any]
    dependency_identity: str
    dependency_sha256: str
    expected_cost_units: float = 0.05
    priority: int = 0

    def __post_init__(self) -> None:
        if not _RULE_ID.fullmatch(self.rule_id):
            raise ValueError("rule_id must be a stable lowercase identifier")
        if not self.version or not self.task_class:
            raise ValueError("version and task_class are required")
        if not self.predicate_name or not self.action_name:
            raise ValueError("predicate_name and action_name are required")
        if not _SHA256.fullmatch(self.dependency_sha256):
            raise ValueError("dependency_sha256 must be a lowercase SHA-256 digest")
        if self.expected_cost_units < 0:
            raise ValueError("expected_cost_units cannot be negative")
        if len(set(self.required_capabilities)) != len(self.required_capabilities):
            raise ValueError("required_capabilities must not contain duplicates")

    @property
    def contract_sha256(self) -> str:
        return stable_hash({
            "rule_id": self.rule_id,
            "version": self.version,
            "task_class": self.task_class,
            "predicate_name": self.predicate_name,
            "action_name": self.action_name,
            "required_capabilities": self.required_capabilities,
            "input_contract": self.input_contract,
            "output_contract": self.output_contract,
            "dependency_identity": self.dependency_identity,
            "dependency_sha256": self.dependency_sha256,
            "expected_cost_units": self.expected_cost_units,
            "priority": self.priority,
        })

@dataclass(frozen=True)
class RuleMatch:
    spec: RuleSpec
    result: dict[str, Any]

class RuleRegistry:
    """Deterministic rule registry. It contains no authority or side-effect grants."""
    def __init__(self) -> None:
        self._rules: dict[str, tuple[RuleSpec, Predicate, Action]] = {}
        self._execution_counts: dict[str, int] = {}

    def register(self, spec: RuleSpec, predicate: Predicate, action: Action) -> None:
        if spec.rule_id in self._rules:
            raise ValueError(f"rule already registered: {spec.rule_id}")
        self._rules[spec.rule_id] = (spec, predicate, action)
        self._execution_counts[spec.rule_id] = 0

    def specs(self) -> tuple[RuleSpec, ...]:
        return tuple(sorted((row[0] for row in self._rules.values()), key=lambda s: s.rule_id))

    def resolve(self, task_class: str, payload: dict[str, Any]) -> RuleSpec:
        candidates: list[RuleSpec] = []
        for spec, predicate, _ in self._rules.values():
            if spec.task_class != task_class:
                continue
            try:
                matched = bool(predicate(payload))
            except Exception as exc:
                raise RuleError(f"rule predicate failed closed: {spec.rule_id}: {exc}") from exc
            if matched:
                candidates.append(spec)
        if not candidates:
            raise NoRuleMatch(f"no deterministic rule matched task class {task_class}")
        highest = max(spec.priority for spec in candidates)
        winners = sorted((spec for spec in candidates if spec.priority == highest), key=lambda s: s.rule_id)
        if len(winners) != 1:
            raise RuleConflict("equally authoritative matching rules fail closed: " + ", ".join(spec.rule_id for spec in winners))
        return winners[0]

    def execute(self, task_class: str, payload: dict[str, Any]) -> RuleMatch:
        spec = self.resolve(task_class, payload)
        _, _, action = self._rules[spec.rule_id]
        try:
            result = action(payload)
        except Exception as exc:
            raise RuleError(f"rule action failed closed: {spec.rule_id}: {exc}") from exc
        if not isinstance(result, dict):
            raise RuleError("rule action must return a dictionary result")
        self._execution_counts[spec.rule_id] += 1
        return RuleMatch(spec=spec, result=result)

    def execution_count(self, rule_id: str) -> int:
        return self._execution_counts.get(rule_id, 0)

DEFAULT_RULE_ID = "read-only-policy-v1"
DEFAULT_RULE_HANDLER_ID = "rule-policy-triage-v1"
DEFAULT_RULE_TASK_CLASS = "request.policy.classify"

def _validate_policy_payload(payload: dict[str, Any]) -> None:
    required = {"operation", "mutating", "publishing", "spending", "credential_change", "authority_change"}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ValueError("policy payload must contain exactly the six policy fields")
    if not isinstance(payload["operation"], str) or not payload["operation"]:
        raise ValueError("operation must be a non-empty string")
    for key in required - {"operation"}:
        if not isinstance(payload[key], bool):
            raise ValueError(f"{key} must be boolean")

def read_only_predicate(payload: dict[str, Any]) -> bool:
    _validate_policy_payload(payload)
    if payload["operation"] not in {"inspect", "read", "list", "search", "summarize"}:
        return False
    return not any(payload[key] for key in ("mutating", "publishing", "spending", "credential_change", "authority_change"))

def read_only_action(payload: dict[str, Any]) -> dict[str, Any]:
    _validate_policy_payload(payload)
    return {"policy_class": "READ_ONLY_SAFE", "requires_owner_gate": False, "operation": payload["operation"]}

def build_default_rule_registry() -> RuleRegistry:
    registry = RuleRegistry()
    dependency_identity = "twis-native-policy:read-only-safe"
    dependency_sha256 = stable_hash({
        "identity": dependency_identity,
        "version": "1.0.0",
        "allowed_operations": ["inspect", "list", "read", "search", "summarize"],
        "protected_flags": ["mutating", "publishing", "spending", "credential_change", "authority_change"],
    })
    spec = RuleSpec(
        rule_id=DEFAULT_RULE_ID,
        version="1.0.0",
        task_class=DEFAULT_RULE_TASK_CLASS,
        predicate_name="read_only_predicate",
        action_name="read_only_action",
        required_capabilities=("cheap.handler.execute",),
        input_contract={"type": "object", "required": ["operation", "mutating", "publishing", "spending", "credential_change", "authority_change"], "additionalProperties": False},
        output_contract={"type": "object", "required": ["policy_class", "requires_owner_gate", "operation"], "additionalProperties": False},
        dependency_identity=dependency_identity,
        dependency_sha256=dependency_sha256,
        expected_cost_units=0.05,
        priority=10,
    )
    registry.register(spec, read_only_predicate, read_only_action)
    return registry

def install_default_rule_handler(cheap_registry: Any) -> RuleRegistry:
    """Integration hook for the verified cheap-handler lane.

    Codex must review/adapt this hook against the latest local Campaign-3 budgeted
    handler signature before promotion.
    """
    from untethered_aios.audit import hash_value
    from untethered_aios.capabilities import CapabilityGrant
    from untethered_aios.cognitive_contracts import Route
    from untethered_aios.reflex_execution import CHEAP_HANDLER_CAPABILITY, CheapHandlerSpec

    rules = build_default_rule_registry()
    rule_spec = rules.specs()[0]
    scope = f"handler:{DEFAULT_RULE_HANDLER_ID}"
    handler_spec = CheapHandlerSpec(
        handler_id=DEFAULT_RULE_HANDLER_ID,
        supported_task_class=DEFAULT_RULE_TASK_CLASS,
        required_capabilities=(CapabilityGrant(CHEAP_HANDLER_CAPABILITY, (scope,)),),
        input_contract=rule_spec.input_contract,
        output_contract=rule_spec.output_contract,
        deterministic=True,
        version=rule_spec.version,
        dependency_identity=rule_spec.dependency_identity,
        dependency_sha256=hash_value({"rule_contract": rule_spec.contract_sha256, "dependency": rule_spec.dependency_sha256}),
        expected_cost_units=rule_spec.expected_cost_units,
        route=Route.RULE,
        invalidation_rule="reuse only when rule handler/version/contract, selected rule, inputs, dependencies, prior proof, and stored result hash remain valid",
    )
    def handler(payload: dict[str, Any]) -> dict[str, Any]:
        match = rules.execute(DEFAULT_RULE_TASK_CLASS, payload)
        return {**match.result, "rule_id": match.spec.rule_id, "rule_version": match.spec.version, "rule_contract_sha256": match.spec.contract_sha256}
    cheap_registry.register(handler_spec, handler)
    return rules
