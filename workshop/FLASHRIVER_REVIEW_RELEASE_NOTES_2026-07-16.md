# FlashRiver Review View Release

This build adds a dedicated local FlashRiver Review View.

## Included

- Dedicated FlashRiver Review screen opened by **Review in My Work**.
- Intake summary with package hash, ZIP result, counts, and source boundary data.
- Deterministic artifact grouping.
- Full records for documents, private source archives, visuals, and manifest.
- Text preview for imported safe documents.
- Source/provenance inspection.
- Review states: unreviewed, reviewed, current candidate, superseded, conflicted, private source, and do not use.
- Local review notes and append-only receipt entries for review actions.
- Two-artifact comparison using imported previews.
- No Promote to Module action. Imported instruction files remain inert source content.

## Verification

- 12 automated tests passed.
- Python compilation passed.
- JavaScript syntax checks passed.
- Smoke test passed.
- API E2E test passed.
- Real FlashRiver package imported with 59 records.
- Review endpoint returned all 59 records.
- Review status persistence endpoint passed.
