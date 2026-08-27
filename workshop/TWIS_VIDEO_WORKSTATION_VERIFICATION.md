PASS — Video V2 deployed and fully verified

# TWIS Video V2 Deployed Verification

Verified on 2026-08-23 America/Chicago against the authoritative Workshop at `C:\TWIS_FLASHRIVER_REVIEW_READY\TWIS`.

## Deployment

- Approved candidate manifest SHA-256: `E38DE27CEE50FD8338065B277DC0BED1F4719CA25BD15F2BFB3FB1E969819152`.
- Scope: exactly 26 application paths (15 replacements, 11 additions, 0 removals) plus exactly 3 adjacent portable-runtime additions.
- Immediate post-copy candidate-to-live equality: 29/29.
- Unexpected application differences: 0.
- Unexpected runtime additions: 0.
- The SQLite database, owner projects, imported sources, reviews, launcher, PATH, and system installation state were excluded from the copy transaction.
- This document is the required post-deployment evidence written to the already-approved verification-report path after the 29/29 equality gate; it is not implementation drift.

## Video capability

Video is now a real local production workstation. It can reference governed Images V2 assets and storyboard frames, Music Studio PCM WAV renders, eligible Write text, and a Scene; arrange one to 24 still-image clips; set durations and order; use cut/crossfade, still/zoom/directional-pan presets, one music track with start/volume/mute/fades, and up to eight title overlays; provide an approximate browser preview; save an inactive `video-composition`; render a real local MP4 through the fixed FFmpeg runtime; save the inactive `video-render`; reopen both kinds through Video and My Work; and roll back only the derived artifacts.

All source media remains referenced rather than overwritten. Image, audio, and writing-reference hashes are revalidated before save/render. Stale, missing, unregistered, mismatched, or unsupported inputs fail closed.

## Real deployed render

The deployed owner workflow rendered a disposable three-image composition with different durations, a Write-sourced title, a real Music WAV, a crossfade, zoom motion, and audio fades.

- Container: MP4
- Video codec: H.264 / AVC (`libx264`), High profile
- Audio codec: AAC LC, stereo, 44.1 kHz
- Resolution: 854 x 480
- Frame rate: 30 fps
- Frames: 120
- Duration: 4.000 seconds
- File size: 108,601 bytes
- Output SHA-256: `616C99603663C95F869A61B8A7BFDDF87511746FAB37E3FCEBBD65E8EB375AAB`
- Governed render time: 2.388 seconds
- Runtime: `ffmpeg version 9.0.1-essentials_build-www.gyan.dev`
- Automatic frame analysis: red -> mixed red/blue crossfade -> blue -> gold; title interval present; changing subject box proves zoom motion.
- Automatic audio analysis: start -47.0 dB, middle -30.2 dB, end -53.0 dB; fade-in and fade-out both verified.
- A separate deployed 480p observation completed in 2.262 renderer seconds; observed FFmpeg peak working set was 114.98 MiB and observed FFmpeg CPU time was 4.375 seconds. Harness wall time was 11.231 seconds.
- Source image hashes and Music WAV hash remained exact.

The live `video-render` and `video-composition` records and MP4 were then rolled back. The external verification contact sheet and operational evidence remain under `C:\TWIS_FLASHRIVER_REVIEW_READY\video-v2-workstation-work\evidence`.

## Cross-room verification

- Write -> Video: a governed `document` was selected as editable title text; its artifact ID and exact hash were retained, and the Write source was unchanged.
- Images -> Video: three governed Images V2 assets were selected by artifact ID and exact SHA-256 without copying or modifying them.
- Storyboard -> Video: three ordered `storyboard-item` records initialized the visual timeline with distinct durations; the storyboard remained unchanged.
- Music -> Video: a governed Music Studio WAV was selected by reference and rendered as AAC; its source hash remained exact.
- Scene -> Video: `live-video-scene` was retained in composition metadata.
- Video -> My Work: `video-composition` and `video-render` each reopened independently; both remained DRAFT/inactive.

## Limits

This release does not provide text-to-video AI, image-to-video AI, diffusion animation, ComfyUI execution, imported video trimming, narration generation, a subtitle editor, exact browser-preview/render parity, mid-render cancellation, or a 1080p preset on this hardware. It installs no model, provider, cloud renderer, global FFmpeg package, unrestricted shell, or arbitrary command surface.

## Tests

