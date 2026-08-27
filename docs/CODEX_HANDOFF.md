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
6. run the mandatory bounded Artifact Compass reality sweep;
7. begin AIOS implementation beside the Workshop baseline;
8. integrate one bounded Workshop capability at a time.

## Updated Artifact Compass requirement

Before choosing implementation technologies for a successor, read and apply:

- `skills/artifact-compass/SKILL.md`
- `skills/direct-successor-autopilot/SKILL.md`
- `skills/no-drift-build/SKILL.md`
- `skills/no-broadening-audit/SKILL.md`
- `skills/receipt-trace-certificate/SKILL.md`

For deeper research or broad questions, also use:

- `skills/deep-salvage/SKILL.md`
- `skills/better-question-rewriter/SKILL.md`

Artifact Compass must be official-source-first, free-first, local-first where practical, legal/open-source-aware, and hardware-measured.

Serious findings are classified:

`KEEP / CUT / TEST / REJECT / DEFER`

Every candidate must have an exact stack position and a reason it affects the current successor.

Salvage mechanisms instead of cloning/importing entire platforms by default.

The sweep ends when another pass is unlikely to change the bounded successor decision. It must not become endless research.

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

Artifact Compass may improve HOW this successor is implemented, but it should not replace the successor with a broader project unless current evidence proves the target itself is wrong.

Do not begin with Rust, WASM, embeddings/vector DB, a giant model, provider integration, or a framework migration merely because research found them.

Those are `DEFER` by default unless evidence shows they solve a current verified bottleneck.

## Execution discipline

Use:

`Artifact Compass -> Direct Successor Autopilot -> NDBA -> tests/evidence -> No-Broadening Audit -> receipt/trace/certificate`

Fix ordinary candidate defects automatically.

Do not modify the authoritative Workshop.

## Completion language

Do not say "AIOS is built" when only the kernel scaffold exists.

Use precise status such as:

`PASS — ARTIFACT COMPASS bounded reality sweep complete`

then, when proven:

`PASS — KERNEL V0.2 candidate verified`

and list exactly which contracts are real.
