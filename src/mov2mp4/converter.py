import platform
import shutil
import subprocess
import threading
import time
from concurrent.futures import CancelledError, ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from .config import PRESETS, Settings


@dataclass(frozen=True)
class ConversionResult:
    input_path: Path
    output_path: Path
    success: bool
    cancelled: bool = False
    message: str = ""


def ensure_ffmpeg(settings):
    return shutil.which(settings.ffmpeg_bin) is not None


def output_path_for(input_path, output_dir):
    return Path(output_dir) / f"{Path(input_path).stem}.mp4"


def build_ffmpeg_command(input_path, output_path, settings, crf, preset):
    if not 0 <= int(crf) <= 51:
        raise ValueError("CRF must be between 0 and 51")

    if preset not in PRESETS:
        raise ValueError(f"Invalid preset: {preset}")

    return [
        settings.ffmpeg_bin,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(input_path),
        "-c:v",
        "libx264",
        "-crf",
        str(crf),
        "-preset",
        preset,
        "-threads",
        str(settings.ffmpeg_threads),
        str(output_path),
    ]


def _cleanup(path, logger=None):
    try:
        Path(path).unlink(missing_ok=True)
    except OSError as exc:
        if logger:
            logger.warning("Could not remove incomplete output %s: %s", path, exc)


def convert_file(
    input_path,
    output_dir,
    settings,
    crf=None,
    preset=None,
    cancel_event=None,
    logger=None,
):
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_path_for(input_path, output_dir)

    cancel_event = cancel_event or threading.Event()
    crf = settings.default_crf if crf is None else int(crf)
    preset = settings.default_preset if preset is None else preset

    if cancel_event.is_set():
        return ConversionResult(input_path, output_path, False, True, "cancelled")

    cmd = build_ffmpeg_command(input_path, output_path, settings, crf, preset)
    creationflags = (
        getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if platform.system() == "Windows"
        else 0
    )

    if logger:
        logger.info("Converting %s -> %s", input_path, output_path)

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=creationflags,
        )
    except OSError as exc:
        return ConversionResult(input_path, output_path, False, False, str(exc))

    while process.poll() is None:
        if cancel_event.is_set():
            process.kill()
            process.wait()
            _cleanup(output_path, logger)
            return ConversionResult(input_path, output_path, False, True, "cancelled")

        time.sleep(0.1)

    stderr = process.stderr.read() if process.stderr else ""

    if process.returncode == 0:
        return ConversionResult(input_path, output_path, True, False, "")

    _cleanup(output_path, logger)
    message = stderr.strip() or f"ffmpeg exited with code {process.returncode}"
    if logger:
        logger.error("Failed converting %s: %s", input_path, message)

    return ConversionResult(input_path, output_path, False, False, message)


def convert_batch(
    files,
    output_dir,
    settings,
    crf=None,
    preset=None,
    cancel_event=None,
    progress_callback=None,
    logger=None,
):
    files = [Path(file) for file in files]
    cancel_event = cancel_event or threading.Event()

    if not files:
        return []

    results = []

    with ThreadPoolExecutor(max_workers=settings.batch_size) as executor:
        futures = [
            executor.submit(
                convert_file,
                file,
                output_dir,
                settings,
                crf,
                preset,
                cancel_event,
                logger,
            )
            for file in files
        ]

        for completed, future in enumerate(as_completed(futures), start=1):
            try:
                result = future.result()
            except CancelledError:
                continue

            results.append(result)

            if progress_callback:
                progress_callback(completed, len(files), result)

            if cancel_event.is_set():
                for pending in futures:
                    pending.cancel()
                break
                
    return results
