# TWIS Build + Modules V2 — Capability Bay Candidate

Status: isolated candidate verified; not deployed pending exact-manifest approval.

## Before

Build could create a governed implementation work-order proposal. Modules could display the fixed Workshop capability list and create an inactive module proposal. Neither room had a canonical capability contract, measured hardware qualification, replacement groups, free-first recommendation, verification age, Agent Skill inspection, or bounded protocol catalog.

## Implementation

- Added `twis-capability-v1`, a small JSON contract with explicit lifecycle, cost, network, permission, authority, health, compatibility, provenance, replacement, and verification fields.
- Added a static, hash-addressed registry of 16 truthful current or candidate capabilities. Discovery never means approval and no registry entry can execute itself.
- Added measured Windows hardware profiling and conservative `GOOD FIT`, `MAY WORK`, `TOO HEAVY`, `UNSUPPORTED`, and `UNKNOWN` qualification.
- Rebuilt Modules as a Capability Bay with owner-readable filters and truth cards.
- Connected Build to a deterministic, free-first registry recommendation and hash-bound work-order context.
- Added deterministic proposal scaffolds for TWIS native capabilities, Agent Skills, local/disposable workers, MCP wrappers/adapters, WASI components, Comfy workflows, and Cloudflare free-tier workers. They create text proposals only.
- Added Artifact Compass → Capability proposal handoff without changing Artifact Compass authority.
- Added Agent Skill discovery/validation with lazy resource counts and zero script execution.
- Added MCP 2026-07-28 catalog/discovery metadata with a loopback-only disposable fixture. Tool execution remains disabled.
- Added A2A 1.0 descriptor validation metadata and a WASI 0.3 contract doorway. Execution is deferred.

## Truth boundaries

- No model, OpenVINO, ComfyUI, Wasmtime, MCP platform, provider SDK, container, or dependency was installed.
- No cloud request, provider call, capability execution, dependency installation, activation, or project mutation is available from Capability Bay.
- OpenVINO is cataloged `INCOMPATIBLE` / `UNSUPPORTED` for the detected AMD A4 hardware; it was not installed.
- ComfyUI is a discovered compatibility contract only; no runtime, models, or nodes are installed.
- Cloudflare Workers AI is optional `free-tier`, network/account dependent, not configured, and has no paid fallback.
- The local model entry reports its actual unavailable/offline state; deterministic Workshop tools continue without it.

## Hardware

Detected on 2026-08-23: AMD A4-6210 with Radeon R3, AMD64, four logical processors, Windows 10 Home build 19045, 7,447,904,256 bytes physical RAM, and instruction evidence MMX/SSE/SSE2/SSE3/XSAVE. Candidate server observation after browser verification: about 39.3 MB working set and 30.8 MB private memory for the actual Python server process. Warm metadata requests completed in 18–96 ms; the first registry request, including first-use hardware capture, completed in 653 ms.

## Governance

Build plans bind the registry hash, hardware-profile hash, and a canonical context hash. Any change before result approval is rejected as stale. Plan approval and result approval remain separate. Saved outputs are inactive artifacts, reopen through My Work, export as TXT/Markdown/JSON, and roll back exactly. Capability metadata cannot self-elevate authority.

## Protocol decisions

- Agent Skills: discovery, frontmatter validation, provenance, and lazy file counts only.
- MCP: 2026-07-28 stateless discovery/catalog metadata only; no automatic enablement or invocation.
- A2A: Agent Card/descriptor validation only; execution deferred.
- WASI: contract only. A runtime proof was not justified on this laptop because no suitable runtime was already present and adding one would violate the low-cost boundary.

## Provenance mapping

Current TWIS source IDs/hashes, derived-from relationships, worker identity, timestamps, approval receipts, and output hashes map cleanly to a future external provenance envelope. Full C2PA claims and signing remain intentionally absent. No schema migration was needed.

## Next focused successor

Add a governed Capability Inspection lifecycle that can take one Artifact Compass finding through source re-verification and bounded health evidence before an owner may mark it VERIFIED. Do not install or execute the discovered capability as part of that successor.

