# Music Loop Deck V1 rollback

Rollback authority is the exact package under:

`C:\TWIS_FLASHRIVER_REVIEW_READY\music-successor-program-work\rollback\MUSIC_LOOP_DECK_V1`

The package contains the pre-deployment bytes for every replacement and an additions list for files that did not exist in the protected baseline. It does not contain or replace the Workshop database, projects, receipts, runtime, model resources, or owner media.

Rollback procedure:

1. Stop only the local TWIS companion after confirming no state-changing job is active.
2. Verify the deployed scope against the deployed manifest.
3. Restore each replacement from `files\<relative path>` using literal paths.
4. Remove only the explicitly listed added files if their hashes still match the deployed manifest.
5. Restart the existing companion and verify health, SQLite integrity, foreign keys, Sanctuary, Crossroads, Music, My Work, and service-worker cache state.
6. Record the rollback outcome without deleting prior receipts.

The deployment and rollback simulations use temporary mirror roots; they never write the live Workshop before owner approval.
