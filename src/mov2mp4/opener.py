import os
import platform
import subprocess
from pathlib import Path


def open_folder(path):
    path = Path(path)

    if platform.system() == "Windows":
        os.startfile(path)
    elif platform.system() == "Darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)
