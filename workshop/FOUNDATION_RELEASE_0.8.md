# Twis Holo Foundation Release 0.8

Date: 2026-07-26  
Release theme: Local API Worker Kit / First Nanite Crew

## Release decision boundary

This report describes the isolated Release 0.8 candidate. Deployment becomes
proven only after exact manifest and rollback authentication, predeployment
hash checks, transactional copy, candidate-to-live equality, deployed
regression, one temporary live lifecycle per worker, product-row cleanup,
protected-state verification, rollback simulation, and the final deployed
verification report.

The active Workshop was not modified during candidate implementation or
isolated verification.

## Authenticated Release 0.7 starting state

Release 0.7 was independently reauthenticated before successor work:

- final report SHA-256:
  `46357E7110FAF01F2F8AEA7AC6DF0EB40F8F5009F134313C1E2A7E4F9FCD2B67`;
- 271-file deployed inventory frozen with exact size and SHA-256;
- SQLite SHA-256:
  `2FC40F0F0D3D2BF9146120782A5ABBD74E783D6880D27A4A1B43499A974C35CB`;
- SQLite integrity `ok`, foreign keys clean, `user_version=7`;
- 2 projects, 59 artifacts/search rows, 2 reviews, 43 receipts;
- 0 Write documents, 0 Talk sessions, and 0 Release 0.8 local jobs;
- 51/51 public imported sources exact;
- 56/56 Worker Harness evidence files exact;
- registry generation 4 and active attachments 0;
- launcher SHA-256:
  `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`;
- ports 8787, 8875, and 8797 closed;
- 139 Python and 31 JavaScript tests plus syntax, compile, smoke, isolated API,
  Worker Harness, and Artifact Inspection checks passed before implementation.

The baseline contains historical bytecode files. They remain unchanged and are
not payload members. Release 0.8 deploys no cache or bytecode.

Git history is unavailable, so release truth is files, hashes, reports,
rollback evidence, SQLite, receipts, tests, and observed runtime behavior.

## Alignment outcome

`FOUNDATION_RELEASE_0.8_ARTIFACT_COMPASS.md` records the required KEEP, REPAIR,
COMPLETE, TEST, DEFER, CUT, and REJECT decisions.

The release keeps the current architecture: one loopback companion, one
Workshop SQLite database, registered artifacts, projects, receipts, the
existing `jobs` table, Talk, Write, My Work, Worker Harness, and Artifact
Inspection.

It retires the owner-writable arbitrary generic job route and rejects earlier
unbounded `/read-file`, `/scan-folder`, shell, Python, filesystem, network,
plugin, attachment, activation, and module-promotion shapes.

## First nanite crew

### Approved Text Reader

Reads one explicitly selected registered UTF-8 text source, current Talk, or
current Write document. It reports exact encoding, size, character count, line
count, content, and source hash. It never accepts an owner-language path or
modifies the source.

### Code Structure Inspector

Reuses the existing deterministic lexical inspection behavior. It reports
proven counts, imports/dependencies, functions, classes, and TODO/FIXME
markers. Probable language and repeated-line findings are separately labeled
heuristic. Source is never executed and semantic understanding is not claimed.

### Note Proposal Worker

Uses only selected current Talk, Write, or registered artifact content. It
shows a complete proposed note before mutation. Separate result approval
creates exactly one draft note, preserves the source, and never attaches or
activates it. Exact rollback removes only the unchanged note bound to that job
and hash.

### Package Manifest Validator

Reads one registered JSON manifest or ZIP. It validates canonical member paths,
member count, expanded-size limits, duplicates, symlinks, encryption facts,
expected members, unexpected members, and hashes where evidence permits. It
never extracts to disk, installs, executes, imports, or activates the package.

## Contracts and packet

`docs\LOCAL_API_WORKER_KIT_0.8_CONTRACT.md` defines four stable Worker Cards,
strict routes and fields, state transitions, approval, transactions, receipts,
recovery, cleanup, and certification limits.

`docs\WORKER_PACKET_0.8_CONTRACT.md` defines `worker-packet-v1`: one source
reference, minimum selected content, purpose, required and prohibited
permissions, expected output, limits, provenance, and validation. Canonical
packet, plan, source, contract, implementation, and output hashes bind the
lifecycle.

No packet contains unrelated project history, private archives, reviews,
credentials, settings, attachments, or permissions.

## API and state

The fixed internal API supports:

- worker list and capability inspection;
- eligible registered source list;
- plan creation and explicit approval/rejection;
- execution of only the approved fixed worker;
- job status and history;
- safe cancellation;
- interruption recovery;
- unaccepted output and evidence inspection;
- result approval/rejection;
- exact Note Proposal rollback;
- safe terminal history cleanup with receipts preserved.

Normal state is:

`planned -> plan_approved -> running -> awaiting_result_approval ->
result_approved`

Stale, abandoned, failed, interrupted, recovered, cancelled, rejected, and
rolled-back states are explicit. A process restart turns `running` into
unaccepted, unattached, inactive `interrupted` evidence. Recovery is
idempotent and returns only to the still-current approved plan.

## Owner-facing integration

