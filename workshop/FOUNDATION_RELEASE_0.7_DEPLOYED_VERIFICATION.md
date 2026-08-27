# TWIS Holo Workshop — Foundation Release 0.7 Deployed Verification

## Final decision

**PASS — Release 0.7 deployed, fully verified, and safely recoverable**

Verification date: 2026-07-26  
Active root: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`  
Release: `0.7 — Talk Room / Twis TalkBox Daily-Use Slice`

Release 0.7 is installed in the active Workshop. The authenticated candidate
matches live 17/17, the complete isolated and deployed regressions pass, the
real-browser lifecycle passes, the single bounded live lifecycle was rolled
back and cleaned, protected owner state remains exact, and the authenticated
rollback package passes a disposable simulation.

No owner engineering verification or beta interval remains.

## Authority and continuity

The active Release 0.6 handoff was authenticated before implementation:

- deployed Release 0.6 report: 14,414 bytes;
- report SHA-256:
  `6FAB789D85912F6318A05832F17B655A7F640D720B83C34D8C96CB2F4EC6727C`;
- authenticated baseline tree: 264/264 exact, where the handoff count of 263
  omitted its own explicit postdeployment report;
- SQLite: integrity `ok`, `user_version=6`, 2 projects, 59 artifacts, 59 search
  rows, 2 reviews, 28 receipts, and 0 Write documents;
- 51/51 public imported sources exact;
- 56/56 Worker Harness evidence files exact;
- registry generation 4 and active attachments 0;
- launcher SHA-256:
  `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`;
- ports 8787 and 8875 closed.

The baseline receipt is:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v07work-20260726\release-0.7-baseline.json`.

Git history was unavailable in the supplied active folder. Authority was
therefore established from the authenticated Release 0.6 report, complete
tree inventory, exact hashes, rollback evidence, tests, database state, and
runtime behavior.

## Recovered TalkBox evidence

The protected `TWIS_TALKBOX_BUILD_FOLDER.zip` was authenticated at SHA-256
`5B8F34A7F3252D6066436C1306F86FC1A4BFDCA7BB910EE36C29530286F0660D`.
All 19 archive entries were extracted outside the active Workshop and read.
No explicit license was present, so no recovered executable code was copied
into Release 0.7. Useful intent was preserved in a new implementation against
the current Workshop architecture.

The KEEP / REPAIR / COMPLETE / TEST / DEFER / CUT / REJECT classification and
per-artifact provenance are recorded in
`FOUNDATION_RELEASE_0.7_ARTIFACT_COMPASS.md`, SHA-256
`69C1EAEAEAA23251D75CD57EEB61319EC33299B9727929AF8D52F1C4B22236D5`.

## Exact deployment scope

Candidate manifest:
`C:\TWIS_FLASHRIVER_REVIEW_READY\FOUNDATION_RELEASE_0.7_CANDIDATE_MANIFEST.txt`  
Candidate manifest SHA-256:
`B9BFF2C7909B49C170487CDFA1C500E50EDC559B0A55D555FFD366898AC078F8`  
Candidate payload:
`C:\TWIS_FLASHRIVER_REVIEW_READY\foundation-0.7-candidate-payload`

The governed payload contains exactly 17 files:

- 8 replacements;
- 9 additions;
- 0 removals;
- 0 data, SQLite, cache, temporary, bytecode, browser, log, screenshot, or
  generated test-output files;
- 0 launcher changes.

Replacements:

1. `app/assets/app.js`
2. `app/assets/style.css`
3. `app/index.html`
4. `app/service-worker.js`
5. `companion/server.py`
6. `package.json`
7. `tests/test_worker_harness_ui.py`
8. `tests/write-room-ui.test.js`

Additions:

1. `FOUNDATION_RELEASE_0.7.md`
2. `FOUNDATION_RELEASE_0.7_ARTIFACT_COMPASS.md`
3. `app/assets/talk-room.js`
4. `companion/talk_room.py`
5. `docs/TALK_ROOM_0.7_CONTRACT.md`
6. `docs/TALK_ROOM_0.7_OWNER_GUIDE.md`
7. `tests/talk-room-ui.test.js`
8. `tests/test_talk_room.py`
9. `tests/test_talk_room_api.py`

