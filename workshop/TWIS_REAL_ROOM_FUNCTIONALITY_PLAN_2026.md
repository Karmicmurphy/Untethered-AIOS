# TWIS Real Room Functionality Plan — 2026

Status: implementation plan only  
Authoritative live root: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`  
Evidence date: 2026-08-14  
Baseline used: current deployed TWIS/Hollow Workshop, including Release 0.17 Local AI Model Bay and the later UI/desktop work

## The strongest recommendation

Do not rebuild the rooms and do not add a second framework. Make **Write** the first complete creative AI workstation by extending its existing editor, versioning, local Model Bay, approvals, and recovery. In parallel, make **Music** the first complete immediate-feedback media workstation by deepening its existing Web Audio sequencer into a small four-pattern groove box.

Those two changes deliver the most obvious owner value with the least architectural risk:

- Write already has durable documents, versions, compare, recovery, export, governed proposals, and one real local-AI rewrite path.
- Music already makes real sound, loops a 16-step pattern, saves/reopens patterns, and renders a real WAV in the browser.
- Neither first slice needs a cloud provider, paid service, database rebuild, large dependency, GPU, or new model.
- Both can preserve TWIS's central rule: generated material is proposed; the owner decides what becomes saved or authoritative.

The rest of the rooms should follow in bounded slices after these two prove the shared workstation pattern.

## Evidence and truth boundary

This plan is based on live implementation evidence, not room labels alone:

- `app/index.html` and `app/assets/app.js` contain the current room surfaces and browser-native Music, Images, Video, Explore, My Work, and navigation behavior.
- `app/assets/write-room.js`, `companion/write_room.py`, and their tests contain durable Write documents, versions, recovery, compare, restore, export, and conflict handling.
- `app/assets/builder-workspace.js`, `companion/local_worker_kit.py`, and `companion/builder_output.py` contain the shared governed builder lifecycle.
- `app/assets/model-bay.js`, `companion/model_bay.py`, and `config/local-ai-models.json` contain the local model registry, routing, runtime control, and inference adapter.
- `release-0.17-work/FOUNDATION_RELEASE_0.17_DEPLOYED_VERIFICATION.md` records a successful real local rewrite, an unchanged source, owner approval separation, and rollback.
- The live SQLite database opened read-only with `integrity_check=ok`, `user_version=13`, and zero foreign-key violations. It currently contains 59 artifacts and 226 receipts, with no active jobs or worker evidence.
- `C:\TWIS_FLASHRIVER_REVIEW_READY\HOLLOW_DECK` is a separate, working local voice layer. Its handoff records microphone capture, Vosk transcription, SAPI speech, deterministic commands, screen reading, stop-speaking, and destructive-action protection. It is not yet presented as a coherent TWIS workstation.
- The local Liquid LFM2.5 1.2B Q4 model and llama.cpp runtime are present beside the Workshop. The verified rewrite took about 18.7 seconds and the model process used roughly 797 MB working set. That is useful for bounded assistance, but it is not a reason to send entire projects or huge contexts to the model.
- `ffmpeg`, `ffprobe`, FluidSynth, and LMMS were not available on `PATH` during this inspection.

One current-state document is stale on the AI point: `CURRENT_STATE.md` says no model is installed, while the later Release 0.17 deployment evidence and the actual model files prove otherwise. The live files and later verified report govern this plan.

### Classification terms

- **ALREADY REAL** — the room's declared purpose is backed by a useful, working capability.
- **PARTIAL** — useful work is possible, but the room does not yet cover its central job well enough.
- **SHELL ONLY** — presentation/navigation exists without a useful task engine.
- **MISSING ENGINE** — the intended function depends on a real runtime that is not currently present.

No mapped room is literally empty now. The problem is depth and coherence: several rooms contain a real but narrow tool beside an older brief-builder or thin utility, rather than one dominant workstation.

## Current room-by-room reality

| Room | Reality | What genuinely works now | Functional gap | Best next engine/tool | Hardware impact |
|---|---|---|---|---|---|
| Sanctuary | **ALREADY REAL** | Calm local entry, Continue, New Idea, My Work, Recover, real clock/navigation identity | No functional gap worth expanding | Keep it an arrival room | Negligible |
| Crossroads | **ALREADY REAL** | Clear navigation across the 14-room map | Avoid adding tools or telemetry here | Keep navigation-only | Negligible |
| Control Room | **PARTIAL** | Real project/system state and Model Bay controls | No single truthful capability matrix for AI, voice, audio, image, FFmpeg/video, storage, and runtime readiness | Read-only capability registry backed by actual probes | Low; probes must be cached/bounded |
| My Work | **PARTIAL** | Central artifact listing, filtering, reopening, builder drafts, ideas, writing, music, images, video notes, research | Media artifacts lack consistent versions, provenance, export history, and edit/reopen semantics | Extend existing artifact metadata and relationships, not a new library | Low to moderate depending on thumbnails |
| New Idea | **ALREADY REAL** | Inline title/note/project form, inactive DRAFT save, safe cancel | It should hand off explicitly to rooms, not grow into an editor | Add only explicit future “continue in…” copy actions | Negligible |
| Write | **PARTIAL** | Durable editor; versions; compare; recovery; restore/rollback; export; governed deterministic proposals; real local-AI rewrite | AI only performs one rewrite profile; no selection-aware continuation, tone, dialogue, scenes, structure, alternatives, bounded project context, or integrated read-aloud | Existing llama.cpp Model Bay plus version-bound writing action profiles | Model process about 0.8 GB observed; bounded requests |
| Images | **PARTIAL** | Real canvas import, drawing, text, grayscale, invert, reset, PNG save/export; governed Visual Brief Builder | No crop, resize, rotate, tonal controls, non-destructive versions, compare, provenance-rich import; no connected generator | Native Canvas 2D first; generator actions shown only through a real engine registry | Low for normal images; cap dimensions/history |
| Music | **PARTIAL** | Real audible Web Audio drum/synth loop, 16 steps, BPM, play/stop, pattern save/reopen, offline WAV render; governed Song Brief Builder | No playable pads, track volume/mute, multiple patterns, arrangement, useful editing feedback, versions, or AI idea proposals | Existing Web Audio engine; no new dependency in first slice | Low; browser audio only while active |
| Video | **PARTIAL + MISSING ENGINE** | Local clip/audio/image preview using object URLs, project notes, metadata save; governed Video Brief Builder | Saved projects do not retain playable media; no ordered timeline, trim, captions, audio binding, transition, or export; FFmpeg absent | Browser preview/editor model plus separately provisioned FFmpeg adapter | Moderate during export; must limit concurrency |
| Build | **PARTIAL** | Governed Build Work Order; project tree; file view/edit/save | No changed-files diff, test/result surface, bounded patch proposal, logs, or safe Codex handoff; direct edit is not a substitute for governed development | Read-only repository inspector plus allowlisted test runner and patch-proposal lifecycle | Low idle; bounded subprocesses only |
| Explore | **PARTIAL** | Research notebook, question prompt, research save/reopen, governed multi-source Evidence Compare | No usable search over the existing FTS index, citation capture, source excerpt cards, or evidence-versus-inference ledger | Existing SQLite FTS5 plus provenance cards and governed synthesis | Low |
| Recover / Machine Room | **ALREADY REAL** | Receipts, conflicts, interrupted work, rollback/recovery, database/protected-state diagnostics | Presentation can unify chronology, but no new recovery engine is needed | Keep current authority; add read-only cross-room filters later | Low |
| Modules | **ALREADY REAL** | Honest capability registry, module proposals, Local AI Model Bay | Installed/configured/healthy states need to feed Control Room consistently | Reuse registry as capability authority | Low |
| Settings | **ALREADY REAL** | Local presentation preferences and Local AI controls | Future engine preferences must appear only after engines exist | Keep bounded, local, and reversible | Negligible |
| Talk / HOLLOW_DECK | **PARTIAL integration** | Talk has durable sessions, versions, compare, voice-draft review, TTS, Talk-to-Write, export, recovery; HOLLOW_DECK separately has real local voice control | TWIS does not show HOLLOW_DECK's push-to-talk, transcript, mode, action preview, sensitive-field block, or speaking state | Thin localhost status/command bridge to existing HOLLOW_DECK; do not rewrite it | HOLLOW_DECK measured about 31 MB idle; STT only on demand |

## Room identity and workstation design

The visual change should support the tool, not merely reskin it. Each functional room gets one obvious primary workstation and a quieter secondary drawer for briefs, provenance, history, or advanced controls.

### Write — the drafting table

- Tone: deep ink blue, controlled cyan, warm parchment-light reading surface.
- Dominant anchor: a large document editor with selection-aware AI actions immediately beside the text.
- Quiet secondary surfaces: versions/compare, sources/context, read-aloud, export.
- Remove the feeling that Draft Workshop and the editor are two unrelated products. The editor is the workstation; governed AI and deterministic transformations are tools attached to it.

### Music — the groove bench

- Tone: ultraviolet and electric blue with restrained amber transport lights.
- Dominant anchor: pads, step grid, transport, and mixer strip in one readable instrument.
- Immediate truth: striking a pad makes sound; toggling a step changes the loop; muting a track is audible.
- Song Production Brief remains available in a secondary planning drawer.

### Images — the light table

- Tone: cool blue, silver, photographic white at the canvas edge.
- Dominant anchor: image/canvas with a compact, honest tool rail.
- Version strip and before/after compare sit beneath the image.
- “Generate” must not exist unless an engine is registered, enabled, healthy, and callable.

### Video — the cutting table

- Tone: cinema blue, deep black, restrained red only for record/export warnings.
- Dominant anchor: preview plus an ordered clip strip—not a fake professional timeline.
- Until FFmpeg exists, label edit decisions as a project/EDL and keep Export unavailable with a precise engine status.

### Explore — the evidence table

- Tone: green-blue map room, pinned evidence, clear provenance lines.
- Dominant anchor: search/result/excerpt capture flow.
- Evidence, owner notes, and AI inference must use visibly different materials and metadata.

### Build — the fabrication bench

- Tone: brass, furnace orange, graphite steel.
- Dominant anchor: file tree + selected file/diff + bounded task/test status.
- Never make a decorative “RUN” control. Every executable action identifies the allowlisted command, scope, working directory, and expected outputs before approval.

### Talk / HOLLOW_DECK — the voice console

- Tone: darkest command-deck treatment with a single strong microphone state.
- Dominant anchor: push-to-talk control, transcript, mode, proposed action, and STOP SPEAKING.
- Decorative meters are forbidden. Show only measured capture/transcription/speaking/error states.

### My Work — the project archive

- Tone: dark library, brass indexing, media-specific preview light.
- Dominant anchor: one filterable collection with type-appropriate preview and provenance.
- It should not become a file manager or social feed.

### Control and Machine Room

- Control Room answers “what can TWIS do right now?” using real health probes.
- Machine Room answers “what happened, what failed, and what can be recovered?” using receipts and actual recovery state.
- Do not duplicate the same status grid in both rooms.

## Exact engine and dependency decisions

### Music: deepen native Web Audio first

Use the current `AudioContext`/`OfflineAudioContext` implementation as Music's first real engine. The W3C specification defines Web Audio as an audio routing graph for processing and synthesis, and includes oscillators, buffers, gain, filters, scheduling, and offline rendering—the exact primitives this first workstation needs: <https://www.w3.org/TR/webaudio/>.

**Do now**

- Encapsulate current drum, synth, transport, and WAV code behind a small `music-engine.js` API.
- Use synthesized kick/snare/hat/clap initially; optionally add a tiny, locally shipped, license-documented sample set later.
- Add `GainNode` per track and master, mute/volume, direct pad triggering, four patterns, and a short pattern chain.
- Persist structured pattern JSON as an inactive TWIS artifact with schema/version/provenance.
- Continue using `OfflineAudioContext` for WAV export.

**Do not add in the first slice**

- Tone.js. It is a credible Web Audio framework and its official guidance correctly requires audio startup from an owner gesture, but TWIS already has working scheduling and rendering. Adding it now would create migration risk without unlocking the first missing capabilities: <https://tonejs.github.io/>. Reconsider it only if swing, transport scheduling, instruments, and automation make the native engine materially harder to maintain.
- FluidSynth or SoundFonts. FluidSynth is a real SoundFont 2 synthesizer and useful later for richer instruments, but it introduces a native runtime, SoundFont licensing/storage, and process management: <https://www.fluidsynth.org/>.
- LMMS integration. LMMS is a real DAW and its documented recommended system is compatible with Windows 10 and 4 GB RAM, but controlling a separate DAW is not the shortest path to an integrated TWIS groove station: <https://docs.lmms.io/user-manual/getting-started/installation>. Treat LMMS export/handoff as a future optional adapter, not TWIS's core engine.
- Web MIDI until actual hardware is detected and the owner requests it.

### Write: extend the current local model route

Keep llama.cpp and the registered LFM model behind the Model Bay. Add bounded task categories rather than model calls inside Write:

- `writing.brainstorm`
- `writing.continue`
- `writing.rewrite-selection`
- `writing.tone`
- `writing.scene-options`
- `writing.dialogue-options`
- `writing.structure`
- `writing.memoir-fiction-blend`
- `writing.alternates`

Each route uses a versioned prompt template and records source/version hashes, selection bounds, project-context hashes, owner instruction, model/runtime/hash, parameters, output hash, and receipt. The existing 1.2B model is the first available engine, not an assertion that it is the best author. Its output must be judged, compared, and approved.

For a project such as The Thousand Year Hangover, context should be an explicit, owner-selected packet of current passage + small project facts/excerpts—not an automatic whole-project dump. Context truncation must be visible. The model must never rewrite the original in place.

### Images: Canvas 2D before generation

Deepen the existing Canvas 2D workstation with crop, resize, rotate, exposure/contrast/saturation, undo history, before/after, and versioned save. Use a Web Worker or incremental operations only if large images cause measured UI stalls.

Generation remains engine-gated:

- No generator button when none is connected.
- A future image engine must register capabilities and health in Modules/Control Room.
- Reference images and generated results retain file hash, operation, engine/model/version, prompt, parameters, parent relationships, approval, and export history.

Do not install an image model in this plan's first implementation wave.

### Video: FFmpeg as a later bounded adapter

Use browser media elements for immediate preview and an ordered clip/decision list for editing. Provision FFmpeg only in a separate approved slice. FFmpeg is the appropriate free local engine because its official tools cover media conversion, probing, streams, filters, codecs, and formats: <https://ffmpeg.org/documentation.html>.

The adapter must never accept a free-form command line. Build validated argument arrays from fixed operations:

- probe media;
- trim one clip;
- concatenate compatible/transcoded clips;
- attach one audio track;
- burn or mux captions;
- simple crossfade where compatible;
- still image + audio;
- export to a fixed local output directory.

Inputs must be explicitly imported or registered; operations run in a disposable workspace; output is proposed until approved. Limit to one export process on this machine.

### Explore: use the SQLite FTS capability already present

Expose search over registered artifacts through a read-only, project-scoped API. Return source ID, title, kind, excerpt, exact hash, and match location. Let the owner pin excerpts into evidence cards. Store three distinct record types:

- **Evidence** — exact source excerpt with provenance.
- **Owner note** — the owner's interpretation.
- **AI inference** — model-produced proposal with model/source provenance.

AI synthesis consumes only selected cards and never becomes evidence automatically.

### Build: bounded developer station, not a browser shell

Make file inspection read-only by default. Add:

- repository/workspace identity;
- protected-path labels;
- changed-files list and text diff;
- approved test catalog with captured exit code/output/time;
- Build Work Order to Codex handoff package;
- later, a governed proposed patch with explicit review and deployment separation.

Do not expose arbitrary shell text. Test commands must come from repository-owned configuration and validated executable/argument allowlists. Never edit protected production files as an incidental side effect of inspection.

### HOLLOW_DECK: integrate status, do not merge implementations

Add a narrowly scoped localhost bridge owned by HOLLOW_DECK that reports real states and accepts only its fixed command vocabulary. TWIS should show:

- VOICE READY / LISTENING / TRANSCRIBING / COMMAND / DICTATION / SPEAKING / OFFLINE / ERROR;
- recognized transcript;
- proposed command/action before destructive confirmation;
- sensitive-field blocking;
- STOP SPEAKING.

No arbitrary shell endpoint, no continuous listening by default, and no duplicate STT/TTS stack inside TWIS.

## Ranked implementation order

Scores use 1–5, where 5 is best. “Fit” combines safety, existing-code reuse, older-PC suitability, and lack of paid/cloud dependency.

| Rank | Slice | Owner usefulness | Fit | Why now |
|---:|---|---:|---:|---|
| 1 | Write Studio AI Actions | 5 | 5 | Reuses the editor, versions, Model Bay, receipts, approval, and rollback already proven live |
| 2 | Music Groove Bench 1.1 | 5 | 5 | Real sound already works; missing controls are bounded browser code with no install |
| 3 | Explore Search + Evidence Cards | 4 | 5 | FTS5 and registered-source provenance already exist; turns Explore into actual research |
| 4 | My Work Media Versions + Provenance | 5 | 4 | Makes every room's output durable and understandable; should follow first media schema |
| 5 | Images Editing 1.1 | 4 | 4 | Canvas engine exists; useful non-generative editing is lightweight and honest |
| 6 | HOLLOW_DECK Voice Console Integration | 4 | 4 | Voice components already work separately; integration can remain thin and local |
| 7 | Control Room Capability Matrix | 3 | 5 | Small truthful layer after engine contracts stabilize |
| 8 | Build Inspector + Test Results | 4 | 3 | High value, but subprocess and protected-state boundaries need careful design |
| 9 | Video Ordered Edit + FFmpeg Adapter | 5 | 2 | Valuable but introduces media storage, native binary, long-running jobs, and export security |

Sanctuary, Crossroads, New Idea, Recover, Modules, and Settings do not need “depth” releases before these. Preserve their focused roles.

## Phased delivery plan

### Phase 1A — Write Studio AI Actions

**Bounded scope**

1. Add a compact AI action rail to the real Write editor.
2. Support: Brainstorm, Continue, Rewrite selection, Tone, Scene ideas, Dialogue, Structure, Memoir/Fiction blend, and 2–3 Alternatives.
3. Bind every request to the current document version hash and exact selection/range.
4. Let the owner explicitly select small project-context sources; show what will be sent and what was omitted.
5. Show proposed output beside the original with accept-as-new-version, save-as-inactive-draft, reject, copy, and read-aloud.
6. Reuse existing local Model Bay readiness, explicit execution, receipts, recovery, and rollback.
7. Preserve deterministic Draft Workshop as an offline/no-model tool.

**Verification**

- All actions fail honestly when the local model is offline.
- At least one real project passage completes brainstorm, continuation, selection rewrite, tone, dialogue, and alternatives.
- Original bytes/version remain unchanged before approval.
- Stale document version blocks approval/save.
- Project-context IDs and hashes are exact and visible.
- Result is proposed; approval and saving remain separate.
- Approved output creates exactly one new version or inactive draft, as selected.
- Compare, recovery, read-aloud, My Work reopen, export, and rollback pass.
- No cloud/provider call occurs.
- Desktop and 390-pixel layouts remain usable.

### Phase 1B — Music Groove Bench 1.1

**Bounded scope**

1. Consolidate the duplicate Music presentation so the groove bench is primary and the brief builder is a secondary drawer.
2. Add four playable drum pads using the existing sound functions.
3. Make step cells preview their instrument and show the real playhead.
4. Add per-track volume/mute and master volume.
5. Add four named patterns (A–D), copy/clear, and a 1–8-slot arrangement chain.
6. Save versioned structured pattern artifacts; reopen them exactly in My Work.
7. Render the arrangement to WAV using the existing offline engine.
8. Add optional AI idea proposals for beat grids, simple chord/root movement, arrangement, lyrics, and production notes. Validate structured suggestions before applying; applying remains an explicit action.

**Verification**

- Clicking every pad produces non-silent audio.
- Kick/snare/hat/clap are measurably distinct in offline render data.
- Play/stop, BPM, loop, mute, volume, pattern switching, and arrangement work audibly.
- Pattern JSON round-trips exactly through save/reopen.
- WAV contains non-zero samples, correct duration, sample rate, and valid header.
- AI suggestions cannot mutate a pattern until explicitly applied, and applying produces a version.
- Model-offline mode leaves the entire manual instrument usable.
- My Work reopen, export, recovery, and rollback pass.
- No audio model, cloud call, or fake meter is used.

### Phase 2 — Research and library spine

1. Explore FTS search and evidence cards.
2. My Work shared media version/provenance display.
3. Control Room real capability matrix.

This phase makes subsequent Images, Video, Build, and voice artifacts consistently searchable and understandable.

### Phase 3 — Images and voice

1. Images non-destructive basic editing and compare.
2. HOLLOW_DECK status/command bridge and Talk voice console.
3. No image generator installation unless separately approved and hardware-tested.

### Phase 4 — Build station

Add read-only repository inspection, diffs, bounded test execution, captured results, and governed Codex handoff. Proposed file changes remain a later, separately approved capability.

### Phase 5 — Video station

Add durable import, ordered clips, trim decisions, captions, audio association, and then an allowlisted FFmpeg export adapter. Do not begin with effects, multi-camera, or a full DAW/NLE imitation.

## Shared workstation contract

Each deepened room should reuse one small cross-room contract rather than create another builder framework:

1. **Input identity** — artifact/source IDs, hashes, version, selection, temporary-input hash.
2. **Engine truth** — engine ID, installed/configured/healthy state, version, parameters.
3. **Proposal** — output is visibly proposed and hash-bound.
4. **Preview** — immediate, real preview appropriate to the medium.
5. **Decision** — approve/reject is explicit; stale input blocks approval.
6. **Save** — approved material becomes a new inactive artifact/version; original remains.
7. **Provenance** — parent relationships, engine/model, operations, receipts, export history.
8. **Recovery** — refresh never silently resumes a state-changing operation.
9. **Rollback** — removes or deactivates only the bounded created output.
10. **Capability status** — unavailable engines disable their actions with a factual reason.

This is an extension of the current Worker Kit/builder-output/receipt architecture, not a replacement for it.

## What should not be built

- No room-specific model integrations that bypass the Model Bay.
- No autonomous agent chain or “make it for me” button that combines approval, execution, and saving.
- No cloud or paid provider dependency for the core workstation.
- No full DAW, Photoshop clone, Premiere clone, IDE, or browser-based operating system.
- No Tone.js migration until native Web Audio complexity proves it necessary.
- No FluidSynth, SoundFont library, LMMS automation, or MIDI layer in the first Music slice.
- No image-generation control until a real registered engine is present and healthy.
- No free-form FFmpeg or shell command endpoint.
- No video editing based on fragile filesystem paths or browser object URLs presented as durable projects.
- No automatic whole-project or whole-corpus context sent to the local model.
- No synthetic meters, render progress, health status, or capability badges.
- No rewriting of HOLLOW_DECK inside TWIS.
- No database rebuild or replacement to make UI development easier.
- No visual overhaul of Sanctuary/Crossroads while workstation functionality is the priority.

## First bounded implementation slice

Treat the first delivery as two coordinated but independently deployable candidates.

### Candidate A: Write Studio AI Actions

Expected application scope:

- `app/index.html` — compact action rail and proposal compare surface.
- `app/assets/write-room.js` — selection/version/context capture and proposal UI.
- `app/assets/write-room.css` — literary workstation layout.
- `app/assets/builder-workspace.js` — only shared wiring required for the new fixed profiles.
- `companion/local_worker_kit.py` — registered writing task profiles and source/version gates.
- `companion/builder_output.py` — output validation for writing proposals.
- `companion/server.py` — bounded endpoints only if existing job routes cannot express selection/version context.
- focused Python and JavaScript tests.

No schema migration is expected. If exact selection/version provenance cannot fit current job packets, extend versioned JSON metadata before considering a table change.

### Candidate B: Music Groove Bench 1.1

Expected application scope:

- `app/index.html` — one consolidated Music workstation.
- new `app/assets/music-engine.js` — native audio engine and offline renderer.
- new `app/assets/music-room.js` — pads, grid, transport, patterns, arrangement, save/reopen.
- `app/assets/app.js` — remove the old inline Music implementation after parity.
- `app/assets/ui-coherence.css` or a focused Music stylesheet — room identity and responsive layout.
- `app/service-worker.js` — cache the new static assets and advance the cache version.
- focused JavaScript tests plus a browser audio lifecycle.

Pattern artifacts can initially use the existing artifact store with a versioned `music-pattern-v2` data contract. Do not migrate SQLite merely for convenience. A later shared media-version table should be justified by Images/Video needs together, not Music alone.

### Deployment gate for both candidates

Before either touches live files:

1. Create an isolated candidate workspace.
2. Record protected database/source hashes.
3. Produce an exact changed-file manifest.
4. Prepare bounded rollback copies.
5. Run focused tests, then the established full suites once at candidate completion.
6. Prove source/version immutability, approval separation, recovery, rollback, and My Work reopen.
7. Deploy only the declared paths after explicit owner approval.
8. Run one real governed lifecycle per room and clean disposable outputs while preserving meaningful receipts.

## Definition of “actually useful”

Write is actually useful when the owner can select real project prose, ask for a specific creative operation, inspect a local-AI proposal against the unchanged original, hear it, compare alternatives, and deliberately save the chosen version.

Music is actually useful when the owner can hit a pad and hear it, program and edit a loop, arrange multiple patterns, mix tracks, save/reopen the exact work, export audible WAV audio, and optionally request ideas without surrendering control of the pattern.

Images is actually useful when a real image can be imported, edited non-destructively, compared, versioned, saved, and exported—with generation appearing only when a real engine exists.

Video is actually useful when imported media remains durable, the owner can order and trim it, attach audio/captions, preview the plan, and produce a real local export.

Explore is actually useful when findings can be searched, captured as exact evidence, cited, distinguished from inference, and promoted into project artifacts.

Build is actually useful when it can inspect the actual workspace, show changes/tests, prepare a governed handoff, and never silently alter protected production state.

Talk/HOLLOW_DECK is actually useful when push-to-talk, transcription, proposed action, speaking, sensitive-field blocking, and stop controls are visibly tied to real states.

Randy, here are the first two rooms I would make actually fucking useful.
