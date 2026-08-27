# TWIS Build + Modules V2 — Rollback

The live Workshop has not been changed by candidate construction or verification.

Rollback package root: `C:\TWIS_FLASHRIVER_REVIEW_READY\build-modules-v2-work\rollback`

If this exact candidate is later approved and deployed, rollback is bounded to the manifest:

1. Stop only the TWIS service after checking that no governed job is active.
2. Verify the live root resolves to `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`.
3. Restore each of the 16 replacement originals from `rollback\originals` to its same relative path.
4. Remove only the 15 manifest-declared additions.
5. Do not touch `data`, owner projects, receipts, external runtime/model assets, launcher files, or any out-of-scope path.
6. Recompute the restored scope hashes and compare them with `baseline\baseline.json` and the rollback manifest.
7. Open SQLite read-only and verify integrity, foreign keys, `user_version`, counts, and the original database hash.
8. Start TWIS and run the bounded smoke/regression verification.

The rollback simulation must occur in `build-modules-v2-work\rollback-simulation`, never against the live Workshop. A successful simulation must reproduce every predeployment file in the exact scope and leave every out-of-scope candidate file irrelevant to rollback.

