# Talk Room 0.7 Contract

Release: Foundation 0.7  
Authority: the existing Workshop project, artifact, search, receipt, recovery,
and SQLite systems

## Purpose

Talk is a durable local room for ordinary language, pasted text, questions,
ideas, notes, and bounded code inspection. It is not an AI-chat simulation and
does not require an account, API key, paid provider, cloud database, GPU, or
internet connection.

## Durable identity and storage

- A Talk session is an existing Workshop `conversation` artifact with
  `schemaVersion=talk-session-v1`, a stable UUID, project ID, owner-facing
  title, current version, entry count, timestamps, and content hash.
- Ordered transcript entries are immutable. A saved change creates a new
  canonical transcript version; it never rewrites an earlier version.
- Talk uses additive tables in the existing `workshop.sqlite3` database:
  entries, versions, recovery drafts, restore operations, marked passages,
  exports, transfers, artifact relationships, and deterministic inspections.
- The artifact row remains the current projection used by My Work and search.
  There is no second database, browser-only authority, or disconnected store.
- Local mutation requests are serialized by the companion's existing
  process-wide lock. SQLite uses the existing five-second busy timeout and
  transactional mutation discipline.

## Save, recovery, and conflicts

- The UI writes browser recovery immediately when an owner edits the composer.
- It also writes debounced durable recovery to SQLite while the local companion
  is available.
- Every durable append, title change, snapshot, restore, and transfer is bound
  to the opened version. A stale base version fails without overwriting either
  state.
- Recovery is presented for review only when it is newer and bound to the
  session's current version. Loading recovery does not make it permanent;
  adding it to Talk does.
- The source field records whether an entry was typed, pasted, or deliberately
  copied from a reviewed voice draft.
- Browser storage denial, companion failure, and conflicts are visible. The UI
  does not describe failed persistence as saved.

## History, comparison, restore, and undo

- Named snapshots create immutable versions with owner-facing labels.
- History shows version number, cause or label, entry count, and time.
- Comparison is deterministic and reports added, removed, and replaced entries
  between exact versions.
- Restore creates a pre-restore recovery version before making an earlier
  transcript current.
- Restore undo is valid only while the restored version remains current. A
  later edit makes the operation stale instead of overwriting that edit.
- Restore and restore rollback write governed receipts.

## Marked passages

- The owner selects text from one transcript entry and supplies a label.
- The exact selected range, including the correct occurrence of repeated text,
  is stored against the entry and source version.
- Marking does not edit the transcript.

## Talk to Write

- The owner chooses the complete transcript or checked entries.
- Preparing a proposal creates a recovery version first and displays the exact
  title and content to be copied.
- A proposal remains `awaiting_approval` until the owner provides a non-blank
  approval note.
- A current, explicitly approved proposal creates a normal Release 0.6
  `document` artifact and version 1 without changing the Talk source.
- The transaction records a receipt and `talk_to_write` relationship.
- Awaiting and approved proposals are recovered after a browser restart.
  Proposals whose source version is no longer current are shown as stale and
  cannot execute.
- Rollback removes only the unchanged version-1 Write document created by that
  transfer. It refuses rollback if the document changed or gained unrelated
  activity. The Talk source and governed receipts remain.

## Exports

- TXT, Markdown, and JSON copies are written under the active project's export
  directory using Windows-safe bounded filenames, UTF-8, a temporary file, and
  atomic replace.
- Default JSON contains owner-facing Talk content without internal IDs, hashes,
  relationships, or schema machinery.
- Advanced provenance is included only after the owner explicitly selects it.
- Every export stores its SHA-256 and writes a receipt.
- Export paths are resolved and checked beneath the project export root.

## Deterministic code inspection

- Inspection accepts only a selected pasted code entry in Talk.
- It reports probable file type, line and character counts, imports,
  functions, classes, TODO/FIXME markers, and reliably repeated lines.
- Inspection is lexical and heuristic. It does not execute, compile, import, or
  model-evaluate the pasted code.
- The existing governed Artifact Inspection room remains the only route for an
  explicitly approved Workshop artifact. Talk links to that room without
  bypassing selection, plan, approval, or receipt gates.
- No arbitrary shell, unrestricted filesystem read, hidden network worker,
  package installation, model, automatic attachment, or activation exists.

## Voice

- Text Talk is the complete product path and never depends on voice.
- The microphone starts only after an explicit click and is always paired with
  visible listening and stop state.
- Speech-to-text is enabled only when the browser proves an on-device
  `SpeechRecognition.processLocally` implementation and reports the language
  pack as already available. Release 0.7 does not install a language pack and
  never falls back to network recognition.
- Recognition text remains a disabled-by-default review draft until the owner
  explicitly copies it into the normal composer. Raw audio is not stored.
- Read-aloud lists only browser voices whose `localService` flag is true.
  Play, pause, stop, completion, and failure are visible. A synthesis failure
  does not change Talk.
- The companion voice-capability endpoint describes this contract only; it
  does not claim the browser or operating system has a capability.

## Bounded commands

The fixed owner-language classifier may open visible actions for:

- starting Talk;
- saving or recovering;
- snapshots and comparison;
- local read-aloud and stop;
- the existing approved Artifact Inspection room;
- Talk-to-Write preview;
- export.

It does not execute a command silently. Unsupported wording returns a visible
bounded refusal and changes nothing.

## Security and network boundary

- Talk API mutations require JSON, same-origin request metadata, bounded
  request bodies, validated IDs, and canonical path containment.
- Imported text and code are rendered with `textContent`; no transcript,
  finding, diff, path, or title is assigned as HTML.
- The service worker caches only the static local shell. API requests remain
  network-only to the loopback companion and are never cached.
- Talk makes no external request and contains no provider endpoint, account,
  telemetry, tracking, cloud storage, or API-key path.
- The supported writer topology remains one local companion process per
  database.

## Deliberate limits

Release 0.7 does not add a universal agent, IDE, arbitrary tool runner, local
model manager, rich text, collaboration, cloud sync, background recording,
automatic transcription-pack installation, or network speech provider.

