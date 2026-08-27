# TWIS Video V2 Rollback

The live Workshop has not been changed. The staged rollback source is:

`C:\TWIS_FLASHRIVER_REVIEW_READY\video-v2-workstation-work\rollback`

## Prepared rollback boundary

- Exact pre-release copies of all 15 application replacements are stored under `application-originals` using their live relative paths.
- The 11 application additions and three adjacent runtime additions are listed as absent-before paths.
- The live SQLite database, project trees, launcher, receipts, and owner content are not deployment targets and are not replaced during rollback.

## Exact rollback procedure after a future approved deployment

1. Stop only the TWIS local service after confirming no governed job is active.
2. Verify every deployed replacement/addition still has its approved deployed SHA-256. Stop on any out-of-band mismatch.
3. Restore the 15 originals from `application-originals` to the exact relative paths.
4. Remove only the 11 release-added application paths whose hashes still equal the deployed manifest.
5. Remove only the three adjacent FFmpeg runtime files whose hashes still equal the deployed manifest. Remove empty release-created runtime directories only after resolving and checking the exact path under `C:\TWIS_FLASHRIVER_REVIEW_READY\runtime\ffmpeg\9.0.1`.
6. Do not touch `data/workshop.sqlite3`, `data/projects`, receipts, launchers, or unrelated runtime resources.
7. Re-run Python/JavaScript regression, SQLite integrity/foreign-key checks, and Sanctuary/Crossroads startup.

If any target differs from the deployed manifest, rollback must stop and report a conflict rather than overwrite newer work.
