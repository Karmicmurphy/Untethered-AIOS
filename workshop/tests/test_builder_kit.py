from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from companion.capability_registry import CapabilityRegistry
from companion.local_worker_kit import LocalWorkerError, LocalWorkerKit


SCHEMA = """
CREATE TABLE projects(id TEXT PRIMARY KEY,title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',next_action TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE TABLE artifacts(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,kind TEXT NOT NULL,title TEXT NOT NULL,path TEXT NOT NULL DEFAULT '',payload TEXT NOT NULL DEFAULT '{}',authority_state TEXT NOT NULL DEFAULT 'DRAFT',sha256 TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
CREATE VIRTUAL TABLE artifact_search USING fts5(id UNINDEXED,project_id UNINDEXED,title,kind,content);
CREATE TABLE receipts(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,action TEXT NOT NULL,actor TEXT NOT NULL,details TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL);
CREATE TABLE jobs(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,operation TEXT NOT NULL,status TEXT NOT NULL,payload TEXT NOT NULL DEFAULT '{}',result TEXT NOT NULL DEFAULT '{}',created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
"""


@pytest.fixture()
def kit(tmp_path: Path):
    database = tmp_path / "data" / "workshop.sqlite3"
    projects = tmp_path / "data" / "projects"
    root = projects / "p" / "sources"
    root.mkdir(parents=True)

    def connect():
        con = sqlite3.connect(database)
        con.row_factory = sqlite3.Row
        return con

    con = connect()
    con.executescript(SCHEMA)
    now = "2026-08-02T00:00:00+00:00"
    con.execute("INSERT INTO projects VALUES(?,?,?,?,?,?)", ("p", "Project", "", "", now, now))
    for artifact_id, title, name, body in (
        ("a", "Same title", "a.md", "Current state is verified.\nCompleted: Release 0.8."),
        ("b", "Same title", "b.md", "Constraint: preserve sources.\nRemaining: build 0.9."),
    ):
        raw = body.encode()
        (root / name).write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest().upper()
        con.execute("INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?,?,?)", (artifact_id, "p", "source", title, f"sources/{name}", "{}", "PUBLIC", digest, now, now))
    con.commit()
    con.close()
    return LocalWorkerKit(connect, projects), connect, root


def plan(service: LocalWorkerKit, worker: str, profile: str):
    value = service.create_plan({
        "projectId": "p", "workerId": worker, "sourceArtifactIds": ["a", "b"],
        "destinationProfile": profile, "goal": "Continue the verified release safely",
        "purpose": "Continue the verified release safely", "actor": "owner",
    })
    return value


def run_approved(service: LocalWorkerKit, value: dict):
    service.decide_plan(value["jobId"], "approve", "Approved exact plan", actor="owner")
    return service.execute(value["jobId"], actor="owner")


def test_handoff_save_and_exact_rollback(kit):
    service, connect, _ = kit
    value = plan(service, "handoff-proposal-builder", "Project Recovery Handoff")
    generated = run_approved(service, value)
    assert generated["status"] == "awaiting_result_approval"
    assert generated["result"]["validation"]["valid"] is True
    text = generated["result"]["output"]["text"]
    assert "## Acceptance criteria" in text
    assert "ID a" in text and "ID b" in text
    approved = service.decide_result(value["jobId"], "approve", "Approve proposal", actor="owner")
    assert approved["actions"]["saveDraft"] is True
    saved = service.save_builder_draft(value["jobId"], confirmed=True, actor="owner")
    assert saved["status"] == "draft_saved"
    draft_id = saved["result"]["savedDraft"]["artifactId"]
    con = connect()
    assert tuple(con.execute("SELECT kind,authority_state FROM artifacts WHERE id=?", (draft_id,)).fetchone()) == ("handoff-draft", "DRAFT")
    assert con.execute("SELECT count(*) FROM artifact_relationships WHERE target_artifact_id=?", (draft_id,)).fetchone()[0] == 2
    con.close()
    with pytest.raises(LocalWorkerError) as duplicate:
        service.save_builder_draft(value["jobId"], confirmed=True, actor="owner")
    assert duplicate.value.code == "duplicate_save"
    rolled = service.rollback(value["jobId"], confirmed=True, actor="owner")
    assert rolled["status"] == "rolled_back"
    con = connect()
    assert con.execute("SELECT count(*) FROM artifacts WHERE id=?", (draft_id,)).fetchone()[0] == 0
    assert con.execute("SELECT count(*) FROM artifacts WHERE id IN ('a','b')").fetchone()[0] == 2
    con.close()
    with pytest.raises(LocalWorkerError, match="no saved draft"):
        service.rollback(value["jobId"], confirmed=True, actor="owner")


