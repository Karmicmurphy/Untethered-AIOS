# Twis Holo Foundation Release 0.2 — Delivery Report

Delivered locally on 2026-07-16 to:

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

This is the corrected runnable build. Start it with `start-workshop.bat`. The working folder was patched in place after explicit approval; it was not replaced, re-imported, published, or converted into a Git repository.

## Outcome

Release 0.2 preserves the existing Workshop, dedicated FlashRiver Review, live SQLite data, original archives, receipts, and private source artifacts. It adds four bounded foundation capabilities:

1. Worker Card v0.1 schema/validator/examples.
2. Canonical Windows path containment for cooperating callers.
3. Transaction manifests, hash-linked receipt evidence, bounded file snapshots, and SQLite backup/restore.
4. A separate deterministic Artifact Compass SQLite/FTS5 index and CLI.

No worker was activated. No Artifact Compass index was built from live/private data. No live database migration ran.

## Architecture and schema changes

- Existing runtime architecture remains `app/` + `companion/server.py` + `data/workshop.sqlite3`.
- New standard-library modules live under `companion/foundation/` and are inert until explicitly called.
- `schemas/worker-card-v0.1.schema.json` defines the declaration contract and exact schema compatibility policy.
- `schemas/transaction-manifest-v0.2.schema.json` defines transaction state/evidence fields.
- Artifact Compass creates only an explicitly named separate database with `compass_meta`, `compass_artifacts`, and `compass_fts`. It does not alter the Workshop schema.
- `/api/capabilities` reports the foundation honestly: Worker Cards are not host-enforced, path containment is a cooperating-caller library, transactions are bounded, and Artifact Compass has no live index or vector search.

See `ARCHITECTURE.md`, `DECISIONS.md`, `PROJECT_STATE.md`, and `OPEN_QUESTIONS.md` for the current truth boundary.

## Enforcement matrix

The field-by-field Worker Card enforcement matrix is in `docs/WORKER_CARD_V0.1.md`.

Summary:

| Capability | Validated/enforced now | Not claimed |
|---|---|---|
| Worker Cards | Schema, compatibility, types, roots, permission dependencies, failure policy, provenance | Activation, permission grant, OS sandbox |
| Path policy | Canonical read/write/blocked roots, traversal, drive/case/UNC, prefix, nonexistent, ADS/reserved names, symlink and junction escape | Interception of arbitrary/uncooperative I/O; elimination of TOCTOU |
| Transactions | State transitions, hashes, permission evidence, hash-linked receipts, fixture snapshots/backups, interruption detection | Signatures, immutability, distributed atomicity, whole-system rollback |
| Artifact Compass | Deterministic filename/path/phrase/project/status/provenance search, generations, changed reindex, tombstones, stale detection, exact-hash groups with all paths | Source authority, archive parsing/import, deletion/deduplication, embeddings/vector search |

## Recovery limits

Recovery is limited to explicitly captured individual files and SQLite backups. SQLite backup/restore uses the SQLite backup API and integrity checks. Restore refuses an existing destination unless a caller deliberately opts into replacement. There is no live-route transaction wrapper, process supervisor, multi-process lock manager, filesystem journal, or whole-machine rollback.

Receipts are hash-linked tamper evidence only. They are not digitally signed, immutable, trusted timestamps, or proof of actor identity.

## Verification results

Run from the deployed live folder:

| Check | Result |
|---|---|
| `npm test` | PASS — 51 Python tests and 3 JavaScript tests |
| `python tests\smoke_test.py` | PASS |
| `python tests\e2e_api_test.py` | PASS — isolated temporary data |
| `python -m compileall -q .` with redirected cache | PASS |
| `node --check` across every `.js` file | PASS — 7 files |
| Live SQLite immutable/read-only `PRAGMA integrity_check` | PASS — `ok` |
| Protected-file SHA-256 comparison | PASS — 9/9 unchanged |

The 51 Python tests include:

- FlashRiver import/recovery UI and Review API/view regression coverage.
- Refresh restoration and active-project persistence (with 3 JavaScript navigation tests).
- Review-status and note persistence.
- Exact-hash grouping that retains every source path.
- Worker Card schema, compatibility, valid/invalid examples, and permission dependencies.
- Windows traversal, absolute escape, prefix confusion, drive mismatch, case, UNC, nonexistent targets, blocked roots, ADS/reserved names, symlink, and actual temporary junction tests.
- Transaction schema/lifecycle, permission gating, receipt tamper detection, crash/recovery state, file snapshot, and SQLite backup/restore tests on temporary fixtures.
- Artifact Compass deterministic search, exact phrases, provenance/status/project filters, duplicate paths, changed reindex, generations, tombstones, stale detection, rebuild, and CLI tests.

