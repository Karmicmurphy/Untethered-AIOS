# Skill: Artifact Compass Deep Salvage

Use this skill when the user asks for a deep dive, salvage pass, several passes, frontier search, or when the obvious answer is too shallow for a strategic system decision.

Deep Salvage is the extraction layer of Artifact Compass. Its job is to find transferable mechanisms without dragging whole platforms into Untethered AIOS.

## Core question

Do not ask only:

`Can we use this project?`

Ask:

`What exact mechanism inside this project is worth salvaging, where would it sit in Untethered, and can we prove it with less dependency and less authority?`

## Required pass structure

For each pass:

1. **Source map** — primary docs, repo, releases, license, issue health, examples.
2. **Layer map** — identify what layer the mechanism belongs to.
3. **Classification** — `KEEP/CUT/TEST/REJECT/DEFER`.
4. **Missing question** — what is still unproven or misunderstood?
5. **Future phase** — if not now, where could it become useful later?

Each pass must narrow uncertainty. Do not merely repeat broader search terms.

## Salvage targets

Look for mechanisms such as:

- scheduler policies;
- process lifecycle models;
- capability-token patterns;
- event/wake semantics;
- state checkpoints;
- sandbox boundaries;
- resource accounting;
- model/runtime discovery;
- routing/governor policies;
- receipt/provenance structures;
- rollback and recovery patterns;
- artifact interchange contracts;
- local-first sync patterns;
- testing harnesses;
- protocol interoperability.

## Do not salvage blindly

Reject or defer mechanisms that:

- require paid service as core infrastructure;
- make a remote provider authoritative;
- depend on hardware not available to the target machine;
- widen filesystem/network/process authority without a proven need;
- introduce a large framework to solve a small problem;
- are abandoned or poorly licensed;
- duplicate a verified Workshop capability;
- force a rewrite of working owner-visible features.

## Deep Salvage report

A useful report has:

- the mechanism found;
- why it matters;
- exact stack position;
- smallest salvageable form;
- evidence/source;
- license/legal note;
- local hardware fit;
- classification;
- reversible test;
- adoption threshold;
- explicit reason if rejected/deferred.

## Stopping condition

Stop researching when another pass is no longer likely to change the direct-successor decision.

Depth is valuable only if it improves the next bounded build.
