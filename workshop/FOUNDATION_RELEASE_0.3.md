# Twis Holo Foundation Release 0.3

## Status

Release 0.3 code is deployed and verified in the existing folder:

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

Launcher, unchanged:

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS\start-workshop.bat`

Release date: 2026-07-16.

Result: **PASS / VERIFIED for code, isolated execution, persistence, activation-registry, recovery, and regression tests.** The production browser walkthrough remains **implemented but not owner-validated** because approval and activation must be deliberate owner actions.

The folder is not a Git checkout. No Git history was available, no repository was initialized, and nothing was published.

## Scope delivered

- Worker Harness v0.1 for exactly one fixed harmless worker.
- Deterministic reference metadata worker using a public fixture.
- Serializable exact execution-plan preview.
- Candidate lifecycle with constrained transitions.
- Hash- and generation-bound approve/reject gate.
- Separate registry-only activation action.
- Hash-verified bounded rollback.
- Transaction manifests, recovery snapshots, and hash-linked receipts.
- Artifact Compass records for the complete safe evidence flow.
- Local API and minimal Modules-room interface.
- Unit, adversarial, lifecycle, API, UI, schema, E2E, recovery, and regression tests.

No FlashRiver data was used as worker input. No live database schema or row was added. No archive, private document, launcher, or artifact was changed.

## Architecture change

Release 0.2 components are connected without replacing them:

1. `worker_cards.py` validates the exact Worker Card contract.
2. `path_policy.py` canonicalizes and enforces fixed read/write/blocked roots in both parent and child.
3. `transactions.py` records the execution/promotion actions, recovery snapshot, before/after hashes, and hash-linked receipts.
4. `reference_worker.py` performs one deterministic metadata operation.
5. `worker_harness.py` binds validation, planning, bounded execution, effect checks, tests, candidate creation, promotion, rollback, and provenance.
6. `promotion.py` enforces lifecycle transitions, immutable candidate material, approval binding, atomic registry updates, and registry interruption detection.
7. `artifact_compass.py` remains a separate derived SQLite/FTS5 index. The harness supplies safe evidence metadata only.
8. `server.py` exposes the bounded workflow without adding Workshop SQLite tables.
9. The existing Modules room renders plans, candidates, tests, hashes, decisions, activation, and rollback controls.

Prototype evidence is created only after an explicit plan under:

`data\worker_harness\`

At final verification that directory was still absent in the live folder. All automated harness use occurred in temporary isolated runtimes.

## Worker Harness design

The only supported worker is:

- ID: `reference-metadata-worker`
- Version: `0.1.0`
- Entry point: `companion.foundation.reference_worker`
- Input: one public `.txt` or `.md` fixture, maximum 256 KiB
- Output: one deterministic JSON file, maximum 32 KiB
- Result fields: input filename/SHA-256, byte count, line count, word count, and bounded Markdown headings
- Timeout: 5 seconds
- Captured stdout/stderr: 16 KiB per stream, with total-byte/truncation evidence
- Declared test: fixed internal `reference-output-v0.1`
- Network: unsupported
- Shell: unsupported; host uses a fixed argument array with `shell=False`
- Destructive actions: unsupported
- Automatic activation: prohibited

The parent writes an atomic request file and supplies its SHA-256 to the child. The child hashes the bytes it parses, closing the request-file substitution gap. The child environment is a small allowlist and excludes credentials, proxy variables, user-site packages, and inherited `PYTHONPATH` content.

## Enforcement matrix

| Control | Application-enforced | Host-enforced | Honest limit |
|---|---|---|---|
| Worker identity/version | Exact fixed values | Fixed `-m companion.foundation.reference_worker` argv | No arbitrary worker loading |
| Worker Card compatibility | Closed validator and exact expected-card hash | None | Cards generally remain declarations |
| Read/write/blocked roots | Parent and child `WindowsPathPolicy`; planned canonical roots rechecked | Filesystem canonical resolution | Not an OS ACL sandbox |
| Junction/root substitution | Canonical anchors captured and rechecked before any initialization write | Windows path resolution | Protects cooperating fixed workflow, not hostile native code |
| Input/request integrity | Plan input SHA and child request SHA | Child parses the verified request bytes | Local same-user processes remain in the machine trust boundary |
| Shell | Unsupported permission rejected | Fixed argv and `shell=False` | No unrestricted shell path exists |
| Network | Card must be false; fixed worker contains no network client | Proxy/credential environment removed | No OS firewall or network namespace is claimed |
| Timeout | Fixed card/plan value | Parent terminate/kill deadline | Windows startup latency required a five-second bound |
| Captured output | Receipt keeps summary only | Concurrent bounded readers | Capture contents remain in local candidate/failure evidence only |
| File effects | Before/after inventory permits only one output | Filesystem hashes | Scope is the bounded harness input/output workspace |
| Output and tests | Size/schema/identity checks and one internal allowlisted test | None | No shell-supplied test command |
| Approval | Exact candidate hash, generation, decision, actor assertion, note, timestamp | None | Actor assertion is not authenticated identity |
| Activation | Approved-state revalidation and atomic registry | Atomic same-volume replacement | Registry only; no startup execution or permission grant |
| Rollback | Current/snapshot/restored hashes and exact lifecycle | Bounded file restoration | One output plus registry status, not complete rollback |
| Receipts | Hash-linked chain verification | Atomic files | Not signed or immutable |
| Cross-site browser action | JSON-only, 16 KiB request limit, cross-site Fetch Metadata denial | Browser preflight behavior | Loopback service has no authenticated user session |

## Execution-plan contract

The preview contains worker identity/version/status/purpose, initiating actor, input/output paths and hashes, canonical read/write/blocked roots, requested permissions, application/host/unsupported enforcement labels, fixed callable/argv template, timeout and byte limits, exact expected file effects, fixed required test, recovery plan, Worker Card hash, workspace generation, plan hash, and `auto_activate: false`.

Execution revalidates the stored plan. UI display is not treated as enforcement.

Schema: `schemas\execution-plan-v0.3.schema.json`.

## Lifecycle state machine

```text
draft
  -> validated
  -> execution_planned
  -> executed
  -> tests_passed
  -> candidate
  -> awaiting_approval
      -> approved -> active -> rolled_back | revoked
      -> rejected