def test_prompt_approval_is_inactive_and_exports_are_explicit(kit):
    service, _, _ = kit
    value = plan(service, "prompt-proposal-builder", "Local Model Task Prompt")
    generated = run_approved(service, value)
    assert "## Final response format" in generated["result"]["output"]["text"]
    with pytest.raises(LocalWorkerError, match="explicitly approved"):
        service.export_builder_result(value["jobId"], "txt", include_provenance=True, confirmed=True, actor="owner")
    approved = service.decide_result(value["jobId"], "approve", "Approved prompt", actor="owner")
    assert approved["attachmentStatus"] == "unattached"
    assert approved["activationStatus"] == "inactive"
    for fmt in ("txt", "json"):
        exported = service.export_builder_result(value["jobId"], fmt, include_provenance=True, confirmed=True, actor="owner")
        record = exported["result"]["exports"][-1]
        path = Path(record["path"])
        assert path.exists() and path.suffix == f".{fmt}"
        assert ".." not in path.name
    assert len(exported["result"]["exports"]) == 2


def test_builder_negative_contracts_and_stale_plan(kit):
    service, _, root = kit
    base = {"projectId":"p", "workerId":"handoff-proposal-builder", "sourceArtifactIds":["a"], "destinationProfile":"Codex Build Handoff", "goal":"Do it"}
    for change, code in (
        ({"sourceArtifactIds":[]}, "builder_sources_invalid"),
        ({"sourceArtifactIds":["missing"]}, "source_artifact_not_found"),
        ({"goal":"   "}, "builder_goal_invalid"),
        ({"destinationProfile":"Unknown"}, "builder_profile_unsupported"),
    ):
        with pytest.raises(LocalWorkerError) as error:
            service.create_plan({**base, **change})
        assert error.value.code == code
    value = service.create_plan(base)
    service.decide_plan(value["jobId"], "approve", "Approve", actor="owner")
    (root / "a.md").write_text("changed", encoding="utf-8")
    with pytest.raises(LocalWorkerError) as error:
        service.execute(value["jobId"], actor="owner")
    assert error.value.code == "stale_plan"


def test_rejection_creates_no_draft_and_save_before_approval_is_blocked(kit):
    service, connect, _ = kit
    value = plan(service, "handoff-proposal-builder", "Human Technical Handoff")
    run_approved(service, value)
    with pytest.raises(LocalWorkerError) as error:
        service.save_builder_draft(value["jobId"], confirmed=True, actor="owner")
    assert error.value.code == "save_requires_approval"
    rejected = service.decide_result(value["jobId"], "reject", "Not accepted", actor="owner")
    assert rejected["status"] == "result_rejected"
    con = connect()
    assert con.execute("SELECT count(*) FROM artifacts WHERE kind IN ('handoff-draft','prompt-draft')").fetchone()[0] == 0
    con.close()


def test_changed_source_blocks_result_approval(kit):
    service, _, root = kit
    value = plan(service, "prompt-proposal-builder", "Codex Implementation Prompt")
    run_approved(service, value)
    (root / "b.md").write_text("changed after generation", encoding="utf-8")
    with pytest.raises(LocalWorkerError) as stale:
        service.decide_result(value["jobId"], "approve", "Approve", actor="owner")
    assert stale.value.code in {"source_hash_mismatch", "stale_plan"}


def test_draft_workshop_registered_source_full_lifecycle(kit):
    service, connect, root = kit
    original = (root / "a.md").read_bytes()
    value = service.create_plan({
        "projectId": "p", "workerId": "draft-workshop",
        "sourceArtifactIds": ["a"], "destinationProfile": "Rewrite clearly",
        "goal": "Use a calm professional tone", "purpose": "Prepare Rewrite clearly",
    })
    generated = run_approved(service, value)
    output = generated["result"]["output"]
    assert output["metadata"]["writingOperation"] == "Rewrite clearly"
    assert output["metadata"]["ownerInstructions"] == "Use a calm professional tone"
    assert "No language model or external provider was called" in output["text"]
    service.decide_result(value["jobId"], "approve", "Approve writing task", actor="owner")
    saved = service.save_builder_draft(value["jobId"], confirmed=True, actor="owner")
    draft_id = saved["result"]["savedDraft"]["artifactId"]
    exported = service.export_builder_result(value["jobId"], "md", include_provenance=True, confirmed=True, actor="owner")
    assert Path(exported["result"]["exports"][-1]["path"]).suffix == ".md"
    con = connect()
    draft = con.execute("SELECT kind,authority_state,payload FROM artifacts WHERE id=?", (draft_id,)).fetchone()
    assert tuple(draft[:2]) == ("writing-draft", "DRAFT")
    assert len(json.loads(draft["payload"])["exportHistory"]) == 1
    con.close()
    rolled = service.rollback(value["jobId"], confirmed=True, actor="owner")
    assert rolled["status"] == "rolled_back"
    assert (root / "a.md").read_bytes() == original


def test_draft_workshop_rough_text_is_hash_bound_and_honest(kit):
    service, _, _ = kit
    value = service.create_plan({
        "projectId": "p", "workerId": "draft-workshop", "sourceArtifactIds": [],
        "roughText": "rough idea\nneeds shape", "destinationProfile": "Expand rough notes",
        "goal": "", "purpose": "Prepare Expand rough notes",
    })
    assert value["sources"][0]["artifactId"].startswith("rough-text:")
    generated = run_approved(service, value)
    assert "rough idea" in generated["result"]["output"]["text"]
    assert generated["result"]["output"]["networkUsed"] is False
    assert generated["result"]["output"]["shellUsed"] is False
    with pytest.raises(LocalWorkerError) as unsupported:
        service.export_builder_result(value["jobId"], "md", include_provenance=True, confirmed=True, actor="owner")
    assert unsupported.value.code == "export_requires_approval"


