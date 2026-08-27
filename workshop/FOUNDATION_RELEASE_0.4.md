# Twis Holo Foundation Release 0.4

## Status

Release 0.4 is **DEPLOYED / GUARDED HASH-DOMAIN REPAIR PASS / OWNER
WALKTHROUGH PENDING**.

Deployment date: 2026-07-21.

The verified candidate is at:

`C:\Users\Olli_Twis\Documents\Codex\2026-07-21\files-mentioned-by-the-user-twis\work\foundation-0.4-candidate\TWIS`

The deployed runnable location is:

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

The launcher remains unchanged:

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS\start-workshop.bat`

After explicit owner approval, exactly 30 original manifest paths were
deployed: 20 existing code/document/test files were replaced and 10 files were
added.  The immediate and post-test candidate-to-live comparisons were 30/30
with zero mismatches.

The first owner walkthrough then exposed a live-data eligibility failure: the
importer had stored raw ZIP-member hashes while Windows materialization had
written deterministic CRLF text bytes.  The owner explicitly approved a narrow
hash-domain repair.  That repair changed only `companion\flashriver_intake.py`,
two tests, exactly 51 public-document artifact rows, one new repair receipt,
this report, and normal SQLite sidecars with a zero-byte WAL.  It did not rewrite any
extracted document.  The launcher, FlashRiver packages and receipt, private
archives, visuals, project paths, reviews, schema, worker candidates, and
activation state remain unchanged.  No live worker evidence was created.
Release 0.4 must not be described as fully owner-accepted until the repeated
manual browser walkthrough passes.

The folder is not a Git checkout.  No repository was initialized and nothing
was published.

## Evidence and authority classification

Artifact Compass inspection widened from the requested surface through the
repository, history availability, tooling, and product fit:

- **Canonical/current:** current live code and tests, Release 0.2 and 0.3
  reports, current documentation, immutable Workshop SQLite state, imported
  artifact records, source files, and protected hashes.
- **Active supporting:** the existing Worker Card, path policy, transaction,
  receipt, candidate, activation-registry, rollback, and Artifact Compass
  components.
- **Historical/reference:** the fixed Release 0.3 reference worker and its
  public fixture.  They remain intact as regression evidence, not the new
  production inspection input.
- **Missing:** Git history, because the supplied folder has no `.git` directory.
- **Unverified:** only the owner-driven browser flow and deliberate production
  approval/attachment/rollback actions.

The live inventory contains 59 artifact records.  Fifty current public-safe
`.md`, `.json`, or `.txt` files below imported `docs` roots meet the Release 0.4
selection shape.  The CSV manifest, four private archives, three visual files,
and files outside the public `docs` roots are ineligible.

## Guarded hash-domain repair

The repair establishes two explicit hash domains:

- `artifacts.sha256` and provenance `materializedSha256` are the SHA-256 of the
  exact extracted file bytes used by inspection eligibility.
- provenance `archiveMemberSha256` is the SHA-256 of the raw ZIP member bytes.

Before the database transaction, the root and archived package both matched
`6EF7317722202769B08D74A434519871736E055D1864FA5EB6C6FB547CB40108`.
All 51 artifact-to-member/path/UUID mappings were one-to-one; every old stored
hash exactly matched its raw member; and every current file exactly matched the
deterministic Windows importer output.  A byte-exact 745,472-byte database
backup matched the original
`4DC0249DEBF32C70CF9C3FB8BF56E9E8FA92E88B66B69B61522E5A7FC49D5863`
hash, `integrity_check=ok`, schema fingerprint, user version, and table counts.

One `BEGIN IMMEDIATE` transaction updated exactly 51 rows with guarded
old-hash/old-payload predicates and inserted exactly one complete receipt.  A
mismatch would have rolled back the whole transaction.  The committed receipt
is `a3b4822a-52db-4233-a9ac-b59f538c78b2`, action
`flashriver.public-document-hash-domain.repair`; it contains every artifact ID,
artifact path, ZIP member, old hash, new hash, raw-member hash, and materialized
hash.  No existing receipt changed.

## Scope delivered in the candidate

- One fixed `artifact-compass-inspection-worker` Worker Card.
- Explicit public-safe artifact selection with visible block reasons.
- Deterministic standard-library text inspection; no model, network, imported
  code execution, HTML rendering, or Markdown instruction execution.
- Exact, hash-bound execution-plan preview.
- Canonical structured JSON candidate output.
- Existing candidate approval/rejection, activation registry, transaction,
  receipts, rollback, and Artifact Compass evidence reused and extended.
- Activation semantics limited to attaching an approved report descriptor to
  the selected artifact.
- Minimal owner controls in the existing Modules room.
- Regression, adversarial, schema, API, lifecycle, rollback, receipt-chain, UI,
  navigation, smoke, and E2E tests.

## Architecture changes

1. `artifact_inspection_worker.py` implements the one fixed deterministic
   inspector.  It hashes before and after reading, treats all input as inert
   bytes/text, emits canonical JSON, and writes only one bounded output.
2. `worker_harness.py` retains the Release 0.3 reference worker and dispatches
   the inspection worker only when approved public roots exist.  It binds the
   artifact, card, plan, source hash, transaction, test evidence, candidate,
   decision, attachment, receipts, and rollback.
3. `promotion.py` includes the selected artifact ID/hash in inspection candidate
   identity, records an artifact-attachment descriptor in the existing registry,
   and uses short atomic temporary names for Windows path safety.
4. `server.py` discovers only imported public `docs` roots, resolves artifact
   records through SQLite opened read-only for selection, rejects structural
   private/out-of-root cases before reading content, exposes inspection options
   and attachments, and accepts only closed request fields.
5. The existing Modules room gains an explicit artifact selector, ineligibility
   reasons, exact plan display, structured report display, approval bindings,
   attach, provenance, and rollback controls.
6. The Workshop database schema is unchanged.  Harness/attachment evidence
   remains file-backed under `data\worker_harness\` only after an explicit plan
   or action.

## Worker Card

| Field | Value |
|---|---|
| Worker ID | `artifact-compass-inspection-worker` |
| Version | `0.4.0` |
| Lifecycle | `active` card; output still requires approval |
| Input | exactly one explicitly selected public-safe text artifact |
| Extensions | `.txt`, `.md`, `.json`, `.py`, `.js`, `.html`, `.css` |
| Maximum input | 524,288 bytes |
| Output | one `application/json` candidate |
| Maximum output | 131,072 bytes |
| Maximum items per extracted field | 256 |
| Timeout | 5 seconds |
| Captured stdout/stderr | 16,384 bytes per bounded stream |
| Network | denied |
| Shell permission | denied; host uses only a fixed argv with `shell=False` |
| Destructive actions | denied |
| Approval | required |
| Receipt | required |
| Test | `artifact-inspection-output-v0.4` |

Allowed read roots are the canonical imported `docs` directories supplied by
the server.  The database, `data\imports`, `data\backups`,
`data\source_archives`, root FlashRiver ZIP/receipt, private-source roots, and
visual-source roots are blocked.  The only write root is the inspection
candidate workspace.

## Enforcement matrix

| Control | Application-enforced | Host-enforced | Honest limit |
|---|---|---|---|
| Worker identity/card | Exact fixed ID, version, permissions, test, implementation hash, and card hash | Fixed Python module argv | No arbitrary worker loading |
| Artifact selection | SQLite artifact ID plus canonical public-root membership, supported suffix, size, encoding, binary, and current hash checks | Filesystem resolution and reparse-point checks | Public-safe classification depends on the current imported-root layout |
| Private roots | Structural private/out-of-root cases reject before content read | Canonical path containment | Not an OS ACL boundary |
| Source immutability | Plan hash plus parent and child pre/post source hashes | Read-only worker behavior | Same-user hostile processes remain in the host trust boundary |
| Imported content | Regex/text parsing only; code is never imported and markup is never rendered | Fixed child module has no evaluation path | Not a general hostile-code sandbox |
| Network | Card/plan must be false; fixed worker uses no network client | Scrubbed child environment | No OS firewall or network namespace is claimed |
| Shell | Unsupported permission rejects | Fixed argv and `shell=False` | The proven harness still launches its one fixed Python module |
| Time and bytes | Exact card/plan limits and bounded extraction arrays | Process deadline and concurrent bounded stream readers | Windows process startup occurs inside the five-second bound |
| File effects | Before/after inventory permits only the one planned JSON output | Filesystem hashes and recovery snapshot | Bounded workspace, not whole-machine monitoring |
| Output/tests | Canonical JSON is recomputed by the parent and schema/identity/hash tests must pass | Output byte ceiling | Heuristic purpose is explicitly not fact |
| Approval | Candidate/source/card/plan hashes, generation, actor assertion, note, and timestamp must match | None | Actor assertion is local and unauthenticated |
| Attachment | Approved candidate revalidated; registry stores artifact/report/hash descriptor | Atomic same-volume replacement | Attachment grants no permissions and does not alter review status |
| Receipts/provenance | Hash-linked transaction receipts and evidence records | Atomic files | Receipts are not signed or immutable |
| Rollback | Current output, recovery snapshot, restored hash, registry state, and chain are verified | One bounded file restoration | Does not silently delete owner-created harness evidence |

## Execution-plan contract

The preview visibly includes worker identity/version, selected artifact and ID,
canonical source path and hash, MIME-like file type, requested read root,
candidate write root, blocked roots, network/shell/destructive flags, timeout,
input/output/capture limits, exact output, required test, recovery scope, Worker
Card path/hash, current workspace generation, `auto_activate: false`, and the
plan hash.

Run revalidates every stored value.  A missing, changed, ambiguous, out-of-root,
private, reparse-substituted, unsupported, oversized, binary, invalid-UTF-8, or
hash-stale source fails closed.

Schema: `schemas\execution-plan-v0.4.schema.json`.

## Inspection-output schema

Canonical JSON includes:

- schema version, artifact ID, canonical source path, source SHA-256, and type;
- byte, line, and word counts;
- bounded headings, code symbols/declarations, links/references, and TODO/FIXME
  markers;
- deterministic likely-purpose classification with
  `classification: heuristic_not_fact` and the exact matching rule;
- duplicate-hash group, provenance references, review status, warnings;
- plan-supplied inspection timestamp and inspector version.

Warnings label prompt-like text and active markup without following or
executing it.  The parent recomputes the expected document from the same source
bytes and requires exact equality.

Schema: `schemas\artifact-inspection-output-v0.4.schema.json`.

## Lifecycle and approval binding

```text
explicit artifact selection
  -> exact plan
  -> executed
  -> tests_passed
  -> candidate
  -> awaiting_approval
      -> rejected
      -> approved
          -> explicit attach/activate
          -> active artifact report attachment
              -> explicit bounded rollback
              -> rolled_back
