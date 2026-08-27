# Artifact Compass — Kernel V0.2 Bounded Reality Sweep

Date: 2026-08-27

Candidate branch: `bootstrap/workshop-baseline`

Phase 0 commit: `c3ce1cf`

Decision boundary: `KERNEL V0.2 — REAL PROCESS LIFECYCLE`

## Pass 1 — Reality baseline

- The authenticated Workshop snapshot contains 293 code-safe files and matches the authoritative source at tree SHA-256 `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`.
- Imported Workshop verification passed: 249 Python tests and 86 JavaScript/UI tests, plus all declared JavaScript syntax checks.
- Untethered bootstrap verification passed: 13 tests.
- Existing AIOS mechanisms: Python `ProcessState`, PID/parent PID, a FIFO `deque`, cooperative `Step`, event queues, capability grants, path resolution, in-memory receipts, and deterministic `FakeModel`.
- Verified missing contracts: durable process-table storage, authoritative transition validation, restart/recovery behavior, deterministic waiting order, suspended-wait semantics, worker-proof grant immutability, narrow child delegation, structured mutation receipts, durable traces, and current Windows path-policy denial cases.
- Existing Workshop mechanisms worth salvaging: transition matrices, atomic replace-after-flush persistence, interrupted-write detection, Windows path-component denial, workspace generations, fixed capability metadata, and hash-linked receipt verification.

Measured machine:

- Windows 10 Home 10.0.19045 build 19045.
- AMD A4-6210 APU, 4 logical processors.
- 7,447,904,256 bytes RAM (about 6.94 GiB).
- AMD Radeon R3 integrated graphics, reported 1 GiB adapter RAM.
- Python 3.12.10; embedded SQLite 3.49.1; Node 24.12.0.
- No Rust, WASM, model, provider, or separate database runtime is required for this successor.

## Pass 2 — Better question rewrite

What exact durable scheduling, transition, event-wake, delegation, path-scope, and evidence mechanisms are missing from the verified Python bootstrap; can Python standard-library primitives plus a local SQLite process table prove them deterministically on this Windows machine without adding a framework, provider, model, or new authority?

## Pass 3 — Official source map

