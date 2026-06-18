import argparse
from dataclasses import replace
from pathlib import Path
import sys
import threading

from .config import PRESETS, load_settings
from .converter import convert_batch, ensure_ffmpeg
from .logging_config import configure_logging


def build_parser():
    parser = argparse.ArgumentParser(description="Convert MOV files to MP4 with ffmpeg.")
    parser.add_argument("files", nargs="+", help="MOV files to convert")
    parser.add_argument("-o", "--output", default=".", help="Output directory")
    parser.add_argument("--crf", type=int, default=None, help="Quality from 0 to 51; lower is better")
    parser.add_argument("--preset", choices=PRESETS, default=None)
    parser.add_argument("--ffmpeg-bin", default=None)
    parser.add_argument("--threads", type=int, default=None, help="Threads per ffmpeg process")
    parser.add_argument("--batch-size", type=int, default=None, help="Concurrent conversions")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    settings = load_settings()

    if args.ffmpeg_bin:
        settings = replace(settings, ffmpeg_bin=args.ffmpeg_bin)

    if args.threads:
        settings = replace(settings, ffmpeg_threads=max(1, args.threads))

    if args.batch_size:
        settings = replace(settings, batch_size=max(1, args.batch_size))

    logger = configure_logging(settings.log_file)

    if not ensure_ffmpeg(settings):
        print(f"ffmpeg not found: {settings.ffmpeg_bin}", file=sys.stderr)
        return 1

    def progress(done, total, result):
        status = "ok" if result.success else "cancelled" if result.cancelled else "error"
        print(f"[{done}/{total}] {status}: {result.input_path}")

    results = convert_batch(
        args.files,
        Path(args.output),
        settings,
        crf=args.crf,
        preset=args.preset,
        cancel_event=threading.Event(),
        progress_callback=progress,
        logger=logger,
    )

    failed = [result for result in results if not result.success]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
