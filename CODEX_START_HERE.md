# CODEX START HERE — TWIS Untethered AIOS

This is the first file a fresh Codex session should read after `AGENTS.md`.

## What this repository is

`Karmicmurphy/Untethered-AIOS` is the experimental operating-system descendant of Twis Holo Workshop.

It is NOT the production Workshop repository and must not overwrite the authoritative local Workshop.

Authoritative local Workshop:

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

Recommended local Untethered AIOS checkout:

`C:\TWIS_FLASHRIVER_REVIEW_READY\Untethered-AIOS`

Keep them as SIBLING folders. Do not nest the AIOS Git repository inside the Workshop Git repository.

```text
C:\TWIS_FLASHRIVER_REVIEW_READY\
├── TWIS\                    authoritative Workshop
└── Untethered-AIOS\         experimental AIOS repo
```

## Fresh Codex session objective

Do not start by inventing more architecture.

Do this in order:

### PHASE 0 — authenticate the real Workshop

1. Inspect this repo and read:
   - `AGENTS.md`
   - `CODEX_START_HERE.md`
   - `docs/AUTHORITY_AND_GATES.md`
   - `docs/CODEX_HANDOFF.md`
   - `skills/workshop-baseline/SKILL.md`
2. Confirm the authoritative Workshop exists at:
   `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`
3. Treat that Workshop path as READ-ONLY during this program.
4. Create a candidate branch in this AIOS repo from current `main`:
   `bootstrap/workshop-baseline`
5. Run:

```powershell
python scripts\authenticate_workshop.py `
  --workshop "C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS" `
  --output "evidence\workshop-baseline.json"
```

6. Inspect the manifest and exclusions. Do not blindly copy private/runtime state.
7. Verify the authoritative Workshop health using its own current tests and launch evidence where practical. Do not restart Music Loop Deck V1; it is already deployed/live-verified in the authoritative Workshop.
8. Import only the authenticated code-safe snapshot into this repo:

```powershell
python scripts\import_workshop_baseline.py `
  --manifest "evidence\workshop-baseline.json" `
  --destination "workshop"
```

9. Re-hash and verify the imported baseline exactly matches the authenticated code-safe tree.
10. Run Untethered AIOS bootstrap tests:

```powershell
scripts\test.ps1
```

11. Record exact evidence and commit ONLY to the AIOS candidate branch.

### PHASE 1 — KERNEL V0.2

After Phase 0 is verified, continue automatically into the first real AIOS successor.

Target:

`KERNEL V0.2 — REAL PROCESS LIFECYCLE`

Required contracts:

- persistent process table abstraction;
- explicit PID/parent PID;
- READY/RUNNING/WAITING/SUSPENDED/DONE/FAILED/CANCELLED;
- deterministic cooperative scheduler;
- real yield/requeue;
- event wait + kernel wake;
- child spawning through kernel authority;
- child grants cannot exceed parent grants;
- structured capability invocation;
- canonical path/resource scope enforcement;
- mutation receipts;
- deterministic fake model/runtime for tests;
- crash/failure evidence;
- complete unit tests.

Do NOT begin with:

- Rust rewrite;
- WASM sandbox migration;
- vector database;
- large local model installation;
- provider integration;
- cloud authority;
- full Workshop redesign.

Those are later evidence-based decisions, not Phase 1 goals.

## Workshop integration law

The Workshop is the body. Untethered AIOS becomes the nervous system underneath it.

Do not refactor every room at once.

Prove one bounded capability path at a time:

```text
existing Workshop function
-> bounded adapter
-> capability registry
-> worker permission
-> kernel scheduling
-> artifact/receipt
-> verification
```

Existing owner-visible Workshop behavior must remain usable while the AIOS path is introduced.

## Standing autopilot

Proceed automatically through reversible work:

- inspect;
- implement;
- test;
- fix ordinary candidate defects;
- rerun tests;
- create evidence;
- make manifests;
- simulate rollback;
- clean candidate state.

Do not stop for routine permission.

STOP before:

- modifying `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`;
- deploying AIOS into the live Workshop;
- destructive data changes;
- external publishing;
- paid-service activation;
- credential/permission widening.

## Honest completion language

Phase 0:

`PASS — WORKSHOP BASELINE authenticated and imported into Untethered AIOS candidate`

Kernel successor:

`PASS — KERNEL V0.2 candidate verified`

Never say the full AIOS is finished when only one kernel successor is verified.

## First message for a fresh Codex chat

Use this:

> Read `AGENTS.md` and `CODEX_START_HERE.md` completely. This is the new Untethered AIOS repository. The authoritative Workshop is `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS` and must remain read-only. Execute Phase 0 exactly, authenticate/import the current code-safe Workshop baseline into this repo on a candidate branch, run all required verification, then continue automatically into KERNEL V0.2. Do not restart already-deployed Music Loop Deck V1. Fix ordinary candidate defects automatically. Stop only at a real protected/live deployment gate.
