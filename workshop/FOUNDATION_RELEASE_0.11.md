# Foundation Release 0.11 — Evidence Compare

Release 0.11 adds the first governed Explore/Research tool without replacing the Release 0.10 builder lifecycle.

`evidence-compare` is one fixed deterministic worker. It accepts two to eight explicitly selected registered readable text sources, retains source order and exact SHA-256 values, and supports seven allowlisted comparison focuses.

The result is a `builder-output-v1` comparison workspace containing source inventory, provenance, per-source claim capture, exact textual agreement and difference matrices, unassessed contradiction and evidence-gap registers, unresolved questions, a synthesis outline, and completion instructions. It never presents exact textual overlap as semantic agreement and never fabricates conclusions, live research, provider analysis, or model output.

Plan approval, execution, result approval, inactive saving, export, and rollback remain separate. A saved result is one inactive `research-comparison-draft`; TXT, Markdown, and JSON exports remain explicit and local. Every registered parent source receives a provenance relationship and remains unchanged.

Release 0.11 advances SQLite `user_version` from 10 to 11 transactionally without changing table schema or replacing the database.
