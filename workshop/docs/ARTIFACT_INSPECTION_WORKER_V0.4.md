# Artifact Compass Inspection Worker v0.4

`artifact-compass-inspection-worker` is a fixed, deterministic, read-only Worker Harness capability. It analyzes one explicitly selected public-safe text artifact and produces one structured JSON candidate report.

## Eligibility

Release 0.4 recognizes only FlashRiver importer `docs` roots as public-safe. Eligible extensions are `.txt`, `.md`, `.json`, `.py`, `.js`, `.html`, and `.css`.

Selection rejects private authority/roots, archives, databases, executables, binaries, invalid UTF-8, files over 512 KiB, unsupported extensions, missing files, stored/current hash mismatches, traversal, sibling-prefix escapes, and symlink/junction paths. Structurally private or out-of-root files are rejected without reading their contents.

## Output

The canonical JSON report contains artifact identity/path/hash/type, byte/line/word counts, bounded headings/code symbols/links/TODO markers, a transparent rule-labeled `heuristic_not_fact` purpose, exact-hash duplicate records and paths, safe provenance references, review status, warnings, plan-bound timestamp, and inspector version.

Headings, symbols, links, and markers are capped at 256 entries each. Excess is reported as a deterministic warning. Output is capped at 128 KiB.

## Inert-content rule

The worker never imports inspected code, evaluates expressions, renders HTML/Markdown, follows links, or treats embedded instructions as commands. Prompt-like text and active markup produce inert-content warnings. No AI model is installed or used.

## Approval and attachment

Execution produces `awaiting_approval`; it never attaches automatically. Approval binds candidate, source, Worker Card, plan, and generation hashes plus actor, note, and timestamp.

Activation associates the approved report with the artifact through the existing activation registry. Artifact bytes, SQLite rows, review status, permissions, and startup behavior remain unchanged. Rollback restores bounded output and marks the attachment rolled back.

## Honest limits

This is trusted fixed standard-library code constrained by application checks, fixed argv, `shell=False`, timeout, bounded streams, path policy, hashes, and file-effect verification. It is not an OS sandbox. Network denial is not an OS firewall. Human identity and receipts are not cryptographically authenticated.