pre-activation states may fail closed where defined
```

Invalid transitions are rejected. Tests passing can create only `awaiting_approval`; they cannot create `active`.

Candidate identity hashes the candidate/worker/version IDs, Worker Card hash, plan ID/hash, execution transaction ID, recovery descriptor hash, output hash, test-evidence hash, and workspace generation.

Schema: `schemas\promotion-candidate-v0.3.schema.json`.

## Local API additions

- `GET /api/workers`
- `POST /api/workers/validate`
- `POST /api/workers/reference-metadata-worker/plan`
- `POST /api/workers/reference-metadata-worker/run`
- `GET /api/candidates`
- `GET /api/candidates/{candidate-id}`
- `POST /api/candidates/{candidate-id}/approve`
- `POST /api/candidates/{candidate-id}/reject`
- `POST /api/candidates/{candidate-id}/activate`
- `POST /api/candidates/{candidate-id}/rollback`

The production run route accepts only `planId` and `actor`. Test fault injection is disabled in the server-created harness and is not exposed by the UI/API.

## UI additions

The existing Modules room now includes:

- fixed Worker Card validation;
- unauthenticated local actor assertion label;
- exact execution-plan preview;
- separate Plan and Run actions;
- candidate/card/plan/output hashes and workspace generation;
- deterministic output summary and test results;
- receipt/recovery summary;
- optional approval note;
- separate Approve, Reject, Activate, and Roll Back actions; and
- explicit language that registry activation does not execute on startup or grant permissions.

The service-worker cache is versioned to `twis-holo-full-v3`. All `/api/` responses remain excluded from service-worker caching.

## Transaction, receipt, and Artifact Compass flow

```text
Worker Card
  -> execution plan
  -> execution transaction manifest
  -> bounded pre-run snapshot
  -> fixed worker request and output
  -> declared test evidence
  -> committed execution receipt
  -> candidate awaiting approval
  -> approval/rejection transaction and decision
  -> optional activation transaction and registry record
  -> optional rollback transaction and rollback record
