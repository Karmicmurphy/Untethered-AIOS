from __future__ import annotations

import hashlib
import io
import json
import sqlite3
from pathlib import Path

import pytest

from companion.local_worker_kit import LocalWorkerError, LocalWorkerKit
from companion.model_bay import (
    DEFAULT_MODEL_ID,
    MUSIC_ACTIONS,
    ModelBay,
    ModelBayError,
    WRITE_ACTIONS,
    _bounded_music_proposal,
    _compact_music_prompt_state,
    sha256_text,
)


class Response:
    def __init__(self, value):
        self.value = json.dumps(value).encode()
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def read(self): return self.value


class Process:
    pid = 4321
    returncode = None
    def __init__(self): self.stopped = False
    def poll(self): return 0 if self.stopped else None
    def terminate(self): self.stopped = True; self.returncode = 0
    def wait(self, timeout=None): return self.returncode
    def kill(self): self.stopped = True; self.returncode = -9


def make_bay(tmp_path: Path, *, enabled=True):
    workshop = tmp_path / "TWIS"; asset = tmp_path / "TWIS_LOCAL_AI"
    (workshop / "config").mkdir(parents=True); (asset / "models").mkdir(parents=True); (asset / "runtime").mkdir(parents=True)
    model = asset / "models" / "model.gguf"; runtime = asset / "runtime" / "llama-server.exe"
    model.write_bytes(b"GGUF-model"); runtime.write_bytes(b"runtime")
    registry = {
        "schemaVersion": "local-model-bay-v1", "models": [{
            "modelId": DEFAULT_MODEL_ID, "displayName": "Test LFM", "provider": "Liquid AI", "family": "LFM2.5", "architecture": "lfm2",
            "localRelativePath": "models/model.gguf", "fileName": "model.gguf", "fileSize": model.stat().st_size,
            "sha256": hashlib.sha256(model.read_bytes()).hexdigest().upper(), "quantization": "Q4_K_M", "runtime": "llama.cpp-server",
            "runtimeExecutableRelativePath": "runtime/llama-server.exe", "runtimeExecutableSize": runtime.stat().st_size,
            "runtimeExecutableSha256": hashlib.sha256(runtime.read_bytes()).hexdigest().upper(), "runtimeVersion": "test", "enabled": enabled,
            "sourceRepository": "official", "licenseReference": "official", "capabilities": ["text-generation"], "intendedTaskCategories": ["text.rewrite"],
        }]
    }
    (workshop / "config" / "local-ai-models.json").write_text(json.dumps(registry), encoding="utf-8")
    calls = []
    def opener(request, timeout=0):
        calls.append((request.full_url, request.data, timeout))
        if request.full_url.endswith("/health"): return Response({"status": "ok"})
        payload = json.loads(request.data.decode())
        prompt = payload["messages"][-1]["content"]
        if "TWIS_LOCAL_MODEL_OK" in prompt:
            content = "TWIS_LOCAL_MODEL_OK"
        elif "MUSIC STUDIO ACTION" in prompt:
            content = json.dumps({"summary": "A bounded beat proposal.", "changes": {"bpm": 104, "arrangement": ["A", "A", "B", "A"]}, "chords": ["Am", "F", "C", "G"], "lyrics": "", "notes": ["Keep the kick sparse."]})
        else:
            content = "A clear local rewrite."
        return Response({"choices": [{"message": {"content": content}}], "usage": {"prompt_tokens": 5, "completion_tokens": 4}})
    processes = []
    def popen(command, **kwargs):
        processes.append((command, kwargs)); return Process()
    return ModelBay(workshop, asset_root=asset, opener=opener, popen=popen), model, runtime, calls, processes


