import os

from mov2mp4.config import load_settings


def test_batch_size_is_auto_clamped(monkeypatch):
    monkeypatch.setattr(os, "cpu_count", lambda: 8)
    monkeypatch.setenv("FFMPEG_THREADS", "2")
    monkeypatch.setenv("BATCH_SIZE", "99")

    settings = load_settings()

    assert settings.batch_size == 4


def test_invalid_preset_falls_back_to_medium(monkeypatch):
    monkeypatch.setenv("DEFAULT_PRESET", "invalid")

    settings = load_settings()

    assert settings.default_preset == "medium"


def test_crf_is_clamped(monkeypatch):
    monkeypatch.setenv("DEFAULT_CRF", "80")

    settings = load_settings()

    assert settings.default_crf == 51

