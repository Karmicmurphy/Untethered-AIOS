import hashlib
import json
import sqlite3
import struct
import wave
import zlib
from pathlib import Path

import pytest

from companion.video_workstation import VideoWorkstation, VideoWorkstationError


def png(width: int, height: int, rgb: tuple[int, int, int]) -> bytes:
    raw = b"".join(b"\x00" + bytes(rgb) * width for _ in range(height))
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def make_workspace(tmp_path: Path):
    database = tmp_path / "workshop.sqlite3"
    projects = tmp_path / "projects"
    root = projects / "p1"
    (root / "media" / "assets").mkdir(parents=True)
    (root / "exports" / "music").mkdir(parents=True)
    con = sqlite3.connect(database)
    con.executescript("""
    CREATE TABLE projects(id TEXT PRIMARY KEY,title TEXT,description TEXT,next_action TEXT,created_at TEXT,updated_at TEXT);
    CREATE TABLE artifacts(id TEXT PRIMARY KEY,project_id TEXT,kind TEXT,title TEXT,path TEXT,payload TEXT,authority_state TEXT,sha256 TEXT,created_at TEXT,updated_at TEXT);
    CREATE VIRTUAL TABLE artifact_search USING fts5(id UNINDEXED,project_id UNINDEXED,title,kind,content);
    CREATE TABLE receipts(id TEXT PRIMARY KEY,project_id TEXT,action TEXT,actor TEXT,details TEXT,created_at TEXT);
    CREATE TABLE artifact_relationships(id TEXT PRIMARY KEY,source_artifact_id TEXT,target_artifact_id TEXT,project_id TEXT,relationship_type TEXT,lifecycle_id TEXT,status TEXT,created_at TEXT,updated_at TEXT);
    INSERT INTO projects VALUES('p1','Video Test','','','','');
    """)
    originals = {}
    for index, color in enumerate(((190, 30, 50), (20, 155, 210), (210, 160, 20)), start=1):
        data = png(320, 180, color)
        digest = sha(data)
        relative = f"media/assets/{digest}.png"
        (root / relative).write_bytes(data)
        originals[f"image-{index}"] = data
        payload = {"schemaVersion": "twis-media-asset-v1", "mediaType": "image", "mimeType": "image/png", "width": 320, "height": 180, "size": len(data), "sha256": digest, "status": "inactive-draft"}
        con.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)", (f"image-{index}", "p1", "image", f"Frame {index}", relative, json.dumps(payload), "DRAFT", digest, "", ""))
    audio_path = root / "exports" / "music" / "test.wav"
    with wave.open(str(audio_path), "wb") as target:
        target.setnchannels(2); target.setsampwidth(2); target.setframerate(44100)
        frames = bytearray()
        for sample in range(44100 * 5):
            value = int(3000 * __import__("math").sin(2 * __import__("math").pi * 220 * sample / 44100))
            frames.extend(struct.pack("<hh", value, value))
        target.writeframes(frames)
    audio_hash = hashlib.sha256(audio_path.read_bytes()).hexdigest()
    audio_payload = {"schemaVersion": "music-render-v1", "mimeType": "audio/wav", "sha256": audio_hash, "inactive": True}
    con.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)", ("audio-1", "p1", "music-render", "Test music", "exports/music/test.wav", json.dumps(audio_payload), "DRAFT", audio_hash, "", ""))
    con.commit(); con.close()
    runtime = Path(__file__).resolve().parents[2] / "runtime"
    return VideoWorkstation(database, projects, runtime), database, originals, audio_path.read_bytes()


def composition():
    return {
        "title": "Three-frame test",
        "clips": [
            {"sourceArtifactId": "image-1", "durationSeconds": 1.5, "motion": "zoom-in", "transition": "cut"},
            {"sourceArtifactId": "image-2", "durationSeconds": 1.75, "motion": "pan-right", "transition": "crossfade"},
            {"sourceArtifactId": "image-3", "durationSeconds": 1.25, "motion": "still", "transition": "cut"},
        ],
        "audio": {"sourceArtifactId": "audio-1", "startSeconds": 0, "trimStartSeconds": 0, "volume": .7, "fadeInSeconds": .2, "fadeOutSeconds": .4, "muted": False},
        "titles": [{"text": "TWIS VIDEO V2", "startSeconds": .25, "durationSeconds": 1.25, "position": "center", "size": 44, "fade": True}],
        "size": "480p",
        "quality": "draft",
    }


