# Artifact Compass — Cheap-Execution Budget and Recovery V0.1

## Bounded question

Can the verified Python Kernel and one trusted deterministic handler enforce a
cooperative execution budget, persist failure, and recover finitely with the
same authority, or is another runtime/isolation platform necessary?

Current repository evidence answers the fit question. Kernel V0.2 already owns
PIDs, lifecycle transitions, structured capability checks, SQLite persistence,
restart failure evidence, and chained receipts. Campaign 2 already owns handler
resolution, exact grants, result hashing, and Computation Memory reuse. No
unresolved external fact could change the smallest stdlib design, so no public
web research or installation was justified.

## Classification and exact stack position

| Candidate | Exact stack position | Decision | Campaign 3 treatment |
|---|---|---:|---|
| Existing Kernel lifecycle and ProcessTable | kernel/process authority | KEEP | Own PIDs, transitions, persistent metadata, and reopen truth. |
| Existing CapabilityRegistry exact grant path | capability-security layer | KEEP | Authorize before checkpoint injection; no new scope. |
| Existing request-normalizer-v1 | trusted deterministic handler | KEEP | Minimally add cooperative checkpoints; no second production handler. |
| Existing AuditLog/SQLite receipt sink | evidence/recovery layer | KEEP | Persist start, exhaustion, failure, retry, and recovery links. |
| Existing Computation Memory | successful-result evidence layer | KEEP | Store only successful/recovered output; reuse predicates unchanged. |
| Immutable ExecutionBudget | kernel resource-contract layer | TEST | Prove identities and explicit wall/CPU/tick/work-unit/retry limits. |
| Per-PID BudgetGuard + injected checkpoint | kernel cooperative-enforcement layer | TEST | Prove deterministic fail-closed exhaustion under fake clocks. |
| Finite bridge retry derived from receipts | execution recovery policy | TEST | Prove same version/grants/budget, reopen visibility, success, and terminal failure. |
| Threads or multiprocessing for forced preemption | runtime/isolation replacement | REJECT | Unnecessary for the requested cooperative trusted-handler contract. |
| Rust, WASM, containers, agent/supervisor frameworks | hostile isolation/runtime layer | REJECT | No measured need and would replace verified authority. |
| Redis, broker, external database/service | persistence replacement | REJECT | Embedded SQLite already provides the required durable proof. |
| More handlers, Workshop capability, associative memory, MicroForge, Downshift | later product/cognitive layers | DEFER | Explicitly outside Campaign 3. |
| Hostile/native/blocked-code preemption | future isolation boundary | DEFER | V0.1 documents the non-preemptive boundary honestly. |
| Real provider/model/GPU/network | later optional model layer | DEFER | FakeModel remains the only central test double. |

## Direct-successor decision

TEST only an immutable stdlib `ExecutionBudget`, a Kernel-owned per-PID guard,
checkpoint injection after capability authorization, and one finite recovery
loop that validates persistent authority hashes. Prove it against the existing
handler with deterministic clocks, SQLite reopen, complete regression,
rollback, and protected-state authentication.

No dependency, handler, provider, runtime, database service, UI, Workshop
capability, persistent permission, or deployment scope was broadened.
