# Foundation Release 0.6 — Deployed Verification

## Decision

**PASS — Release 0.6 deployed, fully verified, and safely recoverable**

Verification date: 2026-07-26  
Active root: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

Release 0.6 is deployed in the active Workshop. The exact governed payload
matches live 16/16, the deployed regression and browser checks pass, the live
Write lifecycle was rolled back and cleaned up, protected source and Worker
Harness state remain exact, and both file rollback and database recovery
evidence authenticate.

## Recovered and authenticated starting state

The starting installation was authenticated as the final Release 0.5 deployed
state before any Release 0.6 candidate work or deployment:

- Release 0.5 deployed report SHA-256:
  `731852196AA48A8DA493785F56A6CA6F8EB6546DB025E4429DE27BA2923E3B7C`;
- frozen Release 0.5 tree: 254 files, 0 unexplained differences;
- protected members: 11/11 exact, including the pre-release database;
- database: integrity `ok`, `user_version=0`, 2 projects, 59 artifacts,
  59 search rows, 2 reviews, 13 receipts, and 0 documents;
- public imported source: 51/51 byte-identical;
- Worker Harness: 56 evidence files exact, registry generation 4, active
  attachment count 0;
- launcher SHA-256:
  `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`;
- active Release 0.6 candidate matches before deployment: 0/16;
- no usable Git history was present: `.git` is a placeholder file, so release
  truth came from files, hashes, reports, receipts, tests, and runtime state.

Recovery checkpoint:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v06verify-019f9210\recovery-checkpoint-20260726.json`

## Artifact Compass completion audit

The recovered isolated candidate was classified and completed without widening
Release 0.6 beyond the durable Write Room:

- **KEEP:** existing application shell, artifact authority, project identity,
  local companion, SQLite, receipts, Worker Harness, source archive, and
  service-worker architecture;
- **REPAIR:** Windows-safe export names and length, autosave error handling,
  browser-recovery quota reporting, recovery-delete request guards, and mobile
  min-content width;
- **COMPLETE:** additive Write schema, recovery, autosave, history, comparison,
  governed restore, deterministic proposals, rollback, export, My Work, owner
  guide, and exact-scope release evidence;
- **TEST:** concurrency, stale saves, malformed and cross-site requests, path
  containment, escaping, interruption/restart recovery, cache refresh, mobile
  layout, receipts, protected hashes, and rollback;
- **DEFER:** rich text, DOCX, collaboration, cloud sync, hosted backup, a
  universal language router, and an AI writing model;
- **CUT/REJECT:** arbitrary workers, unrestricted filesystem or shell access,
  hidden network work, silent mutation, automatic attachment, and automatic
  activation.

The detailed audit is
`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS\FOUNDATION_RELEASE_0.6_ARTIFACT_COMPASS.md`.

## Exact deployment scope

Deployment copied exactly 16 authenticated payload files: 7 replacements,
9 additions, 0 removals.

Replacements:

1. `app/assets/app.js`
2. `app/assets/style.css`
3. `app/index.html`
4. `app/service-worker.js`
5. `companion/server.py`
6. `package.json`
7. `tests/test_worker_harness_ui.py`

Additions:

1. `FOUNDATION_RELEASE_0.6.md`
2. `FOUNDATION_RELEASE_0.6_ARTIFACT_COMPASS.md`
3. `app/assets/write-room.js`
4. `companion/write_room.py`
5. `docs/WRITE_ROOM_0.6_CONTRACT.md`
6. `docs/WRITE_ROOM_0.6_OWNER_GUIDE.md`
7. `tests/test_write_room.py`
8. `tests/test_write_room_api.py`
9. `tests/write-room-ui.test.js`

The payload contains no database, user project, imported source, cache,
bytecode, temporary file, test output, browser profile, or screenshot. The
launcher was not in scope. This deployed-verification report is the single
declared postdeployment evidence addition and is not part of the 16-file
product payload.

Deployment transaction:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v06verify-019f9210\deployment-transaction.json`

Result:

- predeployment replacements: 7/7 exact;
- predeployment additions: 9/9 absent;
- copy transaction: PASS, no automatic rollback required;
- candidate-to-live: **16/16 exact**;
- whole-tree diff immediately after copy: only the approved payload;
- final tree diff: only the approved payload, expected additive database
  migration/receipts, and this report;
- unapproved additions, replacements, or removals: 0.

## Candidate and deployed automated verification

### Isolated candidate

