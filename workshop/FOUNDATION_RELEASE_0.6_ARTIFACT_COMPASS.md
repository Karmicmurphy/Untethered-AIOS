# Foundation Release 0.6 — Focused Artifact Compass

Date: 2026-07-23  
Scope: only the technologies needed for the Write Room daily-use slice

## Authority map

The deployed Release 0.5 Workshop, its SQLite artifact/receipt store, project
folders, guarded worker boundaries, service worker, tests, and launcher remain
authoritative. Release 0.6 extends those systems. It does not introduce another
document database, a browser-only document authority, a cloud authority, or an
AI dependency.

Official references checked:

- HTML textarea behavior and mobile/browser editing attributes:
  https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/textarea
- Input events for direct user edits:
  https://developer.mozilla.org/en-US/docs/Web/API/Element/input_event
- Page Visibility lifecycle:
  https://developer.mozilla.org/en-US/docs/Web/API/Page_Visibility_API
- WCAG status messages:
  https://www.w3.org/WAI/WCAG22/Understanding/status-messages
- WAI-ARIA modal dialog pattern:
  https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/
- WCAG 2.2 guidance applied to mobile:
  https://www.w3.org/TR/wcag2mobile-22/
- Python `difflib`:
  https://docs.python.org/3.12/library/difflib.html
- SQLite write-ahead logging:
  https://www.sqlite.org/wal.html
- SQLite busy timeout:
  https://www.sqlite.org/pragma.html#pragma_busy_timeout
- SQLite public-domain status:
  https://www.sqlite.org/copyright.html

## Dependency decisions

| Decision | Technology or approach | Release 0.6 reason |
|---|---|---|
| KEEP | Existing SQLite `artifacts`, FTS, projects, and receipts | One durable authority; existing provenance and My Work integration remain intact. |
| KEEP | SQLite tables dedicated to Write versions, recovery, proposals, restores, and exports | This is a schema extension inside the existing authority, not a disconnected store. |
| KEEP | Native `<textarea>` and browser `input` events | Reliable native cursor, selection, paste, undo, redo, spellcheck, desktop, and mobile behavior without an editor framework. |
| KEEP | Immediate `localStorage` recovery plus debounced SQLite recovery | Browser storage covers the instant before a request completes; SQLite provides durable restart recovery. Neither silently becomes the confirmed version. |
| KEEP | Python standard-library `difflib.SequenceMatcher` | Produces deterministic line operations without a new package. The owner UI converts operations into Before/After changes. |
| KEEP | Native `<dialog>` and `role="status"` | Explicit restore decisions and perceivable save-state changes with no UI dependency. |
| KEEP | Existing service worker, with a v6 cache | Offline shell remains available and old Workshop caches are retired. API requests remain network-only to the local companion and are never cached. |
| KEEP | Standard-library UTF-8 export and `os.replace` | Local, atomic TXT/Markdown/JSON exports without a package or network call. |
| TEST | SQLite WAL behavior with the bundled SQLite 3.49.1 | SQLite documents a rare WAL-reset defect in versions before 3.51.3 under concurrent write/checkpoint conditions. Release 0.6 serializes local HTTP mutations, initializes WAL once, sets a 5-second busy timeout, and runs threaded write plus integrity tests. |
| TEST | Browser storage quota or storage denial | Immediate recovery handles storage exceptions visibly and keeps Save now available; durable recovery remains the primary restart path. |
| TEST | Visibility changes, reload, browser close, and process restart | The owner lifecycle uses a disposable real browser and a disposable local database. |
| TEST | Narrow/mobile layout and native dialog focus | Verified at desktop and mobile viewport widths in the browser acceptance pass. |
| CUT | Third-party diff libraries | Standard-library line comparison is sufficient and avoids bundle, license, and maintenance cost. |
| CUT | Rich editor frameworks | They add content-model conversion and cursor risk without helping the Release 0.6 plain-writing goal. |
| CUT | A separate document database or browser-only source of truth | It would split identity, receipts, search, recovery, and My Work. |
| CUT | Telemetry, hosted storage, remote autosave, and automatic uploads | They violate local-first authority and are unnecessary. |
| REJECT | `contenteditable` as the primary editor | It would introduce inconsistent HTML, paste, selection, and serialization behavior for no required Release 0.6 benefit. |
| REJECT | Silent AI revision or arbitrary worker execution | The fixed Write actions are deterministic, local, bounded, source-preserving, and explicitly approved. |
| REJECT | Shell, network, unrestricted file access, automatic attachment, or automatic activation | None is needed for writing, comparison, recovery, proposals, or export. |
| DEFER | DOCX export | TXT, Markdown, and JSON meet the release. DOCX would add a dependency and a document-format validation obligation. |
| DEFER | Rich text, collaborative CRDTs, cloud sync, and universal natural-language routing | These expand authority and failure modes beyond the daily-use slice. |

## SQLite risk treatment

The Python runtime reports SQLite 3.49.1. The official WAL documentation now
describes a rare WAL-reset corruption defect fixed in SQLite 3.51.3 and
selected backports. The Workshop is a single local process, so Release 0.6
uses one process-wide re-entrant mutation lock around every POST and DELETE,
opens connections with a five-second timeout, applies `busy_timeout=5000`,
and performs schema/WAL initialization once per database path. This prevents
concurrent local writers in the supported server while retaining the
foundation's WAL behavior.

This is a bounded mitigation, not a claim that SQLite 3.49.1 is globally
certified safe under every multi-process workload. The Workshop does not
support multiple companion processes writing the same database.

## Result

No new runtime dependency, paid service, API key, model, network worker, or
license obligation was added. The selected implementation is the smallest
path that preserves Release 0.5 authority while making Write useful.
