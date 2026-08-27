# Foundation Release 0.14.2 — New Idea Inline Room Form

Release 0.14.2 replaces the New Idea room's inherited browser-prompt handoff with an inline Workshop intake station. It is a bounded presentation and local-workflow refinement on the accepted Release 0.14.1 room system.

The form records an owner-entered title, an exact plain-text quick note, and an optional real project selection. Saving creates one existing-style artifact with kind `idea` and authority state `DRAFT`. It remains inactive and appears in My Work. The generic artifact endpoint supplies the existing `artifact.upsert` receipt; no worker, provider, publication, activation, or new persistence subsystem is involved.

An unassigned idea uses the active project only as its required Workshop storage scope and records no explicit project association in its payload. Choosing a project uses that real project as both storage scope and association. Cancel clears the unsaved form and returns to Crossroads without a write.

There is no database migration. SQLite `user_version` remains 13. Release 0.15 functionality is not included.
