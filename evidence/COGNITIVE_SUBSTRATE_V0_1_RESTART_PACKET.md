# Cognitive Substrate V0.1 restart packet

## Resume identity

- Branch: `successor/cognitive-substrate-v0.1`
- Rollback base: `acf981b15de4b098659e0f74b28465d288a97e0b`
- Verified implementation: `a329349ca8483396d49e142082dd0c8c5dec034e`
- Authoritative Workshop: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`
  (read-only; not deployed)

The selected base contains verified Kernel V0.2, Workshop Read Adapter V0.1,
and its live-read validation, while owner-surface work remains separate.

## Reverify

```powershell
Set-Location '<candidate checkout>'
$env:PYTHONPATH = Join-Path (Get-Location) 'src'
python -m unittest tests.test_attention_governor tests.test_computation_memory tests.test_cognitive_benchmark tests.test_cognitive_contracts -q
python scripts\run_cognitive_benchmark.py --output evidence\cognitive-substrate-v0.1-benchmark.json
.\scripts\test.ps1
python -m compileall -q src scripts tests
python -c "import glob,json; [json.load(open(f,encoding='utf-8')) for f in glob.glob('contracts/*.json')]"
python scripts\demo.py
git diff --check
```

Expected: 14 focused, 63 complete, nine correct benchmark routes, six parsed
contracts, and all remaining checks pass. Regenerating the benchmark changes
timing measurements; commit it only after rerunning the complete proof.

## Exact rollback

Create a detached worktree at the rollback base above. Its preserved 49-test
suite passed in this campaign; the simulation worktree was removed. Do not
destructively reset another active checkout.

## Next bounded recommendation

Campaign 2 should be a Kernel-owned Reflex/Rule Execution Bridge V0.1 with one
deterministic handler and computation reuse. It requires a new explicit
instruction. Do not begin it from this packet automatically.

## Stop boundary

Do not modify/deploy into the live Workshop, restart Workshop/Music, merge the
owner surface, add a real model/provider/network path, widen permissions,
publish externally, or start Campaign 2 without a new instruction.
