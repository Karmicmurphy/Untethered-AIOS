# Skill: Better Question Rewriter

Use this skill at the beginning of Artifact Compass work when the owner's request is broad, aspirational, comparative, or framed around a technology rather than a missing capability.

The goal is not to argue with the request. The goal is to turn it into a question that can produce a bounded engineering decision.

## Rewrite pattern

Convert:

`What technology/framework/model should we use?`

into:

`What exact capability is missing, what constraints must it satisfy, and what is the smallest mechanism that can prove it?`

## Required fields

A rewritten question should identify:

- current verified baseline;
- missing owner-visible or kernel capability;
- stack layer involved;
- free/local/privacy constraints;
- actual hardware/runtime constraints;
- authority/security boundary;
- proof needed;
- current successor boundary.

## Examples

Instead of:

`Should Untethered use WASM?`

Ask:

`Which current tool calls require stronger isolation than path-scoped capabilities provide, and can a reversible WASM experiment measurably improve that boundary without breaking Windows/local-first operation?`

Instead of:

`What is the best memory database?`

Ask:

`What retrieval failure exists in the current artifact/receipt model, what query latency/scale is required, and can SQLite/FTS satisfy it before adding another database?`

## Rule

Do not let the rewritten question erase the owner's product goal. It should make the goal testable, not smaller for convenience.