def test_draft_workshop_rejects_ambiguous_or_blank_input(kit):
    service, _, _ = kit
    base = {"projectId": "p", "workerId": "draft-workshop", "destinationProfile": "Change tone", "goal": "friendly", "purpose": "Prepare Change tone"}
    for request in (
        {**base, "sourceArtifactIds": []},
        {**base, "sourceArtifactIds": ["a", "b"]},
        {**base, "sourceArtifactIds": ["a"], "roughText": "also rough"},
        {**base, "sourceArtifactIds": [], "roughText": "   "},
    ):
        with pytest.raises(LocalWorkerError) as error:
            service.create_plan(request)
        assert error.value.code == "builder_sources_invalid"


def test_evidence_compare_full_multisource_lifecycle(kit):
    service, connect, root = kit
    originals = {name: (root / name).read_bytes() for name in ("a.md", "b.md")}
    value = service.create_plan({
        "projectId": "p", "workerId": "evidence-compare",
        "sourceArtifactIds": ["b", "a"], "destinationProfile": "Requirement coverage",
        "goal": "Keep source order and identify only exact textual facts.",
        "purpose": "Prepare Requirement coverage",
    })
    assert [source["artifactId"] for source in value["sources"]] == ["b", "a"]
    generated = run_approved(service, value)
    output = generated["result"]["output"]
    assert output["metadata"]["sourceIds"] == ["b", "a"]
    assert output["metadata"]["comparisonFocus"] == "Requirement coverage"
    assert "No semantic contradictions were inferred" in output["text"]
    assert "Semantic agreement" in output["text"] and "Not assessed" in output["text"]
    service.decide_result(value["jobId"], "approve", "Approve exact comparison scaffold", actor="owner")
    saved = service.save_builder_draft(value["jobId"], confirmed=True, actor="owner")
    draft_id = saved["result"]["savedDraft"]["artifactId"]
    for fmt in ("txt", "md", "json"):
        saved = service.export_builder_result(value["jobId"], fmt, include_provenance=True, confirmed=True, actor="owner")
        assert Path(saved["result"]["exports"][-1]["path"]).suffix == f".{fmt}"
    con = connect()
    draft = con.execute("SELECT kind,authority_state,payload FROM artifacts WHERE id=?", (draft_id,)).fetchone()
    assert tuple(draft[:2]) == ("research-comparison-draft", "DRAFT")
    payload = json.loads(draft["payload"])
    assert payload["sourceIds"] == ["b", "a"]
    assert payload["comparisonFocus"] == "Requirement coverage"
    assert len(payload["exportHistory"]) == 3
    assert con.execute("SELECT count(*) FROM artifact_relationships WHERE target_artifact_id=?", (draft_id,)).fetchone()[0] == 2
    con.close()
    assert service.rollback(value["jobId"], confirmed=True, actor="owner")["status"] == "rolled_back"
    assert {name: (root / name).read_bytes() for name in originals} == originals


def test_evidence_compare_source_bounds_duplicates_and_stale_result(kit):
    service, _, root = kit
    base = {"projectId": "p", "workerId": "evidence-compare", "destinationProfile": "General comparison", "goal": "", "purpose": "Prepare General comparison"}
    for ids in ([], ["a"], ["a", "a"], [str(index) for index in range(9)]):
        with pytest.raises(LocalWorkerError) as error:
            service.create_plan({**base, "sourceArtifactIds": ids})
        assert error.value.code == "builder_sources_invalid"
    value = service.create_plan({**base, "sourceArtifactIds": ["a", "b"]})
    run_approved(service, value)
    (root / "b.md").write_text("changed after deterministic comparison", encoding="utf-8")
    with pytest.raises(LocalWorkerError) as stale:
        service.decide_result(value["jobId"], "approve", "Approve", actor="owner")
    assert stale.value.code in {"source_hash_mismatch", "stale_plan"}


