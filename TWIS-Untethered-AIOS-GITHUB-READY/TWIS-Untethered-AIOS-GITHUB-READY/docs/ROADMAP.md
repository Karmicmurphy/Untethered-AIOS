# Untethered AIOS Roadmap

## Phase 0 — Authenticate

- capture exact verified Workshop baseline;
- populate `workshop/`;
- preserve protected local authority;
- establish tests.

## Phase 1 — Kernel

- real process table;
- cooperative scheduler;
- waiting/wake;
- cancellation;
- process tree;
- audit receipts;
- capability scopes.

## Phase 2 — Workshop capability adapters

Start with one owner-visible path at a time.

Candidate order:

1. artifact read/write;
2. Music render/loop actions;
3. Build bounded file inspection;
4. Images bounded local transform adapter;
5. Explore research artifact intake.

Existing Workshop behavior remains available.

## Phase 3 — Resource governor

- hardware discovery;
- runtime discovery;
- local model inventory;
- task/capability routing;
- budgets;
- fallback based on verified capability.

## Phase 4 — Memory

- working context;
- artifact retrieval;
- episodic receipts;
- resumable jobs;
- optional embedding backend only if useful.

## Phase 5 — Isolation

Evaluate, do not assume:

- subprocess isolation;
- OS account/container boundaries;
- WASM tools;
- restricted network lanes.

Adopt only where measurable value exceeds complexity.

## Phase 6 — Autonomy

Only bounded autonomy:

- plan;
- spawn;
- perform;
- verify;
- receipt;
- recover.

Human approval remains at permanent/destructive/publish/deploy boundaries.