- full Python suite: **131 passed** in 266.52 seconds;
- full JavaScript suite: **20 passed**;
- JavaScript syntax: **7/7 passed**;
- Python compile-all: **37 sources passed**, bytecode routed outside TWIS;
- smoke test: PASS;
- standalone isolated API E2E: PASS;
- Worker Harness and Artifact Inspection API E2E: PASS;
- targeted Write backend/API tests: **11 passed**;
- stale-save conflict: PASS;
- near-simultaneous save: one 200 and one governed 409, as required;
- threaded recovery and SQLite integrity: PASS;
- malformed request, cross-site request, traversal, escaping, export-byte,
  provenance default/opt-in, proposal gate, rejection, approval, restore, and
  both rollback paths: PASS.

### Deployed code

- full Python suite: **131 passed** in 246.57 seconds;
- full JavaScript suite: **20 passed**;
- JavaScript syntax: **7/7 passed**;
- Python compile-all: **37 sources passed**, 80 compiled files including
  imported standard-library dependencies, all outside TWIS;
- smoke test: PASS;
- standalone isolated API E2E: PASS;
- Worker Harness and Artifact Inspection E2E: their 3 tests passed within the
  authoritative 131-test run;
- all Write backend, API, UI-contract, security, concurrency, escaping, cache,
  and navigation regressions passed within the same deployed runs.

The machine's bare system Python does not have `pytest` installed, so one
redundant follow-on invocation could not launch. This did not skip coverage:
the authoritative deployed Python environment had already run all 131 tests,
including the exact Worker Harness and Artifact Inspection E2E files. It is an
environmental invocation detail, not a Workshop product defect.

One pre-existing bytecode cache member was regenerated by the test runner.
It was reconstructed from the authenticated Release 0.5 rollback source,
matched the frozen cache hash exactly, and was restored to
`B917CA45D08F2F5B484C620BECCE24B5474828E349050BE7242CB205FC91F47D`.
No implementation source changed and no test cache residue remains.

## Real-browser verification

### Full isolated acceptance

The full candidate lifecycle passed through the real owner-facing UI with a
disposable server, database, browser profile, cache, and temporary directories:

- create, multi-paragraph edit, visible autosave, interruption recovery,
  browser restart, server restart, My Work rediscovery, and stable identity;
- 11 durable versions;
- plain-language Before/After comparison;
- 3 proposals: 2 rejected and 1 explicitly approved then rolled back;
- restore explicitly applied and rolled back;
- 4 validated TXT, Markdown, and JSON exports;
- default JSON excluded internal provenance; opt-in JSON included it;
- unsupported internet-publishing language returned a bounded unavailable
  result and did not mutate content;
- source files: 43/43 exact;
- service-worker cache: `twis-holo-full-v6`;
- navigation refresh retained `#work`;
- viewport 390x844, document width 390;
- browser console: 0 errors, 0 warnings;
- network origins: loopback only.

Candidate browser receipt:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v06accept-final-20260726\acceptance-verification.json`

### Disposable deployed-code browser

A fresh runtime copied from the deployed source was exercised independently:

- deployed runtime source against live source: 43/43 exact;
- owner UI created a new writing project;
- immediate recovery and autosave requests succeeded;
- durable version 2 reopened after refresh;
- My Work rediscovered the same stable document;
- `#work` survived refresh;
- cache was exactly `twis-holo-full-v6`;
- viewport 390x844, document width 390;
- console: 0 errors, 0 warnings;
- all requests were to `http://127.0.0.1:8798`.

Deployed browser receipt:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v06deployed-browser-20260726\deployed-browser-verification.json`

Mobile screenshot:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v06deployed-browser-20260726\browser\.playwright-cli\page-2026-07-26T07-36-38-386Z.png`

## Bounded live Write lifecycle

A single temporary document was created in the existing
`thousand-year-hangover` project:

- title: `Release 0.6 Live Verification - 2026-07-26`;
- artifact ID: `84d8e11c-f185-42ea-b3b5-d689ac425b93`;
- approval note: `Release 0.6 deployed lifecycle verification`.

The live lifecycle passed:

1. create;
2. durable recovery and reopen;
3. recovery save;
4. named snapshot;
5. version comparison;
6. unsupported internet-publishing command rejection without mutation;
7. findings-only inspection proposal and explicit rejection;
8. modifying formatting proposal held at `awaiting_approval`;
9. explicit approval;
10. TXT, Markdown, default JSON, and provenance JSON export with exact hashes;
11. approved proposal rollback;
12. recovery-first restore;
13. restore rollback;
14. receipt verification;
15. temporary artifact cleanup.

Evidence before cleanup was 9 versions, 2 proposals, 1 restore operation,
4 exports, and 0 pending recovery drafts. Exactly 15 durable receipts remain:
14 lifecycle receipts plus the explicit temporary-artifact deletion receipt.
The four active export copies were hash-verified, copied to external evidence,
and removed from the active project. Final active Write state is 0 documents
and 0 Write lifecycle rows. No Write proposal attached or activated anything.

