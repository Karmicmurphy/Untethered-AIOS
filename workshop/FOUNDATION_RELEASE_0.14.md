# Foundation Release 0.14 — Sovereign-HUD / Lattice-OS Shell

Release 0.14 is a visual shell and governed interface integration release. It adds no worker, builder, provider, model, execution engine, database schema, or room capability.

The shell uses sharp one-pixel geometry, compact room identity, a real-state status band, an owner-facing Home control deck, a Recover control deck, an optional instant split workspace, visible keyboard focus, and a reduced-motion guarantee. The vocabulary is read/verified green, compute/active blue, dotted ghost/proposed boundaries, solid approved boundaries, and red quarantine treatment only when real stale, hash-mismatch, failed, invalid, or conflict state is present.

Home derives the active project, registered-source count, artifact count, inactive-draft count, pending governed jobs, recent project receipt, local companion availability, database-open availability, and Workshop release from existing local APIs. Anything not exposed by an existing API is labeled `NOT EXPOSED`, `UNKNOWN`, or `NONE SELECTED`.

Recover derives interrupted jobs, rollback eligibility, stale-source conflict count, and recent recovery receipts from existing job and receipt APIs. Protected-manifest and SQLite integrity details remain explicitly `NOT EXPOSED BY UI API`; the shell does not invent them.

The existing room IDs, selectors, routes, backend authority, database, workers, builders, approval gates, receipts, exports, recovery, service worker, and source hashes remain authoritative and unchanged in behavior.
