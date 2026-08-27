# FlashRiver UI Release Notes — 2026-07-16

This package includes the local FlashRiver source archive intake engine and the Recover-room UI button.

## Added

- `companion/flashriver_intake.py`
- `POST /api/import-flashriver` in `companion/server.py`
- Recover-room controls in `app/index.html`
- `app/assets/flashriver-import-ui.js`
- FlashRiver My Work filters
- `tests/test_flashriver_intake.py`
- `tests/test_flashriver_recover_ui.py`
- `docs/FLASHRIVER_INTAKE_API.md`
- `docs/FLASHRIVER_SOURCE_ARCHIVE_INTAKE.md`
- `docs/CODEX_FLASHRIVER_NEXT_PROMPT.md`
- `docs/TWIS_TALKBOX_MODULE_SPEC.md`

## Verified locally in this package

- Python syntax compile: PASS
- Existing smoke test: PASS
- Existing API e2e test: PASS
- FlashRiver intake tests: PASS
- FlashRiver Recover UI tests: PASS
- JavaScript syntax checks for `app.js` and `flashriver-import-ui.js`: PASS
- Real import endpoint test against uploaded FlashRiver ZIP: PASS

## Boundary

Raw FlashRiver package and nested source ZIPs remain local/private. GitHub and Cloudflare are not private source authority.
