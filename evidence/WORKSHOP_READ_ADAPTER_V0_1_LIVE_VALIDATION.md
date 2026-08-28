# Workshop Read Adapter V0.1 Live-Read Validation Certificate

Date: 2026-08-28  
Branch: `validation/workshop-read-adapter-v0.1-live`  
Starting candidate HEAD: `390e2cba9b4f1377642bcfe6fad9b47235fee556`  
Validation harness commit: `93637403ad69567edd0cfc38d42d1898acabbfde`  
Validation harness tree: `8d0dc4eb8c7197fac97c12baa92ff64b17f60588`

## Result

**PASS — WORKSHOP READ ADAPTER V0.1 live-read validation verified**

This certificate proves one existing public-safe artifact-metadata read against
the authoritative running Workshop. It does not deploy the adapter, add a
second capability, expose artifact content, or authorize Workshop writes.

## Preserved candidate and publication proof

- Verified candidate branch: `successor/workshop-read-adapter-v0.1`
- Verified candidate HEAD: `390e2cba9b4f1377642bcfe6fad9b47235fee556`
- Pre-push complete Untethered suite: **49/49 PASS**.
- Normal GitHub push: **PASS**; no force, rebase, or history rewrite.
- Remote branch after push:
  `refs/heads/successor/workshop-read-adapter-v0.1` at exact `390e2cba9b4f1377642bcfe6fad9b47235fee556`.
- Validation branch was created from that exact commit; the verified candidate
  branch was not modified.

## Exact live target

- Type: existing registered public-safe artifact metadata
- Project scope: `project:flashriver-source-archive`
- Artifact ID: `9217e4a7-7254-53a6-a75e-1d20e0754d86`
- Title: `AGENT.md`
- Kind: `flashriver-core-doc`
- File type: Markdown
- Byte count: `2462`
- Review status reported by the primitive: `unreviewed`
- Source SHA-256:
  `E4EFEDCAB226193F35EAE9E1CB6070102D7FD336B70A5C3205D33976D48BB38A`

The target was selected from existing code-safe deployed Workshop evidence
that already labels this exact artifact and hash public-safe. No database
enumeration, new project, new artifact, or payload/content capture was needed.

## Real invocation path

```text
Kernel process pid:1
-> CapabilityRequest
-> workshop.artifact.read grant check
-> exact project:flashriver-source-archive scope validation
-> WorkshopArtifactReadAdapter.read
-> workshop.companion.server.artifact_inspection_options(project_id)
-> existing live AGENT.md metadata
-> twis-workshop-artifact-read-v0.1 structured result
-> SHA-256
-> capability.call receipt
-> three-hop result trace
```

The live and imported `companion/server.py` files were byte-identical before
execution, both at SHA-256
`10bb4fb6776197d90756e319a2029cfde86b5daf2a0040fbecf4f36ba259baa7`.

## Immutable inspection lane

The validation-only harness temporarily bound the imported module in memory to
the authoritative live database/projects paths. It replaced the primitive's
ordinary read helper only in that process with exactly:

- SQLite URI `mode=ro&immutable=1`;
- `PRAGMA query_only=ON` verified as `1`;
- one connection total;
- no connection or configuration persisted after the process.

No live file was patched and no live configuration was changed.

## Structured result, receipt, and trace

Result schema: `twis-workshop-artifact-read-v0.1`

Top-level result fields:

```text
artifact
capability
primitive
schema
scope
trace
```

Artifact fields:

```text
artifact_id
byte_count
file_type
kind
path
project_id
review_status
sha256
title
```

- Request/input SHA-256:
  `22b14fd639f3a428d8d406266ce96d9eb676238f12846f66f26c0269c2013074`
- Structured result SHA-256:
  `5b8e7d3a2407a89b369937b70b7a0ed730a96a4f9207d6140a558775322d9a2e`
- Capability receipt SHA-256:
  `1b7e15771337f7a5bde2fc6dee7b268a3625213ee7316bb5b1a601e460796157`
