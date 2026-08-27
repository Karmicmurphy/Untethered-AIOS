import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_worker_harness_schemas_are_closed_and_fixed_scope() -> None:
    plan = json.loads((ROOT / "schemas" / "execution-plan-v0.3.schema.json").read_text(encoding="utf-8"))
    candidate = json.loads((ROOT / "schemas" / "promotion-candidate-v0.3.schema.json").read_text(encoding="utf-8"))
    assert plan["additionalProperties"] is False
    assert plan["properties"]["worker_id"]["const"] == "reference-metadata-worker"
    assert plan["properties"]["auto_activate"]["const"] is False
    assert plan["properties"]["requested_permissions"]["properties"]["network"]["const"] is False
    assert candidate["properties"]["worker_id"]["const"] == "reference-metadata-worker"
    assert {"awaiting_approval", "approved", "active", "rolled_back"}.issubset(
        candidate["properties"]["lifecycle_state"]["enum"]
    )


def test_artifact_inspection_schemas_are_closed_bounded_and_fixed_scope() -> None:
    plan = json.loads((ROOT / "schemas" / "execution-plan-v0.4.schema.json").read_text(encoding="utf-8"))
    candidate = json.loads((ROOT / "schemas" / "promotion-candidate-v0.4.schema.json").read_text(encoding="utf-8"))
    output = json.loads((ROOT / "schemas" / "artifact-inspection-output-v0.4.schema.json").read_text(encoding="utf-8"))
    assert plan["additionalProperties"] is False
    assert plan["properties"]["worker_id"]["const"] == "artifact-compass-inspection-worker"
    assert plan["properties"]["max_input_bytes"]["const"] == 512 * 1024
    assert plan["properties"]["max_output_bytes"]["const"] == 128 * 1024
    assert plan["properties"]["requested_permissions"]["properties"]["read_only_source"]["const"] is True
    assert plan["properties"]["auto_activate"]["const"] is False
    assert candidate["additionalProperties"] is False
    assert candidate["properties"]["worker_id"]["const"] == "artifact-compass-inspection-worker"
    assert "source_artifact" in candidate["required"]
    assert "approval_binding" in candidate["required"]
    assert output["additionalProperties"] is False
    assert output["properties"]["likely_document_purpose"]["properties"]["classification"]["const"] == "heuristic_not_fact"
    assert output["properties"]["headings"]["$ref"] == "#/$defs/boundedObjects"
