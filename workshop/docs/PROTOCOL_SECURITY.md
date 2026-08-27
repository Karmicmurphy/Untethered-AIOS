# Protocol Security Pass — 2026-06-18

Twis Holo must treat MCP-style tool ecosystems as useful but dangerous.

## Current rule

MCP, AG-UI, A2UI, A2A and Cloudflare modules are **capability adapters**, not trusted authority.

## MCP default posture

- deny by default;
- no automatic shell execution;
- no blind trust in tool metadata;
- no invoking tools merely because a model asked;
- show tool name, parameters, source, and risk before execution;
- receipts required for every tool invocation;
- external filesystem writes must stay inside the active project unless explicitly approved;
- secrets are never passed to tools unless the human approves that specific use.

## Why

Recent MCP security research and reporting focus on tool poisoning, prompt injection, and remote-code-execution style risks. Twis Holo therefore uses a broker/gate model: models recommend actions, but the Workshop checks capability cards, permissions, risk, and receipts before execution.

## Cloudflare remote rule

Cloudflare is optional remote muscle. Local project folders + SQLite remain authoritative.

## Human-only actions

- approve Canon;
- delete permanent source;
- publish;
- spend money;
- expose private memory;
- run shell commands;
- install external modules.