```

The candidate is not attached automatically.  Approval and later attachment
require the candidate ID and exact candidate hash, source artifact hash, Worker
Card hash, execution-plan hash, workspace generation, explicit local actor
assertion, approval note, and timezone-bearing timestamp.  Changes or replay
reject.  Approval and attachment remain separate actions.

Schema: `schemas\promotion-candidate-v0.4.schema.json`.

## API and UI additions

New/extended local API surface:

- `GET /api/artifacts/inspection-options`
- `GET /api/artifacts/{artifact-id}/inspections`
- `POST /api/workers/artifact-compass-inspection-worker/plan`
- `POST /api/workers/artifact-compass-inspection-worker/run`
- existing candidate `approve`, `reject`, `activate`, and `rollback` routes with
  the additional source/card/plan approval bindings

The UI lets the owner select one eligible artifact, see block reasons, validate
the fixed card, preview the full plan, run, inspect the candidate/evidence and
hashes, approve or reject, attach, verify provenance, and roll back.  It follows
the existing Modules-room layout.  Service-worker cache is versioned `v4` and
API responses remain uncached.

## Provenance chain and rollback proof

The file-backed chain is:

```text
source artifact ID/hash
  -> Worker Card/hash
  -> execution plan/hash
  -> execution transaction and recovery snapshot
  -> worker output/hash
  -> deterministic test evidence/hash
  -> candidate ID/hash
  -> approval decision and note hash
  -> activation registry artifact-attachment descriptor
  -> activation receipt
  -> optional rollback transaction/receipt
