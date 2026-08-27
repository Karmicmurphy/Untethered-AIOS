# Twis Holo Foundation Release 0.7

Date: 2026-07-26  
Release theme: Talk Room / Twis TalkBox daily-use slice

## Release decision boundary

This report describes the isolated, authenticated Release 0.7 candidate.
Deployment is proven only by the exact candidate manifest, transactional copy
receipt, candidate-to-live equality, deployed regression, temporary live
lifecycle, protected-state audit, rollback simulation, and final deployed
verification report.

## Authenticated Release 0.6 starting state

Before candidate work, the active Workshop was independently authenticated:

- Release 0.6 final report SHA-256:
  `6FAB789D85912F6318A05832F17B655A7F640D720B83C34D8C96CB2F4EC6727C`;
- 264 current files matched the expected Release 0.6 tree 264/264, with no
  missing, changed, or unexpected member (the handoff's 263 count omitted its
  own final deployed-verification report);
- database SHA-256:
  `FAA793C736F533421E68E2C5CD566A94DE5EC5BB77600555DE63AFD59C49DC3F`;
- SQLite integrity `ok`, foreign keys clean, `user_version=6`;
- 2 projects, 59 artifacts/search rows, 2 reviews, 28 receipts, and 0 Write
  documents or lifecycle rows;
- 51/51 public imported sources byte-identical;
- 56/56 Worker Harness evidence files exact, registry generation 4, and 0
  active attachments;
- launcher SHA-256:
  `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`;
- ports 8787 and 8875 closed;
- Git history was unavailable, so release truth came from files, hashes,
  reports, receipts, tests, protected state, and runtime behavior.

Candidate construction and every test used roots outside the active TWIS
folder. The active product was not modified during recovery or candidate work.

## What Release 0.7 adds

### Durable Talk

Talk sessions use stable existing Workshop conversation artifacts linked to a
project. Ordered entries, owner-facing titles, timestamps, save state,
recovery, immutable versions, named snapshots, comparison, recovery-first
restore and undo, marked passages, exports, transfer relationships,
deterministic inspections, and receipts extend the existing SQLite authority.

Immediate browser recovery and debounced durable recovery survive browser and
companion interruption. Every mutation is base-version-bound; stale work is
blocked rather than overwritten.

### Talk to Write

The owner previews either checked entries or the complete transcript. Preparing
the proposal creates a Talk recovery version. Approval requires a non-blank
note and creates a normal Release 0.6 Write document, receipt, and relationship
without changing Talk. Awaiting or approved proposals recover after a browser
restart. Stale proposals cannot execute. Rollback removes only the exact,
unchanged version-1 document created by that transfer.

### Deterministic inspection and constrained commands

Selected pasted code can be classified and counted lexically for imports,
functions, classes, markers, and repeated lines. It is never executed or sent
to a model. Approved Workshop artifacts still use the existing governed
Artifact Inspection room.

A fixed owner-language classifier opens only visible supported actions.
Unsupported shell, filesystem, internet, or arbitrary execution wording is
refused without state change.

### Voice truth

Text Talk is complete without voice. The browser enables STT only if it proves
on-device `processLocally` support and an already available language pack.
Network recognition and automatic pack installation are disabled. A transcript
remains a review draft and raw audio is never retained.

Read-aloud lists only `localService=true` voices. Play, pause, stop, completion,
and failure are visible; failure never changes text. No voice engine, model, or
asset is shipped.

### My Work, export, and offline shell

My Work projects Talk title, project, stable identity, modified/save/recovery
state, entry/version counts, and useful actions. TXT, Markdown, and JSON
exports are local, atomic, hash-receipted, and path-bounded. JSON provenance is
excluded by default and included only by explicit opt-in.

The static cache is `twis-holo-full-v7`, includes the Talk client, retires older
Workshop caches, and never caches API responses.

## Safety boundaries

- no cloud, paid service, API key, subscription, account, telemetry, or hosted
  database;
- no AI/model dependency or automatic model installation;
- no arbitrary shell, filesystem worker, network worker, or unrestricted tool;
- no microphone activation without an owner action;
- no automatic attachment, activation, startup execution, import, or deletion;
- no imported-source, review, permission, private-archive, launcher, or Worker
  Harness mutation;
- no data, cache, bytecode, browser profile, screenshot, log, or test output in
  the deployment payload;
- one supported local companion writer process per database.

## Candidate verification

| Gate | Result |
|---|---|
| Authenticated Release 0.6 baseline | PASS — 264/264 tree, protected state exact |
| Existing Release 0.6 regression before Talk work | PASS — 131 Python, 14 JavaScript |
| Full Release 0.7 Python suite | PASS — 139 passed |
| Full Release 0.7 JavaScript suite | PASS — 31 passed |
| JavaScript syntax | PASS — 9 files |
| Python compile-all | PASS — external bytecode root |
| Smoke and isolated API E2E | PASS |
| Worker Harness and Artifact Inspection API E2E | PASS — 3 tests |
| Talk backend/API/security/recovery/transfer/export tests | PASS |
| Real browser daily-use lifecycle | PASS |
| Browser/server restart recovery | PASS |
| Transfer preview, blank-note gate, approval, My Work, rollback | PASS |
| Durable transfer recovery after full browser restart | PASS |
| TXT/Markdown/default JSON/provenance JSON | PASS — four exact local exports |
| Repeated-text passage selection | PASS — second occurrence preserved exactly |
| Deterministic inspection and governed artifact link | PASS |
| Voice | PASS — local STT unavailable shown truthfully; 7 local TTS voices discovered; synthesis failure visible and text-safe |
| Service worker/navigation refresh | PASS — `twis-holo-full-v7`, `#work` retained |
| Mobile | PASS — 390×844 viewport; document and body width 390 |
| Browser console | PASS — final clean context 0 errors, 0 warnings |
| Browser network | PASS — static and API requests only to `127.0.0.1` |
| Acceptance SQLite | PASS — integrity `ok`, foreign keys clean, `user_version=7` |

The browser exercise created three entries, eleven versions, one exact marked
passage, one deterministic inspection, four exports, an explicitly approved
Write document that was rolled back, and a current transfer proposal that
remained visible after a full browser restart and was explicitly rejected.
All browser and test state remained outside active TWIS.

## Candidate defects repaired before freeze

1. A blank approval was rejected correctly by the API but produced an expected
   HTTP 400 console entry. The visible client now blocks the request while the
   server remains authoritative.
2. Pending or approved transfer evidence was durable but was not rebound to the
   visible panel after a full browser restart. The session now restores the
   newest current proposal and its exact approve/rollback actions.
3. An older pending proposal could be surfaced after the Talk version changed.
   The client now binds proposal actions to the current source version and
   displays stale evidence without permitting execution.
4. Marking repeated text originally risked choosing its first occurrence. The
   browser selection now uses the exact DOM Range offsets.
5. The browser requested a missing favicon, producing an otherwise unrelated
   console error. A local data favicon removes that request.

## Declared limits

Release 0.7 deliberately omits rich text, collaboration, cloud sync, hosted
backup, a universal agent, IDE, arbitrary tool execution, local-model manager,
network speech, language-pack installation, and background recording. These
are boundaries, not missing daily-use gates.

## Owner use

The narrow guide is `docs\TALK_ROOM_0.7_OWNER_GUIDE.md`. After a final deployed
PASS, no owner engineering verification or beta interval is required. The
single owner action is to return the final Release 0.7 output for preparation
of the next direct-successor build.

