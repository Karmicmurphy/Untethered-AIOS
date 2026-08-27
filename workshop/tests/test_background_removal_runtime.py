from __future__ import annotations

import hashlib
import json
import sqlite3
import struct
import zlib
from pathlib import Path

import pytest

from companion.background_removal_runtime import BackgroundRemovalError, BackgroundRemovalRuntime
from companion.media_workspace import MediaWorkspace


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = ROOT.parent / "runtime"
RUNTIME_CONFIG = ROOT / "config" / "background-removal-runtime.json"


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def synthetic_png(width: int = 128, height: int = 96) -> bytes:
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            inside = 34 <= x < 94 and 18 <= y < 80
            row.extend((232, 72, 48) if inside else (24, 150, 210))
        rows.append(bytes(row))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(b"".join(rows), 6)) + _chunk(b"IEND", b"")


def workspace(tmp_path: Path) -> tuple[BackgroundRemovalRuntime, MediaWorkspace, Path]:
    database = tmp_path / "workshop.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE projects(id TEXT PRIMARY KEY,title TEXT,description TEXT,next_action TEXT,created_at TEXT,updated_at TEXT);
            CREATE TABLE artifacts(id TEXT PRIMARY KEY,project_id TEXT,kind TEXT,title TEXT,path TEXT,payload TEXT,authority_state TEXT,sha256 TEXT,created_at TEXT,updated_at TEXT);
            CREATE VIRTUAL TABLE artifact_search USING fts5(id UNINDEXED,project_id UNINDEXED,title,kind,content);
            CREATE TABLE receipts(id TEXT PRIMARY KEY,project_id TEXT,action TEXT,actor TEXT,details TEXT,created_at TEXT);
            CREATE TABLE artifact_relationships(id TEXT PRIMARY KEY,source_artifact_id TEXT,target_artifact_id TEXT,project_id TEXT,relationship_type TEXT,lifecycle_id TEXT,status TEXT,created_at TEXT,updated_at TEXT);
            INSERT INTO projects VALUES('p1','Background removal fixture','','','','');
            PRAGMA user_version=13;
            """
        )
    contract = tmp_path / "media-capabilities.json"
    contract.write_text(json.dumps({"schemaVersion": "twis-media-capability-registry-v1"}), encoding="utf-8")
    projects = tmp_path / "projects"
    media = MediaWorkspace(database, projects, contract)
    service = BackgroundRemovalRuntime(database, projects, RUNTIME_ROOT, RUNTIME_CONFIG, media)
    return service, media, database


def registered_source(media: MediaWorkspace) -> tuple[dict, Path, bytes]:
    raw = synthetic_png()
    artifact = media.save_image("p1", "Synthetic foreground", "image/png", raw, 128, 96)["artifact"]
    path = media.asset(artifact["id"])[0]
    return artifact, path, raw


def proposal(service: BackgroundRemovalRuntime, source: dict) -> dict:
    return service.create_proposal(
        "p1",
        {
            "sourceArtifactId": source["id"],
            "sourceSha256": source["sha256"],
            "rectangle": {"x": 0.18, "y": 0.08, "width": 0.64, "height": 0.86},
            "strokes": [{"mode": "keep", "x": 0.5, "y": 0.5, "radius": 0.025}],
        },
    )


def test_registered_runtime_health_is_real_local_and_hash_verified(tmp_path: Path):
    service, _, _ = workspace(tmp_path)
    result = service.health(verify_files=True)
    assert result["state"] == "HEALTHY"
    assert result["opencvVersion"] == "4.14.0"
    assert result["runtimeFiles"] == 1033
    assert result["runtimeBytes"] == 157_640_551
    assert result["hashVerified"] is True
    assert result["network"] == "none"
    assert result["persistentProcess"] is False


def test_proposal_approval_saves_inactive_derived_image_and_preserves_source(tmp_path: Path):
    service, media, database = workspace(tmp_path)
    source, source_path, source_bytes = registered_source(media)
    created = proposal(service, source)
    item = created["proposal"]
    assert item["state"] == "PROPOSED"
    assert item["automaticSave"] is False
    assert 0 < item["metrics"]["foregroundRatio"] < 1
    assert service.preview("p1", item["proposalId"]).read_bytes().startswith(b"\x89PNG")
    assert service.list_proposals("p1")["proposals"][0]["proposalId"] == item["proposalId"]
    assert source_path.read_bytes() == source_bytes

    approved = service.decide("p1", item["proposalId"], "approve", "Approved synthetic cutout")
    artifact = approved["artifact"]
    assert approved["inactiveDraft"] is True
    assert artifact["payload"]["status"] == "inactive-draft"
    assert artifact["payload"]["provenance"]["origin"] == "opencv-grabcut-assisted-cutout"
    assert artifact["payload"]["provenance"]["sourceArtifactIds"] == [source["id"]]
    assert artifact["payload"]["provenance"]["sourceHashes"] == [source["sha256"]]
    assert source_path.read_bytes() == source_bytes
    assert service.list_proposals("p1")["proposals"] == []

    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 13
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        relationship = connection.execute(
            "SELECT relationship_type FROM artifact_relationships WHERE source_artifact_id=? AND target_artifact_id=?",
            (source["id"], artifact["id"]),
        ).fetchone()
        assert relationship == ("background-removal-variation",)
        assert connection.execute("SELECT authority_state FROM artifacts WHERE id=?", (artifact["id"],)).fetchone() == ("DRAFT",)
        actions = {row[0] for row in connection.execute("SELECT action FROM receipts")}
        assert {"media.background-removal.proposed", "media.background-removal.asset-saved", "media.background-removal.approved"} <= actions


def test_reject_is_non_mutating_and_stale_source_blocks_approval(tmp_path: Path):
    service, media, database = workspace(tmp_path)
    source, source_path, source_bytes = registered_source(media)
    rejected = proposal(service, source)["proposal"]
    with sqlite3.connect(database) as connection:
        before = connection.execute("SELECT count(*) FROM artifacts").fetchone()[0]
    result = service.decide("p1", rejected["proposalId"], "reject")
    assert result["decision"] == "rejected" and result["sourcePreserved"] is True
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT count(*) FROM artifacts").fetchone()[0] == before
    assert source_path.read_bytes() == source_bytes

    pending = proposal(service, source)["proposal"]
    source_path.write_bytes(source_bytes + b"out-of-band-change")
    try:
        with pytest.raises(BackgroundRemovalError) as error:
            service.decide("p1", pending["proposalId"], "approve")
        assert error.value.code == "source_stale" and error.value.status == 409
        assert service.list_proposals("p1")["proposals"][0]["proposalId"] == pending["proposalId"]
    finally:
        source_path.write_bytes(source_bytes)
        service.decide("p1", pending["proposalId"], "reject")


def test_manifest_mismatch_and_arbitrary_source_inputs_fail_closed(tmp_path: Path):
    service, media, _ = workspace(tmp_path)
    source, _, _ = registered_source(media)
    config = json.loads(RUNTIME_CONFIG.read_text(encoding="utf-8"))
    config["manifestSha256"] = "0" * 64
    invalid_config = tmp_path / "invalid-runtime.json"
    invalid_config.write_text(json.dumps(config), encoding="utf-8")
    invalid = BackgroundRemovalRuntime(service.database, service.projects, RUNTIME_ROOT, invalid_config, media)
    with pytest.raises(BackgroundRemovalError) as error:
        invalid.health(verify_files=True)
    assert error.value.code == "runtime_manifest_mismatch"

    with pytest.raises(BackgroundRemovalError) as unregistered:
        service.create_proposal(
            "p1",
            {
                "sourceArtifactId": str(tmp_path / "outside.png"),
                "sourceSha256": hashlib.sha256(b"outside").hexdigest(),
                "rectangle": {"x": 0.1, "y": 0.1, "width": 0.8, "height": 0.8},
                "command": "whoami",
            },
        )
    assert unregistered.value.code == "source_invalid"
    assert source["id"]