def test_manifest_hash_route_start_health_inference_and_stop(tmp_path):
    bay, _, _, calls, processes = make_bay(tmp_path)
    installed = bay.model_status()
    assert installed["state"] == "INSTALLED" and installed["installed"] is True
    assert bay.route("text.rewrite")["modelId"] == DEFAULT_MODEL_ID
    ready = bay.start()
    assert ready["models"][0]["state"] == "READY"
    command, options = processes[0]
    assert "--host" in command and command[command.index("--host") + 1] == "127.0.0.1"
    assert "--port" in command and command[command.index("--port") + 1] == "8876"
    assert options["shell"] is False
    assert all(url.startswith("http://127.0.0.1:8876/") for url, _, _ in calls)
    inference_plan = bay.inference_plan("text.rewrite", "Balanced", "Keep the facts")
    source = {"sources": [{"artifactId": "a", "sha256": "A" * 64}], "content": "Rough sentence."}
    result = bay.infer_rewrite(source, {"ownerGoal": "Keep the facts", "inference": inference_plan})
    assert result["output"] == "A clear local rewrite."
    assert result["externalNetworkUsed"] is False and result["providerCloudCalled"] is False
    assert bay.stop()["stopped"] is True
    assert bay.status()["models"][0]["state"] == "INSTALLED"


def test_missing_corrupt_disabled_and_unsupported_are_honest(tmp_path):
    bay, model, _, _, _ = make_bay(tmp_path)
    model.write_bytes(b"corrupt")
    assert bay.model_status()["state"] == "ERROR"
    with pytest.raises(ModelBayError, match="hash verification"):
        bay.start()
    model.unlink()
    assert bay.model_status()["state"] == "REGISTERED"
    with pytest.raises(ModelBayError) as unsupported:
        bay.route("image.generate")
    assert unsupported.value.code == "task_category_unsupported"
    disabled, _, _, _, _ = make_bay(tmp_path / "disabled", enabled=False)
    with pytest.raises(ModelBayError) as denied:
        disabled.route("text.rewrite")
    assert denied.value.code == "model_disabled"


SCHEMA = """
CREATE TABLE projects(id TEXT PRIMARY KEY,title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',next_action TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE artifacts(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,kind TEXT NOT NULL,title TEXT NOT NULL,path TEXT NOT NULL DEFAULT '',payload TEXT NOT NULL DEFAULT '{}',authority_state TEXT NOT NULL DEFAULT 'DRAFT',sha256 TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE VIRTUAL TABLE artifact_search USING fts5(id UNINDEXED,project_id UNINDEXED,title,kind,content);
CREATE TABLE receipts(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,action TEXT NOT NULL,actor TEXT NOT NULL,details TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL);
CREATE TABLE jobs(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,operation TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL DEFAULT '{}',result TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
"""


class FakeInference:
    def inference_plan(self, task, preset, instruction):
        return {"taskCategory": task, "modelId": DEFAULT_MODEL_ID, "runtime": "llama.cpp-server", "modelSha256": "B" * 64, "promptTemplateVersion": "twis-write-rewrite-v1", "ownerInstructionSha256": sha256_text(instruction), "parameterPreset": preset, "parameters": {"temperature": .45, "topP": .9, "maxOutputTokens": 768}, "bindingAddress": "127.0.0.1", "port": 8876, "externalNetworkAllowed": False}
    def infer_rewrite(self, source, plan):
        inference = plan["inference"]
        music = plan.get("destinationProfile") in MUSIC_ACTIONS
        proposal = {"schemaVersion": "music-ai-proposal-v1", "action": plan.get("destinationProfile"), "summary": "Raise the tempo deliberately.", "changes": {"bpm": 106}, "chords": [], "lyrics": "", "notes": [], "applied": False}
        output = json.dumps(proposal, sort_keys=True, separators=(",", ":")) if music else "Clear proposed wording."
        result = {"schemaVersion": "local-inference-result-v1", "taskCategory": inference["taskCategory"], "modelId": inference["modelId"], "runtime": inference["runtime"], "modelSha256": inference["modelSha256"], "sourceArtifactIds": [source["artifactId"]], "sourceHashes": [source["sha256"]], "promptTemplateVersion": inference["promptTemplateVersion"], "promptSha256": "C" * 64, "ownerInstructionSha256": inference["ownerInstructionSha256"], "parameters": inference["parameters"], "parameterPreset": inference["parameterPreset"], "output": output, "outputSha256": sha256_text(output), "startedAt": "2026-08-09T00:00:00+00:00", "completedAt": "2026-08-09T00:00:01+00:00", "elapsedMs": 1000, "success": True, "loopbackUsed": True, "externalNetworkUsed": False, "providerCloudCalled": False, "usage": {}}
        if music:
            result.update({"musicAction": plan["destinationProfile"], "proposalData": proposal, "writingAction": plan["destinationProfile"], "inputScope": "whole-draft", "targetTextSha256": source["sha256"]})
        return result


