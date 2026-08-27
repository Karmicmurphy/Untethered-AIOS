# Project State — Foundation Release 0.4

Baseline re-verified on 2026-07-21 against `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS` before Release 0.4 staging.

## Authority order

1. Current files and immutable/read-only SQLite contents.
2. Current runtime behavior and executable tests.
3. Receipts, protected hashes, and current schemas.
4. This state document and `FOUNDATION_RELEASE_0.4.md`.
5. Release 0.2/0.3 reports and older audit documents as historical evidence.

The folder is not a Git checkout. No repository was initialized, and no Git history was available.

## Current baseline

- Runtime: local Python companion at `http://127.0.0.1:8787`, launched by unchanged `start-workshop.bat`.
- Frontend: static HTML/CSS/JavaScript in `app/`.
- Primary persistence: `data/workshop.sqlite3` and local project folders.
- Immutable SQLite integrity: `ok`.
- Projects: 2.
- Artifacts and FTS rows: 59 each.
- Artifact review rows: 2.
- Receipts: 12.
- Sessions, modules, and jobs: 0 each.
- Release 0.3 `data/worker_harness/` state was absent at the Release 0.4 baseline.

These counts are an inspection snapshot, not a future invariant.

## Artifact eligibility baseline

The importer-defined FlashRiver `docs` directory is the only approved public-safe source root in Release 0.4.

- Eligible: 50 current `.md`, `.json`, or `.txt` artifact records under `docs`.
- Ineligible: one `.csv`, the intake manifest outside `docs`, four private ZIP artifacts, and three visuals.
- Structurally private/out-of-root files are rejected without opening their contents.

## Protected baseline hashes

| Path under project root | Bytes | SHA-256 |
|---|---:|---|
| `FLASHRIVER.zip` | 7,363,639 | `6EF7317722202769B08D74A434519871736E055D1864FA5EB6C6FB547CB40108` |
| `data/source_archives/flashriver/6ef7317722202769/FLASHRIVER.zip` | 7,363,639 | `6EF7317722202769B08D74A434519871736E055D1864FA5EB6C6FB547CB40108` |
| `data/workshop.sqlite3` | 745,472 | `4DC0249DEBF32C70CF9C3FB8BF56E9E8FA92E88B66B69B61522E5A7FC49D5863` |
| `FLASHRIVER_RECEIPT.json` | 2,905 | `8FE1FF272E4196D43B5012B6057E48103B8488167E65AF258AB39075A62BDA69` |
| `.../CERT_RIVER_PHASE708_HANDOFF_FOLDER.zip` | 4,427 | `F284D63B665679B14869410B36CC07F64319B5FE21EFF0904D9C5B0EE26BA01F` |
| `.../CERT_RIVER_PHASE755_FULL_REPAIR_AND_DEBUG_CLOSE.zip` | 61,367 | `F85E92DA8F5F225B670D76074E62712BCAE32588DC14FF7A182054C071721F1C` |
| `.../FlashRiver_CERT-RIVER_phases709_to_754_T43_T44_T45_T46_MASTER_BUNDLE.zip` | 280,403 | `82D5EC34EA01674DDBC5B92DC7BD70B0130735DC6F2AFC31F1925AEABC5453D8` |
| `.../TWIS_TALKBOX_BUILD_FOLDER.zip` | 12,226 | `5B8F34A7F3252D6066436C1306F86FC1A4BFDCA7BB910EE36C29530286F0660D` |
| `data/source_archives/.gitkeep` | 0 | `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` |

The abbreviated private prefix is `data/projects/flashriver-source-archive/sources/flashriver/6ef7317722202769/private_source_artifacts/source_artifacts/`.

## Release 0.4 capability state

- Release 0.3 reference worker/lifecycle behavior remains supported.
- `artifact-compass-inspection-worker` v0.4.0 accepts one explicit public-safe text artifact and produces bounded canonical JSON without AI.
- Source SHA-256 is checked before reading, after reading, after child completion, and during deterministic parent validation.
- Approval explicitly binds candidate, source, Worker Card, execution plan, and workspace generation hashes.
- Activation attaches only the approved report; artifact bytes, SQLite rows, review status, permissions, and startup behavior remain unchanged.
- Rollback restores bounded harness output and marks the report attachment rolled back.
- Worker persistence remains separate under `data/worker_harness/`; no Workshop SQLite migration is added.

## Explicitly not built

AI/model inspection, arbitrary/generated workers, artifact repair, vector search, voice routing, TalkBox promotion, autonomous repair, unrestricted shell/network, broader UI redesign, backend rewrite, publishing, and cloud deployment remain out of scope.