```

Artifact Compass registers Worker Card, plan, transaction manifest, receipt, test result, candidate output, candidate record, approval decision, activation record, and rollback record. Candidate/transaction IDs provide provenance links. It does not index private archives, worker input contents, raw captured streams, approval-note text, or unrestricted command output.

Approval notes remain local in decision/candidate records. Receipts store only the note SHA-256 and `note_stored_in_receipt: false`.

## Failure and rollback proof

Temporary tests prove:

- invalid cards and unsupported network/shell/destructive permissions reject;
- path traversal, blocked roots, malicious output names, alternate data streams, and junction substitution reject;
- modified cards/plans/inputs/candidates/tests/receipts/recovery evidence reject;
- worker timeout, worker exception, process-launch error, malformed JSON, invalid/oversized output, declared-test failure, unexpected file creation, and oversized capture fail closed as designed;
- run failures restore the exact pre-run output and remove unexpected output;
- process-launch failures write a terminal failed receipt and leave the receipt chain valid;
- stale generations, incorrect hashes, replayed approvals, rejected candidates, and duplicate activation reject;
- an interrupted activation-registry replacement leaves `.pending`, does not activate the candidate, and blocks later registry use for review;
- interrupted transaction manifests are detected after a new manager instance starts;
- owner-selected rollback verifies current output, snapshot, and restored hashes, restores the one-file pre-run state, marks the registry entry rolled back, and increments generation.

The deterministic initial output used by the isolated harness has SHA-256:

`F99572B0FA29FB17CE2E9D67F66B1A7816D8D60092BD352A3334537C764215D1`

No claim is made beyond the bounded output file and activation-registry status.

## Final test results

Final deployed-folder results:

| Check | Result |
|---|---|
| Full Python suite | PASS — 96 passed in 114.34 s |
| JavaScript navigation suite | PASS — 3 passed, 0 failed |
| JavaScript syntax | PASS — 5 files |
| Python compile-all | PASS |
| Smoke test | PASS |
| Existing API E2E | PASS — isolated temporary data |
| Worker Harness API E2E | PASS — included in the 96-test deployed suite; separate candidate run 2 passed in 15.42 s |
| Candidate-to-live manifest | PASS — 28 files, 0 SHA-256 mismatches |
| SQLite immutable integrity | PASS — `integrity_check=ok` |
| Protected hashes | PASS — 9/9 unchanged |
| Live worker prototype state | PASS — `data\worker_harness\` absent after automated verification |

The full candidate suite also passed 96 tests in 121.74 s before deployment.

Development-time failures were resolved and are not hidden:

- The first adversarial run found a real preflight-ordering defect: output-root substitution could receive an initialization write before rejection. Canonical anchor verification now occurs before every initialization write, and the junction test passes.
- An invalid-card test expected a field-specific denial but received only a generic validation failure. Validation now retains both schema and authority-denial reasons.
- A long pytest temp path caused 13 Windows `FileNotFoundError` failures. Final tests use a short isolated temp root.
- A two-second process deadline produced three Windows startup/antivirus false timeouts. The enforced bound is now five seconds; the deliberate timeout test exceeds it and passes.
- One UI static assertion expected literal URLs even though action URLs are constructed from a closed action set. The test now verifies that closed set and route template.
- The first redirected compile-all cache path exceeded Windows path length. Compile-all passed with a short external cache root.

No final check failed.

## Live SQLite verification

Opened using SQLite URI `mode=ro&immutable=1`:

| Check/table | Value |
|---|---:|
| `PRAGMA integrity_check` | `ok` |
| projects | 2 |
| artifacts | 59 |
| artifact_search | 59 |
| artifact_reviews | 2 |
| receipts | 12 |
| sessions | 0 |
| modules | 0 |
| jobs | 0 |

The existing `modules` table remains unchanged with columns `id`, `enabled`, and `settings`. Release 0.3 adds no Workshop SQLite table or worker row.

## Protected-hash comparison

| Protected path | Bytes | Before/after SHA-256 |
|---|---:|---|
| `FLASHRIVER.zip` | 7,363,639 | `6EF7317722202769B08D74A434519871736E055D1864FA5EB6C6FB547CB40108` |
| `data\source_archives\flashriver\6ef7317722202769\FLASHRIVER.zip` | 7,363,639 | `6EF7317722202769B08D74A434519871736E055D1864FA5EB6C6FB547CB40108` |
| `data\workshop.sqlite3` | 745,472 | `4DC0249DEBF32C70CF9C3FB8BF56E9E8FA92E88B66B69B61522E5A7FC49D5863` |
| `FLASHRIVER_RECEIPT.json` | 2,905 | `8FE1FF272E4196D43B5012B6057E48103B8488167E65AF258AB39075A62BDA69` |
| `...\CERT_RIVER_PHASE708_HANDOFF_FOLDER.zip` | 4,427 | `F284D63B665679B14869410B36CC07F64319B5FE21EFF0904D9C5B0EE26BA01F` |
| `...\CERT_RIVER_PHASE755_FULL_REPAIR_AND_DEBUG_CLOSE.zip` | 61,367 | `F85E92DA8F5F225B670D76074E62712BCAE32588DC14FF7A182054C071721F1C` |
| `...\FlashRiver_CERT-RIVER_phases709_to_754_T43_T44_T45_T46_MASTER_BUNDLE.zip` | 280,403 | `82D5EC34EA01674DDBC5B92DC7BD70B0130735DC6F2AFC31F1925AEABC5453D8` |
| `...\TWIS_TALKBOX_BUILD_FOLDER.zip` | 12,226 | `5B8F34A7F3252D6066436C1306F86FC1A4BFDCA7BB910EE36C29530286F0660D` |
| `data\source_archives\.gitkeep` | 0 | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` |

