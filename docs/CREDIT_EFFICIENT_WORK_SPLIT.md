# Credit-Efficient Work Split — ChatGPT + Codex

Goal: build Untethered AIOS as fast as possible without wasting Codex allowance on work that can be decided, researched, or prepared elsewhere.

## Core rule

Use Codex only for work that materially benefits from direct access to the local Windows machine, the authoritative Workshop files, local terminals, browser/runtime state, or exact candidate execution.

Use ChatGPT + GitHub for research, architecture, design decisions, repo documentation, bounded patch preparation, review, and handoff packets whenever local machine access is not required.

## Why

Codex usage is affected by task complexity, context size, reasoning, tools, and long-running execution. Therefore broad prompts such as `figure out the whole OS and build it` are expensive and create drift.

The efficient pattern is:

`research/decide here -> commit exact instructions/specs -> Codex executes local-only slice -> Codex records evidence -> review here -> next bounded slice`

## ChatGPT lane — do here first

ChatGPT should own when possible:

- Artifact Compass public-web research;
- official-source comparisons;
- architecture and stack-position decisions;
- dependency/license/hardware-fit analysis;
- UI design system and component specifications;
- GitHub repo edits that do not require local Windows state;
- contracts, schemas, skills, docs, tests that can be reasoned about independently;
- code review of GitHub commits/branches/PRs;
- successor selection and no-broadening review;
- concise Codex execution packets;
- checkpoint/restart packets;
- release-gate review.

## Codex lane — reserve allowance for this

Codex should own:

- reading/authenticating `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`;
- local filesystem comparison against manifests;
- local branch/worktree operations;
- running Windows-specific tests and scripts;
- launching the Workshop/Untethered runtime;
- browser lifecycle and responsive verification;
- screenshot/console/network inspection when local runtime evidence is required;
- applying local integration patches that depend on current Workshop bytes;
- verifying protected state and rollback on the actual machine;
- local performance measurements;
- final candidate evidence that cannot be established from GitHub alone.

## One-turn Codex packets

Every Codex turn should be bounded enough to finish a meaningful slice in one active turn when practical.

A good packet contains:

1. exact objective;
2. exact source-of-truth paths;
3. files/skills to read;
4. known verified baseline;
5. allowed change scope;
6. tests/evidence required;
7. ordinary defects it may fix automatically;
8. explicit stop gate.

Do not make Codex rediscover project history that already exists in repo files.

## Context budget rules

- Prefer references to repo files over pasting giant handoffs repeatedly.
- Keep `AGENTS.md`, `CODEX_START_HERE.md`, and restart packets current.
- Do not ask Codex to re-run broad Artifact Compass web research when a current research artifact already exists; ask it only to validate local fit or unresolved facts.
- Batch related tests into one turn rather than asking `run this`, then `run that`, then `check this` in separate turns.
- Fix ordinary candidate defects in the same turn.
- Stop research when another pass is unlikely to change the successor decision.
- Avoid huge generated output in chat; write evidence to files and summarize.

## Model/reasoning policy

If Codex exposes model/reasoning choices, use the least expensive/least intensive option that can reliably perform the current mechanical task, and reserve stronger reasoning for architecture, difficult debugging, or ambiguous failures.

Do not hardcode a model name because Codex availability changes. Check the current Codex model selector and usage dashboard.

## Usage monitoring

Before a long Codex session, check current allowance/reset information in Codex Settings/Usage or `/status` where supported.

Never enable automatic paid credit reload merely as a build strategy. Paid usage remains an owner decision.

## Handoff loop

Preferred loop:

```text
CHATGPT
research + architecture + UI + repo prep
       |
       v
CODEX
local authenticate + implement + execute + verify
       |
       v
GITHUB EVIDENCE
commit / branch / report
       |
       v
CHATGPT
review + next successor packet
```

This is the default work-sharing model for Untethered AIOS.
