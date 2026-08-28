# Workshop Read Adapter V0.1 Verification Certificate

Date: 2026-08-27  
Branch: `successor/workshop-read-adapter-v0.1`  
Base commit: `f93dfcbda3831bc918d42c8ff3f298af6e7681fe`  
Implementation commit: `1ba5800e598b4b3063e68541d95625cffeac6133`  
Implementation tree: `fa149d97cc5a7a76eb699053082744f163c76243`

## Result

**PASS — WORKSHOP READ ADAPTER V0.1 candidate verified**

This certificate covers one candidate-only, read-only capability bridge. It
does not claim live deployment, live-data validation, a Workshop write path, or
completion of the wider AIOS.

## Exact bounded bridge

- Workshop primitive: `workshop.companion.server.artifact_inspection_options(project_id)`
- Capability name: `workshop.artifact.read`
- Scope form: `project:<project-id>`
- Scope semantics: strict lowercase resource grammar, exact project match,
  wildcard invocation denied, wildcard delegation denied, and child scopes
  must remain equal to the parent's exact project scope.
- Worker inputs: canonical project resource scope and bounded artifact ID only.
  No caller-supplied filesystem path, SQL, process, network, or write input is
  accepted.
- Mutation flag: `false`.

Verified invocation path:

```text
ProcessContext.invoke(CapabilityRequest)
-> Kernel CapabilityRegistry grant check
-> canonical_resource_scope exact-match validation
-> WorkshopArtifactReadAdapter.read
-> workshop.companion.server.artifact_inspection_options(project_id)
-> eligible project-matching artifact metadata
-> structured twis-workshop-artifact-read-v0.1 result
-> SHA-256 result hash
-> hash-linked capability.call receipt and trace
```

The existing Workshop primitive opens its configured SQLite database through
the Workshop's `connect_read_only()` path, filters artifact rows by project,
and validates public-safe roots, traversal, reparse points, private authority,
file class, size, UTF-8 content, and stored source hash. Its internal
duplicate-hash lookup is broader than the requested project, but V0.1 returns
none of that duplicate/provenance data; the worker receives only the selected
project's eligible artifact metadata.

## Contract-to-proof map

| Required behavior | Candidate proof |
|---|---|
| Exact grant and structured request | Process record retains the exact `CapabilityGrant`; worker sends `CapabilityRequest` |
| Canonical bounded scope | strict `project:<id>` parser and exact resource-scope registry match |
| Existing Workshop primitive | wrapped call assertion proves the imported primitive is invoked with the exact project ID |
| Real structured result | actual imported Workshop code reads a disposable SQLite/public-file fixture and returns eligible metadata |
| Result hash | `capability.call.detail.output_sha256` equals `hash_value(process.result)` |
| Receipt and trace | receipt binds PID, capability, canonical target, input hash, output hash, and `mutation=false`; result names all three hops |
| Read-only behavior | fixture database SHA-256 is identical before/after; no mutation receipt exists; receipt chain verifies |
| Failure evidence | authorized adapter/primitive failures emit `capability.failed` with canonical project target |

## Exact validation

- Focused adapter/capability/kernel set: **34 passed**, 0 failures, 0 errors,
  3.985 seconds.
- Adapter-specific tests: **12 passed**, including success, contract, denial,
  failure, immutable-process-view, and child-delegation cases.
- Full `scripts\test.ps1` suite: **49 passed**, 0 failures, 0 errors,
  9.347 seconds reported by `unittest` (38.558 seconds command wall time).
- `python -m compileall -q src scripts tests`: **PASS**.
- JSON contract parse: **5/5 PASS**.
- Synthetic `scripts\demo.py`: **PASS**, PID 1 `DONE`, 2 ticks, 8 receipts;
  the demo deliberately invokes no Workshop adapter.
- `git diff --check`: **PASS**.

## Denial and security evidence

The candidate tests prove:

- missing `workshop.artifact.read` grant -> `capability.denied` before adapter;
- a different project scope -> denied before adapter;
- traversal, Windows-path, uppercase-scheme, and empty scopes -> denied;
- wildcard project authority -> denied before adapter;
- malformed artifact ID -> targeted `capability.failed`;
- missing artifact -> targeted `artifact_not_found` failure;
- Workshop primitive exception -> targeted `workshop_primitive_failed` receipt;
- copied process views cannot self-grant;
- an exact-scope parent cannot delegate another project;
- an unusable wildcard parent cannot delegate an exact usable project scope;
- successful read emits `capability.call`, never `capability.mutation`;
- receipt-chain verification remains valid.

The boundary is application-level authority for cooperating workers. It is not
hostile-code sandboxing or subprocess isolation.

## Artifact Compass and No-Broadening Audit

Narrow local-fit classifications:

- `KEEP` — existing `artifact_inspection_options(project_id)` primitive at the
  trusted Workshop-read layer.
- `TEST` — exact non-path `project:<id>` resource scope at the Kernel capability
  registry layer; tests now prove invocation and delegation behavior.
- `REJECT` — direct HTTP/server startup, raw SQL exposure, arbitrary path input,
  wildcard Workshop authority, and direct live-data access for this candidate.
- `DEFER` — every additional Workshop adapter and any live integration gate.

Changed implementation scope is exactly nine files. There are zero changed
`workshop/` paths, zero dependency/lockfile changes, zero database migrations,
and zero new model, provider, Ollama, network, subprocess, UI, Rust, WASM,
vector-database, agent-framework, sandbox, or resource-budget mechanisms.

## Protected Workshop proof

Authoritative Workshop: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

- Before code-safe tree:
  `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`
- After code-safe tree:
  `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`
- Before/after counts: **293 included / 233 excluded**.
- Tree and counts match: **PASS**.
- Tracked changes under `workshop/`: **0**.
- Workshop writes, service stop/restart, Music rebuild/restart, SQLite
  checkpoint, artifact/project creation, configuration change, and deployment:
  **NONE**.

The 233 excluded files remain excluded runtime/private classes. No private live
data was copied into the candidate or Git.

## Runtime, provider, and database status

- Runtime: Python 3.12 and existing standard-library/imported Workshop code.
- New dependencies: **NONE**.
- Model/provider/Ollama: **not required and not integrated**.
- Candidate database proof: disposable temporary SQLite plus a public-file
  fixture; database hash unchanged before/after the read.
- Live Workshop database: **not opened by the candidate test and not modified**.
- Production Kernel database/migration: **none**.
- Live integration/deployment: **not approved and not performed**.

## Rollback proof

In a disposable worktree, reversing implementation commit
`1ba5800e598b4b3063e68541d95625cffeac6133` produced Git tree
`128b6aa64afb3067a00ae76035ce3b768fed18c7`, exactly equal to base commit
`f93dfcbda3831bc918d42c8ff3f298af6e7681fe`. That rolled-back tree passed the
preserved **37/37** baseline tests in 4.004 seconds. The disposable worktree was
removed afterward.

## Remaining limitations and next gate

V0.1 is a candidate code bridge proven against the authenticated imported
primitive and deterministic data, not a live-data integration. It returns
metadata only, requires the authenticated `workshop/` snapshot at runtime, and
does not supervise hostile worker code or make the primitive call and Kernel
receipt one atomic transaction.

The exact next bounded recommendation is a separately approved
**Workshop Read Adapter V0.1 owner/live-read validation gate**: configure this
same candidate against the authoritative Workshop through a read-only,
immutable inspection lane, prove one owner-selected public artifact read, and
prepare deployment/rollback materials without adding a second capability.
That gate was not started because live integration requires new explicit owner
approval.