```

Isolated lifecycle tests prove a report can be attached after explicit approval,
remains associated after companion restart, and can be rolled back with exact
snapshot/current/restored hashes.  Tests also prove missing snapshots,
receipt-chain tampering, unexpected files, source/card/candidate changes, stale
generation, duplicate approval, replayed activation, and junction substitution
reject or fail closed as intended.

A code rollback package already preserves all 20 pre-0.4 files and lists the 10
new files.  It contains no database or project artifact and does not
automatically remove owner-created harness evidence.

## Exact staged and deployed test results

| Check | Result |
|---|---|
| Complete staged Python suite after repair | PASS - 117 passed in 151.08 s |
| Complete deployed Python suite after repair | PASS - 117 passed in 143.85 s |
| JavaScript navigation suite | PASS - 3 passed, 0 failed |
| JavaScript syntax | PASS - 8 repository JavaScript files |
| Python compile-all | PASS |
| Smoke test | PASS |
| Existing isolated API E2E | PASS - `Twis Holo API E2E PASS (isolated temporary data)` |
| Release 0.3 Worker Harness plus Release 0.4 inspection API E2E | PASS - 3 staged tests in 22.00 s and 3 deployed tests in 22.31 s |
| Approval/attachment/rollback/receipt tests | PASS - included in the 117-test suite and API E2E |
| Live inspection eligibility | PASS - 50 eligible, 9 blocked, 0 `source_hash_mismatch` |
| Immutable live SQLite integrity | PASS - `integrity=ok` |
| Protected hashes after repair and tests | PASS - 8/8 non-database hashes unchanged; database equals its authorized post-repair hash |
| Live worker prototype state | PASS - `data\worker_harness\` absent |
| Candidate-to-live manifest | PASS - 30/30 exact, zero mismatches immediately after deployment and after tests |
| Hash-domain repair candidate-to-live | PASS - importer and two tests 3/3 exact |
| Original deployment whole-live-tree test guard | PASS - 191 files before/after; 0 added, 0 removed, 0 changed |
| Deployed-folder test rerun | PASS - Python, JavaScript, compile-all, smoke, and isolated API gates |
| Manual browser walkthrough | PENDING owner action |

The test tree remained isolated from the live Workshop database and artifacts.
The final suite used a short explicit pytest temp root because the generated
task workspace itself is unusually deep on Windows.  During verification, the
first deep-path run found that atomic temporary names repeated the destination
basename; the helper now uses a short fixed prefix.  A concurrent local API
rerun also demonstrated that independent loopback E2E servers must not be
launched in parallel because ephemeral-port discovery is intentionally a test
helper, not a reservation.  The serial final API gates pass.

The first post-repair deployed-suite command also stopped before collection
because its new external `TEMP` path had not yet been created.  It ran zero
tests, changed no live data, and was an environment launch error rather than a
test failure.  After the isolated directory was explicitly created, the same
complete command passed all 117 deployed tests.

## Live SQLite verification after deployment and tests

Integrity, schema, counts, and live-vs-backup comparisons used URI
`mode=ro&immutable=1`.  The deployed eligibility helper used its normal
read-only SQLite connection.

| Check/table | Value |
|---|---:|
| `PRAGMA integrity_check` | `ok` |
| projects | 2 |
| artifacts | 59 |
| artifact_search | 59 |
| artifact_reviews | 2 |
| receipts | 13 |
| sessions | 0 |
| modules | 0 |
| jobs | 0 |

Release 0.4 adds no Workshop SQLite table or migration.  The guarded repair
changed `sha256` and the two approved provenance fields in exactly 51 existing
artifact rows and added exactly one receipt.  All other artifact columns, all
eight unaffected artifact rows, all old receipts, search rows, reviews,
projects, sessions, modules, and jobs are byte-for-byte/row-for-row identical to
the verified backup.

## Protected-hash comparison after deployment and tests

Eight non-database values match the captured baseline.  The database is the one
authorized protected change and matches the exact post-repair value below.

| Protected path | Bytes | Baseline/current SHA-256 |
|---|---:|---|
| `FLASHRIVER.zip` | 7,363,639 | `6EF7317722202769B08D74A434519871736E055D1864FA5EB6C6FB547CB40108` |
| `data\source_archives\flashriver\6ef7317722202769\FLASHRIVER.zip` | 7,363,639 | `6EF7317722202769B08D74A434519871736E055D1864FA5EB6C6FB547CB40108` |
| `data\workshop.sqlite3` | 745,472 | `8963DC86337E40606F493DD78792069113DF6B7B0B570CB64F8B247F173CCBC6` (authorized; pre-repair `4DC0249DEBF32C70CF9C3FB8BF56E9E8FA92E88B66B69B61522E5A7FC49D5863`) |
| `FLASHRIVER_RECEIPT.json` | 2,905 | `8FE1FF272E4196D43B5012B6057E48103B8488167E65AF258AB39075A62BDA69` |
| `...\CERT_RIVER_PHASE708_HANDOFF_FOLDER.zip` | 4,427 | `F284D63B665679B14869410B36CC07F64319B5FE21EFF0904D9C5B0EE26BA01F` |
| `...\CERT_RIVER_PHASE755_FULL_REPAIR_AND_DEBUG_CLOSE.zip` | 61,367 | `F85E92DA8F5F225B670D76074E62712BCAE32588DC14FF7A182054C071721F1C` |
| `...\FlashRiver_CERT-RIVER_phases709_to_754_T43_T44_T45_T46_MASTER_BUNDLE.zip` | 280,403 | `82D5EC34EA01674DDBC5B92DC7BD70B0130735DC6F2AFC31F1925AEABC5453D8` |
| `...\TWIS_TALKBOX_BUILD_FOLDER.zip` | 12,226 | `5B8F34A7F3252D6066436C1306F86FC1A4BFDCA7BB910EE36C29530286F0660D` |
| `data\source_archives\.gitkeep` | 0 | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` |