def test_visual_brief_full_governed_lifecycle(kit):
    service, connect, root = kit
    original = (root / "a.md").read_bytes()
    notes = "A small cyan workshop light floating above a dark river."
    controls = {
        "conceptTitle": "River Workshop",
        "centralSubject": "A floating workshop light",
        "setting": "A dark river at night",
        "moodEmotion": "Quiet resolve",
        "visualStyle": "Painterly concept art",
        "composition": "Centered subject with broad negative space",
        "cameraViewpoint": "Eye level",
        "lighting": "One cyan practical light",
        "colorDirection": "Deep navy and cyan",
        "aspectRatio": "1:1",
        "requiredText": "TWIS",
        "prohibitedText": "No other lettering",
        "requiredElements": "River and workshop light",
        "prohibitedElements": "No logos",
        "realismLevel": "Stylized realism",
        "referenceSourcePriority": "Registered source controls facts; owner notes control composition",
        "additionalInstructions": "Keep the frame uncluttered",
    }
    value = service.create_plan({
        "projectId": "p", "workerId": "visual-brief-builder", "sourceArtifactIds": ["a"],
        "roughText": notes, "visualControls": controls,
        "destinationProfile": "Song or album cover", "goal": "Keep the frame uncluttered",
        "purpose": "Prepare Song or album cover",
    })
    assert value["plan"]["visualControls"] == controls
    assert value["sources"][0]["artifactId"] == "a"
    assert value["sources"][1]["artifactId"] == f"visual-notes:{hashlib.sha256(notes.encode()).hexdigest().upper()}"
    generated = run_approved(service, value)
    output = generated["result"]["output"]
    assert output["metadata"]["visualPurpose"] == "Song or album cover"
    assert output["metadata"]["visualControls"] == controls
    assert output["metadata"]["ownerNotesHash"] == hashlib.sha256(notes.encode()).hexdigest().upper()
    assert "No image was generated, rendered, downloaded, submitted" in output["text"]
    assert "[Unresolved creative decision]" not in output["text"]
    service.decide_result(value["jobId"], "approve", "Approve exact visual brief", actor="owner")
    saved = service.save_builder_draft(value["jobId"], confirmed=True, actor="owner")
    draft_id = saved["result"]["savedDraft"]["artifactId"]
    for fmt in ("txt", "md", "json"):
        saved = service.export_builder_result(value["jobId"], fmt, include_provenance=True, confirmed=True, actor="owner")
        assert Path(saved["result"]["exports"][-1]["path"]).suffix == f".{fmt}"
    con = connect()
    draft = con.execute("SELECT kind,authority_state,payload FROM artifacts WHERE id=?", (draft_id,)).fetchone()
    payload = json.loads(draft["payload"])
    assert tuple(draft[:2]) == ("visual-brief-draft", "DRAFT")
    assert payload["inactive"] is True and payload["attached"] is False
    assert payload["executed"] is False and payload["published"] is False and payload["promoted"] is False
    assert payload["visualPurpose"] == "Song or album cover" and len(payload["exportHistory"]) == 3
    assert con.execute("SELECT count(*) FROM artifact_relationships WHERE target_artifact_id=?", (draft_id,)).fetchone()[0] == 1
    con.close()
    assert service.rollback(value["jobId"], confirmed=True, actor="owner")["status"] == "rolled_back"
    assert (root / "a.md").read_bytes() == original


def test_visual_brief_notes_only_bounds_controls_and_stale_source(kit):
    service, _, root = kit
    base = {"projectId": "p", "workerId": "visual-brief-builder", "destinationProfile": "General image concept", "goal": "", "purpose": "Prepare General image concept", "visualControls": {}}
    for request in (
        {**base, "sourceArtifactIds": [], "roughText": ""},
        {**base, "sourceArtifactIds": ["a", "a"], "roughText": ""},
        {**base, "sourceArtifactIds": [str(index) for index in range(5)], "roughText": ""},
        {**base, "sourceArtifactIds": [], "roughText": "idea", "visualControls": {"unknown": "blocked"}},
    ):
        with pytest.raises(LocalWorkerError) as error:
            service.create_plan(request)
        assert error.value.code in {"builder_sources_invalid", "builder_controls_invalid"}
    notes_only = service.create_plan({**base, "sourceArtifactIds": [], "roughText": "An honest temporary visual idea."})
    assert notes_only["sources"][0]["kind"] == "temporary-visual-notes"
    generated = run_approved(service, notes_only)
    assert generated["result"]["validation"]["valid"] is True
    sourced = service.create_plan({**base, "sourceArtifactIds": ["a"], "roughText": ""})
    run_approved(service, sourced)
    (root / "a.md").write_text("changed after visual plan", encoding="utf-8")
    with pytest.raises(LocalWorkerError) as stale:
        service.decide_result(sourced["jobId"], "approve", "Approve", actor="owner")
    assert stale.value.code in {"source_hash_mismatch", "stale_plan"}