def test_governed_ai_builder_lifecycle_preserves_source(tmp_path):
    db = tmp_path / "data" / "workshop.sqlite3"; projects = tmp_path / "data" / "projects"; source_dir = projects / "p" / "sources"; source_dir.mkdir(parents=True)
    def connect():
        con = sqlite3.connect(db); con.row_factory = sqlite3.Row; return con
    con = connect(); con.executescript(SCHEMA); now = "2026-08-09T00:00:00+00:00"
    con.execute("INSERT INTO projects VALUES(?,?,?,?,?,?)", ("p", "Project", "", "", now, now))
    raw = b"This sentence needs clarity."; (source_dir / "a.md").write_bytes(raw); digest = hashlib.sha256(raw).hexdigest().upper()
    con.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)", ("a", "p", "source", "Source", "sources/a.md", "{}", "PUBLIC", digest, now, now)); con.commit(); con.close()
    service = LocalWorkerKit(connect, projects, model_bay=FakeInference())
    planned = service.create_plan({"projectId": "p", "workerId": "local-ai-rewrite", "sourceArtifactIds": ["a"], "destinationProfile": "Rewrite while preserving meaning", "goal": "Keep every fact", "purpose": "Prepare explicit local AI rewrite", "inferencePreset": "Balanced", "actor": "owner"})
    assert planned["actions"]["approvePlan"] is True
    service.decide_plan(planned["jobId"], "approve", "Approve exact local inference plan", actor="owner")
    generated = service.execute(planned["jobId"], actor="owner")
    assert generated["status"] == "awaiting_result_approval"
    assert generated["result"]["output"]["metadata"]["inference"]["modelSha256"] == "B" * 64
    assert generated["result"]["inferenceReceiptId"]
    assert (source_dir / "a.md").read_bytes() == raw
    service.decide_result(planned["jobId"], "approve", "Approve proposed rewrite", actor="owner")
    saved = service.save_builder_draft(planned["jobId"], confirmed=True, actor="owner")
    draft_id = saved["result"]["savedDraft"]["artifactId"]
    con = connect(); assert con.execute("SELECT kind,authority_state FROM artifacts WHERE id=?", (draft_id,)).fetchone()[:] == ("ai-writing-proposal-draft", "DRAFT"); con.close()
    service.rollback(planned["jobId"], confirmed=True, actor="owner")
    assert (source_dir / "a.md").read_bytes() == raw
    con = connect(); assert con.execute("SELECT count(*) FROM artifacts WHERE id=?", (draft_id,)).fetchone()[0] == 0; assert con.execute("SELECT count(*) FROM receipts").fetchone()[0] >= 6; con.close()


