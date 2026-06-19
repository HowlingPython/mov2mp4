import pytest

from mov2mp4.paths import collect_input_files


def test_single_mov_file_passed_directly_without_pattern(tmp_path):
    file = tmp_path / "video.mov"
    file.write_text("")

    files = collect_input_files([file])

    assert files == [file]


def test_directory_without_recursive_does_not_scan_subdirectories(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()

    root_file = tmp_path / "root.mov"
    nested_file = nested / "child.mov"

    root_file.write_text("")
    nested_file.write_text("")

    files = collect_input_files([tmp_path])

    assert files == [root_file]


def test_directory_with_recursive_scans_subdirectories(tmp_path):
    nested = tmp_path / "nested"
    nested.mkdir()

    root_file = tmp_path / "root.mov"
    nested_file = nested / "child.mov"

    root_file.write_text("")
    nested_file.write_text("")

    files = collect_input_files([tmp_path], recursive=True)

    assert set(files) == {root_file, nested_file}


def test_invalid_regex_raises_value_error(tmp_path):
    with pytest.raises(ValueError, match="Invalid regex"):
        collect_input_files([tmp_path], pattern="[")


def test_case_sensitive_pattern_does_not_match_different_case(tmp_path):
    file = tmp_path / "VIDEO.mov"
    file.write_text("")

    insensitive = collect_input_files([tmp_path], pattern="video")
    sensitive = collect_input_files(
        [tmp_path],
        pattern="video",
        case_sensitive=True,
    )

    assert insensitive == [file]
    assert sensitive == []


def test_duplicate_file_found_directly_and_through_directory_is_deduped(tmp_path):
    file = tmp_path / "video.mov"
    file.write_text("")

    files = collect_input_files([file], directories=[tmp_path])

    assert files == [file]


def test_non_mov_file_that_does_not_match_pattern_is_ignored(tmp_path):
    file = tmp_path / "video.mp4"
    file.write_text("")

    files = collect_input_files([file])

    assert files == []


def test_non_matching_files_in_directory_are_ignored_silently(tmp_path):
    (tmp_path / "video.mp4").write_text("")
    (tmp_path / "notes.txt").write_text("")
    (tmp_path / "image.png").write_text("")

    files = collect_input_files([tmp_path])

    assert files == []


def test_directory_parameter_scans_directories_directly(tmp_path):
    file = tmp_path / "video.mov"
    file.write_text("")

    files = collect_input_files([], directories=[tmp_path])

    assert files == [file]


def test_valid_regex_with_no_matches_returns_empty_list(tmp_path):
    (tmp_path / "random.mov").write_text("")
    (tmp_path / "other.mov").write_text("")

    files = collect_input_files(
        [tmp_path],
        pattern=r"^trial_",
    )

    assert files == []
