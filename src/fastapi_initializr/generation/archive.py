"""Build deterministic, safe zip archives."""

from __future__ import annotations

import io
import re
from collections.abc import Mapping
from pathlib import PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

_SAFE_FILENAME = re.compile(r"[^a-z0-9._-]+")


def archive_filename(name: str) -> str:
    """Return a safe download filename."""
    cleaned = _SAFE_FILENAME.sub("-", name.strip().lower()).strip("-._")
    return f"{cleaned or 'project'}.zip"


def _validate_path(path: str) -> str:
    if not path or "\x00" in path or "\\" in path:
        raise ValueError(f"Invalid archive path: {path!r}")
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or pure.name in {"", "."}:
        raise ValueError(f"Invalid archive path: {path!r}")
    return pure.as_posix()


def build_zip(files: Mapping[str, str], *, root: str | None = None) -> bytes:
    """Build a zip from relative text files with a fixed timestamp."""
    root_path = _validate_path(root) if root else None
    if root_path and "/" in root_path:
        raise ValueError("Archive root must be a single directory name.")

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        for path, content in sorted(files.items()):
            relative = _validate_path(path)
            arcname = f"{root_path}/{relative}" if root_path else relative
            info = ZipInfo(arcname, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content.encode("utf-8"))
    return buffer.getvalue()
