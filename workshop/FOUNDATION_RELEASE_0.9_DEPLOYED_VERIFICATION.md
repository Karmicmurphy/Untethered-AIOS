# Foundation Release 0.9 — Deployed Verification

## Decision

**PASS — Release 0.9 deployed, fully verified, and safely recoverable**

Verified on 2026-08-02 against the accepted Release 0.8 live baseline at `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`.

## Built

Release 0.9 extends the existing Local Worker Kit with exactly two fixed, deterministic, network-denied builders:

- **Handoff Proposal Builder**, supporting Codex Build Handoff, ChatGPT Continuation Handoff, Human Technical Handoff, and Project Recovery Handoff, with all 14 required sections.
- **Prompt Proposal Builder**, supporting Codex Implementation Prompt, ChatGPT Research Prompt, Local Model Task Prompt, and Human Work Order, with all 11 required sections.

The versioned `builder-output-v1` contract binds proposal text, builder/profile identity, worker/job/plan identity, ordered source IDs and hashes, owner goal, validation/approval/save/rollback state, and output SHA-256. The implementation reuses the Release 0.8 Worker Kit jobs, evidence, hashes, approvals, receipts, interruption recovery, and terminal cleanup.

The owner-facing builder workspace is available from My Work, Talk, Write, Artifact Inspection, and approved inactive worker results. It keeps plan approval separate from generation, result approval separate from saving, and saving separate from export. Long titles, paths, goals, proposal text, IDs, and hashes wrap at desktop and 390-pixel width.

Approved output can create exactly one inactive `handoff-draft` or `prompt-draft`. Explicit export supports UTF-8 plain text and JSON only under `data/exports/builders`, using generated sanitized and duplicate-distinguishing filenames. No output is sent, executed, attached, activated, installed, imported, promoted, or submitted.

## Exact deployment scope

Candidate manifest: `C:\TWIS_FLASHRIVER_REVIEW_READY\FOUNDATION_RELEASE_0.9_CANDIDATE_MANIFEST.txt`  
SHA-256: `5214D14A77C0B672A7BA87F3710CB5B8F4807A93613CEEFAB57D10CD04B92CB2`

Scope: **20 files — 12 replacements, 8 additions, 0 removals**.

Additions:

1. `FOUNDATION_RELEASE_0.9.md`
2. `app/assets/builder-workspace.css`
3. `app/assets/builder-workspace.js`
4. `companion/builder_output.py`
5. `docs/BUILDER_OUTPUT_V1_CONTRACT.md`
6. `docs/RELEASE_0.9_OWNER_GUIDE.md`
7. `tests/builder-workspace-ui.test.js`
8. `tests/test_builder_kit.py`

Replacements:

1. `app/assets/local-worker-kit.js`
2. `app/index.html`
3. `app/service-worker.js`
4. `companion/local_worker_kit.py`
5. `companion/server.py`
6. `package.json`
7. `tests/local-worker-kit-ui.test.js`
8. `tests/talk-room-ui.test.js`
9. `tests/test_local_worker_api.py`
10. `tests/test_talk_room_api.py`
11. `tests/test_worker_harness_ui.py`
12. `tests/write-room-ui.test.js`

No database replacement, cache, bytecode, browser output, evidence directory, rollback package, archive, temporary file, secret, launcher, or unrelated Workshop file was deployed. The predeployment gate reverified all 12 original hashes and all 8 absent addition paths. Candidate-to-live equality is **20/20 exact**, with zero out-of-scope payload changes.

Whole-tree inventory was 283 files before Release 0.9, 291 after the declared payload, and **292 accounted files after this report**.

## Database migration

The live SQLite file was migrated in place in a transaction; no replacement database was deployed.

- `user_version`: 8 → **9**;
- integrity: **ok**;
- foreign-key violations: **0**;
- projects: **2**, preserved;
- artifacts/search: **59/59**, preserved;
- reviews: **2**, preserved;
- receipts before Release 0.9 live lifecycle: **97**, preserved;
- final receipts: **131**;
- jobs, worker evidence, relationships, notes, handoff drafts, and prompt drafts after cleanup: **0**;
- final SQLite SHA-256: `8D954FDCAD8B86E17B9F5A37CF967BA48D52B9F98A14AD5D0E1B3FDDB6535448`;
- WAL/SHM sidecars after shutdown: absent.

