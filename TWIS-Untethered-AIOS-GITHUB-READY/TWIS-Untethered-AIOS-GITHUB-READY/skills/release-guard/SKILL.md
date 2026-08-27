# Skill: Release Guard

Use for candidate verification, manifests, deployment simulation, rollback, or production integration.

## Candidate work

Continue automatically through reversible fixes and testing.

## Protected authority

No live Workshop file change without an explicit owner deployment/change gate.

## Before a release candidate can be called PASS

- affected tests pass;
- complete relevant suite passes;
- changed-file scope is explicit;
- database/runtime/provider status stated;
- protected state verified;
- rollback package or deterministic rollback instructions exist;
- rollback simulation passes where applicable;
- candidate/scope hashes recorded.

Never use an older audit as proof of a newer candidate.
