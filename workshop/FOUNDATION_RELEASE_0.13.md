# Foundation Release 0.13 — Song Production Brief Builder

Release 0.13 adds the first governed Music Room tool without replacing the Release 0.12 foundation.

`song-production-brief-builder` accepts zero to four ordered registered readable text sources, temporary owner music notes, and temporary owner lyrics. At least one source, meaningful notes, or meaningful lyrics is required. Registered sources remain exact. Temporary inputs use deterministic `music-notes:<SHA-256>` and `music-lyrics:<SHA-256>` identities and are not silently registered.

The worker creates a deterministic `builder-output-v1` production brief and manual-use prompt. It organizes only owner-supplied controls and exact source metadata. Missing choices remain `Unresolved musical decision`. Owner lyrics are reproduced exactly and are never completed or rewritten.

Plan approval, execution, result approval, inactive saving, and explicit export remain separate. An approved result may be saved once as `song-production-brief-draft`, exported explicitly as TXT, Markdown, or JSON, reopened from My Work, recovered after refresh/restart, and boundedly rolled back while receipts remain.

No music, audio, vocals, lyrics, melody, chords, instrumentation, or provider output is generated or played. There is no network retrieval, provider submission, publication, attachment, activation, promotion, shell worker, model execution, or source mutation.

The database migration advances `user_version` from 12 to 13 transactionally without replacing the database or changing existing rows.