- [Python `collections.deque`](https://docs.python.org/3.12/library/collections.html#collections.deque): approximately O(1) append/pop behavior supports the existing deterministic FIFO ready queue.
- [Python `asyncio` Tasks](https://docs.python.org/3.12/library/asyncio-task.html#task-object): Tasks are cooperatively scheduled, but introduce event-loop/coroutine semantics and cancellation behavior not required by the current synchronous proof.
- [Python 3.12 `sqlite3`](https://docs.python.org/3.12/library/sqlite3.html): local serverless persistence with explicit transaction control; Python remains the only runtime dependency.
- [SQLite atomic commit](https://www.sqlite.org/atomiccommit.html): rollback journals provide crash-recovery and all-or-nothing transaction behavior.
- [SQLite WAL documentation](https://www.sqlite.org/wal.html): WAL is single-host and more concurrent, but the current advisory identifies a rare reset race in versions through 3.51.2 under concurrent write/checkpoint conditions.
- [Python `pathlib.Path.resolve`](https://docs.python.org/3.12/library/pathlib.html#pathlib.Path.resolve) and [`os.path.commonpath`](https://docs.python.org/3.12/library/os.path.html#os.path.commonpath): canonicalization and valid-path containment primitives.
- [SQLite public-domain status](https://www.sqlite.org/copyright.html) and [Python PSF licensing](https://docs.python.org/3.12/license.html): free, local, redistribution-compatible foundations.

Freshness: all sources were read on 2026-08-27 from official Python or SQLite documentation.

## Pass 4 — Open implementation map

The smallest open implementation is the existing Python package plus a repository-owned `ProcessTable` abstraction with in-memory and SQLite implementations. No external service or library is needed. Workshop patterns will be reimplemented narrowly; the Workshop platform itself will not be imported as kernel authority.

## Pass 5 — Adjacent/frontier sweep

- Structured-concurrency ideas from `asyncio.TaskGroup` reinforce parent/child ownership, but an event-loop migration does not improve the bounded deterministic proof.
- Workshop promotion/transaction code proves explicit transitions, atomic evidence replacement, stale-generation denial, and receipt chaining. These mechanisms transfer; the whole harness does not.
- SQLite is already proven in Workshop and fits the machine. A vector database or remote workflow engine solves no verified V0.2 gap.
- WASM or subprocess isolation may later strengthen hostile-code boundaries, but V0.2 runs cooperating deterministic test workers and does not claim hostile-process isolation.

Stopping condition: another pass is unlikely to replace the direct Python/SQLite successor or change its proof criteria.

## Passes 6–8 — Stack position, filters, and classification

| Candidate or mechanism | Exact stack position | Class | Current decision |
|---|---|---:|---|
| Python 3.12 standard-library core | kernel/runtime | KEEP | Already installed, free, local, low-overhead, and verified. |
| `deque` FIFO + explicit `Step` protocol | scheduler | KEEP | Preserve deterministic cooperative scheduling and real yield/requeue. |
| Explicit transition matrix | kernel/process authority | KEEP | Salvage the proven Workshop invariant style; terminal states cannot silently restart. |
| SQLite rollback-journal `ProcessTable` | kernel persistence/evidence | TEST | Prove atomic process/transition/receipt persistence, reopen, monotonic PID, and crash recovery. No server or new dependency. |
| Workshop-derived Windows canonical path decisions | capability adapter/security boundary | TEST | Prove UNC, parent traversal, alternate-data-stream/reserved-name, different-drive, junction, and allowed-root behavior. |
| Structured mutation receipt + hash-linked trace | evidence/receipt layer | TEST | Prove actor PID/parent, capability, canonical target, input/output hashes, result/error, sequence, and persistence. |
| Mutable public process record containing runner authority | kernel API | CUT | Separate serializable process state from in-memory runner bindings; workers receive a read-only view. |
| Flat JSON file as the process table | kernel persistence | REJECT | Atomic replacement is salvageable, but querying, uniqueness, transition transactions, and concurrent safety would be reimplemented poorly. |
| SQLite WAL mode on embedded SQLite 3.49.1 | kernel persistence configuration | REJECT | Unneeded concurrency and the current official WAL-reset advisory make rollback journaling safer for this single-kernel proof. |
| `asyncio`/TaskGroup migration | scheduler/runtime | DEFER | Useful if real async I/O becomes a measured need; migration is unnecessary for deterministic V0.2. |
| External agent/workflow framework | external optional adapter | REJECT | Adds authority, dependencies, and lifecycle semantics while duplicating the bounded kernel contract. |
| Rust/Tokio rewrite | kernel/runtime | DEFER | No measured CPU or safety bottleneck justifies a language/toolchain migration. |
| WASM runtime | isolation boundary | DEFER | Revisit in Phase 5 only for a proven hostile-tool isolation gap. |
| Vector database | memory | DEFER | No retrieval-scale failure exists in this successor. |
| Large local model or provider integration | model governor/external adapter | DEFER | Scheduling and security tests use deterministic local fakes; no inference dependency is needed. |

Reality filters:

- Hardware: the selected design is comfortable on the measured low-power CPU and limited RAM/GPU.
- Windows: Python, SQLite rollback journaling, `Path.resolve`, and `commonpath` are available now.
- Privacy/network/cost: runtime operation is offline, free, and local; research was the only network use.
- Legal: Python is PSF-licensed; SQLite deliverables are public domain.
- Authority: process state, grants, receipts, and persistence remain repository/kernel-owned; no model or framework becomes authoritative.

## Pass 9 — Salvage cards and proof plans

### SQLite process table

- Source: Python/SQLite official documentation and verified Workshop SQLite use.
- Stack position: kernel persistence and evidence.
- Classification: `TEST`.
- Salvage: transactional rows, uniqueness, foreign keys, rollback-journal recovery; not the Workshop database/schema.
- Proof: in-memory and file-backed stores satisfy one contract; reopen retains rows/receipts; PID allocation remains monotonic; interrupted `RUNNING` state becomes observable failure/recovery evidence; `PRAGMA integrity_check` returns `ok`.
- Adoption threshold: all persistence/failure tests pass with no external dependency.

### Canonical Windows path policy

- Source: Python path documentation plus authenticated Workshop path-policy behavior/tests.
- Stack position: capability security boundary.
- Classification: `TEST`.
- Salvage: explicit Windows component denial and normalized containment; not the Workshop foundation package.
- Proof: valid in-root operations pass; traversal, sibling-prefix, UNC, ADS/reserved/trailing-dot-space, wrong drive, and junction escape fail closed.
- Adoption threshold: success and denial tests pass without widening any read/write root.

### Structured receipt/trace

- Source: authenticated Workshop transactions/receipts and repository receipt skill.
- Stack position: evidence layer.
- Classification: `TEST`.
- Salvage: sequence, previous-hash binding, canonical JSON hashing, transition/action detail.
- Proof: governed mutation, denial, spawn, wake, cancellation, completion, and crash create deterministic ordered receipts that survive SQLite reopen and verify as a chain.
- Adoption threshold: tamper/shape/order tests pass and no secret/full-content capture is introduced.

## Pass 10 — Direct successor synthesis

Implement Kernel V0.2 in the existing Python package:

1. add `ProcessTable` with in-memory and SQLite rollback-journal implementations;
2. separate serializable records from runner bindings and expose read-only worker views;
3. enforce one transition matrix and deterministic FIFO ready/wait queues;
4. implement wake delivery, suspended-wait semantics, cancellation cleanup, and restart crash evidence;
5. allow only same-or-narrower child grants through kernel authority;
6. add structured capability requests, canonical Windows path enforcement, and mutation receipts;
7. persist hash-linked receipts/traces and keep `FakeModel` deterministic;
8. prove every success, denial, recovery, and failure path with unit tests.

No-broadening statement: this decision adds no model, provider, network access, framework, Rust, WASM, vector database, Workshop room, UI redesign, live integration, or production deployment.

**PASS — ARTIFACT COMPASS bounded reality sweep complete; direct Kernel V0.2 implementation selected**