def test_song_production_brief_full_governed_lifecycle_preserves_lyrics(kit):
    service, connect, root = kit
    original = (root / "a.md").read_bytes()
    notes = "A restrained river song that grows from one voice into a warm ensemble."
    lyrics = "Hold the river light\nKeep the workshop warm\nDo not change this line: <river & sky>"
    controls = {
        "workingTitle": "River Light", "centralSubject": "keeping a workshop alive",
        "emotionalArc": "quiet resolve to shared warmth", "genre": "folk", "subgenre": "cinematic folk",
        "tempoBpm": "84", "tonalCenter": "D minor", "timeSignature": "4/4",
        "vocalType": "solo voice with ensemble", "vocalDelivery": "intimate, then open",
        "instrumentation": "acoustic guitar, piano, strings", "rhythmGroove": "steady pulse",
        "songStructure": "intro, verse, chorus, verse, chorus, bridge, final chorus", "intro": "sparse piano",
        "verseTreatment": "intimate", "chorusTreatment": "wider dynamics", "bridgeBreakdown": "drop to voice",
        "soloInstrumental": "short cello line", "ending": "quiet resolved chord",
        "productionTexture": "warm and natural", "recordingCharacter": "close and human",
        "dynamicBuild": "gradual", "referenceInfluences": "owner references only",
        "requiredElements": "preserve supplied lyric fragment", "prohibitedElements": "no invented lyrics",
        "lyricBoundaries": "do not rewrite or complete", "explicitLanguagePreference": "none",
        "approximateDuration": "3:30", "additionalInstructions": "leave missing choices unresolved",
        "referenceSourcePriority": "registered source controls factual provenance",
    }
    value = service.create_plan({
        "projectId": "p", "workerId": "song-production-brief-builder", "sourceArtifactIds": ["a"],
        "musicNotes": notes, "musicLyrics": lyrics, "productionControls": controls,
        "destinationProfile": "Full original song", "goal": "Prepare an honest manual-use brief",
        "purpose": "Prepare Full original song",
    })
    note_hash = hashlib.sha256(notes.encode()).hexdigest().upper()
    lyric_hash = hashlib.sha256(lyrics.encode()).hexdigest().upper()
    assert [source["artifactId"] for source in value["sources"]] == ["a", f"music-notes:{note_hash}", f"music-lyrics:{lyric_hash}"]
    generated = run_approved(service, value)
    output = generated["result"]["output"]
    assert output["metadata"]["musicNotesIdentity"] == f"music-notes:{note_hash}"
    assert output["metadata"]["musicLyricsIdentity"] == f"music-lyrics:{lyric_hash}"
    assert f"## Owner-supplied lyrics or lyric fragments preserved exactly\n\n{lyrics}\n\n##" in output["text"]
    assert "No music, lyrics, vocals, melody, chords, instrumentation, or audio was generated, played" in output["text"]
    service.decide_result(value["jobId"], "approve", "Approve exact song brief", actor="owner")
    saved = service.save_builder_draft(value["jobId"], confirmed=True, actor="owner")
    draft_id = saved["result"]["savedDraft"]["artifactId"]
    for fmt in ("txt", "md", "json"):
        saved = service.export_builder_result(value["jobId"], fmt, include_provenance=True, confirmed=True, actor="owner")
    con = connect()
    draft = con.execute("SELECT kind,authority_state,payload FROM artifacts WHERE id=?", (draft_id,)).fetchone()
    payload = json.loads(draft["payload"])
    assert tuple(draft[:2]) == ("song-production-brief-draft", "DRAFT")
    assert payload["inactive"] is True and payload["attached"] is False and payload["executed"] is False
    assert payload["published"] is False and payload["promoted"] is False and len(payload["exportHistory"]) == 3
    assert payload["musicLyricsIdentity"] == f"music-lyrics:{lyric_hash}"
    assert con.execute("SELECT count(*) FROM artifact_relationships WHERE target_artifact_id=?", (draft_id,)).fetchone()[0] == 1
    con.close()
    assert service.rollback(value["jobId"], confirmed=True, actor="owner")["status"] == "rolled_back"
    assert (root / "a.md").read_bytes() == original


def test_song_production_brief_bounds_controls_and_stale_source(kit):
    service, _, root = kit
    base = {"projectId": "p", "workerId": "song-production-brief-builder", "destinationProfile": "General music concept", "goal": "", "purpose": "Prepare General music concept", "productionControls": {}}
    for request in (
        {**base, "sourceArtifactIds": []},
        {**base, "sourceArtifactIds": ["a", "a"]},
        {**base, "sourceArtifactIds": [str(index) for index in range(5)]},
        {**base, "sourceArtifactIds": [], "musicNotes": "idea", "productionControls": {"unknown": "blocked"}},
    ):
        with pytest.raises(LocalWorkerError) as error:
            service.create_plan(request)
        assert error.value.code in {"builder_sources_invalid", "builder_controls_invalid"}
    lyrics_only = service.create_plan({**base, "sourceArtifactIds": [], "musicLyrics": "Exact lyric fragment"})
    assert lyrics_only["sources"][0]["kind"] == "temporary-music-lyrics"
    assert run_approved(service, lyrics_only)["result"]["validation"]["valid"] is True
    sourced = service.create_plan({**base, "sourceArtifactIds": ["a"]})
    run_approved(service, sourced)
    (root / "a.md").write_text("changed after song plan", encoding="utf-8")
    with pytest.raises(LocalWorkerError) as stale:
        service.decide_result(sourced["jobId"], "approve", "Approve", actor="owner")
    assert stale.value.code in {"source_hash_mismatch", "stale_plan"}


