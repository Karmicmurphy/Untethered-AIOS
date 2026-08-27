# Foundation Release 0.16 — Complete Workshop Room Pass

Release 0.16 completes the current fourteen-room Workshop foundation without adding an execution engine or changing database authority.

Build now provides the fixed `build-work-order-builder`. It prepares a deterministic technical work order from zero to four ordered registered text sources and/or hash-identified temporary owner input. It cannot execute code or shell commands, modify files, submit to Codex, contact a provider, or deploy.

Modules now provides an honest static local capability registry plus the fixed `module-proposal-builder`. The proposal builder documents a future module without installing packages, downloading assets, executing code, activating capability, or contacting a provider. Disabled registry entries are explicitly labeled inactive rather than installed or ready.

Both tools use `builder-output-v1`, exact source hashes, separate plan and result approval, one inactive draft, explicit TXT/Markdown/JSON export, My Work reopening, receipt-backed recovery, stale-source rejection, and exact rollback. Temporary inputs use `build-input:<SHA-256>` and `module-input:<SHA-256>` identities over canonical owner notes and controls.

Settings already provides genuine local presentation and identity preferences, including reduced-motion mode, persisted in local browser storage. It is preserved without a new schema or system-level settings access.

SQLite `user_version` remains 13. No database replacement, provider integration, network retrieval, package installation, automatic execution, or source mutation is introduced.
