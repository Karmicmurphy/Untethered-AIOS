# TWIS Holo Workshop — Current State

**Current-state identifier:** TWIS Music Loop Deck V1 over the verified Images V2, Video V2, and Build + Modules V2 capability foundation. This identifier applies only when this file's exact hash is present in the active Workshop tree.

**Authoritative live root:** `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

This file is the current answer to “What is TWIS right now?” Historical release documents remain evidence, but they do not supersede this snapshot.

## Architecture

TWIS is a local-first Workshop served by a Python standard-library `ThreadingHTTPServer` companion on `127.0.0.1:8787`. Static HTML, CSS, and JavaScript implement the explorable Sanctuary → Crossroads → room interface. SQLite and local project folders hold owner authority. Fixed workers and deterministic builders use source hashes, separate approvals, receipts, recovery, and bounded rollback.

The Windows desktop launcher in `desktop-launcher/` checks local health, starts the existing companion without a persistent console when needed, waits for readiness, and opens the Sanctuary in a dedicated Windows window. Desktop and Start Menu shortcuts are local installation artifacts; the compiled executable is intentionally excluded from the public repository.

## Fourteen mapped spaces and genuine capability

1. **Sanctuary** — calm local entry and owner shortcuts.
2. **Crossroads** — district-based navigation.
3. **Control Room** — real project/system state and inherited Talk access.
4. **My Work** — artifact filtering, reopening, governed lifecycle views, and owner-only Visitor's Bench review.
5. **New Idea** — inline inactive idea intake with optional real project association.
6. **Write** — Draft Workshop and optional registered local-model assistance.
7. **Images** — Visual Brief Builder plus Images V2 import, non-destructive adjustment, version comparison, storyboard, governed media routing, and owner-guided local background removal with separate proposal review and inactive derived-image saving.
8. **Music** — Song Production Brief Builder plus the native Web Audio Music Studio with playable pads, sequencing, four governed PCM WAV loop channels, beat/bar launch quantization, bounded loop mixing/effects, performance-event capture, arrangements, project saving/versioning/rollback, and WAV rendering.
9. **Video** — Video Production Brief Builder plus Video V2 composition, preview, timeline, titles, motion, transitions, audio, and governed FFmpeg MP4 rendering.
10. **Build** — free-first Capability Advisor and deterministic registry-bound Build Work Order Builder; no automatic code execution.
11. **Explore** — Evidence Compare.
12. **Recover / Machine Room** — receipts, conflicts, diagnostics, interruption recovery, and rollback.
13. **Modules** — canonical Capability Bay, measured hardware fit, Agent Skills/MCP/A2A/WASI catalog boundaries, proposal-only capability scaffolds, legacy module registration, and Local AI Model Bay state.
14. **Settings** — local presentation/companion preferences and bounded Local AI enablement.

No room is empty. Media workstations perform only their explicitly verified local operations: Images does not claim a connected generator, Music does not claim model-generated music, and Video does not claim generative video. Build does not execute code, and module proposals do not install or activate modules.

## Data and governance

- Main database: `data/workshop.sqlite3` (live `user_version=13`; never publish by default).
- Guest namespace: `data/visitor_bench.sqlite3`, separate from owner authority and excluded from Git.
- Original sources remain immutable unless an existing explicit owner workflow authorizes a bounded change.
- Plans and results retain separate owner approval gates.
- Drafts remain inactive until an explicit supported action changes state.
- Receipts record meaningful governed actions. Recovery and rollback never derive authority from GitHub or Cloudflare.

## Local service and UI

- Origin: `http://127.0.0.1:8787/` only.
- Backend: Python standard library plus SQLite FTS5; no web framework migration.
- UI: static, dependency-light HTML/CSS/JavaScript with responsive room layouts and reduced-motion handling.
- Desktop path: desktop shortcut → launcher → health/start gate → Sanctuary.
- Background-removal runtime: adjacent, hash-verified OpenCV 4.14.0 plus NumPy 2.5.2; invoked only by a fixed local adapter for an explicit owner preview and never kept resident.

