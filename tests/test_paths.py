"""
Tests for audio_pipeline.paths: workspace path safety rules.
"""

from pathlib import Path

import pytest

from audio_pipeline.paths import PathRejectedError, resolve_input, resolve_output


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """
    Mock dir for data/
    """
    workspace = tmp_path / "data"
    workspace.mkdir()
    return workspace


def make_audio(dir: Path, name: str = "talk.wav", size: int = 10) -> Path:
    """
    Test audio file. Only name and size matters to these rules.
    """
    file = dir / name
    file.write_bytes(b"\0" * size)
    return file


# --- INPUT RULES ---


def test_input_accepts_valid_file(workspace: Path) -> None:
    file = make_audio(workspace)
    assert resolve_input(file, workspace=workspace) == file.resolve()


def test_input_accepts_str_and_upper_extension(workspace: Path) -> None:
    file = make_audio(workspace, "TALK.WAV")
    assert resolve_input(str(file), workspace=workspace) == file.resolve()


def test_input_rejects_missing_file(workspace: Path) -> None:
    with pytest.raises(PathRejectedError):
        resolve_input(workspace / "nope.wav", workspace=workspace)


def test_input_rejects_dir(workspace: Path) -> None:
    (workspace / "folder.wav").mkdir()
    with pytest.raises(PathRejectedError):
        resolve_input(workspace / "folder.wav", workspace=workspace)


def test_input_rejects_disallowed_extension(workspace: Path) -> None:
    file = make_audio(workspace, "notes.txt")
    with pytest.raises(PathRejectedError):
        resolve_input(file, workspace=workspace)


def test_input_rejects_dotdot_traversal(workspace: Path, tmp_path: Path) -> None:
    make_audio(tmp_path, "outside.wav")
    sneaky = workspace / ".." / "outside.wav"
    with pytest.raises(PathRejectedError):
        resolve_input(sneaky, workspace=workspace)


def test_input_rejects_absolute_path_outside(workspace: Path, tmp_path: Path) -> None:
    outside = make_audio(tmp_path, "outside.wav")
    with pytest.raises(PathRejectedError):
        resolve_input(outside, workspace=workspace)


def test_input_rejects_sibling_with_same_prefix(tmp_path: Path) -> None:
    workspace = tmp_path / "data"
    workspace.mkdir()
    evil = tmp_path / "data_evil"
    evil.mkdir()
    file = make_audio(evil)
    with pytest.raises(PathRejectedError):
        resolve_input(file, workspace=workspace)


def test_input_rejects_symlink_pointing_outside(
    workspace: Path, tmp_path: Path
) -> None:
    outside = make_audio(tmp_path, "secrets.wav")
    link = workspace / "link.wav"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("this system does not allow creating symlinks")
    with pytest.raises(PathRejectedError):
        resolve_input(link, workspace=workspace)


def test_input_rejects_file_over_size_limit(workspace: Path) -> None:
    file = make_audio(workspace, size=10)
    with pytest.raises(PathRejectedError):
        resolve_input(file, workspace=workspace, max_bytes=5)


# --- OUTPUT RULES ---


def test_output_accepts_new_file(workspace: Path) -> None:
    target = workspace / "talk_vocals.wav"
    assert resolve_output(target, workspace=workspace) == target.resolve()


def test_output_rejects_existing_file(workspace: Path) -> None:
    existing = make_audio(workspace, "talk_vocals.wav")
    with pytest.raises(PathRejectedError):
        resolve_output(existing, workspace=workspace)


def test_output_rejects_dotdot_traversal(workspace: Path) -> None:
    with pytest.raises(PathRejectedError):
        resolve_output(workspace / ".." / "out.wav", workspace=workspace)


def test_output_rejects_absolute_path_outside(workspace: Path, tmp_path: Path) -> None:
    with pytest.raises(PathRejectedError):
        resolve_output(tmp_path / "out.wav", workspace=workspace)


def test_output_rejects_disallowed_extension(workspace: Path) -> None:
    with pytest.raises(PathRejectedError):
        resolve_output(workspace / "out.exe", workspace=workspace)


def test_output_rejects_missing_parent_folder(workspace: Path) -> None:
    with pytest.raises(PathRejectedError):
        resolve_output(workspace / "no_such_dir" / "out.wav", workspace=workspace)
