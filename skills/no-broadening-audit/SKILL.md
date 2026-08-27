# Skill: No-Broadening Audit

Use this skill before committing, declaring a candidate PASS, or adding a new dependency/capability during a bounded successor.

## Question

`Did this successor quietly become a different project?`

## Audit

Compare the current candidate against the approved/direct-successor scope.

Check for accidental expansion in:

- features;
- rooms/workers;
- dependencies;
- models/providers;
- network access;
- filesystem/process authority;
- databases/migrations;
- cloud services;
- hardware requirements;
- UI redesign;
- installation footprint;
- persistent background behavior;
- deployment scope.

## Result

Classify every extra change:

- `REQUIRED` — necessary to make the bounded successor correct and tested;
- `INCIDENTAL` — harmless unavoidable generated/format change;
- `DEFER` — useful but not needed now; remove from candidate and record for future;
- `REJECT` — unrelated or boundary-breaking; remove.

## Rule

A good idea is not automatically in scope.

If a discovery belongs to a later phase, preserve it in evidence/roadmap and keep it out of the current implementation.

## PASS statement

A candidate may claim no-broadening only when:

- changed files map to the successor;
- added dependencies are justified;
- no protected authority widened;
- deferred discoveries remain deferred;
- tests were not weakened merely to accommodate drift.
