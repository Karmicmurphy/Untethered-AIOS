# TWIS Background Removal Runtime — Verification

## Candidate result

`PASS — VERIFIED CANDIDATE, LIVE WORKSHOP UNCHANGED`

## Automated evidence

- Full Python suite: 242 passed, 1 skipped.
- Focused runtime/API/remote-authorization suite after the final request-boundary hardening: 10 passed.
- Full JavaScript/UI suite: 84 passed.
- Runtime import health: OpenCV 4.14.0 and NumPy 2.5.2 loaded from the adjacent pinned runtime.
- Full runtime manifest verification: 1,033/1,033 files; tree SHA-256 exact.
- Candidate SQLite: integrity `ok`; foreign-key violations `0`; `user_version=13`.

## Real browser lifecycle

The isolated candidate completed:

Sanctuary → Crossroads → Images → registered source → foreground rectangle → Keep correction → proposed cutout → compare → refresh recovery → explicit approval → inactive derived image → My Work reopen.

Evidence:

- proposal visible: pass
- comparison visible: pass
- source identity/hash shown: pass
- correction stroke recorded: 1
- refresh proposal recovery: pass
- approved output remained `DRAFT` / inactive: pass
- My Work reopening: pass
- desktop horizontal overflow: 0
- 390×844 horizontal overflow: 0
- primary mobile touch control height: 79 px
- keyboard focus: visible
- reduced motion: honored
- console errors/warnings/page errors: 0/0/0
- unexpected external requests: 0

## Integrity and governance

- Registered source SHA-256 before/after: `ba7dcf3af13847d9ca40b3338407bae776750e583e21de85b99e3cad4eb3c2b9` / exact.
- Proposed output SHA-256: `7A38D47CDC5B45F4726CC0B943C5EF3C39D32A94191F4E58F7145E0E9EE9AB8F`.
- Result saved only after a separate explicit decision.
- Saved result state: inactive `DRAFT` image with parent relationship and full runtime/source provenance.
- Reject path: proposal removed, no artifact saved, source preserved.
- Stale-source path: approval blocked.
- Non-owner remote APIs: fail closed through existing backend authorization.
- Cross-site or non-JSON mutation requests: rejected.
- Arbitrary shell input: no accepted field or endpoint exists.
- Provider/model/network calls after provisioning: 0.

All browser data and rendered images used for verification were synthetic and isolated from the live Workshop. Disposable candidate project data is removed before candidate sealing; screenshots, reports, manifests, and audit evidence remain outside the deployment scope.
