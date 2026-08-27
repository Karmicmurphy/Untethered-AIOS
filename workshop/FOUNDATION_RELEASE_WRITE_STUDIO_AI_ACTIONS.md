# TWIS Write Studio AI Actions

This bounded release turns the existing Write Room Local AI entry into an inline, governed creative-writing station while preserving the accepted Workshop architecture and installed Local AI Model Bay.

## What it adds

- Sixteen fixed writing actions: brainstorming, continuation, selection rewrite, five tone/direction changes, dialogue work, scene/character development, alternate versions, structure, direction summary, and creative possibilities.
- Selection-aware or whole-draft input, plus zero to three explicitly selected same-project context sources.
- Task-specific, bounded prompts routed deterministically through the registered localhost model.
- A Write-native two-gate interface: exact plan approval, then separate result approval.
- Original/proposal comparison, copy, insert, selected-passage replacement, whole-draft replacement, inactive proposal saving, new Write version saving, and governed Write restore rollback.
- Local browser read-aloud for the current draft or proposal, with an explicit Stop speaking action.

## Authority boundary

The installed `llama.cpp` runtime and Liquid LFM2.5 1.2B Q4_K_M registration are unchanged. The model output is proposed content only. Generation does not edit, save, approve, attach, activate, publish, or replace any owner writing. Context is opt-in and displayed by title and hash. Every model job retains task, source, model, prompt, parameter, output, time, validation, decision, and receipt provenance through the existing Worker Kit.

## Deliberate limits

- No model or runtime installation or replacement.
- No cloud provider, external AI endpoint, hidden project dump, autonomous writing, or automatic save.
- The local 1.2B model is useful for bounded creative assistance but is not represented as equivalent to a large hosted model.
- Read aloud uses the browser/Windows local speech capability already available to the Workshop and creates no audio artifact.