This report is the one declared postdeployment evidence addition. It is not a
candidate payload member and is not counted in candidate-to-live equality.

## Transactional deployment

Immediately before deployment:

- all 8 replacement paths matched their authenticated Release 0.6 hashes;
- all 9 addition paths were absent;
- this final report path was absent;
- ports 8787 and 8875 were closed;
- the payload, originals, and rollback package were exact.

The transaction copied only the 17 governed paths. Post-copy verification
proved 17/17 candidate-to-live byte equality. No rollback was needed.

Deployment transaction receipt:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v07work-20260726\deployment-transaction.json`.

## Implemented daily-use slice

Release 0.7 extends the existing SQLite, artifact, project, receipt, recovery,
and Write systems rather than introducing parallel storage. It provides:

- stable Talk artifact identity, project association, owner title, ordered
  entries, timestamps, save state, optimistic concurrency, and transactions;
- immediate browser recovery plus durable server recovery across companion
  restart;
- Talk and My Work discovery and reopen;
- immutable transcript versions, named snapshots, understandable history,
  comparison, recovery-first restore, and restore undo;
- exact-occurrence passage marking, including repeated identical text;
- clean TXT, Markdown, default JSON, and explicit opt-in provenance JSON
  exports;
- deterministic pasted-code inspection without execution, shell, model, or
  network use;
- a fixed, bounded owner-language command layer with honest refusal of
  unrestricted commands;
- governed Talk-to-Write preview, stale-plan gating, required nonblank approval
  note, explicit approval, normal Release 0.6 Write creation, source-preserving
  relationship, receipts, and safe rollback;
- `twis-holo-full-v7` static service-worker cache with API requests excluded.

Imported text and owner text are rendered as text, not executable HTML.
Exports are atomic and bounded to approved locations. There is no AI chat
bridge, model invocation, automatic activation, arbitrary shell, unrestricted
filesystem access, hidden network worker, or automatic install path.

Release contract SHA-256:
`C5FB5D9A169D6B59F07D3BC07E60ED589BA57989B9789942A1B1DC2B3C86008E`  
Owner guide SHA-256:
`D279E0C652886139F1C2B0C6D53B1307B6F4A55F552F6D608528FA65F09897BF`

## Voice capability truth

The text Talk Room is complete and does not depend on voice.

Speech-to-text is enabled only if the browser exposes the standards-track
on-device controls and reports the requested language as already available.
Release 0.7 never invokes language-pack installation and never falls back to
network recognition. The deployed Playwright/Chromium environment did not
prove an installed local recognizer, so the UI truthfully displayed local
speech-to-text as unavailable.

Text-to-speech lists and accepts only voices whose browser-reported
`localService` value is true. Playwright exposed 7 such voices. Play, pause,
resume/stop, and failure states are visible; the exercised browser synthesis
failure was reported without damaging text state.

Microphone access requires an explicit owner action, active listening is
visible, stop is explicit, raw audio is not retained, and a recognition result
remains a reviewable draft before entry creation.

Primary-source basis:

- Web Speech API specification:
  `https://webaudio.github.io/web-speech-api/`
- Chrome speech-synthesis API description, including `localService`:
  `https://developer.chrome.com/blog/web-apps-that-talk-introduction-to-the-speech-synthesis-api`

No claim of universal offline browser voice support is made.

## Automated verification

All test scratch state, Python bytecode destinations, browser profiles, and
temporary databases were outside the active Workshop.

| Check | Isolated candidate | Deployed code |
|---|---:|---:|
| Full Python suite | 139 passed | 139 passed |
| Full JavaScript suite | 31 passed | 31 passed |
| JavaScript syntax checks | 9 passed | 9 passed |
| Python compile-all | passed | passed |
| Smoke test | passed | passed |
| Isolated API E2E | passed | passed |
| Worker Harness and Artifact Inspection E2E | 3 passed | 3 passed |
| SQLite integrity / foreign keys | `ok` / none | `ok` / none |

