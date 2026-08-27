from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_modules_room_exposes_separate_guarded_lifecycle_actions() -> None:
    html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "app" / "assets" / "worker-harness.js").read_text(encoding="utf-8")
    view = (ROOT / "app" / "assets" / "worker-harness-view.js").read_text(encoding="utf-8")
    app = (ROOT / "app" / "assets" / "app.js").read_text(encoding="utf-8")
    assert "Guarded Worker Harness" in html
    assert "Foundation 0.5 - owner-truth control panel" in html
    assert "Human actor assertion (not authenticated)" in html
    assert "Create execution plan" in html
    assert "Run planned worker" in html
    assert "Explicit hash + generation required" in html
    assert 'id="workerLifecycleOverview"' in html
    assert 'id="workerActionLog"' in html
    assert "twis:modules-open" in app
    for endpoint in (
        "/api/workers",
        "/api/candidates",
        "/plan",
        "/run",
    ):
        assert endpoint in script
    assert "/api/candidates/${candidateId}/${action}" in script
    for action in ("approve", "reject", "activate", "rollback"):
        assert f'{action}:' in script
    assert "candidateHash" in script
    assert "workspaceGeneration" in script
    assert "view.validActions(candidate.lifecycle_state)" in script
    assert "view.isCurrentPlan(currentPlan, currentSelection())" in script
    assert "approval_note_required" in script
    assert "Heuristic - not established fact" in view
    assert "executes_on_startup" not in script  # server evidence, not a UI claim derived client-side
    assert "faultMode" not in script


def test_worker_ui_is_versioned_in_service_worker_and_api_is_never_cached() -> None:
    service_worker = (ROOT / "app" / "service-worker.js").read_text(encoding="utf-8")
    assert 'const C="twis-holo-full-v27-music-loop-deck-v1"' in service_worker
    assert '"./assets/worker-harness-view.js"' in service_worker
    assert '"./assets/worker-harness.js"' in service_worker
    assert 'url.pathname.startsWith("/api/")' in service_worker


def test_server_declares_fixed_scope_and_no_live_worker_tables() -> None:
    server = (ROOT / "companion" / "server.py").read_text(encoding="utf-8")
    harness = (ROOT / "companion" / "foundation" / "worker_harness.py").read_text(encoding="utf-8")
    assert '"release": "0.5.0"' in server
    assert '"arbitraryWorkers": False' in server
    assert '"automaticActivation": False' in server
    assert 'allow_test_faults=False' in server
    assert '"card": supplied' in harness
    assert '"worker_card_hash": hash_json(supplied)' in harness
    assert 'PromotionError("approval_note_required"' in harness
    assert "CREATE TABLE IF NOT EXISTS workers" not in server
    assert "CREATE TABLE IF NOT EXISTS candidates" not in server


def test_modules_room_exposes_artifact_selection_and_hash_bound_attachment() -> None:
    html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "app" / "assets" / "worker-harness.js").read_text(encoding="utf-8")
    view = (ROOT / "app" / "assets" / "worker-harness-view.js").read_text(encoding="utf-8")
    assert "Artifact Compass Inspection" in html
    assert "Explicit public-safe artifact" in html
    assert "Ineligible artifacts and reasons" in html
    assert "Title and distinct path" in script
    assert "Source-hash mismatches" in script
    assert "Worker Card summary" in html
    assert "Execution-plan authority" in html
    assert "Readable provenance and receipts" in script
    assert "Attachment rolled back; history preserved" in view
    assert "Attach approved report" in script
    assert "/api/artifacts/inspection-options" in script
    for binding in ("sourceArtifactHash", "workerCardHash", "executionPlanHash"):
        assert binding in script
    assert "escapeHtml(JSON.stringify(output, null, 2))" in script
    assert "faultMode" not in script


def test_owner_truth_ui_keeps_raw_evidence_and_escapes_rendered_content() -> None:
    html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "app" / "assets" / "worker-harness.js").read_text(encoding="utf-8")
    view = (ROOT / "app" / "assets" / "worker-harness-view.js").read_text(encoding="utf-8")
    for identifier in (
        "workerCardOutput",
        "workerPlanOutput",
        "workerCardTechnical",
        "workerPlanDetails",
    ):
        assert f'id="{identifier}"' in html
    assert 'textContent = JSON.stringify(validation.card, null, 2)' in script
    assert 'textContent = JSON.stringify(plan, null, 2)' in script
    assert "escapeHtml(JSON.stringify(output, null, 2))" in script
    assert "replace(/[&<>\"']/g" in view
    assert "Hashes show byte equality. They are not signatures." in script
