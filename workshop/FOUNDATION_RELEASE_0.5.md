# Twis Holo Foundation Release 0.5

## Release status

**STAGED / COMPLETE AUTOMATED PASS / LIVE DEPLOYMENT NOT PERFORMED / EXPLICIT OWNER APPROVAL REQUIRED**

Candidate root:

`C:\Users\Olli_Twis\Documents\Codex\2026-07-21\files-mentioned-by-the-user-twis\work\foundation-0.5-candidate\TWIS`

Active Release 0.4 root:

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

Release 0.5 has not been copied into the active root. The launcher, Workshop
SQLite, FlashRiver packages, private archives, imported material, review data,
and owner-accepted Worker Harness state remain the exact Release 0.4 baseline.
The release is conditionally ready for deployment only after the owner approves
the exact external 16-file manifest.

## Objective

Release 0.5 turns Modules -> Guarded Worker Harness into an owner-facing control
panel whose labels and available actions are projections of real backend state.
It exposes explicit artifact identity, duplicate paths, eligibility totals,
validated Worker Card authority, execution-plan authority, candidate lifecycle,
approval bindings, inspection output, attachment state, provenance, receipts,
rollback evidence, and actionable errors. It does not add a new worker, model,
network path, shell path, activation path, database schema, or autonomous action.

The implementation keeps the existing visual language and changes only the
Modules control panel and its supporting view/controller code. It is not a full
Workshop redesign.

## Authority and lifecycle classification

The Artifact Compass pass classified the relevant material as follows:

| Class | Authority in this release |
|---|---|
| Active Release 0.4 code | Authoritative deployed baseline; read and hashed, not changed |
| Workshop SQLite and imported public/private source | Protected source/data authority; immutable-read verification only |
| Existing Worker Harness records | Owner-acceptance evidence; all 29 files frozen and preserved |
| Release 0.5 candidate | Staged implementation; not active until exact-manifest deployment is approved |
| Tests, browser fixture, report, manifest, rollback package | Verification and operational evidence; not product authority |

This classification prevented generated pytest/bytecode/browser data from
entering the candidate manifest and kept all lifecycle exercise in disposable
data roots.

## Frozen Release 0.4 baseline

Before implementation, the owner-accepted state was copied to:

