# Release 0.10 Owner Guide — Draft Workshop

Open Write and select **Open Draft Workshop**. A saved Write document is preselected when available. You may instead clear the source selection and enter temporary rough text.

1. Choose exactly one registered text source or enter nonblank rough text.
2. Choose one of the five writing operations and add optional instructions.
3. Prepare and inspect the hash-bound plan.
4. Add an approval note and approve the plan.
5. Generate the proposal. The current local implementation prepares a ready-to-use writing task and scaffold; it does not pretend a model wrote new prose.
6. Review and separately approve or reject the result.
7. After approval, optionally save one inactive `writing-draft`, export TXT or Markdown, or later roll back the unchanged saved draft.

The original registered source is never overwritten. Source changes invalidate the plan or result. Refresh or restart recovery returns to the recorded safe state and does not silently resume a state-changing action. Draft Workshop never contacts ChatGPT, Codex, a local model, or another provider and never submits or executes an export.
