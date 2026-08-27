# Decisions — Foundation Release 0.4

## D-001: Preserve the working runtime

Status: accepted. Extend the current Python/SQLite/static-JavaScript application without redesigning it, re-importing FlashRiver, or destructively migrating live data.

## D-002: Treat Worker Cards as validated declarations

Status: accepted. Cards do not activate workers, grant permissions, or create an OS sandbox. Only exact fixed cards receive harness enforcement.

## D-003: Use canonical path containment, not string prefixes

Status: accepted. Resolve Windows paths, separate read/write roots, let blocked roots win, deny parent components and unsafe Windows names, and reject sibling-prefix/symlink/junction ambiguity.

## D-004: Keep transaction evidence honest and bounded

Status: accepted. Hash-linked receipts are tamper evidence, not signatures. Recovery covers explicit files/SQLite backups, not whole-system rollback.

## D-005: Keep Artifact Compass derived and separate

Status: accepted. Workshop SQLite and source artifacts remain authoritative. Exact-hash groups retain all records and source paths; nothing is deleted, rewritten, or hidden.

## D-006: Prefer deterministic lexical inspection before AI or vectors

Status: accepted. Release 0.4 uses transparent standard-library rules. AI models, embeddings, and vector search remain out of scope.

## D-007: Do not initialize version control or publish

Status: accepted. The deployed folder has no `.git`; Release 0.4 neither initializes Git nor publishes material.

## D-008: Support only exact fixed modules

Status: accepted. The retained `reference-metadata-worker` and new `artifact-compass-inspection-worker` are fixed Python module paths. Requests cannot supply a module, executable, command, test, environment, network target, or shell fragment.

## D-009: Separate every lifecycle action

Status: accepted. Validation, planning, execution, candidate creation, approve/reject, activation/attachment, and rollback remain distinct. Passing tests produces `awaiting_approval`, never `active`.

## D-010: Bind promotion to immutable evidence and mutable generation

Status: accepted. Inspection approval explicitly binds candidate, source artifact, Worker Card, execution plan, and workspace generation hashes plus actor, note, and timestamp.

## D-011: Keep harness state outside Workshop SQLite

Status: accepted. Candidate, transaction, receipt, provenance, decision, activation/attachment, and rollback evidence remain under `data/worker_harness/`.

## D-012: Define activation narrowly

Status: accepted. Reference activation is registry-only. Inspection activation adds a report attachment descriptor. Neither executes at startup or grants permissions.

## D-013: Recognize only importer-defined public-safe roots

Status: accepted. Release 0.4 does not infer that an entire project is public. Only FlashRiver intake `docs` roots are allowlisted. Private/visual siblings, manifests outside `docs`, archives, databases, reparse paths, unsupported types, and out-of-root paths fail closed.

## D-014: Treat artifact content as inert data

Status: accepted. The worker never imports code, evaluates expressions, renders HTML/Markdown, follows links, or treats embedded instructions as commands. “Likely document purpose” is a labeled heuristic, not a fact.

## D-015: Attach reports without changing artifact authority

Status: accepted. Attachment does not update artifact bytes, Workshop SQLite, review status, permissions, or startup execution. Rollback marks the attachment rolled back and restores only bounded harness output.
