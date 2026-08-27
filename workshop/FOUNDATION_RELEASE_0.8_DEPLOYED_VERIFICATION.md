# TWIS Holo Workshop — Foundation Release 0.8 Deployed Verification

## Final decision

**PASS — Release 0.8 deployed, fully verified, and safely recoverable**

Verification date: 2026-07-26  
Active root: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`  
Release: `0.8 — Local API Worker Kit / First Nanite Crew`

Release 0.8 is installed in the active Workshop. The authenticated candidate
matches live 22/22, the isolated and deployed regressions pass, the disposable
real-browser lifecycle passes, all four fixed workers completed governed live
lifecycles, every temporary mutation and product row was cleaned, protected
owner state remains exact, no attachment or activation remains, and both
predeployment and post-live rollback simulations pass.

No owner engineering verification or beta interval remains.

## Authenticated starting state

Release 0.7 was independently reauthenticated before successor work:

- deployed report SHA-256:
  `46357E7110FAF01F2F8AEA7AC6DF0EB40F8F5009F134313C1E2A7E4F9FCD2B67`;
- complete active inventory: 271/271 files exact;
- SQLite SHA-256:
  `2FC40F0DBDC770C4C2465385369D0C8C909A00207229ACEE2DEC65EFC60E2A48`;
- SQLite integrity `ok`, foreign-key violations 0, `user_version=7`;
- 2 projects, 59 artifacts, 59 search rows, 2 reviews, and 43 receipts;
- 0 Write documents, 0 Talk sessions, and 0 local worker jobs;
- 51/51 public imported sources byte-identical;
- 56/56 Worker Harness evidence files exact;
- registry generation 4 and active attachments 0;
- launcher SHA-256:
  `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`;
- ports 8787, 8875, and 8797 closed;
- the existing Release 0.7 suite passed: 139 Python and 31 JavaScript tests,
  syntax, compile-all, smoke, isolated API E2E, Worker Harness E2E, and
  Artifact Inspection E2E.

Git history was unavailable in the supplied active folder. Release authority
therefore came from files, hashes, release reports, manifests, rollback
evidence, SQLite state, receipts, tests, and observed runtime behavior.

## Alignment and bounded architecture

`FOUNDATION_RELEASE_0.8_ARTIFACT_COMPASS.md` records the focused KEEP, REPAIR,
COMPLETE, TEST, DEFER, CUT, and REJECT decisions.

Release 0.8 extends the existing loopback companion, Workshop SQLite database,
projects, registered artifacts, receipts, `jobs` table, My Work, Talk, Write,
Worker Harness, and Artifact Inspection. It does not introduce a parallel
application or storage system.

The prior generic owner-writable `/api/jobs` shape is retired with HTTP 410.
Earlier unbounded `/read-file`, `/scan-folder`, arbitrary operation, shell,
Python, subprocess, filesystem, network, plugin, attachment, activation, and
module-promotion shapes are rejected.

## Exact deployment scope

Candidate manifest:
`C:\TWIS_FLASHRIVER_REVIEW_READY\FOUNDATION_RELEASE_0.8_CANDIDATE_MANIFEST.txt`  
Candidate manifest SHA-256:
`357FDE317E579B4E8A0DBC2D24F82E2C5EFFED9FDDA9E721BC6EBDD02D36A8BF`  
Candidate payload:
`C:\TWIS_FLASHRIVER_REVIEW_READY\foundation-0.8-candidate-payload`

The governed payload contains exactly 22 files:

- 11 replacements;
- 11 additions;
- 0 removals;
- 0 `data/**`, SQLite, cache, bytecode, browser, screenshot, log, temporary,
  or generated test-output files;
- 0 launcher changes.

Replacements:

1. `app/assets/talk-room.js`
2. `app/assets/write-room.js`
3. `app/index.html`
4. `app/service-worker.js`
5. `companion/server.py`
6. `package.json`
7. `tests/e2e_api_test.py`
8. `tests/talk-room-ui.test.js`
9. `tests/test_talk_room_api.py`
10. `tests/test_worker_harness_ui.py`
11. `tests/write-room-ui.test.js`

Additions:

1. `FOUNDATION_RELEASE_0.8.md`
2. `FOUNDATION_RELEASE_0.8_ARTIFACT_COMPASS.md`
3. `app/assets/local-worker-kit.css`
4. `app/assets/local-worker-kit.js`
5. `companion/local_worker_kit.py`
6. `docs/LOCAL_API_WORKER_KIT_0.8_CONTRACT.md`
7. `docs/LOCAL_API_WORKER_KIT_0.8_OWNER_GUIDE.md`
8. `docs/WORKER_PACKET_0.8_CONTRACT.md`
9. `tests/local-worker-kit-ui.test.js`
10. `tests/test_local_worker_api.py`
11. `tests/test_local_worker_kit.py`

This report is one declared postdeployment evidence addition. It is not a
candidate payload member and is not counted in candidate-to-live equality.

## Transactional deployment

Immediately before deployment:

- all 271 active Release 0.7 files matched their frozen size and SHA-256;
- all 11 replacement paths matched their authenticated predeployment hashes;
- all 11 addition paths were absent;
- this final report path was absent;
- ports 8787, 8875, 8797, and 8798 were closed;
- all 22 payload files, all 11 originals, every rollback package member, and
  the protected emergency SQLite copy were exact.

The transaction atomically copied only the 22 governed paths, verifying each
temporary copy before replacement and retaining automatic file rollback on
failure. No rollback was needed.

Post-copy verification proved:

- candidate-to-live equality: 22/22;
- live files immediately after deployment: 282;
- complete tree: authenticated Release 0.7 baseline plus only the 22 governed
  candidate changes;
- missing, unexpected, and removed paths: 0/0/0;
- no database, data, launcher, source, review, permission, private archive,
  receipt, Worker Harness, registry, or attachment path was deployed.

Deployment receipt:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v08work-20260726\release-0.8-deployment-receipt.json`  
SHA-256:
`D40B284AA2C63177B4AA2ED3A8FCDD6C8831CD8BD63F8D3270C0676BF36267F3`

## Implemented first nanite crew

### Approved Text Reader

Reads one explicitly selected registered UTF-8 text artifact, current Talk
session, or current Write document. It reports exact encoding, size,
characters, lines, content, and source hash. It accepts no owner-language
filesystem path and does not modify its source.

### Code Structure Inspector

Reuses the existing deterministic lexical inspection behavior for supported
registered text code. It separates proven lines, imports/dependencies,
functions, classes, and TODO/FIXME markers from heuristic probable-language
and repeated-line findings. It reports `sourceExecuted=false`, claims no
semantic understanding, and uses no shell, model, or network.

### Note Proposal Worker

Uses explicitly selected current Talk, Write, or registered artifact content.
It shows a complete proposed note before mutation. A separate nonblank result
approval creates exactly one draft note, never attaches or activates it, and
retains exact job/source/hash provenance. Rollback removes only the unchanged
note bound to that job and hash.

### Package Manifest Validator

Reads one explicitly selected registered JSON manifest or ZIP. It validates
canonical member paths, members, expected and unexpected entries, hashes,
duplicates, symlinks, encryption facts, member count, and expanded-size
limits where evidence permits. It does not extract, install, execute, import,
attach, or activate package content.

## Worker and packet contracts

The Worker Kit contract is:
`docs\LOCAL_API_WORKER_KIT_0.8_CONTRACT.md`  
SHA-256:
`021544D17A3966307763A73C5CC2454141E4B27B92CD30665A5D4EC124115260`

The bounded `worker-packet-v1` contract is:
`docs\WORKER_PACKET_0.8_CONTRACT.md`  
SHA-256:
`DD2F3F0AE4D44CC2BAD627ADD6C25B5861A66684A1811D0DD34E368C0A7C622F`

The narrow owner guide is:
`docs\LOCAL_API_WORKER_KIT_0.8_OWNER_GUIDE.md`  
SHA-256:
`E9F1325DD821F20A006007A907DFC38B4B862B17AD9F13BCC1EC9D3E25FE0EBB`

Every fixed worker contract contains a stable ID, owner-facing description,
one responsibility, supported sources, required and prohibited permissions,
input/output/runtime limits, deterministic classification, network denial,
output schema, validation rules, mutation policy, approval and receipt rules,
rollback behavior, version, contract hash, and implementation hash.

Every plan binds the canonical packet, source, selection, worker contract,
worker implementation, expiry, and plan using SHA-256. Packets include one
source reference and only the minimum selected content needed for the job.
They omit unrelated project history, private archives, reviews, credentials,
settings, attachments, and permissions.

The fixed internal API supports:

- list and inspect supported workers;
- list eligible registered sources;
- create, approve, or reject a bounded plan;
- execute only an approved current fixed worker;
- inspect status, output, evidence, and history;
- reject or explicitly approve a validated result;
- cancel and recover eligible jobs;
- roll back an accepted note mutation;
- delete terminal job history while retaining receipts.

State, failure, interruption, expiry, stale plans, duplicate execution,
cancellation, result acceptance, rollback, attachment, activation, and module
promotion are independently represented. A crash never makes output accepted,
attached, active, or trusted.

## Security and recovery boundaries

Verified enforcement includes:

- loopback-only companion and worker API;
- fixed worker, route, method, field, source-type, and action allowlists;
- strict `application/json`, request-size, and cross-site checks;
- canonical project/source containment plus traversal, junction, symlink,
  malformed-project, and ZIP-member controls;
- current registered source/hash/version verification before execution;
- plan, packet, contract, implementation, source, selection, and expiry gates;
- bounded two- or five-second runtime and bounded output schemas;
- SQLite busy timeout, a process write lock, immediate transactions, rollback,
  restart interruption marking, and idempotent recovery;
- dynamic owner and source text rendered as text or read-only values;
- no shell, subprocess, dynamic Python, `eval`, arbitrary filesystem path,
  network worker, AI model, plugin installation, self-modification, automatic
  import, attachment, activation, or promotion.

Validated output is evidence, not owner approval. Approval still does not mean
attachment, activation, or module promotion.

## Automated verification

All scratch state, browser profiles, temporary databases, pytest caches, npm
caches, and generated Python bytecode were kept outside the active Workshop or
removed immediately after whole-tree detection.

| Check | Isolated candidate | Deployed code |
|---|---:|---:|
| Full Python suite | 153 passed | 153 passed |
| Full JavaScript/UI suite | 36 passed | 36 passed |
| JavaScript syntax checks | 10 passed | 10 passed |
| Python compile-all | passed | passed |
| Smoke test | passed | passed |
| Isolated API E2E | passed | passed |
| Worker Harness, Artifact Inspection, Worker Kit API E2E | 6 passed | 6 passed |
| SQLite integrity / foreign keys | `ok` / 0 | `ok` / 0 |

The 153 Python tests include backend, API, schema, contract, packet,
transaction, receipt, output validation, cancellation, stale-plan, expiry,
timeout, duplicate execution, interruption recovery, safe cleanup, result
rejection, note approval/rollback, path, malicious worker ID, malformed
project, oversized input, unsupported file, and unsafe ZIP checks.

The 36 JavaScript/UI tests include the Release 0.8 My Work workflow, Talk and
Write entry points, owner-language Worker Cards, blank approval blocking,
literal text rendering, service-worker cache, navigation refresh, history,
and 390-pixel mobile layout.

There were no skipped product gates and no failing product tests.

## Disposable real-browser lifecycle

A disposable Workshop/database, browser profile, and companion verified the
complete Release 0.8 owner flow at 1440 × 1000 and 390 × 844:

- all four Worker Cards visible in My Work with honest responsibilities,
  reads, possible creation, prohibited access, plan, state, result, evidence,
  decision, rollback, and history;
- Talk and Write worker actions use their current saved source without asking
  for technical identifiers;
- Approved Text Reader result explicitly rejected;
- Code Structure Inspector plan survived a full refresh and result approved;
- Note Proposal Worker created a proposal from selected Write text, accepted
  explicit approval, created one draft note, and exactly rolled it back;
- Package Manifest Validator proved its expected members and hashes and had
  its result approved;
- all four browser jobs remained unattached and inactive;
- blank plan and result approval blocked before failed network requests;
- stale state and changing source selection were correctly gated;
- service-worker cache contained only `twis-holo-full-v8`;
- navigation refresh retained the current approved job;
- hostile Talk title, imported text, selected passage, note title, and worker
  output remained literal and did not execute;
- mobile document/body width was exactly 390 pixels with one worker-card
  column and no horizontal overflow;
- console errors: 0;
- console warnings: 0;
- unhandled page errors: 0;
- observed browser requests: 185, all loopback.

Browser evidence:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v08work-20260726\browser-evidence\release-0.8-browser-evidence.json`  
SHA-256:
`5D0DD0773EA1F52F8699DEC3C47F3BC6B0E1FDCB18E1EEF39B8A9D4D85EA0B30`

Desktop screenshot SHA-256:
`E2054DC1DFBF69299F683933D4D8900F64C051B02E92511FA26EFB3A3FA59A20`  
390-pixel screenshot SHA-256:
`18306359995D81378B12F1BFECAAA43895A11674BB3FAB29324E94838F1F93A4`

The disposable browser and companion were stopped.

## Governed live worker lifecycles

The active Release 0.8 companion ran one complete governed lifecycle for each
fixed worker using approval note:
`Release 0.8 automated deployed verification`.

### Approved Text Reader

- source: authenticated artifact
  `9217e4a7-7254-53a6-a75e-1d20e0754d86`;
- source SHA-256:
  `E4EFEDCAB226193F35EAE9E1CB6070102D7FD336B70A5C3205D33976D48BB38A`;
- blank plan approval rejected without state change;
- returned exact byte-faithful UTF-8 content and source hash;
- validated output explicitly rejected;
- terminal evidence rows before cleanup: 4;
- unattached and inactive.

### Code Structure Inspector

- temporary registered Python source SHA-256:
  `0E05B81B96BE37E8C2FA36A55E1FD86F4C9CCDB96B4C332EADF6B1B2425E9A5F`;
- facts and separately labeled heuristics returned;
- source execution false, network false, shell false;
- blank result approval rejected without state change;
- validated result explicitly approved;
- terminal evidence rows before cleanup: 4;
- unattached and inactive.

### Note Proposal Worker

- source: the same authenticated AGENT.md artifact;
- selected content was bound into the packet and source hash;
- validated proposal shown before mutation;
- explicit approval created exactly one draft note;
- source remained byte-identical;
- explicit rollback removed exactly that unchanged job-bound note;
- terminal state `rolled_back`;
- terminal evidence rows before cleanup: 5;
- unattached and inactive.

### Package Manifest Validator

- temporary registered manifest SHA-256:
  `85B5BB398BDDDCC755823B7D452414C43458E5AA8E9E12D63CB90503B5C0178B`;
- expected member: `release08_probe.py`;
- expected hash:
  `0E05B81B96BE37E8C2FA36A55E1FD86F4C9CCDB96B4C332EADF6B1B2425E9A5F`;
- missing, unexpected, unsafe, duplicate, and hash-mismatched members: 0;
- validation passed;
- install, execution, import, and activation all false;
- result explicitly approved;
- terminal evidence rows before cleanup: 4;
- unattached and inactive.

After evidence capture:

- all 4 successful-run job rows were deleted;
- all 17 successful-run evidence rows were deleted;
- receipts were preserved;
- the temporary accepted note had already been rolled back;
- both temporary registered artifacts and search rows were deleted;
- the exact two-file temporary import directory was removed;
- final temporary jobs, evidence rows, notes, artifacts, search rows, and files:
  0.

Live lifecycle evidence:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v08work-20260726\release-0.8-live-worker-lifecycles.json`  
SHA-256:
`75ED2ABCF29878D17F4A0273883B92CDEEBF9F3B9785CA22D470208F6D655402`

### Verifier retry accounting

Three earlier live-verifier attempts stopped after valid product transitions
because the external evidence collector expected:

1. provenance at `provenance` rather than the returned `advanced` field;
2. newline-normalized text rather than the worker's byte-faithful CRLF text;
3. `executed` rather than the returned `sourceExecuted` fact.

These were evidence-script defects, not product defects. No product code was
changed. Each retry's terminal job and two temporary imported artifacts were
cleaned through governed APIs, the exact temporary directory was removed, and
all receipts were deliberately preserved.

Receipt accounting is therefore:

- Release 0.7 baseline receipts: 43;
- final successful four-worker run and cleanup: 25;
- three evidence-collector retries and cleanup: 29;
- final receipts: 97.

The 54 new receipts contain:

- 4 folder imports and 8 matching artifact deletions;
- 8 plans created and 8 explicitly approved;
- 8 executions completed;
- 4 results rejected and 4 explicitly approved;
- 1 note created and 1 exactly rolled back;
- 8 terminal job-history deletions with receipts preserved.

The retry evidence is retained because deleting receipts would violate the
Release 0.8 recovery and provenance contract.

## Final database and protected-state proof

Final active database:

- bytes: 909,312;
- SHA-256:
  `EE9B63B8AF1CBCC5AE6D3250B32B0E2887F8B8BB82D4E9FE1C478B30523423FD`;
- integrity `ok`;
- foreign-key violations: 0;
- `user_version=8`;
- journal mode `delete`;
- projects: 2;
- artifacts/search rows: 59/59;
- reviews: 2, exactly unchanged;
- receipts: 97;
- documents: 0;
- Talk artifacts: 0;
- notes: 0;
- jobs: 0;
- local worker evidence rows: 0;
- Talk rows, Write rows, relationships, sessions, and modules: all 0;
- WAL/SHM sidecars: absent.

Post-live recovery backup:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v08work-20260726\post-live-workshop.sqlite3`  
SHA-256:
`EE9B63B8AF1CBCC5AE6D3250B32B0E2887F8B8BB82D4E9FE1C478B30523423FD`  
Integrity: `ok`.

Final protected-state checks:

- 10/10 protected files exact;
- 51/51 public imported source artifacts byte-identical;
- authenticated AGENT.md exact at
  `E4EFEDCAB226193F35EAE9E1CB6070102D7FD336B70A5C3205D33976D48BB38A`;
- 56/56 Worker Harness evidence files exact;
- Worker Harness registry generation 4;
- active attachments 0;
- all registry entries remain rolled back;
- `executes_on_startup=false` and `grants_permissions=false` for every entry;
- launcher exact at
  `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`;
- permissions, projects, review state, startup behavior, private archives, and
  unrelated Workshop state unchanged;
- payload 22/22 exact;
- ports 8787, 8875, 8797, and 8798 closed.

No source deletion, network worker, AI model, arbitrary worker, unrestricted
shell, plugin installation, automatic import, attachment, activation, or
module promotion occurred.

## Whole-tree and generated-artifact accounting

Before this declared final report, the complete active tree contained exactly
282 files: the 271-file Release 0.7 baseline plus 11 Release 0.8 additions.
All 11 replacements matched candidate hashes. The only baseline file allowed
to change outside payload was `data/workshop.sqlite3`, whose governed schema
and receipts are documented above.

The full regression and active companion generated Python bytecode during
verification. Whole-tree audits detected and removed exactly those runtime
cache files. Existing historical baseline caches remain byte-identical and
outside payload authority. No Release 0.8 cache, bytecode, browser artifact,
screenshot, log, temporary database, test output, or imported test source
remains in the active Workshop.

With this one declared postdeployment report, final live inventory is 283
accounted files.

## Rollback and recovery

Rollback root:
`C:\TWIS_FLASHRIVER_REVIEW_READY\foundation-0.8-rollback`  
Rollback manifest:
`C:\TWIS_FLASHRIVER_REVIEW_READY\foundation-0.8-rollback\ROLLBACK_MANIFEST.json`  
Rollback manifest SHA-256:
`B9DB48A3C6354696D591AF91E2FB8747375AFA97939B19958C512574A69EA9DC`

Package verification proved:

- 14/14 declared package members including the manifest exact;
- 11/11 authenticated Release 0.7 originals exact;
- 11 additions each bound to exact-hash removal;
- 0 rollback removals;
- pre-release emergency SQLite copy exact at
  `2FC40F0DBDC770C4C2465385369D0C8C909A00207229ACEE2DEC65EFC60E2A48`;
- emergency copy integrity `ok`, `user_version=7`;
- database rollback deliberately not automatic, preventing overwrite of
  post-release owner work.

Two disposable rollback simulations passed:

1. Before deployment, the package applied all 22 files to an exact baseline,
   restored 11 originals, removed 11 additions only after candidate-hash
   checks, and returned to all 271 exact Release 0.7 files.
2. After the live lifecycles, normal rollback started from all 282 deployed
   files, restored 11 originals, removed 11 additions, matched every
   authenticated Release 0.7 code/protected file, and preserved the current
   909,312-byte SQLite database exactly.

The live Release 0.8 installation was not rolled back and remains 22/22 exact.

Post-live rollback simulation:
`C:\TWIS_FLASHRIVER_REVIEW_READY\.v08work-20260726\release-0.8-postlive-rollback-simulation.json`  
SHA-256:
`79384872FB6B63B94E60D6C7519BEE897D86FCEC70A7E23D87E2E4A46020F293`

## Major evidence hashes

- Release 0.7 deployed report:
  `46357E7110FAF01F2F8AEA7AC6DF0EB40F8F5009F134313C1E2A7E4F9FCD2B67`
- Release 0.8 candidate manifest:
  `357FDE317E579B4E8A0DBC2D24F82E2C5EFFED9FDDA9E721BC6EBDD02D36A8BF`
- Release 0.8 candidate report:
  `32DD206A26A8632337B82B04DF0F18BF575B9632DD1B5FE6D5F2A067DBFD756B`
- Release 0.8 Artifact Compass:
  `6B2222D8BD782133D0983462BE24D101CB4226A5131384FE93F6A2CBB98831DD`
- Release 0.8 rollback manifest:
  `B9DB48A3C6354696D591AF91E2FB8747375AFA97939B19958C512574A69EA9DC`
- Deployment receipt:
  `D40B284AA2C63177B4AA2ED3A8FCDD6C8831CD8BD63F8D3270C0676BF36267F3`
- Browser evidence:
  `5D0DD0773EA1F52F8699DEC3C47F3BC6B0E1FDCB18E1EEF39B8A9D4D85EA0B30`
- Live lifecycle evidence:
  `75ED2ABCF29878D17F4A0273883B92CDEEBF9F3B9785CA22D470208F6D655402`
- Final safety audit:
  `91711080849D40C7BAE29E3E6E758D40F264612371F420DD3D3F934F6FD915BE`
- Post-live rollback simulation:
  `79384872FB6B63B94E60D6C7519BEE897D86FCEC70A7E23D87E2E4A46020F293`
- Final active SQLite:
  `EE9B63B8AF1CBCC5AE6D3250B32B0E2887F8B8BB82D4E9FE1C478B30523423FD`
- Launcher:
  `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`

## Deliberate remaining limits

Release 0.8 deliberately does not include a complete Tool Registry interface,
universal prompt or handoff building, folder salvage, module promotion,
external provider/model routing, local-model installation, cloud workers,
unrestricted folder scanning, natural-language universal routing, creative
generation workers, or autonomous multi-agent crews.

These are scope boundaries, not incomplete Release 0.8 checks.

## Owner handoff

Engineering proof is complete. The single owner action is:

**Return the complete Release 0.8 output for preparation of the next direct-successor build.**
