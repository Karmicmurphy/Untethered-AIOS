# Skill: No-Drift Build Algorithm (NDBA)

Use this skill after Artifact Compass has selected a bounded successor or whenever a Codex session resumes interrupted implementation.

NDBA prevents architecture drift, restart-from-scratch behavior, and endless rediscovery.

## Algorithm

`Load State -> Select Step -> Execute/Specify Patch -> Check -> Audit -> Update State -> Continue/Restart Packet`

## 1. Load State

Before changing code:

- inspect current branch/commit;
- read current candidate evidence;
- read relevant handoff/checkpoint;
- inspect surviving files before repeating edits;
- distinguish verified facts from assumptions;
- identify the last completed step.

Never restart a verified successor merely because the conversation/thread changed.

## 2. Select Step

Choose the smallest remaining step that moves the current successor toward its existing completion gate.

Do not silently replace the successor with a new one.

## 3. Execute / Specify Patch

Make the bounded change in the candidate repo/branch.

Preserve protected authority and owner-visible working behavior.

## 4. Check

Run the narrow affected tests first, then the complete relevant suite.

Ordinary candidate defects are fixed automatically and retested.

## 5. Audit

Check:

- scope;
- authority boundaries;
- permissions;
- private data exposure;
- dependency/cost changes;
- regression risk;
- changed-file declaration;
- receipts/evidence.

## 6. Update State

Record what is now proven, what remains, exact branch/commit, and any changed completion criteria.

## 7. Continue / Restart Packet

If the session continues, take the next bounded step automatically.

If interrupted, write a restart packet that contains enough exact state to continue without re-auditing or rebuilding proven work.

## Rules

- no restart-from-scratch unless evidence proves the candidate is unrecoverable;
- no broad redesign to fix an ordinary defect;
- no claiming completion from partial tests;
- no live deployment without the actual owner gate;
- no memory-based recreation when candidate files/evidence exist.
