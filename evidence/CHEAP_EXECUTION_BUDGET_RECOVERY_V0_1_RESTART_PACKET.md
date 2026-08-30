# Cheap-Execution Budget and Recovery V0.1 restart packet

## Resume identity

- Branch: `successor/cheap-execution-budget-recovery-v0.1`
- Exact base: `bab64c263e337400e0a7b77bcebb47677cd701da`
- Verified implementation: `05e4dc3c08ba5eba7415d2b7c0b5c9d1c214680c`
- Implementation tree: `5f39063b2f2ffc8e8648d5135cf0dab016cd0c25`
- Authoritative Workshop: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`
  (read-only, unchanged, not deployed)

Campaign 2 was pushed normally and verified at the exact base above. Campaign
3 is a local candidate only and adds cooperative Kernel-owned budgets and
finite receipt-derived recovery to the existing single cheap handler lane.

## Reverify

```powershell
Set-Location '<candidate checkout>'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -c "import unittest; patterns=['test_reflex_execution_bridge.py','test_reflex_contracts.py','test_reflex_benchmark.py','test_execution_budget_recovery.py','test_budget_recovery_contracts.py','test_budget_recovery_benchmark.py']; loader=unittest.TestLoader(); suite=unittest.TestSuite(loader.discover('tests', pattern=p) for p in patterns); result=unittest.TextTestRunner(verbosity=1).run(suite); raise SystemExit(not result.wasSuccessful())"
python scripts\run_budget_recovery_benchmark.py
.\scripts\test.ps1
python -m compileall -q src tests scripts
python -c "import glob,json; [json.load(open(f,encoding='utf-8')) for f in glob.glob('contracts/*.json')]"
python scripts\demo.py
git diff --check
```

Expected: 24 focused, 89 complete, all 14 benchmark correctness predicates,
eight parsed contracts, 73/73 persisted benchmark receipts with all chains
valid, and all remaining checks pass. Benchmark timing and receipt hashes vary
between runs; regenerate only as part of a complete re-verification.

## Exact rollback

Create a disposable detached worktree at exact base
`bab64c263e337400e0a7b77bcebb47677cd701da`. Its clean preserved 75-test suite
passed during Campaign 3; the disposable worktree was removed. Do not
destructively reset an active checkout.

## Protected state

Before/final Workshop authentication produced identical stable manifests: 293
included files, 231 excluded private/runtime files, and code-safe tree
`a8db4ee742ad0a4c048bc02df0f14a24748d4d609f587a2f345f1fb304652d27`.
The compact comparison is in
`evidence/cheap-execution-budget-recovery-v0.1-protected-state.json`.

## Stop boundary

Do not push or deploy Campaign 3, modify/restart the Workshop or Music, add a
Workshop capability, add a real model/provider/network path, widen persistent
permissions, or start Campaign 4 without a new explicit instruction.

Recommended next bounded campaign, only after new authorization: one
deterministic RULE handler using these same budget, recovery, capability, and
Computation Memory contracts. No Campaign 4 work has begun.