The copied-database migration test preserved the row count of every existing table, advanced only `user_version`, reopened successfully, reported integrity `ok`, and found zero foreign-key violations.

## Tests

Isolated candidate verification:

- complete Python suite: **160 passed**;
- complete JavaScript/UI suite: **38 passed**;
- JavaScript syntax checks: passed;
- Python compile-all: passed;
- smoke test: passed;
- isolated API E2E: passed;
- Worker Harness, Artifact Inspection, Local Worker Kit, Handoff Builder, and Prompt Builder API E2E: **8 passed** in the selected E2E group;
- migration, security-negative, stale-plan, stale-result, recovery, save, export, and rollback tests: passed.

Deployed verification:

- Python suite: **159 passed in the loaded full run; the one inherited Worker Harness fault-injection check reached its timeout guard instead of its expected unexpected-file guard under concurrent verifier load, then passed immediately in an isolated exact retry (1/1)**. No Release 0.9 code touches that harness. This was classified as a verifier-load race rather than a product defect, per the release instruction not to fail correct product behavior over harmless evidence-collector timing.
- JavaScript/UI suite: **38 passed**;
- syntax checks, compile-all, smoke, isolated API E2E, Worker Harness E2E, Artifact Inspection E2E, Local Worker Kit API E2E, Handoff Builder API E2E, and Prompt Builder API E2E: passed;
- inherited four Release 0.8 fixed workers remain registered and their focused/API/E2E coverage passed;
- script injection and HTML/imported-text escaping checks passed; the builder UI inserts owner/source/output content as text.

No inherited test was deleted or weakened. Cache-version assertions were advanced from the accepted Release 0.8 cache to the required Release 0.9 cache.

## Six live lifecycles

All scenarios used the registered public-safe AGENT.md source, artifact ID `9217e4a7-7254-53a6-a75e-1d20e0754d86`, and verified SHA-256 `E4EFEDCAB226193F35EAE9E1CB6070102D7FD336B70A5C3205D33976D48BB38A`.

1. **Reject a handoff — PASS.** A valid Human Technical Handoff reached result review and was explicitly rejected. No draft was created; source bytes remained exact; job/evidence were cleaned; receipts remained.
2. **Approve a prompt without saving — PASS.** A Codex Implementation Prompt was approved and remained inactive, unattached, unexecuted, unsent, unsaved, and unexported.
3. **Save and roll back a handoff draft — PASS.** One Project Recovery Handoff was approved and saved as one inactive `handoff-draft`, appeared as a My Work artifact with exact source provenance, and was rolled back. Only that draft and its relationship were removed.
4. **Export a prompt — PASS.** One Local Model Task Prompt produced distinct sanitized UTF-8 TXT and JSON exports inside the approved Workshop export location. Network, execution, and provider-submission flags remained false. The two disposable verification copies were removed exactly.
5. **Reject a stale plan — PASS.** One controlled registered text fixture changed after planning. Execution was rejected as stale. The fixture, artifact/search row, job, and evidence were cleaned.
6. **Recover an interrupted job — PASS.** A running Human Work Order was interrupted, restart classified it as `interrupted`, no mutation resumed, explicit recovery returned it to the approved plan, explicit cancellation completed, and disposable job/evidence state was cleaned.

Live lifecycle receipts increased from 97 to **131**, a delta of **34**. The delta records six plan creations, six plan approvals, four completed/validated outputs, three result approvals, one result rejection, one stale-plan rejection, one draft save, one exact draft rollback, two exports, one interruption, one recovery, one cancellation, and six terminal history cleanups. Audit receipts remain after job/evidence cleanup.

## Browser, cache, and network

Disposable candidate and deployed-byte-copy Playwright lifecycles passed at 1440×1000 and 390×844.

- desktop handoff plan, browser refresh recovery, generation, validation, full preview, and rejection: passed;
- mobile prompt plan, generation, full preview, approval without save, and builder-scoped wrapping: passed;
- browser console errors: **0**;
- browser console warnings: **0**;
- page errors: **0**;
- application requests outside the selected loopback origin: **0**;
- provider submissions, model calls, and product network workers: **0**;
- service-worker caches after activation: exactly **`twis-holo-full-v9`**;
- stale Release 0.8 Workshop cache: removed by the versioned service-worker activation contract;
- navigation/project refresh reloads builder sources, and session recovery restores the current governed builder job.

