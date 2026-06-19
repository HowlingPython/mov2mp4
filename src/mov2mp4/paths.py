import re
from pathlib import Path

MOV_PATTERN = re.compile(r".*\.mov$", re.IGNORECASE)


def compile_pattern(pattern=None, case_sensitive=False):
    if pattern is None:
        return MOV_PATTERN

    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        return re.compile(pattern, flags)
    except re.error as exc:
        raise ValueError(f"Invalid regex pattern: {exc}") from exc


def matches_file(path, pattern=None):
    path = Path(path)
    regex = pattern or MOV_PATTERN
    return path.is_file() and regex.search(path.name) is not None


def iter_matching_files(directory, pattern=None, recursive=False):
    directory = Path(directory)

    if not directory.is_dir():
        raise ValueError(f"Not a directory: {directory}")

    regex = pattern or MOV_PATTERN
    paths = directory.rglob("*") if recursive else directory.iterdir()

    for path in sorted(paths):
        if matches_file(path, regex):
            yield path


def collect_input_files(
    inputs,
    directories=None,
    pattern=None,
    recursive=False,
    case_sensitive=False,
):
    selected = []
    seen = set()
    directories = directories or []
    regex = compile_pattern(pattern, case_sensitive)

    def add(path):
        path = Path(path)
        key = str(path.resolve())
        if key not in seen:
            selected.append(path)
            seen.add(key)

    def add_directory(directory):
        for path in iter_matching_files(directory, regex, recursive):
            add(path)

    for item in inputs:
        path = Path(item)
        if path.is_dir():
            add_directory(path)
        elif matches_file(path, regex):
            add(path)

    for directory in directories:
        add_directory(directory)

    return selected