`...\outputs\foundation-0.5-release-0.4-baseline-freeze\`

| Evidence | Bytes | SHA-256 / result |
|---|---:|---|
| Release 0.4 report | 33,588 | `0E19A4C6E2D6B5741BF1894032A28DAF5CC9C1B7B73291FC6593F953EABC7536` |
| Owner-accepted Workshop SQLite copy | 745,472 | `8963DC86337E40606F493DD78792069113DF6B7B0B570CB64F8B247F173CCBC6` |
| Complete baseline evidence JSON | 64,759 | `0AFF17EFC084C34ED1A57DE50EA1CBBA58368779821C0F5B83FD0171765F6209` |
| Owner-acceptance Worker Harness ZIP | 50,498 | `F25515CC14F1B7182648632458520367A523BC74B4F5CEA3DFE8BB33809B327C` |
| Frozen harness members | 29 | ZIP-to-live comparison exact |
| Release 0.4 rollback packages | 2 | copied and member-hash verified |

The final live recomputation produced the same 64,759-byte evidence JSON and
the same SHA-256, proving the complete captured baseline is unchanged, not just
the selected protected files.

Owner-acceptance harness state remains:

- registry generation: `2`
- candidate: `1104aee4006345339a91c6aa064b3a2c`
- artifact: `9217e4a7-7254-53a6-a75e-1d20e0754d86`
- lifecycle: `rolled_back`
- active attachments: `0`
- rolled-back attachments: `1`
- executes on startup: `false`
- grants permissions: `false`

## UI changes

### Artifact identity and eligibility

- Duplicate titles use `title - shortened path`, for example
  `AGENT.md - docs\AGENT.md` and
  `AGENT.md - docs\agent_files\AGENT.md`.
- The details view shows artifact ID, exact eligibility, file type, byte count,
  review status, SHA-256, and every record in the duplicate-byte group.
- Eligibility shows eligible, blocked, source-hash mismatch, blocked-reason
  categories, and the actual refresh time returned by the page session.
- Blocked artifacts are listed with their returned reasons and are never added
  to the executable selector.

### Worker Card and plan authority

- Validation renders worker/version, exact read/write roots, network, shell,
  destructive-action policy, approval requirement, automatic-activation
  policy, limits, card hash, and unsupported capabilities.
- The complete validated Worker Card remains available in an expandable raw
  technical view.
- The plan view projects selected artifact, source hash, read/write/blocked
  roots, permissions, timeout, byte limits, required tests, recovery scope,
  workspace generation, and automatic-activation state from the exact plan.
- The raw execution-plan JSON remains available.
- Execution is disabled when there is no plan or when worker, artifact, actor,
  automatic-activation policy, or workspace-generation selection no longer
  matches the current plan.
- Declared-only boundaries explicitly state that the actor assertion is not
  authenticated identity and network denial is not an OS network sandbox.

### Candidate, approval, attachment, evidence, and rollback

- The visible lifecycle is `planned -> running -> awaiting approval -> approved
  -> active -> rolled back`.
- Only the action valid for the returned backend lifecycle is shown.
- Inspection output is organized into source identity, counts, headings,
  symbols, links, TODO/FIXME findings, duplicate group, review status,
  provenance, warnings, and heuristic purpose.
- Heuristic classification is always labeled `Heuristic - not established
  fact`.
- Canonical inspection JSON remains available in an expandable technical view.
- Before approval, the UI shows candidate, source, Worker Card, plan, and output
  hashes; workspace generation; local actor assertion; and the required note.
- Approval, active attachment, and rolled-back attachment are distinct states.
- The attachment panel states that source bytes and review status do not change,
  no permissions are granted, and nothing executes at startup.
- Provenance and receipt entries connect artifact, card, plan, transaction,
  test, candidate, approval, attachment, rollback, and receipt paths/times.
- Hashes are described as byte hashes, not signatures. Receipts are described
  as evidence, not immutable records.
- Rollback shows the bounded target, recovery scope, current output hash,
  expected restored hash, verified restored hash, and unchanged-source result.
- Page-session action history and the status region visibly classify started,
  succeeded, failed, blocked, stale, and awaiting-owner outcomes.
- Imported text is escaped before HTML templates are rendered.

## Minimal backend changes

No endpoint, schema, worker, permission, or activation kind was added.

1. `WorkerHarness.validate_card()` now returns the same validated card object
   and its canonical `worker_card_hash` with the existing validation result.
   This gives the UI truthful card data instead of requiring duplicated claims.
2. `WorkerHarness.approve()` rejects a blank approval note with
   `approval_note_required`. This strengthens the owner gate on the server as
   well as in the browser.
3. Capability/package release labels changed from `0.4.0` to `0.5.0`.

All path containment, source-hash checks, card binding, plan binding, candidate
hash binding, workspace generation binding, receipt verification, attachment
guards, and rollback hash verification remain in their existing enforcement
paths.

## Lifecycle-to-action mapping

| State | Owner-visible truth | Valid action |
|---|---|---|
| no plan | no current authority | validate card or create plan; run disabled |
| planned | exact current plan is reviewable | run that plan only |
| running | deliberate fixed-worker request is in flight | no competing lifecycle action |
| awaiting approval | tests passed; candidate hashes and output are reviewable | approve with note or reject |
| approved | approved candidate is not attached | attach exact approved result |
| active | bounded report attachment is active | roll back attachment |
| rolled back | restored hash is verified and history retained | no further lifecycle action |

The backend remains authoritative. The UI derives action availability from the
returned state and does not manufacture intermediate records.

## Evidence views and real-browser lifecycle proof

The complete owner lifecycle was exercised against a disposable server/data
root copied from the candidate. No live path was used.

| Browser evidence | Result |
|---|---|
| Browser | Chrome for Testing headless shell `151.0.7922.10` |
| Duplicate fixture | two distinct `AGENT.md` paths with identical bytes |
| Eligibility | `2` eligible, `1` blocked, `0` source-hash mismatches |
| Block categories | `outside public safe roots: 1`; `private source: 1` |
| Worker Card | exact roots/policies/hash rendered; raw card retained |
| Plan | exact authority rendered; run enabled only for current plan |
| Stale-plan test | selecting the other duplicate disabled run and required a new plan |
| Candidate | `c13e7f064553476abb30342650bf5c44` reached awaiting approval |
| Blank approval note | visibly blocked as `approval_note_required` |
| Approval | exact candidate approved only after an explicit note |
| Attachment | explicit confirmation; state changed to active |
| Rollback | explicit confirmation; state changed to rolled back |
| Expected/restored hash | both `FDF9BF34124DC49F58362158DF9C6F1D22FF49AB3E7DCC3C8D4B24A09A1117A0` |
| Source before/after | both duplicate files remained `B3573F32DDFB1B4B1009CFF1337E975142489D0E6D5F5A9B0472C2F7D7164A5A` |
| Isolated SQLite | integrity `ok`; projects 1, artifacts 3, search 3, receipts 4, sessions/modules/jobs 0 |
| Browser console | 0 errors, 0 warnings |
| Automatic behavior | no automatic run, approval, attachment, activation, or rollback |

The browser screenshot after verified rollback is external evidence named
`FOUNDATION_RELEASE_0.5_UI_E2E_ROLLED_BACK.png`, 221,458 bytes, SHA-256
`9381BC509E6E65C5004C553851C63B7E4FEAFBCD4FFE7570C7CF779434F7762A`.

The only worker execution and attachment in Release 0.5 verification occurred
in that disposable fixture after explicit browser clicks. No live worker ran,
no live attachment was created, and no live harness file changed.

## Exact staged test results

| Gate | Result |
|---|---|
| Focused UI/security/harness/inspection regressions | PASS - 34 tests in 71.24 s |
| Complete Python suite | PASS - 120 passed in 153.58 s |
| JavaScript unit/navigation suite | PASS - 14 passed, 0 failed, 917.5722 ms |
| JavaScript syntax | PASS - `app.js`, both Worker Harness files, FlashRiver import/review files, and service worker |
| Python compile-all | PASS - 34 candidate Python files in exact short-path mirror |
| Smoke | PASS - `Twis Holo smoke test PASS` |
| Isolated API E2E | PASS - `Twis Holo API E2E PASS (isolated temporary data)` |
| Worker Harness plus Artifact Inspection API E2E | PASS - 3 passed in 22.48 s |
| Owner-lifecycle UI E2E | PASS - plan/stale-plan/run/approval/attachment/rollback plus 0 console errors/warnings |
| Complete live baseline comparison after all tests | PASS - frozen and current evidence hash both `0AFF17...6209` |

Environment notes, reported for completeness:

- A first full-suite command used the system Python, which had no `pytest`;
  it stopped before test collection. The authoritative run used the preserved
  Release 0.4 local environment (`pytest 9.1.1`) and passed 120/120.
- A first compile output location exceeded the Windows path limit while writing
  `.pyc` files. No syntax result was accepted from that attempt. Candidate
  Python sources were hash-copied to a short external mirror and all 34 compiled
  successfully. No bytecode or pytest cache remains in the candidate.
- The default browser channel's GPU process could not stay active in the
  restricted test session. The Playwright CLI was bound to its downloaded
  headless Chromium shell with workspace-scoped data; the lifecycle then passed
  with a clean console.

These were test-environment setup failures, not product assertions or ignored
test failures. Every authoritative release gate above completed successfully.

## Protected-hash comparison

All 11 protected Release 0.4 files remain byte-exact:

| Protected path | Bytes | SHA-256 |
|---|---:|---|
| `FOUNDATION_RELEASE_0.4.md` | 33,588 | `0E19A4C6E2D6B5741BF1894032A28DAF5CC9C1B7B73291FC6593F953EABC7536` |
| `start-workshop.bat` | 1,644 | `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1` |
| `FLASHRIVER.zip` | 7,363,639 | `6EF7317722202769B08D74A434519871736E055D1864FA5EB6C6FB547CB40108` |
| `data\source_archives\flashriver\6ef7317722202769\FLASHRIVER.zip` | 7,363,639 | `6EF7317722202769B08D74A434519871736E055D1864FA5EB6C6FB547CB40108` |
| `data\workshop.sqlite3` | 745,472 | `8963DC86337E40606F493DD78792069113DF6B7B0B570CB64F8B247F173CCBC6` |
| `FLASHRIVER_RECEIPT.json` | 2,905 | `8FE1FF272E4196D43B5012B6057E48103B8488167E65AF258AB39075A62BDA69` |
| `...\source_artifacts\CERT_RIVER_PHASE708_HANDOFF_FOLDER.zip` | 4,427 | `F284D63B665679B14869410B36CC07F64319B5FE21EFF0904D9C5B0EE26BA01F` |
| `...\source_artifacts\CERT_RIVER_PHASE755_FULL_REPAIR_AND_DEBUG_CLOSE.zip` | 61,367 | `F85E92DA8F5F225B670D76074E62712BCAE32588DC14FF7A182054C071721F1C` |
| `...\source_artifacts\FlashRiver_CERT-RIVER_phases709_to_754_T43_T44_T45_T46_MASTER_BUNDLE.zip` | 280,403 | `82D5EC34EA01674DDBC5B92DC7BD70B0130735DC6F2AFC31F1925AEABC5453D8` |
| `...\source_artifacts\TWIS_TALKBOX_BUILD_FOLDER.zip` | 12,226 | `5B8F34A7F3252D6066436C1306F86FC1A4BFDCA7BB910EE36C29530286F0660D` |
| `data\source_archives\.gitkeep` | 0 | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` |