Playwright and its Chromium binary were downloaded only into the external Release 0.9 verification work directory as test infrastructure. They were not product dependencies, product network activity, candidate payload, or deployed files.

## Protected state and safety

- all 20 deployed payload files: exact;
- 51/51 public imported core/support artifacts: byte-identical and registered hashes exact;
- 4/4 private source archives: byte-identical and registered hashes exact;
- 3/3 registered visuals: byte-identical and registered hashes exact;
- 1/1 FlashRiver intake manifest: byte-identical and registered hash exact;
- all 56 Worker Harness evidence files: exact;
- authenticated AGENT.md: exact at `E4EFEDCAB226193F35EAE9E1CB6070102D7FD336B70A5C3205D33976D48BB38A`;
- launcher `start-workshop.bat`: unchanged at `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`;
- secondary `START_TWIS.bat`: unchanged at `12AF861C9E3EF2A10EB05CF03C0B71738187DA935D704AF3EB3D6925BF0D437B`;
- projects, reviews, source registrations, permissions, private archives, imported source bytes, startup behavior, and unrelated Workshop data: unchanged;
- active attachments: 0;
- imports, modules, automatic activation, package installation/execution, shell/Python workers, arbitrary workers, provider/model calls, autonomous chains, and network workers: 0;
- disposable `.pytest_cache` files and one generated Worker Harness bytecode file detected by the final whole-tree audit were removed exactly; historical accepted baseline caches were preserved;
- test/browser output and all verification runtimes remain outside the active Workshop;
- ports **8787, 8875, 8891, and 8892**: closed after verification.

## Rollback and recovery

Rollback package: `C:\TWIS_FLASHRIVER_REVIEW_READY\foundation-0.9-rollback`

- rollback manifest SHA-256: `79EA1E07BAE3D7F4194A17E0D4A01BCDF433A3F08C43AA1130BB40C8486BF422`;
- rollback README SHA-256: `5C856BF8E0FF06266DCCC56B54857E5BDA72525A40F8B25CFCF82E794A4E2CB4`;
- pre-migration SQLite backup SHA-256: `EE9B63B8AF1CBCC5AE6D3250B32B0E2887F8B8BB82D4E9FE1C478B30523423FD`;
- predeployment rollback simulation: PASS;
- post-live rollback simulation: **PASS** — 12 authenticated originals restored, 8 exact additions removed, database backup restored to `user_version=8`, integrity `ok`, and foreign-key violations 0;
- live Workshop was not rolled back; the simulation operated only in the external Release 0.9 work directory.

## Key deliverables

- `FOUNDATION_RELEASE_0.9.md` — SHA-256 `561B3A3A8245CF1B1A7DA3254202E7A0FCC49172A3921B610141DD30E1D305C5`;
- `docs/BUILDER_OUTPUT_V1_CONTRACT.md` — SHA-256 `0E35EA64EE5ABE18299B91F4445D886E78A090C5BDD951B7CFDAA14B60E6DA82`;
- `docs/RELEASE_0.9_OWNER_GUIDE.md` — SHA-256 `CEC3FAAA1E3FF63B717666B4D9914D41C7CAE3C967FD835469FB30553A3B4166`;
- `companion/builder_output.py` — SHA-256 `FB383F6014623089E58A124A969E95630F940B643BF332308BB90C6AAF96DDCE`;
- candidate and rollback manifests — hashes listed above.

## Deliberate limits and Release 0.10 direction

Release 0.9 deliberately does not include provider routing, model execution, cloud workers, unrestricted scanning, shell/Python workers, MCP execution, package execution, automatic prompt submission, automatic attachment/activation, module promotion, image/music/video workers, autonomous chains/crews/agents, cloud sync, mobile packaging, or a visual redesign.

The recommended next release remains **Release 0.10 — Tool Registry and Governed Adapter Catalog**: a read-first catalog of fixed, versioned adapters and capability/permission contracts, while retaining explicit owner approval and keeping provider dispatch outside the Release 0.9 builder boundary.
