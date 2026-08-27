# Write Studio AI Actions — Rollback

Rollback material is stored outside the live Workshop under `C:\TWIS_FLASHRIVER_REVIEW_READY\write-studio-ai-actions-work\rollback`.

The bounded rollback restores only the 15 replaced application/test files from their authenticated predeployment copies and removes only the six release-evidence additions declared by the deployment manifest. It does not replace or edit the SQLite database, projects, source files, model weights, runtime assets, launchers, receipts, exports, or owner artifacts.

Before rollback, stop the Workshop service and verify the rollback manifest hashes. After rollback, run SQLite integrity and foreign-key checks, compare protected hashes, start the Workshop, run smoke and targeted Write regression checks, and confirm ports used only for verification are closed.

Rollback is never automatic and must be an explicit owner/deployment action.

