# AGENTS.md — TWIS Untethered AIOS

This repository is the experimental AI operating layer for Twis Holo Workshop.

Codex should treat this file as the default operating harness.

## Mission

Build a small, local-first, recoverable operating layer that can coordinate Workshop capabilities without turning one model, cloud provider, agent framework, or external runtime into the authority.

The Workshop is the body and owner-facing creative environment.
Untethered AIOS is the nervous system.

## Source-of-truth order

1. `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS` — authoritative local Workshop when available.
2. authenticated snapshot recorded in `evidence/workshop-baseline.json`.
3. `workshop/` — code-safe copied baseline inside this experimental repo.
4. this repository's AIOS implementation and tests.
5. old GitHub Workshop snapshots and memory are reference only.

If these disagree, stop assuming and authenticate the real files.

## Hard boundary

Do not modify the authoritative local Workshop while implementing reversible AIOS experiments.

Changes belong in this repository unless the owner separately approves a production Workshop successor/deployment.

## Must read before substantial work

1. `CODEX_START_HERE.md`
2. `README.md`
3. `docs/ARCHITECTURE.md`
4. `docs/AUTHORITY_AND_GATES.md`
5. `docs/CODEX_HANDOFF.md`
6. `skills/artifact-compass/SKILL.md`
7. `skills/direct-successor-autopilot/SKILL.md`
8. `skills/no-drift-build/SKILL.md`
9. `skills/no-broadening-audit/SKILL.md`
10. `skills/receipt-trace-certificate/SKILL.md`
11. `contracts/capability.schema.json`
12. any additional relevant file under `skills/`.

When the owner asks for a deep dive, multiple passes, frontier search, salvage, or technology sweep, also read:

- `skills/deep-salvage/SKILL.md`
- `skills/better-question-rewriter/SKILL.md`

`CODEX_START_HERE.md` is the definitive launch order for a fresh Codex session and overrides older bootstrap wording if there is any conflict.

## Artifact Compass gate

Artifact Compass is mandatory before:

- selecting a new model/runtime/framework/database/sandbox/protocol;
- adopting a new external dependency that materially affects architecture;
- beginning a major new AIOS successor after current-state authentication;
- replacing a verified mechanism with a different one;
- making a claim that a frontier technology is necessary.

Use the 10-pass method in `skills/artifact-compass/SKILL.md`.

Every serious candidate must be classified:

- `KEEP`
- `CUT`
- `TEST`
- `REJECT`
- `DEFER`

Do not install or integrate a discovery simply because it is interesting. `TEST` means reversible candidate experiment first.

Artifact Compass must end in one bounded direct-successor decision, not a pile of links.

## Default engineering loop

1. Inspect current repo and git state.
2. Authenticate required baselines.
3. If technology/successor choice is involved, run the bounded Artifact Compass gate.
4. Define the smallest owner-visible or kernel-contract improvement.
5. Implement in isolation using Direct Successor Autopilot + NDBA.
6. Add or update tests.
7. Run affected tests.
8. Run the complete suite.
9. Fix ordinary defects automatically.
10. Run No-Broadening Audit.
11. Record receipts/traces/evidence.
12. Update state/restart packet.
13. Stop only at a real destructive/live/deployment gate.

Do not ask for routine permission to test, fix candidate bugs, write manifests, or create rollback evidence.

## AIOS laws

- A worker is a process, not a personality.
- A tool is a capability, not an entitlement.
- Capabilities must be explicit and scope-bounded.
- Models are replaceable compute resources.
- No model self-grants capabilities.
- No worker can elevate its own permissions.
- Every governed mutation emits a receipt.
- Permanent/destructive/publish/deploy operations require an owner gate.
- No hidden network access.
- No silent paid-service fallback.
- Prefer local/free runtimes where useful.
- Discover hardware and model availability at runtime; do not hardcode giant models as mandatory.
- Preserve artifacts and provenance across engine replacement.
- Failure must be observable and recoverable.
- Official sources outrank hype when evaluating technology.
- Hardware reality outranks benchmark fantasy.
- Legal/license fit is part of engineering proof.

## Definition of done for a kernel feature

A feature is not done because code exists.

It is done when:

- contract is explicit;
- tests exercise success and denial/failure behavior;
- no authority boundary is weakened;
- audit evidence exists;
- existing tests remain green;
- No-Broadening Audit is clean;
- status is reported honestly.

## Forbidden drift

Do not:

- rewrite the Workshop from scratch;
- restart already verified successors;
- call scaffolding "working integration";
- copy private runtime databases or personal artifacts into GitHub;
- commit tokens, cookies, browser profiles, model weights, recovered archives, or `.env`;
- add broad filesystem/process/network authority for convenience;
- install system-wide packages without explicit owner need;
- make Rust/WASM/vector DB/framework migration the goal by itself;
- broaden one bounded successor into the entire roadmap;
- merge into production Workshop automatically;
- adopt a technology before establishing its stack position and proof need;
- use Artifact Compass as an excuse for endless research instead of a bounded decision.

## Codex report format

1. What changed.
2. What Artifact Compass classified/selected when relevant.
3. What tests/evidence passed.
4. What remains partial, deferred, rejected, or blocked.
5. Exact owner gate only when one genuinely exists.
