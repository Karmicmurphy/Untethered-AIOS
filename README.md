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

## First use

1. Create the GitHub repository `TWIS-Untethered-AIOS`.
2. Upload this package.
3. Open the repository in Codex.
4. Tell Codex to read `AGENTS.md` and `docs/CODEX_HANDOFF.md`.
5. Give Codex access to the authoritative local Workshop path:
   `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`
6. Codex must authenticate the current Workshop **before** copying any baseline into `workshop/`.
7. Do not merge AIOS work back into the production Workshop automatically.

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

The included kernel is intentionally small and testable. It is a foundation to beat on, not a declaration that the final Untethered AIOS is finished.
