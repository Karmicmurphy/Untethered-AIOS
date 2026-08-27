# Twis Holo Workshop Release Audit

Audit date: 2026-06-18

## What was checked

- ZIP contents inspected.
- Runtime test data removed from release.
- Python companion syntax checked.
- Browser app JavaScript syntax checked.
- Cloudflare Worker JavaScript syntax checked.
- Smoke test executed.
- Local companion started on a test port.
- `/api/health` verified.
- Project creation verified.
- Artifact creation and retrieval verified.
- Session save verified.
- Project Capsule ZIP creation verified.
- Service worker registration added for HTTP/local companion mode.
- GitHub Actions smoke workflow included.

## Test results

```text
Python syntax: PASS
App JavaScript syntax: PASS
Cloudflare Worker syntax: PASS
Smoke test: PASS
API end-to-end test: PASS
```

## Clean-release corrections made

- Removed accidental runtime database from the repo ZIP.
- Removed accidental `runtime-test` project folder from the repo ZIP.
- Added `tests/e2e_api_test.py`.
- Added service worker registration in `app/assets/app.js`.
- Kept runtime data paths as `.gitkeep` placeholders only.

## Current honest status

### Working inside this package

- Local companion server.
- SQLite project/artifact/session/receipt/job schema.
- FTS5 artifact search table.
- Project creation and switching.
- Artifact save/search/delete API.
- Session save API.
- Project Capsule export API.
- Folder import and indexing API.
- Browser Workshop shell.
- Talk, Write, Music, Image, Video Storyboard, Explore, Build, Recover, My Work, Modules, Settings rooms.
- WAV export.
- PNG export.
- Coding bench file read/write through the local companion.
- Cloudflare Worker/Durable Object scaffold.
- GitHub Actions smoke workflow.

### Not bundled because it requires outside action or outside files

- Cloudflare account login/deployment.
- Liquid LFM model files/runtime.
- llama.cpp model server.
- MCP servers.
- AG-UI/A2UI/A2A external runtimes.
- The owner's old folders, repositories, conversations, images, audio, and video.
- Full DAW and nonlinear-video-editor engine integrations.

## Run

Double-click `start-workshop.bat`, then open:

```text
http://127.0.0.1:8787
```

## Current Pass Addendum — 2026-06-18

Additional release pass performed after checking current platform/protocol direction.

### Added

- `/api/capabilities` local companion endpoint.
- `/api/security-policy` local companion endpoint.
- Cloudflare `/capabilities` endpoint.
- Optional Cloudflare write-token support via `REMOTE_WRITE_TOKEN`.
- Optional Cloudflare origin restriction via `ALLOWED_ORIGIN`.
- `docs/PROTOCOL_SECURITY.md` with deny-by-default MCP/protocol policy.
- `CURRENT_UPGRADE_PASS_2026-06-18.md` upgrade report.
- Updated Cloudflare README and wrangler comments.
- Expanded smoke/API tests.

### Verified

- Python syntax: PASS.
- App JavaScript syntax: PASS.
- Cloudflare Worker syntax: PASS.
- Smoke test: PASS.
- API end-to-end test: PASS.

### Clean release check

Runtime SQLite and e2e test project data were removed after validation. The release contains only `.gitkeep` placeholders under `data/`.
