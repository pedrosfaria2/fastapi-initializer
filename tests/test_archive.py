"""Safe deterministic archive behavior."""

import io
from zipfile import ZipFile

import pytest

from fastapi_initializr.generation.archive import archive_filename, build_zip


def test_builds_deterministic_zip_with_root() -> None:
    first = build_zip({"a.txt": "alpha", "nested/b.txt": "beta"}, root="demo")
    second = build_zip({"a.txt": "alpha", "nested/b.txt": "beta"}, root="demo")

    assert first == second
    with ZipFile(io.BytesIO(first)) as archive:
        assert archive.namelist() == ["demo/a.txt", "demo/nested/b.txt"]
        assert archive.read("demo/a.txt") == b"alpha"
        assert archive.getinfo("demo/a.txt").date_time == (1980, 1, 1, 0, 0, 0)


@pytest.mark.parametrize(
    "path",
    ["../evil.txt", "/absolute.txt", "a/../../evil.txt", "bad\\path.txt", ""],
)
def test_rejects_unsafe_paths(path: str) -> None:
    with pytest.raises(ValueError, match="Invalid archive path"):
        build_zip({path: "content"})


def test_rejects_unsafe_root() -> None:
    with pytest.raises(ValueError, match="Invalid archive path"):
        build_zip({"a.txt": "alpha"}, root="../demo")


def test_archive_filename_is_safe() -> None:
    assert archive_filename("My Service!") == "my-service.zip"
    assert archive_filename("../../") == "project.zip"


def test_empty_zip_is_valid() -> None:
    content = build_zip({})

    with ZipFile(io.BytesIO(content)) as archive:
        assert archive.namelist() == []
