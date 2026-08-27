# Foundation Release 0.7 — Talk Room Artifact Compass

Date: 2026-07-26  
Scope: recovered TalkBox evidence and the smallest durable daily-use Talk slice

## Authority map

The authenticated deployed Release 0.6 Workshop remains authoritative:
application shell, local companion, SQLite artifact/search/project/receipt
store, Release 0.6 Write documents, Worker Harness, governed Artifact
Inspection, service worker, launcher, imported sources, reviews, and protected
archives. Release 0.7 extends those systems; it does not establish TalkBox as a
separate product authority.

## Recovered source and provenance

The protected archive
`private_source_artifacts\source_artifacts\TWIS_TALKBOX_BUILD_FOLDER.zip`
authenticated against its source receipt at:

`5B8F34A7F3252D6066436C1306F86FC1A4BFDCA7BB910EE36C29530286F0660D`

It contained 19 entries: TalkBox plans, a small Python application skeleton,
filesystem and TTS placeholders, a deterministic Code Buddy sketch, adapter
plans, and module/config notes. Every member was extracted outside the active
Workshop and inspected. Searches of neighboring release/session evidence found
no newer authoritative Talk implementation.

The archive contains no explicit license grant. Therefore no executable
TalkBox source was copied into Release 0.7. Product intent and requirements
were treated as evidence; the implementation was written anew against the
existing Workshop contracts.

## Classification

| Class | Recovered material | Release 0.7 decision |
|---|---|---|
| KEEP | local-first, free-first Talk intent | Preserved as a text-complete local room with no provider dependency. |
| KEEP | small deterministic code-inspection idea | Reimplemented as bounded lexical inspection of selected pasted code. |
| KEEP | adapters must not become authority | Voice capability remains a replaceable browser adapter; unavailable is truthful. |
| KEEP | TTS-before-STT caution | Local read-aloud can be used when locally installed voices are proven; STT stays disabled without stronger proof. |
| REPAIR | separate TalkBox application/database/files | Integrated into existing Workshop artifacts, project identity, My Work, SQLite, recovery, versions, receipts, and Write. |
| REPAIR | `startswith` path containment | Replaced with resolved-path ancestry checks and bounded export filenames. |
| REPAIR | incomplete save/recovery concepts | Completed with immediate browser recovery, durable SQLite recovery, optimistic concurrency, visible states, and restart recovery. |
| COMPLETE | title, ordered entries, stable identity, timestamps | Implemented as versioned Talk conversation artifacts. |
| COMPLETE | history, compare, restore, undo, marked passages | Implemented with immutable snapshots and recovery-first restore. |
| COMPLETE | Talk-to-Write | Explicit preview, non-blank approval, normal Write document, relationship, receipt, stale gate, and safe rollback. |
| COMPLETE | TXT/Markdown/JSON export | Atomic local exports, receipt hashes, provenance excluded by default and opt-in only. |
| COMPLETE | My Work integration | Project, title, saved/recovery state, entry/version counts, open/history/export/transfer actions. |
| TEST | archive origin/hash and absence of license | Authenticated; absence of a license prevented code import. |
| TEST | voice/local/network claims | Audited against current primary specifications and tested in a real browser. |
| TEST | interruption, service restart, service worker, mobile | Exercised in disposable real browser state. |
| TEST | path, request, conflict, escaping, concurrency | Covered by backend/API/UI suites and exact source scans. |
| DEFER | model adapters and local-model management | Not required for a complete text Talk and would widen runtime/license obligations. |
| DEFER | full Code Buddy and IDE behavior | Existing deterministic inspection is sufficient for Release 0.7. |
| DEFER | language-pack installation | Release 0.7 never installs a speech pack; on-device STT must already be proven available. |
| CUT | separate TalkBox server/database/file store | Would split identity, recovery, search, provenance, and receipts. |
| CUT | placeholder brain/filesystem/TTS notes | They are plans, not authenticated capability. |
| REJECT | arbitrary file read/write and tool execution | Violates the Workshop boundary and is unnecessary. |
| REJECT | prefix-only path checks | Unsafe on sibling-prefix paths. |
| REJECT | automatic browser SpeechRecognition fallback | Recognition may use a server; Release 0.7 requires explicit local proof. |
| REJECT | hidden network/model/worker activity | No provider endpoint, model, arbitrary worker, or automatic activation exists. |

## Voice primary-source audit

- The current Web Speech API specification distinguishes recognition that may
  use a platform or remote service and provides `processLocally`, `available`,
  and language-pack mechanisms for explicit on-device recognition:
  https://webaudio.github.io/web-speech-api/
- Chrome's speech-synthesis documentation states that `SpeechSynthesisVoice`
  exposes `localService`, and notes that synthesis services may be local or
  remote:
  https://developer.chrome.com/blog/web-apps-that-talk-introduction-to-the-speech-synthesis-api
- Microsoft documents installed Windows voices and the operating-system
  language/voice configuration surface:
  https://support.microsoft.com/windows/download-languages-and-voices-for-immersive-reader-read-mode-and-read-aloud-4c83a8d8-7486-42f7-8e46-2b0fdf753130

Decision: the browser adapter enables STT only when `processLocally` and
`available()` prove the installed language is available. It does not call
`install()`. Otherwise the UI says local STT is unavailable and network
recognition is disabled. TTS lists only `localService=true` voices and exposes
play, pause, stop, completion, and failure. Browser capabilities carry their
platform/browser licenses; Release 0.7 ships no voice engine, model, or voice
asset and adds no runtime license obligation.

## Dependency and safety result

Release 0.7 adds no runtime package, provider, API key, model, account,
telemetry, hosted storage, network worker, shell, or new storage engine.
Standard-library Python, native browser controls, the existing SQLite
authority, and the existing guarded Workshop rooms are sufficient.

