# Codex Handoff — Bootstrap Untethered AIOS

## Context

This is a NEW experimental repository derived from Twis Holo Workshop.

Do not treat the older GitHub Workshop repository as guaranteed current.

Authoritative local Workshop:

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

At the time this bootstrap was created, the Workshop had advanced locally beyond the older GitHub snapshot. Music Loop Deck V1 had already been deployed and live-verified locally. Do not restart that successor.

## First action

Authenticate the authoritative local Workshop before importing a baseline.

Run:

```powershell
python scripts\authenticate_workshop.py `
  --workshop "C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS" `
  --output "evidence\workshop-baseline.json"
```

Inspect the generated exclusions and manifest.

Do not copy databases, secrets, personal artifacts, browser state, generated media dumps, model weights, or other private runtime state.

## Then

1. establish exact local git/file status if available;
2. verify the current local Workshop tests/health applicable to the snapshot;
3. copy only code-safe Workshop files into `workshop/`;
4. preserve the baseline manifest;
5. run this repo's bootstrap tests;
6. begin AIOS development beside the Workshop baseline;
7. integrate one bounded Workshop capability at a time.

## First AIOS successor

Target:

**KERNEL V0.2 — REAL PROCESS LIFECYCLE**

Required:

- process table;
- lifecycle transitions;
- cooperative requeue/yield;
- WAITING + wake event;
- child spawning through kernel authority;
- structured capability calls;
- path/resource scope enforcement;
- receipts;
- deterministic fake backend;
- full unit tests.

Do not begin with Rust, WASM, embeddings, or a giant model.

Those may be evaluated later if evidence shows they solve a real bottleneck.

## Completion language

Do not say "AIOS is built" when only the kernel scaffold exists.

Use precise status such as:

`PASS — KERNEL V0.2 candidate verified`

and list exactly which contracts are real.
