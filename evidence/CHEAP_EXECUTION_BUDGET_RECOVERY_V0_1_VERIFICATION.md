# Cheap-Execution Budget and Recovery V0.1 verification certificate

Date: 2026-08-29

Branch: `successor/cheap-execution-budget-recovery-v0.1`

Exact base: `bab64c263e337400e0a7b77bcebb47677cd701da`

Implementation commit: `05e4dc3c08ba5eba7415d2b7c0b5c9d1c214680c`

Implementation tree: `5f39063b2f2ffc8e8648d5135cf0dab016cd0c25`

## Result

**PASS — TWIS CHEAP-EXECUTION BUDGET + RECOVERY CAMPAIGN 3 VERIFIED**

The exact verified Campaign 2 branch was pushed normally to the official
`Karmicmurphy/Untethered-AIOS` repository before this branch was created. The
remote resolved to exact Campaign 2 head
`bab64c263e337400e0a7b77bcebb47677cd701da`. No force-push, rebase, or history
rewrite occurred. This Campaign 3 branch remains a local candidate and was not
pushed, deployed, or published.

## Nineteen-gate proof

| Gate | Current proof |
|---|---|
| 1. Kernel owns explicit budgets | Immutable `ExecutionBudget` binds budget, owner, task, wall ns, CPU ns, ticks, work units, and finite recovery count. Kernel creates and retains the per-PID `BudgetGuard`. |
| 2. Handler observes contract | Kernel injects `ProcessContext.checkpoint` only after exact capability authorization; `request-normalizer-v1` checkpoints at entry, per tag, and before return. |
| 3. Exhaustion fails closed | Deterministic fake clocks prove wall, CPU, tick, and work-unit limits raise `BudgetExceeded`; clock regression also fails closed. |
| 4. Failure is not reusable | Budget and ordinary handler failures never write successful Computation Memory rows. A later budget-ID reset for the same failed inputs is rejected. |
| 5. Correct process failure state | Every exhausted or failed attempt reaches existing terminal `FAILED`; the repeated-failure benchmark records two `FAILED` PIDs. |
| 6. Failure evidence persists | `execution.started`, `execution.budget_exceeded`, and `execution.failed` receipts plus process metadata are persisted through the existing ProcessTable sink. |
| 7. Attempts are finite | `max_attempts = 1 + max_recovery_attempts`; validation caps recovery configuration and the bridge refuses exhausted histories. |
| 8. Recovery cannot widen authority | Recovery re-evaluates the Governor and requires exact budget contract, handler ID/version/contracts, capability-grant hash, and execution inputs. Forged worker checkpoint arguments and changed authority are denied. |
| 9. Reopen preserves evidence | Forced failure was closed and reopened; failed PID, failure receipt, budget identity, and valid chain remained visible. SQLite integrity remained `ok`. |
| 10. One recovery succeeds | Permanent benchmark recovers the reopened forced wall failure under the same authority with a new PID and `RECOVERED` outcome. |
| 11. Recovered result reusable | Only the successful retry is written; `execution.recovered` is its proof reference and the next identical call is `REUSED`. |
| 12. Repeated failure terminates | A one-recovery budget produces exactly two failed attempts, then returns terminal `BUDGET_EXCEEDED` with no computation record. |
| 13. Existing cheap reuse works | Normal budgeted success executes once; an identical repeat reuses it without a new PID or handler execution. |
| 14. CENTRAL_AI remains correct | Novel benchmark work routes `CENTRAL_AI` and invokes the deterministic FakeModel exactly once. |
| 15. OWNER_GATE remains protected | Protected work is re-evaluated and returns `OWNER_GATE`; recovery cannot convert it into cheap execution. |
| 16. Receipt chain valid | Four benchmark stores contain 73/73 persisted receipts; all hash chains validate with zero errors. |
| 17. Complete regression | Campaign 2+3 focused 24/24 and complete Untethered 89/89 pass; compile, eight contracts, benchmark, demo, and diff checks pass. |
| 18. Rollback | Disposable detached worktree at exact Campaign 2 base was clean and passed its preserved 75/75 suite before exact removal. |
| 19. Workshop unchanged | Before/final authentication: 293 included, 231 excluded, identical stable manifests and code-safe tree `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`. |

## Budget and enforcement design

```text
WorkItem
-> Attention Governor
-> REFLEX
-> Kernel process and exact capability grant
-> Kernel-owned per-PID BudgetGuard
-> injected cooperative checkpoints
-> success OR FAILED with explicit evidence
-> exact finite recovery policy
-> successful result/proof OR terminal failure
-> Computation Memory only after proven success
```

Wall time uses `time.perf_counter_ns()` and CPU time uses
`time.process_time_ns()`. Injected clocks make exhaustion deterministic in
tests. Tick and work-unit counters are part of the same guard. Budget and
attempt metadata are persisted with each Kernel process; receipt history binds
recovery to the same input hash and prevents a caller from resetting a failed
attempt sequence merely by choosing another budget identity.

The enforcement boundary is cooperative trusted Python code. A handler that
does not reach a checkpoint cannot be interrupted by this mechanism. Campaign
3 does not claim hostile-code sandboxing, preemptive native-process
containment, blocked-call interruption, or OS crash isolation.