The live tree remains exactly 223 files, including all 29 owner-acceptance
Worker Harness files.

## Database and source comparisons

Workshop SQLite was opened with `mode=ro&immutable=1` for final verification.

| Table/result | Release 0.4 freeze | Final live check |
|---|---:|---:|
| integrity | `ok` | `ok` |
| projects | 2 | 2 |
| artifacts | 59 | 59 |
| artifact_search | 59 | 59 |
| artifact_reviews | 2 | 2 |
| receipts | 13 | 13 |
| sessions | 0 | 0 |
| modules | 0 | 0 |
| jobs | 0 | 0 |
| database SHA-256 | `8963DC...CBC6` | `8963DC...CBC6` |
| schema SHA-256 | `0570D24F...F056` | `0570D24F...F056` |

The separate Artifact Compass database also remains exact at 90,112 bytes,
SHA-256 `3D9DCA0F7AC6751AB551DF6C9B365D9C34A4BDDDB07F8A2991D25DB796526DFD`,
integrity `ok`, with artifact/FTS counts unchanged (`20/20`).

All 51 public-source files remain byte-identical to the frozen record. The two
live duplicate AGENT files both remain:

`E4EFEDCAB226193F35EAE9E1CB6070102D7FD336B70A5C3205D33976D48BB38A`