- Complete deployed Python suite: 210 passed in 184.40 seconds.
- Deployed Video backend/render tests: 4 passed in 14.74 seconds.
- Complete deployed JavaScript/UI/syntax suite: 77 passed.
- Python compile-all: passed with cache output redirected outside the Workshop and removed afterward.
- Desktop + 390 x 844 deployed Playwright lifecycle: 2 passed in 1.3 minutes.
- Additional desktop evidence-capture rerun: 1 passed in 1.2 minutes.
- Browser console errors / warnings / page errors: 0 / 0 / 0.
- Unexpected browser requests: 0.
- Provider/cloud calls: 0.
- 390 px horizontal overflow: 0.
- Touch target, visible focus, reduced-motion, refresh/reopen, and service-worker registration checks: passed.
- The first live evidence run reached a successful MP4 but its test harness expected camel-case `authorityState` instead of the established `authority_state` and assumed one saved composition although Render intentionally saves a fresh governed composition. Only the external evidence assertions were corrected; no product file was patched. The corrected lifecycle passed twice.

## Database and protected state

- Database migration: none.
- SQLite `user_version`: 13.
- Integrity: `ok`.
- Foreign-key violations: 0.
- Final projects / artifacts / receipts: 3 / 60 / 305.
- Final jobs / worker evidence / artifact relationships / reviews: 1 / 2 / 0 / 2.
- Preserved deployed-lifecycle receipts: 18.
- Remaining disposable project records / disposable artifacts / Video test artifacts: 0 / 0 / 0.
- Protected source rows exact: 59/59.
- Reviews exact: 2/2.
- Owner project-file differences: 0.
- Pre-existing governed job and worker evidence: exact and unchanged.
- No source, owner media, active artifact, approval state, or review was overwritten or automatically activated.

## Runtime

- `runtime/ffmpeg/9.0.1/bin/ffmpeg.exe`: SHA-256 `72A489ECCD008C2EC2C0A5856C5C75BC3D8BBFA90166C4566865C246445E6AA3`.
- `runtime/ffmpeg/9.0.1/bin/ffprobe.exe`: SHA-256 `19202B23C0043F15AD1B7BCE2344F406FD52BD6EFD8F995CE02E7392A1CEC52F`.
- `runtime/ffmpeg/9.0.1/licenses/LICENSE`: SHA-256 `8CEB4B9EE5ADEDDE47B31E975C1D90C73AD27B6B165A1DCD80C7C545EB65B903`.
- Required libx264, AAC, xfade, zoompan, drawtext, and afade capabilities: verified.
- Runtime binding: adjacent fixed local files only; no system PATH, user PATH, or machine PATH modification and no global installation.
- Owner UI exposes no arbitrary executable, command, argument, or shell input.

## Recovery

Rollback package: `C:\TWIS_FLASHRIVER_REVIEW_READY\video-v2-workstation-work\rollback`.

The external rollback simulation restored 15/15 original application files, removed 11/11 application additions, removed 3/3 runtime additions, left owner projects untouched, and preserved the additive live database. The emergency SQLite copy remains disaster-recovery-only and was not used.

## Files changed by deployment

Replaced (15):

- `app/assets/app.js`
- `app/index.html`
- `app/modules/modules.json`
- `app/service-worker.js`
- `companion/server.py`
- `config/media-capabilities.json`
- `docs/TWIS_MEDIA_WORKSPACE_CONTRACT_V1.md`
- `package.json`
- `tests/local-worker-kit-ui.test.js`
- `tests/music-studio-ui.test.js`
- `tests/room-system-ui.test.js`
- `tests/shell-ui.test.js`
- `tests/talk-room-ui.test.js`
- `tests/test_worker_harness_ui.py`
- `tests/write-room-ui.test.js`

Added to the Workshop (11):

- `TWIS_VIDEO_WORKSTATION_CANDIDATE_MANIFEST.txt`
- `TWIS_VIDEO_WORKSTATION_CHANGED_FILES.txt`
- `TWIS_VIDEO_WORKSTATION_RELEASE.md`
- `TWIS_VIDEO_WORKSTATION_ROLLBACK.md`
- `TWIS_VIDEO_WORKSTATION_VERIFICATION.md`
- `app/assets/video-workstation.css`
- `app/assets/video-workstation.js`
- `companion/video_workstation.py`
- `config/ffmpeg-runtime.json`
- `tests/test_video_workstation.py`
- `tests/video-workstation-ui.test.js`

Added adjacent runtime files (3):

- `runtime/ffmpeg/9.0.1/bin/ffmpeg.exe`
- `runtime/ffmpeg/9.0.1/bin/ffprobe.exe`
- `runtime/ffmpeg/9.0.1/licenses/LICENSE`

Removed by deployment: none.

## Final state

- Temporary Workshop, browser, render, and FFmpeg processes: stopped.
- Temporary ports 8787 and 8895: closed.
- Temporary bytecode, pytest, Playwright, render-workspace, disposable project, and generated MP4 residue: removed.
- Active test attachments: 0.
- Owner projects and sources: protected and exact.
- Launcher SHA-256: `12AF861C9E3EF2A10EB05CF03C0B71738187DA935D704AF3EB3D6925BF0D437B` (unchanged).
- Unexpected external requests / provider calls / network workers: 0 / 0 / 0.
- No ComfyUI runtime, AI video engine, model, provider, or fake generation state was added.
