import threading
from pathlib import Path

import pytest

from mov2mp4.config import Settings
from mov2mp4.converter import build_ffmpeg_command, convert_file, output_path_for


def settings():
    return Settings(
        ffmpeg_bin="ffmpeg",
        ffmpeg_threads=2,
        batch_size=2,
        default_crf=18,
        default_preset="medium",
        default_font_size=15,
        log_file=Path("test.log"),
    )


def test_output_path_keeps_stem_and_changes_extension():
    assert output_path_for("input/video.mov", "out") == Path("out/video.mp4")


def test_build_ffmpeg_command_contains_quality_options():
    cmd = build_ffmpeg_command(
        Path("video.mov"),
        Path("out/video.mp4"),
        settings(),
        crf=20,
        preset="fast",
    )

    assert cmd[:5] == ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y"]
    assert "-crf" in cmd
    assert "20" in cmd
    assert "-preset" in cmd
    assert "fast" in cmd
    assert cmd[-1] == "out/video.mp4"


def test_invalid_crf_raises():
    with pytest.raises(ValueError):
        build_ffmpeg_command(Path("a.mov"), Path("a.mp4"), settings(), 99, "medium")


def test_cancelled_before_start_does_not_run_ffmpeg(tmp_path):
    cancel_event = threading.Event()
    cancel_event.set()

    result = convert_file(
        tmp_path / "a.mov",
        tmp_path,
        settings(),
        cancel_event=cancel_event,
    )

    assert result.cancelled
    assert not result.success
