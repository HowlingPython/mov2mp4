import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:

    def load_dotenv(*args, **kwargs):
        return False


PRESETS = (
    "ultrafast",
    "superfast",
    "veryfast",
    "faster",
    "fast",
    "medium",
    "slow",
    "slower",
    "veryslow",
)


@dataclass(frozen=True)
class Settings:
    ffmpeg_bin: str
    ffmpeg_threads: int
    batch_size: int
    default_crf: int
    default_preset: str
    default_font_size: int
    log_file: Path


def _int_env(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _crf(value):
    return max(0, min(51, value))


def _clamp(value, low, high):
    return max(low, min(high, value))


def load_settings(env_file=None):
    load_dotenv(env_file)

    cpu_count = os.cpu_count() or 2
    ffmpeg_threads = max(1, _int_env("FFMPEG_THREADS", 2))
    max_batch = max(1, cpu_count // ffmpeg_threads)

    raw_batch = os.environ.get("BATCH_SIZE", "").strip()
    if raw_batch:
        batch_size = max(1, min(_int_env("BATCH_SIZE", max_batch), max_batch))
    else:
        batch_size = max_batch

    preset = os.environ.get("DEFAULT_PRESET", "medium")
    if preset not in PRESETS:
        preset = "medium"

    return Settings(
        ffmpeg_bin=os.environ.get("FFMPEG_BIN", "ffmpeg"),
        ffmpeg_threads=ffmpeg_threads,
        batch_size=batch_size,
        default_crf=_crf(_int_env("DEFAULT_CRF", 18)),
        default_preset=preset,
        default_font_size=_clamp(_int_env("DEFAULT_FONT_SIZE", 15), 9, 50),
        log_file=Path.home() / ".mov2mp4_converter.log",
    )