def test_composition_is_inactive_hash_bound_and_sources_remain_exact(tmp_path):
    video, database, originals, audio = make_workspace(tmp_path)
    result = video.save_composition("p1", composition())
    artifact = result["artifact"]
    assert artifact["kind"] == "video-composition"
    assert artifact["payload"]["durationSeconds"] == 4.0
    con = sqlite3.connect(database)
    row = con.execute("select authority_state from artifacts where id=?", (artifact["id"],)).fetchone()
    assert row == ("DRAFT",)
    assert con.execute("select count(*) from artifact_relationships where target_artifact_id=?", (artifact["id"],)).fetchone()[0] == 4
    for source_id, expected in originals.items():
        path = next((tmp_path / "projects" / "p1" / "media" / "assets").glob(f"{sha(expected)}.png"))
        assert path.read_bytes() == expected
    assert (tmp_path / "projects" / "p1" / "exports" / "music" / "test.wav").read_bytes() == audio


def test_stale_source_and_unregistered_input_are_rejected(tmp_path):
    video, _, _, _ = make_workspace(tmp_path)
    value = composition()
    value["clips"][0]["sourceSha256"] = "0" * 64
    with pytest.raises(VideoWorkstationError, match="stale"):
        video.save_composition("p1", value)
    value = composition()
    value["clips"][0]["sourceArtifactId"] = "missing"
    with pytest.raises(VideoWorkstationError, match="not registered"):
        video.save_composition("p1", value)


def test_changed_writing_title_reference_blocks_reopen_and_render(tmp_path):
    video, database, _, _ = make_workspace(tmp_path)
    first_payload = json.dumps({"text": "Opening title"})
    first_hash = sha(first_payload.encode())
    con = sqlite3.connect(database)
    con.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)", ("writing-1", "p1", "document", "Opening", "", first_payload, "DRAFT", first_hash, "", ""))
    con.commit(); con.close()
    value = composition()
    value["titles"] = [{"text": "Opening title", "startSeconds": 0, "durationSeconds": 1, "position": "center", "size": 44, "fade": True, "sourceArtifactId": "writing-1", "sourceSha256": first_hash}]
    saved = video.save_composition("p1", value)["artifact"]
    changed_payload = json.dumps({"text": "Changed title"})
    con = sqlite3.connect(database)
    con.execute("UPDATE artifacts SET payload=?,sha256=? WHERE id='writing-1'", (changed_payload, sha(changed_payload.encode())))
    con.commit(); con.close()
    with pytest.raises(VideoWorkstationError, match="title writing hash is stale"):
        video.composition("p1", saved["id"])


def test_runtime_is_fixed_and_real_render_has_video_audio_and_provenance(tmp_path):
    video, database, originals, audio = make_workspace(tmp_path)
    runtime = video.runtime_status(verify=True)
    if not runtime.get("available"):
        pytest.skip("portable FFmpeg candidate runtime is not provisioned")
    assert runtime["state"] == "READY"
    assert runtime["features"] == {"libx264": True, "aac": True, "xfade": True, "zoompan": True, "drawtext": True, "afade": True}
    saved = video.save_composition("p1", composition())["artifact"]
    rendered = video.render("p1", saved["id"])["artifact"]
    payload = rendered["payload"]
    assert rendered["kind"] == "video-render"
    assert payload["videoCodec"] == "h264"
    assert payload["audioCodec"] == "aac"
    assert (payload["width"], payload["height"]) == (854, 480)
    assert abs(payload["durationSeconds"] - 4.0) <= .35
    assert payload["size"] > 1024
    output, mime = video.render_asset(rendered["id"])
    assert mime == "video/mp4"
    assert hashlib.sha256(output.read_bytes()).hexdigest() == rendered["sha256"]
    assert {ref["artifactId"] for ref in payload["sourceRefs"]} == {"image-1", "image-2", "image-3", "audio-1"}
    con = sqlite3.connect(database)
    assert con.execute("select count(*) from receipts where action='video.render.completed'").fetchone()[0] == 1
    assert con.execute("select count(*) from artifact_relationships where target_artifact_id=?", (rendered["id"],)).fetchone()[0] == 5
    for expected in originals.values():
        assert next((tmp_path / "projects" / "p1" / "media" / "assets").glob(f"{sha(expected)}.png")).read_bytes() == expected
    assert (tmp_path / "projects" / "p1" / "exports" / "music" / "test.wav").read_bytes() == audio
