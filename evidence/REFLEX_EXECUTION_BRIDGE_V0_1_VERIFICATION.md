# Reflex Execution Bridge V0.1 verification certificate

Date: 2026-08-29  
Branch: `successor/reflex-execution-bridge-v0.1`  
Exact base: `d71ed807bf55499312a1a70c5aed7ac09e8cd5ac`  
Implementation commit: `387c9598de90924bd8413d1c5076277b079ee2fc`  
Implementation tree: `4d39ae7651496e82b6071e1ad93b39f8ca13f5e6`

## Result

**PASS — TWIS REFLEX EXECUTION BRIDGE CAMPAIGN 2 VERIFIED**

Campaign 1 was preserved and pushed normally to the official
`Karmicmurphy/Untethered-AIOS` repository. The remote branch resolved to its
exact verified head before this branch was created. No force-push, rebase, or
history rewrite occurred.

## Sixteen-gate proof

| Gate | Current proof |
|---|---|
| 1. Governor controls real lane | A real `WorkItem` is decided by the existing Governor; only REFLEX is eligible for the one default handler. The Governor never invokes it directly. |
| 2. One cheap handler under Kernel | Exactly one `request-normalizer-v1` handler executes as a Kernel process through `cheap.handler.execute`. |
| 3. Capability enforcement intact | Exact resource scope is `handler:request-normalizer-v1`; missing and wrong grants fail with `capability.denied`; inherited no-self-grant/child-subset tests remain green. |
| 4. First run executes | Permanent benchmark records `REFLEX / EXECUTED`, PID present, one capability call, hashed result, and ledger row. |
| 5. Identical repeat reuses | Same handler/version/contract, inputs, dependencies, rule, proof, and stored result produces `REFLEX / REUSED`. |
| 6. Repeat has zero recomputation | Repeat has no PID and does not increment the handler execution count; benchmark records one handler recomputation avoided. |
| 7. Cheap path has zero central calls | FakeModel count remains zero across initial cheap execution, identical reuse, and dependency-triggered recompute. |
| 8. Only affected work recomputes | Changing dependency A makes only the dependent cheap computation STALE and executes it once; U stays VALID/reusable. |
| 9. Unrelated work reusable | Permanent benchmark and focused unit test both return reusable for independent computation U. |
| 10. Novel work escalates | Novel/high-uncertainty case routes CENTRAL_AI and calls the deterministic FakeModel exactly once. |
| 11. Protected work owner-gated | Protected case routes OWNER_GATE with no handler, process, result, or FakeModel call. |
| 12. Distinct receipts | Chain contains `computation.executed`, `computation.reused`, `execution.central_ai`, and `execution.owner_gate`, plus exact `capability.call` evidence. |
| 13. Saved work quantified | Benchmark: two handler executions total (first plus affected recompute), one reuse, one avoided handler recomputation, four FakeModel calls avoided, one real FakeModel test call. |
| 14. Complete regression | Focused 18/18 and complete Untethered 75/75 pass; compile, seven contracts, demo, and diff checks pass. |
| 15. Rollback | Disposable detached worktree at exact base passed its preserved 63/63 suite and was clean before removal. |
| 16. Workshop unchanged | Before/final authentication: 293 included, 231 excluded, identical code-safe tree `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`; zero tracked `workshop/` changes. |

## Exact execution and reuse contracts

```text
WorkItem
-> Attention Governor
-> REFLEX
-> CheapHandlerRegistry resolution
-> Kernel process with exact grant
-> scoped CapabilityRequest
-> request-normalizer-v1
-> result SHA-256
-> SQLite Computation Memory
-> hash-linked execution receipt
```

The registry is a descriptor/resolver and has no grant, spawn, filesystem,
network, process, model, or Workshop authority. The single handler accepts
exactly `title` and `tags`; it trims the title and trims, lowercases,
deduplicates, and sorts tags. It declares task class `request.normalize`,
version `1.0.0`, deterministic behavior, standard-library dependency identity
and hash, input/output contracts, one exact capability, and expected cost 0.1.

Computation Memory adds optional canonical JSON result persistence. It rejects
a stored value whose hash differs from `result_hash`. Bridge reuse additionally
requires the exact handler/version producer identity, exact inputs, exact valid
dependency results, unchanged invalidation rule, non-empty proof, stored value,
and stored value/hash agreement. Any failed predicate recomputes or fails
closed; the registry cannot convert a failed predicate into authority.

## Permanent benchmark

