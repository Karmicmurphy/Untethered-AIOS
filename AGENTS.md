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

1. `README.md`
2. `docs/ARCHITECTURE.md`
3. `docs/AUTHORITY_AND_GATES.md`
4. `docs/CODEX_HANDOFF.md`
5. `contracts/capability.schema.json`
6. the relevant file under `skills/`

## Default engineering loop

1. Inspect current repo and git state.
2. Authenticate required baselines.
3. Define the smallest owner-visible or kernel-contract improvement.
4. Implement in isolation.
5. Add or update tests.
6. Run affected tests.
7. Run the complete suite.
8. Fix ordinary defects automatically.
9. Record evidence.
10. Stop only at a real destructive/live/deployment gate.

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

## Definition of done for a kernel feature

A feature is not done because code exists.

It is done when:

- contract is explicit;
- tests exercise success and denial/failure behavior;
- no authority boundary is weakened;
- audit evidence exists;
- existing tests remain green;
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
- merge into production Workshop automatically.

## Codex report format

1. What changed.
2. What tests/evidence passed.
3. What remains partial or blocked.
4. Exact owner gate only when one genuinely exists.
