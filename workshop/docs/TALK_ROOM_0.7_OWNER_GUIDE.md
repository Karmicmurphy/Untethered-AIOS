# Talk Room 0.7 Owner Guide

Talk is a durable local place for thoughts, notes, questions, ideas, pasted
text, and small code excerpts. It works as a text room without an account,
subscription, API key, cloud database, GPU, or internet connection.

## Begin and continue a Talk

1. Start the Workshop normally and choose the project in the left sidebar.
2. Open **Talk**.
3. Choose **New Talk session**, give it a useful title, and optionally add the
   first entry.
4. Type or paste in **New Talk entry**, choose the entry type if useful, and
   select **Add to Talk**.
5. Watch the status beside the title. It says when the Talk is saving, saved,
   recoverable, conflicted, or unavailable.
6. You can leave and later find the same session in either **Talk** or
   **My Work**. Its identity, project, title, entries, and history stay stable.

If an interruption leaves an unsaved composer draft, Talk presents a recovery
banner. Review it, then load it or discard it. Loading places it back in the
composer; **Add to Talk** makes it permanent.

## Preserve and revisit

- **Named snapshot** saves a meaningful point without changing the transcript.
- **History** shows saved states. Choose an earlier and later version, then
  **Show what changed**.
- **Restore** first preserves the current state, then restores the chosen
  version. **Undo restore** is available while no later edit has replaced it.
- To keep a particular phrase, select text inside one transcript entry and
  choose **Mark selected passage**.

## Copy useful material to Write

1. Choose the whole transcript or check the entries you want.
2. Select **Preview Write document**.
3. Review the exact copy and title. The original Talk does not change.
4. Add a short approval note.
5. Select **Approve and create Write document**.

The new item is a normal Write document in My Work. **Roll back created
document** removes only that unchanged transfer-created document. If it has
since been edited, rollback refuses rather than deleting unrelated writing.

## Export

Choose Plain text, Markdown, or JSON, then **Export a copy**. JSON hides
internal provenance by default. Expand **Advanced provenance** only when you
deliberately want internal identity, version, hash, and relationship evidence.

## Voice truth

Text Talk always works independently of voice.

- **Start local dictation** is disabled unless the browser proves an installed
  on-device speech-recognition capability. Release 0.7 does not use network
  recognition or install language packs.
- When local dictation is available, listening begins only after your click.
  Stop is visible, raw audio is not saved, and the transcript remains a review
  draft until you deliberately copy it into the composer.
- **Read Talk aloud** uses only voices the browser identifies as installed
  locally. Pause, stop, completion, and failure are visible.
- A voice failure never changes or blocks the saved text.

## Pasted code

Select a code entry and choose **Inspect selected code entry** for a small,
deterministic structural report. It does not run the code or use an AI model.
For a governed Workshop artifact, choose **Open approved Artifact Inspection**;
the existing selection, plan, approval, and receipt gates remain in force.

## Commands

The command box recognizes a small fixed set of Talk actions and only opens the
matching visible control. It is not a shell or universal assistant. Unsupported
requests are refused without changing the session.

