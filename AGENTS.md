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
6. `docs/CREDIT_EFFICIENT_WORK_SPLIT.md`
7. `skills/artifact-compass/SKILL.md`
8. `skills/credit-efficient-execution/SKILL.md`
9. `skills/direct-successor-autopilot/SKILL.md`
10. `skills/no-drift-build/SKILL.md`
11. `skills/no-broadening-audit/SKILL.md`
12. `skills/receipt-trace-certificate/SKILL.md`
13. `contracts/capability.schema.json`
14. any additional relevant file under `skills/`.

Before any owner-facing UI work also read:

- `docs/UI_DESIGN_SYSTEM.md`
- `skills/high-end-ui/SKILL.md`

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

## Credit-efficiency law

Codex allowance is for local execution, not repeated public research or project-history rediscovery.

Use `docs/CREDIT_EFFICIENT_WORK_SPLIT.md` and `skills/credit-efficient-execution/SKILL.md`.

- Prefer current repo instructions/evidence over giant repeated handoffs.
- Do not repeat public Artifact Compass research when `evidence/ARTIFACT_COMPASS_BOOTSTRAP_FINDINGS.md` already answers it; validate only unresolved/local-fit questions.
- Batch bounded implementation + tests + ordinary fixes + full verification + evidence into one Codex turn where practical.
- Write verbose machine evidence to files and keep chat summaries compact.
- Never solve a usage-limit problem by silently buying credits or enabling auto-reload.

## High-end UI law

Any owner-facing UI must follow `docs/UI_DESIGN_SYSTEM.md` and `skills/high-end-ui/SKILL.md`.

High-end means deliberate hierarchy, spacing, typography, tactile controls, restrained light, cinematic but functional motion, and excellent responsiveness.

Reject generic SaaS styling, rainbow neon, glow everywhere, fake hologram clutter, tiny HUD text, gratuitous 3D, and framework migration purely for fashion.

Preserve the existing static/local shell. Lit and Motion are bounded `TEST` candidates, not permission to rewrite the Workshop.

## Default engineering loop

1. Inspect current repo and git state.
2. Authenticate required baselines.
3. Read current evidence to avoid repeated research/work.
4. If technology/successor choice is involved, run only the unresolved bounded Artifact Compass gate.
5. Define the smallest owner-visible or kernel-contract improvement.
6. Implement in isolation using Direct Successor Autopilot + NDBA.
7. Add or update tests.
8. Run affected tests.
9. Fix ordinary defects automatically.
10. Run the complete suite.
11. Run No-Broadening Audit.
12. Record receipts/traces/evidence.
13. Update state/restart packet.
14. Stop only at a real destructive/live/deployment gate.

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
- use Artifact Compass as an excuse for endless research instead of a bounded decision;
- spend Codex allowance redoing current public research already preserved in repo evidence;
- make owner-facing UI look like generic SaaS, gamer neon, or a stock AI dashboard.

## Codex report format

1. What changed.
2. What Artifact Compass classified/selected when relevant.
3. What tests/evidence passed.
4. What remains partial, deferred, rejected, or blocked.
5. Exact owner gate only when one genuinely exists.
