# Transaction, Receipt, and Recovery Foundation

`companion/foundation/transactions.py` supplies bounded evidence and recovery helpers for cooperating local workflows.

## Manifest lifecycle

States are `prepared`, `in_progress`, `committed`, `failed`, `recovery_pending`, and `recovered`. The manifest records transaction ID/generation, actor/action, paths, before/after hashes, permission decision, commands, tests, timestamps, result, recovery point, and optional approval evidence.

Machine-readable contract: `schemas/transaction-manifest-v0.2.schema.json`.

## Receipts

Terminal operations append individual JSON receipts with a sequence number, the previous receipt hash, and their own SHA-256. Verification detects changed content, broken links, and sequence gaps.

These receipts are tamper-evident only. They are not digital signatures, immutable storage, trusted timestamps, or proof of actor identity. A privileged writer could replace an entire chain.

## Recovery points

- File snapshots copy one explicit file, verify its SHA-256, and restore only to a path permitted for writes.
- SQLite backup uses the SQLite backup API from a read-only source connection and requires `PRAGMA integrity_check = ok`.
- Restore refuses an existing destination by default.
- Interrupted nonterminal manifests are discoverable and can be recorded as recovery-pending, failed, or recovered.
- Evidence paths are rechecked through the read/write path policy before hashing.

## Limits

This is not a filesystem journal, distributed transaction coordinator, process sandbox, multi-process locking service, archive repair tool, or whole-machine rollback. It does not automatically wrap current Workshop routes. Recovery tests operate on temporary fixtures only; Release 0.2 does not restore or migrate the live Workshop database.
