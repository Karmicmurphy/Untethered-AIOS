# Kernel-owned Reflex Execution Bridge V0.1

Campaign 2 closes one Campaign 1 gap: a REFLEX decision can now execute one
deterministic cheap handler under exact Kernel authority and reuse its proven
result.

## Exact path

```text
WorkItem
-> Attention Governor
-> REFLEX
-> CheapHandlerRegistry resolution
-> Kernel process with exact cheap.handler.execute grant
-> CapabilityRequest scoped to handler:request-normalizer-v1
-> deterministic request-normalizer-v1
-> result SHA-256
-> Computation Memory row and dependency edges
-> computation.executed receipt
```

An identical repeat checks Computation Memory before spawning a process:

```text
same handler ID/version/contract
+ same WorkItem and payload hashes
+ valid dependency result hashes
+ same invalidation rule
+ proof reference
+ stored value matching result hash
-> computation.reused
-> no process, handler call, or FakeModel call
```

## One handler, not a plugin system

`request-normalizer-v1` supports only task class `request.normalize`. Its
input is exactly:

```json
{"title": " string ", "tags": ["strings"]}
```

It trims the title, then trims, lowercases, deduplicates, and sorts tags. The
output is a JSON-safe object with the same two fields. It uses Python string and
sorting primitives only, declares version `1.0.0`, a stable dependency hash,
one exact resource-scoped capability grant, deterministic behavior, and a
0.1-unit expected cost. It is deterministic logic, not AI.

The registry stores contracts and resolves handlers. The registry cannot grant
capabilities, create grants, spawn processes, call models, access files/network,
or mutate the Workshop.

## Authority

The Governor recommends a lane and does not execute. The bridge resolves the
declared handler. Kernel is the only execution authority: it spawns the process
and authorizes a structured `CapabilityRequest`. Missing grants and wrong
handler scopes fail before the handler. Existing no-self-grant, child-subset,
path, resource, and lifecycle rules remain unchanged. `OWNER_GATE` stops without
running this handler or the FakeModel.

The cheap capability is non-mutating and accepts no filesystem path, network
destination, process target, SQL, arbitrary executable, or Workshop resource.

## Reuse and evidence

Computation Memory now optionally persists a JSON-safe result value. On write,
its SHA-256 must equal `result_hash`. Reuse explicitly checks producer
identity (handler ID + version), inputs, dependency hashes and states,
invalidation rule, proof reference, stored result presence, and stored
result/hash agreement.

Receipt kinds distinguish:

- `cognitive.route` — Governor decision;
- `capability.call` — exact Kernel-authorized handler invocation;
- `computation.recorded` — ledger mutation;
- `computation.executed` — handler actually ran;
- `computation.reused` — proven result returned without execution;
- `computation.invalidated` — dependency result changed;
- `execution.central_ai` — FakeModel escalation;
- `execution.owner_gate` — protected work stopped without execution.

Kernel and Computation Memory must share one AuditLog. With
`SQLiteProcessTable`, the complete chain persists.

## Boundary

This is one in-process deterministic handler for cooperating code. It is not a
plugin framework, hostile-code sandbox, general worker marketplace, real model
gateway, Workshop integration, or production deployment.