def test_video_production_brief_full_governed_lifecycle(kit):
    service, connect, root = kit
    original = (root / "a.md").read_bytes()
    notes = "A quiet clockwork workshop emerges from reflected ocean light.\nKeep the final frame still."
    controls = {
        "workingTitle": "Workshop Tide", "productionGoal": "Prepare a 45-second concept film",
        "coreConcept": "arrival through water and machinery", "intendedAudience": "project collaborators",
        "targetDuration": "45 seconds", "aspectRatio": "16:9", "resolutionIntent": "4K master intent",
        "visualStyle": "surreal practical architecture", "pacing": "slow opening, measured build",
        "cameraLanguage": "controlled wide frames and close details", "environmentLocation": "ocean workshop",
        "subjectCharacterNotes": "one owner entering the room", "wardrobeAppearance": "dark coat",
        "propsObjects": "brass compass and clock", "lighting": "teal water reflections",
        "colorPalette": "graphite, teal, antique brass", "composition": "central compass geometry",
        "lensFraming": "wide establishing view then detail inserts", "cameraMovement": "slow deliberate push",
        "subjectMovement": "walk, pause, look toward the compass", "shotIdeas": "wide threshold; hand on compass; still closing frame",
        "transitionStyle": "hard cuts at mechanical beats", "storySequence": "arrival, discovery, readiness",
        "openingBeat": "water reflection before the room", "mainProgression": "workshop systems reveal in sequence",
        "closingBeat": "still frame on the active compass", "audioDialogue": "none",
        "narrationVoice": "optional owner narration", "musicNotes": "low restrained pulse",
        "soundDesignNotes": "water, brass clicks, room tone", "onScreenText": "TWIS HOLO WORKSHOP",
        "effectsCompositing": "subtle reflection layers only", "continuityRequirements": "compass remains north-aligned",
        "productionConstraints": "older local editing machine", "safetyLegalConsent": "owner-controlled likeness only",
        "referenceSourcePriority": "registered source controls facts", "unresolvedDecisions": "exact narration text",
        "additionalInstructions": "keep all missing choices explicit",
    }
    value = service.create_plan({
        "projectId": "p", "workerId": "video-production-brief-builder", "sourceArtifactIds": ["a"],
        "videoNotes": notes, "videoControls": controls, "destinationProfile": "Cinematic scene",
        "goal": "Prepare an honest manual production handoff", "purpose": "Prepare Cinematic scene",
    })
    note_id = "video-notes:" + hashlib.sha256(notes.encode()).hexdigest().upper()
    assert [source["artifactId"] for source in value["sources"]] == ["a", note_id]
    generated = run_approved(service, value)
    assert generated["status"] == "awaiting_result_approval"
    output = generated["result"]["output"]
    assert output["metadata"]["videoNotesIdentity"] == note_id
    assert "## Final production prompt and handoff block" in output["text"]
    assert "No video was generated, rendered, downloaded, uploaded, submitted, published" in output["text"]
    service.decide_result(value["jobId"], "approve", "Approve exact video brief", actor="owner")
    saved = service.save_builder_draft(value["jobId"], confirmed=True, actor="owner")
    draft_id = saved["result"]["savedDraft"]["artifactId"]
    for fmt in ("txt", "md", "json"):
        saved = service.export_builder_result(value["jobId"], fmt, include_provenance=True, confirmed=True, actor="owner")
    con = connect()
    draft = con.execute("SELECT kind,authority_state,payload FROM artifacts WHERE id=?", (draft_id,)).fetchone()
    payload = json.loads(draft["payload"])
    assert tuple(draft[:2]) == ("video-production-brief-draft", "DRAFT")
    assert payload["inactive"] is True and payload["attached"] is False and payload["executed"] is False
    assert payload["published"] is False and payload["promoted"] is False and len(payload["exportHistory"]) == 3
    assert payload["videoNotesIdentity"] == note_id
    assert con.execute("SELECT count(*) FROM artifact_relationships WHERE target_artifact_id=?", (draft_id,)).fetchone()[0] == 1
    con.close()
    assert service.rollback(value["jobId"], confirmed=True, actor="owner")["status"] == "rolled_back"
    assert (root / "a.md").read_bytes() == original


def test_video_brief_bounds_separate_approvals_and_stale_source(kit):
    service, _, root = kit
    base = {"projectId": "p", "workerId": "video-production-brief-builder", "destinationProfile": "Documentary / story", "goal": "", "purpose": "Prepare Documentary / story", "videoControls": {}}
    for request in (
        {**base, "sourceArtifactIds": []},
        {**base, "sourceArtifactIds": ["a", "a"]},
        {**base, "sourceArtifactIds": [str(index) for index in range(5)]},
        {**base, "sourceArtifactIds": [], "videoNotes": "idea", "videoControls": {"unknown": "blocked"}},
    ):
        with pytest.raises(LocalWorkerError) as error:
            service.create_plan(request)
        assert error.value.code in {"builder_sources_invalid", "builder_controls_invalid"}
    notes_only = service.create_plan({**base, "sourceArtifactIds": [], "videoNotes": "Exact owner video concept"})
    assert notes_only["sources"][0]["kind"] == "temporary-video-notes"
    with pytest.raises(LocalWorkerError):
        service.execute(notes_only["jobId"], actor="owner")
    generated = run_approved(service, notes_only)
    with pytest.raises(LocalWorkerError) as early_save:
        service.save_builder_draft(notes_only["jobId"], confirmed=True, actor="owner")
    assert early_save.value.code == "save_requires_approval"
    sourced = service.create_plan({**base, "sourceArtifactIds": ["a"]})
    run_approved(service, sourced)
    (root / "a.md").write_text("changed after video plan", encoding="utf-8")
    with pytest.raises(LocalWorkerError) as stale:
        service.decide_result(sourced["jobId"], "approve", "Approve", actor="owner")
    assert stale.value.code in {"source_hash_mismatch", "stale_plan"}


