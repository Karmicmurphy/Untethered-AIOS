# TWIS Background Composition — Candidate Verification

Status: PASS — ISOLATED CANDIDATE — NOT DEPLOYED

## Automated evidence

- Python: 246 passed.
- JavaScript/UI: 85 passed; all declared JavaScript syntax checks passed.
- Targeted media/API gate: 13 passed after linking the isolated candidate read-only to the already verified adjacent OpenCV runtime.
- Candidate browser lifecycle: passed.
- Desktop 1440×900: zero horizontal overflow.
- Mobile 390×844: zero horizontal overflow; 42 px primary control; reduced-motion true.
- Browser console errors/warnings/page errors: 0/0/0.
- Browser external requests: 0.

## Real lifecycle

A synthetic transparent registered foreground and a separate registered backdrop were used.

- Gradient preview created no artifact.
- Reject created no artifact.
- Registered-image preview created no artifact.
- Refresh did not auto-resume or save the proposal.
- Explicit approval created exactly one `inactive-draft` image.
- My Work displayed the saved composite.
- Saved output SHA-256: `6936afba99fd47a9d7fb190a59c1a427e121377912b0c9d8209a2bc864bed05f`.
- Foreground SHA-256: `6c50cbdf6457066abb0ba916ed8408515ea4c2e365c3edb27f2cbbed7d130fe9`.
- Backdrop SHA-256: `9c529811083fa2435dba00533e7f4a6373db789c7b4837b3ace577501874a8a5`.
- Both source identities and hashes were retained in provenance.

The exact candidate manifest, rollback package, protected-state verification, and rollback simulation are external evidence under `C:\TWIS_FLASHRIVER_REVIEW_READY\background-composition-images-v2-work`.

