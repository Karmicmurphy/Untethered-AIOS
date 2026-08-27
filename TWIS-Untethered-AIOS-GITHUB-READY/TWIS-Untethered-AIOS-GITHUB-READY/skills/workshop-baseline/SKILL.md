# Skill: Workshop Baseline Authentication

Use this skill before importing or refreshing `workshop/`.

## Authority

The local Workshop is the source authority:

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

GitHub may lag it.

## Procedure

1. Inspect local Workshop status.
2. Run `scripts/authenticate_workshop.py`.
3. Review excluded files.
4. Run relevant live/local verification.
5. Copy only code-safe files into `workshop/`.
6. Authenticate the copied snapshot.
7. Compare manifests.
8. Record source and copied hashes.
9. Do not mutate the source Workshop.

If manifests differ unexpectedly, investigate. Never repair by guessing from memory.
