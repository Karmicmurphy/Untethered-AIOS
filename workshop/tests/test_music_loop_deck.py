from __future__ import annotations

import math
import struct
from pathlib import Path

import pytest

from companion import server


def pcm_loop(*, bpm: int = 120, bars: int = 1, sample_rate: int = 8000) -> bytes:
    frames = int(bars * 4 * 60 / bpm * sample_rate)
    samples = [int(math.sin(index * 2 * math.pi * 110 / sample_rate) * 8000) for index in range(frames)]
    audio = b"".join(struct.pack("<h", sample) for sample in samples)
    fmt = struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate * 2, 2, 16)
    chunks = b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(audio)) + audio
    return b"RIFF" + struct.pack("<I", len(chunks) + 4) + b"WAVE" + chunks


def test_loop_wav_duration_proves_one_bar_grid():
    evidence = server._validate_music_wav(pcm_loop())
    assert evidence["durationSeconds"] == 2.0
    assert evidence["frames"] == 16000
    assert evidence["audioBytes"] == 32000


def test_loop_path_is_bounded_to_project_media(monkeypatch, tmp_path: Path):
    projects = tmp_path / "projects"
    projects.mkdir()
    monkeypatch.setattr(server, "PROJECTS", projects)
    path = server._music_loop_path("test-project", "media/audio/loops/kick.wav")
    assert path == (projects / "test-project" / "media" / "audio" / "loops" / "kick.wav").resolve()
    with pytest.raises(ValueError, match="governed loop directory"):
        server._music_loop_path("test-project", "exports/music/not-a-loop.wav")


def test_loop_path_rejects_non_wav(monkeypatch, tmp_path: Path):
    projects = tmp_path / "projects"
    projects.mkdir()
    monkeypatch.setattr(server, "PROJECTS", projects)
    with pytest.raises(ValueError, match="governed loop directory"):
        server._music_loop_path("test-project", "media/audio/loops/loop.mp3")
