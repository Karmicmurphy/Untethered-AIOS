from __future__ import annotations

import hashlib
import json
from typing import Any


BUILDER_SCHEMA_VERSION = "builder-output-v1"
BUILDER_WORKERS = {
    "handoff-proposal-builder": {
        "builderType": "handoff",
        "profiles": (
            "Codex Build Handoff",
            "ChatGPT Continuation Handoff",
            "Human Technical Handoff",
            "Project Recovery Handoff",
        ),
        "sections": (
            "Title", "Purpose", "Current state", "Completed work",
            "Verified evidence", "Important files or artifacts", "Constraints",
            "Prohibited actions", "Known limitations", "Remaining work",
            "Recommended next action", "Acceptance criteria", "Source record",
            "Builder metadata",
        ),
    },
    "prompt-proposal-builder": {
        "builderType": "prompt",
        "profiles": (
            "Codex Implementation Prompt", "ChatGPT Research Prompt",
            "Local Model Task Prompt", "Human Work Order",
        ),
        "sections": (
            "Role", "Mission", "Starting state", "Selected evidence",
            "Required work", "Constraints", "Prohibited actions",
            "Verification requirements", "Required deliverables",
            "Stop conditions", "Final response format",
        ),
    },
    "draft-workshop": {
        "builderType": "writing-draft",
        "profiles": (
            "Rewrite clearly",
            "Shorten without losing meaning",
            "Expand rough notes",
            "Change tone",
            "Organize into a structured document",
        ),
        "sections": (
            "Output status", "Writing operation", "Source record",
            "Owner instructions", "Prepared writing task", "Draft scaffold",
            "Safety and provenance",
        ),
    },
    "evidence-compare": {
        "builderType": "research-comparison",
        "profiles": (
            "General comparison",
            "Factual consistency",
            "Implementation differences",
            "Project status differences",
            "Requirement coverage",
            "Conflicting claims",
            "Missing evidence",
        ),
        "sections": (
            "Output status", "Source inventory", "Hash and provenance table",
            "Comparison instructions", "Claim-capture sections",
            "Agreement matrix", "Difference matrix", "Contradiction register",
            "Evidence-gap register", "Unresolved-question list",
            "Synthesis outline", "Completion instructions",
        ),
    },
    "visual-brief-builder": {
        "builderType": "visual-brief",
        "profiles": (
            "Song or album cover",
            "Story or scene artwork",
            "Character concept",
            "Poster or promotional image",
            "Product or invention concept",
            "Memorial or emotional artwork",
            "General image concept",
        ),
        "sections": (
            "Project or concept title", "Visual purpose",
            "Source inventory and exact hashes", "Core visual concept",
            "Central subject", "Setting and environment", "Emotional target",
            "Composition and viewpoint", "Lighting direction", "Color direction",
            "Style and realism guidance", "Required visual elements",
            "Elements to avoid", "Text-overlay requirements",
            "Aspect ratio and output intent", "Final clean image-generation prompt",
            "Optional negative prompt or exclusion instructions",
            "Human artist production notes", "Source-preservation statement",
            "No-image-generated statement",
        ),
    },
    "song-production-brief-builder": {
        "builderType": "song-production-brief",
        "profiles": (
            "Full original song", "Song from existing story or source",
            "Instrumental composition", "Song rewrite or alternate arrangement",
            "Soundtrack or cinematic cue", "Memorial or emotional song",
            "Commercial, theme, or promotional music", "General music concept",
        ),
        "sections": (
            "Working title", "Song purpose", "Source inventory and exact hashes",
            "Temporary music-note identity", "Temporary lyric identity", "Core concept",
            "Emotional or narrative arc", "Genre and subgenre",
            "Tempo, key, and time-signature direction", "Vocal character and delivery",
            "Instrumentation plan", "Rhythm and groove", "Song-section structure",
            "Intro plan", "Verse plan", "Chorus plan",
            "Bridge, breakdown, or contrast section", "Solo or instrumental section",
            "Ending plan", "Dynamic progression", "Production texture",
            "Recording and mix direction", "Required elements", "Prohibited elements",
            "Lyric boundaries", "Owner-supplied lyrics or lyric fragments preserved exactly",
            "Unresolved musical decisions", "Final clean manual-use music-generation prompt",
            "Human musician or producer work notes", "Source-preservation statement",
            "No-music-generated statement",
        ),
    },
    "video-production-brief-builder": {
        "builderType": "video-production-brief",
        "profiles": (
            "Cinematic scene", "Music video", "Short-form vertical",
            "Talking / performance", "Surreal visual", "Documentary / story",
            "Product / demonstration", "Image-to-video concept",
        ),
        "sections": (
            "Working title", "Production objective", "Core concept",
            "Intended audience and use", "Format", "Target duration",
            "Aspect ratio and resolution intent", "Story and sequence overview",
            "Opening beat", "Main progression", "Closing beat",
            "Subject and character direction", "Environment and location",
            "Wardrobe and appearance", "Props and objects", "Visual style",
            "Color palette", "Lighting", "Composition", "Camera language",
            "Lens and framing intent", "Camera movement", "Subject movement",
            "Shot list and shot ideas", "Transitions", "Pacing and rhythm",
            "Continuity requirements", "Dialogue", "Narration and voice",
            "Music", "Sound design", "On-screen text",
            "Effects and compositing notes", "Source and reference notes",
            "Production constraints", "Safety legal and consent notes",
            "Unresolved decisions", "Final production prompt and handoff block",
            "Source-preservation statement", "No-video-generated statement",
        ),
    },
    "build-work-order-builder": {
        "builderType": "build-work-order",
        "profiles": (
            "Add feature", "Fix defect", "UI refinement", "Local tool",
            "Integration", "Refactor bounded area", "Test/verification task",
            "Deployment work order",
        ),
        "sections": (
            "Work order title", "Objective", "Current TWIS context", "Existing context", "Desired outcome",
            "In scope", "Out of scope", "Requirements", "Constraints",
            "Existing relevant capabilities", "Free options found", "Hardware fit",
            "Recommended path", "Why", "Relevant sources", "Relevant files and components", "UI behavior",
            "Backend behavior", "Data and persistence", "External dependencies",
            "Input contract", "Output contract", "Permissions", "Network", "Cost",
            "Security and safety", "Performance", "Provenance", "Receipts", "Failure behavior",
            "Acceptance criteria", "Test plan", "Deployment expectations",
            "Rollback expectations", "Unresolved decisions",
            "Final implementation handoff block", "Source-preservation statement",
            "No-execution statement",
        ),
    },
    "module-proposal-builder": {
        "builderType": "module-proposal",
        "profiles": (
            "Local tool", "Worker", "Adapter", "Importer", "Exporter",
            "Media tool", "Research tool", "System utility", "Experimental module",
            "TWIS native capability",
            "Agent Skill", "Local Python worker", "Local JavaScript worker",
            "Disposable worker", "MCP server wrapper", "MCP client adapter",
            "WASI component proposal", "Comfy workflow adapter", "Cloudflare free-tier worker",
        ),
        "sections": (
            "Module name", "Purpose", "User problem", "Target Workshop location",
            "Capability summary", "Inputs", "Outputs", "Dependencies",
            "Runtime boundary", "Data and storage", "Permissions", "UI integration",
            "Existing Workshop integration", "Licensing considerations",
            "Safety and security considerations", "Performance considerations",
            "Failure behavior", "Testing plan", "Recovery", "Rollback",
            "Acceptance criteria", "Unresolved decisions",
            "Proposed scaffold", "Final implementation handoff", "Source-preservation statement",
            "No-installation statement",
        ),
    },
    "local-ai-rewrite": {
        "builderType": "local-ai-writing-proposal",
        "profiles": (
            "Rewrite while preserving meaning",
            "Brainstorm story ideas", "Continue passage", "Rewrite selection", "Make darker",
            "Make funnier", "Make more emotional", "Make more direct", "Make stranger or surreal",
            "Improve dialogue", "Suggest dialogue", "Suggest next scene", "Develop character",
            "Generate alternate version", "Suggest structure", "Summarize direction",
            "Suggest creative possibilities",
            "Suggest beat pattern", "Suggest BPM", "Suggest chord progression",
            "Suggest bassline", "Suggest arrangement", "Suggest song structure",
            "Suggest instrumentation", "Suggest transition or fill",
            "Suggest production direction", "Help with lyrics",
        ),
        "sections": (
            "Output status", "Writing task", "Proposed rewrite",
            "Source record", "Local inference provenance",
            "Source-preservation statement", "Approval boundary",
        ),
    },
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def _source_record(sources: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"- {source['title']} | {source['kind']} | ID {source['artifactId']} | "
        f"SHA-256 {source['sha256']} | {source['bytes']} bytes | project {source['projectId']}"
        for source in sources
    )


def _evidence(sources: list[dict[str, Any]]) -> str:
    blocks = []
    for source in sources:
        content = str(source.get("content") or "").strip()
        excerpt = content[:4000] if content else "[No text excerpt available]"
        blocks.append(
            f"Source: {source['title']}\nID: {source['artifactId']}\n"
            f"SHA-256: {source['sha256']}\nExact bounded excerpt:\n{excerpt}"
        )
    return "\n\n".join(blocks)


def _comparison_tables(sources: list[dict[str, Any]]) -> dict[str, str]:
    line_sets: list[set[str]] = []
    captures: list[str] = []
    for index, source in enumerate(sources, start=1):
        lines = [line.strip() for line in str(source.get("content") or "").splitlines() if line.strip()]
        line_sets.append(set(lines))
        exact_lines = "\n".join(f"  - {line}" for line in lines[:20]) or "  - [No nonblank lines]"
        captures.append(
            f"### Source {index}: {source['title']}\n"
            f"- Source ID: {source['artifactId']}\n"
            f"- Exact candidate lines for manual claim review:\n{exact_lines}\n"
            "- Claims accepted as factual: [Not assessed]\n"
            "- Claims needing verification: [Not assessed]"
        )
    agreement_rows = ["| Pair | Exact whole-text match | Shared exact nonblank lines | Semantic agreement |", "|---|---:|---:|---|"]
    difference_rows = ["| Pair | Exact whole-text difference | Source-specific exact lines | Semantic difference |", "|---|---:|---:|---|"]
    for left in range(len(sources)):
        for right in range(left + 1, len(sources)):
            pair = f"Source {left + 1} ↔ Source {right + 1}"
            same = sources[left]["sha256"] == sources[right]["sha256"]
            shared = len(line_sets[left] & line_sets[right])
            unique = len(line_sets[left] ^ line_sets[right])
            agreement_rows.append(f"| {pair} | {'yes' if same else 'no'} | {shared} | Not assessed |")
            difference_rows.append(f"| {pair} | {'no' if same else 'yes'} | {unique} | Not assessed |")
    return {
        "captures": "\n\n".join(captures),
        "agreements": "\n".join(agreement_rows),
        "differences": "\n".join(difference_rows),
    }


def build_output(
    *, worker_id: str, worker_version: str, job_id: str, plan_id: str,
    profile: str, goal: str, sources: list[dict[str, Any]], created_at: str,
    builder_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    spec = BUILDER_WORKERS[worker_id]
    record = _source_record(sources)
    evidence = _evidence(sources)
    prohibited = (
        "Do not modify original sources. Do not execute, install, activate, attach, "
        "submit, contact an external service, or infer facts not supported by the selected evidence."
    )
    if spec["builderType"] == "handoff":
        section_values = {
            "Title": f"{profile}: {goal[:120]}",
            "Purpose": goal,
            "Current state": "Continue only from the explicitly selected, hash-bound Workshop sources below.",
            "Completed work": "Treat only work directly shown in the selected evidence as completed.",
            "Verified evidence": evidence,
            "Important files or artifacts": record,
            "Constraints": "Preserve source authority, provenance, existing behavior, and explicit approval boundaries.",
            "Prohibited actions": prohibited,
            "Known limitations": "This package is deterministic and local; it does not independently interpret, execute, or verify external claims.",
            "Remaining work": goal,
            "Recommended next action": "Inspect the selected evidence, confirm the starting state, then perform the smallest verifiable next step.",
            "Acceptance criteria": "Report concrete changes, tests, evidence, unresolved defects, and deliberate limits without claiming unperformed work.",
            "Source record": record,
            "Builder metadata": f"Contract {BUILDER_SCHEMA_VERSION}; worker {worker_id} {worker_version}; job {job_id}; plan {plan_id}.",
        }
    elif spec["builderType"] == "prompt":
        section_values = {
            "Role": f"Act as the responsible {profile} collaborator for the selected Workshop material.",
            "Mission": goal,
            "Starting state": "Use only the explicitly selected, hash-bound sources as the starting evidence.",
            "Selected evidence": evidence,
            "Required work": goal,
            "Constraints": "Stay within the selected sources and preserve working behavior, provenance, and owner approval boundaries.",
            "Prohibited actions": prohibited,
            "Verification requirements": "Inspect before modifying; verify hashes and relevant tests; distinguish verified facts, inference, and unknowns.",
            "Required deliverables": "Return the completed work plus exact changed scope, verification results, and remaining limitations.",
            "Stop conditions": "Stop for destructive ambiguity, stale evidence, data-loss risk, missing authority, or a real product defect outside the authorized scope.",
            "Final response format": "Lead with PASS or FAIL where applicable, then summarize changes, evidence, tests, and the single best next action.",
        }
    elif spec["builderType"] == "writing-draft":
        instructions = goal.strip() or "No additional owner instructions."
        operation_guidance = {
            "Rewrite clearly": "Improve clarity, sentence flow, and readability while preserving meaning and factual claims.",
            "Shorten without losing meaning": "Remove repetition and excess wording while preserving every material fact, constraint, and qualification.",
            "Expand rough notes": "Turn the notes into coherent prose without inventing facts, decisions, or evidence.",
            "Change tone": "Apply only the tone described in the owner instructions while preserving meaning and provenance.",
            "Organize into a structured document": "Arrange the material under useful headings in a logical order without adding unsupported content.",
        }[profile]
        task = (
            "Prepare one proposed written draft from the exact source text below. "
            f"Operation: {profile}. {operation_guidance} Owner instructions: {instructions} "
            "Return only the proposed draft. Do not claim that work was generated, sent, published, or applied.\n\n"
            f"{evidence}"
        )
        section_values = {
            "Output status": "Prepared locally as a ready-to-use writing task and draft scaffold. No language model or external provider was called, and no rewritten prose is being falsely represented as generated.",
            "Writing operation": profile,
            "Source record": record,
            "Owner instructions": instructions,
            "Prepared writing task": task,
            "Draft scaffold": "[Proposed draft text will be produced only when the owner deliberately uses this approved task with a writing engine or writes into this inactive draft. Original source text remains unchanged.]",
            "Safety and provenance": "The source identity and SHA-256 are bound to this result. This inactive proposal is not executed, attached, activated, submitted, published, promoted, or applied to its source.",
        }
    elif spec["builderType"] == "research-comparison":
        instructions = goal.strip() or "No additional owner comparison instructions."
        tables = _comparison_tables(sources)
        inventory = "\n".join(
            f"{index}. {source['title']} — {source['kind']} — {source['bytes']} bytes — ID {source['artifactId']}"
            for index, source in enumerate(sources, start=1)
        )
        provenance = "\n".join(
            ["| Order | Title | Source ID | SHA-256 | Project |", "|---:|---|---|---|---|"]
            + [
                f"| {index} | {source['title']} | {source['artifactId']} | {source['sha256']} | {source['projectId']} |"
                for index, source in enumerate(sources, start=1)
            ]
        )
        section_values = {
            "Output status": "Prepared deterministically from explicitly selected registered sources. No language model, internet research, provider, semantic classifier, or external retrieval was used. Exact textual facts are labeled separately from unassessed semantic questions.",
            "Source inventory": inventory,
            "Hash and provenance table": provenance,
            "Comparison instructions": f"Focus: {profile}. Owner instructions: {instructions}",
            "Claim-capture sections": tables["captures"],
            "Agreement matrix": tables["agreements"],
            "Difference matrix": tables["differences"],
            "Contradiction register": "No semantic contradictions were inferred. Record candidate contradictions here only after checking the exact source passages and source authority.",
            "Evidence-gap register": "No semantic evidence gaps were inferred. Record missing support here only after reviewing each source-specific claim and the selected comparison focus.",
            "Unresolved-question list": "1. Which source-specific claims require authority or date verification?\n2. Which exact textual differences are materially meaningful?\n3. Which apparent conflicts are scope, terminology, version, or factual conflicts?",
            "Synthesis outline": "1. Comparison purpose and source authority\n2. Confirmed exact textual overlaps\n3. Confirmed exact textual differences\n4. Human-verified agreements and contradictions\n5. Evidence gaps and unresolved questions\n6. Bounded synthesis and next verification action",
            "Completion instructions": "Complete semantic fields manually, or export this approved comparison as a separate prompt for a deliberately chosen tool. Verify every semantic conclusion against the cited source ID and hash. Do not modify sources or claim live research, provider analysis, execution, publication, or submission.",
        }
    elif spec["builderType"] == "visual-brief":
        controls = dict(builder_data or {})
        unresolved = "[Unresolved creative decision]"
        supplied = lambda key: str(controls.get(key) or "").strip() or unresolved
        notes_sources = [source for source in sources if source.get("kind") == "temporary-visual-notes"]
        notes = str(notes_sources[0].get("content") or "").strip() if notes_sources else ""
        source_priority = supplied("referenceSourcePriority")
        prompt_parts = [
            f"Visual purpose: {profile}.",
            f"Concept title: {supplied('conceptTitle')}.",
            f"Central subject: {supplied('centralSubject')}.",
            f"Setting: {supplied('setting')}.",
            f"Mood and emotion: {supplied('moodEmotion')}.",
            f"Visual style: {supplied('visualStyle')}.",
            f"Composition: {supplied('composition')}.",
            f"Camera viewpoint: {supplied('cameraViewpoint')}.",
            f"Lighting: {supplied('lighting')}.",
            f"Color direction: {supplied('colorDirection')}.",
            f"Aspect ratio: {supplied('aspectRatio')}.",
            f"Realism level: {supplied('realismLevel')}.",
            f"Required text: {supplied('requiredText')}.",
            f"Required elements: {supplied('requiredElements')}.",
            f"Reference-source priority: {source_priority}.",
        ]
        if notes:
            prompt_parts.append(f"Owner visual notes: {notes}.")
        if str(controls.get("additionalInstructions") or "").strip():
            prompt_parts.append(f"Additional instructions: {controls['additionalInstructions'].strip()}.")
        prompt_parts.append("Do not add prohibited text or elements. Preserve uncertainty where the brief marks an unresolved creative decision.")
        exclusions = "; ".join(
            value for value in (str(controls.get("prohibitedText") or "").strip(), str(controls.get("prohibitedElements") or "").strip()) if value
        ) or "[No owner-supplied exclusions; do not infer additional exclusions.]"
        source_inventory = record or "Owner-entered visual notes only; no registered source was selected."
        section_values = {
            "Project or concept title": supplied("conceptTitle"),
            "Visual purpose": profile,
            "Source inventory and exact hashes": source_inventory,
            "Core visual concept": notes or "[No owner-entered visual notes. Use only the explicitly supplied controls and selected source references; no semantic source interpretation was performed.]",
            "Central subject": supplied("centralSubject"),
            "Setting and environment": supplied("setting"),
            "Emotional target": supplied("moodEmotion"),
            "Composition and viewpoint": f"Composition: {supplied('composition')}\nCamera viewpoint: {supplied('cameraViewpoint')}",
            "Lighting direction": supplied("lighting"),
            "Color direction": supplied("colorDirection"),
            "Style and realism guidance": f"Style: {supplied('visualStyle')}\nRealism: {supplied('realismLevel')}",
            "Required visual elements": supplied("requiredElements"),
            "Elements to avoid": f"Prohibited elements: {supplied('prohibitedElements')}\nProhibited text: {supplied('prohibitedText')}",
            "Text-overlay requirements": f"Required text: {supplied('requiredText')}\nProhibited text: {supplied('prohibitedText')}",
            "Aspect ratio and output intent": f"Aspect ratio: {supplied('aspectRatio')}\nPurpose: {profile}",
            "Final clean image-generation prompt": " ".join(prompt_parts),
            "Optional negative prompt or exclusion instructions": exclusions,
            "Human artist production notes": f"Use the registered source identities and hashes as provenance references in owner-selected order. Source priority: {source_priority}. Resolve every placeholder with the owner before production. No source was semantically interpreted by a model.",
            "Source-preservation statement": "Every registered source remains unchanged. Owner-entered visual notes are hash-identified temporary job input and are not silently registered as permanent source material.",
            "No-image-generated statement": "No image was generated, rendered, downloaded, submitted, published, or sent to a provider. This is only an approved-ready visual brief and manual-use prompt.",
        }
    elif spec["builderType"] == "song-production-brief":
        controls = dict(builder_data or {})
        unresolved = "Unresolved musical decision"
        supplied = lambda key: str(controls.get(key) or "").strip() or unresolved
        note_source = next((s for s in sources if s.get("kind") == "temporary-music-notes"), None)
        lyric_source = next((s for s in sources if s.get("kind") == "temporary-music-lyrics"), None)
        notes = str((note_source or {}).get("content") or "")
        lyrics = str((lyric_source or {}).get("content") or "")
        note_id = str((note_source or {}).get("artifactId") or "None supplied")
        lyric_id = str((lyric_source or {}).get("artifactId") or "None supplied")
        inventory = record or "No registered source selected; only hash-identified temporary owner input was used."
        prompt_fields = (
            ("Purpose", profile), ("Working title", supplied("workingTitle")),
            ("Central subject", supplied("centralSubject")), ("Emotional arc", supplied("emotionalArc")),
            ("Genre", supplied("genre")), ("Subgenre", supplied("subgenre")),
            ("Tempo or BPM", supplied("tempoBpm")), ("Key or tonal center", supplied("tonalCenter")),
            ("Time signature", supplied("timeSignature")), ("Vocal type", supplied("vocalType")),
            ("Vocal delivery", supplied("vocalDelivery")), ("Instrumentation", supplied("instrumentation")),
            ("Rhythm and groove", supplied("rhythmGroove")), ("Song structure", supplied("songStructure")),
            ("Production texture", supplied("productionTexture")), ("Recording character", supplied("recordingCharacter")),
            ("Approximate duration", supplied("approximateDuration")),
        )
        clean_prompt = "Prepare a song-production plan for manual use. " + " ".join(f"{k}: {v}." for k, v in prompt_fields)
        if notes.strip():
            clean_prompt += f" Owner music notes: {notes}"
        if lyrics.strip():
            clean_prompt += " Preserve the following owner-supplied lyric text exactly, without rewriting or completing it:\n" + lyrics
        clean_prompt += " Do not invent lyrics, melody, chords, analysis, source meaning, or production conclusions. Keep missing choices labeled Unresolved musical decision."
        section_values = {
            "Working title": supplied("workingTitle"), "Song purpose": profile,
            "Source inventory and exact hashes": inventory,
            "Temporary music-note identity": note_id, "Temporary lyric identity": lyric_id,
            "Core concept": notes if notes.strip() else supplied("centralSubject"),
            "Emotional or narrative arc": supplied("emotionalArc"),
            "Genre and subgenre": f"Genre: {supplied('genre')}\nSubgenre: {supplied('subgenre')}",
            "Tempo, key, and time-signature direction": f"Tempo or BPM: {supplied('tempoBpm')}\nKey or tonal center: {supplied('tonalCenter')}\nTime signature: {supplied('timeSignature')}",
            "Vocal character and delivery": f"Vocal type: {supplied('vocalType')}\nVocal delivery: {supplied('vocalDelivery')}",
            "Instrumentation plan": supplied("instrumentation"), "Rhythm and groove": supplied("rhythmGroove"),
            "Song-section structure": supplied("songStructure"), "Intro plan": supplied("intro"),
            "Verse plan": supplied("verseTreatment"), "Chorus plan": supplied("chorusTreatment"),
            "Bridge, breakdown, or contrast section": supplied("bridgeBreakdown"),
            "Solo or instrumental section": supplied("soloInstrumental"), "Ending plan": supplied("ending"),
            "Dynamic progression": supplied("dynamicBuild"), "Production texture": supplied("productionTexture"),
            "Recording and mix direction": f"Recording character: {supplied('recordingCharacter')}\nAdditional instructions: {supplied('additionalInstructions')}",
            "Required elements": supplied("requiredElements"), "Prohibited elements": supplied("prohibitedElements"),
            "Lyric boundaries": f"Boundaries: {supplied('lyricBoundaries')}\nExplicit-language preference: {supplied('explicitLanguagePreference')}",
            "Owner-supplied lyrics or lyric fragments preserved exactly": lyrics if lyrics else unresolved,
            "Unresolved musical decisions": "Every field labeled Unresolved musical decision remains for the owner, musician, producer, or separately chosen tool to decide.",
            "Final clean manual-use music-generation prompt": clean_prompt,
            "Human musician or producer work notes": f"Reference influences: {supplied('referenceInfluences')}\nSource priority: {supplied('referenceSourcePriority')}\nApproximate duration: {supplied('approximateDuration')}",
            "Source-preservation statement": "Every registered source remains unchanged. Temporary notes and lyrics are content-hash-bound job inputs and were not registered as permanent sources. Owner lyrics are reproduced exactly.",
            "No-music-generated statement": "No music, lyrics, vocals, melody, chords, instrumentation, or audio was generated, played, rendered, submitted, published, or sent to a provider.",
        }
    elif spec["builderType"] == "video-production-brief":
        controls = dict(builder_data or {})
        unresolved = "Unresolved production decision"
        supplied = lambda key: str(controls.get(key) or "").strip() or unresolved
        note_source = next((s for s in sources if s.get("kind") == "temporary-video-notes"), None)
        notes = str((note_source or {}).get("content") or "")
        note_id = str((note_source or {}).get("artifactId") or "None supplied")
        inventory = record or "No registered source selected; only hash-identified temporary owner video notes were used."
        prompt_fields = (
            ("Video type", profile), ("Working title", supplied("workingTitle")),
            ("Production objective", supplied("productionGoal")),
            ("Intended audience/use", supplied("intendedAudience")),
            ("Target duration", supplied("targetDuration")),
            ("Aspect ratio", supplied("aspectRatio")),
            ("Resolution intent", supplied("resolutionIntent")),
            ("Visual style", supplied("visualStyle")), ("Pacing", supplied("pacing")),
            ("Camera language", supplied("cameraLanguage")),
            ("Environment/location", supplied("environmentLocation")),
            ("Subject/character", supplied("subjectCharacterNotes")),
            ("Lighting", supplied("lighting")), ("Color palette", supplied("colorPalette")),
            ("Shot ideas", supplied("shotIdeas")), ("Continuity", supplied("continuityRequirements")),
        )
        handoff = "Prepare this video-production brief for deliberate manual use. " + " ".join(f"{key}: {value}." for key, value in prompt_fields)
        if notes.strip():
            handoff += f" Owner video notes: {notes}"
        handoff += " Do not render, generate, upload, publish, or submit video. Do not invent source meaning. Keep missing choices labeled Unresolved production decision."
        section_values = {
            "Working title": supplied("workingTitle"),
            "Production objective": supplied("productionGoal"),
            "Core concept": notes if notes.strip() else supplied("coreConcept"),
            "Intended audience and use": supplied("intendedAudience"),
            "Format": profile,
            "Target duration": supplied("targetDuration"),
            "Aspect ratio and resolution intent": f"Aspect ratio: {supplied('aspectRatio')}\nResolution intent: {supplied('resolutionIntent')}",
            "Story and sequence overview": supplied("storySequence"),
            "Opening beat": supplied("openingBeat"),
            "Main progression": supplied("mainProgression"),
            "Closing beat": supplied("closingBeat"),
            "Subject and character direction": supplied("subjectCharacterNotes"),
            "Environment and location": supplied("environmentLocation"),
            "Wardrobe and appearance": supplied("wardrobeAppearance"),
            "Props and objects": supplied("propsObjects"),
            "Visual style": supplied("visualStyle"),
            "Color palette": supplied("colorPalette"),
            "Lighting": supplied("lighting"),
            "Composition": supplied("composition"),
            "Camera language": supplied("cameraLanguage"),
            "Lens and framing intent": supplied("lensFraming"),
            "Camera movement": supplied("cameraMovement"),
            "Subject movement": supplied("subjectMovement"),
            "Shot list and shot ideas": supplied("shotIdeas"),
            "Transitions": supplied("transitionStyle"),
            "Pacing and rhythm": supplied("pacing"),
            "Continuity requirements": supplied("continuityRequirements"),
            "Dialogue": supplied("audioDialogue"),
            "Narration and voice": supplied("narrationVoice"),
            "Music": supplied("musicNotes"),
            "Sound design": supplied("soundDesignNotes"),
            "On-screen text": supplied("onScreenText"),
            "Effects and compositing notes": supplied("effectsCompositing"),
            "Source and reference notes": f"{inventory}\nTemporary video-note identity: {note_id}\nReference priority: {supplied('referenceSourcePriority')}",
            "Production constraints": supplied("productionConstraints"),
            "Safety legal and consent notes": supplied("safetyLegalConsent"),
            "Unresolved decisions": supplied("unresolvedDecisions"),
            "Final production prompt and handoff block": handoff,
            "Source-preservation statement": "Every registered source remains unchanged. Owner video notes are content-hash-bound temporary job input and were not registered as a permanent source.",
            "No-video-generated statement": "No video was generated, rendered, downloaded, uploaded, submitted, published, or sent to a provider. This output is only a governed production brief.",
        }
    elif spec["builderType"] == "build-work-order":
        controls = dict(builder_data or {})
        capability_context = dict(controls.pop("_capabilityRegistryContext", {}) or {})
        unresolved = "Unresolved implementation decision"
        supplied = lambda key: str(controls.get(key) or "").strip() or unresolved
        input_source = next((s for s in sources if s.get("kind") == "temporary-build-input"), None)
        owner_notes = str((input_source or {}).get("ownerNotes") or "")
        inventory = _source_record([s for s in sources if s.get("kind") != "temporary-build-input"]) or "No registered source selected."
        def capability_line(item: dict[str, Any] | None) -> str:
            if not item:
                return "None verified."
            fit = dict(item.get("hardwareFit") or {})
            return (
                f"{item.get('name')} [{item.get('capabilityId')}] — {item.get('status')} — "
                f"health {item.get('healthState', 'UNKNOWN')} — "
                f"{item.get('costClass')} — hardware {fit.get('state', 'UNKNOWN')} — "
                f"network {item.get('networkRequirement')} — authority {item.get('authorityLevel')}"
            )

        matched = [item for item in capability_context.get("matched", []) if isinstance(item, dict)]
        discovered = [item for item in capability_context.get("discoveredCandidates", []) if isinstance(item, dict)]
        recommended = capability_context.get("recommended") if isinstance(capability_context.get("recommended"), dict) else None
        existing_capabilities = "\n".join(f"- {capability_line(item)}" for item in matched) or "No registry match."
        free_options = "\n".join(
            f"- {capability_line(item)}" for item in matched
            if item.get("costClass") in {"local-free", "open-source-free", "free-tier", "free-with-account"}
        ) or "No declared free match."
        hardware_fit = "\n".join(
            f"- {item.get('name')}: {(item.get('hardwareFit') or {}).get('state', 'UNKNOWN')} — "
            f"{' '.join((item.get('hardwareFit') or {}).get('reasons', []))}"
            for item in matched
        ) or "No matched capability to qualify."
        if recommended:
            path_recommendation = f"Use the verified capability: {capability_line(recommended)}"
            why = str(capability_context.get("decision") or "It is the highest-ranked verified free fit.")
        elif discovered:
            path_recommendation = (
                "Inspect and test the discovered candidate before any use: "
                + capability_line(discovered[0])
                + " If it does not pass, use CREATE OUR OWN to produce a proposal-only scaffold."
            )
            why = str(capability_context.get("decision") or "No verified free hardware-fit capability exists.")
        else:
            path_recommendation = "Use CREATE OUR OWN to prepare a governed proposal-only capability scaffold."
            why = str(capability_context.get("decision") or "No relevant registered capability exists.")
        handoff = (
            f"Implement this bounded {profile.lower()} work order. Objective: {supplied('buildGoal')}. "
            f"Requirements: {supplied('requirements')}. Constraints: {supplied('constraints')}. "
            f"Acceptance criteria: {supplied('acceptanceCriteria')}. Testing: {supplied('testingExpectations')}. "
            "Inspect before modifying, preserve working behavior, report exact scope and evidence, and stop for destructive ambiguity. "
            "Do not treat this proposal as approval to execute code, modify files, invoke a shell, submit to Codex, contact a provider, or deploy."
        )
        section_values = {
            "Work order title": supplied("workingTitle"), "Objective": supplied("buildGoal"),
            "Current TWIS context": (
                f"Capability request: {capability_context.get('request') or supplied('capabilityRequest')}. "
                f"Registry hash: {capability_context.get('registryHash') or 'Not available'}. "
                f"Hardware profile hash: {capability_context.get('hardwareProfileHash') or 'Not available'}."
            ),
            "Existing context": supplied("existingContext"), "Desired outcome": supplied("desiredOutcome"),
            "In scope": supplied("inScope"), "Out of scope": supplied("outOfScope"),
            "Requirements": supplied("requirements"), "Constraints": supplied("constraints"),
            "Existing relevant capabilities": existing_capabilities,
            "Free options found": free_options,
            "Hardware fit": hardware_fit,
            "Recommended path": path_recommendation,
            "Why": why,
            "Relevant sources": f"{inventory}\nReference-source priority: {supplied('referenceSourcePriority')}",
            "Relevant files and components": supplied("relevantFilesComponents"),
            "UI behavior": supplied("uiRequirements"), "Backend behavior": supplied("backendRequirements"),
            "Data and persistence": supplied("dataPersistence"), "External dependencies": supplied("externalDependencies"),
            "Input contract": "Use only explicit owner input, selected registered sources, and the hash-bound capability registry snapshot named above.",
            "Output contract": "Produce a bounded implementation candidate, exact manifest, verification evidence, and rollback material; do not treat a work order as execution authority.",
            "Permissions": "Only permissions explicitly approved by the later implementation release may be used. Unknown or expanded permissions fail closed.",
            "Network": "No network use is authorized by this work order unless a later exact plan names and approves it.",
            "Cost": "Prefer local-free and open-source-free capability. Paid-required capability cannot become a core dependency.",
            "Security and safety": supplied("securitySafety"), "Performance": supplied("performanceLimits"),
            "Provenance": "Retain capability ID/version, registry hash, input source IDs/hashes, worker/engine identity, timestamps, owner approvals, and output hashes.",
            "Receipts": "Record plan, plan decision, execution/validation evidence, result decision, inactive save/export, and rollback through existing TWIS receipts.",
            "Failure behavior": supplied("failureBehavior"), "Acceptance criteria": supplied("acceptanceCriteria"),
            "Test plan": supplied("testingExpectations"), "Deployment expectations": supplied("deploymentExpectations"),
            "Rollback expectations": supplied("rollbackExpectations"), "Unresolved decisions": supplied("unresolvedDecisions"),
            "Final implementation handoff block": handoff,
            "Source-preservation statement": "Every registered source remains unchanged. Owner build notes and controls are hash-bound temporary job input and were not registered as a permanent source.",
            "No-execution statement": "No code, shell command, file modification, deployment, provider call, cloud action, or external submission was executed. This output is only a governed work order.",
        }
        if owner_notes:
            section_values["Existing context"] += f"\n\nOwner notes preserved exactly:\n{owner_notes}"
    else:
        controls = dict(builder_data or {})
        unresolved = "Unresolved module decision"
        supplied = lambda key: str(controls.get(key) or "").strip() or unresolved
        input_source = next((s for s in sources if s.get("kind") == "temporary-module-input"), None)
        owner_notes = str((input_source or {}).get("ownerNotes") or "")
        inventory = _source_record([s for s in sources if s.get("kind") != "temporary-module-input"]) or "No registered source selected."
        scaffold_type = str(controls.get("scaffoldType") or profile).strip()
        module_name = supplied("moduleName")
        slug = "".join(character if character.isalnum() else "-" for character in module_name.lower()).strip("-") or "proposed-capability"
        scaffold_templates = {
            "TWIS native capability": f"companion/capabilities/{slug}.py\nconfig/capabilities/{slug}.json\ntests/test_{slug.replace('-', '_')}.py\n\nUse existing TWIS authority, receipts, provenance, and rollback; no parallel subsystem.",
            "Agent Skill": (
                f"{slug}/\n  SKILL.md\n  references/ (only if needed)\n  scripts/ (only if separately inspected and approved)\n  assets/ (only if needed)\n\n"
                "SKILL.md must declare name, description, when to use, when not to use, workflow, safety, examples, edge cases, required tools, and compatibility. This text proposal does not create or activate the folder."
            ),
            "Local Python worker": f"companion/workers/{slug}.py\nconfig/capabilities/{slug}.json\ntests/test_{slug.replace('-', '_')}.py\n\nFixed entry point, bounded inputs, declared permissions, no arbitrary command surface.",
            "Local JavaScript worker": f"app/assets/{slug}.js\nconfig/capabilities/{slug}.json\ntests/{slug}.test.js\n\nDependency-free bounded worker; no dynamic code or remote import.",
            "Disposable worker": f"workers/{slug}/contract.json\nworkers/{slug}/README.md\ntests/{slug}-contract.*\n\nExecution environment and teardown remain separately approved.",
            "MCP server wrapper": f"adapters/mcp/{slug}.json\ncompanion/adapters/{slug}_mcp.py\ntests/test_{slug.replace('-', '_')}_mcp.py\n\nRegister metadata first; tools remain DISCOVERED and invocation disabled.",
            "MCP client adapter": f"adapters/mcp/{slug}.json\ncompanion/adapters/{slug}_client.py\ntests/test_{slug.replace('-', '_')}_client.py\n\nFixed server descriptor only; no arbitrary endpoint or auto-enabled tools.",
            "WASI component proposal": f"components/{slug}/component.json\ncomponents/{slug}/world.wit\ntests/{slug}-contract.*\n\nContract only until a runtime and sandbox proof receive separate approval.",
            "Comfy workflow adapter": f"workflows/comfy/{slug}.json\nconfig/capabilities/{slug}.json\ntests/{slug}-contract.*\n\nDeclare workflow, nodes, models, runtime, hardware, and worker requirements; no ComfyUI install or execution.",
            "Cloudflare free-tier worker": f"adapters/cloudflare/{slug}.json\nworkers/{slug}/README.md\ntests/{slug}-contract.*\n\nProposal only; no account, credential, deployment, billing, or provider call.",
        }
        proposed_scaffold = scaffold_templates.get(
            scaffold_type,
            f"Capability type: {scaffold_type}\nSuggested contract: config/capabilities/{slug}.json\nImplementation files remain unresolved until a separately approved Build work order.",
        )
        handoff = (
            f"Evaluate and implement this proposed {profile.lower()} only after a separate authorized build decision. "
            f"Module: {supplied('moduleName')}. Purpose: {supplied('purpose')}. Runtime boundary: {supplied('localCloudBoundary')}. "
            f"Permissions: {supplied('permissionsCapabilities')}. Acceptance criteria: {supplied('acceptanceCriteria')}. "
            "Do not install, execute, download, activate, fetch dependencies, or contact a provider from this proposal."
        )
        section_values = {
            "Module name": supplied("moduleName"), "Purpose": supplied("purpose"),
            "User problem": supplied("problemSolved"), "Target Workshop location": supplied("targetRoom"),
            "Capability summary": f"Proposal type: {profile}\n{owner_notes or unresolved}",
            "Inputs": supplied("inputs"), "Outputs": supplied("outputs"), "Dependencies": supplied("dependencies"),
            "Runtime boundary": supplied("localCloudBoundary"), "Data and storage": supplied("dataStorageNeeds"),
            "Permissions": supplied("permissionsCapabilities"), "UI integration": supplied("uiNeeds"),
            "Existing Workshop integration": f"{supplied('integrationPoints')}\nRelevant sources:\n{inventory}",
            "Licensing considerations": supplied("licensingNotes"),
            "Safety and security considerations": supplied("risks"),
            "Performance considerations": supplied("hardwareExpectations"), "Failure behavior": supplied("failureBehavior"),
            "Testing plan": supplied("testingRequirements"), "Recovery": supplied("recoveryRequirements"),
            "Rollback": supplied("rollbackRequirements"), "Acceptance criteria": supplied("acceptanceCriteria"),
            "Unresolved decisions": supplied("unresolvedDecisions"),
            "Proposed scaffold": proposed_scaffold,
            "Final implementation handoff": handoff,
            "Source-preservation statement": "Every registered source remains unchanged. Owner module notes and controls are hash-bound temporary job input and were not registered as a permanent source.",
            "No-installation statement": "No module, package, dependency, executable, adapter, provider, or remote asset was installed, downloaded, executed, activated, or contacted.",
        }
    text = "\n\n".join(f"## {name}\n\n{section_values[name].strip()}" for name in spec["sections"])
    metadata = {
        "schemaVersion": BUILDER_SCHEMA_VERSION,
        "builderType": spec["builderType"],
        "destinationProfile": profile,
        "workerId": worker_id,
        "workerVersion": worker_version,
        "jobId": job_id,
        "planId": plan_id,
        "createdAt": created_at,
        "sourceIds": [source["artifactId"] for source in sources],
        "sourceHashes": [source["sha256"] for source in sources],
        "ownerGoal": goal,
        "validationState": "validated",
        "approvalState": "awaiting-review",
        "savedArtifactId": None,
        "rollbackState": "not-applicable",
    }
    if spec["builderType"] == "writing-draft":
        metadata["writingOperation"] = profile
        metadata["ownerInstructions"] = goal
    if spec["builderType"] == "research-comparison":
        metadata["comparisonFocus"] = profile
        metadata["ownerInstructions"] = goal
    if spec["builderType"] == "visual-brief":
        metadata["visualPurpose"] = profile
        metadata["visualControls"] = dict(builder_data or {})
        metadata["sourcePriority"] = str((builder_data or {}).get("referenceSourcePriority") or "")
        metadata["ownerNotesHash"] = next((source["sha256"] for source in sources if source.get("kind") == "temporary-visual-notes"), None)
    if spec["builderType"] == "song-production-brief":
        metadata["songPurpose"] = profile
        metadata["productionControls"] = dict(builder_data or {})
        metadata["sourcePriority"] = str((builder_data or {}).get("referenceSourcePriority") or "")
        metadata["musicNotesIdentity"] = next((source["artifactId"] for source in sources if source.get("kind") == "temporary-music-notes"), None)
        metadata["musicLyricsIdentity"] = next((source["artifactId"] for source in sources if source.get("kind") == "temporary-music-lyrics"), None)
        metadata["ownerInstructions"] = goal
    if spec["builderType"] == "video-production-brief":
        metadata["videoPurpose"] = profile
        metadata["videoControls"] = dict(builder_data or {})
        metadata["sourcePriority"] = str((builder_data or {}).get("referenceSourcePriority") or "")
        metadata["videoNotesIdentity"] = next((source["artifactId"] for source in sources if source.get("kind") == "temporary-video-notes"), None)
        metadata["ownerInstructions"] = goal
    if spec["builderType"] == "build-work-order":
        build_metadata = dict(builder_data or {})
        capability_metadata = dict(build_metadata.pop("_capabilityRegistryContext", {}) or {})
        metadata["workOrderType"] = profile
        metadata["buildControls"] = build_metadata
        metadata["capabilityRegistryContext"] = capability_metadata
        metadata["sourcePriority"] = str((builder_data or {}).get("referenceSourcePriority") or "")
        metadata["buildInputIdentity"] = next((source["artifactId"] for source in sources if source.get("kind") == "temporary-build-input"), None)
        metadata["ownerInstructions"] = goal
    if spec["builderType"] == "module-proposal":
        metadata["moduleProposalType"] = profile
        metadata["moduleControls"] = dict(builder_data or {})
        metadata["sourcePriority"] = str((builder_data or {}).get("referenceSourcePriority") or "")
        metadata["moduleInputIdentity"] = next((source["artifactId"] for source in sources if source.get("kind") == "temporary-module-input"), None)
        metadata["ownerInstructions"] = goal
    binding = {"text": text, "metadata": metadata}
    output_hash = sha256_text(canonical_json(binding))
    metadata["outputHash"] = output_hash
    return {
        "schemaVersion": BUILDER_SCHEMA_VERSION,
        "text": text,
        "metadata": metadata,
        "outputHash": output_hash,
        "networkUsed": False,
        "shellUsed": False,
    }


def validate_output(worker_id: str, output: dict[str, Any]) -> None:
    spec = BUILDER_WORKERS[worker_id]
    if output.get("schemaVersion") != BUILDER_SCHEMA_VERSION:
        raise ValueError("schema")
    text = output.get("text")
    metadata = output.get("metadata")
    if not isinstance(text, str) or not text.strip() or not isinstance(metadata, dict):
        raise ValueError("content")
    for section in spec["sections"]:
        if f"## {section}\n" not in text:
            raise ValueError(f"section:{section}")
    required = {
        "schemaVersion", "builderType", "destinationProfile", "workerId",
        "workerVersion", "jobId", "planId", "createdAt", "sourceIds",
        "sourceHashes", "ownerGoal", "validationState", "approvalState",
        "savedArtifactId", "rollbackState", "outputHash",
    }
    if spec["builderType"] == "writing-draft":
        required.update({"writingOperation", "ownerInstructions"})
    if spec["builderType"] == "research-comparison":
        required.update({"comparisonFocus", "ownerInstructions"})
    if spec["builderType"] == "visual-brief":
        required.update({"visualPurpose", "visualControls", "sourcePriority", "ownerNotesHash"})
    if spec["builderType"] == "song-production-brief":
        required.update({"songPurpose", "productionControls", "sourcePriority", "musicNotesIdentity", "musicLyricsIdentity", "ownerInstructions"})
    if spec["builderType"] == "video-production-brief":
        required.update({"videoPurpose", "videoControls", "sourcePriority", "videoNotesIdentity", "ownerInstructions"})
    if spec["builderType"] == "build-work-order":
        required.update({"workOrderType", "buildControls", "capabilityRegistryContext", "sourcePriority", "buildInputIdentity", "ownerInstructions"})
    if spec["builderType"] == "module-proposal":
        required.update({"moduleProposalType", "moduleControls", "sourcePriority", "moduleInputIdentity", "ownerInstructions"})
    if spec["builderType"] == "local-ai-writing-proposal":
        required.update({"writingOperation", "ownerInstructions", "inference"})
    if set(metadata) != required or not metadata["sourceIds"]:
        raise ValueError("metadata")
    if spec["builderType"] not in {"writing-draft", "research-comparison", "visual-brief", "song-production-brief", "video-production-brief", "build-work-order", "module-proposal", "local-ai-writing-proposal"} and not metadata["ownerGoal"].strip():
        raise ValueError("metadata")
    if spec["builderType"] == "writing-draft" and (
        metadata["writingOperation"] not in spec["profiles"]
        or not isinstance(metadata["ownerInstructions"], str)
    ):
        raise ValueError("metadata")
    if spec["builderType"] == "research-comparison" and (
        metadata["comparisonFocus"] not in spec["profiles"]
        or not isinstance(metadata["ownerInstructions"], str)
        or not 2 <= len(metadata["sourceIds"]) <= 8
    ):
        raise ValueError("metadata")
    if spec["builderType"] == "visual-brief" and (
        metadata["visualPurpose"] not in spec["profiles"]
        or not isinstance(metadata["visualControls"], dict)
        or not isinstance(metadata["sourcePriority"], str)
        or metadata["ownerNotesHash"] is not None and not isinstance(metadata["ownerNotesHash"], str)
        or not 1 <= len(metadata["sourceIds"]) <= 5
    ):
        raise ValueError("metadata")
    if spec["builderType"] == "song-production-brief" and (
        metadata["songPurpose"] not in spec["profiles"]
        or not isinstance(metadata["productionControls"], dict)
        or not isinstance(metadata["sourcePriority"], str)
        or metadata["musicNotesIdentity"] is not None and not str(metadata["musicNotesIdentity"]).startswith("music-notes:")
        or metadata["musicLyricsIdentity"] is not None and not str(metadata["musicLyricsIdentity"]).startswith("music-lyrics:")
        or not isinstance(metadata["ownerInstructions"], str)
        or not 1 <= len(metadata["sourceIds"]) <= 6
    ):
        raise ValueError("metadata")
    if spec["builderType"] == "video-production-brief" and (
        metadata["videoPurpose"] not in spec["profiles"]
        or not isinstance(metadata["videoControls"], dict)
        or not isinstance(metadata["sourcePriority"], str)
        or metadata["videoNotesIdentity"] is not None and not str(metadata["videoNotesIdentity"]).startswith("video-notes:")
        or not isinstance(metadata["ownerInstructions"], str)
        or not 1 <= len(metadata["sourceIds"]) <= 5
    ):
        raise ValueError("metadata")
    if spec["builderType"] == "build-work-order" and (
        metadata["workOrderType"] not in spec["profiles"]
        or not isinstance(metadata["buildControls"], dict)
        or not isinstance(metadata["capabilityRegistryContext"], dict)
        or metadata["buildInputIdentity"] is not None and not str(metadata["buildInputIdentity"]).startswith("build-input:")
        or not isinstance(metadata["ownerInstructions"], str)
        or not 1 <= len(metadata["sourceIds"]) <= 5
    ):
        raise ValueError("metadata")
    if spec["builderType"] == "module-proposal" and (
        metadata["moduleProposalType"] not in spec["profiles"]
        or not isinstance(metadata["moduleControls"], dict)
        or metadata["moduleInputIdentity"] is not None and not str(metadata["moduleInputIdentity"]).startswith("module-input:")
        or not isinstance(metadata["ownerInstructions"], str)
        or not 1 <= len(metadata["sourceIds"]) <= 5
    ):
        raise ValueError("metadata")
    if spec["builderType"] == "local-ai-writing-proposal" and (
        metadata["writingOperation"] not in spec["profiles"]
        or not isinstance(metadata["ownerInstructions"], str)
        or not isinstance(metadata["inference"], dict)
        or metadata["inference"].get("externalNetworkUsed") is not False
        or metadata["inference"].get("providerCloudCalled") is not False
        or not 1 <= len(metadata["sourceIds"]) <= 4
    ):
        raise ValueError("metadata")
    check = dict(metadata)
    claimed = check.pop("outputHash")
    expected = sha256_text(canonical_json({"text": text, "metadata": check}))
    if claimed != expected or output.get("outputHash") != expected:
        raise ValueError("hash")
