# TWIS Best Engine per Room — 2026

Status: implementation-ready engine strategy; no implementation performed  
Authoritative live root: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`  
Evidence date: 2026-08-14  
Governing plan: `TWIS_REAL_ROOM_FUNCTIONALITY_PLAN_2026.md`

## Decision in one page

The best engine strategy for this computer is not “install the smallest thing” and not “install the fashionable thing.” It is:

1. **Write:** keep the proven `llama.cpp` + Liquid LFM2.5 1.2B Q4_K_M runtime as the default engine, then add much better task-specific prompts, selected-context construction, comparison, and approval. Do not replace it until a controlled A/B test proves that a larger model gives materially better writing at tolerable latency.
2. **Music:** keep Web Audio as the actual audio engine, but upgrade its scheduling and instrument layer to a locally vendored, version-pinned Tone.js build. Add a small license-audited local sample set. Defer FluidSynth to a second instrument-expansion slice.
3. **Images:** keep Canvas 2D for pixels; add Fabric.js as a locally vendored object/transform layer. Do not expose generation because this machine has no comfortable local image-generation engine.
4. **Video:** retain browser preview and add native FFmpeg later through a fixed, allowlisted adapter. Reject `ffmpeg.wasm` on this hardware.
5. **Explore:** keep and expose SQLite FTS5; add `ripgrep` only for explicitly registered project trees.
6. **Build:** use installed Git, ripgrep, Python/Node test runners, and a fixed command catalog. Do not create a shell console.
7. **Talk/HOLLOW_DECK:** keep Vosk for low-latency commands and Windows SAPI for dependable speech. Benchmark `whisper.cpp tiny.en` only as an optional dictation path; do not replace the working command recognizer.
8. **My Work:** keep SQLite as the metadata/authority ledger, but move future large media payloads to an app-managed content-addressed file store with hashes and database relationships.
9. **Control, Modules, Settings, Recover, New Idea, Sanctuary, and Crossroads:** keep their existing engines and deepen only truthful integration/status behavior.

The first bounded implementation slice should be **Write Studio AI Actions**. It needs no model download, no schema migration, and no new runtime. It creates obvious owner value by turning the existing one-profile AI rewrite into a selection-aware creative writing workstation while preserving every governance boundary.

## 1. Actual machine constraints

These values were read from Windows on this machine, not assumed from the earlier “about 8 GB” description.

| Component | Verified machine value | Engineering consequence |
|---|---|---|
| Computer | HP Pavilion Notebook | Older mobile thermal and power envelope |
| Operating system | Windows 10 Home, build 19045 | Use supported native Windows binaries; no Windows 11-only dependency |
| CPU | AMD A4-6210 APU, 4 cores / 4 logical processors | CPU throughput is the main bottleneck; avoid multiple inference/render processes |
| RAM | 6.94 GiB visible to Windows | One small model at a time; no 4–8B default model; bounded media buffers |
| Graphics | AMD Radeon R3 integrated graphics, reported 1 GiB adapter memory | No dependable modern GPU inference path; treat AI and export as CPU work |
| Fixed storage | C: NTFS, 953.2 GiB total, 807.1 GiB free | Storage is not the limiting resource, but model/media duplication still needs governance |
| Installed development tools | Python 3.12, Node 24, npm, Git 2.54 | Reuse current stack; no frontend framework or container platform needed |
| Missing media tools on `PATH` | FFmpeg, ffprobe, FluidSynth, LMMS | These are not current capabilities and must never appear READY |

### Observed incumbent performance

- Installed model: Liquid LFM2.5 1.2B Instruct Q4_K_M, 730,895,168 bytes.
- Runtime: existing pinned `llama.cpp` server.
- Verified local rewrite: 18.656 seconds for 99 prompt + 16 completion tokens.
- Observed model-server working set: 797,208,576 bytes.
- HOLLOW_DECK measured idle memory before STT model load: 31.4 MB.
- Vosk small English model class: about 40–50 MB on disk and approximately 300 MB runtime memory according to its official model guidance.

### Hardware classifications used below

- **RUNS WELL NOW** — should remain responsive and leave enough memory for TWIS and Windows.
- **RUNS BUT MARGINAL** — technically plausible, but latency, memory, or sustained CPU use requires an on-device benchmark before adoption.
- **FUTURE HARDWARE** — not a reasonable default on this computer.
- **REJECT** — poor fit, unsafe integration, abandoned/unmaintained, or no meaningful benefit.

## 2. Current engine authority

| Artifact | Classification | Why it governs |
|---|---|---|
| Live TWIS code and SQLite state | **Canonical** | Actual room behavior and owner state |
| `TWIS_REAL_ROOM_FUNCTIONALITY_PLAN_2026.md` | **Active supporting** | Verified room reality and functional gaps |
| `config/local-ai-models.json` | **Canonical configuration** | Exact registered model/runtime/hash/routes |
| `..\release-0.17-work\FOUNDATION_RELEASE_0.17_DEPLOYED_VERIFICATION.md` | **Canonical deployed evidence** | Actual inference time, memory, source preservation, tests, rollback |
| `C:\TWIS_FLASHRIVER_REVIEW_READY\HOLLOW_DECK` | **Active supporting external subsystem** | Real isolated microphone/STT/router/TTS/desktop-control implementation |
| `CURRENT_STATE.md` Local AI statement | **Stale contradiction** | It says no model is installed; later live files and Release 0.17 evidence prove one is installed |

No engine recommendation below is authority to download, install, activate, migrate, or deploy it.

## 3. Current 2026 alternatives researched

Only maintained primary/official sources were used for technical selection.

### Local text inference

| Candidate | Current evidence | Machine class | Decision |
|---|---|---|---|
| **Liquid LFM2.5 1.2B Instruct Q4_K_M + llama.cpp** | Official GGUF is 731 MB; Liquid describes the model as on-device, CPU-oriented, under 1 GB, with llama.cpp support. TWIS has already verified this exact file and runtime locally. [Official model](https://huggingface.co/LiquidAI/LFM2.5-1.2B-Instruct-GGUF) | **RUNS WELL NOW** | **KEEP as default** |
| **Qwen3 1.7B** | Official model emphasizes creative writing, role-play, dialogue, and instruction following. The official GGUF currently exposed is Q8_0 at 1.83 GB before runtime/KV overhead. [Official GGUF](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF) | **RUNS BUT MARGINAL** | Benchmark later as an optional quality profile; do not replace default without proof |
| **Gemma 3 1B IT** | Mature 1B instruction model with broad ecosystem, but there is no live-machine evidence that it improves this writing workload over LFM enough to justify a replacement and another license/model path. [Official model](https://huggingface.co/google/gemma-3-1b-it) | **RUNS WELL NOW** | **REJECT as replacement**; no demonstrated improvement |
| **Microsoft BitNet b1.58 2B4T + bitnet.cpp** | Official CPU-first framework and native 1.58-bit model are promising; current optimized x86 documentation targets AVX2-class kernels and a separate runtime. This exact laptop has not been compatibility/quality benchmarked. [Official runtime](https://github.com/microsoft/BitNet), [official model](https://huggingface.co/microsoft/bitnet-b1.58-2B-4T-bf16) | **RUNS BUT MARGINAL / UNKNOWN** | **DEFER** to an isolated benchmark, not production replacement |
| 3B–4B Q4 instruction models | Weight memory may fit narrowly, but old four-core CPU latency and total Windows/TWIS memory pressure make interactive writing poor | **FUTURE HARDWARE** | **REJECT on current laptop** |
| 7B+ local models | Excessive RAM and CPU latency | **FUTURE HARDWARE** | **REJECT** |

`llama.cpp` remains the right runtime abstraction: it is maintained, CPU-capable, GGUF-native, exposes a local server, and can load one registered model without bringing a Python ML stack into TWIS. The official project now supports single-model inference server operation and routing modes, but TWIS should retain its own deterministic Model Bay authority rather than adopt an unrestricted runtime router: <https://github.com/ggml-org/llama.cpp>.

### Music/audio

| Candidate | Current evidence | Machine class | Decision |
|---|---|---|---|
| **Native Web Audio** | Already produces real sound and offline WAV in TWIS. W3C defines native synthesis, routing, gain, oscillators, buffers, filters, scheduling, and offline rendering. [Specification](https://www.w3.org/TR/webaudio/) | **RUNS WELL NOW** | **KEEP as audio foundation** |
| **Tone.js over Web Audio** | Maintained Web Audio framework with DAW-like Transport, synchronized events, loops, synths, effects, and offline rendering; uses native AudioNodes for processing. [Official repository](https://github.com/Tonejs/Tone.js), [offline rendering](https://tonejs.github.io/docs/14.5.40/fn/Offline) | **RUNS WELL NOW** | **UPGRADE scheduling/instrument layer** |
| **Small local samples** | Zero runtime service; immediate and musically better drums if assets and licenses are audited | **RUNS WELL NOW** | **ADD** a tiny, versioned, local-only kit |
| **FluidSynth + one small SoundFont** | Maintained cross-platform real-time SoundFont 2 synth; its own project notes wavetable synthesis is low CPU. Version 2.5.4 was released in 2026. [Official project](https://github.com/FluidSynth/fluidsynth) | **RUNS WELL NOW**, but integration cost is higher | **DEFER** to instrument expansion after groove bench |
| **Web MIDI** | Standard API for real MIDI device events; it does not create audio or high-level sequencing. [Specification](https://www.w3.org/TR/webmidi/) | **RUNS WELL NOW if hardware exists** | **DEFER** until a device is detected/requested |
| **LMMS integration** | Mature free DAW; official recommended spec is Windows 10, four cores, 4 GB RAM. It could run, but it is a separate workstation with separate project/storage/UI authority. [Official requirements](https://docs.lmms.io/user-manual/getting-started/installation) | **RUNS BUT MARGINAL** alongside TWIS/model | **DEFER/REJECT as core engine**; optional future handoff only |
| Audio-generation models | No GPU and too little comfortable RAM/CPU for good interactive generation | **FUTURE HARDWARE** | **REJECT** |

### Voice

| Candidate | Current evidence | Machine class | Decision |
|---|---|---|---|
| **Vosk small English** | Existing HOLLOW_DECK engine works; official small models are designed for desktop/mobile/Raspberry Pi, about 50 MB and ~300 MB runtime, with streaming and vocabulary control. [Official models](https://alphacephei.com/vosk/models) | **RUNS WELL NOW** | **KEEP for commands and current dictation** |
| **whisper.cpp tiny.en** | Maintained CPU-only C/C++ runtime; official figures: 75 MiB disk and ~273 MB memory for tiny, with quantization support. Better open-ended transcription is plausible, but this CPU's latency is unmeasured. [Official project](https://github.com/ggml-org/whisper.cpp) | **RUNS BUT MARGINAL** | **DEFER to A/B dictation benchmark**; never replace command grammar blindly |
| **Windows SAPI TTS** | Already installed, bounded, tested, and very low integration cost | **RUNS WELL NOW** | **KEEP dependable default** |
| **Piper (OHF-Voice)** | Maintained local neural TTS, potentially more natural, but introduces voice models, GPL considerations, and unmeasured generation latency on this APU. [Official project](https://github.com/OHF-Voice/piper1-gpl) | **RUNS BUT MARGINAL** | **DEFER to optional voice-quality benchmark** |

### Images/video/search/development

| Candidate | Current evidence | Machine class | Decision |
|---|---|---|---|
| **Canvas 2D** | Already works for image import, drawing, filters, PNG save/export | **RUNS WELL NOW** | **KEEP pixel engine** |
| **Fabric.js 7.x** | Maintained Canvas object/selection/transformation layer; 7.4.0 includes a 2026 security fix. [Official releases](https://github.com/fabricjs/fabric.js/releases) | **RUNS WELL NOW** for bounded canvas sizes | **UPGRADE object/edit layer**, vendored and pinned |
| Local diffusion/image generators | Radeon R3 and 6.94 GiB RAM are not a comfortable generation platform | **FUTURE HARDWARE** | **REJECT** |
| **Native FFmpeg/ffprobe** | Mature local converter/prober with codecs, filters, subtitles, audio, image, and container support. [Official documentation](https://ffmpeg.org/documentation.html) | **RUNS WELL NOW for probing/light operations; RUNS BUT MARGINAL for encoding** | **ADD later through fixed adapter** |
| **ffmpeg.wasm** | Browser port exists, but its project discussion documents high memory and performance constraints; multi-threading can consume roughly 2 GB. [Official repository](https://github.com/ffmpegwasm/ffmpeg.wasm), [project performance discussion](https://github.com/ffmpegwasm/ffmpeg.wasm/discussions/415) | **REJECT** | Native FFmpeg is decisively better here |
| **SQLite FTS5** | Already present in TWIS; supports indexed full-text queries without another service. [Official documentation](https://sqlite.org/fts5.html) | **RUNS WELL NOW** | **KEEP and expose** |
| **ripgrep** | Installed/available workflow tool; fast recursive search respecting ignore rules. [Official project](https://github.com/BurntSushi/ripgrep) | **RUNS WELL NOW** | **ADD only for registered project trees** |
| Heavy search servers/vector databases | Additional service, memory, indexing, recovery, and authority for a 59-artifact local corpus | **REJECT** | No current need |

## 4. Room-by-room engine comparison

The required decision format is preserved verbatim in the table headings.

| ROOM | CURRENT ENGINE | BEST CURRENT OPTION | WHY | RESOURCE COST | WHAT IT ADDS | KEEP/UPGRADE/REPLACE/DEFER |
|---|---|---|---|---|---|---|
| Write | Durable Write Room + Worker Kit + llama.cpp/LFM2.5 one-profile rewrite + browser/SAPI read-aloud paths | Same runtime/model, expanded task router and context builder | Proven on this exact machine; quality gain now comes more cheaply from good task templates, selected evidence, and comparison than a slower default model | Observed ~797 MB model working set; inference on demand only | Selection rewrite, continue, brainstorm, scene/dialogue/character/tone/structure/alternatives, project context, proposal compare | **KEEP engine; UPGRADE capabilities — RUNS WELL NOW** |
| Music | Inline native Web Audio drum/synth sequencer + OfflineAudioContext WAV | Locally vendored Tone.js orchestration over Web Audio + small licensed samples | Meaningful improvement in transport, timing, loops, patterns, synths, swing, arrangement, and offline render without a native service | Low browser CPU/RAM; audio only while active; one pinned JS asset plus small samples | Real pads, mixer, patterns, song mode, instruments, save/version/export | **UPGRADE — RUNS WELL NOW** |
| Images | Canvas 2D drawing/filter/import/export; image data URL artifact | Canvas 2D + pinned Fabric.js object layer; content-addressed media persistence later | Preserves working pixels while adding selections, transforms, layered objects, serialization, and better editing | Low to moderate; cap working dimensions/history | Crop/resize/rotate/text objects/layers-like ordering/undo/version/compare | **UPGRADE — RUNS WELL NOW** |
| Video | Browser media preview/object URLs + notes + brief builder | Durable media import + ordered edit model + native FFmpeg/ffprobe fixed adapter | Native FFmpeg gives real probing/rendering; browser WASM is a poor fit | Preview low; encoding may saturate CPU and must be one job at a time | Durable clips, trim, captions, audio, simple transitions, real export | **DEFER engine install; then UPGRADE — MARGINAL for export** |
| Explore | Research notes + Evidence Compare + hidden SQLite FTS index | SQLite FTS5 evidence search + selected-tree ripgrep + provenance cards | Existing local index is enough; no search server needed | Very low | Search, excerpt capture, citations, evidence/inference separation | **KEEP engine; UPGRADE UI/API — RUNS WELL NOW** |
| Build | Build Work Order + project tree/direct editor + Python/Node/Git available | Read-only inspector using Git/ripgrep + repository-owned allowlisted tests + governed patch/handoff | Uses mature installed tools while preserving production boundaries | Low idle; bounded test process on demand | Diffs, changed files, test output, logs, safe Codex handoff | **UPGRADE — RUNS WELL NOW** |
| Talk / HOLLOW_DECK | Talk durable sessions; isolated HOLLOW_DECK Vosk + deterministic router + SAPI | Keep HOLLOW stack; add narrow localhost status/action bridge; optional whisper.cpp tiny A/B later | Current command path is proven and lighter than replacing it; bridge avoids duplicated voice authority | ~31 MB idle plus ~300 MB Vosk class when loaded | Real voice state, transcript, command preview, privacy block, stop speaking | **KEEP engine; UPGRADE integration — RUNS WELL NOW** |
| My Work | SQLite artifact ledger + JSON/data-URL payloads + builder reopen | SQLite authority + app-managed content-addressed media blob store + typed previews | SQLite remains excellent metadata authority; large media does not belong as duplicated base64 rows | Low metadata; media disk proportional to actual content; thumbnail caps | Durable media, versions, hashes, provenance, export history, reopen/edit | **UPGRADE persistence, not authority — RUNS WELL NOW** |
| Control Room | Existing APIs + Model Bay status | Shared capability registry with cached real probes; optional `psutil` only if a measured process metric cannot be obtained safely otherwise | Truthful status can come from existing model/module/voice/media adapters; avoid a monitoring platform | Very low | AI/voice/music/image/video/storage status without fake telemetry | **KEEP/UPGRADE — RUNS WELL NOW** |
| Modules | Static capability JSON + Module Proposal + Model Bay | Versioned capability/engine manifests plus real health callbacks | Existing registry is the correct authority; it needs stronger per-engine state, not replacement | Negligible | Installed/configured/healthy/suitable distinction | **KEEP/UPGRADE — RUNS WELL NOW** |
| Settings | Browser local preferences + bounded Local AI settings | Keep local preferences; engine-specific settings owned by each registered adapter | Avoids turning settings into uncontrolled executable/config paths | Negligible | Defaults for model profile, audio latency, voice mode, export limits | **KEEP — RUNS WELL NOW** |
| Recover / Machine Room | SQLite receipts, conflicts, recovery, rollback, protected-state checks | Keep; extend checks for content-addressed media and engine jobs when those exist | This is already the authoritative recovery mechanism | Low, on demand | Media hash verification and bounded render/job cleanup later | **KEEP — RUNS WELL NOW** |
| New Idea | Inline form saved as inactive idea artifact | Keep; add explicit copy/handoff into Write/Music/Images/etc. only after those accept governed inputs | It already performs its room purpose | Negligible | Fast idea-to-workstation transition without mutation | **KEEP; DEFER handoffs — RUNS WELL NOW** |
| Sanctuary | Static/local arrival and navigation | Keep | Its job is calm entry, not production | Negligible | Nothing needed | **KEEP — RUNS WELL NOW** |
| Crossroads | Room routing/navigation | Keep | Its job is spatial navigation, not an engine | Negligible | Only truthful capability badges from registry | **KEEP — RUNS WELL NOW** |

## 5. Exact Write recommendation

### Engine decision

**Keep `llama.cpp` and Liquid LFM2.5 1.2B Instruct Q4_K_M as TWIS's default writing engine.**

This is not blind loyalty to the installed engine. It wins because:

- its exact binary/model/hash are registered and verified;
- it actually loaded and completed governed inference on this laptop;
- observed memory stayed under 0.8 GB working set;
- it leaves enough RAM for Windows, TWIS, browser UI, and recovery;
- it uses the existing localhost-only Model Bay and receipts;
- swapping to another 1B model has no proven quality benefit;
- Qwen3 1.7B is the only clearly attractive creative-writing challenger, but its official Q8 weight alone is 1.83 GB and this old CPU has not been benchmarked with it.

### What improves quality now

Add versioned task templates, not a generic “ask AI” box:

- `writing.brainstorm`
- `writing.continue`
- `writing.rewrite-selection`
- `writing.tone` with bounded owner-visible tone profiles
- `writing.scene-options`
- `writing.dialogue-options`
- `writing.character-development`
- `writing.structure`
- `writing.memoir-fiction-blend`
- `writing.alternates`

Every request packet contains:

- document/artifact ID;
- exact current version and hash;
- selected-text offsets and selected-text hash;
- explicit owner instruction and hash;
- selected project-context source IDs/hashes/order;
- prompt-template ID/version;
- model/runtime/file hash;
- actual inference parameters;
- output hash and timestamps.

The UI shows the source selection and context budget before execution. For The Thousand Year Hangover, the owner selects the current passage and a few relevant source cards; TWIS must not silently feed an entire corpus into a 2,048-token runtime context.

### Qwen3 benchmark gate

Do not install it during the first slice. In a later explicitly approved model-evaluation task:

1. Pin an official or independently verified GGUF revision and license.
2. Run ten representative owner-approved, non-private-or-disposable creative prompts against LFM and Qwen3 1.7B.
3. Measure load RAM, prompt speed, generation speed, time-to-first-token, completion time, and thermal stability.
4. Blind-review continuation quality, voice preservation, instruction following, invention rate, and usefulness.
5. Add it only if the quality improvement is material and interactive latency remains acceptable.

Until that evidence exists, Qwen is **an optional benchmark candidate, not the recommended installed engine**.

## 6. Exact Music recommendation

### Engine decision

**Use Tone.js as a locally vendored, pinned orchestration layer over the incumbent Web Audio engine.** Do not replace Web Audio; Tone.js is built on it. Preserve the current sound-generation and WAV code until the new path passes audio parity.

This is a meaningful upgrade over raw inline Web Audio because the desired workstation now needs a reusable transport, synchronized patterns, tempo changes, swing, instruments, effects, and offline arrangement rendering. Those are exactly the abstractions Tone.js supplies. It remains lightweight compared with a native DAW or server process and runs only while the Music room is active.

### Workstation engine stack

1. **Audio foundation:** Web Audio `AudioContext`, gain graph, analyser only for real measured levels, and `OfflineAudioContext`.
2. **Transport/scheduling:** Tone.js Transport/Sequence/Part, locally hosted—never CDN-loaded.
3. **Drums:** existing synthesis plus one small license-audited local kit for stronger kick/snare/hat/percussion choices.
4. **Instrument:** Tone.Synth/MonoSynth initially; no SoundFont runtime in slice one.
5. **Patterns:** versioned `music-pattern-v2` JSON with 4–8 tracks, 16/32 steps, velocity, mute, volume, pattern A–D, and arrangement slots.
6. **Export:** real offline WAV render; later optional MIDI export.
7. **AI:** LFM text proposals for beat grids, chords, song structure, lyrics, and production ideas. All structured musical output is schema-validated and previewed before explicit apply.

### FluidSynth gate

FluidSynth is worth adding later if the owner wants piano, bass, strings, and General MIDI timbres. It is not the first engine because real-time browser-to-native control, process lifecycle, SoundFont selection/licensing, and project portability are extra architecture. Add it only after the Tone/Web Audio groove bench is stable, using one verified small SoundFont and a fixed localhost or render adapter.

### What must be audibly true

- Each pad produces sound on pointer and keyboard activation.
- Muting or changing volume audibly changes the output.
- BPM and swing affect actual scheduling.
- Pattern changes and arrangement order are heard, not merely displayed.
- Saved patterns reopen sample-for-sample and event-for-event.
- Exported WAV has valid headers, expected duration/sample rate, and non-silent distinct tracks.
- AI remains optional; the entire instrument works with Model Bay offline.

## 7. Hardware and resource impact

| Engine/action | Expected impact on this machine | Operating limit |
|---|---|---|
| LFM writing inference | Observed ~797 MB model working set; CPU-bound, ~18.7 seconds for verified short rewrite | One inference at a time; model auto-start OFF; bounded context/output |
| Qwen3 1.7B Q8 benchmark | 1.83 GB weights plus runtime/KV; likely substantially slower | Isolated benchmark only; never co-load with LFM |
| Tone/Web Audio Music | Low-to-moderate browser CPU during playback; memory dominated by decoded samples | Small sample kit; stop/dispose audio graph on room close; no fake continuous analyser |
| Fabric.js/Canvas | Memory rises with pixel dimensions and undo snapshots | Cap imported working dimensions; bounded undo; thumbnails instead of duplicate full images |
| Vosk | Official small-model class ~300 MB runtime | Push-to-talk; one recognizer; command grammar retained |
| whisper.cpp tiny benchmark | Official ~273 MB model runtime, plus capture/app overhead; CPU latency unknown | Optional dictation only after real-time-factor benchmark |
| Native FFmpeg | Low idle; can saturate all CPU cores during encode | One job; low-priority process; default preview proxies/720p; cancellation/cleanup |
| SQLite FTS/ripgrep | Low for current corpus; short CPU/disk bursts | Project-scoped queries; result caps; cancellation |

## 8. Dependencies and packaging rules

### First slice dependencies

Write Studio AI Actions adds **no new runtime or model dependency**.

Music's later slice may add:

- one version-pinned Tone.js production artifact stored locally;
- its license and upstream source/version record;
- a very small, explicitly licensed drum sample set with per-file hashes and attribution;
- no CDN, npm runtime, bundler, or network request.

### Later optional dependencies

- Fabric.js, vendored and pinned, with security/version evidence.
- Official Windows FFmpeg/ffprobe build from a trusted documented source, hashed and registered outside ordinary source rollback where appropriate.
- FluidSynth plus a separately licensed/hashed SoundFont only after explicit approval.
- whisper.cpp tiny.en or Piper only as benchmark candidates, never silent installs.

Large binaries/models/media must live in governed adjacent resource storage and be referenced by manifests/hashes. They must not bloat ordinary rollback packages or be committed to a public repository.

## 9. Risks and controls

| Risk | Control |
|---|---|
| Small model invents prose facts or loses voice | Proposal-only output, selected context, source comparison, owner approval, no original mutation |
| Model context truncation hides relevant material | Show selected sources, token estimate, omissions, and exact hashes before execution |
| Larger model makes UI unusably slow | Benchmark on actual laptop before registration; retain LFM default; never co-load models |
| Tone.js migration breaks existing sound | Build adapter, parity tests, preserve old engine until real audio/WAV verification passes |
| Samples have unclear licenses | Ship only audited local assets with license/attribution/hash manifest |
| Browser audio timing drifts | Tone Transport scheduled against audio clock; test under UI load |
| Canvas history exhausts RAM | Dimension and undo limits; serialized object deltas; explicit flattening |
| Media bloats SQLite | Content-addressed files with SQLite metadata/relationships; transactional registration |
| FFmpeg command injection/path traversal | No free-form command; fixed operation schemas and argument arrays; bounded directories |
| FFmpeg overheats/stalls laptop | One low-priority job, progress from real output, timeout/cancel, 720p defaults |
| Voice integration creates command bypass | HOLLOW_DECK remains authoritative; fixed localhost API; sensitive-field and confirmation checks server-side |
| Build room becomes arbitrary shell | Repository-owned allowlist, visible exact command/scope, no owner-supplied executable/arguments |
| Capability UI lies | Engine registry distinguishes known, installed, enabled, running, healthy, and suitable |

## 10. Implementation order

1. **Write Studio AI Actions** — no new engine; highest owner value and lowest infrastructure risk.
2. **Music Groove Bench 2** — Tone.js/Web Audio transport, pads, mixer, patterns, arrangement, WAV.
3. **Explore Search and Evidence Cards** — expose FTS5 and provenance.
4. **My Work media/version foundation** — typed preview and content-addressed storage before richer media.
5. **Images Light Table 2** — Fabric.js/Canvas editing and version compare.
6. **HOLLOW_DECK voice console integration** — retain Vosk/SAPI; no engine replacement.
7. **Control Room capability matrix** — truthful probes from the now-stable engines.
8. **Build Inspector/Test Station** — read-only first; fixed test catalog.
9. **Video Edit Station** — durable media and ordered edits, then native FFmpeg.
10. **Optional engine benchmarks** — Qwen3, whisper.cpp, Piper, FluidSynth, one at a time and only with explicit approval.

Sanctuary, Crossroads, New Idea, Modules, Settings, and Recover receive only integration changes required by these slices.

## 11. First bounded implementation slice

### Write Studio AI Actions — candidate scope

This is the recommended first implementation. It is **not implemented by this document** because the current instruction asks for engine selection and a deliverable, not approval to stage/deploy a release.

Expected paths:

- `app/index.html` — writing action rail, context selector, proposal/compare surface.
- `app/assets/write-room.js` — selection/version capture, request state, result compare/decision.
- `app/assets/write-room.css` — one dominant writing workstation at desktop and 390 px.
- `app/assets/builder-workspace.js` — shared job rendering only where necessary.
- `companion/local_worker_kit.py` — fixed writing task categories, version/source gates, inference routing.
- `companion/builder_output.py` — writing proposal metadata/section/hash validation.
- `companion/server.py` — only bounded API additions that cannot use current job endpoints.
- focused Python and JavaScript tests.
- service worker cache update only if frontend assets change.

No model download, database replacement, provider call, or schema migration is expected. If selection metadata does not fit the current packet, extend the versioned JSON job contract before proposing a table migration.

### Lifecycle

Current Write document/version  
→ select exact text  
→ choose fixed writing action  
→ choose explicit project-context records  
→ inspect source/version/context/model packet  
→ approve plan  
→ explicitly run local inference  
→ proposed result beside unchanged original  
→ approve or reject result  
→ save as new version or inactive draft  
→ My Work reopen / compare / export / rollback

## 12. Exact verification requirements

### Protected baseline

- Record live source, launcher, protected artifact, and immutable SQLite hashes/counts before candidate work.
- SQLite must remain `integrity_check=ok`, zero foreign-key violations, and `user_version=13` unless a separately justified migration is approved.
- Existing 59 artifacts and owner projects/sources remain exact before disposable lifecycle work.
- Existing Model Bay manifest/model/runtime hashes remain exact.

### Write functional tests

- All ten fixed action profiles produce valid request packets.
- Selection offsets/hash and document version/hash are exact.
- Blank selection is allowed only for whole-document actions explicitly designed for it.
- Stale source/version blocks plan execution and result approval.
- Project context includes only explicitly selected registered records in owner-selected order.
- Context limit/truncation is visible and deterministic.
- Offline/disabled/missing/hash-mismatched model states fail honestly.
- AI output is a proposal and never overwrites the source.
- Plan approval and result approval remain separate.
- Duplicate approval/replay/cross-job token use fails.
- Approved result saves exactly one chosen version/draft.
- Rejection creates no content artifact.
- Refresh/restart recovery never silently resumes inference or saving.
- Compare, read-aloud, My Work reopen, TXT/MD/JSON export, cancellation, and rollback pass.
- One real lifecycle uses owner-approved/disposable project text; protected source remains byte-identical.
- No cloud/provider/external request occurs.

### Model quality/performance acceptance

- Measure model start time, working set/peak, prompt tokens/sec, generated tokens/sec, first-token time, and completion time.
- Test short and maximum-supported context packets.
- UI remains responsive while inference runs.
- No second model is resident.
- Stop/cancel leaves the Workshop healthy.
- The deterministic Write tool remains usable with AI offline.
- Owner quality review is recorded as a manual acceptance boundary; automated tests do not claim literary quality.

### Music verification for the following slice

- Real pointer and keyboard pad activation produces non-silent output.
- Timing, BPM, loop, swing, play/stop, mute, volume, patterns, and arrangement change actual audio.
- Audio graph is disposed on stop/room close; no stuck notes.
- Pattern schema validation and exact save/reopen/version round trip pass.
- Offline WAV header, channels, sample rate, duration, and non-zero energy pass.
- AI musical suggestions are valid structured proposals and cannot mutate a pattern without explicit apply.
- Music remains fully playable when Local AI is offline.
- Desktop and 390×844 layout, visible focus, reduced motion, and zero horizontal overflow pass.

### Full release gate

- Isolated candidate workspace and temp output outside live TWIS.
- Exact candidate manifest and rollback package.
- Focused tests during development, then one complete inherited Python and JavaScript/UI suite.
- Syntax, compile-all, smoke, API, builder/worker, browser desktop/mobile, recovery, and rollback tests proportional to changed systems.
- Candidate-to-live byte equality for every deployed path.
- Console errors/warnings/page errors 0/0/0.
- Test ports/processes closed and disposable artifacts removed.
- Final source/database/protected hashes and counts verified.

## RANDY — HERE'S WHAT I WOULD ACTUALLY PUT IN EACH ROOM

- **Write:** the existing LFM/llama.cpp engine, upgraded with serious selection-aware writing tools and project context. Keep originals sacred.
- **Music:** Tone.js over the working Web Audio engine, real pads, patterns, mixer, synth, arrangement, and WAV export.
- **Images:** Canvas plus Fabric.js for a real light-table editor. No generator until real hardware exists.
- **Video:** native FFmpeg behind safe fixed operations. One modest export at a time.
- **Explore:** SQLite search, exact evidence cards, citations, and clearly labeled AI inference.
- **Build:** Git, ripgrep, real test output, diffs, and governed Codex handoffs—never an open shell.
- **Talk:** keep Vosk and SAPI; connect HOLLOW_DECK visibly without swallowing it into TWIS.
- **My Work:** SQLite authority plus hashed media files, versions, previews, provenance, and reopen.
- **Control:** one truthful capability board fed by real engine health.
- **Modules, Settings, Recover, New Idea, Sanctuary, Crossroads:** keep the proven engines and make them support the work, not compete with it.
