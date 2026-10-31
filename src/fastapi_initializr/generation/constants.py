"""Shared generation constants."""

SUPPORTED_PYTHON_VERSIONS: tuple[str, ...] = ("3.11", "3.12", "3.13", "3.14")
DEFAULT_PYTHON_VERSION = "3.13"

SUPPORTED_FASTAPI_VERSIONS: tuple[str, ...] = ("0.162.0", "0.161.1", "0.160.0")
DEFAULT_FASTAPI_VERSION = "0.162.0"


def fastapi_version_range(version: str) -> str:
    """Return a bounded dependency range for a supported FastAPI version."""
    major, minor, _patch = (int(part) for part in version.split("."))
    return f">={version},<{major}.{minor + 1}.0"
