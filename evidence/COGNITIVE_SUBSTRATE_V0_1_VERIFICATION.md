# Cognitive Substrate V0.1 verification certificate

Date: 2026-08-29  
Branch: `successor/cognitive-substrate-v0.1`  
Selected base: `acf981b15de4b098659e0f74b28465d288a97e0b`  
Implementation commit: `a329349ca8483396d49e142082dd0c8c5dec034e`  
Implementation tree: `233d89365bd562a66c7ba8a8187dee60684c77dc`

## Result

**PASS — TWIS COGNITIVE SUBSTRATE CAMPAIGN 1 VERIFIED**

The selected base is the safest verified lineage because it contains the frozen
Kernel V0.2, Workshop Read Adapter V0.1, and immutable live-read validation,
while remaining the exact rollback base of the separate owner-surface
candidate. The owner-surface branch and its pre-existing dirty checkout were
not modified; Campaign 1 was built in an isolated clean clone.

## Twelve-gate proof

| Gate | Current proof |
|---|---|
| 1. Verified baseline preserved | Exact base rollback suite 49/49; Kernel/adapter tests remain in the 63/63 full suite; zero `workshop/` changes. |
| 2. Architecture contracts | JSON schema plus contract map covers WorkItem, RouteDecision, Governor, Computation Memory, Reflex Handler, Blackboard, Memory, Capability Cell, Model Gateway, and Cognitive Downshift. |
| 3. Deterministic routing | 14 focused tests include same-input/same-clock receipt equality and all seven route outcomes. |
| 4. Protected -> OWNER_GATE | Permanent benchmark and unit test both prove the hard owner boundary. |
| 5. Cheap bypasses central | Cheap deterministic -> REFLEX; repeated familiar -> RULE. |
| 6. Novel/high-value can escalate | Novel ambiguous and high-value uncertain cases both -> CENTRAL_AI through FakeModel only. |
| 7. Computation proof data | SQLite rows persist identity, input/dependency/result hashes, producer, duration, CPU, memory, cost, invalidation rule, proof reference, and state. |
| 8. Exact invalidation | A v1 -> B -> C plus independent D; A v2 makes only B/C STALE, while A/D remain VALID and D is reusable. |
| 9. Permanent benchmark | Nine cases record routes, required/avoided calls, worker calls, CPU/wall/memory, reuse, recomputation, 20 receipts, and correctness. |
| 10. Regressions | Focused 14/14; complete Untethered 63/63; compile, demo, contracts, and diff checks pass. |
| 11. Rollback | Detached exact-base worktree passed 49/49 and was removed. |
| 12. Workshop protected | Live code-safe tree remained `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`; Campaign writes were zero. |

## Routing model

The Governor emits exactly one of IGNORE, DEFER, REFLEX, RULE, WORKER,
CENTRAL_AI, or OWNER_GATE.

`expected net value = expected benefit * empirical success probability - estimated cost`

Benefit and cost share caller-supplied utility units. Risk/protected state,
novelty/uncertainty, CPU/memory budgets, and memory pressure are explicit
eligibility gates rather than decorative score terms. Prior failures lower the
empirical success multiplier. Exact ties prefer REFLEX, RULE, WORKER, then
CENTRAL_AI. Every decision emits a hash-linked receipt with input hash,
candidate values, route, reason, and resource assumptions. The Governor chooses
but cannot execute or grant capabilities.

## Computation Memory

The local SQLite ledger uses rollback journal mode and foreign-key dependency
edges. Reuse requires exact input/dependency hashes, VALID state, and current
VALID dependency results. Updating a result recursively invalidates only its
reachable dependents. Mutations and reuse checks emit AuditLog receipts.

Permanent benchmark result:

- routes: 9/9 expected;
- central-AI calls required: 2, both deterministic FakeModel calls;
- central-AI calls avoided: 4;
- worker calls: 1;
- database: `integrity_check=ok`, `journal_mode=delete`;
- A-change state: A VALID, B STALE, C STALE, D VALID;
- recomputed dependents: B and C; final A/B/C/D all VALID;
- receipt chain: 20 receipts, valid, no errors;
- measured CPU: 265,625,000 ns;
- measured wall: 335,428,700 ns;
- peak traced Python memory: 56,094 bytes.

## Exact validation

- Focused Campaign 1 tests: **14/14 PASS** in 2.024 seconds.
- Complete `scripts/test.ps1`: **63/63 PASS** in 7.150 seconds.
- Exact-base rollback `scripts/test.ps1`: **49/49 PASS** in 2.199 seconds.
- `python -m compileall -q src scripts tests`: **PASS**.
- JSON contract parse: **6/6 PASS**.
- `python scripts/demo.py`: **PASS**, PID 1 DONE in 2 ticks with 8 receipts.
- `git diff --check`: **PASS**.
- Tracked Campaign changes under `workshop/`: **0**.

## Artifact Compass and no-broadening

- KEEP: Python, embedded SQLite, existing AuditLog/Receipt, FakeModel.
- TEST and proven: value-of-computation Governor, SQLite computation ledger,
  permanent synthetic benchmark.
- CUT: opaque blended priority scores.
- REJECT: AERA/NARS/orchestration platforms, vector database, provider/model,
  network, GPU, Rust, WASM, container, or new database runtime.
- DEFER: Blackboard implementation, general/associative memory, Capability
  Cells, Model Gateway implementation, Cognitive Downshift, MicroForge, UI.

Implementation scope is 16 files, all mapped to contracts, implementation,
tests, benchmark, architecture, or evidence. New runtime dependencies,
lockfiles, models, providers, network calls, migrations, UI changes, Kernel
authority changes, live deployment, and persistent background work: **0**.

## Protected-state qualification

Fresh before/final authentication both found 293 code-safe files at the exact
expected live tree hash. Excluded count changed 233 -> 231 because the running
Workshop removed the excluded `visitor_bench.sqlite3-wal` and
`visitor_bench.sqlite3-shm` sidecars. This is non-authoritative runtime drift;
no code-safe file changed and Campaign 1 performed no Workshop write, database
open, checkpoint, restart, Music action, copy, deployment, or configuration
change.

The isolated clean checkout also exposed a pre-existing selected-base
limitation: Git had normalized three imported Workshop text blobs from CRLF to
LF. Fresh live/import working-byte comparison is therefore 290/293, with the
three exact paths and hashes recorded in the protected-state JSON. Campaign 1
does not alter those Workshop bytes or misstate them as a fresh 293/293 import.

## Runtime and limitations

- Runtime: Python 3.12 standard library plus embedded SQLite.
- Model/provider: FakeModel only; no real model, provider, Ollama, network, or
  paid service.
- Database: temporary/candidate SQLite only; no production database or
  migration.
- Hardware: measured on four logical processors with a 7,447,904,256-byte RAM
  target profile; GPU not required.
- The benchmark is synthetic and estimates are caller-supplied, not calibrated
  production economics.
- Governor decisions are not yet wired to Kernel execution.
- Computation receipts persist only when the supplied AuditLog uses a durable
  sink; the computation rows themselves persist.
- SQLite implementation is a small local ledger, not a multi-process service
  or semantic memory system.

## Next gate

Recommended Campaign 2: one bounded **Kernel-owned Reflex/Rule Execution Bridge
V0.1**. It should execute a single Governor-selected deterministic handler
through an exact Kernel capability grant, reuse Computation Memory when hashes
match, recompute when stale, and prove one end-to-end receipt trace. CENTRAL_AI
should remain FakeModel-only. Campaign 2 was not started.
