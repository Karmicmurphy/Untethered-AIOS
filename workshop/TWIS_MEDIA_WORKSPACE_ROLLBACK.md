# TWIS Images V2 Owner Workstation Rollback

Rollback package:

`C:\TWIS_FLASHRIVER_REVIEW_READY\images-v2-workstation-work\rollback`

The package contains the exact predeployment originals for every replaced path plus `ROLLBACK_MANIFEST.csv`. There are no release additions to remove and no database migration to reverse.

Safe rollback procedure:

1. Stop the TWIS local service.
2. Verify each rollback member against `ROLLBACK_MANIFEST.csv`.
3. Copy only the declared original files back to their exact relative paths under `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`.
4. Do not replace or modify `data\workshop.sqlite3`, project media, receipts, owner artifacts, or any unrelated Workshop file.
5. Restart TWIS and run the smoke, media-workspace, JavaScript/UI, SQLite integrity, desktop, and 390-pixel checks.

The simulated rollback is performed against a copied environment before live deployment. It must restore the full declared source scope to exact predeployment hashes.