There were no skipped product checks and no failing tests.

## Disposable real-browser lifecycle

A disposable copy, database, browser profile, and companion on port 8797
verified:

- Talk creation, owner-facing title, project association, typing, paste, and
  literal `<script>` escaping;
- browser recovery and durable recovery after companion restart;
- My Work rediscovery and stable reopen;
- 3 entries, 11 immutable versions, named snapshot, compare, restore, and
  restore undo;
- exact second-occurrence marking of repeated text;
- deterministic Python inspection;
- Talk-to-Write preview, blank-note client rejection, explicit approval,
  simultaneous Talk and Write visibility, rollback, and Write removal;
- a transfer proposal persisted across a full browser restart, stale actions
  stayed hidden, and explicit rejection succeeded;
- exact TXT, Markdown, default JSON, and provenance-selected JSON exports;
- supported snapshot command and honest refusal of unrestricted PowerShell and
  deletion commands;
- truthful local voice state: local STT unavailable, 7 local TTS voices, and
  visible synthesis failure;
- service-worker controller, only cache `twis-holo-full-v7`, and no API cache;
- `#work` navigation survived refresh;
- 390 × 844 viewport with document and body widths of 390 pixels;
- zero unhandled console errors and zero warnings;
- every observed request remained on `http://127.0.0.1:8797`.

Mobile browser evidence:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v07work-20260726\browser-runtime\.playwright-cli\page-2026-07-26T10-47-36-560Z.png`  
Screenshot SHA-256:
`34EBE1785A2AE7DD19249A62DD40205D1A0F866C03350C2A65476408FF5F626E`

The browser and companion were stopped and port 8797 was closed.

## Bounded live governed lifecycle

Exactly one temporary live Talk lifecycle ran with approval note:
`Release 0.7 automated deployed verification`.

It proved:

- Talk create, title, entry, named snapshot, restore, restore rollback, passage
  mark, and deterministic inspection;
- a prepared transfer became stale after a source edit and could not approve;
- blank approval was blocked;
- a current transfer accepted explicit approval;
- the Write artifact was a normal version-1 Write document;
- Talk source content and identity were preserved;
- the Talk-to-Write relationship became active only after approval;
- explicit rollback removed only the unchanged generated Write artifact;
- no unrelated writing was removed;
- the temporary Talk artifact and all Talk/Write product rows were cleaned;
- 15 governed receipts were preserved.

Temporary Talk artifact:
`a04bde09-9e04-4909-b3c9-9229e96194a8`  
Temporary Write artifact:
`0789db54-e5e6-4cda-840c-53b4bd7d9bb4`  
Stale transfer:
`27137a9c-5f24-4d5e-b6fb-cfabfec79b34`  
Approved and rolled-back transfer:
`a493e053-57d1-42f0-8be3-dd8dbe2e9a01`

The lifecycle and cleanup committed before its first verifier encountered a
same-connection SQLite journal-mode lock while finalizing WAL-to-DELETE state.
The product lifecycle was not rerun. A fresh-connection verifier reconstructed
the exact 15-receipt chain, checkpointed safely, restored journal mode
`delete`, and passed every final condition. This was a verifier-finalization
issue, not a product defect or incomplete cleanup.

Live lifecycle receipt:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v07work-20260726\live-evidence\live-talk-lifecycle-verification.json`.

## Final database and protected-state proof

Final active database:

- SHA-256:
  `2FC40F0DBDC770C4C2465385369D0C8C909A00207229ACEE2DEC65EFC60E2A48`;
- integrity `ok`;
- foreign-key violations: 0;
- `user_version=7`;
- journal mode `delete`;
- projects: 2;
- artifacts/search rows: 59/59;
- reviews: 2, byte-for-byte state unchanged;
- receipts: 43 = 28 baseline + 15 governed live-verification receipts;
- documents: 0;
- Talk artifacts: 0;
- Talk rows, Write rows, relationships, sessions, modules, and jobs: all 0.

