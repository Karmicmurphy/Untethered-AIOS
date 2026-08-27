# Background Removal Functional Inspection Report

Status: exact evidence accepted by the owner; live runtime remains `NOT-INSTALLED`.

- Inspection ID: `c3c72fce-1442-44f5-bf13-e51945cdc2d2`
- Evidence SHA-256: `34C09EEFA97856ED4BC9CDF91EC76F4AFE0E4910006185C5348878AE685FACD0`
- Engine: OpenCV 4.14.0 GrabCut
- Inspected package version: `4.14.0.94`
- Inspected registry SHA-256: `6A776E2E954DA6A7B5AB3F5CE0167178F55EBBC85A8E1354E12503C5AC8648DE`
- Hardware profile SHA-256: `FD44C4D042A6DF0E9FDFB9B96731A2C0DDDFA52E967C9EB947BCFDA1A3CC8B4A`
- Owner verification receipt: `73da128c-83c8-4967-9ec9-f1a4b2ed5027`
- Environment creation: 229.244735 seconds
- Fixed adapter elapsed: 15.737587 seconds
- Engine wall time: 4.763240 seconds
- Engine CPU time: 3.031250 seconds
- Downloaded bytes: 53,492,704
- Disposable footprint: 235,504,853 bytes
- Peak working set: NOT MEASURED; the Windows query returned no value
- Retained wheel/venv files: none
- Live installation or Images integration: none

## Synthetic sanity cases

| Case | Seconds | IoU | False foreground | False background | Edge error |
|---|---:|---:|---:|---:|---:|
| A_high_contrast | 0.911139 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| B_irregular_edge | 0.718563 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| C_fur_like_edge | 0.823107 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |
| D_similar_tones | 1.133568 | 1.000000 | 0.000000 | 0.000000 | 0.000000 |

These are deliberately simple deterministic synthetic checks. They are not a professional vision benchmark and do not prove performance on photography, hair, clutter, owner images, or production workloads.

## Governance result

The owner accepted the exact evidence object. This establishes a verified capability-evidence record only. OpenCV remains absent from the live Workshop, the registered health state remains `NOT-INSTALLED`, Build cannot recommend it as ready, and Images has no background-removal control or execution path in this release.
