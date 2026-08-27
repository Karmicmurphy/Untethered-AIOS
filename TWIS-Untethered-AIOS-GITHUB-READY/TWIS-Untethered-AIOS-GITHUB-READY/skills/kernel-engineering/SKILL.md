# Skill: Kernel Engineering

Use this skill for scheduler, process lifecycle, event bus, cancellation, child spawning, and recovery work.

## Required sequence

1. Define the state transition or kernel invariant.
2. Add denial/failure tests first when practical.
3. Keep worker code unable to mutate its own permissions/process table entry.
4. Implement the smallest contract.
5. Run affected tests.
6. Run complete suite.
7. Record any new lifecycle state or invariant in `docs/ARCHITECTURE.md`.

## Invariants

- one PID identifies one process record;
- terminal states do not silently return to RUNNING;
- WAITING processes run only after a kernel wake/requeue;
- a child is created by kernel authority, not by fabricating an object inside a tool;
- cancellation is observable;
- failures produce receipts/events;
- scheduler policy must be deterministic under tests.