def test_stale_source_blocks_local_ai_execution(tmp_path):
    db = tmp_path / "data" / "workshop.sqlite3"; projects = tmp_path / "data" / "projects"; source_dir = projects / "p" / "sources"; source_dir.mkdir(parents=True)
    def connect():
        con = sqlite3.connect(db); con.row_factory = sqlite3.Row; return con
    con = connect(); con.executescript(SCHEMA); now = "2026-08-09T00:00:00+00:00"; con.execute("INSERT INTO projects VALUES(?,?,?,?,?,?)", ("p", "P", "", "", now, now))
    raw=b"original"; (source_dir/"a.md").write_bytes(raw); digest=hashlib.sha256(raw).hexdigest().upper(); con.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)", ("a","p","source","A","sources/a.md","{}","PUBLIC",digest,now,now)); con.commit(); con.close()
    service=LocalWorkerKit(connect,projects,model_bay=FakeInference()); job=service.create_plan({"projectId":"p","workerId":"local-ai-rewrite","sourceArtifactIds":["a"],"destinationProfile":"Rewrite while preserving meaning","goal":"","purpose":"rewrite","inferencePreset":"Precise"}); service.decide_plan(job["jobId"],"approve","Approved",actor="owner")
    (source_dir/"a.md").write_bytes(b"changed")
    with pytest.raises(LocalWorkerError) as stale: service.execute(job["jobId"],actor="owner")
    assert stale.value.code == "stale_plan"


def test_governed_music_ai_proposal_rejects_without_mutating_music_state(tmp_path):
    db = tmp_path / "data" / "workshop.sqlite3"; projects = tmp_path / "data" / "projects"; projects.mkdir(parents=True)
    def connect():
        con = sqlite3.connect(db); con.row_factory = sqlite3.Row; return con
    con = connect(); con.executescript(SCHEMA); now = "2026-08-09T00:00:00+00:00"
    con.execute("INSERT INTO projects VALUES(?,?,?,?,?,?)", ("p", "Project", "", "", now, now)); con.commit(); con.close()
    blank = [0] * 16
    music_state = {
        "schemaVersion": "music-pattern-v2", "title": "Test groove", "bpm": 92, "activePattern": "A",
        "arrangement": ["A", "", "", "", "", "", "", ""],
        "patterns": {key: {"name": f"Pattern {key}", "tracks": {track: list(blank) for track in ("kick", "snare", "closedHat", "openHat", "percussion", "synth")}} for key in "ABCD"},
    }
    original = json.dumps(music_state, sort_keys=True, separators=(",", ":"))
    service = LocalWorkerKit(connect, projects, model_bay=FakeInference())
    planned = service.create_plan({"projectId": "p", "workerId": "local-ai-rewrite", "sourceArtifactIds": [], "musicState": music_state, "destinationProfile": "Suggest BPM", "goal": "Keep it deliberate", "purpose": "Prepare a proposal only", "inferencePreset": "Precise", "actor": "owner"})
    assert planned["plan"]["source"]["kind"] == "temporary-music-studio-state"
    service.decide_plan(planned["jobId"], "approve", "Approve exact music-state-bound plan", actor="owner")
    generated = service.execute(planned["jobId"], actor="owner")
    assert generated["status"] == "awaiting_result_approval"
    assert generated["result"]["output"]["proposalData"]["changes"] == {"bpm": 106}
    rejected = service.decide_result(planned["jobId"], "reject", "Do not apply this suggestion", actor="owner")
    assert rejected["status"] == "result_rejected"
    assert json.dumps(music_state, sort_keys=True, separators=(",", ":")) == original
    con = connect()
    assert con.execute("SELECT count(*) FROM artifacts").fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM receipts WHERE action LIKE 'local_worker.%' OR action LIKE 'local_model.%'").fetchone()[0] >= 4
    con.close()


