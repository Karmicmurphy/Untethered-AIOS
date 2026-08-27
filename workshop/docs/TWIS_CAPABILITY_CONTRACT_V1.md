# TWIS Capability Contract v1

`twis-capability-v1` is the canonical, static, lightweight description used by Modules / Capability Bay and Build V2. It does not grant authority and is not an executable plugin contract.

## Truth boundary

- Discovery is not approval.
- Valid syntax is not approval.
- Open source is not approval.
- Free is not approval.
- A catalog entry never installs, downloads, invokes, activates, submits, or pays for itself.
- `DISCOVERED`, `INSPECTING`, `TESTING`, `INCOMPATIBLE`, `BLOCKED`, and `RETIRED` records cannot hold write, execute, or external-submit authority.
- Executable permissions are declared using the fixed `reads`, `writes`, `network`, `shell`, `environment`, `credentials`, `models`, and `externalServices` manifest.

The current registry is `config/capability-registry.json`. It is application configuration, not owner data, and requires a normal bounded Workshop release to change.

## Hardware fit

The companion derives a local profile from Windows CPU identity, Kernel32 memory and processor-feature evidence, and current drive capacity. It reports `GOOD FIT`, `MAY WORK`, `TOO HEAVY`, `UNSUPPORTED`, or `UNKNOWN`. Marketing claims cannot yield `GOOD FIT`; a record must supply bounded requirements, and expensive benchmarks remain explicit later actions.

## Replacement and cost

Comparable entries share a `replacementGroup`. Build V2 ranks only declared matches and prefers verified, free, local, hardware-compatible options. It never silently replaces capability. Cost classes are:

- `local-free`
- `open-source-free`
- `free-tier`
- `free-with-account`
- `paid-optional`
- `paid-required`

Core TWIS capability does not depend on `paid-required`.

## Agent Skills

Initial Agent Skills support is discovery and inspection only. TWIS reads `name` and `description` frontmatter from `SKILL.md`, counts optional `scripts/`, `references/`, and `assets/` files without loading their contents, records the source hash, and leaves the skill `DISCOVERED`. A bundled script is explicitly blocked pending separate review and approval.

## MCP 2026-07-28

Initial MCP support catalogs server metadata, tool schemas, and resource metadata. The test proof uses only a disposable loopback server. It uses the stateless `2026-07-28` request shape and never calls a tool. Live catalog entries have no arbitrary endpoint input and no auto-enabled tools.

## A2A and WASI

A2A 1.0 Agent Card and WASI 0.3 Component descriptions have contract-level doorway support only. A2A execution, agent swarms, Wasmtime, and component execution are deferred.

## Artifact Compass handoff

Artifact Compass remains the discovery authority. An explicit finding can be selected as a registered source for the Module Proposal Builder, where it becomes a `DISCOVERED` capability proposal retaining source identity and evidence. Only later inspection, testing, owner approval, and a bounded release can move it toward use. No finding self-registers, executes, or elevates authority.

## Provenance mapping

Current TWIS fields already retain the core future-provenance bridge: source identity and hash, derived-from relationships, worker/engine identity, timestamps, owner approval state, and output hash. Full C2PA signing, assertion packaging, and external certificate identity are not implemented.

Existing `jobId`, worker evidence, artifact relationships, and receipt IDs can map to lightweight future `trace_id`, `span_id`, `parent_span_id`, capability/worker/engine IDs, timestamps, and input/output artifact IDs. This release records the capability registry context inside governed Build plans and outputs without adding a parallel telemetry store or database migration.
