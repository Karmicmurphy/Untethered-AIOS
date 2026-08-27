# Foundation Release 0.9 — Universal Handoff and Prompt Builder

Release 0.9 extends the accepted Release 0.8 Worker Kit with exactly two fixed deterministic builders. It preserves the four existing workers and their established lifecycle.

## Added

- Handoff Proposal Builder with four allowlisted destination profiles and fourteen required sections.
- Prompt Proposal Builder with four allowlisted destination profiles and eleven required sections.
- `builder-output-v1` text-and-metadata binding.
- explicit multi-source selection with ordered IDs and SHA-256 values;
- stale-plan and stale-result blocking;
- separate plan approval, generation, result approval, save, export, and rollback gates;
- one inactive `handoff-draft` or `prompt-draft` with source relationships;
- explicit UTF-8 plain-text and JSON export in the bounded Workshop export location;
- desktop and narrow-screen builder workspace with entry actions from My Work, Talk, Write, Artifact Inspection, and approved worker results;
- transactional SQLite `user_version` migration from 8 to 9 without replacing the database.

## Boundaries

No external request, provider call, arbitrary filesystem path, directory scan, shell/Python execution, package action, attachment, activation, promotion, autonomous chain, or automatic export is added. Original selected sources are read-only and reverified at execution, result approval, save, and export.

See `docs/BUILDER_OUTPUT_V1_CONTRACT.md` and `docs/RELEASE_0.9_OWNER_GUIDE.md`.
