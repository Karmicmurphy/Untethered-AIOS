# Skill: Artifact Compass — 10-Pass Discovery and Salvage

Use this skill before selecting a new technology, runtime, model, framework, database, sandbox, agent system, integration pattern, or major successor direction.

Artifact Compass is not a shopping list and not an excuse to broaden scope. Its job is to find useful parts, identify where they belong in the stack, reject bad fits, and convert evidence into one bounded next move.

## Non-negotiable biases

- official-source-first;
- legal/open-source-aware;
- free-first;
- local-first where practical;
- hardware-measured, not hardware-imagined;
- artifacts/receipts remain authority;
- providers/models/frameworks remain replaceable;
- no silent installation or activation;
- no paid dependency as a core requirement;
- no proprietary cloning or license laundering;
- do not confuse an interesting project with a necessary project dependency.

## 10-pass method

### Pass 1 — Reality baseline

Inspect the current repository, runtime, tests, hardware evidence, and verified capabilities first.

Write down what already works so research does not rediscover or replace it unnecessarily.

### Pass 2 — Better question rewrite

Rewrite the owner's request into the smallest answerable engineering question.

Bad:

`What is the best AI agent framework?`

Better:

`What missing capability prevents Untethered KERNEL V0.2 from safely waking blocked workers, and is an external framework actually needed to solve it?`

### Pass 3 — Official source map

Search primary/official sources first:

- project documentation;
- source repository;
- release notes/changelog;
- standards/specification;
- license;
- hardware/runtime requirements;
- maintained examples.

Record exact source and freshness.

### Pass 4 — Open implementation map

Find legal, permissively usable implementations and primitives that solve the underlying capability.

Prefer salvageable mechanisms over wholesale adoption.

Ask:

- What is the smallest useful primitive here?
- Can Untethered implement or adapt that primitive without importing the whole platform?
- What dependency/runtime burden comes with it?

### Pass 5 — Adjacent/frontier sweep

Look one and two rings beyond the obvious solution:

- direct dependency alternatives;
- adjacent layers;
- current research/standards;
- small local runtimes;
- emerging interoperable protocols;
- techniques used in other system classes that may transfer cleanly.

This is how Untethered stays ahead without randomly accumulating software.

### Pass 6 — Stack-position map

For every serious candidate, state exactly where it belongs:

- UI;
- Workshop room;
- worker;
- capability adapter;
- kernel;
- scheduler;
- event bus;
- memory;
- model governor;
- isolation boundary;
- evidence/receipt layer;
- external optional adapter.

If the stack position is unclear, do not adopt it.

### Pass 7 — Reality filters

Evaluate:

- actual CPU/RAM/GPU fit;
- Windows/local compatibility;
- offline capability;
- startup/runtime cost;
- dependency weight;
- maintenance state;
- license/legal fit;
- privacy implications;
- network requirements;
- money/billing risk;
- authority/security impact.

### Pass 8 — Classify

Every candidate receives exactly one current classification:

- `KEEP` — already useful/correct; preserve it.
- `CUT` — existing complexity that should be removed when safely bounded.
- `TEST` — promising enough for a reversible candidate experiment.
- `REJECT` — poor fit, unsafe, paid/core-dependent, stale, legally unsuitable, or unnecessary.
- `DEFER` — potentially valuable, but not for the current successor.

Classification is about THIS phase, not eternal judgment.

### Pass 9 — Salvage card + proof plan

For each `TEST`, complete an Artifact Compass Salvage Card and define the smallest experiment that could prove or disprove its value.

Do not install first and invent the reason afterward.

### Pass 10 — Successor synthesis + no-broadening audit

Produce:

1. current stack truth;
2. important findings;
3. `KEEP/CUT/TEST/REJECT/DEFER` table;
4. missing capability/question;
5. one bounded direct successor;
6. proof criteria;
7. explicit deferred ideas;
8. statement that current scope did not silently broaden.

Then hand execution to the Direct Successor Autopilot / No-Drift Build Algorithm.

## Artifact Compass Salvage Card

For any serious candidate record:

- source inspected;
- what it does;
- stack position;
- classification (`KEEP/CUT/TEST/REJECT/DEFER`);
- exact salvage mechanism;
- source/license/legal notes;
- hardware/runtime requirements;
- privacy/network/cost implications;
- future phase if deferred;
- current boundary impact;
- proof required before adoption.

## Continuous pipeline

The long-form operating pipeline is:

`Discover -> compare -> test -> prove -> stage -> verify -> approve -> deploy -> monitor -> roll back`

Do not skip from `discover` directly to `deploy`.

## Output rule

Artifact Compass must end with a decision, not another pile of links.

Codex owns engineering proof. The owner owns product truth and live/deployment approval.