Post-live recovery backup:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v07work-20260726\live-evidence\post-live-workshop.sqlite3`  
SHA-256:
`B1FDEF23161B460091793E4743B640906A6755075B2B1495D4379BBD6A2A3EF7`  
Integrity: `ok`.

Final protected-state checks:

- 10/10 protected files exact;
- 51/51 public imported source artifacts byte-identical;
- 56/56 Worker Harness evidence files exact;
- registry generation 4;
- active attachments 0;
- launcher exact at
  `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`;
- permissions, startup behavior, projects, and review state unchanged;
- payload 17/17 exact;
- ports 8787, 8875, and 8797 closed.

No import, source deletion, network worker, AI model, arbitrary worker,
unrestricted shell, automatic installation, or automatic activation occurred.

## Whole-tree and generated-artifact accounting

The authoritative non-data tree differs from Release 0.6 only at the 8
approved replacements, 9 approved additions, and this declared final report.
The clean SQLite checkpoint removed the two volatile Release 0.6 WAL/SHM
sidecars. Verification also removed one changed generated
`worker_harness.cpython-312.pyc` and the active `.pytest_cache`; neither is
implementation or deployment evidence. No replacement bytes were inferred or
guessed.

Existing unrelated baseline caches remain outside payload authority and were
not counted as Release 0.7 additions. No Release 0.7 cache, bytecode, browser
artifact, screenshot, temporary database, test output, or log remains in the
active Workshop.

## Rollback and recovery

Rollback root:
`C:\TWIS_FLASHRIVER_REVIEW_READY\foundation-0.7-rollback`  
Rollback manifest:
`C:\TWIS_FLASHRIVER_REVIEW_READY\foundation-0.7-rollback\ROLLBACK_MANIFEST.json`  
Rollback manifest SHA-256:
`52F0BCE30B0437DAE195E40615B228F54095D456FAD44D308E609A6390AF8B52`

Package verification:

- 10/10 declared package members exact;
- 8/8 Release 0.6 originals exact;
- pre-release protected database backup exact and integrity `ok`;
- backup SHA-256:
  `3B80C0ABCDE64E8AD83CFAE33B101553AA4416EF2762F966DFDB2A03D94DA4EF`;
- database rollback is deliberately not automatic, preventing overwrite of
  post-release owner work.

A disposable rollback simulation:

- authenticated the manifest and all package members;
- restored 8/8 originals;
- removed 9/9 additions only after exact candidate-hash checks;
- changed, added, or removed zero ungoverned paths;
- matched 117/117 authoritative Release 0.6 non-data files;
- preserved the active database and protected data by contract;
- left live Release 0.7 at 17/17 exact.

Rollback simulation receipt:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v07work-20260726\rollback-simulation-verification.json`.

## Major evidence hashes

- Release 0.6 deployed report:
  `6FAB789D85912F6318A05832F17B655A7F640D720B83C34D8C96CB2F4EC6727C`
- Release 0.7 candidate manifest:
  `B9BFF2C7909B49C170487CDFA1C500E50EDC559B0A55D555FFD366898AC078F8`
- Release 0.7 candidate report:
  `6205317FF5B4164EBD9C5D6F176D15799A258A795560ADF68BCC13FA6BF78C41`
- Release 0.7 Artifact Compass:
  `69C1EAEAEAA23251D75CD57EEB61319EC33299B9727929AF8D52F1C4B22236D5`
- Release 0.7 rollback manifest:
  `52F0BCE30B0437DAE195E40615B228F54095D456FAD44D308E609A6390AF8B52`
- Pre-release emergency database backup:
  `3B80C0ABCDE64E8AD83CFAE33B101553AA4416EF2762F966DFDB2A03D94DA4EF`
- Final active database:
  `2FC40F0DBDC770C4C2465385369D0C8C909A00207229ACEE2DEC65EFC60E2A48`
- Post-live recovery database backup:
  `B1FDEF23161B460091793E4743B640906A6755075B2B1495D4379BBD6A2A3EF7`
- Launcher:
  `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`

## Owner handoff

Release 0.7 requires no owner technical verification.

**Return the final Release 0.7 output for preparation of the next
direct-successor build.**