The private-archive `...` prefix is
`data\projects\flashriver-source-archive\sources\flashriver\6ef7317722202769\private_source_artifacts\source_artifacts\`.

## Guarded repair changed-file manifest

| Change | Path/data | Bytes | Final SHA-256/effect |
|---|---|---:|---|
| changed | `companion\flashriver_intake.py` | 11,469 | `0F07BFE8163435BF2F37EDBCFF0254279322444F2CA84CAC3FC73EE093787571` |
| changed | `tests\test_flashriver_intake.py` | 4,173 | `0761534E651AC5E1DF9E641803A9BDF44CA1F6189C7379CBA72F44BC36B5E897` |
| changed | `tests\test_artifact_inspection_selection.py` | 6,909 | `883D510BBAF5324FB0DD42394BF19F4B48187026789BA9680F798AF4A065A78B` |
| changed | `data\workshop.sqlite3` | 745,472 | `8963DC86337E40606F493DD78792069113DF6B7B0B570CB64F8B247F173CCBC6`; exactly 51 artifact rows plus one receipt |
| changed | `FOUNDATION_RELEASE_0.4.md` | external manifest | final report hash recorded outside the report |

No extracted document or other source artifact is in this changed-file list.

## Original deployed changed-file manifest

The original deployed scope was exactly 20 replacements plus 10 new files.  The
table below is the original deployment receipt; the later guarded repair scope
above supersedes the current hash for
`tests\test_artifact_inspection_selection.py` and this report.  A file cannot
contain its own final hash, so the report hash is recorded externally.

| Change | Path | Bytes | SHA-256 |
|---|---|---:|---|
| changed | `app\assets\style.css` | 16,758 | `7789E0BE6180FB040A2896E0A42D43DF3DC52307F184E5AE304A8AFA7D853222` |
| changed | `app\assets\worker-harness.js` | 13,870 | `3D39B12A5F4A990300AA3F93D0826CBE7880C396CF01E063D3ABE65CEF370F62` |
| changed | `app\index.html` | 16,365 | `CBFD8F0958AF82EA9CF22CF8A6F8AEFDDC3E1CA1668F5B2F12A4CBA012B9830D` |
| changed | `app\service-worker.js` | 1,327 | `10D6D344D71004D2AB01F5791AB34F93626462740138CDAE4E65397E91A71A4E` |
| changed | `ARCHITECTURE.md` | 5,474 | `3867D29EB304A59DBCA62F32080A0471A6D4B75BC81FED7D6EF2FC6375F9D0D7` |
| changed | `companion\foundation\__init__.py` | 1,240 | `CCD6321BC6EB46378D9D9CA7551ECF45DF5F11AE748FD1990CDD296E7CA283EB` |
| new | `companion\foundation\artifact_inspection_worker.py` | 16,462 | `489717E4B04726774EDBBDA8161A8EFA2C7520DD3E817C90B65F10EEB7F9E7E9` |
| changed | `companion\foundation\promotion.py` | 11,514 | `9096C1CD45A4633E560D2B973D923511B4CB4A992BAA06EA1D60D4FBBA3CA8FD` |
| changed | `companion\foundation\worker_harness.py` | 101,157 | `2729A2E9BF830E9D499F2C985BDF8D2E62235CA205AC667912F40120628A108B` |
| changed | `companion\server.py` | 45,833 | `ABD127053B336CA4595BB31FB3FAC2E524F1983D8A2952012C596CDF7DC98B28` |
| changed | `DECISIONS.md` | 3,597 | `974F064CF44D621FEFAFBE9D9CAE9A8C02EB85FE148AD29D8ECFB31C814F7226` |
| new | `docs\ARTIFACT_INSPECTION_WORKER_V0.4.md` | 2,360 | `BD0042969DDAA01CA26FAD2F721F13C7519F5E7B1150C708FFBA95AA411FDA84` |
| changed | `docs\WORKER_CARD_V0.1.md` | 2,087 | `4916920666B34486B6DD0CA9816FB03A747AD5452C12D3A746488629126ED4EE` |
| changed | `docs\WORKER_HARNESS_V0.1.md` | 4,101 | `12DCD8146A5B0F7DA17CE8B58B9808AB5FA39F1D75155BF2BFA0FBFC19EC0229` |
| changed | `OPEN_QUESTIONS.md` | 1,136 | `2F713AED1AB96C93DF85266CB7AB4A69145A6EB39E63E8D1B2607B4B75F0836E` |
| changed | `package.json` | 1,095 | `1482DE9017B3FB3BDCB1F96EC83E188B1CF1151BF8596524FA5009A18329F650` |
| changed | `PROJECT_STATE.md` | 4,029 | `09B596839E0460439ECCD442F686987FB7E4FCEE96CF65CBA0C3C2F51B2816DC` |
| changed | `README.md` | 2,619 | `E15CCDB1209BFD52AE9CF3283EFBCAF510CCA1CD4EA728B4D148A9FA3BCB6579` |
| new | `schemas\artifact-inspection-output-v0.4.schema.json` | 2,378 | `0F33D31338904893355A01CFB5D42F0964A76D6F010DB50FB72B411ECF91D5B0` |
| new | `schemas\execution-plan-v0.4.schema.json` | 3,996 | `DABAEFA39FCD2C80FBBD1DCFB623A78267F4FF8EB18EF6344C228AF9AA9BDC14` |
| new | `schemas\promotion-candidate-v0.4.schema.json` | 3,704 | `985AC844437F2ED38C8A6A0C6D1054CD6D854650044182FE0996974F087F443B` |
| changed | `tests\e2e_api_test.py` | 3,912 | `0CFF8679558A370D9AFEFF1DC6928437F1B6DEA869088496440E5E839D53C933` |
| new | `tests\test_artifact_inspection_api_e2e.py` | 8,897 | `86C5E298FBA5388B4826D3F6C3E10464E450F783143CF1F34B4BD06EA090413D` |
| new | `tests\test_artifact_inspection_harness.py` | 13,876 | `75F38F9315A3F7034038E9313C50C9A0D62997A7AEF7570986A31096E5A8F942` |
| new | `tests\test_artifact_inspection_selection.py` | 5,167 | `98B4F4F3A621DD567E4D24DD1D798040F76A26939169D4AA137A634C4B13CFBC` |
| new | `tests\test_artifact_inspection_worker.py` | 4,064 | `A1EB59C81CDB2DF0F8B3A7B5D6F0A704FC623A13CD101B53AAAFEC30C8C3DE97` |
| changed | `tests\test_worker_harness_api_e2e.py` | 8,424 | `184F8E41754180F9B6E8D8ED316020F093730FE7CA212D72B8AE4468E0D784A9` |
| changed | `tests\test_worker_harness_schemas.py` | 2,303 | `FA570913051CC753553BE6CBF64F29FEE22B04D1064037AB41B9C4C3E9F4AAD4` |
| changed | `tests\test_worker_harness_ui.py` | 2,770 | `2785DA88C8A47B3E55FBE29C1B5E5BE2844A964510050215D40A7AA5B7EF1396` |
| new | `FOUNDATION_RELEASE_0.4.md` | external manifest | external manifest |

## Acceptance status

| Criterion | Current evidence |
|---:|---|
| 1-13 | PASS in staged and deployed automated tests: regression, selection, rejection, visible authority, inert content, source immutability, deterministic JSON, no auto-attach, hash binding, stale/tamper rejection, attachment-only activation, full provenance, and rollback |
| 14 | PASS: 8/8 non-database protected files unchanged; database matches its authorized post-repair hash |
| 15 | PASS: tests used external temporary data; 51/51 source files and 66 launcher/imported files remained byte-identical |
| 16 | AUTOMATED PASS: original 30/30 deployment, repair 3/3 code/test comparison, 50 eligible artifacts, and every automated gate passed; repeated manual owner walkthrough remains before full owner acceptance |
| 17 | PASS: limitations and unsupported claims are explicit below |

## Capability labels

### Proven in the deployed implementation

- Fixed worker/card/plan/path/hash/generation enforcement.
- Explicit eligible artifact selection and visible rejection reasons.
- Deterministic, bounded, inert text inspection and canonical JSON.
- No automatic approval or attachment.
- Candidate/source/card/plan tamper, stale generation, replay, private/out-of-root,
  junction, malformed text, binary, oversize, unexpected-file, receipt-chain, and
  recovery-snapshot rejection.
- Exact attachment descriptor and bounded rollback behavior.
- Release 0.2/0.3 regression behavior and protected live data preserved.

### Tested only in isolation

- HTTP selection, plan, run, companion restart, approval, rejection, attachment,
  provenance lookup, receipt-chain verification, and rollback.
- Source changing during inspection and before decision.
- Candidate/card/plan/generation tampering and interrupted/failure paths.
- Malicious Markdown, HTML/script, code-looking text, and excessive extracted
  items remaining inert and bounded.

### Implemented but not owner-validated

- Browser rendering and controls in the deployed Modules room.
- Service-worker v4 refresh in the owner's normal launcher session.
- Deliberate creation of production `data\worker_harness\` evidence.
- Owner approval, attachment, provenance inspection, and rollback in the active
  folder.

### Declared only

- The local actor string is a human assertion, not authenticated identity.
- Worker Card intent outside the fixed harness remains declarative.
- Receipt actors and evidence are hash-linked but not cryptographically signed.

### Unsupported

- Arbitrary/generated workers, imported code or Markdown execution, network
  workers, unrestricted shell, destructive actions, startup execution,
  permission grants, hostile-process isolation, or complete sandboxing.
- AI/model installation, vector search, voice routing, autonomous repair,
  FlashRiver re-import, duplicate deletion, private-source transfer, database
  migration, launcher replacement, publication, or UI redesign.

## Exact owner-validation walkthrough after the repair

1. Before launch, confirm no other Workshop process is using port 8787.  The
   unchanged launcher must be 1,644 bytes with SHA-256
   `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`.
2. Double-click `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS\start-workshop.bat`, open
   `http://127.0.0.1:8787`, hard-refresh once for service-worker cache v4, and
   open **Modules**.
