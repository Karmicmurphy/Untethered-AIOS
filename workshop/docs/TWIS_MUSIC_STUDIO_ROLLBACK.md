# TWIS Music Studio — Rollback

Authenticated rollback originals are stored outside the live Workshop under:

`C:\TWIS_FLASHRIVER_REVIEW_READY\music-studio-work\rollback`

The rollback manifest records every predeployment replacement hash. A bounded rollback restores only the 15 declared replacements and removes only the 11 declared additions. It never replaces or edits SQLite, owner projects, registered sources, artifacts, receipts, model/runtime resources, launchers, or unrelated Workshop files.

Rollback procedure:

1. Stop only the Workshop service bound to `127.0.0.1:8787` and stop the registered local model if running.
2. Verify every rollback original against `rollback\ROLLBACK_MANIFEST.json`.
3. Restore the 15 replacement originals and remove the 11 release additions.
4. Verify all restored hashes, SQLite integrity, foreign keys, and `user_version=13`.
5. Start the Workshop and run smoke plus Music/Write targeted regression tests.

Rollback is an explicit owner/deployment action; it is never automatic.