@pytest.mark.parametrize(
    "worker,profile,notes_key,controls_key,notes,controls,kind,section,prefix",
    [
        (
            "build-work-order-builder", "Add feature", "buildNotes", "buildControls",
            "Preserve this exact owner build note.\nNo automatic execution.",
            {"workingTitle": "Bounded room pass", "buildGoal": "Add one safe room capability", "requirements": "Separate plan and result approval", "acceptanceCriteria": "Inactive draft reopens", "testingExpectations": "Run focused and inherited tests", "rollbackExpectations": "Remove only the created draft"},
            "build-work-order-draft", "## Final implementation handoff block", "build-input:",
        ),
        (
            "module-proposal-builder", "Local tool", "moduleNotes", "moduleControls",
            "Preserve this exact owner module note.\nProposal only.",
            {"moduleName": "Source Question Sheet", "purpose": "Prepare source questions", "targetRoom": "Explore", "localCloudBoundary": "Local only", "permissionsCapabilities": "Read selected sources only", "testingRequirements": "Verify no install or execution", "rollbackRequirements": "Remove only the proposal draft", "acceptanceCriteria": "Honest inactive proposal"},
            "module-proposal-draft", "## Final implementation handoff", "module-input:",
        ),
    ],
)
def test_release_016_build_and_module_governed_lifecycle(kit, worker, profile, notes_key, controls_key, notes, controls, kind, section, prefix):
    service, connect, root = kit
    original = (root / "a.md").read_bytes()
    request = {
        "projectId": "p", "workerId": worker, "sourceArtifactIds": ["a"],
        notes_key: notes, controls_key: controls, "destinationProfile": profile,
        "goal": "Owner instructions remain separate", "purpose": f"Prepare {profile}",
    }
    value = service.create_plan(request)
    assert value["status"] == "planned" and value["actions"]["approvePlan"] is True
    assert value["sources"][1]["artifactId"].startswith(prefix)
    with pytest.raises(LocalWorkerError):
        service.execute(value["jobId"], actor="owner")
    generated = run_approved(service, value)
    assert generated["status"] == "awaiting_result_approval"
    assert section in generated["result"]["output"]["text"]
    assert generated["result"]["output"]["networkUsed"] is False
    assert generated["result"]["output"]["shellUsed"] is False
    with pytest.raises(LocalWorkerError) as early_save:
        service.save_builder_draft(value["jobId"], confirmed=True, actor="owner")
    assert early_save.value.code == "save_requires_approval"
    service.decide_result(value["jobId"], "approve", "Approve exact deterministic proposal", actor="owner")
    saved = service.save_builder_draft(value["jobId"], confirmed=True, actor="owner")
    draft_id = saved["result"]["savedDraft"]["artifactId"]
    for fmt in ("txt", "md", "json"):
        exported = service.export_builder_result(value["jobId"], fmt, include_provenance=True, confirmed=True, actor="owner")
        assert Path(exported["result"]["exports"][-1]["path"]).suffix == f".{fmt}"
    con = connect()
    draft = con.execute("SELECT kind,authority_state,payload FROM artifacts WHERE id=?", (draft_id,)).fetchone()
    payload = json.loads(draft["payload"])
    assert tuple(draft[:2]) == (kind, "DRAFT")
    assert payload["inactive"] is True and payload["attached"] is False and payload["executed"] is False
    assert payload["published"] is False and payload["promoted"] is False
    assert con.execute("SELECT count(*) FROM artifact_relationships WHERE target_artifact_id=?", (draft_id,)).fetchone()[0] == 1
    con.close()
    assert service.rollback(value["jobId"], confirmed=True, actor="owner")["status"] == "rolled_back"
    assert (root / "a.md").read_bytes() == original


@pytest.mark.parametrize(
    "worker,profile,notes_key,controls_key,controls",
    [
        ("build-work-order-builder", "Fix defect", "buildNotes", "buildControls", {"buildGoal": "Fix safely"}),
        ("module-proposal-builder", "Adapter", "moduleNotes", "moduleControls", {"moduleName": "Bounded Adapter"}),
    ],
)
def test_release_016_builder_bounds_and_stale_source(kit, worker, profile, notes_key, controls_key, controls):
    service, _, root = kit
    base = {"projectId": "p", "workerId": worker, "destinationProfile": profile, "goal": "", "purpose": f"Prepare {profile}", controls_key: controls}
    with pytest.raises(LocalWorkerError) as duplicate:
        service.create_plan({**base, "sourceArtifactIds": ["a", "a"]})
    assert duplicate.value.code == "builder_sources_invalid"
    with pytest.raises(LocalWorkerError) as excessive:
        service.create_plan({**base, "sourceArtifactIds": [str(index) for index in range(5)]})
    assert excessive.value.code == "builder_sources_invalid"
    notes_only = service.create_plan({**base, "sourceArtifactIds": [], notes_key: "Exact temporary owner input"})
    assert notes_only["sources"][0]["artifactId"].startswith("build-input:" if worker.startswith("build") else "module-input:")
    sourced = service.create_plan({**base, "sourceArtifactIds": ["a"]})
    run_approved(service, sourced)
    (root / "a.md").write_text("changed after plan", encoding="utf-8")
    with pytest.raises(LocalWorkerError) as stale:
        service.decide_result(sourced["jobId"], "approve", "Approve", actor="owner")
    assert stale.value.code in {"source_hash_mismatch", "stale_plan"}


