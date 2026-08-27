# TWIS Build + Modules V2 — Verification

Candidate root: `C:\TWIS_FLASHRIVER_REVIEW_READY\build-modules-v2-work\candidate\TWIS`

Live root: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`

Verification date: 2026-08-23 America/Chicago.

## Baseline

- Application files: 252; tree digest `9870D3F92839EB0A95583FFD7F60D55AE9A7D73B6CB6350CC29580F143223189`.
- SQLite SHA-256: `CD79502D2800D32DA54B2F942CBAF4B1381B202F2F2223658FD85BD077AF326F`.
- SQLite integrity: `ok`; foreign-key violations: 0; `user_version`: 13.
- Owner project files: 62, exact hashes frozen in the external baseline evidence.
- Runtime assets: 3 external portable FFmpeg files; no runtime is part of this candidate.
- Baseline suites: Python 210 passed; JavaScript/UI 77 passed.

## Candidate suites

- Python: 223 passed, 1 skipped in 299.13 seconds.
- Skip: portable FFmpeg candidate runtime is not provisioned inside the isolated application candidate. Its unchanged integration tests passed and the separately governed runtime is not in deployment scope.
- JavaScript/UI: 82 passed, 0 failed.
- JavaScript syntax checks: all declared application and service-worker scripts passed.
- Targeted capability tests: 34 passed.

## Real browser lifecycle

An isolated copy of the live data was used at `127.0.0.1:8897`; the live Workshop and live database were not used by the test.

Build lifecycle:

`Sanctuary → Crossroads → Build → free-first recommendation → plan → plan approval → deterministic work order → result approval → inactive save → TXT/MD/JSON export → My Work reopen → rollback`

- Job: `9f979930-bddc-42ee-9db4-cbdc7df5c137` (disposable verification copy only).
- Request: remove an image background without a paid service.
- Truthful decision: no verified free fit; inspect the discovered rembg CPU candidate or create a governed proposal.
- Registry/hardware/context hashes were visible and bound to the plan.

Modules lifecycle:

`Crossroads → Modules → Capability Bay → Free + Local filters → truth card → Agent Skill proposal → plan → plan approval → deterministic scaffold proposal → result approval → inactive save → TXT/MD/JSON export → My Work reopen → rollback`

- Job: `cdf4135e-af13-495d-9091-dd699418a8dd` (disposable verification copy only).
- Result contained a proposed `SKILL.md` package and explicitly stated that it did not create, install, activate, or execute the package.

Browser results:

- Desktop: pass.
- 390 × 844: pass.
- Horizontal overflow: 0.
- Keyboard focus: pass.
- Reduced motion: pass.
- Console errors/warnings/page errors: 0/0/0.
- External requests: 0.

## Security and authority

- Malformed and unknown capability fields rejected.
- Duplicate IDs rejected.
- Lifecycle transitions constrained.
- Unknown/discovered capability authority cannot self-elevate.
- Disabled execution remains the default for MCP, Agent Skills, A2A, WASI, Comfy, cloud, and candidate tools.
- Permission manifests are fixed and runtime undeclared authority fails closed.
- No POST, install, execution, provider fallback, public bind, arbitrary URL, or shell surface was added to Capability Bay.
- Build source, registry, and hardware hashes are stale-checked before result approval.

## Database and protected state

No migration is included. The candidate contains no live SQLite database, owner project data, model/runtime binary, export, cache, bytecode, or browser profile. Final predeployment comparison and rollback simulation are recorded outside the application candidate.

