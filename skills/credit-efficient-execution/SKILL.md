# Skill: Credit-Efficient Execution

Use this skill whenever a task could become long-running, research-heavy, repetitive, or context-heavy in Codex.

## Goal

Spend Codex allowance only where local machine access or direct execution materially improves the result.

## Before starting Codex work

Ask:

1. Can public research be completed outside Codex first?
2. Can architecture/design be decided and committed to repo docs first?
3. Can the task be reduced to exact files, tests, and one completion gate?
4. Does Codex actually need the local Workshop/runtime/browser for this step?
5. Can the task finish as one bounded turn rather than many conversational micro-turns?

If local access is not required, prefer preparing the work through ChatGPT/GitHub first.

## Codex prompt compression

Prefer:

`Read AGENTS.md + exact skill/spec -> change these paths -> run these tests -> fix ordinary failures -> record evidence -> stop at this gate.`

Avoid:

`Look around, figure everything out, research the internet, redesign whatever you think is needed, and tell me what to do.`

## Reuse state

- Read existing evidence/checkpoints instead of re-running audits.
- Never paste long historical handoffs when current repo files already encode them.
- Do not repeat Artifact Compass research that has a current evidence artifact unless local verification is the unresolved question.
- Keep restart packets exact enough for a new chat to continue from the last proven state.

## Test batching

A single candidate turn should normally:

1. implement bounded change;
2. run focused tests;
3. fix ordinary defects;
4. run complete relevant suite;
5. create evidence;
6. run No-Broadening Audit.

Do not turn each of those into a separate owner/Codex conversation unless a genuine gate exists.

## Output discipline

Write verbose machine evidence to files.

Chat summary should contain only:

- what changed;
- what passed;
- what failed/was deferred;
- next real gate.

## Paid usage

Never solve an efficiency problem by silently purchasing credits or enabling auto-reload.

If included allowance is exhausted, finish the active turn when allowed, preserve exact restart state, and report the available account options without making a purchase decision for the owner.
