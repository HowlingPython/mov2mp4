import threading
from pathlib import Path

import pytest

from mov2mp4 import converter
from mov2mp4.config import Settings
from mov2mp4.converter import (
    ConversionResult,
    build_ffmpeg_command,
    convert_batch,
    convert_file,
    output_path_for,
)


def settings(**kwargs):
    data = {
        "ffmpeg_bin": "ffmpeg",
        "ffmpeg_threads": 2,
        "batch_size": 2,
        "default_crf": 18,
        "default_preset": "medium",
        "log_file": Path("test.log"),
    }
    data.update(kwargs)
    return Settings(**data)


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


def test_convert_file_handles_missing_ffmpeg_binary(tmp_path):
    result = convert_file(
        tmp_path / "a.mov",
        tmp_path,
        settings(ffmpeg_bin="ffmpeg-que-no-existe-123456"),
    )

    assert not result.success
    assert not result.cancelled
    assert result.message


def test_convert_file_success_without_real_ffmpeg(monkeypatch, tmp_path):
    calls = []

    class FakeStderr:
        def read(self):
            return ""

    class FakeProcess:
        def __init__(self):
            self.returncode = 0
            self.stderr = FakeStderr()

        def poll(self):
            return self.returncode

    def fake_popen(cmd, *args, **kwargs):
        calls.append(cmd)
        return FakeProcess()

    monkeypatch.setattr(converter.subprocess, "Popen", fake_popen)

    result = convert_file(
        tmp_path / "video.mov",
        tmp_path / "out",
        settings(),
    )

    assert result.success
    assert not result.cancelled
    assert result.input_path == tmp_path / "video.mov"
    assert result.output_path == tmp_path / "out" / "video.mp4"
    assert calls
    assert calls[0][0] == "ffmpeg"


def test_convert_batch_empty_list_returns_empty_list(tmp_path):
    assert convert_batch([], tmp_path, settings()) == []


def test_convert_batch_calls_progress_callback_once_per_file(monkeypatch, tmp_path):
    input_files = [
        tmp_path / "a.mov",
        tmp_path / "b.mov",
        tmp_path / "c.mov",
    ]
    calls = []

    def fake_convert_file(
        input_path,
        output_dir,
        settings,
        crf=None,
        preset=None,
        cancel_event=None,
        logger=None,
    ):
        input_path = Path(input_path)
        return ConversionResult(
            input_path=input_path,
            output_path=Path(output_dir) / f"{input_path.stem}.mp4",
            success=True,
        )

    def progress_callback(done, total, result):
        calls.append((done, total, result.input_path.name))

    monkeypatch.setattr(converter, "convert_file", fake_convert_file)

    results = convert_batch(
        input_files,
        tmp_path / "out",
        settings(),
        progress_callback=progress_callback,
    )

    assert len(results) == 3
    assert len(calls) == 3
    assert [done for done, _, _ in calls] == [1, 2, 3]
    assert all(total == 3 for _, total, _ in calls)
    assert {name for _, _, name in calls} == {"a.mov", "b.mov", "c.mov"}