def test_build_v2_binds_free_first_registry_and_surfaces_create_our_own(kit):
    _old_service, connect, root = kit
    registry_root = Path(__file__).resolve().parents[1]
    capability_registry = CapabilityRegistry(registry_root / "config" / "capability-registry.json", root=registry_root)
    service = LocalWorkerKit(connect, root.parent.parent, capability_registry=capability_registry)
    value = service.create_plan({
        "projectId": "p", "workerId": "build-work-order-builder", "sourceArtifactIds": ["a"],
        "destinationProfile": "Local tool", "goal": "Use free-first evidence",
        "purpose": "Prepare background-removal work order",
        "buildControls": {
            "workingTitle": "Background removal capability",
            "capabilityRequest": "remove an image background",
            "buildGoal": "Add safe background removal",
            "requirements": "Preserve source image bytes",
            "constraints": "No paid service and no automatic install",
            "acceptanceCriteria": "Proposal is truthful and inactive",
            "testingExpectations": "Verify transparent output and unchanged source",
        },
    })
    context = value["plan"]["capabilityRegistryContext"]
    assert context["registryHash"] == capability_registry.registry_hash
    assert context["hardwareProfileHash"] == capability_registry.profile["profileHash"]
    assert context["replacementGroup"] == "background-removal"
    assert context["recommended"]["capabilityId"] == "external.opencv-grabcut-cpu-candidate"
    assert context["createOurOwn"] is False
    opencv = next(row for row in context["matched"] if row["capabilityId"] == "external.opencv-grabcut-cpu-candidate")
    assert opencv["status"] == "VERIFIED" and opencv["healthState"] == "HEALTHY"
    assert context["discoveredCandidates"][0]["capabilityId"] == "external.rembg-cpu-candidate"
    generated = run_approved(service, value)
    output = generated["result"]["output"]
    assert output["networkUsed"] is False and output["shellUsed"] is False
    assert "## Existing relevant capabilities" in output["text"]
    assert "OpenCV GrabCut Assisted Cutout" in output["text"]
    assert "rembg CPU Background Removal Candidate" in output["text"]
    assert "Use the verified capability" in output["text"]
    assert output["metadata"]["capabilityRegistryContext"]["registryHash"] == capability_registry.registry_hash


def test_build_v2_rejects_stale_capability_registry(kit):
    _old_service, connect, root = kit
    registry_root = Path(__file__).resolve().parents[1]
    capability_registry = CapabilityRegistry(registry_root / "config" / "capability-registry.json", root=registry_root)
    service = LocalWorkerKit(connect, root.parent.parent, capability_registry=capability_registry)
    value = service.create_plan({
        "projectId": "p", "workerId": "build-work-order-builder", "sourceArtifactIds": ["a"],
        "destinationProfile": "Local tool", "goal": "Prepare only", "purpose": "Prepare only",
        "buildControls": {"capabilityRequest": "remove an image background"},
    })
    service.decide_plan(value["jobId"], "approve", "Approve exact registry-bound plan", actor="owner")
    capability_registry.transition("external.rembg-cpu-candidate", "INSPECTING")
    with pytest.raises(LocalWorkerError) as stale:
        service.execute(value["jobId"], actor="owner")
    assert stale.value.code == "stale_capability_registry"


def test_module_v2_agent_skill_scaffold_is_text_only_and_inactive(kit):
    service, _connect, root = kit
    value = service.create_plan({
        "projectId": "p", "workerId": "module-proposal-builder", "sourceArtifactIds": [],
        "destinationProfile": "Agent Skill", "goal": "Proposal only", "purpose": "Prepare skill proposal",
        "moduleNotes": "Inspect registered sources safely.",
        "moduleControls": {
            "moduleName": "Source evidence inspector", "scaffoldType": "Agent Skill",
            "purpose": "Inspect source evidence", "permissionsCapabilities": "Read selected sources only",
            "acceptanceCriteria": "No script executes and no skill activates",
        },
    })
    generated = run_approved(service, value)
    output = generated["result"]["output"]
    assert "source-evidence-inspector/" in output["text"]
    assert "SKILL.md" in output["text"]
    assert "does not create or activate the folder" in output["text"]
    assert output["networkUsed"] is False and output["shellUsed"] is False
    assert not any(path.name == "source-evidence-inspector" for path in root.parent.rglob("*"))