Release 0.5 contains no `data` file and deploys no database, source artifact,
private archive, imported material, path record, review record, candidate,
activation record, or receipt.

## Exact changed-file manifest

The external `FOUNDATION_RELEASE_0.5_CANDIDATE_MANIFEST.txt` is deployment
authority because it can record the final report hash without a self-reference.
The deployment scope is exactly 16 files: 13 replacements and 3 additions.

| Status | Relative path | Bytes | Candidate SHA-256 |
|---|---|---:|---|
| changed | `app\assets\style.css` | 21,009 | `359220CA4D8F05DF44C4231007F9F108BE00EFD32630C06440F9363BBECAEF7B` |
| changed | `app\assets\worker-harness.js` | 31,797 | `41353F4A0DA6A263C0CF3E44F6F0EDEF2F351A97ACC86D36DB0507A1E06A5F2E` |
| new | `app\assets\worker-harness-view.js` | 10,695 | `DFE14637291404D9413BCAFB6648F1FDA79CFD1F87CF06C135EFC2DAD565533B` |
| changed | `app\index.html` | 17,837 | `CE60BD12CFC6DC37CF5DAEE2BC3CF3942F82212540B555333B71144A6FD1CD74` |
| changed | `app\service-worker.js` | 1,364 | `619BB8E56D4CA163B8C5042DF25362C2EC400CC5F819F2BC8286DB0884AD7635` |
| changed | `companion\foundation\worker_harness.py` | 101,450 | `7BE4A6921F1BD430E81D4B1D0266B374040A51E98EB955DF7864ACE420F98A04` |
| changed | `companion\server.py` | 45,833 | `F4F4779B916B03172F051040447A932EAE5E722760A5A467B0E0D6AD8390F9F8` |
| changed | `package.json` | 1,263 | `3D803B909F436CB06409B8FC6503FA933788F1573F58744DBC0B1811E1C66875` |
| changed | `tests\e2e_api_test.py` | 3,912 | `2C2191DFB4A190BADFBC32B54281D0B92B60FD028B212492C42A0AFAD05E5156` |
| changed | `tests\test_artifact_inspection_api_e2e.py` | 9,393 | `7437C978C67A8B4DA8E8E9BE1E2D6D3BE12B557706F40FF8B2A025A55D26133D` |
| changed | `tests\test_worker_harness.py` | 8,063 | `A244096D9BA0BD30D7307454E9D3E3B09FBE6AA898ED61DFF990368501317F9D` |
| changed | `tests\test_worker_harness_api_e2e.py` | 8,424 | `8C212338244585D87A00F261710C4C0F15EF758C7153A3F41DAC2669C075903C` |
| changed | `tests\test_worker_harness_security.py` | 9,827 | `C05AD72F35CE11B95DF3D6C71C95F292EDD04B8FA0A90A29AE1E7162B22AC20E` |
| changed | `tests\test_worker_harness_ui.py` | 4,816 | `DCDC115CDF0A72E3F9E5DC2CB245267627F1FE559F3CA5BE752A706EF61C114E` |
| new | `tests\worker-harness-view.test.js` | 7,926 | `892A9FFDE83F63DC1F1527CC2B302A682FFC6CEA9AE01447EC203E0967CDDCCC` |
| new | `FOUNDATION_RELEASE_0.5.md` | external manifest | external manifest records final bytes/hash |

