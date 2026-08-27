# Write Room 0.6 Contract

## Owner-facing project

A writing project is an existing Workshop `document` artifact with:

- one stable UUID;
- one existing Workshop project ID;
- owner-facing title and UTF-8 text;
- created, modified, and last-saved timestamps;
- SHA-256 of the confirmed text;
- current version number and version count;
- `write-project-v1` payload marker and origin;
- optional recovery draft;
- durable versions, proposals, restores, exports, and receipts.

The artifact row remains the current document authority. Write-specific tables
record lifecycle evidence. Browser storage is only a last-mile recovery copy;
it is never a confirmed saved version.

## Durable tables

| Table | Purpose |
|---|---|
| `write_versions` | Immutable ordered title/text versions, cause, actor, label, parent relationship, and content hash. |
| `write_recovery_drafts` | At most one newer unconfirmed recovery draft per writing project. |
| `write_proposals` | Source-bound deterministic plans, proposed content, human-readable comparison, findings, decision, and apply/rollback relationships. |
| `write_restore_operations` | Target, pre-restore recovery, applied restore, and optional rollback versions. |
| `write_exports` | Export format, local path, content hash, provenance choice, and timestamp. |

Schema creation is additive and idempotent. It does not rewrite existing
artifacts, reviews, receipts, source archives, or Worker Harness evidence.
SQLite `user_version` becomes `6`.

## Save and recovery rules

1. The editor writes a browser recovery copy immediately on input.
2. A debounced request upserts the durable recovery draft.
3. Autosave or Save now requires the version that was current when editing
   began.
4. A stale base version returns `write_version_conflict` and does not overwrite
   either version.
5. A changed save creates one immutable version, updates the artifact current
   state, clears recovery, updates search, and writes a receipt.
6. An unchanged save clears matching recovery but does not make a useless
   version.
7. Opening a document presents a newer recovery draft as a choice. It does not
   silently replace the confirmed version.

## Version, restore, and rollback rules

- Manual saves, autosaves, named snapshots, restores, worker applications, and
  rollbacks state their cause.
- A named snapshot creates a durable version even when text is unchanged.
- A restore requires explicit confirmation.
- Restore first writes a pre-restore recovery version, then writes the restored
  version and receipt.
- Restore rollback is allowed only while the restored version is still current.
  Newer saved work makes automatic rollback stale rather than overwriting it.

## Bounded Write action contract

Supported deterministic actions:

- `inspect`
- `summarize`
- `clean_formatting`
- `repeated_passages`
- `structure`

Every action plan declares:

- fixed local worker name;
- exact action;
- no network;
- no AI model;
- no shell;
- no source mutation;
- explicit decision required.

The proposal binds to the current version number and text hash. Findings-only
actions never create a changed version. A modifying proposal remains
`awaiting_approval` until an explicit approve or reject request. Approval first
creates a worker-recovery version and then the applied version. Rejection
preserves the source. Rollback is possible only while the applied version is
current.

The constrained command box also maps owner language to existing bounded room
actions for compare, restore, export, snapshot, and recovery. Unsupported
language returns an honest unavailable message and performs no action.

## Export contract

Supported formats are TXT, Markdown, and JSON. All are UTF-8, use
Windows-safe filenames, are written through a temporary file followed by
atomic replace, and receive an export receipt.

Default JSON contains title, text, and export time. Internal artifact/project
identifiers and the saved version hash appear only when the owner chooses the
advanced provenance option.

## API summary

| Method and route | Purpose |
|---|---|
| `GET /api/write-projects?projectId=...` | List owner-facing Write summaries for My Work and the Write picker. |
| `POST /api/write-projects` | Create and confirm version 1. |
| `GET /api/write-projects/{document}` | Reopen current content, history, recovery, and recent proposals. |
| `POST /api/write-projects/{document}/recovery` | Upsert unconfirmed recovery. |
| `DELETE /api/write-projects/{document}/recovery` | Explicitly discard recovery. |
| `POST /api/write-projects/{document}/save` | Manual, automatic, or recovery save with optimistic version binding. |
| `POST /api/write-projects/{document}/snapshot` | Create a named version. |
| `GET /api/write-projects/{document}/compare` | Return deterministic line operations for two versions. |
| `POST /api/write-projects/{document}/restore` | Confirmed recovery-first restore. |
| `POST /api/write-restore-operations/{operation}/rollback` | Roll back a still-current restore. |
| `POST /api/write-projects/{document}/proposals` | Create a source-bound deterministic proposal. |
| `POST /api/write-proposals/{proposal}/decision` | Explicit approve or reject. |
| `POST /api/write-proposals/{proposal}/rollback` | Roll back a still-current applied proposal. |
| `POST /api/write-projects/{document}/exports` | Create a receipt-backed local export. |

Technical identifiers exist in these internal routes and receipts, but the
ordinary Write and My Work interfaces never require the owner to enter them.
