# Worker Harness and Guarded Promotion

Foundation Release 0.4 retains the Release 0.3 reference proof and uses the same guarded lifecycle for one fixed useful read-only capability. It is not a general plugin host or hostile-code sandbox.

## Fixed workers

- `reference-metadata-worker` v0.1.0 reads only its harmless copied fixture and writes metadata JSON.
- `artifact-compass-inspection-worker` v0.4.0 reads one server-resolved public-safe `.txt`, `.md`, `.json`, `.py`, `.js`, `.html`, or `.css` artifact, maximum 512 KiB, and writes one canonical JSON report, maximum 128 KiB.

Both module entry points, paths, permissions, tests, timeouts, and limits are fixed. Requests cannot supply an executable, module, command, environment override, test command, network target, or shell fragment.

## Lifecycle

```text
draft -> validated -> execution_planned -> executed -> tests_passed
      -> candidate -> awaiting_approval -> approved -> active -> rolled_back
                                      \-> rejected
```

Passing tests never skips `awaiting_approval`.

## Execution enforcement

- Exact Worker Card and plan hashes.
- Canonical public/fixture read roots, bounded output roots, and protected blocked roots.
- Source/input SHA-256 and workspace generation revalidation.
- Fixed Python argv, `shell=False`, closed stdin, five-second deadline, bounded concurrent output capture.
- One expected output, no unexpected file effects, closed output schema, canonical JSON, and internal deterministic test.
- Automatic bounded output recovery and terminal failure receipts.

The inspection worker hashes source bytes before reading and after reading; the parent verifies again after child completion and deterministic recomputation. Artifact content is never imported, evaluated, rendered, or executed.

## Candidate and approval binding

Candidate identity binds worker/card/plan/transaction/recovery/output/test/generation material. Inspection candidates also bind artifact ID and source SHA-256. Approve/reject/activate/rollback require exact candidate hash and generation. Inspection actions additionally require explicit source artifact, Worker Card, and plan hashes.

Actor identity is a local assertion, not authenticated identity. Approval-note text stays in the local decision/candidate record; receipts retain only its SHA-256.

## Attachment and rollback

Reference activation remains registry-only. Inspection activation adds an `artifact_attachment` descriptor with artifact ID, source hash, report path/hash, and attachment kind. It does not execute code, grant permission, update Workshop SQLite, alter review status, or modify the artifact.

Rollback verifies candidate/output/recovery/receipt evidence, restores the bounded pre-run output, and marks the registry/attachment entry rolled back.

## API

- `GET /api/workers`
- `POST /api/workers/validate`
- `GET /api/artifacts/inspection-options`
- `POST /api/workers/reference-metadata-worker/plan|run`
- `POST /api/workers/artifact-compass-inspection-worker/plan|run`
- `GET /api/candidates`
- `GET /api/candidates/{candidate-id}`
- `POST /api/candidates/{candidate-id}/approve|reject|activate|rollback`
- `GET /api/artifacts/{artifact-id}/inspections`

State-changing requests require JSON, are bounded to 16 KiB, and reject cross-site Fetch Metadata. Production APIs expose no fault injection.

## Persistence and provenance

Evidence lives under `data/worker_harness/` after the first explicit plan: cards, plans, requests, workspace outputs, transaction manifests/receipts/recovery, tests, candidates, decisions, activation/attachment records, rollback records, registry, provenance inventory, and derived Artifact Compass SQLite.

Source content, private inputs, approval notes, and raw captured streams are not indexed into derived Artifact Compass evidence.

## Honest limits

No OS container, restricted token, job object, cross-process lock, authenticated human identity, signed/immutable receipt, AI, vector search, artifact repair, arbitrary worker, private archive inspection, shell, or network authority is claimed.