3. In **Guarded Worker Harness**, select
   `artifact-compass-inspection-worker`, then choose **Refresh artifact
   eligibility**.  Stop if the UI does not show exactly **50 eligible** and **9
   blocked**, or if any record reports `source_hash_mismatch`.
4. Confirm the remaining blocked evidence is structural: eight outside the
   public-safe roots, eight unsupported extensions, four private-source flags,
   and three oversize flags.  These reason counts overlap across the nine
   blocked records.
5. Select the root `AGENT.md` artifact ID
   `9217e4a7-7254-53a6-a75e-1d20e0754d86`.  Confirm the displayed canonical
   path ends in `...\6ef7317722202769\docs\AGENT.md` and its SHA-256 is
   `E4EFEDCAB226193F35EAE9E1CB6070102D7FD336B70A5C3205D33976D48BB38A`.
6. Validate the fixed Worker Card.  Confirm network, shell, destructive action,
   arbitrary worker, and automatic activation capabilities are denied.
7. Create the plan and inspect the exact artifact ID/path/hash, allowed and
   blocked roots, byte/time/output limits, required test, recovery scope,
   workspace generation, Worker Card hash, and `auto_activate: false`.  Do not
   run if any binding differs.
8. Run the plan deliberately.  Confirm the source pre/post hashes are identical,
   output is bounded structured JSON, heuristic purpose is labeled as not fact,
   candidate state is `awaiting_approval`, and no attachment/activation occurs.
