import os
import subprocess
import sys
from pathlib import Path


def test_python_m_mov2mp4_propagates_main_exit_code(tmp_path):
    root = Path(__file__).resolve().parents[1]
    video = tmp_path / "a.mov"
    video.write_text("")

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{root / 'src'}{os.pathsep}{env.get('PYTHONPATH', '')}"

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "mov2mp4",
            str(video),
            "-o",
            str(tmp_path),
            "--ffmpeg-bin",
            "ffmpeg-que-no-existe-123456",
        ],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
    )

    assert proc.returncode == 1
    assert "ffmpeg not found" in proc.stderr