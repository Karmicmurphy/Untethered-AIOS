# CODEX START HERE — FRIDAY / Untethered AIOS

**Current governing entry: October 2026.** This is the *AIOS component* entry point, not authority to restart the old Workshop bootstrap or to merge/deploy FRIDAY. The earlier Windows-baseline / Kernel V0.2 instructions in this file have been superseded; their historical copy remains in repository Git history and the contextual `docs/CODEX_HANDOFF.md`.

## First: current authority, not an old prompt

1. Read `AGENTS.md`. Its AIOS-local safety requirements remain in force.
2. Resolve the current *cross-repository* job from:
   - [Harness Card — active canonical project](https://github.com/Karmicmurphy/Harness-card/blob/main/state/CURRENT_PROJECT.json)
   - [Harness Card — machine status](https://github.com/Karmicmurphy/Harness-card/blob/main/state/FRIDAY_MACHINE_STATUS.md)
   - [Harness Card — operator receipt](https://github.com/Karmicmurphy/Harness-card/blob/main/state/FRIDAY_OPERATOR_LAST_RUN.json)
   - [Harness Card — Codex clearance and repository reconciliation](https://github.com/Karmicmurphy/Harness-card/blob/main/state/FRIDAY_PRE_CODEX_MACHINE_CLEARANCE_2026-10-22.md)
   - [Harness Card — newest governed integration proof](https://github.com/Karmicmurphy/Harness-card/blob/main/state/FRIDAY_GOVERNED_INTEGRATION_PROOF_2026-10-22.md)
3. Check live branch HEAD, tests, exact source SHAs and draft/merge status before acting. A README, historical bootstrap document, chat handoff, candidate PR or green test **never overrules the live Harness work order**.

## What was already proven

- **Harness:** the existing bounded FRIDAY maintenance operator and CI authority checks run with receipts. A general-purpose autonomous FRIDAY is not proven.
- **Foundry / AIOS:** Foundry's [draft PR #35](https://github.com/Karmicmurphy/temporal-capability-foundry/pull/35), built on `software-builder-v0`, has a green bounded, deterministic Foundation Core -> AIOS test with an independently certified repair receipt ([CI proof](https://github.com/Karmicmurphy/temporal-capability-foundry/actions/runs/39879548240)). It remains a **draft, unmerged** candidate. This does not prove free-form task admission, durable exactly-once recovery, live services or local host integration.
- The Harness-approved executable AIOS kernel SHA at the time of the proof is `8a954439af2b15b00f7c961d83552772b382fd1f`. This repository's later `main` also contains documentation updates. Do not silently repin the canonical runtime to a moving branch.

## Safe Codex first pass: inspect, compare, report

This is the *first job*, not a request to build the entire machine.

- Confirm which repository, branch and exact source commit Codex opened.
- Validate existing `AGENTS.md`, Harness current authority, relevant PRs and latest green tests.
- Review Foundry [#35](https://github.com/Karmicmurphy/temporal-capability-foundry/pull/35), [#34](https://github.com/Karmicmurphy/temporal-capability-foundry/pull/34) and [#31](https://github.com/Karmicmurphy/temporal-capability-foundry/pull/31) **without merging them**. Identify concrete missing integration tests and unsafe engine/subprocess boundaries; do not treat Builder tool write allowlists as a sandbox for a model's separate shell/process.
- Return an exact, smallest candidate-only next step, current source SHA and tests needed. Do not duplicate salvage registries, bootstrap a second repo, or import a new framework.
- **Stop** before a merge, canonical pin promotion, live job dispatch, public/production deployment, secrets, paid service, permission widening, system-wide install, or unbounded local-machine changes unless separately authorized through the appropriate owner gate.

## What stays parked

Android-to-FRIDAY/phone and Cloudflare Preview are explicitly **parked**, not missing prerequisites. So are local/private Workshop rehydration, Windows host recovery, full music/Pro Rig redevelopment and business/commerce work. A cloud-only Codex session is allowed to perform repository inspection and disposable, credential-free candidate tests without pretending it accessed the physical PC.

The historic local Workshop path `C:\\TWIS_FLASHRIVER_REVIEW_READY\\TWIS` is context **only**. Never assert it exists now, reconstruct its content or make physical machine access step one.

## Closeout contract

Return: **verified source**, **what passed**, **what did not run**, **exact PR/commit**, **one bounded next proof**, and **owner approval needed or none**.

For local Windows / historical AIOS bootstrap context only, see `docs/CODEX_HANDOFF.md` and prior Git history. Do not execute Phase 0 / Phase 0.5 / Kernel V0.2 merely because an old document once prescribed it.
