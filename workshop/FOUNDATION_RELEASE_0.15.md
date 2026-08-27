# Foundation Release 0.15 — Video Production Brief Builder

Release 0.15 turns the Video room into a genuine governed shot-planning station without adding video generation or replacing the accepted Release 0.14.2 shell.

`video-production-brief-builder` accepts zero to four ordered registered readable text sources and/or nonblank temporary owner video notes. Registered sources retain their exact identities and SHA-256 values. Temporary notes use the deterministic identity `video-notes:<SHA-256>` and are not silently registered.

The fixed worker prepares a deterministic `builder-output-v1` production brief covering format, sequence, subjects, locations, visual and camera direction, movement, shots, transitions, audio, continuity, constraints, safety, unresolved decisions, and a manual-use handoff block. It does not interpret source meaning or fill missing choices; those remain `Unresolved production decision`.

Plan approval, generation, result approval, inactive saving, and export are separate explicit actions. An approved result may be saved once as `video-production-brief-draft`, exported as UTF-8 TXT, Markdown, or JSON, reopened from My Work, recovered after refresh or restart, and rolled back only while the created draft remains exact.

No video model, renderer, cloud provider, paid API, external network request, background render, automatic submission, attachment, activation, publication, promotion, shell worker, or source mutation is introduced. The existing schema represents the lifecycle, so SQLite `user_version` remains 13 and no database replacement or migration occurs.
