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

Workshop Read Adapter V0.1 adds strict non-path resource scopes in the form
`project:<project-id>`. They are exact-match only for this capability: wildcard
invocation and wildcard-to-child delegation are denied. The adapter accepts no
filesystem path or SQL input from the worker. After kernel authorization, it
calls the authenticated Workshop's existing
`artifact_inspection_options(project_id)` primitive and returns only eligible,
project-matching public artifact metadata under that project's Workshop root.
The result includes its source hash, a three-hop trace, and a non-mutation
capability receipt. Adapter and primitive failures are explicit and bind the
canonical project target.

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

## Cognitive Substrate V0.1 candidate

Campaign 1 adds a local decision and computation-evidence layer beside the
Kernel. The Attention Governor maps a bounded WorkItem to exactly one route
using explicit authority/resource gates and expected benefit minus cost.
Computation Memory persists hashes and dependency edges in a candidate-only
rollback-journal SQLite ledger, so changed dependencies invalidate only
reachable dependents. Kernel V0.2 remains process/capability authority; the
governor cannot execute or self-grant work.

The complete bounded contract is in
`docs/COGNITIVE_SUBSTRATE_V0_1.md`. Blackboard, general memory, Capability
Cells, Model Gateway implementation, Cognitive Downshift, associative memory,
MicroForge, provider integration, and owner UI remain deferred.

## Reflex Execution Bridge V0.1 candidate

Campaign 2 adds one Kernel-owned cheap execution lane. The Governor still only
selects a route. For `request.normalize`, the bridge resolves one declared
deterministic handler, spawns a Kernel process with the exact
`cheap.handler.execute` resource grant, and invokes it through the existing
CapabilityRegistry. A valid Computation Memory record returns its stored,
hash-verified result without spawning or executing again.

This does not create a general plugin framework or add filesystem, network,
process, provider, model, Workshop, or deployment authority.

## Cheap-Execution Budget and Recovery V0.1 candidate

Campaign 3 makes the single cheap lane cooperatively resource-bounded. An
immutable `ExecutionBudget` binds owner/task/budget identity, monotonic
wall/CPU limits, process ticks, work units, and finite recovery attempts.
Kernel owns a per-PID `BudgetGuard`; `ProcessContext.checkpoint()` is injected
into the already-verified handler only after exact capability authorization.

Budget exhaustion and handler failure transition through the existing FAILED
state and persist distinct receipts. Failed attempts never publish a successful
Computation Memory result. Recovery uses a new PID but must retain the exact
budget contract, handler/version/contract, and grant hash. Reopen recovery is
derived from the existing persistent process/receipt stores.

This is cooperative enforcement for trusted handlers, not hostile-code
preemption or native-process isolation.
