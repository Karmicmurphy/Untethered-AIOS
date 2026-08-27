# Kernel V0.2 Restart Packet

## Resume point

- Repository: `C:\Users\Olli_Twis\Documents\ChatGPT\New project`
- Branch: `bootstrap/workshop-baseline`
- Phase 0 commit: `c3ce1cf`
- Artifact Compass commit: `cca5026`
- Kernel V0.2 implementation commit:
  `dde57590c2df28274271ff3bec171d4e850f81e6`
- Authenticated Workshop tree:
  `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`

Read `AGENTS.md`, `CODEX_START_HERE.md`, `STATUS.md`, and
`evidence/KERNEL_V0_2_VERIFICATION.md` before continuing.

## Safe resume checks

```powershell
Set-Location -LiteralPath 'C:\Users\Olli_Twis\Documents\ChatGPT\New project'
git status --short --branch
$env:PYTHONPATH = 'src'
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe scripts\demo.py
```

The demo is synthetic and proves no Workshop integration.

## Candidate rollback

The non-destructive history-preserving rollback is a revert of the bounded
implementation commit on the candidate branch:

```powershell
git revert dde57590c2df28274271ff3bec171d4e850f81e6
```

This was simulated in a disposable worktree: the reverse result equaled
`cca5026` and its 13 baseline tests passed. Do not use reset/checkout commands
against the authoritative Workshop.

## Authority boundary

`C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS` remains read-only. Do not rebuild or
restart Music Loop Deck V1. Do not copy, integrate, deploy, publish, activate a
paid provider, widen credentials, or alter persistent live state without a new
explicit owner approval.

## Next bounded work

Design and prove one read-only Workshop capability adapter entirely in this
candidate repository. Do not describe it as working integration until the
adapter, kernel path, receipts, and integration test all pass.
