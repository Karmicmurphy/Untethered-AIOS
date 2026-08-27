# Local API Worker Kit 0.8 Contract

## Purpose

Release 0.8 adds one internal, loopback-only API for four bounded local
workers. It extends the existing Workshop companion, SQLite, artifacts,
projects, jobs, receipts, Talk, Write, and My Work. It is not a plugin host,
shell runner, general agent, tool registry, model router, or parallel app.

## Fixed worker allowlist

### Approved Text Reader

- ID: `approved-text-reader`
- responsibility: read one explicitly selected registered text source;
- input: UTF-8 registered artifact, current Talk session, or current Write
  document, at most 512 KiB;
- output: exact encoding, bytes, characters, lines, content, and source hash;
- mutation: none;
- runtime: two seconds;
- network, shell, subprocess, arbitrary path, attachment, activation, and
  promotion: denied.

### Code Structure Inspector

- ID: `code-structure-inspector`
- responsibility: lexical structure inspection without execution;
- input: supported registered text code, Talk, or Write, at most 512 KiB;
- output: facts for counts, imports/dependencies, functions, classes, and
  markers; separately labeled heuristic probable type and repeated lines;
- mutation: none;
- runtime: two seconds;
- semantic understanding is not claimed.

The implementation reuses the tested deterministic inspection behavior already
used by Talk and the governed Artifact Inspection foundation.

### Note Proposal Worker

- ID: `note-proposal-worker`
- responsibility: propose one note from selected current content;
- input: current selected Talk, Write, or registered artifact content, at most
  256 KiB;
- output before approval: title, proposed Markdown note, hash, and proof flags;
- mutation: create exactly one draft `note` artifact only after result
  approval;
- source: always preserved;
- rollback: remove only the unchanged `local-worker-note-v1` artifact bound to
  that exact job and hash;
- runtime: two seconds.

### Package Manifest Validator

- ID: `package-manifest-validator`
- responsibility: validate one registered JSON manifest or ZIP package;
- input: at most 16 MiB, 500 members, 64 MiB expanded size;
- output: container hash, format facts, safe members, member hashes, missing,
  unexpected, unsafe, duplicate, and hash-mismatch lists;
- mutation: none;
- installation, extraction to disk, execution, import, and activation: denied;
- runtime: five seconds.

## Contract validation

Every Worker Card contains:

- stable ID, owner name, description, and one responsibility;
- supported inputs;
- required and prohibited permissions;
- input, output, member, expanded-size, and runtime limits as applicable;
- deterministic classification;
- denied network policy;
- versioned output schema and validation rules;
- mutation and approval policy;
- receipt requirements and rollback behavior;
- version `0.8.0`;
- current implementation SHA-256;
- canonical contract SHA-256.

The companion refuses a contract that is incomplete, is outside the fixed
allowlist, permits network, omits required prohibitions, or does not require
both plan and result approval.

## API

Read routes:

- `GET /api/local-workers`
- `GET /api/local-workers/{worker}`
- `GET /api/local-worker-sources?projectId=...`
- `GET /api/local-worker-jobs?projectId=...&limit=...`
- `GET /api/local-worker-jobs/{job}`

Mutation routes:

- `POST /api/local-worker-jobs/plan`
- `POST /api/local-worker-jobs/{job}/plan-decision`
- `POST /api/local-worker-jobs/{job}/execute`
- `POST /api/local-worker-jobs/{job}/cancel`
- `POST /api/local-worker-jobs/{job}/recover`
- `POST /api/local-worker-jobs/{job}/result-decision`
- `POST /api/local-worker-jobs/{job}/rollback`
- `POST /api/local-worker-jobs/{job}/delete`

All mutation routes require `application/json`, reject cross-site browser
requests, reject unsupported fields, and cap bodies at 256 KiB. IDs select
only existing registered records. Ordinary UI use displays titles and worker
names, not required technical IDs.

The legacy generic `/api/jobs` read and write routes return HTTP 410. They
cannot create arbitrary local worker operations.

## State machine

Normal lifecycle:

`planned -> plan_approved -> running -> awaiting_result_approval ->
result_approved`

Explicit alternatives:

- `planned -> plan_rejected`
- `planned|plan_approved|interrupted -> cancelled`
- approved execution with changed source -> `stale`
- expired plan -> `abandoned`
- bounded runtime or validation failure -> `failed`
- result decision -> `result_rejected`
- accepted Note Proposal -> `rolled_back`
- process interruption while `running` -> `interrupted -> plan_approved`

An execute request repeated after the same job reached
`awaiting_result_approval` returns the existing output idempotently. A
concurrent `running` job is rejected as duplicate. Recovery never accepts
output; it returns an unchanged current plan to `plan_approved`. Repeated
recovery after that state is idempotent.

## Plan and source binding

Before execution the companion verifies:

- job and worker allowlist identity;
- project and registered artifact identity;
- canonical path containment and absence of symlink/junction escape;
- stored and current source hash;
- Talk/Write current version and source hash;
- selected text still belongs to the current source;
- packet hash;
- plan hash;
- contract hash and implementation hash;
- nonexpired plan;
- explicit nonblank approval note.

Any source drift fails closed. No replacement source is silently substituted.

## Output and approval

Worker output must be a JSON object with its exact versioned schema, bounded
canonical size, `networkUsed=false`, and `shellUsed=false`.

Validation establishes only that the output matches the declared contract.
The initial result always has `accepted=false`, `attachmentStatus=unattached`,
`activationStatus=inactive`, and
`modulePromotionStatus=not-requested`.

Result approval requires a separate nonblank note. Approval never attaches,
activates, installs, imports, starts, or promotes anything. Only the Note
Proposal Worker has a mutation, and that mutation is one new draft note.

## Receipts, evidence, cleanup, and recovery

Receipts record meaningful plan, decision, execution, failure, note, rollback,
cancellation, interruption, recovery, and history-cleanup actions. The
`worker_job_evidence` table stores hash-addressed evidence projections tied to
the job.

Terminal job history may be deleted only with explicit confirmation. An active
created note blocks cleanup until exact rollback. Job/evidence rows are
removed, but receipts remain. Unrelated artifacts, writing, Talk, reviews,
imports, permissions, and Worker Harness state are never cleanup targets.

On companion startup, a job left `running` becomes `interrupted` with
`accepted=false`, unattached and inactive evidence. The owner may recover its
still-current approved plan or cancel it.

## Security and certification limits

- host binding: `127.0.0.1`;
- no worker network API;
- no shell, subprocess, dynamic Python, `eval`, plugin installation, or
  self-modification;
- no owner-supplied arbitrary file path;
- no archive extraction to disk;
- explicit canonical path, traversal, reparse-point, archive-member, size,
  timeout, output, and SQLite transaction controls;
- browser output uses text nodes or read-only textarea values;
- certification means only the declared code paths, hashes, schemas,
  transactions, tests, and observed lifecycle passed.

The operating claim remains: worker output is evidence, not proof; validated
output is not owner approval; owner approval is not attachment or activation.
