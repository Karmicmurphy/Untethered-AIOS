# Music Loop Deck V1 verification

Candidate root: `C:\TWIS_FLASHRIVER_REVIEW_READY\music-successor-program-work\candidate\TWIS`

Live root remained unchanged during candidate construction and verification.

## Automated suites

- Python: **248 passed, 1 skipped** in 312.35 seconds.
- JavaScript/UI: **86 passed, 0 failed**; all declared JavaScript syntax checks passed.
- Music-targeted Python: **7 passed**.
- Candidate browser lifecycle: **PASS** in real headless Microsoft Edge at 1440×900 and 390×844.

## Real browser and audio evidence

- Four different PCM WAV inputs imported and downloaded back byte-exact with matching SHA-256 values.
- Four loop buffers played concurrently.
- Next-bar launch scheduled at beat 4; next-beat launch scheduled at beat 5.
- Gain 0.41, pan -0.72, filter 3200 Hz, echo 0.24, mute, and solo changes reached real engine state.
- Ten transport-positioned performance actions were captured.
- Save, second version, exact bounded rollback into version 3, My Work reopen, and four-loop restoration passed.
- Offline stereo WAV: RIFF, 44.1 kHz, 5.23 seconds, 922,620 bytes, peak 1.077551, RMS 0.080419, non-silent; render completed in 814.54 ms.
- Desktop and mobile horizontal overflow: 0. Mobile loop channel width: 342.40625 px. Launch control height: 44 px.
- Browser console errors/warnings/page errors: 0/0/0. Unexpected external requests: 0.
- Used JavaScript heap during the final desktop lifecycle: 11,102,721 bytes.
- All six lifecycle artifacts were deleted after verification; a separately discovered interrupted-run render was also removed.

Evidence files are retained outside the deployment scope under `music-successor-program-work\evidence`.

## Failure and integrity evidence

- Malformed WAV import returned 400.
- Tampering with an isolated registered loop caused retrieval to fail closed with 409.
- Restoring the exact bytes restored access and the exact SHA-256.
- The disposable stale-source artifact was deleted with status 200.
- Candidate SQLite: integrity `ok`, no foreign-key violations, `user_version=13`, and 60 baseline artifacts after WAL checkpoint/cleanup.
- Live SQLite: integrity `ok`, no foreign-key violations, `user_version=13`, with accepted counts unchanged: 60 artifacts, 60 search rows, 331 receipts, 1 job, 2 worker-evidence rows, 0 relationships.
- Live application files: 291/291 exact to the frozen baseline. Protected non-database data files: 122/122 exact.

## Honest inherited checks

The existing Groove Bench contributed Pattern A to the real loop-inclusive render and remains covered by the full Music/UI suites. The separate governed Music AI plan/result/apply path remains covered by the full Python and JavaScript regression suites; this release did not invoke, replace, or require a model.
