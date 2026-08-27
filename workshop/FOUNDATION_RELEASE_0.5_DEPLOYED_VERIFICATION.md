# Foundation Release 0.5 - Deployed Verification

Date: 2026-07-23  
Active target: `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`  
Authoritative evidence root: `C:\Users\Olli_Twis\Documents\Codex\2026-07-21\files-mentioned-by-the-user-twis\outputs`  
Final decision: **PASS — deployed, fully verified, and lifecycle rolled back safely**

## Executive result

Foundation Release 0.5 was deployed from the authenticated candidate after all
16 predeployment conditions were rechecked. The deployment replaced exactly 13
approved files and added exactly three approved files. No other file was copied.

Post-deployment verification proves:

- active Release 0.5 files match the authenticated candidate: **16/16**
- Python suite: **120 passed**
- JavaScript suite: **14 passed**
- JavaScript syntax: **6/6 passed**
- Python compile-all: **34/34 passed**
- smoke and isolated API E2E: **passed**
- Worker Harness and Artifact Inspection API E2E: **3 passed**
- focused Release 0.5 UI/security/API regression set: **34 passed**
- disposable browser lifecycle: **passed through rollback**
- live governed lifecycle on the required artifact: **passed through rollback**
- final active attachment count: **0**
- Workshop SQLite integrity: **ok**
- all 51 public source artifacts: **byte-identical**
- protected hashes, reviews, launcher, permissions, and startup behavior:
  **unchanged**
- ports 8787 and 8875 after shutdown: **closed**

## 1. Evidence authentication and predeployment gate

| Evidence | SHA-256 | Result |
|---|---|---|
| `FOUNDATION_RELEASE_0.5.md` | `A79D65EACC8DBEA318FD0AB55349F16280DDEC9325BE942DF942CF926AF2C4E5` | exact |
| `FOUNDATION_RELEASE_0.5_CANDIDATE_MANIFEST.txt` | `37B50E5BEBD612654D5853D63675B41F94E3B0EB9F8ABC22E9BA376E16470810` | exact |
| `foundation-0.5-rollback\ROLLBACK_MANIFEST.json` | `FAD6A12140794D44884D86D723CA0FE33D975060263D5F6BEF5B1C3D8832334B` | exact |
| frozen baseline evidence | `0AFF17EFC084C34ED1A57DE50EA1CBBA58368779821C0F5B83FD0171765F6209` | exact |

Before copying, all 13 replacement paths matched their manifest
predeployment hashes and all three addition paths were absent. Candidate files
matched the manifest at 16/16. The manifest contained no `data`, cache,
temporary, SQLite, or bytecode path.

The launcher was not in deployment scope and remained:

`start-workshop.bat`  
SHA-256 `E50EDFA8B151EFBBEFF401DD771E22C82C4885FD314D4239AD452DA5A42CC1C1`

## 2. Exact deployment

| Action | Relative path | Release 0.5 SHA-256 | Live result |
|---|---|---|---|
| replace | `app\assets\style.css` | `359220CA4D8F05DF44C4231007F9F108BE00EFD32630C06440F9363BBECAEF7B` | exact |
| replace | `app\assets\worker-harness.js` | `41353F4A0DA6A263C0CF3E44F6F0EDEF2F351A97ACC86D36DB0507A1E06A5F2E` | exact |
| add | `app\assets\worker-harness-view.js` | `DFE14637291404D9413BCAFB6648F1FDA79CFD1F87CF06C135EFC2DAD565533B` | exact |
| replace | `app\index.html` | `CE60BD12CFC6DC37CF5DAEE2BC3CF3942F82212540B555333B71144A6FD1CD74` | exact |
| replace | `app\service-worker.js` | `619BB8E56D4CA163B8C5042DF25362C2EC400CC5F819F2BC8286DB0884AD7635` | exact |
| replace | `companion\foundation\worker_harness.py` | `7BE4A6921F1BD430E81D4B1D0266B374040A51E98EB955DF7864ACE420F98A04` | exact |
| replace | `companion\server.py` | `F4F4779B916B03172F051040447A932EAE5E722760A5A467B0E0D6AD8390F9F8` | exact |
| add | `FOUNDATION_RELEASE_0.5.md` | `A79D65EACC8DBEA318FD0AB55349F16280DDEC9325BE942DF942CF926AF2C4E5` | exact |
| replace | `package.json` | `3D803B909F436CB06409B8FC6503FA933788F1573F58744DBC0B1811E1C66875` | exact |
| replace | `tests\e2e_api_test.py` | `2C2191DFB4A190BADFBC32B54281D0B92B60FD028B212492C42A0AFAD05E5156` | exact |
| replace | `tests\test_artifact_inspection_api_e2e.py` | `7437C978C67A8B4DA8E8E9BE1E2D6D3BE12B557706F40FF8B2A025A55D26133D` | exact |
| replace | `tests\test_worker_harness.py` | `A244096D9BA0BD30D7307454E9D3E3B09FBE6AA898ED61DFF990368501317F9D` | exact |
| replace | `tests\test_worker_harness_api_e2e.py` | `8C212338244585D87A00F261710C4C0F15EF758C7153A3F41DAC2669C075903C` | exact |
| replace | `tests\test_worker_harness_security.py` | `C05AD72F35CE11B95DF3D6C71C95F292EDD04B8FA0A90A29AE1E7162B22AC20E` | exact |
| replace | `tests\test_worker_harness_ui.py` | `DCDC115CDF0A72E3F9E5DC2CB245267627F1FE559F3CA5BE752A706EF61C114E` | exact |
| add | `tests\worker-harness-view.test.js` | `892A9FFDE83F63DC1F1527CC2B302A682FFC6CEA9AE01447EC203E0967CDDCCC` | exact |

