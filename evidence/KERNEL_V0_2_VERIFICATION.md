# Kernel V0.2 Verification Certificate

Date: 2026-08-27  
Branch: `bootstrap/workshop-baseline`  
Implementation commit: `dde57590c2df28274271ff3bec171d4e850f81e6`  
Implementation tree: `ed230538763a472264821245d0d4146abe69b39f`

## Result

**PASS — KERNEL V0.2 candidate verified**

This certificate covers the bounded direct successor selected by the mandatory
Artifact Compass sweep. It does not claim that the whole AIOS, a real Workshop
adapter, or production integration is complete.

## Contract-to-proof map

| Required contract | Candidate mechanism | Current proof |
|---|---|---|
| Persistent process table | `ProcessTable`, in-memory store, rollback-journal `SQLiteProcessTable` | SQLite reopen, PID continuity, integrity, journal-mode, READY/WAITING recovery tests |
| PID / parent PID | Monotonic table allocator and immutable parent link | root/child and SQLite round-trip tests |
| Complete lifecycle | One transition matrix for `NEW/READY/RUNNING/WAITING/SUSPENDED/DONE/FAILED/CANCELLED` | transition-order, suspend/resume, failure, cancellation, restart tests |
| Deterministic scheduling | FIFO `deque` ready and per-topic wait queues | exact interleaving assertion |
| Yield / requeue | `Step.yield_cpu()` produces `RUNNING -> READY` and tail requeue | two-process FIFO test |
| Event wait / kernel wake | `Step.wait()`, topic queues, `publish()`, suspended pending-wake flag | live and SQLite-reopen wait/wake tests |
| Kernel-authorized child spawn | `ProcessContext.spawn()` delegates to a RUNNING parent check | child lifecycle tests |
| No child escalation | every requested child grant must be equal/narrower than a parent grant | narrower-path pass and broader/cross-capability denial tests |
| Structured capability invocation | `CapabilityRequest` and capability-owned scope/mutation metadata | registry and kernel invocation tests |
| Canonical path scope | resolved absolute handler target plus containment check | traversal, sibling, UNC, ADS, reserved-name, trailing-component tests |
| Mutation receipts | canonical target, PID lineage, input/output hashes, hash link, durable sink | mutation and reopen tests |
| Deterministic fake model | fixed response sequence and recorded prompts | fake-model test |
| Crash/failure evidence | RUNNING-on-reopen fails as `KernelRestart`; runner and capability failures receipted | crash recovery, exception, denial-order tests |

## Exact validation

- `python -m unittest discover -s tests -q`: **37 passed**, 0 failures,
  0 errors, 16.576 seconds on the final release-proof run.
- `python -m compileall -q src scripts tests`: **PASS**.
- `python scripts/demo.py`: **PASS**; synthetic capability only, PID 1 reached
  `DONE` in 2 ticks with 8 receipts.
- JSON parse check: **4/4 PASS** for process, receipt, capability, and worker
  contracts.
- Receipt-chain tamper test: **PASS**, persisted corruption fails closed.
- SQLite checks: **PASS**, rollback journal mode (`delete`), `integrity_check=ok`,
  persistent process/receipt round trips and reopen behavior.
- Rollback simulation: **PASS**. In a disposable worktree, reversing
  `dde5759` produced a Git tree equal to `cca5026`; that rolled-back tree ran
  **13/13** baseline tests successfully in 0.619 seconds. The worktree was
  removed afterward.

## Artifact Compass and no-broadening result

**PASS — ARTIFACT COMPASS bounded reality sweep complete; direct Kernel V0.2 implementation selected**

The selected stack is Python 3.12 standard library plus embedded SQLite in
rollback-journal mode. No runtime dependency was added. No Rust, WASM, vector
database, local model, provider SDK, agent framework, or framework migration was
introduced. The implementation commit contains 17 files and zero `workshop/`
paths.

SQLite WAL was rejected for this bounded candidate because the installed Python
runtime embeds SQLite 3.49.1 and the current upstream WAL documentation records
a rare concurrent WAL-reset issue for affected versions. V0.2 instead serializes
writes and uses rollback journaling.

## Protected Workshop proof

- Authoritative live Workshop writes: **NONE**.
- Music Loop Deck V1 restart/rebuild: **NONE**.
- Fresh code-safe authentication: **293 included / 233 excluded**.
- Live source tree: `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`.
- Imported tree: `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`.
- Imported extras/missing: **0 / 0**.
- Tracked `workshop/` changes after Phase 0 commit: **NONE**.
- Live SQLite read used `mode=ro&immutable=1`: `integrity_check=ok`,
  `user_version=13`, foreign-key violations 0, projects 3, artifacts 60,
  receipts 331, jobs 1.
- Raw live-database file hash: **not obtained** because the active service held
  the file; no checkpoint, stop, or lock-widening action was attempted.

## Runtime, provider, and database status

- Kernel runtime: Python standard library, candidate-local execution only.
- Model/provider runtime: deterministic `FakeModel` only; Ollama and external
  providers are **not required and not integrated**.
- Kernel database: tested local SQLite implementation; test databases were
  temporary and no production Kernel database was created or migrated.
- Workshop adapters: **not implemented**.
- Live integration/deployment: **not approved and not performed**.

## Remaining gaps and next gate

Kernel V0.2 is cooperative in-process orchestration, not hostile-code sandboxing,
OS subprocess supervision, preemptive scheduling, or resource-budget enforcement.
Capability side effects and their receipts are not a single atomic transaction
across external resources. Runner code must be rebound by exact `runner_id`
after restart.

The next bounded engineering gate is one candidate-only, read-only Workshop
capability adapter with an integration test and receipt proof. Any modification
or deployment into `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS` remains a separate
explicit owner-approval gate.
