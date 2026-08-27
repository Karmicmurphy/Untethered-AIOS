# Builder Output V1 Contract

Release 0.9 extends the existing fixed Local Worker Kit. It does not create a generic execution engine.

## Fixed builders

- `handoff-proposal-builder` produces a structured continuation package.
- `prompt-proposal-builder` produces a structured task prompt.
- `draft-workshop` produces an honest ready-to-use writing task and draft scaffold for one of five fixed writing operations.
- `evidence-compare` produces a deterministic comparison workspace from two to eight ordered registered text sources.
- `visual-brief-builder` produces a deterministic visual-production brief and manual-use image prompt from zero to four ordered registered text sources and/or hash-identified temporary visual notes.
- `song-production-brief-builder` produces a deterministic song-production brief and manual-use music prompt from zero to four ordered registered text sources and/or hash-identified temporary music notes and exact owner lyrics.
- `video-production-brief-builder` produces a deterministic video-production brief and manual-use production handoff from zero to four ordered registered text sources and/or hash-identified temporary video notes.
- `build-work-order-builder` produces a deterministic technical implementation work order from zero to four ordered registered text sources and/or hash-identified temporary owner build input.
- `module-proposal-builder` produces a deterministic future-module proposal from zero to four ordered registered text sources and/or hash-identified temporary owner module input.

All builders are deterministic, local, network-denied, and shell-denied. The Release 0.9 builders accept one to twenty registered text sources. Draft Workshop accepts exactly one registered text source or one nonblank owner-entered rough-text value. Evidence Compare accepts two to eight unique registered text sources in explicit owner-selected order. Visual Brief Builder accepts zero to four registered text sources plus optional owner-entered visual notes and requires at least one of those inputs. Inputs are bounded to 512 KiB. No builder scans a directory, fetches a URL, selects related material automatically, calls a provider, generates an image, executes output, overwrites source text, attaches output, activates output, installs anything, publishes, or promotes a module.

## `builder-output-v1`

Each output binds its complete proposal text to metadata containing:

- schema version, builder type, destination profile;
- fixed worker ID and version;
- job ID and plan ID;
- creation time;
- ordered source IDs and source SHA-256 values;
- the owner goal;
- output SHA-256;
- validation and approval state;
- saved artifact ID when saved;
- rollback state after rollback.

The output hash is SHA-256 over canonical UTF-8 JSON containing the exact text and metadata without the `outputHash` member. Any approval, save, or rollback metadata transition rebinds the output. The enclosing Worker Kit validation record separately hashes the complete structured output.

## Governance

The gates remain separate:

1. create hash-bound plan;
2. approve or reject plan;
3. generate and validate proposal;
4. approve or reject proposal;
5. optionally save exactly one inactive draft;
6. optionally export an approved copy by explicit action;
7. optionally roll back only the unchanged draft created by that job.

The handoff profiles are Codex Build Handoff, ChatGPT Continuation Handoff, Human Technical Handoff, and Project Recovery Handoff. The prompt profiles are Codex Implementation Prompt, ChatGPT Research Prompt, Local Model Task Prompt, and Human Work Order.

Draft Workshop operations are Rewrite clearly, Shorten without losing meaning, Expand rough notes, Change tone, and Organize into a structured document. Its output states when no model-generated rewrite exists. It prepares a bounded writing task and draft scaffold instead of pretending that an AI generated prose.

Evidence Compare focuses are General comparison, Factual consistency, Implementation differences, Project status differences, Requirement coverage, Conflicting claims, and Missing evidence. Exact whole-text and normalized-line comparisons are labeled textual facts. Semantic agreements, differences, contradictions, evidence gaps, and conclusions remain `Not assessed` until deliberately completed.

Visual Brief Builder purposes are Song or album cover, Story or scene artwork, Character concept, Poster or promotional image, Product or invention concept, Memorial or emotional artwork, and General image concept. Its output organizes only owner-supplied controls, selected source provenance, and temporary visual notes. Missing details remain explicit unresolved creative decisions. The final prompt is prepared for manual use and is never executed or submitted.

Song Production Brief Builder supports eight fixed purposes from Full original song through General music concept. It organizes only owner-supplied controls, exact registered-source provenance, and hash-identified temporary notes and lyrics. Owner lyrics remain exact in the brief. Missing details remain `Unresolved musical decision`. No music, lyric, vocal, audio, melody, chord, or provider output is generated or played.

Video Production Brief Builder supports Cinematic scene, Music video, Short-form vertical, Talking / performance, Surreal visual, Documentary / story, Product / demonstration, and Image-to-video concept. It organizes only owner-supplied controls, exact registered-source provenance, and hash-identified temporary video notes. Missing details remain `Unresolved production decision`. No video is generated, rendered, uploaded, published, or submitted.

Build Work Order Builder supports Add feature, Fix defect, UI refinement, Local tool, Integration, Refactor bounded area, Test/verification task, and Deployment work order. Missing choices remain `Unresolved implementation decision`. It prepares a handoff only; it never executes code or shell commands, modifies files, submits to Codex, calls a provider, or deploys.

Module Proposal Builder supports Local tool, Worker, Adapter, Importer, Exporter, Media tool, Research tool, System utility, and Experimental module. Missing choices remain `Unresolved module decision`. It never installs, downloads, executes, activates, or fetches a module or dependency.

Saved kinds are `handoff-draft`, `prompt-draft`, `writing-draft`, `research-comparison-draft`, `visual-brief-draft`, `song-production-brief-draft`, `video-production-brief-draft`, `build-work-order-draft`, and `module-proposal-draft`. They remain `DRAFT`, inactive, unattached, unexecuted, unpublished, and unpromoted. One `builder-source` relationship records provenance from each registered source to the saved draft; temporary Build and Module inputs remain identified by `build-input:<SHA-256>` and `module-input:<SHA-256>` in immutable job and draft metadata.

Exports are explicit UTF-8 copies under `data/exports/builders`: TXT/JSON for the Release 0.9 builders, TXT/Markdown for Draft Workshop, and TXT/Markdown/JSON for Evidence Compare, Visual Brief Builder, Song Production Brief Builder, Video Production Brief Builder, Build Work Order Builder, and Module Proposal Builder. Names are generated from an allowlisted profile, sanitized, and distinguished by job and random suffix. Callers cannot provide a path. Exports do not contact a network or provider and are never executed.

## Rejection rules

The service rejects invalid source counts, duplicate or unregistered source IDs, cross-project IDs, conflicting registered and rough-text input, missing/blank/unsupported/binary content, input overflow, blank goals where required, unsupported profiles or writing operations, stale hashes, changed sources after generation, contract or plan mismatch, malformed output, missing sections, output hash mismatch, duplicate result decisions, save before approval, save after rejection, duplicate save, export before approval, missing explicit confirmation, unsupported export formats, unrelated or changed draft rollback, and repeated rollback.

Interrupted running jobs are classified by the inherited safe startup recovery pass. No state-changing builder action silently resumes after restart. Atomic database transactions and atomic export rename prevent partially accepted saves or exports.