9. Enter a local approval note and approve the exact candidate/source/card/plan/
   generation bindings.  Refresh the page and confirm the approved candidate
   persists but is still not attached.
10. Choose **Attach approved report** explicitly.  Confirm the artifact
    inspection endpoint exposes only the report descriptor and that the
    artifact source, review status, and review notes did not change.
11. Inspect provenance and the hash-linked receipt chain, then choose rollback.
    Confirm the attachment is marked rolled back and the bounded output recovery
    hashes match.  This is the Worker Harness report rollback, not the database
    hash-domain rollback below.
12. Close the Workshop.  Recheck SQLite `integrity_check=ok`; counts must be
    projects 2, artifacts 59, artifact_search 59, artifact_reviews 2, receipts
    13, sessions/modules/jobs 0.  Recheck the 9 protected hashes listed above.

Steps 8-11 intentionally create local file-backed `data\worker_harness`
evidence and exercise the one fixed worker.  Before owner validation, no live
worker ran or activated automatically.  The walkthrough does not inspect a
private archive or write Workshop SQLite.

## Repair rollback location and instructions

The byte-exact pre-repair database plus the four pre-repair files are stored at:

`C:\Users\Olli_Twis\Documents\Codex\2026-07-21\files-mentioned-by-the-user-twis\outputs\foundation-0.4-hash-domain-repair-rollback\`

The database backup is 745,472 bytes with SHA-256
`4DC0249DEBF32C70CF9C3FB8BF56E9E8FA92E88B66B69B61522E5A7FC49D5863`,
`integrity_check=ok`, the original schema fingerprint, and the original 12
receipts.  Rollback restores the three prior code/test files, the pre-repair
database, and the pre-repair report; it removes all 51 repairs and their one
receipt together.

Run the following in PowerShell only after closing the Workshop.  It fails
closed if port 8787 is active, the live database is not the expected repaired
database, the backup hash differs, or a non-empty WAL exists.

```powershell
$twisRoot = 'C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS'
$repairRollback = 'C:\Users\Olli_Twis\Documents\Codex\2026-07-21\files-mentioned-by-the-user-twis\outputs\foundation-0.4-hash-domain-repair-rollback'
$twisDb = Join-Path $twisRoot 'data\workshop.sqlite3'
$twisWal = $twisDb + '-wal'
$twisShm = $twisDb + '-shm'

