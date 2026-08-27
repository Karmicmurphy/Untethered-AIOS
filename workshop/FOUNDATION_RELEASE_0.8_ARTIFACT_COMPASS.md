# Foundation Release 0.8 Artifact Compass

Date: 2026-07-26  
Scope: Local API Worker Kit / First Nanite Crew

## Evidence boundary

This alignment pass was performed against the authenticated deployed Release
0.7 tree, its final report, the live SQLite schema and counts, current browser
and API behavior, the four fixed Worker Harness layers, Write and Talk
contracts, FlashRiver public planning documents, and the complete test suite.

Git history is unavailable in this supplied installation. Authority therefore
comes from current files, exact hashes, deployment and rollback reports,
SQLite, receipts, tests, and runtime behavior. Protected imported sources,
private archives, reviews, permissions, launcher state, and Worker Harness
evidence are reference-only and are not implementation targets.

The pass rejects a parallel application or database. Release 0.8 extends the
existing loopback companion, `jobs` table, artifacts, projects, receipts,
Talk, Write, and My Work.

## Classification

### KEEP

| Component | Evidence | Release 0.8 use |
|---|---|---|
| Loopback companion API | `companion/server.py` binds `127.0.0.1` | Remains the single internal API boundary |
| SQLite authority | Existing projects, artifacts, FTS, jobs, receipts, reviews, Write, Talk, modules | Extended in place with one evidence table and `user_version=8` |
| Worker Harness | Fixed Worker Cards, plans, candidates, approval, attachment, rollback, receipts | Preserved as the governed promotion/attachment system; not duplicated |
| Artifact Inspection worker | Existing public-artifact selection, hash binding, lexical inspection | Reused through the same deterministic inspection function and source identity rules |
| Write proposals | Source-preserving proposal, explicit decision, rollback | Remains the specialized writing mutation workflow |
| Talk actions | Durable transcripts, code inspection, bounded command classifier | Supplies registered Talk sources to fixed local workers |
| Talk-to-Write | Separate preview, approval note, source preservation, rollback | Preserved; worker notes do not bypass it |
| Artifact storage and FTS | Stable artifact identity plus source hash and project ownership | Registered artifact identity is the only worker source selector |
| Projects | Existing project boundary | Every plan and job is project-bound |
| My Work | Existing owner-facing artifact inventory | Gains worker planning and job history without exposing required IDs |
| Receipts | Existing durable append-only action evidence | Records plan, decisions, execution, note creation, rollback, recovery, cancellation, and cleanup |
| Attachments | Existing Worker Harness attachment registry | Worker Kit results stay explicitly unattached |
| Rollback | Existing exact-output rollback patterns | Note worker removes only its unchanged job-bound note |
| Worker Cards | Existing validated authority projection | Extended with four versioned contracts and implementation hashes |

### REPAIR

| Component | Problem found | Repair |
|---|---|---|
| Generic `/api/jobs` endpoint | Accepted arbitrary operation names and exposed raw payloads, although it did not execute them | Retired with HTTP 410; fixed worker routes are the only Release 0.8 job API |
| Isolated API path assertion | A Windows short-path `TEMP` spelling could compare unequal to the server's long-path spelling | Test now resolves both paths before containment comparison |
| Talk source eligibility size | Prior draft logic could confuse transcript entry count with input bytes | Current transcript UTF-8 bytes govern eligibility |
| Package validation result | Unexpected members were reported but did not initially make validation fail | Unexpected members now fail validation whenever an expected member set was supplied |
| File-source staleness | A changed registered file first appeared as a registry-hash mismatch | Execution converts current-source changes into a visible stale plan and records the reason |

### COMPLETE

Release 0.8 completes these previously missing connections:

- four fixed, versioned local worker contracts;
- bounded worker packets containing only source reference, minimum selected
  content, purpose, permissions, output expectation, limits, and provenance;
- plan creation, approval/rejection, execution, status, cancellation, restart
  recovery, result approval/rejection, note rollback, history, and safe cleanup;
- source, packet, plan, contract, implementation, and output hash binding;
- abandoned-plan expiry, stale-source blocking, duplicate-run protection, time
  and output limits, SQLite transactions, and failure receipts;
- Talk and Write actions that pass their currently open saved artifact and only
  selected content where present;
- My Work worker cards, plain-language plan, unaccepted result review, evidence,
  receipts, rollback state, and job history;
- safe terminal history deletion that preserves receipts and unrelated work.

### TEST

The following are retained but require continuous regression evidence:

- Worker Harness approval, attachment, rollback, source immutability, and
  registry generation;
- Artifact Inspection selection, duplicate distinction, and lexical claims;
- Write recovery, versions, proposals, exports, and rollback;
- Talk recovery, versions, transfers, voice truth, code inspection, exports,
  and rollback;
- SQLite integrity, FTS parity, protected counts and hashes;
- path containment, reparse-point rejection, traversal rejection, input and
  archive bounds;
- worker interruption, stale plans, blank notes, duplicate execution,
  cancellation, timeout, result validation, and exact note rollback;
- desktop and 390-pixel browser lifecycle, refresh, service-worker cache,
  escaping, console, and loopback-only requests.

### DEFER

These are real future extensions, deliberately outside Release 0.8:

- complete Tool Registry interface;
- universal natural-language, prompt, or handoff builders;
- universal Artifact Compass folder salvage;
- module promotion from Worker Kit results;
- external provider routing, local-model installation, cloud workers, and
  network workers;
- unrestricted folder scanning;
- creative-room generation workers;
- autonomous or multi-agent crews.

The packet and contract schemas are replaceable so later implementations can
add these capabilities without changing the current safety boundary.

### CUT

- the owner-writable arbitrary generic job creation route;
- the raw generic job history response containing unprojected payload JSON;
- earlier FlashRiver plan suggestions for owner-supplied `/read-file` or
  `/scan-folder` paths;
- any plan to copy full project history or private archives into a job.

### REJECT

The following shapes are incompatible with Workshop authority and were not
built:

- arbitrary command, Python, shell, subprocess, filesystem, or network
  execution;
- arbitrary owner-language paths;
- worker IDs outside the fixed allowlist;
- hidden or self-modifying workers;
- automatic plugin installation, package installation, import, attachment,
  activation, startup execution, or module promotion;
- output treated as accepted merely because it validated;
- approval treated as permission to attach or activate;
- source mutation by read-only workers;
- rollback that removes unrelated owner work;
- certification beyond hashes, schemas, transactions, tests, and observed
  runtime evidence.

## Aligned Release 0.8 shape

The resulting design is one small extension of the existing Workshop:

1. The owner selects visible work in Talk, Write, or My Work.
2. The companion resolves its registered artifact identity and current hash.
3. One fixed contract produces a bounded packet and plain-language plan.
4. The owner separately approves the exact current plan.
5. The fixed in-process deterministic worker runs without network, shell, or
   arbitrary paths.
6. The output schema and size are validated.
7. The owner reviews a still-unaccepted result.
8. Approval records evidence; only Note Proposal approval creates one draft
   note.
9. Attachment and activation remain absent.
10. The unchanged created note can be rolled back exactly.
11. Terminal job history may be cleaned while receipts remain.

This is useful before it is expansive: four narrow workers, one packet
contract, one API boundary, and existing Workshop authority throughout.
