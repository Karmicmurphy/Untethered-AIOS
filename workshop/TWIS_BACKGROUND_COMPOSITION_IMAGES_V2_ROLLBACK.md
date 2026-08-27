# TWIS Background Composition — Rollback

Status: PREPARED FOR VERIFIED CANDIDATE

Rollback is exact-scope and application-only:

- restore every declared replacement from the external rollback originals;
- remove only additions declared by the candidate scope;
- do not touch the Workshop database, project files, registered sources, media bytes, receipts, runtime, model state, launchers, or credentials;
- verify every restored hash and every removed addition;
- verify SQLite integrity, foreign keys, service health, and protected trees after rollback.

The executable rollback script and original bytes are stored outside the live Workshop at:

`C:\TWIS_FLASHRIVER_REVIEW_READY\background-composition-images-v2-work\rollback`

Do not run rollback unless this exact candidate is deployed and the owner requests or requires restoration.

