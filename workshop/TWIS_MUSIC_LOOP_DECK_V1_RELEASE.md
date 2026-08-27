# TWIS Music Loop Deck V1

Music Loop Deck V1 is a bounded successor to the existing native Web Audio Music Studio. It keeps the Groove Bench, synth, sequencer, arrangements, governed AI proposal workflow, project save/version/rollback, and WAV rendering intact.

## Owner capability

- Import up to four owner-supplied mono or stereo 16-bit PCM WAV loops into governed project storage.
- Retain an inactive `music-loop` artifact, exact SHA-256, BPM, bar count, duration, and musical-grid validation for every imported loop.
- Launch and stop loops immediately, on the next beat, or on the next bar.
- Mix each channel with real gain, stereo pan, mute, solo, low-pass filtering, and echo.
- Capture launch, stop, level, pan, mute, solo, filter, and echo actions against transport beat positions.
- Save, reopen, version, and roll back a Music Studio project with loop references and captured actions.
- Render a real stereo PCM WAV containing the Groove Bench arrangement and loaded loops.

## Authority and limits

Imported WAV files remain inactive local project artifacts. Loading, duplicating, or clearing a channel does not delete or mutate its registered source. Retrieval verifies the registered hash and fails closed on stale bytes. No provider, model, network music engine, native package, PATH change, or database migration is introduced.

This is not a full DAW. Tempo matching uses `AudioBufferSourceNode.playbackRate`, so pitch changes with tempo. Captured actions are preserved as performance evidence; the offline render uses the final saved loop mix rather than replaying mixer automation. Live speaker audition remains an owner acceptance check because browser automation verifies the real Web Audio graph and rendered waveform, not the physical speaker.

## Engine decision

Native Web Audio remains the engine. Tone.js was not added: the incumbent already provides the required scheduling, nodes, and offline rendering with lower dependency and cache cost on the audited AMD A4-6210 system.
