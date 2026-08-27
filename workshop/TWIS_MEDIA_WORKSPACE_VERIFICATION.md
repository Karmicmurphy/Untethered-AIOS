# TWIS Images V2 Owner-Usable Workstation Verification

## Candidate result

- Full Python suite: 206 passed.
- Full JavaScript/UI suite: 72 passed.
- Python compile-all: passed.
- JavaScript syntax checks: passed.
- Smoke test: passed.
- Isolated API E2E: passed.
- Worker Harness and Artifact Inspection E2E group: 3 passed.
- Focused media backend: 4 passed.
- Focused Images UI: 5 passed.

## Real browser lifecycle

The isolated candidate lifecycle exercised:

- PNG drag/drop;
- JPEG and WebP selection;
- invalid-signature and over-12-MiB rejection;
- owner drawing, positioned text, grayscale, invert, undo, compare, and reset-capable UI;
- real PNG export (142,524 bytes in the final candidate run);
- one inactive governed image save;
- one provenance-linked inactive variation;
- byte verification that the parent source hash remained exact;
- scene creation;
- two storyboard frames, reorder, and removal of one frame without source deletion;
- Write to Images incoming context, including non-destructive dismissal from the current working view;
- Images to Music and Images to Video routes;
- storyboard frame to Video route;
- refresh recovery and project asset reopening.

Desktop 1440×1000: passed. Mobile 390×844: passed. Page horizontal overflow: 0/0. Minimum mobile primary-action height: 44 px. Reduced motion: honored. Console errors/warnings/page errors: 0/0/0. External requests: 0.

After cleanup the candidate retained 60 artifacts, zero image/scene/storyboard/route test artifacts, zero relationships, and 283 receipts (17 meaningful lifecycle receipts above the 266 baseline). SQLite integrity was `ok`, foreign-key violations were 0, and `user_version` remained 13.

## Truth boundary

ComfyUI remains NOT_INSTALLED. No compatible image worker, diffusion model, custom node, workflow runtime, provider, AI image generation, inpainting, AI upscaling, animation, or image-to-video generation was installed or claimed.

## Deployed result

- Exact application scope: 23 replacements, 0 additions, 0 removals.
- Predeployment hash gate: 23/23 passed.
- Candidate-to-live byte equality: 23/23 passed.
- Deployed Python suite: 206 passed.
- Deployed JavaScript/UI suite: 72 passed.
- Deployed compile, syntax, and smoke checks: passed.
- Deployed isolated API E2E: passed; Worker Harness and Artifact Inspection E2E group: 3 passed.
- Deployed browser lifecycle: passed with the same PNG/JPEG/WebP, editing, export, provenance, scene, storyboard, cross-room, refresh, desktop, and mobile checks as the candidate.
- Deployed browser console errors/warnings/page errors: 0/0/0; external requests: 0.
- Final SQLite integrity: `ok`; foreign-key violations: 0; `user_version`: 13.
- Final database SHA-256 after preserved lifecycle receipts: `B89C103AB50D1DA61D03168DE2E375D05B9B0B3DAAA81D043C24DBF3C1EA6420`.
- Final state: 3 projects, 60 artifacts, 287 receipts, 0 artifact relationships, 0 active jobs, 0 image/scene/storyboard/route test artifacts, and 0 disposable media files. The four receipts after the main lifecycle record two bounded create/delete route checks used to verify non-destructive Write-context dismissal.
- Protected non-scope files: 218/218 exact. Launcher/start script remained unchanged; `START_TWIS.bat` SHA-256 is `12AF861C9E3EF2A10EB05CF03C0B71738187DA935D704AF3EB3D6925BF0D437B`.
- Service port 8787 was closed after bounded verification.
- Rollback package: 23/23 originals verified; copied-environment rollback simulations passed before deployment and again against the final deployed scope.