def test_every_write_studio_action_routes_and_selection_context_are_bounded(tmp_path):
    bay, _, _, calls, _ = make_bay(tmp_path)
    bay.start()
    sources = [
        {"artifactId": "draft", "projectId": "p", "title": "Draft", "kind": "document", "sha256": "A" * 64, "bytes": 40, "content": "Opening. Selected passage. Closing."},
        {"artifactId": "context", "projectId": "p", "title": "Project notes", "kind": "source", "sha256": "B" * 64, "bytes": 20, "content": "Established context only."},
    ]
    for profile, (task, _) in WRITE_ACTIONS.items():
        plan = {
            "destinationProfile": profile,
            "ownerGoal": "Preserve names",
            "inference": bay.inference_plan(task, "Precise", "Preserve names"),
        }
        result = bay.infer_rewrite({**sources[0], "selection": "Selected passage.", "sources": sources}, plan)
        assert result["writingAction"] == profile
        assert result["taskCategory"] == task
        assert result["inputScope"] == "selection"
        assert result["sourceArtifactIds"] == ["draft", "context"]
    payload = json.loads(calls[-1][1].decode())
    prompt = payload["messages"][-1]["content"]
    assert "TARGET TEXT:\nSelected passage." in prompt
    assert "CONTEXT SOURCE: Project notes\nEstablished context only." in prompt
    assert "Opening." not in prompt
    assert all(url.startswith("http://127.0.0.1:8876/") for url, _, _ in calls)


def test_music_studio_actions_return_bounded_structured_proposals(tmp_path):
    bay, _, _, calls, _ = make_bay(tmp_path)
    bay.start()
    state = {
        "schemaVersion": "music-pattern-v2",
        "bpm": 92,
        "activePattern": "A",
        "arrangement": ["A", "", "", "", "", "", "", ""],
        "patterns": {"A": {"tracks": {track: [0] * 16 for track in ("kick", "snare", "closedHat", "openHat", "percussion", "synth")}}},
    }
    source = {
        "artifactId": "music-studio:state",
        "sha256": hashlib.sha256(json.dumps(state, sort_keys=True, separators=(",", ":")).encode()).hexdigest().upper(),
        "content": json.dumps(state, sort_keys=True, separators=(",", ":")),
        "sources": [{"artifactId": "music-studio:state", "sha256": "A" * 64}],
    }
    for profile, (task, _) in MUSIC_ACTIONS.items():
        plan = {
            "destinationProfile": profile,
            "ownerGoal": "Keep it restrained",
            "inference": bay.inference_plan(task, "Precise", "Keep it restrained"),
        }
        result = bay.infer_rewrite(source, plan)
        assert result["musicAction"] == profile
        assert result["taskCategory"] == task
        assert result["proposalData"]["schemaVersion"] == "music-ai-proposal-v1"
        assert result["proposalData"]["changes"]["bpm"] == 104
        assert result["proposalData"]["changes"]["arrangement"] == ["A", "A", "B", "A"]
        assert result["proposalData"]["applied"] is False
    assert all(url.startswith("http://127.0.0.1:8876/") for url, _, _ in calls)


def test_music_bpm_summary_is_recovered_as_one_bounded_change():
    proposal = _bounded_music_proposal(
        "Suggest BPM",
        json.dumps(
            {
                "summary": "Suggest 96 BPM for a restrained groove.",
                "changes": {},
                "lyrics": "No lyrics provided",
            }
        ),
    )
    assert proposal["changes"] == {"bpm": 96}
    assert proposal["applied"] is False


def test_music_prompt_state_compacts_sparse_steps_without_losing_active_events():
    state = {
        "title": "Proof groove",
        "notes": "Keep it spare.",
        "bpm": 92,
        "activePattern": "A",
        "arrangement": ["A", "B", "A", ""],
        "patterns": {
            "A": {"tracks": {"kick": [1, 0, 0, 0] * 4, "synth": [1, 0, 3, 0] * 4}},
            "B": {"tracks": {"snare": [0, 0, 1, 0] * 4}},
        },
    }
    compact = json.loads(_compact_music_prompt_state(json.dumps(state)))
    assert compact["activeTracks"]["kick"] == "1,5,9,13"
    assert compact["activeTracks"]["synth"] == "1:1,3:3,5:1,7:3,9:1,11:3,13:1,15:3"
    assert compact["patternEventCounts"]["B"]["snare"] == 4
