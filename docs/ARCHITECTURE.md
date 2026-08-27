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

The kernel owns coordination, not creative authority.

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

## Capability model

A worker receives explicit grants such as:

```text
artifact.read:/project/123
artifact.write:/project/123/output
audio.render
music.loop.launch
network:https://allowed.example
```

A grant combines:

- capability name;
- allowed scope;
- optional resource budget;
- optional expiry.

The first bootstrap implements name + scope enforcement.

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
