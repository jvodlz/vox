"""
Workspace path rules.

Validates path. Pipeline ONLY takes IN paths from here.
Workspace is passed by the caller.
"""

from pathlib import Path

ALLOWED_EXTENSIONS = frozenset({".wav", ".mp3", ".flac"})
DEFAULT_MAX_BYTES = 500 * 1024 * 1024


class PathRejectedError(Exception):
    """
    A path broke one of the workspace rules.
    """


def _resolve_inside(path: str | Path, workspace: Path) -> Path:
    """
    Resolve symlinks and '..' first, then require the result be inside.
    """
    try:
        resolved = Path(path).resolve()
        root = workspace.resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise PathRejectedError(f"path cannot be resolved: {str(path)!r}") from exc
    if not resolved.is_relative_to(root):
        raise PathRejectedError(f"path is outside the workspace: {str(path)!r}")

    return resolved


def _check_extension(resolved: Path) -> None:
    if resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
        allowed = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise PathRejectedError(f"file type not allowed (use: {allowed})")


def resolve_input(
    path: str | Path,
    *,
    workspace: Path,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Path:
    """
    Return a trusted path to an existing audio file inside the workspace.
    """
    resolved = _resolve_inside(path, workspace)
    _check_extension(resolved)
    if not resolved.is_file():
        raise PathRejectedError(f"not an existing file: {str(path)!r}")
    try:
        size = resolved.stat().st_size
    except OSError as exc:
        raise PathRejectedError(f"file cannot be read: {str(path)!r}") from exc
    if size > max_bytes:
        raise PathRejectedError(f"file is larger than {max_bytes} bytes")

    return resolved


def resolve_output(path: str | Path, *, workspace: Path) -> Path:
    """
    Return a trusted path for a NEW audio file inside the workspace.
    """
    resolved = _resolve_inside(path, workspace)
    _check_extension(resolved)
    if not resolved.parent.is_dir():
        raise PathRejectedError("output folder does not exist")
    if resolved.exists():
        raise PathRejectedError(f"refusing to overwrite: {str(path)!r}")
    return resolved
