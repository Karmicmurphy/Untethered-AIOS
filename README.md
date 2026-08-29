# TWIS Untethered AIOS

**Untethered AIOS** is the experimental operating layer for Twis Holo Workshop.

It is not a replacement for the Workshop, not a cloud rewrite, and not a claim that a full AI operating system already exists.

The goal is narrower and more useful:

> Turn the Workshop's existing rooms, engines, artifacts, receipts, and governed adapters into bounded capabilities that an operating layer can schedule, permission, observe, recover, and compose.

## Repository role

This repository is an **experimental descendant** of the verified Twis Holo Workshop.

```text
Authoritative local Workshop
C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS
            |
            | authenticated snapshot only
            v
workshop/                  aios/
verified baseline          experimental operating layer
            \              /
             \            /
              integration tests
```

The authoritative local Workshop remains outside this repository until Codex deliberately authenticates and copies an approved code-safe snapshot into `workshop/`.

## Core rules

- Local Workshop remains the private authority.
- Never reconstruct newer Workshop code from memory or stale GitHub state.
- Never write into the authoritative local Workshop during AIOS experimentation.
- No paid provider is required.
- No provider/model is allowed to become the operating-system authority.
- Workers receive explicit capabilities and bounded resource scopes.
- Artifacts and receipts are durable; engines and models are replaceable.
- Human approval remains required for permanent/destructive/publish/deploy actions.
- No broad autonomous write/delete/publish behavior.
- A scaffold is not a capability until tests and evidence prove it.

## What is included now

The current candidate contains:

- a runnable Python standard-library Kernel V0.2 candidate;
- in-memory and rollback-journal SQLite process-table implementations;
- explicit process lifecycle states and transition authority;
- cooperative scheduler;
- event wait, wake, suspend, resume, cancellation, and restart recovery;
- capability registry with canonical scoped permissions and narrow child delegation;
- one candidate-only, project-scoped Workshop artifact-metadata read adapter;
- structured hash-linked audit receipts;
- deterministic fake-model worker backend;
- one Kernel-owned deterministic REFLEX execution bridge with an exact
  resource-scoped capability grant;
- one declared `request-normalizer-v1` cheap handler and proven
  Computation-Memory reuse/invalidation path;
- baseline hashing/authentication script;
- unit tests;
- Codex operating instructions;
- repository-local engineering skills;
- architecture and release gates;
- the authenticated, code-safe Workshop baseline imported during Phase 0.

## Reproduce the current candidate

1. Check out `successor/reflex-execution-bridge-v0.1`.
2. Read `AGENTS.md`, `CODEX_START_HERE.md`, and `docs/CODEX_HANDOFF.md`.
3. Verify `evidence/workshop-baseline.json` against the authoritative local
   Workshop without writing to that Workshop.
4. Verify the imported `workshop/` tree against the same manifest.
5. Run `scripts\test.bat` and `python scripts\demo.py`.
6. Do not merge or deploy AIOS work into the production Workshop automatically.

## Run the current kernel tests

Windows:

```bat
scripts\test.bat
```

Any Python 3.10+ environment:

```bash
python -m unittest discover -s tests -v
```

Run demo:

```bash
python scripts/demo.py
```

## Current status

**BOOTSTRAP / EXPERIMENTAL.**

The included kernel is intentionally small and testable. Workshop Read Adapter
V0.1 exposes one real, project-scoped metadata read through the authenticated
Workshop primitive and emits a hash-linked capability receipt. Cognitive
Substrate Campaign 2 adds one bounded REFLEX handler path through the existing
Governor, Kernel capability authority, Computation Memory, and receipt chain.
It remains candidate-only: no live deployment, real provider, or broader
Workshop authority is claimed.
