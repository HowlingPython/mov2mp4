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


def patch_cli_basics(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "load_settings", lambda: make_settings(tmp_path))
    monkeypatch.setattr(cli, "ensure_ffmpeg", lambda settings: True)
    monkeypatch.setattr(cli, "configure_logging", lambda log_file: None)


def test_sigint_sets_cancel_event_and_main_returns_130(monkeypatch, tmp_path, capsys):
    patch_cli_basics(monkeypatch, tmp_path)

    video = tmp_path / "video.mov"
    video.write_text("")

    previous_handler = object()
    installed_handlers = []

    monkeypatch.setattr(cli.signal, "getsignal", lambda sig: previous_handler)

    def fake_signal(sig, handler):
        installed_handlers.append((sig, handler))
        return previous_handler

    monkeypatch.setattr(cli.signal, "signal", fake_signal)

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
        assert cancel_event is not None
        assert not cancel_event.is_set()

        handler = installed_handlers[0][1]
        handler(cli.signal.SIGINT, None)

        assert cancel_event.is_set()

        return [
            SimpleNamespace(
                success=False,
                cancelled=True,
                input_path=input_files[0],
            )
        ]

    monkeypatch.setattr(cli, "convert_batch", fake_convert_batch)

    code = cli.main([str(video), "-o", str(tmp_path)])

    assert code == 130
    assert "Cancelando conversiones activas" in capsys.readouterr().err
    assert installed_handlers[0][0] == cli.signal.SIGINT
    assert installed_handlers[-1] == (cli.signal.SIGINT, previous_handler)


def test_second_sigint_raises_keyboard_interrupt_and_restores_handler(
    monkeypatch,
    tmp_path,
):
    patch_cli_basics(monkeypatch, tmp_path)

    video = tmp_path / "video.mov"
    video.write_text("")

    previous_handler = object()
    installed_handlers = []

    monkeypatch.setattr(cli.signal, "getsignal", lambda sig: previous_handler)

    def fake_signal(sig, handler):
        installed_handlers.append((sig, handler))
        return previous_handler

    monkeypatch.setattr(cli.signal, "signal", fake_signal)

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
        handler = installed_handlers[0][1]

        handler(cli.signal.SIGINT, None)

        assert cancel_event.is_set()

        handler(cli.signal.SIGINT, None)

    monkeypatch.setattr(cli, "convert_batch", fake_convert_batch)

    with pytest.raises(KeyboardInterrupt):
        cli.main([str(video), "-o", str(tmp_path)])

    assert installed_handlers[-1] == (cli.signal.SIGINT, previous_handler)