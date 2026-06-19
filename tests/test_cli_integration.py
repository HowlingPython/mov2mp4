from types import SimpleNamespace

import pytest

from mov2mp4 import cli
from mov2mp4.config import Settings


def make_settings(tmp_path):
    return Settings(
        ffmpeg_bin="ffmpeg",
        ffmpeg_threads=2,
        batch_size=2,
        default_crf=18,
        default_preset="medium",
        log_file=tmp_path / "test.log",
    )


def patch_cli_success(monkeypatch, tmp_path, calls):
    monkeypatch.setattr(cli, "load_settings", lambda: make_settings(tmp_path))
    monkeypatch.setattr(cli, "ensure_ffmpeg", lambda settings: True)
    monkeypatch.setattr(cli, "configure_logging", lambda log_file: None)

    def fake_convert_batch(
        input_files,
        output_dir,
        settings,
        crf=None,
        preset=None,
        cancel_event=None,
        progress_callback=None,
        logger=None,
    ):
        calls.append(
            {
                "input_files": input_files,
                "output_dir": output_dir,
                "settings": settings,
                "crf": crf,
                "preset": preset,
            }
        )

        if progress_callback:
            for done, file in enumerate(input_files, start=1):
                result = SimpleNamespace(
                    success=True,
                    cancelled=False,
                    input_path=file,
                )
                progress_callback(done, len(input_files), result)

        return [SimpleNamespace(success=True) for _ in input_files]

    monkeypatch.setattr(cli, "convert_batch", fake_convert_batch)


def test_no_inputs_found_exits_with_error(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["-d", str(tmp_path)])

    assert exc_info.value.code == 2
    assert "No MOV files" in capsys.readouterr().err


def test_invalid_pattern_exits_with_error(tmp_path, capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main([str(tmp_path), "--pattern", "["])

    assert exc_info.value.code == 2
    assert "Invalid regex" in capsys.readouterr().err


def test_main_converts_mov_files_from_positional_directory(monkeypatch, tmp_path):
    calls = []
    patch_cli_success(monkeypatch, tmp_path, calls)

    videos = tmp_path / "videos"
    output = tmp_path / "output"
    videos.mkdir()

    (videos / "a.mov").write_text("")
    (videos / "b.MOV").write_text("")
    (videos / "c.mp4").write_text("")

    code = cli.main([str(videos), "-o", str(output)])

    assert code == 0
    assert len(calls) == 1
    assert [file.name for file in calls[0]["input_files"]] == ["a.mov", "b.MOV"]
    assert calls[0]["output_dir"] == output


def test_main_uses_directory_option_and_pattern(monkeypatch, tmp_path):
    calls = []
    patch_cli_success(monkeypatch, tmp_path, calls)

    videos = tmp_path / "videos"
    output = tmp_path / "output"
    videos.mkdir()

    (videos / "trial_01.mov").write_text("")
    (videos / "random.mov").write_text("")

    code = cli.main(
        [
            "--directory",
            str(videos),
            "--pattern",
            r"^trial_",
            "-o",
            str(output),
        ]
    )

    assert code == 0
    assert [file.name for file in calls[0]["input_files"]] == ["trial_01.mov"]


def test_main_recursive_option_reaches_nested_files(monkeypatch, tmp_path):
    calls = []
    patch_cli_success(monkeypatch, tmp_path, calls)

    videos = tmp_path / "videos"
    nested = videos / "nested"
    output = tmp_path / "output"

    nested.mkdir(parents=True)

    (videos / "root.mov").write_text("")
    (nested / "child.mov").write_text("")

    code = cli.main([str(videos), "--recursive", "-o", str(output)])

    assert code == 0
    assert {file.name for file in calls[0]["input_files"]} == {
        "root.mov",
        "child.mov",
    }


def test_main_passes_quality_options_to_converter(monkeypatch, tmp_path):
    calls = []
    patch_cli_success(monkeypatch, tmp_path, calls)

    video = tmp_path / "video.mov"
    output = tmp_path / "output"
    video.write_text("")

    code = cli.main(
        [
            str(video),
            "-o",
            str(output),
            "--crf",
            "20",
            "--preset",
            "fast",
        ]
    )

    assert code == 0
    assert calls[0]["crf"] == 20
    assert calls[0]["preset"] == "fast"


def test_main_returns_1_when_any_conversion_fails(monkeypatch, tmp_path):
    video = tmp_path / "a.mov"
    video.write_text("")

    fake_result = SimpleNamespace(
        success=False,
        cancelled=False,
        input_path=video,
    )

    monkeypatch.setattr(cli, "load_settings", lambda: make_settings(tmp_path))
    monkeypatch.setattr(cli, "ensure_ffmpeg", lambda settings: True)
    monkeypatch.setattr(cli, "configure_logging", lambda log_file: None)
    monkeypatch.setattr(cli, "convert_batch", lambda *args, **kwargs: [fake_result])

    code = cli.main([str(video), "-o", str(tmp_path)])

    assert code == 1


def test_main_returns_1_when_ffmpeg_is_missing(monkeypatch, tmp_path, capsys):
    calls = []

    video = tmp_path / "a.mov"
    video.write_text("")

    monkeypatch.setattr(cli, "load_settings", lambda: make_settings(tmp_path))
    monkeypatch.setattr(cli, "ensure_ffmpeg", lambda settings: False)
    monkeypatch.setattr(cli, "configure_logging", lambda log_file: None)

    def fail_if_called(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("convert_batch should not be called")

    monkeypatch.setattr(cli, "convert_batch", fail_if_called)

    code = cli.main([str(video), "-o", str(tmp_path)])

    assert code == 1
    assert calls == []
    assert "ffmpeg not found" in capsys.readouterr().err