The private-archive prefix represented by `...` is:

`data\projects\flashriver-source-archive\sources\flashriver\6ef7317722202769\private_source_artifacts\source_artifacts\`

## Complete deployed-file manifest

| Change | Path | SHA-256 |
|---|---|---|
| changed | `app\assets\app.js` | `924403C7F9627E3E095F841D8B94D6FA9BB1048B3B7077EB0ADA59390A2269E8` |
| changed | `app\assets\style.css` | `BBC3CA94E4A18AA7CF79F494DC244DA80916754BD1420B1BE7C60E076A9D5749` |
| new | `app\assets\worker-harness.js` | `5A031D42B2A9D6153F95CDB13C2B1032DBB8DDBA922939ABFD14DA43FC121378` |
| changed | `app\index.html` | `65B3AD925758DF52F474E1BE85BB6B8CCE6DC56E6190AD7CAB7D727610E1457A` |
| changed | `app\service-worker.js` | `D9723417A418B6D26B5DE3449341453D297BC5126CE0CC52669D234D402B9152` |
| changed | `ARCHITECTURE.md` | `8074C97CF05AC37D07F90146937274BCCB6292A4ED98A61648CD53DAF40F6DFD` |
| changed | `companion\foundation\__init__.py` | `FB20E4AF5FD1AFFAD6A4075D35861CF15B209BE134052995CADBE66406B71403` |
| new | `companion\foundation\promotion.py` | `917F132C668A76FCE14CB5A11F58754FC247E2D6FC7892BBBB5FB1A7ECFC152D` |
| new | `companion\foundation\reference_worker.py` | `1A6DE93B6FEE84E1F2980BCA2741C104DF8B94D17A71F9B42085A0CA0B4C5A92` |
| new | `companion\foundation\worker_harness.py` | `467AA21BDF0D9F23B8D42DD47077FA744C6AF0E381F991293FDC70733FD38E24` |
| changed | `companion\server.py` | `1D2ABA6E83570D1A38A35E89BF1BCA3660C8044C768E55ACBC8773082CB7FDB9` |
| changed | `DECISIONS.md` | `C18D29F101AEB09435705D98270434A5B80E781580B15E52FE6D9791E091CB9F` |
| changed | `docs\WORKER_CARD_V0.1.md` | `261CDEDD12D7127971A807584B85BAE39204FB26A9F56628DFE70EB42C9B4F7E` |
| new | `docs\WORKER_HARNESS_V0.1.md` | `B0A81B614427E1CA475EFC81B8FC239D05E5A7D16426DD4F73A8365BB0687D5D` |
| new | `examples\worker_harness\reference-input.md` | `750E7B4D7CDFDEA3F06850D17BCD65A6C6B8A5F338DAACB875035EC78E8DCC72` |
| changed | `OPEN_QUESTIONS.md` | `DFD8C07E3EB96F7C6005BC0662BEB4A663600B368145AB1656CFAAE6CE39DF5B` |
| changed | `package.json` | `951557C68318D6A890466C64E7794FB53FA6C1D9FC168C1E0F9D6D0ED84D4C82` |
| changed | `PROJECT_STATE.md` | `C4C825F9CBE4325546E6105A7E00DFF49C99D7847365FC7717713D96F53A3D8D` |
| changed | `README.md` | `C1E910F9A9C306EE891348F94814FFBC6A8EA7E9202767E2888F9D520B6959C6` |
| new | `schemas\execution-plan-v0.3.schema.json` | `60A835204A992004A5F7C87B25ED96FAF10D55D41926CE0A68884849D8AD232E` |
| new | `schemas\promotion-candidate-v0.3.schema.json` | `F88F8E56DAD61EB0201449C15A7D83E2A2B00CBBDA59C7636FA8EC4CB2937C0C` |
| changed | `tests\e2e_api_test.py` | `08045D0F319CB18AB12E61DFC7F4BB33434705A7964A5EE67D113956F455086B` |
| new | `tests\test_guarded_promotion.py` | `85C4AFAF62E1635592B5D47BC9F1F48E815614A8C4BF05F24170E8EE207E9A14` |
| new | `tests\test_worker_harness.py` | `CE146A9B6B0E4183B5CD57549BF14A0437CCA228983797D2952069A3F600D7D0` |
| new | `tests\test_worker_harness_api_e2e.py` | `D4087A6BA1E9001C780DC422B427EBCDA3C5FA70EFC42B60E6103755BFC251DE` |
| new | `tests\test_worker_harness_schemas.py` | `58B8634F9A282144075B08314C577755F34BA71B28EEFF0FC7517DA25AA3A8DD` |
| new | `tests\test_worker_harness_security.py` | `F13791983D2E533F2FF237AAD509A95471CFED2472702F4F19A813E089F69E59` |
| new | `tests\test_worker_harness_ui.py` | `8E022572383C7FEE44A1A7BB7C1F992737CF955576CDC5FAC9732CF6E5ADA229` |

This report is an additional new delivery file. Its SHA-256 is recorded in the external handoff because a file cannot contain its own final hash.

## Capability labels

### Proven

- Exact fixed-worker/Card/plan/path/hash/generation checks.
- Deterministic bounded output and internal test.
- No automatic activation.
- Candidate tamper, stale generation, replay, duplicate activation, receipt tamper, and recovery tamper rejection.
- Bounded failure restoration and owner-selected rollback by hashes.
- Atomic registry pending-write detection.
- Safe Artifact Compass evidence chain in temporary workspaces.
- Existing FlashRiver Review/navigation/API regressions preserved.
- Protected files and live SQLite unchanged.

### Tested in isolation

- End-to-end HTTP plan, run, companion restart, approval-note persistence, activation, and rollback.
- Timeout/kill, worker/process failure, malformed/oversized outputs, unexpected files, and bounded capture.
- Activation-registry interruption and interrupted-transaction restart detection.
- Artifact Compass provenance generation and receipt-chain verification.

### Implemented but not owner-validated

- Visual Modules-room workflow in the deployed browser.
- Deliberate production creation of `data\worker_harness\`.
- Owner approval, registry activation, and rollback using the deployed UI.
- Browser service-worker v3 refresh behavior on the owner's normal launcher session.

### Declared only

- The actor string is a human assertion; identity is not authenticated.
- Worker Card intent outside the fixed harness remains declarative.
- Receipt actors are not cryptographically signed.

### Deferred

- Cross-process locks and multi-process registry ownership.
- Authenticated/signed approval identity and receipts.
- OS restricted tokens/job objects/containers for untrusted processes.
- Recovery tooling for automatically reconciling multi-file partial operations.
- Any proposal for a real worker after separate architecture and threat-model approval.

### Unsupported

- Arbitrary, generated, imported-Markdown, FlashRiver, self-modifying, or self-activating worker execution.
- Network workers, unrestricted shell, destructive workers, startup scheduling, or permission grants.
- Hostile-process isolation, complete sandboxing, complete rollback, or immutable receipts.
- TalkBox promotion, voice routing, autonomous repair, AI/model installation, vector search, publishing, or Cloudflare/private-source transfer.

## Manual owner validation

1. Double-click the unchanged `start-workshop.bat`.
2. Open `http://127.0.0.1:8787` and hard-refresh once so service-worker cache v3 is active.
3. Open **Modules** and confirm the Guarded Worker Harness panel shows one test worker and no candidates.
4. Select **Validate Worker Card** and confirm the denied/unsupported boundaries remain no network, no shell, no destructive actions, no arbitrary worker, and no hostile-process-isolation claim.
5. Select **Create execution plan**. Inspect exact roots, hashes, permissions, fixed callable, five-second timeout, limits, required test, recovery scope, generation, and `auto_activate: false`.
6. Select **Run planned worker**. Confirm the candidate is `awaiting_approval`, not active, and the deterministic output/test pass.
7. Add an optional local note and explicitly approve the exact candidate. Refresh Modules and confirm the note/status persist.
8. Select **Activate registry entry** and accept the confirmation. Confirm the state is active while the UI continues to say no startup execution and no permission grant.
9. Select **Verify and roll back** and accept the confirmation. Confirm `rolled_back` and restored-hash evidence.
10. Optionally inspect `data\worker_harness\provenance-inventory.json`, `activation-registry.json`, transaction manifests/receipts, and the derived Artifact Compass database. Do not delete this evidence as part of validation.

This walkthrough intentionally creates local prototype evidence. It never reads or writes FlashRiver archives or Workshop SQLite.

## Rollback location

Code-only pre-0.3 originals and the exact list of new files are stored at:

`C:\Users\Olli_Twis\Documents\Codex\2026-07-16\inspect-this-existing-repository-first-and\outputs\foundation-0.3-rollback\`

The rollback package contains no database, archive, project artifact, receipt, or private source. It does not automatically delete `data\worker_harness\`; any local evidence created by the owner remains owner-controlled.

## Recommended next release

After the owner completes the manual walkthrough, the single best next release is a small 0.3.1 hardening pass for cross-process locking and partial multi-file operation audit/reconciliation. Do not add a real or generated worker until that foundation has its own threat review and explicit architecture approval.

