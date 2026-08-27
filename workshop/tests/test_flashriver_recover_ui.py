from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SHA = "6ef7317722202769b08d74a434519871736e055d1864fa5eb6c6fb547cb40108"


def test_recover_room_has_flashriver_controls():
    html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    assert 'id="flashriverPath"' in html
    assert 'id="flashriverSha"' in html
    assert 'id="importFlashriver"' in html
    assert 'id="reviewFlashriver"' in html
    assert 'id="flashriverResult"' in html
    assert EXPECTED_SHA in html


def test_missing_app_ids_are_present():
    html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    assert 'id="micBtn"' in html
    assert 'id="exportProject"' in html


def test_flashriver_ui_script_is_loaded_and_posts_to_route():
    html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    script = (ROOT / "app" / "assets" / "flashriver-import-ui.js").read_text(encoding="utf-8")
    assert "assets/flashriver-import-ui.js" in html
    assert "/api/import-flashriver" in script
    assert "expectedSha256" in script
    assert "FlashRiver package imported" in script


def test_my_work_has_flashriver_filters():
    html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    assert 'value="flashriver-intake-manifest"' in html
    assert 'value="flashriver-core-doc"' in html
    assert 'value="flashriver-support-doc"' in html


def test_flashriver_import_uses_dedicated_project_and_review_shows_all():
    script = (ROOT / "app" / "assets" / "flashriver-import-ui.js").read_text(encoding="utf-8")
    app = (ROOT / "app" / "assets" / "app.js").read_text(encoding="utf-8")
    assert 'FLASHRIVER_PROJECT_ID = "flashriver-source-archive"' in script
    assert 'projectId: FLASHRIVER_PROJECT_ID' in script
    assert 'twis:select-project' in script
    assert 'twis:select-project' in app
    assert 'showAll: true' in script

def test_my_work_has_private_source_and_visual_filters():
    html = (ROOT / "app" / "index.html").read_text(encoding="utf-8")
    assert 'value="flashriver-private-source"' in html
    assert 'value="flashriver-visual"' in html
