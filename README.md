# mov2mp4

Lightweight desktop tool for batch-converting MOV files to MP4 using Python, Tkinter and ffmpeg.

The original use case was converting iPhone-recorded oscillation videos for frame-by-frame analysis in a physics experiment. The project is now organized as a proper Python package with a reusable conversion core, a GUI entry point, a CLI entry point, tests and `uv`-based project management.

## Features

* Batch conversion of multiple `.mov` files.
* Dynamic GUI built with Tkinter.
* CLI entry point for terminal-based conversion.
* Multithreaded conversion using `ThreadPoolExecutor`.
* Clean cancellation of active conversions.
* Configurable CRF, preset, ffmpeg binary, thread count and batch size.
* Rotating log written to `~/.mov2mp4_converter.log`.
* Standalone executable support through PyInstaller.

## Requirements

The project requires Python `>=3.10`, `uv`, and `ffmpeg` available in `PATH`.

`ffmpeg` is a system dependency, not a Python dependency. The project calls the `ffmpeg` executable through `subprocess`, so it must be installed separately unless `FFMPEG_BIN` is set in `.env`.

Check that `ffmpeg` is installed:

```bash
ffmpeg -version
```

On Ubuntu or Debian:

```bash
sudo apt install ffmpeg python3-tk
```

On macOS, using Homebrew:

```bash
brew install ffmpeg
```

On Windows, install ffmpeg and make sure the executable is available from PowerShell or CMD.

## Installation

From the repository root:

```bash
uv sync --extra dev
```

This creates or updates `.venv`, installs runtime dependencies and installs development dependencies such as `pytest` and `pyinstaller`.

After the first successful sync, `uv` generates `uv.lock`. Commit that file to keep dependency resolution reproducible across machines.

You do not need to activate the virtual environment. Use `uv run`.

## Usage

Open the GUI:

```bash
uv run mov2mp4-gui
```

Convert files from the command line:

```bash
uv run mov2mp4 video1.mov video2.mov -o output/
```

Set quality options from the CLI:

```bash
uv run mov2mp4 video.mov -o output/ --crf 18 --preset medium
```

Lower CRF means higher quality and larger files. Valid CRF values are from `0` to `51`.

## GUI workflow

1. Run `uv run mov2mp4-gui`.
2. Click `Seleccionar y convertir`.
3. Select one or more `.mov` files.
4. Select an output folder.
5. Wait for the progress bar or press `Cancelar` to stop cleanly.

Cancellation kills active `ffmpeg` processes and removes incomplete output files.

## Configuration

Create a `.env` file in the project root to override defaults:

```env
FFMPEG_BIN=ffmpeg
FFMPEG_THREADS=2
BATCH_SIZE=
DEFAULT_CRF=18
DEFAULT_PRESET=medium
DEFAULT_FONT_SIZE=15
```

`FFMPEG_BIN` can be used to point directly to an ffmpeg executable when it is not available globally in `PATH`.

`FFMPEG_THREADS` controls how many threads each ffmpeg process may use.

`BATCH_SIZE` controls how many conversions run at the same time. If it is empty, the project chooses a conservative value from the CPU count and `FFMPEG_THREADS`.

`DEFAULT_CRF` controls video quality. Lower values produce higher quality and larger files.

`DEFAULT_PRESET` controls encoding speed versus compression efficiency.

`DEFAULT_FONT_SIZE` controls the default text size in the app. The GUI clamps it to a readable range and can also scale it upward on high-resolution screens. (Currently Broken)

## Tests

Run:

```bash
uv run pytest -q
```

The tests do not require real MOV files or ffmpeg execution. They validate command construction, configuration parsing and cancellation behavior.

## Building a standalone executable

Build the GUI with PyInstaller:

```bash
uv run pyinstaller mov2mp4_gui.spec
```

The executable is written to `dist/`.

The spec file uses `scripts/mov2mp4_gui.py` as a small launcher and includes `src/` in `pathex`, so PyInstaller can find the package.

The generated executable still requires ffmpeg to be available on the target machine unless the build is modified to bundle an ffmpeg binary explicitly.

## Project layout

```text
mov2mp4/
├── .env.example
├── .gitignore
├── .python-version
├── LICENSE
├── README.md
├── mov2mp4_gui.spec
├── pyproject.toml
├── uv.lock
├── scripts/
│   └── mov2mp4_gui.py
├── src/
│   └── mov2mp4/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── config.py
│       ├── converter.py
│       ├── gui.py
│       ├── logging_config.py
│       └── opener.py
└── tests/
    ├── test_config.py
    └── test_converter.py
```

`converter.py` contains the conversion logic and knows how to build and run `ffmpeg` commands.

`gui.py` contains the Tkinter UI logic, including the dynamic layout, runtime font-size control (currently broken), and thread-safe queue polling.

`cli.py` exposes the command-line interface.

`config.py` loads environment-based settings.

`logging_config.py` configures the rotating log.

`opener.py` contains platform-specific output-folder opening logic.

## Notes on the threading model

Tkinter is not thread-safe. The GUI starts conversion in a background thread and receives progress messages through `queue.Queue`.

The UI polls the queue with `after()`, so worker threads never mutate widgets directly. This keeps the interface responsive while conversions are running.

## Git hygiene

The repository should not track generated files, local environments or converted videos.

The `.gitignore` should exclude at least:

```text
__pycache__/
*.pyc
.pytest_cache/
.venv/
*.egg-info/
build/
dist/
*.mov
*.mp4
*.log
.env
```

Do not ignore `uv.lock`. It should be committed.

## License

MIT.