Deployment totals: **13 replacements, 3 additions, 16/16
candidate-to-live equality, zero unapproved deployment paths**.

## 3. Automated deployed verification

All mutable test state, browser profiles, browser caches, compile output, and
pytest temporary roots were outside the active TWIS folder.

| Check | Result |
|---|---|
| full Python suite | **120 passed in 195.82s** |
| full JavaScript suite | **14 passed in 2198.3532ms** |
| JavaScript syntax (`node --check`) | **6/6 passed** |
| Python compile-all on an external hash-exact source copy | **34/34 passed** |
| smoke test | `Twis Holo smoke test PASS` |
| isolated API E2E | `Twis Holo API E2E PASS (isolated temporary data)` |
| Worker Harness + Artifact Inspection API E2E | **3 passed in 29.38s** |
| focused Release 0.5 UI/security/harness/inspection set | **34 passed in 83.38s** |
| rollback package verification | **16/16 members, 13/13 originals, 3/3 removal paths** |

The JavaScript and focused Release 0.5 tests cover stale-plan rejection,
blank-note rejection, duplicate artifact distinction, HTML/imported-text
escaping, explicit approval, explicit attachment, rollback, navigation state,
and owner-truth UI behavior.

One initial full-suite attempt used a nested Windows pytest base directory that
the runtime could not create. It ended with 28 passes, three failures, and 89
errors, all sharing the same `PermissionError` on that temporary root. The
suite was rerun without code changes using the short external base
`C:\TWIS_FLASHRIVER_REVIEW_READY\pt05r`; that authoritative run passed all
120 tests. This was an environment-path failure, not a product failure.

Python imports during verification refreshed an existing
`worker_harness.cpython-312.pyc` cache entry. It was not deployed. After each
active run it was reconstructed from the authenticated Release 0.4 original
with the original source identity and restored to its exact pre-verification
hash:

`B917CA45D08F2F5B484C620BECCE24B5474828E349050BE7242CB205FC91F47D`

The final active-tree comparison therefore contains no cache or bytecode
change.

## 4. Disposable browser lifecycle

A fresh headless Chromium 151 browser profile and a disposable Workshop
runtime were kept outside the active TWIS folder. The browser verified:

- two eligible and one blocked fixture artifact with zero source mismatches;
- duplicate `AGENT.md` entries visibly distinguished by path and artifact ID;
- validated fixed Worker Card with denied network, shell, destructive, and
  automatic-activation capabilities;
- changed artifact selection made the plan stale and disabled execution;
- a fresh exact plan ran to `awaiting_approval`;
- blank approval returned
  `approval_note_required: an explicit approval note is required`;
- explicit approval succeeded and remained unattached;
- explicit attachment succeeded only after confirmation;
- explicit rollback restored
  `FDF9BF34124DC49F58362158DF9C6F1D22FF49AB3E7DCC3C8D4B24A09A1117A0`;
- source files remained at
  `B3573F32DDFB1B4B1009CFF1337E975142489D0E6D5F5A9B0472C2F7D7164A5A`;
- final fixture attachment count was zero;
- reload preserved `#modules`, the service worker controlled the page, and
  the only cache was `twis-holo-full-v5`;
- browser console: **0 errors, 0 warnings**.

Disposable final screenshot:

`C:\TWIS_FLASHRIVER_REVIEW_READY\pw05r\.playwright-cli\page-2026-07-24T03-50-30-248Z.png`  
SHA-256 `70E08CF1EBF1C653A1F299B0C3BF4FCD1444767DCBAE1D0B7707F26188E2068B`

## 5. Live governed lifecycle

The live fixed worker was exercised once for the required artifact:

| Binding | Verified value |
|---|---|
| artifact ID | `9217e4a7-7254-53a6-a75e-1d20e0754d86` |
| distinct path | `...\docs\AGENT.md` |
| source SHA-256 | `E4EFEDCAB226193F35EAE9E1CB6070102D7FD336B70A5C3205D33976D48BB38A` |
| worker | `artifact-compass-inspection-worker 0.4.0` |
| Worker Card SHA-256 | `89010C75E141A3A367B87EDF70E154E1374CAD02402EF414CB3940517277FBAA` |
| candidate ID | `36cba086363f44fd99aff8da424dfc30` |
| candidate SHA-256 | `1CCB8C32A09121F1D2201A4EBD38160AC5F193E7AB44BDBC27B4E731B6B77C0A` |
| execution-plan SHA-256 | `19D8049BE107899FEEBE5774C4E02BD1DF4A91B6652B9410B3E94B1890AC8E82` |
| transaction | `8dc0e9e2c0084f74bb43522362dc1481` |
| output SHA-256 | `85AF98D7082C75D96E1E122926F10B99F424105D9A54D8FAA02CE756A1A4E624` |
| approval note | `Release 0.5 automated deployed verification` |
| restored output SHA-256 | `99C77BA9BB05B55837758ABD3FC0E76C89E53618AA6C1E56D614F6946082B64D` |

