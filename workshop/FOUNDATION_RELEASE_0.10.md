# Foundation Release 0.10 — Draft Workshop

Release 0.10 adds the first practical governed Write Room tool without replacing the Release 0.9 Worker Kit.

`draft-workshop` is one fixed deterministic worker. It accepts exactly one current registered text source or one owner-entered rough-text value and supports five allowlisted operations: Rewrite clearly, Shorten without losing meaning, Expand rough notes, Change tone, and Organize into a structured document.

The worker creates a hash-bound `builder-output-v1` writing task and draft scaffold. It is explicit that no language model generated prose. Plan approval, execution, result approval, inactive draft saving, export, and rollback remain separate owner actions. A saved result is one inactive `writing-draft`; TXT and Markdown exports remain local. Original sources are never modified.

Release 0.10 advances SQLite `user_version` from 9 to 10 transactionally, changes no table schema, preserves every existing row, and reuses existing jobs, evidence, relationships, receipts, recovery, export containment, and rollback controls.

Deliberate exclusions include external provider/model calls, prompt execution, automatic submission, source overwrite, unrestricted scanning, shell or Python worker execution, autonomous workers, plugin installation, MCP execution, attachment, activation, publication, and promotion.
