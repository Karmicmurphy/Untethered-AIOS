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

This bootstrap contains:

- a runnable Python standard-library AIOS kernel scaffold;
- process table and lifecycle states;
- cooperative scheduler;
- event bus;
- capability registry with scoped permissions;
- audit receipts;
- deterministic fake-model worker backend;
- baseline hashing/authentication script;
- unit tests;
- Codex operating instructions;
- repository-local engineering skills;
- architecture and release gates;
- a placeholder for the authenticated Workshop baseline.

## Current cloud-first use — October 2026

This repository already exists at `Karmicmurphy/Untethered-AIOS`. **Do not create a replacement repository.**
This is the AIOS kernel/runtime component of a *five-repository* Foundation, not the complete FRIDAY machine.

1. Read `AGENTS.md`, then the **current** cross-project authority in
   [Harness-card/state/CURRENT_PROJECT.json](https://github.com/Karmicmurphy/Harness-card/blob/main/state/CURRENT_PROJECT.json)
   and [FRIDAY_MACHINE_STATUS.md](https://github.com/Karmicmurphy/Harness-card/blob/main/state/FRIDAY_MACHINE_STATUS.md).
2. Read [the Harness operator receipt](https://github.com/Karmicmurphy/Harness-card/blob/main/state/FRIDAY_OPERATOR_LAST_RUN.json).
   A successful scheduled bounded operator is **not** proof of free-form FRIDAY autonomy.
3. Use the existing repository/cloud CI and bounded branch/test workflows first.
   The local Workshop/Windows folder is currently **unavailable for inspection**, not missing
   and not permission to recreate or copy personal data.
4. Keep the existing phone-to-Workshop / Cloudflare Preview path **parked**.
   No new remote machine endpoint, provider account, scheduler, secrets or production deployment.
5. When the real local Workshop host is available again, independently authenticate its
   source **before** any baseline import. Do not imply that a cloud-only AIOS test
   verifies that private local machine.

For Codex, read `docs/CODEX_HANDOFF.md` as updated *historical plus current* context.
The existing Foundry FRIDAY native/startup candidate remains **unmerged and not host-proven**;
inspect rather than automatically promoting it.

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

**BOOTSTRAP / EXPERIMENTAL (AIOS kernel only).**

The included kernel is intentionally small and testable. It is a foundation to beat on, not a declaration that the final Untethered AIOS is finished.
