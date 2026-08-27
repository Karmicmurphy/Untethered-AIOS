# TWIS Music Studio — Bounded Release

## Outcome

This release keeps the existing Song Production Brief Builder and adds a separate, playable Groove Bench to the Music Room. The bench uses native browser Web Audio only: no Tone.js, cloud music engine, external DAW, plug-in host, MIDI service, or native audio runtime was added.

## Owner capability

- Play synthesized kick, snare, closed/open hats, percussion, and a simple pitched synth immediately from mouse, touch, or keyboard.
- Program 16-step patterns A–D, copy or clear patterns, adjust BPM during playback, pause/stop, loop, mix, mute, and solo tracks.
- Arrange up to eight pattern slots into a song-mode sequence.
- Save inactive, project-scoped Music Studio artifacts with exact versions; reopen them from My Work; restore an older version by creating a new recovery version.
- Render the current pattern or arrangement through `OfflineAudioContext` to a real stereo PCM WAV, preview/download it, and optionally save it as a bounded inactive `music-render` artifact.
- Ask the registered localhost model for one of ten fixed music-assist actions. The result is a hash-bound proposal: plan approval, result approval, and explicit application are separate actions.

## Safety boundaries

Original project sources are never modified. AI proposals cannot change music state before explicit result approval and explicit apply. Saved patterns, arrangements, and renders remain DRAFT/inactive. WAV files are validated as PCM RIFF/WAVE, non-silent, and bounded to 16 MiB before storage under the governed music export directory. No database migration is required; SQLite `user_version` remains 13.

## Engine decision

Tone.js was not added. Native Web Audio already supplies the required synthesis, low-overhead mixing, look-ahead scheduling, real analyser data, and offline rendering. Adding Tone.js would increase the cached application payload without materially improving this bounded workstation on the AMD A4-6210 target.

