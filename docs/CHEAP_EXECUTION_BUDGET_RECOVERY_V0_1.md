# Kernel Cheap-Execution Budget and Recovery V0.1

Campaign 3 strengthens the single Campaign 2 cheap execution lane. It does not
add another handler, cognitive subsystem, provider, or Workshop capability.

## Enforcement boundary

Campaign 3 provides **cooperative bounded execution for trusted Untethered
handlers**. Kernel owns the budget, monotonic clocks, attempt identity, process
association, exhaustion decision, and receipts. The handler can only call the
Kernel-injected `budget.checkpoint()` equivalent; it cannot change its limits.

This is not preemptive containment of malicious, native, blocked, or
non-cooperating code. It is not an OS sandbox. A handler that never checkpoints
cannot be interrupted by this V0.1 contract.

## Budget contract

`ExecutionBudget` is immutable and requires:

- stable budget, owner, and task identities;
- positive wall-time and CPU-time limits in nanoseconds;
- positive process-tick and cooperative work-unit limits;
- an explicit finite recovery count from zero through sixteen.

`max_attempts` is one initial attempt plus `max_recovery_attempts`. Each attempt
gets its own stable attempt identity and Kernel PID. `BudgetGuard` uses
`time.perf_counter_ns()` and `time.process_time_ns()` by default; deterministic
tests inject monotonic clock doubles.

## Governed path

```text
WorkItem
-> Attention Governor
-> REFLEX
-> KernelCheapExecutionBridge
-> immutable ExecutionBudget
-> Kernel process + exact existing grant
-> execution.started
-> ProcessContext.checkpoint
-> Kernel-injected checkpoint inside request-normalizer-v1
-> success OR execution.budget_exceeded / execution.failed
-> finite same-contract recovery
-> execution.recovered OR terminal failure
-> successful result only -> Computation Memory
```

The capability registry injects the checkpoint after authorization. A worker
cannot provide or replace it. Missing/wrong grants are still denied before the
handler, and recovery reuses the exact handler ID, version, contract hash,
runner ID, grant set, task identity, and budget contract hash.

## Failure and recovery rules

- Exhaustion raises `BudgetExceeded` at a checkpoint and the Kernel transitions
  the process to `FAILED` through the existing lifecycle.
- Ordinary handler exceptions also produce a `FAILED` process.
- The bridge emits `execution.failed` with `successful_result_published=false`.
- No failed attempt writes a successful Computation Memory row.
- Each retry is finite and linked to the previous failure receipt by
  `execution.recovery_started`.
- A successful retry emits `execution.recovered`; that receipt becomes the
  proof reference for the successful computation.
- If all attempts fail, all PIDs remain terminal and no computation is reusable.
- `recover()` refuses changed budget, handler/version/contract, capability
  grants, missing failure evidence, or an exhausted attempt policy.
- OWNER_GATE is evaluated again and can never be converted into cheap recovery.

## Durability

Budget identity, limits, attempt identity, and attempt number are stored in the
existing process metadata JSON. Kernel/process receipts use the existing
SQLiteProcessTable sink. On reopen, terminal failure evidence and the receipt
chain remain visible. A new bridge instance may recover only from that exact
persistent trace and authority contract. Recovered successful output is stored
in the existing SQLite Computation Memory and can then be reused normally.

## Boundary

This candidate uses Python 3.12, standard library clocks, the existing Kernel,
CapabilityRegistry, AuditLog, ProcessTable, and Computation Memory. It adds no
threads, multiprocessing, dependencies, database service, network, real model,
GPU requirement, Workshop mutation, deployment, or persistent permission.