if (Get-NetTCPConnection -LocalPort 8787 -State Listen -ErrorAction SilentlyContinue) {
    throw 'Stop the Workshop before rollback.'
}
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $twisDb).Hash -ne '8963DC86337E40606F493DD78792069113DF6B7B0B570CB64F8B247F173CCBC6') {
    throw 'Live database is not the verified repaired database.'
}
$backupDb = Join-Path $repairRollback 'workshop.sqlite3.pre-repair'
if ((Get-FileHash -Algorithm SHA256 -LiteralPath $backupDb).Hash -ne '4DC0249DEBF32C70CF9C3FB8BF56E9E8FA92E88B66B69B61522E5A7FC49D5863') {
    throw 'Pre-repair database backup hash mismatch.'
}
if ((Test-Path -LiteralPath $twisWal) -and (Get-Item -LiteralPath $twisWal).Length -ne 0) {
    throw 'Non-empty SQLite WAL detected; do not roll back until it is safely resolved.'
}

Remove-Item -LiteralPath $twisWal -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $twisShm -Force -ErrorAction SilentlyContinue
Copy-Item -LiteralPath (Join-Path $repairRollback 'companion\flashriver_intake.py') -Destination (Join-Path $twisRoot 'companion\flashriver_intake.py')
Copy-Item -LiteralPath (Join-Path $repairRollback 'tests\test_flashriver_intake.py') -Destination (Join-Path $twisRoot 'tests\test_flashriver_intake.py')
Copy-Item -LiteralPath (Join-Path $repairRollback 'tests\test_artifact_inspection_selection.py') -Destination (Join-Path $twisRoot 'tests\test_artifact_inspection_selection.py')
Copy-Item -LiteralPath (Join-Path $repairRollback 'FOUNDATION_RELEASE_0.4.md') -Destination (Join-Path $twisRoot 'FOUNDATION_RELEASE_0.4.md')
Copy-Item -LiteralPath $backupDb -Destination $twisDb

Get-FileHash -Algorithm SHA256 -LiteralPath $twisDb
```

The final printed database hash must be
`4DC0249DEBF32C70CF9C3FB8BF56E9E8FA92E88B66B69B61522E5A7FC49D5863`.
Then repeat immutable integrity/count checks before launching.  The separate
original Release 0.4 code rollback remains at
`...\outputs\foundation-0.4-rollback\`; do not combine the two rollback scopes.

## Recommended next release

After Release 0.4 is deployed and the owner walkthrough passes, make Release
0.4.1 a narrow hardening release for cross-process locking, registry ownership,
and consistent JSON error containment for unexpected server exceptions.  Do not
add another real worker until this first attachment lifecycle has production
owner evidence.
