# Twis Holo Foundation Release 0.6

Date: 2026-07-26  
Release theme: durable daily-use Write Room

## Release decision boundary

This file describes the authenticated Release 0.6 deployment payload. The exact
candidate hashes, predeployment checks, rollback members, transaction result,
deployed regressions, live verification lifecycle, and final safety decision
are recorded in the external governed release evidence:

- `FOUNDATION_RELEASE_0.6_CANDIDATE_MANIFEST.txt`
- `foundation-0.6-rollback\ROLLBACK_MANIFEST.json`
- `FOUNDATION_RELEASE_0.6_DEPLOYED_VERIFICATION.md`

Release 0.6 does not become proven deployed merely because this report exists.
Deployment is proven only when every manifest candidate hash equals the active
file and the whole-tree comparison contains only the declared payload plus the
explicit final verification report.

## Authenticated starting state

The current active root was independently authenticated as the frozen,
deployed Release 0.5 baseline before candidate work:

- active inventory: 254 files;
- frozen-to-live differences: 0;
- protected files: 11/11 exact;
- launcher SHA-256:
  `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`;
- SQLite integrity: `ok`;
- SQLite `user_version`: 0;
- projects: 2;
- artifacts/search rows: 59/59;
- reviews: 2;
- receipts: 13;
- writing projects: 0;
- Worker Harness registry generation: 4;
- active attachments: 0;
- Release 0.6 payload matches in live before deployment: 0.

The live database, imported sources, reviews, receipts, project files, private
archives, launcher, and Worker Harness evidence were not used as candidate test
state.

## What Release 0.6 adds

### Durable writing projects

A writing project is an existing Workshop `document` artifact with a stable
UUID and project ID. The artifact remains the current authority. Five additive
tables preserve immutable versions, recovery drafts, bounded proposals,
recovery-first restore operations, and exports. Schema initialization is
idempotent and sets SQLite `user_version` to 6 without rewriting existing
artifacts, reviews, sources, or receipts.

### Honest save and recovery

- Browser recovery is written immediately on input.
- Durable recovery is debounced to the local companion.
- Autosave and Save now bind to the version opened by the owner.
- A stale or competing save returns a conflict and does not overwrite either
  version.
- Successful changed saves create an immutable version, update search, clear
  recovery, and write a receipt.
- A browser or service restart presents newer recovery as an explicit choice.
- Storage denial or quota failure is visible and never falsely described as
  recovery-ready.

### History, comparison, restore, and rollback

- Named snapshots and saved versions have visible causes and timestamps.
- Comparisons show plain-language added, removed, and replaced operations with
  Before and After text.
- Restore uses a modal confirmation whose safe default keeps current writing.
- Restore saves the current text as a recovery version first.
- Restore undo works only while the restored version remains current.

### Bounded Write actions

Release 0.6 supports five deterministic local actions: inspect, summarize,
clean formatting, repeated passages, and structure. Every plan declares no
network, no AI model, no shell, no source mutation, and an explicit decision
gate.

Findings-only proposals do not mutate text. A modifying proposal is bound to
the source version and SHA-256, remains awaiting approval, and creates both a
recovery version and applied version only after explicit approval. Rejection
preserves the source. An applied proposal can be rolled back while current.
Unsupported commands return a bounded unavailable message.

No Write proposal attaches a worker result, activates a capability, grants
permission, executes at startup, or bypasses the existing Worker Harness.

### Receipt-backed export

TXT, Markdown, and JSON exports use Windows-safe bounded paths, UTF-8, a unique
microsecond timestamp, an atomic temporary-file replace, and a SHA-256 receipt.
Default JSON omits internal identity. The owner must expand Advanced provenance
and opt in before artifact ID, project ID, version, content hash, and saved time
are included.

### My Work and offline shell

My Work projects the same stable document identity, version count, save state,
recovery state, History, and Export actions. The existing service worker uses
cache `twis-holo-full-v6`, includes the Write client, removes older Workshop
caches, and never caches local API responses.

## Safety and implementation boundaries

