from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_review_view_is_wired():
    html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "assets" / "flashriver-review.js").read_text(encoding="utf-8")
    app = (ROOT / "app" / "assets" / "app.js").read_text(encoding="utf-8")
    navigation = (ROOT / "app" / "assets" / "navigation-state.js").read_text(encoding="utf-8")
    assert 'data-panel="flashriver-review"' in html
    assert 'assets/flashriver-review.js' in html
    assert '/flashriver-review' in js
    assert '/review' in js
    assert 'current_candidate' in js
    assert 'private_source' in js
    assert 'openReview' in app
    assert html.index('assets/navigation-state.js') < html.index('assets/app.js')
    assert 'resolveRoom' in navigation
    assert 'openRoom(restoredRoom)' in app


def test_review_api_and_schema_exist():
    server = (ROOT / "companion" / "server.py").read_text(encoding="utf-8")
    assert "CREATE TABLE IF NOT EXISTS artifact_reviews" in server
    assert 'endswith("/flashriver-review")' in server
    assert 'endswith("/review")' in server
    assert 'artifact.review' in server
    assert 'duplicate_artifact_groups' in server


def test_duplicate_group_ui_keeps_records_and_paths_visible():
    js = (ROOT / "app" / "assets" / "flashriver-review.js").read_text(encoding="utf-8")
    css = (ROOT / "app" / "assets" / "style.css").read_text(encoding="utf-8")
    assert "Exact duplicate group" in js
    assert "Every source record and every source path remains visible" in js
    assert "duplicate-paths" in js
    assert ".duplicate-paths" in css


def test_review_does_not_offer_promotion_or_execute_imported_instructions():
    html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    js = (ROOT / "app" / "assets" / "flashriver-review.js").read_text(encoding="utf-8")
    assert "Promote to Module" not in html
    assert "eval(" not in js
    assert "new Function" not in js