Artifact: `evidence/reflex-execution-bridge-v0.1-benchmark.json`

- Campaign 1 benchmark is embedded under `campaign_1`; it was extended, not
  replaced.
- First: REFLEX / EXECUTED, 78,125,000 CPU ns, 157,662,500 wall ns, 9,158
  traced bytes for the bridge operation.
- Identical repeat: REFLEX / REUSED, no PID/handler execution/FakeModel call;
  46,875,000 CPU ns, 41,165,300 wall ns, and 3,400 traced bytes for the real
  lookup, proof checks, stored-result load, and reuse receipt.
- Dependency change: affected computation observed STALE, then EXECUTED once;
  independent U remained reusable.
- Whole Campaign 2 sequence: 640,625,000 CPU ns, 834,352,600 wall ns, 61,613
  peak traced Python bytes on Python 3.12.10 / Windows / four logical CPUs.
- Economy: two handler executions, one reuse hit, one avoided handler
  recomputation, one affected recomputation, four FakeModel calls avoided, one
  FakeModel call for the novel case.
- Receipt chain: 32/32 persisted receipts, valid head
  `1552e1a0f640fb098f465c79367efd948306389693486dcc3f7b47a544e43807`,
  no chain errors, two exact cheap capability calls.
- SQLite: Kernel and Computation Memory both `integrity_check=ok` and
  `journal_mode=delete`.
- Correctness: all ten benchmark predicates true.

## Exact validation

- Focused bridge/memory/contract/benchmark tests: **18/18 PASS** in 6.966 s.
- Complete `scripts/test.ps1`: **75/75 PASS** in 12.000 s.
- Exact-base rollback `scripts/test.ps1`: **63/63 PASS** in 7.264 s.
- `python -m compileall -q src scripts tests`: **PASS**.
- JSON contract parse: **7/7 PASS**.
- `python scripts/demo.py`: **PASS**, PID 1 DONE in two ticks with eight
  receipts.
- `git diff --check`: **PASS**.
- Tracked campaign changes under `workshop/`: **0**.

An early direct `unittest` command omitted the repository's required `src`
PYTHONPATH and failed imports; rerunning the exact command with the same setup as
`scripts/test.ps1` produced the passing focused result above. During test-first
development, the initial missing bridge module and two contract-test mismatches
failed as expected and were resolved before final validation.

## No-broadening audit

- Runtime dependencies remain exactly Python standard library plus embedded
  SQLite; `pyproject.toml` dependencies remain empty.
- Model/provider remains FakeModel only. Network/provider/GPU calls are zero.
- New frameworks, databases, runtimes, lockfiles, background services,
  persistent permissions, Workshop capabilities, owner UI, live deployment,
  paid services, and credentials: **0**.
- The only database shape change is a backward-compatible nullable
  `result_json` column in the candidate Computation Memory database; no
  production database was opened or migrated.
- Artifact Compass decisions and exact stack positions are recorded in
  `evidence/ARTIFACT_COMPASS_REFLEX_EXECUTION_BRIDGE_V0_1.md`.

## Protected-state proof

Fresh before/final authentication both found 293 code-safe files and 231
excluded private/runtime files at the identical live tree hash. The two raw
authentication manifests are deliberately ignored working evidence; their
hashes and compact comparison are preserved in
`evidence/reflex-execution-bridge-v0.1-protected-state.json`. Campaign 2 did not
write, deploy, restart, copy into, or open a database in the authoritative
Workshop. The three inherited imported Workshop CRLF/LF mismatches remain
pre-existing and untouched.

## Remaining limitations

- One in-process cooperating handler is proven; this is not hostile-code
  isolation, a plugin framework, or a general worker marketplace.
- The default handler demonstrates REFLEX. The registry contract permits RULE,
  but no second handler or RULE execution path was added.
- Governor costs are still caller-supplied synthetic utility estimates and the
  benchmark is synthetic, not production-calibrated economics.
- Timing is hardware/run dependent and is evidence, not a service-level target.
- Result persistence is canonical JSON-safe data only.
- No real model, provider, network, GPU, Workshop integration, UI, deployment,
  or production database is present.

## Next gate

Recommended Campaign 3: one bounded **Kernel Cheap-Execution Budget and
Recovery V0.1**. Enforce declared wall/CPU budgets cooperatively and prove an
interrupted deterministic handler can fail/recover with durable receipts before
adding another handler, provider, or Workshop capability. Campaign 3 was not
started.