Anything not in the external manifest is outside deployment scope.

## Rollback package

Prepared package:

`...\outputs\foundation-0.5-rollback\`

- `originals\` holds byte-exact Release 0.4 copies of all 13 files that would
  be replaced.
- `NEW_FILES_TO_REMOVE.txt` lists exactly the three new Release 0.5 files.
- `ORIGINALS_SHA256.txt` records every expected restored hash.
- `ROLLBACK_MANIFEST.json` records package membership, byte counts, and hashes.
- `README.md` provides copy-paste PowerShell rollback instructions.
- No protected data is included or changed by rollback.

The package was verified live-original-to-rollback at 13/13 with zero
mismatches. After a future rollback, the three new files are removed and the
same protected-hash, immutable-database, source-byte, and deployed-suite gates
must pass before reopening the Workshop.

## Exact owner-validation walkthrough

This walkthrough is deliberately not marked complete because Release 0.5 is not
deployed. Perform it only after exact-manifest deployment and deployed test
reruns pass.

1. Close every Workshop window. Confirm no listener exists on port 8787, then
   launch only `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS\start-workshop.bat`.
2. Open **Modules -> Guarded Worker Harness**. Confirm the header says
   `Foundation 0.5 - owner-truth control panel` and reports two fixed workers
   with no automatic attachment or activation.
3. Confirm eligibility reads **50 eligible**, **9 blocked**, and **0 source-hash
   mismatches**. Expand blocked artifacts and confirm private/blocked-root and
   unsupported-extension reasons remain excluded from the selector.
4. In the artifact selector, confirm both labels are separately visible:
   `AGENT.md - docs\AGENT.md` and
   `AGENT.md - docs\agent_files\AGENT.md`. Select each once and confirm the
   details panel changes artifact ID/path while the duplicate group retains both
   records.
5. Before any run, record the source hash in PowerShell:

   ```powershell
   $source = 'C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS\data\projects\flashriver-source-archive\sources\flashriver\6ef7317722202769\docs\AGENT.md'
   $before = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash
   if ($before -ne 'E4EFEDCAB226193F35EAE9E1CB6070102D7FD336B70A5C3205D33976D48BB38A') { throw 'Unexpected source hash before walkthrough.' }
   ```

6. Select **Artifact Compass Inspection** and click **Validate Worker Card**.
   Confirm worker/version, exact live read/write roots, network denied, shell
   denied, destructive actions denied, approval required, automatic activation
   denied, limits, unsupported capabilities, and Worker Card hash. Expand the
   raw card and spot-check that the summary matches it.
7. Confirm **Run planned worker** is disabled. Click **Create execution plan**.
   Review selected artifact/source hash, roots, blocked roots, permissions,
   timeout/limits, required test, recovery scope, generation, and prohibited
   automatic activation. Expand raw JSON and spot-check the same values.
8. Change to the other duplicate artifact. Confirm the plan becomes stale and
   run disables. Create a new plan for the intended artifact and confirm run is
   enabled only for that exact selection.
9. Click **Run planned worker** once. Confirm visible started/succeeded status,
   lifecycle `awaiting approval`, and readable result sections. Confirm purpose
   says **Heuristic - not established fact** and expand canonical JSON.
10. Confirm approval bindings show candidate, source, Worker Card, plan, and
    output hashes; generation; local actor assertion marked unauthenticated; and
    a required note. Try approval with a blank note and confirm the visible
    `approval_note_required` block. Enter an owner note and approve once.
11. Confirm lifecycle `approved` and state **Candidate approved, not attached**.
    Confirm only **Attach approved report** is available. Expand readable
    provenance/receipts and trace artifact -> card -> plan -> transaction ->
    test -> candidate -> approval/receipt. Confirm no hash is called a signature
    and no receipt is called immutable.
12. Click **Attach approved report**, read the confirmation, and accept. Confirm
    lifecycle `active`, state **Report attached and active**, and the four safety
    statements: source unchanged, no permissions, review unchanged, nothing at
    startup.
13. Review rollback target, recovery scope, current hash, expected restored
    hash, and unchanged source. Click **Roll back attachment**, read the
    confirmation, and accept. Confirm lifecycle `rolled back`, expected and
    verified restored hashes match, source is verified unchanged, history is
    still visible, and no further lifecycle action is offered.
14. Recheck the source and live database:

   ```powershell
   $after = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash
   if ($after -ne $before) { throw 'Source changed during owner walkthrough.' }
   $after
   ```

   The result must remain
   `E4EFEDCAB226193F35EAE9E1CB6070102D7FD336B70A5C3205D33976D48BB38A`.
   Then repeat the immutable Workshop SQLite integrity/count check and all 11
   protected hashes. The governed walkthrough may add only the deliberate
   separate Worker Harness candidate/approval/attachment/rollback evidence; it
   must not change Workshop SQLite or imported source bytes.
15. Refresh the browser on Modules. Confirm navigation returns to Modules, the
    rolled-back history remains readable, the service worker serves the 0.5
    assets, and there is no automatic run, attachment, or activation.

Stop the walkthrough immediately on a source-hash, database, protected-hash,
binding, action-gating, or restored-hash mismatch.

## Preserved safety guarantees

- fixed workers only; no arbitrary worker loader or arbitrary execution
- no network worker, unrestricted shell, destructive action, or AI/model install
- no automatic run, approval, attachment, activation, or rollback
- explicit public-safe artifact selection; blocked records remain excluded
- exact source, Worker Card, plan, candidate, output, and generation bindings
- source bytes and review state unchanged by inspection/attachment/rollback
- no launcher, archive, imported material, private data, or schema change
- receipt and rollback verification remain mandatory backend behavior
- HTML/imported-text escaping remains part of rendered view construction

## Honest limitations

- The actor field is a local assertion, not authenticated human identity.
- Network denial is enforced by application/host policy; it is not OS-level
  network isolation.
- Hashes prove byte equality, not authorship, trust, or digital signatures.
- Receipts are durable evidence records but are not cryptographically immutable.
- Purpose classification is deterministic heuristic output, not established
  fact or AI judgment.
- The UI does not make unsafe backend states safe; it reports and gates the
  existing fixed-worker backend, which remains authoritative.
- Live Release 0.5 owner acceptance and deployed-suite evidence do not exist yet
  because deployment correctly stopped at this approval gate.

## Deployment gate and readiness decision

Release-verification decision: **CONDITIONALLY READY FOR EXACT-MANIFEST LOCAL
DEPLOYMENT; NOT DEPLOYED; OWNER APPROVAL REQUIRED.**

Before deployment, verify the candidate manifest, report, and rollback manifest
one more time. Deployment must copy exactly the 16 manifest paths and nothing
else. After deployment, require 16/16 candidate-to-live equality, rerun the full
deployed suite, repeat the complete live-baseline protection checks, then perform
the owner walkthrough above. Any mismatch requires an immediate stop and the
prepared rollback procedure.

## Recommended next release

Make Release 0.5.1 a narrow reliability release: add cross-process locking and
crash-recovery tests for the file-backed Worker Harness registries, and preserve
the same fixed-worker/no-automatic-activation boundary. Do not add new worker,
network, model, or autonomous capabilities until that concurrency boundary is
proven.