- no runtime package or external diff library;
- no cloud, telemetry, hosted storage, account, API key, or paid dependency;
- no AI/model dependency;
- no arbitrary command execution;
- no shell or unrestricted filesystem worker;
- no hidden network worker;
- no automatic approval, attachment, activation, import, or deletion;
- no new storage engine;
- no launcher change;
- no imported-source, private-archive, review, or permission change;
- no data, cache, bytecode, browser artifact, screenshot, or test output in the
  deployment payload.

Local mutation requests are serialized by one process-wide re-entrant lock.
SQLite connections use a five-second timeout and `busy_timeout=5000`, and
schema/WAL initialization runs once per database path. The supported contract
is one local companion process; multi-process writers to the same database are
deferred.

## Candidate verification

All authoritative candidate tests used disposable data, cache, bytecode, and
browser roots outside the active TWIS folder.

| Gate | Authenticated result |
|---|---|
| Complete Python suite | PASS — 131 passed |
| Complete JavaScript suite and syntax | PASS — 20 tests; 7 syntax checks |
| Python compile-all | PASS — 37 sources, external bytecode root |
| Smoke | PASS |
| Isolated API E2E | PASS |
| Worker Harness and Artifact Inspection API E2E | PASS — 3 tests |
| Write backend/API tests | PASS — 11 tests |
| Concurrency | PASS — simultaneous same-base save produced one success and one 409 conflict |
| Request and path safety | PASS — malformed JSON/content type, cross-site mutation, and traversal rejected |
| Export | PASS — byte-exact TXT/Markdown; JSON provenance excluded by default and included only by opt-in; receipt hashes exact |
| Escaping | PASS — source markup remains text; Write rendering does not assign imported text through `innerHTML` |
| Real browser | PASS — create, edit, autosave, browser/server restart, My Work rediscovery, recovery, history, compare, proposals, approval, restore, both rollback paths, four exports |
| Mobile | PASS — 390 px viewport and 390 px document width after responsive regression repair |
| Service worker | PASS — controlled by `twis-holo-full-v6`; refresh retained My Work |
| Clean browser | PASS — 0 errors, 0 warnings; requests only to `127.0.0.1` |
| Acceptance SQLite | PASS — integrity `ok`, `user_version=6`, 11 versions, 3 proposals, 1 rolled-back restore, 4 exports, 0 recovery drafts |
| Acceptance source immutability | PASS — 43/43 runtime source files exact |

The real-browser acceptance intentionally introduced one offline interval.
The resulting `ERR_INTERNET_DISCONNECTED` resource messages were expected fault
evidence, not unhandled application errors. A subsequent clean isolated browser
context completed with zero console errors and zero warnings.

## Candidate defects repaired before release freeze

1. Export filenames could exceed conservative Windows full-path limits for long
   project/title paths. Filename length is now derived from the resolved export
   directory, bounded to 240 full-path characters, and uniqueness includes
   microseconds.
2. The client HTTP helper referenced an undefined save cause on non-autosave
   errors. Autosave-only retry behavior now lives in the save path, while other
   failures remain truthful and visible.
3. A browser storage failure could be followed by a false recovery-ready
   status. Local recovery now returns a success flag and the UI claims readiness
   only after storage succeeds.
4. Recovery DELETE now receives the same JSON content-type and cross-site
   mutation protections as other state changes.
5. The mobile app grid could retain a 917 px min-content width in a 390 px
   viewport. The single responsive track and sidebar can now shrink to the
   viewport; a static regression and fresh browser measurement protect it.

## Known limits and deferred work

- plain text only; rich text and DOCX are deferred;
- no collaborative editing, CRDT, cloud sync, or hosted backup;
- no AI writing model or universal natural-language router;
- bounded deterministic actions are intentionally small;
- only one local companion process may write a Workshop database;
- browser storage can be unavailable or quota-limited, in which case the UI
  reports the limitation and durable server recovery remains available when
  the companion is reachable.

## Owner use

The narrow owner guide is `docs\WRITE_ROOM_0.6_OWNER_GUIDE.md`. After the final
deployed verification reports PASS, the owner should create a real writing
project, write several paragraphs, close and restart the Workshop once, and
report which parts of the flow feel clear or awkward. That beta observation is
owner validation, not a missing engineering gate.
