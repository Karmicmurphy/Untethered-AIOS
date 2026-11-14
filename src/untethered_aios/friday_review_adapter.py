"""Review-only FRIDAY read-only capability adapter.

This module is not wired to any live endpoint. The existing AIOS registry
is the only capability enforcement implementation used here.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Callable

from untethered_aios.capabilities import CapabilityGrant, CapabilityRegistry

TASKS = ("windows-inventory", "workshop-health")
SCOPES = {"windows-inventory": "read:inventory", "workshop-health": "read:health"}


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def make_registry(inventory: Callable[[], dict[str, Any]],
                  health: Callable[[], dict[str, Any]]) -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register("windows-inventory", inventory)
    registry.register("workshop-health", health)
    return registry


def run_approved_readonly(request: dict[str, Any], *,
                          registry: CapabilityRegistry,
                          grant: CapabilityGrant) -> dict[str, Any]:
    if not isinstance(request, dict) or set(request) != {"action", "request_id"}:
        raise ValueError("invalid request shape")
    action, request_id = request["action"], request["request_id"]
    if not isinstance(action, str) or action not in TASKS:
        raise ValueError("unapproved task")
    if not isinstance(request_id, str) or len(request_id) != 32 or any(
        c not in "0123456789abcdef" for c in request_id
    ):
        raise ValueError("invalid request id")
    if not isinstance(grant, CapabilityGrant) or grant.name != action or SCOPES[action] not in grant.scopes:
        raise ValueError("missing exact read-only grant")
    # The AIOS registry checks capability grants; the adapter also checks
    # semantic scope because the current registry only enforces path scopes
    # when scope_arg is supplied.
    result = registry.invoke(action, {}, (grant,))
    if not isinstance(result, dict):
        raise ValueError("invalid capability output")
    payload = {"ok": True, "status": "COMPLETE", "task": action,
               "job_id": f"friday:{action}:{request_id}",
               "output": result, "files_modified": False,
               "activation_performed": False}
    payload["receipt_sha256"] = _digest(payload)
    return payload
