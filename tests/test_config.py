import os
from pathlib import Path

from mov2mp4.config import load_settings


def test_batch_size_is_auto_clamped(monkeypatch, tmp_path):
    monkeypatch.setattr(os, "cpu_count", lambda: 8)
    monkeypatch.setenv("FFMPEG_THREADS", "2")
    monkeypatch.setenv("BATCH_SIZE", "99")

    settings = load_settings(tmp_path / ".env.missing")

    assert settings.batch_size == 4


def test_invalid_preset_falls_back_to_medium(monkeypatch, tmp_path):
    monkeypatch.setenv("DEFAULT_PRESET", "invalid")

    settings = load_settings(tmp_path / ".env.missing")

    assert settings.default_preset == "medium"


def test_crf_is_clamped(monkeypatch, tmp_path):
    monkeypatch.setenv("DEFAULT_CRF", "80")

    settings = load_settings(tmp_path / ".env.missing")

    assert settings.default_crf == 51


def test_non_numeric_ffmpeg_threads_falls_back_to_default(monkeypatch, tmp_path):
    monkeypatch.setattr(os, "cpu_count", lambda: 8)
    monkeypatch.setenv("FFMPEG_THREADS", "abc")
    monkeypatch.delenv("BATCH_SIZE", raising=False)

    settings = load_settings(tmp_path / ".env.missing")

    assert settings.ffmpeg_threads == 2
    assert settings.batch_size == 4


def test_log_file_points_to_home(tmp_path):
    settings = load_settings(tmp_path / ".env.missing")

    assert settings.log_file == Path.home() / ".mov2mp4_converter.log"


def test_unset_batch_size_uses_cpu_count_and_threads(monkeypatch, tmp_path):
    monkeypatch.setattr(os, "cpu_count", lambda: 8)
    monkeypatch.setenv("FFMPEG_THREADS", "2")
    monkeypatch.delenv("BATCH_SIZE", raising=False)

    settings = load_settings(tmp_path / ".env.missing")

    assert settings.batch_size == 4
