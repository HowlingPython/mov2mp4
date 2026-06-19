# mov2mp4

CLI tool for batch-converting MOV files to MP4 using Python and ffmpeg.

Originally written to convert iPhone-recorded oscillation videos before frame-by-frame analysis in a physics experiment. Organized as an installable Python package with a reusable conversion core, tests, and `uv`-based project management.

## Features

- Convert individual files, whole directories, or a mix of both in one command
- Filter directory contents with a regex pattern, optionally case-sensitive
- Recursive directory scanning
- Parallel execution via `ThreadPoolExecutor` with configurable batch size
- Clean cancellation: kills active ffmpeg processes and removes incomplete output files
- Configurable quality settings (CRF, preset, thread count) via CLI flags or `.env`
- Rotating log written to `~/.mov2mp4_converter.log`

## Requirements

Python `>=3.10`, `uv`, and `ffmpeg` available in `PATH`.

`ffmpeg` is a system dependency — the package calls the `ffmpeg` executable through `subprocess` and does not bundle it. Install it separately or point to a binary with `FFMPEG_BIN` in `.env`.

Check that `ffmpeg` is installed:

```bash
ffmpeg -version
```

On Ubuntu or Debian:

```bash
sudo apt install ffmpeg
```

On macOS with Homebrew:

```bash
brew install ffmpeg
```

On Windows, install ffmpeg and ensure the executable is on `PATH`.

## Installation

```bash
uv sync --extra dev
```

This creates `.venv`, installs runtime dependencies, and installs development dependencies (`pytest`). Commit `uv.lock` to keep dependency resolution reproducible.

You do not need to activate the virtual environment — use `uv run`.

## Usage

Convert individual files:

```bash
uv run mov2mp4 video1.mov video2.mov -o output/
```

Convert everything in a directory:

```bash
uv run mov2mp4 -d raw_videos/ -o output/
```

Scan a directory recursively:

```bash
uv run mov2mp4 -d raw_videos/ -r -o output/
```

Filter files by name using a regex pattern:

```bash
uv run mov2mp4 -d raw_videos/ --pattern "^trial_[0-9]+" -o output/
```

By default `--pattern` is case-insensitive. Use `--case-sensitive` to change that.

Files and directories can be combined, and `-d` can be passed more than once:

```bash
uv run mov2mp4 extra_clip.mov -d session1/ -d session2/ -r -o output/
```

Set quality options:

```bash
uv run mov2mp4 video.mov -o output/ --crf 18 --preset medium
```

Lower CRF means higher quality and larger files. Valid range is `0` to `51`.

### CLI reference

| Flag | Description |
|---|---|
| `inputs` | MOV files or directories, positional, any number |
| `-o, --output` | Output directory (default: current directory) |
| `-d, --directory` | Directory to scan for input files; repeatable |
| `--pattern` | Regex matched against filenames found in directories |
| `-r, --recursive` | Scan directories recursively |
| `--case-sensitive` | Make `--pattern` case-sensitive |
| `--crf` | Quality, `0`–`51`, lower is better |
| `--preset` | Encoding speed vs. compression tradeoff |
| `--ffmpeg-bin` | Path to the ffmpeg executable |
| `--threads` | Threads per ffmpeg process |
| `--batch-size` | Concurrent conversions |

Without `--pattern`, directory scans default to matching `*.mov` (case-insensitive). Files passed directly as positional arguments are included even if they don't match the pattern. Duplicate paths reached through more than one input (e.g. a file passed directly and also found via `-d`) are converted once.

## Configuration

Create a `.env` file in the project root to override defaults:

```env
FFMPEG_BIN=ffmpeg
FFMPEG_THREADS=2
BATCH_SIZE=
DEFAULT_CRF=18
DEFAULT_PRESET=medium
```

`FFMPEG_BIN` — path to the ffmpeg binary when not globally available in `PATH`.

`FFMPEG_THREADS` — threads each ffmpeg process may use.

`BATCH_SIZE` — concurrent conversions. If empty, derived from CPU count and `FFMPEG_THREADS`.

`DEFAULT_CRF` — default video quality.

`DEFAULT_PRESET` — default encoding speed vs. compression tradeoff.

CLI flags take precedence over `.env` values.

## Tests

```bash
uv run pytest -q
```

Tests do not require real MOV files or ffmpeg. They validate command construction, configuration parsing, cancellation behavior, and input resolution (file/directory/pattern handling).

## Project layout

```text
mov2mp4/
├── .env.example
├── .gitignore
├── .python-version
├── LICENSE
├── README.md
├── pyproject.toml
├── uv.lock
├── src/
│   └── mov2mp4/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── converter.py
│       ├── logging_config.py
│       └── paths.py
└── tests/
    ├── test_config.py
    ├── test_converter.py
    └── test_paths.py
```

`converter.py` — conversion logic; builds and runs ffmpeg commands, handles cancellation.

`cli.py` — command-line interface and argument parsing.

`paths.py` — resolves CLI inputs (files, directories, patterns) into a deduplicated list of files to convert.

`config.py` — loads and validates environment-based settings into a frozen dataclass.

`logging_config.py` — rotating log setup.

## License

MIT.
