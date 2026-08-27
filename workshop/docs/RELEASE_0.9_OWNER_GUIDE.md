# Release 0.9 Owner Guide

Open **My Work** and use **Prepare work for its next destination**.

1. Check one or more registered sources. The title, type, ID, hash, byte size, project, protection state, and current-state label keep duplicates distinguishable.
2. Choose **Handoff Builder** or **Prompt Builder**.
3. Choose one supported destination profile and enter a concrete goal.
4. Select **Prepare hash-bound plan**. Review what will be read, what may be created, and what remains prohibited.
5. Add an approval note and approve the plan. Generation is still a separate action.
6. Select **Generate proposal**, read the complete proposal, and inspect its validation state.
7. Approve or reject the proposal. Approval does not save, export, send, attach, activate, or execute it.
8. After approval, optionally save one inactive draft or export a plain-text/JSON copy. These remain separate explicit actions.
9. A saved draft appears in My Work and can be rolled back from its builder job. Rollback removes only that unchanged draft; source records and receipts remain.

The same **Build Handoff** and **Build Prompt** entry actions are available from Talk, Write, Artifact Inspection, and approved worker-result history. They open the same governed workspace; they do not silently add or scan sources.

If a source changes after planning or generation, the Workshop blocks the stale plan or result. Prepare a new plan from current evidence. If a run was interrupted, the job is classified as interrupted and offers recovery or safe cancellation; it does not silently resume a mutation.

Release 0.9 deliberately does not submit to Codex, ChatGPT, a local model, another provider, or a human. Copy or use the explicit local export yourself after review.