Live acceptance results:

- eligibility: **50 eligible, 9 blocked, 0 source-hash mismatches**
- duplicate identity: both `docs\AGENT.md` and
  `docs\agent_files\AGENT.md` shown with their distinct IDs
- Worker Card: validated; network, shell, destructive actions, and automatic
  activation denied; approval required
- exact plan: current for the required root artifact
- stale gate: switching to the duplicate artifact cleared the plan, displayed
  `Artifact selection changed. Create a new exact plan.`, and disabled Run
- run: reached `awaiting approval`, test
  `artifact-inspection-output-v0.4: PASS; source unchanged`
- blank note: rejected with `approval_note_required`
- explicit approval: succeeded; state was `approved`, report not attached
- explicit attachment: succeeded only after confirmation; state was `active`
- rollback: succeeded only after confirmation; state was `rolled back`
- recovery: verified restored hash exactly matched expected restored hash
- final active attachment count: **0**

The UI continued to state and the on-disk comparisons confirmed that source
content was not modified, no permission was granted, review status was
unchanged, and nothing executes at startup.

After reload, navigation remained on `#modules`, the page was controlled by the
service worker, cache inventory was exactly `twis-holo-full-v5`, the rolled-back
candidate remained visible, and the console remained at **0 errors and 0
warnings**.

Live final screenshot:

`C:\TWIS_FLASHRIVER_REVIEW_READY\pw05live\.playwright-cli\page-2026-07-24T04-12-13-341Z.png`  
SHA-256 `20984BDA71408414F9B4A93F85A34278F90BB9DCCFBDA2E29C99F62945AB18FC`

## 6. Protected state and final safety comparison

The Workshop database was read in read-only immutable mode before deployment,
before the live lifecycle, and after shutdown.

| Check | Baseline | Final | Result |
|---|---:|---:|---|
| Workshop database SHA-256 | `8963DC86337E40606F493DD78792069113DF6B7B0B570CB64F8B247F173CCBC6` | same | exact |
| SQLite integrity | `ok` | `ok` | pass |
| projects | 2 | 2 | exact |
| artifacts | 59 | 59 | exact |
| artifact_search | 59 | 59 | exact |
| artifact_reviews | 2 | 2 | exact |
| receipts | 13 | 13 | exact |
| sessions | 0 | 0 | exact |
| modules | 0 | 0 | exact |
| jobs | 0 | 0 | exact |
| public source files | 51 | 51 | byte-identical |
| active attachments | 0 | 0 | exact |
| rolled-back attachments | 1 | 2 | expected lifecycle evidence |
| harness registry generation | 2 | 4 | expected attach + rollback |

All 11 protected-path hashes matched baseline, including the launcher,
FlashRiver packages and receipts, source archives, Workshop database, and
private archive packages. Artifact review rows were identical. All 51 public
source files matched both their recorded hashes and baseline bytes.

The live lifecycle added exactly 19 Worker Harness evidence files:

- one candidate, output, request, test result, approval decision, activation
  record, and rollback record;
- two exact plans;
- four transaction manifests and four receipts;
- two bounded transaction snapshots.

The only existing files changed by the lifecycle were the four expected
Worker Harness state/evidence stores:

- `data\worker_harness\activation-registry.json`
- `data\worker_harness\artifact-compass.sqlite3`
- `data\worker_harness\provenance-inventory.json`
- `data\worker_harness\workspace\state.json`

No lifecycle evidence file was removed. Outside those expected Worker Harness
evidence changes and this final report, the post-deployment tree remained
unchanged.

Final safety assertions:

- Workshop processes stopped
- port 8787 listeners: **0**
- port 8875 listeners: **0**
- active attachments: **0**
- import operations: **none**
- source or artifact deletion: **none**
- network worker: **none**
- AI model execution: **none**
- arbitrary worker execution: **none**
- unrestricted shell execution: **none**
- automatic activation: **none**
- launcher modification: **none**
- deployment of data, cache, temp, browser, test-output, or bytecode files:
  **none**

## 7. Rollback readiness

Final package verification was rerun after the live rollback:

- rollback manifest hash: exact
- manifest-listed rollback members: **16/16 exact**
- replacement originals: **13/13 exact against predeployment hashes**
- new-file removal scope: **3/3 exact**
- protected data included in rollback package: **false**

Release rollback therefore remains safely available without guessing or
touching protected data.

## Final release decision

**PASS — deployed, fully verified, and lifecycle rolled back safely**
