# Write Studio AI Actions - Deployed Verification

Decision: PASS - deployed and verified.

## Automated evidence

- Python: 194 passed.
- JavaScript/UI: 62 passed.
- Smoke test: PASS.
- Isolated API E2E: PASS.
- Worker Harness and Artifact Inspection API E2E group: 3 passed.
- JavaScript syntax, Python compile-all, and service-worker syntax: PASS.
- Desktop browser 1440 × 1000: PASS; horizontal overflow 0.
- Mobile browser 390 × 844: PASS; horizontal overflow 0.
- Browser console errors / warnings / page errors: 0 / 0 / 0.
- Browser external requests: 0.
- Service-worker cache: `twis-holo-full-v17-write-studio` only.
- Candidate-to-live equality: 21/21 exact.

## Real local-model evidence

The installed Liquid LFM2.5 1.2B Instruct Q4_K_M completed one disposable selected-passage action through the deployed Worker Kit. The plan was approved separately, inference returned proposed content, the result was approved separately, one inactive AI draft was saved, and that draft was rolled back. The source SHA-256 remained exact after inference and rollback. The registered llama.cpp process was explicitly stopped.

## Negative and governance evidence

Tests cover all fixed actions, selection-only input, whole-draft input, explicit context, invalid/disabled/missing model behavior, stale source rejection at execution and result approval, approval-note gates, result rejection, source preservation, output hashes, receipts, refresh recovery, inactive save, and rollback. No provider or external model call is present.

The database was not replaced or migrated. Final SQLite integrity is `ok`, foreign-key violations are 0, and `user_version` remains 13. The lifecycle left 59 artifacts, 0 active jobs, 0 worker evidence, 0 temporary relationships, 0 Write versions, and 0 Write proposals. Receipts increased from 226 to 237 through legitimate deployed verification activity.

All 59 registered source paths remain present with zero source-hash mismatches. The 50 eligible / 9 intentionally blocked source classification remains unchanged. The launcher and both startup scripts remain unchanged. Rollback-package verification and the copied-environment rollback simulation passed.

The system Python does not include pytest, so the established verification virtual environment ran the full suite and the Worker Harness / Artifact Inspection E2E group. This is an environment packaging detail, not a Workshop defect.
