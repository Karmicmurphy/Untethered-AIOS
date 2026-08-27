# Foundation Release 0.12 — Visual Brief Builder

Release 0.12 adds the first governed Image Room preparation tool without changing the existing image canvas or generating an image.

`visual-brief-builder` is one fixed deterministic worker. It accepts zero to four explicitly selected registered readable text sources and optional owner-entered visual notes. At least one registered source or nonblank visual notes are required. Registered sources retain owner-selected order and exact SHA-256 values. Visual notes receive a deterministic `visual-notes:<SHA-256>` identity and remain temporary governed job input rather than a permanent source.

The result is a `builder-output-v1` visual production brief with a fixed visual-purpose preset, bounded optional controls, explicit placeholders for unresolved creative decisions, a clean manual-use image prompt, exclusion guidance, human-artist notes, source preservation, and an unambiguous statement that no image was generated or submitted.

Plan approval, deterministic preparation, result approval, inactive saving, export, and rollback remain separate. A saved result is one inactive `visual-brief-draft`; TXT, Markdown, and JSON exports remain explicit and local. Registered sources receive provenance relationships and remain unchanged. No image provider, network request, URL retrieval, model execution, shell, attachment, activation, publication, or promotion is available.

Release 0.12 advances SQLite `user_version` from 11 to 12 transactionally without changing table schema or replacing the database.
