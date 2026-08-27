# Write Room 0.6 Owner Guide

Write Room is the first durable daily-use room in Twis Holo Workshop. It keeps
plain UTF-8 writing local, associates every writing project with an existing
Workshop project, and saves confirmed versions in the Workshop SQLite database.
It does not require an account, subscription, API key, model, GPU, or network
connection.

## Everyday workflow

1. Start the Workshop with the existing `start-workshop.bat` launcher.
2. Choose a project in the left project selector.
3. Open **Write**.
4. Choose an existing writing project or select **New writing project**.
5. Enter a title and write normally in the editor.
6. Watch the visible status:
   - **Unsaved changes — local recovery ready** means an immediate browser
     recovery copy exists but the server has not confirmed a version yet.
   - **Autosaved** or **Saved** means the SQLite-backed version succeeded.
   - A conflict or failed save is shown as a failure; it is never relabeled
     Saved.
7. Use **Named snapshot** before an important revision.
8. Use the History controls to view or compare two versions.
9. A restore always asks for confirmation and saves the current text as a
   recovery version first. **Undo last restore** is available while the
   restored version is still current.
10. Open **My Work** to find the same stable writing project, reopen it, inspect
    History, or Export it.

## Interrupted work

The editor creates two recovery layers:

- an immediate browser copy as you type;
- a debounced durable recovery draft in SQLite.

After a browser or service interruption, reopen the same writing project. If a
newer draft exists, the Workshop presents **Load recovery** and **Discard
recovery**. It does not silently replace the confirmed version.

## Bounded writing actions

The available actions are local and deterministic:

- Inspect
- Summarize
- Clean formatting
- Find repeated passages
- Show structure

An action prepares a proposal. Your text is unchanged until you explicitly
approve a modifying proposal. Findings-only proposals report results without
changing text. Rejection preserves the source. An applied change creates a
recovery version and can be rolled back while it remains current.

These actions do not use a model, network, shell, unrestricted filesystem
access, attachment, activation, or arbitrary execution. Unsupported commands
return an honest unavailable message.

## Export

Exports are local UTF-8 copies under the active project's `exports` folder:

- Plain text preserves the confirmed text bytes.
- Markdown adds the writing-project title as a heading.
- JSON contains the title, text, and export time.

The **Advanced provenance** checkbox is off by default. Only when it is selected
does JSON include internal artifact/project identity, version, content hash,
and save time. Every successful export records its path and SHA-256 in a
receipt.

## Release 0.6 limits

Release 0.6 intentionally does not include rich text, DOCX, collaborative
editing, cloud sync, hosted storage, universal natural-language routing, or an
AI writing model. The companion supports one local server process writing the
database; multiple companion processes sharing the same database are outside
the supported contract.

For ordinary beta use, the best next action is to create a new writing project,
write several real paragraphs, close and restart the Workshop once, then report
what feels clear or awkward in the owner workflow.
