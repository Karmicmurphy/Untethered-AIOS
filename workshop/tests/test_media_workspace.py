import base64
import json
import sqlite3

import pytest

from companion.media_workspace import MediaWorkspace, MediaWorkspaceError


PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")


def workspace(tmp_path):
    db = tmp_path / "workshop.sqlite3"
    con = sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE projects(id TEXT PRIMARY KEY,title TEXT,description TEXT,next_action TEXT,created_at TEXT,updated_at TEXT);
    CREATE TABLE artifacts(id TEXT PRIMARY KEY,project_id TEXT,kind TEXT,title TEXT,path TEXT,payload TEXT,authority_state TEXT,sha256 TEXT,created_at TEXT,updated_at TEXT);
    CREATE VIRTUAL TABLE artifact_search USING fts5(id UNINDEXED,project_id UNINDEXED,title,kind,content);
    CREATE TABLE receipts(id TEXT PRIMARY KEY,project_id TEXT,action TEXT,actor TEXT,details TEXT,created_at TEXT);
    CREATE TABLE artifact_relationships(id TEXT PRIMARY KEY,source_artifact_id TEXT,target_artifact_id TEXT,project_id TEXT,relationship_type TEXT,lifecycle_id TEXT,status TEXT,created_at TEXT,updated_at TEXT);
    INSERT INTO projects VALUES('p1','Project','','','','');
    """)
    con.commit(); con.close()
    contract = tmp_path / "contract.json"
    contract.write_text(json.dumps({"schemaVersion":"twis-media-capability-registry-v1"}), encoding="utf-8")
    return MediaWorkspace(db, tmp_path / "projects", contract), db


def test_content_addressed_asset_scene_route_and_storyboard(tmp_path):
    media, db = workspace(tmp_path)
    first = media.save_image("p1", "Frame", "image/png", PNG, 1, 1)["artifact"]
    second = media.save_image("p1", "Frame copy", "image/png", PNG, 1, 1)["artifact"]
    assert first["sha256"] == second["sha256"]
    assert first["path"] == second["path"]
    assert media.asset(first["id"])[0].read_bytes() == PNG
    scene = media.create_scene("p1", "Arrival", "Quiet water")["artifact"]
    route = media.create_route("p1", first["id"], "music", scene["id"])["artifact"]
    board = media.create_storyboard_item("p1", scene["id"], first["id"], 3.5, "slow dissolve")["artifact"]
    assert route["payload"]["sourceSha256"] == first["sha256"]
    assert board["payload"]["durationSeconds"] == 3.5
    summary = media.summary("p1")
    assert {x["kind"] for x in summary["items"]} >= {"image", "scene", "media-route", "storyboard-item"}
    con = sqlite3.connect(db)
    assert con.execute("select count(*) from receipts").fetchone()[0] == 5
    assert con.execute("select count(*) from artifact_relationships").fetchone()[0] == 4


def test_media_workspace_rejects_unregistered_sources_and_unsupported_bytes(tmp_path):
    media, _ = workspace(tmp_path)
    with pytest.raises(MediaWorkspaceError):
        media.save_image("p1", "bad", "image/png", b"not-image", 1, 1)
    with pytest.raises(MediaWorkspaceError):
        media.create_route("p1", "missing", "video")
    with pytest.raises(MediaWorkspaceError):
        media.create_route("p1", "missing", "internet")
    with pytest.raises(MediaWorkspaceError):
        media.save_image("unregistered", "Frame", "image/png", PNG, 1, 1)
    assert not (tmp_path / "projects" / "unregistered").exists()


def test_image_variation_retains_source_provenance_and_blocks_changed_source(tmp_path):
    media, db = workspace(tmp_path)
    original_hash = "a" * 64
    source = media.save_image("p1", "Source", "image/png", PNG, 1, 1, original_sha256=original_hash)["artifact"]
    source_path = media.asset(source["id"])[0]
    source_bytes = source_path.read_bytes()
    variation = media.save_image("p1", "Variation", "image/png", PNG, 1, 1, source["id"], original_hash)["artifact"]
    assert variation["payload"]["provenance"] == {
        "origin": "owner-canvas-variation",
        "sourceArtifactIds": [source["id"]],
        "sourceHashes": [source["sha256"]],
        "originalInputSha256": original_hash,
    }
    assert source_path.read_bytes() == source_bytes
    con = sqlite3.connect(db)
    relationship = con.execute("select relationship_type from artifact_relationships where source_artifact_id=? and target_artifact_id=?", (source["id"], variation["id"])).fetchone()
    assert relationship == ("image-variation",)
    source_path.write_bytes(PNG + b"changed")
    with pytest.raises(MediaWorkspaceError, match="changed"):
        media.save_image("p1", "Blocked", "image/png", PNG, 1, 1, source["id"], original_hash)
    with pytest.raises(MediaWorkspaceError, match="changed"):
        media.asset(source["id"])


def test_storyboard_reorder_and_remove_preserve_source_image(tmp_path):
    media, db = workspace(tmp_path)
    image = media.save_image("p1", "Frame", "image/png", PNG, 1, 1)["artifact"]
    image_path = media.asset(image["id"])[0]
    scene = media.create_scene("p1", "Sequence")["artifact"]
    first = media.create_storyboard_item("p1", scene["id"], image["id"], 2, "cut")["artifact"]
    second = media.create_storyboard_item("p1", scene["id"], image["id"], 3, "dissolve")["artifact"]
    changed = media.reorder_storyboard_item("p1", second["id"], "earlier")
    assert changed["changed"] is True
    ordered = sorted((item for item in media.summary("p1")["items"] if item["kind"] == "storyboard-item"), key=lambda item: item["payload"]["order"])
    assert [item["id"] for item in ordered] == [second["id"], first["id"]]
    removed = media.remove_storyboard_item("p1", first["id"])
    assert removed["sourcePreserved"] is True
    assert image_path.read_bytes() == PNG
    con = sqlite3.connect(db)
    assert con.execute("select count(*) from artifacts where id=?", (first["id"],)).fetchone()[0] == 0
    assert con.execute("select count(*) from artifacts where id=?", (image["id"],)).fetchone()[0] == 1
    assert {row[0] for row in con.execute("select action from receipts")} >= {"media.storyboard.reordered", "media.storyboard.removed"}


def test_background_composite_is_owner_approved_inactive_and_retains_all_sources(tmp_path):
    media, db = workspace(tmp_path)
    foreground = media.save_image("p1", "Transparent foreground", "image/png", PNG, 1, 1)["artifact"]
    backdrop = media.save_image("p1", "Registered backdrop", "image/png", PNG, 1, 1)["artifact"]
    foreground_bytes = media.asset(foreground["id"])[0].read_bytes()
    backdrop_bytes = media.asset(backdrop["id"])[0].read_bytes()

    result = media.save_background_composite(
        "p1", "Approved composite", PNG, 1, 1,
        foreground["id"], foreground["sha256"], "image",
        background_artifact_id=backdrop["id"], expected_background_sha256=backdrop["sha256"],
    )["artifact"]

    provenance = result["payload"]["provenance"]
    assert result["payload"]["status"] == "inactive-draft"
    assert provenance["origin"] == "owner-approved-background-composition"
    assert provenance["sourceArtifactIds"] == [foreground["id"], backdrop["id"]]
    assert provenance["sourceHashes"] == [foreground["sha256"], backdrop["sha256"]]
    assert provenance["operation"] == {
        "schemaVersion": "twis-background-composition-v1",
        "kind": "background-composition",
        "mode": "image",
        "colorA": None,
        "colorB": None,
        "direction": None,
        "backgroundArtifactId": backdrop["id"],
        "backgroundSha256": backdrop["sha256"],
        "engine": "browser-canvas-2d",
        "proposalApproved": True,
        "sourcePreserved": True,
    }
    assert media.asset(foreground["id"])[0].read_bytes() == foreground_bytes
    assert media.asset(backdrop["id"])[0].read_bytes() == backdrop_bytes
    con = sqlite3.connect(db)
    relationships = set(con.execute("select source_artifact_id,relationship_type from artifact_relationships where target_artifact_id=?", (result["id"],)))
    assert relationships == {
        (foreground["id"], "background-composition-foreground"),
        (backdrop["id"], "background-composition-backdrop"),
    }
    assert con.execute("select count(*) from receipts where action='media.background-composition.approved'").fetchone()[0] == 1


def test_background_composite_blocks_stale_or_invalid_sources(tmp_path):
    media, _ = workspace(tmp_path)
    foreground = media.save_image("p1", "Foreground", "image/png", PNG, 1, 1)["artifact"]
    backdrop = media.save_image("p1", "Backdrop", "image/png", PNG, 1, 1)["artifact"]
    with pytest.raises(MediaWorkspaceError, match="source hash changed"):
        media.save_background_composite("p1", "Stale", PNG, 1, 1, foreground["id"], "0" * 64, "solid", "#123456")
    with pytest.raises(MediaWorkspaceError, match="background hash changed"):
        media.save_background_composite("p1", "Stale background", PNG, 1, 1, foreground["id"], foreground["sha256"], "image", background_artifact_id=backdrop["id"], expected_background_sha256="0" * 64)
    with pytest.raises(MediaWorkspaceError, match="different registered image"):
        media.save_background_composite("p1", "Same source", PNG, 1, 1, foreground["id"], foreground["sha256"], "image", background_artifact_id=foreground["id"], expected_background_sha256=foreground["sha256"])
    with pytest.raises(MediaWorkspaceError, match="valid primary"):
        media.save_background_composite("p1", "Invalid color", PNG, 1, 1, foreground["id"], foreground["sha256"], "solid", "not-a-color")