## GitHub relationship

`Karmicmurphy/Ollie_Twis_Holo_workshop` is a public code/documentation/test baseline, not runtime authority. The live folder is not replaced from GitHub. Private databases, user projects, uploads, guest submissions, exports, logs, credentials, model weights, compiled local binaries, and rollback evidence are excluded. Repository updates are branch/PR based and history preserving.

## Cloudflare relationship and current state

Cloudflare is an optional remote path, never the source of Workshop authority. The old Worker/Durable Object “remote hull” source is retired. The target is Cloudflare Access + named Tunnel to the unchanged loopback origin + origin-side JWT validation and backend authorization.

At this snapshot no authenticated Cloudflare account inventory was available, `cloudflared` was not installed as a Windows service, and no current hostname/tunnel/policy is claimed verified. Public remote access therefore remains **not deployed** until the owner authorizes/authenticates the account-side configuration gate.

## Remote roles prepared at the origin

- **OWNER** — full APIs after a validated owner Access application audience and allowlisted identity.
- **GUEST_CREATOR** — Visitor's Bench Write/Music sandbox and only that identity's guest records.
- **VISITOR** — read-only presentation boundary; writes are denied.

The origin never trusts query parameters, client role fields, CSS visibility, or an unvalidated identity header. Remote requests fail closed when a token, issuer, signature, audience, expiry, or role mapping is invalid. Local loopback desktop access remains OWNER.

## Local AI state and future boundary

Release 0.17 includes an optional registered llama.cpp-compatible Local AI Model Bay. Its existing Liquid model registration is preserved, but it is not the architectural baseline for future research. No model is installed, downloaded, enabled, or activated by this consolidation. Future tiered routing is documented in `docs/LOCAL_AI_ROUTING_FUTURE.md`.

## Capability foundation

`config/capability-registry.json` is the canonical application-level capability registry. `twis-capability-v1` records identity, lifecycle state, cost, hardware fit, runtime/protocol, fixed permissions, authority, provenance/receipt/rollback support, replacement group, evidence, limitations, and verification age. It is metadata—not installation or execution authority.

Build reads a hash-bound registry/hardware snapshot when preparing a capability work order. If either snapshot changes before execution or result approval, the job fails stale. Modules can inspect and filter registry truth, validate Agent Skill metadata without running scripts, catalog MCP metadata with no auto-enabled tools, and prepare inactive text scaffolds. A2A and WASI are descriptor/contract doorways only. ComfyUI, OpenVINO, remote providers, and discovered open-source candidates remain unavailable unless a later governed release separately installs and verifies them.

The registered OpenCV GrabCut capability is the bounded exception: its adjacent runtime is installed, exact-file verified, network-free after provisioning, and available through Images. It reads one registered image by exact artifact ID and SHA-256, accepts only numeric rectangle/brush controls, returns a proposed transparent PNG, and requires explicit owner approval before saving a new inactive image. It never overwrites the selected source.

## Known limitations

- Cloudflare account/DNS/Access/tunnel/service configuration requires authenticated owner access and is not represented as complete here.
- Remote identity policies require real audience tags, team domain, and explicit identity allowlists supplied outside Git.
- Visitor's Bench deliberately supports only bounded Write/Music text submissions and explicit owner copy/promotion; it is not social collaboration.
- Cloud access depends on the local Workshop service being running and healthy.
- Compiled launcher/runtime/model assets are local resources and are not reconstructed by a source-only clone.
- Capability discovery does not monitor the internet in the background. Protocol, free-tier, and candidate records become `AGING`, `STALE`, or `UNKNOWN` until deliberately reverified.
- GrabCut is assisted rather than one-click semantic AI. Hair, fur, transparency, clutter, and low-contrast boundaries can require owner keep/remove corrections or a later separately approved quality mode.
