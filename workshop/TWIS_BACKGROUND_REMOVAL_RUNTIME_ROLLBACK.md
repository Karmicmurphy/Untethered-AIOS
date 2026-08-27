# TWIS Background Removal Runtime — Rollback

The rollback package is stored outside the live Workshop under:

`C:\TWIS_FLASHRIVER_REVIEW_READY\background-removal-runtime-work\rollback`

It contains exact predeployment copies of every replaced application file and an explicit list of every application/runtime addition. It does not copy, reset, or remove the Workshop database, projects, sources, artifacts, receipts, exports, or the existing FFmpeg runtime.

## Rollback behavior

1. Stop only the TWIS companion bound to `127.0.0.1:8787`.
2. Validate the deployed scope against the deployed manifest.
3. Restore each replaced application file from the hash-verified rollback original.
4. Remove only additions declared by the release scope, including the exact adjacent directory `runtime/background-removal/opencv-grabcut/4.14.0.94`.
5. Verify every restored hash and every expected absence.
6. Verify SQLite integrity, foreign keys, `user_version`, protected source trees, and the pre-existing FFmpeg runtime.
7. Start the unchanged Workshop service and run health/UI checks.

No broad directory deletion is permitted. Runtime removal is allowed only after resolving the exact runtime target beneath `C:\TWIS_FLASHRIVER_REVIEW_READY\runtime\background-removal` and matching the deployed manifest.

The rollback simulation applies and reverses the exact candidate scope in an isolated tree before owner deployment approval.