The first verifier expected a top-level `status` from restore rollback, while
the documented endpoint correctly returns the updated document. Verification
continued from the durable version-9 rollback state. This was a verifier
assertion mismatch, not a product defect.

Live lifecycle receipt:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v06live-evidence-20260726\live-write-lifecycle-verification.json`

## SQLite and protected-state result

Final active database:

- integrity: `ok`;
- `user_version=6`;
- 2 projects;
- 59 artifacts;
- 59 artifact search rows;
- 2 reviews;
- 28 receipts (13 starting + 15 governed lifecycle/cleanup);
- 0 sessions, 0 modules, 0 jobs;
- 0 Write documents;
- 0 Write versions, recovery drafts, proposals, restore operations, or exports;
- SHA-256:
  `FAA793C736F533421E68E2C5CD566A94DE5EC5BB77600555DE63AFD59C49DC3F`.

The WAL was checkpointed after the verification server stopped. A consistent
post-verification recovery copy was created outside TWIS:

`C:\TWIS_FLASHRIVER_REVIEW_READY\.v06live-evidence-20260726\post-verification-workshop.sqlite3`

Backup SHA-256:
`937F58654EADBCCD38F6A67C5C15E8FA69DBF0886099E3DB333B8CD2A4E640F5`

Protected-state audit:

- 10/10 non-database protected members exact;
- launcher exact at
  `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`;
- reviews 2/2 exact;
- 51/51 public imported source artifacts byte-identical;
- private archives and source archive exact;
- Worker Harness inventory 56/56 exact;
- registry generation 4;
- active attachment count 0;
- permission and startup state exact;
- new Worker Harness evidence additions: 0;
- no unapproved import, owner-data deletion, network worker, AI model,
  arbitrary worker, unrestricted shell worker, or automatic activation.

## Rollback verification

Rollback package:
`C:\TWIS_FLASHRIVER_REVIEW_READY\foundation-0.6-rollback`

- rollback manifest and all 9 declared package members authenticate;
- 7/7 predeployment originals authenticate;
- external rollback simulation restored all 7 replacements and removed all
  9 additions;
- simulation did not modify the active release;
- ordinary rollback leaves the additive database intact so later owner writing
  is not destroyed;
- emergency predeployment database backup integrity is `ok`,
  `user_version=0`, SHA-256
  `F6D5CA7145C1F7AF16372F23C0E570C16639DA32733240C307E702978666A6C4`;
- that emergency database backup is for immediate recovery only and must not
  overwrite post-beta owner writing.

Rollback simulation:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v06rollback-simulation-20260726`

## Final process and port state

- Workshop verification processes: stopped;
- browser sessions: closed;
- port 8787: closed;
- port 8875: closed;
- disposable browser port 8798: closed;
- active browser/test cache, bytecode, screenshots, and test outputs added by
  verification: none;
- temporary browser profiles, test databases, screenshots, and verification
  evidence remain outside the active TWIS root.

## Major authenticated release artifacts

| Artifact | SHA-256 |
|---|---|
| Release 0.6 report | `76ED94C7B7483BD8A35CFBFB20003AC0924DF18A61978D939359D1DA4133E22A` |
| Candidate manifest | `45ED53ABE5CE68E4261B8768EE7633B00CB8F4957F205BC2DAC72FD3D34DE277` |
| Rollback manifest | `DD5157568B813BA6EB087E6887701A76E3FD06FD93D684056FE6BAD8684B7C73` |
| Artifact Compass audit | `075F0FAE9F05AF852AF491832AB63419AFF404507234ACDACE37380332F603E7` |
| Deployment transaction | `52F74D0F8A9C213B84702D281067B9B7663CB2FA42CF6782CA7B02C387FD22D1` |
| Deployed browser receipt | `6C5978C6238239CE757F1DB9121F7C3CE82846DB1641A3BDEDD26356B2C36EAF` |
| Live lifecycle receipt | `2DAC4D09D754D8ABE749307F85B989205D8DB599FEB45AE46FF968C7AA543C59` |

## Remaining owner-facing limits

Release 0.6 is intentionally plain-text and local-first. It does not include
rich text, DOCX, collaborative editing, CRDTs, cloud sync, hosted backup, an AI
writing model, or universal natural-language routing. Bounded deterministic
actions are deliberately small. One local companion process may write the
Workshop database at a time. If browser storage is blocked or quota-limited,
the UI reports that limitation and durable server recovery remains available
while the companion is reachable.

These are declared Release 0.6 boundaries, not failed verification gates.

## Owner beta action

Start the Workshop normally, open **Write**, create one real writing project,
write several paragraphs, close and restart the Workshop once, then report
which parts of the workflow feel clear or awkward.