Talk and Write expose actions for their open saved source. Selected text is
passed only when present for a note. My Work shows four owner-facing Worker
Cards, eligible source titles, supported actions, a plain-language plan,
running/failure/completion state, unaccepted result, decision state, receipt
evidence, rollback availability, and job history. No technical identifier is
required for ordinary use.

Dynamic source names and worker output are inserted with text nodes or
read-only textarea values. Hostile markup remains literal.

## Security boundaries

- loopback-only companion;
- fixed worker and route allowlists;
- `application/json`, cross-site, field, request-size, and output validation;
- canonical project/source containment and traversal, junction, symlink, ZIP
  member, member-count, expanded-size, and hash controls;
- source, selection, plan, packet, contract, implementation, and expiry gates;
- bounded two- or five-second runtime contracts;
- SQLite busy-timeout, write lock, immediate transactions, and rollback;
- no shell, subprocess, dynamic Python, `eval`, arbitrary path, network worker,
  plugin installation, self-modification, import, attachment, activation, or
  promotion;
- validated output is evidence, not approval;
- approval does not imply attachment or activation.

## Candidate verification

| Gate | Result |
|---|---|
| Authenticated Release 0.7 baseline | PASS — 271 exact files and protected state |
| Existing Release 0.7 regression | PASS — 139 Python, 31 JavaScript |
| Full Release 0.8 Python suite | PASS — 153 passed |
| Full Release 0.8 JavaScript suite | PASS — 36 passed |
| JavaScript syntax | PASS — 10 files |
| Python compile-all | PASS — external bytecode root |
| Smoke and isolated API E2E | PASS |
| Worker Harness and Artifact Inspection E2E | PASS |
| Worker Kit backend/API/security/recovery tests | PASS |
| Fixed worker and packet contracts | PASS |
| Malicious worker ID and unsupported field rejection | PASS |
| Traversal, malformed project, oversized input, unsafe ZIP | PASS |
| Stale plan, duplicate execution, expiry, timeout | PASS |
| Blank plan/result approval notes | PASS — client and server |
| Cancellation and restart recovery | PASS |
| Result rejection and note approval/rollback | PASS |
| Real Chromium desktop lifecycle | PASS — all four workers |
| Browser refresh with approved job | PASS |
| Service-worker cache | PASS — only `twis-holo-full-v8` |
| Mobile | PASS — 390×844, document/body width 390 |
| HTML/imported-text/output escaping | PASS |
| Browser console and page errors | PASS — 0 errors, 0 warnings |
| Browser network | PASS — 185 observed requests, all loopback |

The final disposable browser run produced:

- Approved Text Reader: result explicitly rejected;
- Code Structure Inspector: plan survived refresh and result approved;
- Note Proposal Worker: selected Write passage proposed, approved, and exactly
  rolled back;
- Package Manifest Validator: two expected members and hashes exact, result
  approved;
- all four jobs unattached and inactive;
- 17 total job evidence rows;
- no executed hostile markup;
- desktop and 390-pixel screenshots plus machine-readable browser evidence in
  the external Release 0.8 verification workspace.

## Defects repaired before freeze

1. The generic `/api/jobs` route accepted arbitrary inert operation names and
   returned raw payloads. It now returns HTTP 410; fixed worker routes are the
   only Release 0.8 job API.
2. A Windows short-form temporary path could fail a lexical isolated-E2E
   containment assertion against the same long-form path. Resolving both sides
   restores the real check.
3. Package unexpected members were reported but did not initially fail
   validation. They now fail whenever expectations were supplied.
4. Registered file drift initially surfaced only as a stored-hash mismatch. It
   now marks and reports the approved plan stale.
5. Talk eligibility initially risked using entry count as bytes. It now uses
   the current transcript's UTF-8 byte count.
6. Fast navigation from Talk/Write to My Work could submit the prior source
   while eligibility refreshed. Plan preparation is disabled during refresh,
   old review panels hide during creation, and the current source must settle.
7. Approval notes could visually persist between different jobs. Both plan and
   result notes now clear when job identity changes.
8. Generic label CSS overrode note-only `hidden` fields after switching
   workers. The Worker Kit now enforces its hidden state explicitly.
9. A malformed database project ID required defense beyond normal `safe_id`
   creation. Registered source resolution now independently verifies the
   canonical project boundary.

Each repair was followed by focused regression; the final browser run and
complete suites use the corrected candidate.

## Deployment scope and protected exclusions

The candidate currently has 11 replacements and 11 additions, with no
removals. The exact authenticated manifest is
`FOUNDATION_RELEASE_0.8_CANDIDATE_MANIFEST.txt`.

The payload contains no `data/**`, SQLite, cache, bytecode, browser profile,
screenshot, log, temporary directory, runtime output, or owner product row.
It does not include or modify the launcher, imported sources, private archives,
reviews, permissions, projects, receipts, Worker Harness evidence, registry,
or attachments.

`FOUNDATION_RELEASE_0.8_DEPLOYED_VERIFICATION.md` is postdeployment evidence
and is not a candidate payload member.

## Deliberate limits

Release 0.8 does not add the complete Tool Registry UI, universal prompt or
handoff building, folder salvage, module promotion, providers, models, cloud
workers, folder scanning, creative generation workers, natural-language
routing, or multi-agent crews.

The narrow owner guide is
`docs\LOCAL_API_WORKER_KIT_0.8_OWNER_GUIDE.md`.
