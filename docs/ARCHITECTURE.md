# Untethered AIOS Architecture

## Product idea

Untethered AIOS is a control plane beneath Twis Holo Workshop.

```text
OWNER
  |
  v
TWIS HOLO WORKSHOP UI
  |
  v
UNTETHERED AIOS KERNEL
  |--- Process Table
  |--- Scheduler
  |--- Event Bus
  |--- Capability Registry
  |--- Resource Governor
  |--- Memory
  |--- Audit / Recovery
  |
  +--> disposable bounded workers
         |-- music
         |-- image
         |-- video
         |-- research
         |-- build
         |-- write
         `-- future capabilities
```

## Kernel responsibilities

The kernel owns coordination, not creative authority. Kernel V0.2 implements
the process lifecycle, deterministic scheduler, event wake path, capability
scope enforcement, process persistence abstraction, and receipt chain. Resource
budgets, model discovery, and hostile-process isolation remain later work.

It should eventually provide:

- process IDs and lifecycle state;
- cooperative scheduling;
- waiting/wake events;
- capability grants;
- path/resource/network scopes;
- resource budgets;
- model/runtime discovery;
- worker crash isolation;
- receipts and audit log;
- restart/recovery checkpoints.

## Process lifecycle

Canonical states:

```text
NEW
READY
RUNNING
WAITING
SUSPENDED
DONE
FAILED
CANCELLED
```

A process cannot directly edit its permissions.

Kernel V0.2 enforces one transition matrix:

```text
NEW -> READY
READY -> RUNNING | SUSPENDED | FAILED | CANCELLED
RUNNING -> READY | WAITING | SUSPENDED | DONE | FAILED | CANCELLED
WAITING -> READY | SUSPENDED | FAILED | CANCELLED
SUSPENDED -> READY | WAITING | FAILED | CANCELLED
DONE | FAILED | CANCELLED -> terminal
```

The FIFO ready queue and per-topic FIFO wait queues are deterministic. A real
yield returns `RUNNING -> READY` and requeues the PID. An event wakes only the
matching wait queue. If a waiting process is suspended when its event arrives,
the kernel records a pending wake and makes it READY only after resume.

### Process table and restart behavior

`ProcessTable` separates serializable process truth from in-memory runner
bindings. `InMemoryProcessTable` is the deterministic unit-test/default store.
`SQLiteProcessTable` is the persistent implementation and uses one local SQLite
file, serialized transactions, `synchronous=FULL`, foreign keys, and rollback
journal mode. WAL is deliberately not enabled in V0.2.

PIDs remain monotonic across a SQLite reopen. READY, WAITING, and SUSPENDED
records are reconstructed. A record found in RUNNING state after reopen is
failed with explicit `KernelRestart` crash evidence; it is never silently run
again. A persisted nonterminal process must rebind the exact recorded
`runner_id` before execution.

## Capability model

A worker receives explicit grants such as:

```text
artifact.read:/project/123
artifact.write:/project/123/output
audio.render
music.loop.launch
network:https://allowed.example
```

A Kernel V0.2 grant combines:

- capability name;
- one or more allowed scopes.

Resource budgets and grant expiry remain future contracts.

Kernel V0.2 uses structured `CapabilityRequest` values. Capability definitions,
not worker requests, declare whether a call is a mutation and which argument is
the scoped resource. Windows paths are made absolute and canonical before
containment; UNC paths, parent traversal, alternate data streams, reserved
names, trailing dot/space components, sibling-prefix escapes, and other-drive
escapes fail closed. Child grants must be equal to or narrower than parent
grants.

Workers receive a copied process view. Metadata changes and child spawning go
through kernel methods, so supported worker APIs cannot mutate grants or the
process table directly. This is an application-level boundary for cooperating
workers, not hostile-code sandboxing.

## Receipts and traces

Every spawn, state transition, capability denial/call/mutation, event publish,
cancellation, completion, failure, and restart recovery is represented in an
ordered receipt. Receipts bind sequence, previous receipt hash, actor PID,
parent PID, action, canonical target when applicable, timestamp, and bounded
detail. Capability receipts store argument names and input/output hashes rather
than full content. SQLite-backed receipts survive reopen, and a corrupt chain
fails closed during kernel construction.

## Worker model

Workers should be small and disposable.

They may call capabilities, produce artifacts, emit events, and die.

Long-lived truth belongs in artifacts, receipts, project state, and governed memory—not in the worker's hidden conversation state.

## Model governor

Do not route based only on whether a model says "I am not sure."

Future routing should consider:

- task capability;
- available installed models;
- RAM/VRAM;
- expected latency;
- context requirement;
- previous failure;
- privacy lane;
- cost policy;
- owner preference.

A fake deterministic backend is intentionally included so the kernel can be tested without Ollama or any provider.

## Workshop integration

The authenticated Workshop baseline belongs under `workshop/`.

Do not immediately refactor every room.

Add adapters one capability at a time:

```text
existing Music function
-> bounded adapter
-> capability registry
-> worker permission
-> receipt
-> integration test
```

The existing room remains usable while the AIOS path is proven.

## Non-goals for the bootstrap

- full DAW or NLE;
- autonomous publishing;
- cloud authority;
- mandatory Rust rewrite;
- mandatory WASM runtime;
- mandatory vector database;
- mandatory OpenAI/Ollama/provider;
- replacing existing Workshop rooms.
