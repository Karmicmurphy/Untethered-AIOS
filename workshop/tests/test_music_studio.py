from __future__ import annotations

import math
import struct

import pytest

from companion.server import _validate_music_wav


def pcm_wav(*, silent: bool = False, sample_rate: int = 8000, frames: int = 800) -> bytes:
    samples = [0 if silent else int(math.sin(index * 2 * math.pi * 220 / sample_rate) * 12000) for index in range(frames)]
    audio = b"".join(struct.pack("<h", sample) for sample in samples)
    fmt = struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate * 2, 2, 16)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(audio)) + audio
    return b"RIFF" + struct.pack("<I", len(chunks) + 4) + b"WAVE" + chunks


def test_non_silent_pcm_wav_is_measured_from_real_bytes():
    raw = pcm_wav()
    evidence = _validate_music_wav(raw)
    assert evidence == {
        "channels": 1,
        "sampleRate": 8000,
        "bitsPerSample": 16,
        "audioBytes": 1600,
        "frames": 800,
        "durationSeconds": 0.1,
    }


@pytest.mark.parametrize("raw, message", [
    (pcm_wav(silent=True), "no audible waveform"),
    (b"not a wav", "RIFF/WAVE"),
    (pcm_wav()[:-3], "RIFF size"),
])
def test_invalid_or_silent_render_is_rejected(raw, message):
    with pytest.raises(ValueError, match=message):
        _validate_music_wav(raw)