No product test failed. Two verification-command attempts failed for harness reasons and were corrected: the first redirected Python bytecode path exceeded the Windows path limit, and the first live SQLite summary used an incorrect review-note column name after a PowerShell quoting retry. Compile-all then passed with a shorter writable cache path, and the corrected immutable/read-only query returned `integrity=ok`.

## Live state verification

The post-deployment immutable/read-only database audit found:

- 2 projects.
- 59 artifacts, all 59 under `flashriver-source-archive`.
- 2 artifact review rows.
- Both review rows remain `reviewed`.
- Both notes remain nonempty (8 and 14 characters; note contents were not exposed).

## Protected files unchanged

| Protected path | SHA-256 before and after |
|---|---|
| `FLASHRIVER.zip` | `6EF7317722202769B08D74A434519871736E055D1864FA5EB6C6FB547CB40108` |
| `data/source_archives/flashriver/6ef7317722202769/FLASHRIVER.zip` | `6EF7317722202769B08D74A434519871736E055D1864FA5EB6C6FB547CB40108` |
| `data/workshop.sqlite3` | `4DC0249DEBF32C70CF9C3FB8BF56E9E8FA92E88B66B69B61522E5A7FC49D5863` |
| `FLASHRIVER_RECEIPT.json` | `8FE1FF272E4196D43B5012B6057E48103B8488167E65AF258AB39075A62BDA69` |
| `CERT_RIVER_PHASE708_HANDOFF_FOLDER.zip` | `F284D63B665679B14869410B36CC07F64319B5FE21EFF0904D9C5B0EE26BA01F` |
| `CERT_RIVER_PHASE755_FULL_REPAIR_AND_DEBUG_CLOSE.zip` | `F85E92DA8F5F225B670D76074E62712BCAE32588DC14FF7A182054C071721F1C` |
| `FlashRiver_CERT-RIVER_phases709_to_754_T43_T44_T45_T46_MASTER_BUNDLE.zip` | `82D5EC34EA01674DDBC5B92DC7BD70B0130735DC6F2AFC31F1925AEABC5453D8` |
| `TWIS_TALKBOX_BUILD_FOLDER.zip` | `5B8F34A7F3252D6066436C1306F86FC1A4BFDCA7BB910EE36C29530286F0660D` |
| `data/source_archives/.gitkeep` | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` |

## Changed-file manifest

`FOUNDATION_RELEASE_0.2.md` is this delivery report; its hash is reported at final handoff after deployment. The 31 reviewed implementation files are:

| Change | Path | SHA-256 |
|---|---|---|
| Added | `ARCHITECTURE.md` | `9825B3DDD4CB95B5043417EC3EC61B305C43A246307F62E31F0751D98FDA0F01` |
| Added | `DECISIONS.md` | `0332AC0060C15AD899F50030AB4771753DDBA5EE8CB5DEFCF3DD8E1A7E4112D9` |
| Added | `OPEN_QUESTIONS.md` | `BAB64891662B2D470545D18552A09B19A0E9AEC6FCA29DD1775A9EC16D1E9408` |
| Added | `PROJECT_STATE.md` | `B4036C6F4DB77DAFAE393431B85F99450AC6052239D1F431C57AE8446916D8B8` |
| Modified | `README.md` | `6929D3BC36BAB3533C4B0F879A2A2D0CEEDF1D1CA3C068DB2DC17234FA784A79` |
| Modified | `package.json` | `A25316B2AD42ADC6587D9D8BCF72D13CF1923D3EBC93347432FCC1C4D452506B` |
| Added | `companion/__init__.py` | `3AD1B30A9BC42CDE7FE83838E3A0D87493C56A7F4E5FFDDAB00578743B147BBF` |
| Modified | `companion/server.py` | `F71007B1DFF81F1D2A1A1D62FCA748A80E25A6F4AE6E8C0B4055849D9133F177` |
| Added | `companion/foundation/__init__.py` | `43A6D800AB7BF38699DF2BCB7EA52C38A52965BD478CF19E96F79C12F78EB037` |
| Added | `companion/foundation/artifact_compass.py` | `84C7DDB0662C21FFFC6A6C89772C795EBCEC21C0BC07F20E0D4E76ABC3248D88` |
| Added | `companion/foundation/cli.py` | `F29E991EEBE71528B6204E0D0F0FDF1C0DCB036B955084192E1B497CD7D3FBD9` |
| Added | `companion/foundation/path_policy.py` | `B0C3A7CF8C296DC351CC3AAF2E5B13E8F2EAB048334892F72372EF8B74B5B2D4` |
| Added | `companion/foundation/transactions.py` | `A277A833292B681A75FAC6B10618C9431EE1090137C1AE70FA60A7B49F92DBB3` |
| Added | `companion/foundation/worker_cards.py` | `700957AB4986F251007071F91F14E19952745229D37B4A3F1D14A1C03FE7480C` |
| Added | `docs/ARTIFACT_COMPASS_FOUNDATION.md` | `45542966400A882C293DDD59D0E07F0509BF84869E7F18E38EBAAD8804EA3658` |
| Added | `docs/PATH_CONTAINMENT.md` | `6E7F40A54E4DC3F13EB6BF26CD0FE333D17AB67A71E6E203FC56E09ED8287EB8` |
| Added | `docs/TRANSACTION_RECOVERY.md` | `ED2C63BC7AAB22AC56DCB3C71E006AB04009FF1F2CB1303907829593D324BBCC` |
| Added | `docs/WORKER_CARD_V0.1.md` | `22345D5365DDF51188EEB9CE76D5922E720927390F4CD0FA8AE5F4A32E3167AB` |
| Added | `examples/artifact-compass-inventory.example.json` | `BAEE976180BB5835C21295BB0BED840CFC21CBB7058D3ADA1F74EA3FD276CD86` |
| Added | `examples/worker_cards/invalid/future-schema.json` | `0D36F42376F89E3F80553A1FC1C41758E73FB672B3A7C2DC21E238E764E2E07D` |
| Added | `examples/worker_cards/invalid/unsafe-shell-worker.json` | `0583C2A35C06379821E79AEDDC6A1B71A9BCA6CA79E01A8EDD2F2D5A9DA69776` |
| Added | `examples/worker_cards/valid/bounded-file-worker.json` | `0A049D61C08B59B62B2BDEDB44C7709634CBB463C159F3B5FC5A4260AF574E22` |
| Added | `examples/worker_cards/valid/flashriver-review-reader.json` | `E1F873767B1155FF25C843423924760EE1958CB438777EA370566EFF0D06E5FD` |
| Added | `schemas/transaction-manifest-v0.2.schema.json` | `FBE43D4CAD1EA7B45CDACB8E7B450B92C1F2B4F8641AFB4316BF108CF63E95CD` |
| Added | `schemas/worker-card-v0.1.schema.json` | `AE3C7972D64952382056915CCCB73E7C4E26FB79B807D4486ED0484DF5FDAFB0` |
| Modified | `tests/e2e_api_test.py` | `214BF12F1624F23890FCD447BBF3F5944173898105AB461B109F2875E4B001C9` |
| Added | `tests/test_artifact_compass.py` | `1D338BE446373E3C1D02B1D5B0A4F6818464AFD50A3F795B94BB0D5EA7CE27D8` |
| Added | `tests/test_foundation_cli.py` | `57731759ADA63176790C6FD2895164D6ECCA13694F2AD26C8E92668BEF1C820E` |
| Added | `tests/test_path_policy.py` | `34917AEA5BF6AA0BEABFBF80C6C51C2B387D82C4CD61A68BE82A1F08509AF9D0` |
| Added | `tests/test_transactions.py` | `A2AC79B61F2B46DE7E39C1145ACEA1245E85228B07484440A96D1DF21B6BEA98` |
| Added | `tests/test_worker_cards.py` | `15A43A9F659F9B6F7B8ECCA05929698F1A96441DCAEB8350998F034BDE7F0BAD` |

## Rollback evidence

Before deployment, code-only copies of the four modified pre-existing files were saved under the Codex task workspace at `work/foundation-0.2-rollback/`. New files would require an explicitly approved rollback decision before removal. No automatic rollback or deletion was performed.

## Remaining manual validation

One final owner-visible browser check remains: double-click `start-workshop.bat`, open FlashRiver Review, refresh the browser, and confirm the dedicated route reopens with `flashriver-source-archive` active and the two saved statuses/notes visible. Automated navigation, view, API, and persistence tests pass, but this manual check confirms the owner’s actual browser/localStorage state.

## Not built in this release

Worker execution/activation, TalkBox promotion, voice routing, autonomous repair, generated modules, vector search/embeddings, broader UI work, backend rewrite, cloud deployment, container infrastructure, archive rewriting, source deletion, duplicate deletion, and live/private automatic indexing were not built.

## Recommended next release

After the manual browser check, the safest next release is a narrowly scoped host-enforcement pilot for one read-only, non-networked Worker Card using the path policy and transaction receipts. It should not begin until separately authorized and threat-reviewed.
