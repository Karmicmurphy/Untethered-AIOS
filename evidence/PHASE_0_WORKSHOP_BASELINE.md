# Phase 0 Workshop Baseline Certificate

## Scope

- Candidate repository: `Karmicmurphy/Untethered-AIOS`
- Source commit: `f33976af8b484206b46327806fa90362d2e600a6`
- Candidate branch: `bootstrap/workshop-baseline`
- Authoritative read-only source: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`
- Imported destination: `workshop/`
- Date verified: 2026-08-27

## Authentication and import

- Included code-safe files: **293**
- Excluded private/runtime/cache files: **233**
- Source tree SHA-256: `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`
- Imported tree SHA-256: `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`
- Source/import exact match: **PASS**
- Post-test imported authenticated-byte check: **PASS**
- Post-test authoritative code-safe tree check: **PASS**, same SHA-256

The candidate authentication filter explicitly excludes `data/`, `.pytest_cache/`, private source-artifact directories, environment files, Python bytecode, archives, compiled launcher binaries/debug symbols, databases, SQLite sidecars/journals, logs, caches, and temporary directories. Review confirmed that no `data/`, database, environment, archive, compiled launcher, cache, private receipt, or private-source file entered the imported manifest.

## Defects repaired before import

1. The initial exclusion policy admitted project/runtime data, private/recovered archives, root ZIP archives, compound SQLite sidecars, a compiled launcher, and a Workshop-private receipt. The filter now excludes those classes and has a regression test.
2. Authentication and import used different tree-entry ordering on Windows. Import failed closed before copying. Both now use the same path-sorted digest contract, with a regression test.

## Current health evidence

- Imported Workshop Python suite: **249 passed** in 483.90 seconds.
- Imported Workshop JavaScript/UI suite: **86 passed, 0 failed**; all declared syntax checks passed.
- Untethered bootstrap suite: **13 passed** in 1.076 seconds.
- Baseline-focused suite after repairs: **6 passed**.
- Background-removal runtime/API focused verification: **6 passed** in 101.45 seconds.

The Workshop suites ran only against `workshop/`. A temporary candidate-local junction exposed the existing adjacent runtime read-only for runtime-dependent tests. It was verified, removed after testing, and did not become candidate content.

The first imported-copy test attempt correctly reported four runtime-dependent failures because the code-safe snapshot does not copy the adjacent runtime. After the temporary read-only runtime mapping, the focused tests and complete suite passed. The first declared `npm test` attempt also stopped before collection because system Python lacked `pytest`; `pytest 9.1.1` was installed only in the ignored candidate `.venv`.

## Protected-state verification

- Music Loop Deck V1 was not restarted, modified, or redeployed.
- No test command ran from the authoritative Workshop root.
- Authoritative Workshop code-safe tree before/after: exact SHA-256 match.
- Live SQLite was inspected using `mode=ro&immutable=1`: integrity `ok`, `user_version=13`, foreign-key violations `0`, projects `3`, artifacts `60`, receipts `331`, jobs `1`.
- Windows denied a raw live SQLite file hash because the running Workshop held the file; the service was not stopped or checkpointed.
- Verified background-removal runtime manifest SHA-256 after tests: `C9E178F183F662209C682222AA8590FA6C8E8A460F26A946F55F39E32EF102DE`.

## Runtime, provider, database, and authority status

- AIOS runtime: Python 3.12.10 standard-library bootstrap.
- Test-only dependency: `pytest 9.1.1` in ignored `.venv`.
- Model/provider: none required or activated.
- Network/provider authority: none added.
- Database import or migration: none; live databases remain excluded.
- Live Workshop integration/deployment: not performed.

## Phase boundary

**PASS — WORKSHOP BASELINE authenticated and imported into Untethered AIOS candidate**

This certificate proves Phase 0 only. It does not claim the full AIOS or Kernel V0.2 is complete.