## Failure, recovery, and reuse

- Exhaustion emits `execution.budget_exceeded`; both budget exhaustion and
  ordinary exceptions emit `execution.failed` and finish the PID as `FAILED`.
- Failure receipts explicitly state that no successful result was published.
- Recovery emits `execution.recovery_started`, uses a new PID under unchanged
  authority, and links to the prior failure receipt.
- Successful retry emits `execution.recovered`; only that successful result and
  proof enter Computation Memory.
- `SUCCESS` and `RECOVERED SUCCESS` are reusable after all existing
  input/dependency/version/proof checks. `BUDGET_EXCEEDED` and `FAILED` are not.
- A changed budget contract, handler/version/contract, grant hash, input, or
  protected routing decision cannot inherit or widen recovery authority.

## Restart/reopen proof

The permanent benchmark forced a wall-budget failure, confirmed no computation
row, persisted ten receipts, closed both SQLite stores, reconstructed Kernel and
Computation Memory, and observed the same failed PID and failure receipt. It
then recovered under the exact prior budget/handler/grant contract, persisted
the successful result, and reused it. Kernel and computation stores both report
`integrity_check=ok` and `journal_mode=delete`.

## Permanent benchmark

Artifact: `evidence/cheap-execution-budget-recovery-v0.1-benchmark.json`

- Campaign 2 benchmark remains embedded under `campaign_2`; this benchmark
  extends rather than replaces it.
- Correctness: all 14 predicates true, including deterministic wall and CPU
  exhaustion, reopened recovery, terminal repeated failure, successful reuse,
  CENTRAL_AI, OWNER_GATE, and valid chains.
- Economy: two handler executions, two reuse hits, four failed attempts, two
  recovery starts, one recovered success, four budget-exceeded events, and one
  FakeModel call.
- Whole Campaign 3 sequence: 1,296,875,000 CPU ns, 2,128,561,400 wall ns, and
  187,702 peak traced Python bytes on Python 3.12.10 / Windows / four logical
  CPUs. Timing is hardware/run dependent, not a service-level target.
- Receipt persistence: 73/73 receipts across success, recovery, terminal, and
  CPU-exhaustion stores; every chain valid.
- Provider/network calls: zero. Model runtime: deterministic FakeModel only.

## Exact validation

- Campaign 2+3 focused tests: **24/24 PASS** in 23.869 s.
- Complete Untethered suite: **89/89 PASS** in 24.247 s.
- Exact-base rollback suite: **75/75 PASS** in 10.666 s.
- Budget-only focused discovery: **14/14 PASS** in 9.844 s.
- Permanent benchmark: **14/14 correctness predicates PASS**.
- `python -m compileall -q src tests scripts`: **PASS**.
- JSON contract parse: **8/8 PASS**.
- `python scripts/demo.py`: **PASS**, PID 1 `DONE` in two ticks with eight
  receipts.
- `git diff --check`: **PASS**.
- Protected Workshop code-safe tree: **UNCHANGED**.

One attempted validation command, `.\scripts\demo.ps1`, failed because that
file does not exist in this repository. The repository's real demo entry point,
`python scripts\demo.py`, was then run and passed. Test-first development also
produced the expected initial import failure before `ExecutionBudget` existed;
all final validation above is current and passing.

## No-broadening and security audit

- Python 3.12, standard library, embedded SQLite, existing Kernel,
  ProcessTable, AuditLog, CapabilityRegistry, and Computation Memory remain the
  complete stack. Dependency manifests are unchanged.
- Exactly one production handler remains. No second cognitive subsystem,
  supervisor framework, thread/multiprocessing preemption, Rust, WASM,
  container, broker, external database/service, AERA runtime, real model,
  provider SDK, network path, GPU requirement, Workshop capability, or owner UI
  was added.
- Security review found a possible finite-attempt reset using a fresh budget ID
  for the same failed inputs. The final implementation binds failure history to
  the execution-input hash and rejects this reset; adversarial coverage passes.
- Capability checkpoint injection remains Kernel-controlled after exact grant
  authorization. Workers cannot supply or replace the checkpoint callback.
- Artifact Compass positions and `KEEP / CUT / TEST / REJECT / DEFER`
  decisions are recorded in
  `evidence/ARTIFACT_COMPASS_CHEAP_EXECUTION_BUDGET_RECOVERY_V0_1.md`.

## Remaining limitations and Campaign 4 recommendation

- Enforcement remains cooperative and in-process; a trusted handler must reach
  checkpoints. It is not a security boundary for malicious/native/blocked code.
- Limits are explicit contract values, not production-calibrated service
  budgets. Measurements are synthetic and hardware dependent.
- One deterministic REFLEX handler is proven. RULE execution, more handlers,
  real providers, Workshop integration, associative/temporal memory,
  MicroForge, Cognitive Downshift, UI, and deployment remain absent.

Recommended Campaign 4: add exactly one bounded deterministic RULE handler
through the same Kernel budget/recovery/capability contracts, with permanent
comparative economy evidence and no new Workshop or provider authority. That is
the smallest direct successor that grows useful coverage without weakening the
now-proven lane. Campaign 4 was not started.
