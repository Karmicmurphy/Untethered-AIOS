# Open Questions After Foundation Release 0.4

These are deferred decisions, not incomplete Release 0.4 acceptance criteria.

1. Which additional importer-defined roots, if any, can be proven public-safe without weakening the current `docs` boundary?
2. Should future inspection formats include `.csv`, and what deterministic schema/size rules would be required first?
3. What cross-process lock and reconciliation model is required before more than one companion process may share harness state?
4. Should receipts eventually use authenticated signing? Current hash links detect changes but do not establish identity or immutability.
5. Should more than one inspection report per artifact be active at once, or should later reports explicitly supersede/roll back earlier attachments?
6. Should any future release add deterministic language-specific parsing beyond bounded lexical declarations, and how will malformed input remain fail-closed?

AI/model inspection, vector search, artifact repair, arbitrary/generated workers, TalkBox promotion, voice routing, autonomous repair, and broader architecture remain separately scoped work.
