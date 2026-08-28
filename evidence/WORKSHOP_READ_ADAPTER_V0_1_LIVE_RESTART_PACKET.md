# Workshop Read Adapter V0.1 Live Validation Restart Packet

## Resume point

- Repository: `C:\Users\Olli_Twis\Documents\ChatGPT\New project`
- Branch: `validation/workshop-read-adapter-v0.1-live`
- Verified candidate start:
  `390e2cba9b4f1377642bcfe6fad9b47235fee556`
- Validation harness commit:
  `93637403ad69567edd0cfc38d42d1898acabbfde`
- Validation harness tree:
  `8d0dc4eb8c7197fac97c12baa92ff64b17f60588`
- Live result SHA-256:
  `5b8e7d3a2407a89b369937b70b7a0ed730a96a4f9207d6140a558775322d9a2e`
- Live capability receipt SHA-256:
  `1b7e15771337f7a5bde2fc6dee7b268a3625213ee7316bb5b1a601e460796157`
- Protected Workshop code-safe tree:
  `a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`

Read `AGENTS.md`, `CODEX_START_HERE.md`, and
`evidence/WORKSHOP_READ_ADAPTER_V0_1_LIVE_VALIDATION.md` before continuing.

## Safe repository checks

```powershell
Set-Location -LiteralPath 'C:\Users\Olli_Twis\Documents\ChatGPT\New project'
git status --short --branch
git log -3 --oneline
$env:PYTHONPATH = 'src'
.\scripts\test.ps1
```

Do not rerun the live harness casually. Its one fixed immutable read already
passed. A rerun is appropriate only when current live-read evidence is required
and the Workshop remains under the same explicit read-only authorization.

## Candidate rollback

The validation branch adds no Workshop changes. Its history-preserving
repository rollback is:

```powershell
git revert 93637403ad69567edd0cfc38d42d1898acabbfde
```

This removes only the validation harness. The authoritative Workshop needs no
rollback because its database, WAL, SHM, code-safe tree, configuration, and
service state were not changed by validation.

## Exact stop gate

Live-read validation is complete. Do not deploy, modify the Workshop, create
write authority, publish this validation branch, or begin a later successor
without a new explicit instruction.

The next recommendation is an owner-visible read-only integration candidate
for the same `workshop.artifact.read` capability. That is a separate live
integration/deployment gate and has not begun.
