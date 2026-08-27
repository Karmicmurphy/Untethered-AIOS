# Skill: Receipt / Trace / Certificate Harness

Use this skill when a candidate needs to prove what happened rather than merely claim it.

Untethered should preserve three evidence layers:

1. **Receipt** — one governed action happened.
2. **Trace** — the ordered chain of actions/events that produced an outcome.
3. **Certificate** — a compact verification statement derived from current receipts, traces, tests, hashes, and protected-state checks.

## Receipt

A receipt should record, where applicable:

- actor/process PID;
- action/capability;
- bounded target/scope;
- timestamp;
- inputs or input hashes;
- output/artifact hash;
- result/state;
- error if any;
- parent job/process reference.

Do not store secrets or unnecessary private content in receipts.

## Trace

A trace should make lifecycle behavior reconstructable:

`request -> plan -> process spawn -> capability grants -> calls/events -> artifact -> verification -> completion/failure`

Trace order must be deterministic enough for tests and debugging.

## Certificate

A certificate is NOT self-asserted trust.

It is a derived summary that says what current evidence proves, for example:

- candidate commit/hash;
- tests executed and results;
- artifact/output hashes;
- permission-denial tests;
- dependency/runtime/provider status;
- protected-state verification;
- rollback simulation result;
- exact scope.

Never reuse an older certificate as proof for newer bytes.

## Trusted-claim rule

Owner-facing claims such as `verified`, `protected`, `rollback-ready`, or `no external requests` must be backed by current evidence.

If evidence is incomplete, say `PARTIAL` or `UNVERIFIED` rather than manufacturing certainty.

## Integration direction

The existing `AuditLog` / `Receipt` bootstrap can evolve toward this harness incrementally.

Do not redesign it all at once. Add fields/contracts only when a successor needs them and tests prove them.