- Receipt previous SHA-256:
  `520b395d38653dddbdad5f0bec44886a6a9a60fa8a0b272bea4ed60fdf22d7b7`
- Receipt kind/action/target:
  `capability.call` / `workshop.artifact.read` /
  `project:flashriver-source-archive`
- Receipt PID/actor: `1` / `pid:1`
- Receipt mutation flag: `false`
- Mutation receipt count: **0**
- Receipt-chain verification: **PASS**, no errors

Complete result trace:

```text
kernel.capability.invoke
untethered_aios.workshop_read_adapter.WorkshopArtifactReadAdapter.read
workshop.companion.server.artifact_inspection_options
```

## Protected Workshop proof

Authoritative Workshop: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

- Before code-safe tree:
  `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`
- After code-safe tree:
  `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`
- Before/after included/excluded counts: **293 / 233** both times
- Code-safe tree/count match: **PASS**
- Candidate diff under tracked `workshop/`: **0**

The validation harness also fingerprinted the live runtime files immediately
before and after the governed call:

| Runtime file | Before/after SHA-256 | Result |
|---|---|---|
| `workshop.sqlite3` | `5a26b7cc0f612014013fd6eca776547bfb168c3def0fbcf8850db1b027cba724` | unchanged |
| `workshop.sqlite3-wal` | `5cf1ab15abf8899b7e88286bc7102afc05d78ae8b8945e472e7a1e0dc4f0b933` | unchanged |
| `workshop.sqlite3-shm` | `17186664daad3aa0b5b4c2046a8d9e1957d9c44d8970f3537c1aa989af5df481` | unchanged |

Sizes and nanosecond modification times also matched before/after. No SQLite
checkpoint, vacuum, migration, schema/data write, intentional sidecar write,
service stop/restart, Workshop configuration change, Music Loop Deck action,
project/artifact creation, or deployment was performed.

## Tests and exact validation status

- Focused live-read path: **1/1 PASS**.
- Existing adapter/capability/kernel security set: **34/34 PASS** in 4.317 seconds.
- Complete Untethered suite after live read: **49/49 PASS** in 6.311 seconds.
- Python compileall for `src`, `scripts`, and `tests`: **PASS**.
- Live receipt chain: **PASS**.
- Existing V0.1 implementation manifest: **9/9 hashes PASS** from the inherited
  verified candidate.
- Validation harness SHA-256:
  `a0f89647335110e9b51b12b30e5d93c97778cd6a903226dc52f5d59ffc2d48d6`.

## Validation-branch changes and No-Broadening Audit

Exactly one executable file was added:

- `scripts/validate_live_workshop_read_v0_1.py` — fixed-target,
  immutable/query-only live validation harness.

No adapter, Kernel, capability, contract, imported Workshop, dependency,
configuration, database schema, UI, room, provider/model, Ollama, Rust, WASM,
vector database, agent framework, subprocess authority, arbitrary filesystem,
arbitrary SQL, write capability, or deployment mechanism changed.

Classification:

- `REQUIRED` — the one fixed-target immutable validation harness.
- `INCIDENTAL` — none.
- `DEFER` — owner-visible integration/deployment and every later successor.
- `REJECT` — any security-boundary weakening or broader live authority.

## Remaining limitation and next recommendation

SQLite `immutable=1` intentionally treats the database image as unchanging;
this validation proves the established public-safe target and does not claim
visibility into future or concurrently uncheckpointed Workshop records. The
adapter remains metadata-only and application-level; it is not hostile-code
sandboxing and has not been deployed into the Workshop.

The exact next bounded recommendation is a separately approved
**Workshop Read Adapter V0.1 owner-visible read-only integration candidate**:
expose this same already-verified capability through one existing Workshop
surface without adding a second capability or any write authority. That work
requires a new explicit live integration/deployment instruction and was not
started in this validation turn.
