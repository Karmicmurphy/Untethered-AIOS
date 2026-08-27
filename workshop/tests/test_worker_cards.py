from __future__ import annotations

import json
from pathlib import Path

from companion.foundation.worker_cards import (
    SUPPORTED_SCHEMA_VERSION,
    is_schema_compatible,
    load_worker_card,
    validate_worker_card,
)

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples" / "worker_cards"


def test_worker_card_schema_is_machine_readable_and_versioned() -> None:
    schema = json.loads((ROOT / "schemas" / "worker-card-v0.1.schema.json").read_text(encoding="utf-8"))
    assert schema["$schema"].endswith("2020-12/schema")
    assert schema["properties"]["schema_version"]["const"] == SUPPORTED_SCHEMA_VERSION
    assert schema["additionalProperties"] is False


def test_all_valid_examples_pass() -> None:
    valid_examples = sorted((EXAMPLES / "valid").glob("*.json"))
    assert valid_examples
    for path in valid_examples:
        card = load_worker_card(path)
        assert card["schema_version"] == SUPPORTED_SCHEMA_VERSION


def test_all_invalid_examples_fail() -> None:
    invalid_examples = sorted((EXAMPLES / "invalid").glob("*.json"))
    assert invalid_examples
    for path in invalid_examples:
        result = validate_worker_card(json.loads(path.read_text(encoding="utf-8")))
        assert not result.valid, path.name
        assert result.issues


def test_schema_compatibility_is_fail_closed() -> None:
    assert is_schema_compatible("0.1")
    assert not is_schema_compatible("0.0")
    assert not is_schema_compatible("0.2")
    assert not is_schema_compatible("1.0")


def test_shell_and_destructive_permissions_require_approval() -> None:
    card = json.loads((EXAMPLES / "valid" / "bounded-file-worker.json").read_text(encoding="utf-8"))
    card["shell_allowed"] = True
    card["destructive_actions_allowed"] = True
    result = validate_worker_card(card)
    codes = {(issue.path, issue.code) for issue in result.issues}
    assert ("approval_required", "permission_dependency") in codes


def test_network_permission_requires_approval() -> None:
    card = json.loads((EXAMPLES / "valid" / "bounded-file-worker.json").read_text(encoding="utf-8"))
    card["network_allowed"] = True
    result = validate_worker_card(card)
    assert any(issue.path == "approval_required" and issue.code == "permission_dependency" for issue in result.issues)


def test_allowed_and_blocked_root_contradiction_is_rejected() -> None:
    card = json.loads((EXAMPLES / "valid" / "bounded-file-worker.json").read_text(encoding="utf-8"))
    card["blocked_roots"] = [card["allowed_write_roots"][0].lower()]
    result = validate_worker_card(card)
    assert any(issue.code == "contradiction" for issue in result.issues)


def test_unknown_fields_are_rejected() -> None:
    card = json.loads((EXAMPLES / "valid" / "bounded-file-worker.json").read_text(encoding="utf-8"))
    card["pretend_host_enforced"] = True
    result = validate_worker_card(card)
    assert any(issue.path == "pretend_host_enforced" and issue.code == "unknown" for issue in result.issues)
