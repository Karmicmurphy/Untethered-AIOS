# Workshop Read Adapter V0.1 Restart Packet

## Resume point

- Repository: `C:\Users\Olli_Twis\Documents\ChatGPT\New project`
- Branch: `successor/workshop-read-adapter-v0.1`
- Reconciled base: `f93dfcbda3831bc918d42c8ff3f298af6e7681fe`
- Implementation commit:
  `1ba5800e598b4b3063e68541d95625cffeac6133`
- Implementation tree: `fa149d97cc5a7a76eb699053082744f163c76243`
- Authenticated Workshop tree:
  `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`

Read `AGENTS.md`, `CODEX_START_HERE.md`, `STATUS.md`, and
`evidence/WORKSHOP_READ_ADAPTER_V0_1_VERIFICATION.md` before continuing.

## Safe resume checks

```powershell
Set-Location -LiteralPath 'C:\Users\Olli_Twis\Documents\ChatGPT\New project'
git status --short --branch
git rev-parse HEAD
$env:PYTHONPATH = 'src'
.\scripts\test.ps1
.\.venv\Scripts\python.exe -m unittest tests.test_workshop_read_adapter -v
```

The adapter tests use a disposable database and public-file fixture. They do
not open the authoritative live Workshop database.

## Candidate rollback

The history-preserving rollback is:

```powershell
git revert 1ba5800e598b4b3063e68541d95625cffeac6133
```

This was simulated in a disposable worktree. The reverse tree exactly equaled
the reconciled base tree and its 37 baseline tests passed. Do not use reset,
checkout, or file-copy commands against the authoritative Workshop.

## Authority boundary

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS` remains read-only. Do not deploy or
integrate this candidate, open a write lane, rebuild/restart Music Loop Deck V1,
checkpoint live SQLite, publish another branch, activate a paid service, widen
credentials, or alter live persistent state without a separate explicit owner
approval.

## Exact stop and next gate

Workshop Read Adapter V0.1 candidate verification is complete. No later
successor has begun.

The next recommendation is a separately approved owner/live-read validation
gate for this same one capability, using an immutable/read-only data lane and
an owner-selected public artifact. Do not add a second adapter or live
deployment work as part of that gate without explicit scope and approval.
