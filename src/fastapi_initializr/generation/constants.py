"""Shared generation constants."""

SUPPORTED_PYTHON_VERSIONS: tuple[str, ...] = ("3.11", "3.12", "3.13", "3.14")
DEFAULT_PYTHON_VERSION = "3.13"

SUPPORTED_FASTAPI_VERSIONS: tuple[str, ...] = ("0.162.0", "0.161.1", "0.160.0")
DEFAULT_FASTAPI_VERSION = "0.162.0"

UVICORN_VERSION = "0.54.0"
PYDANTIC_SETTINGS_VERSION = "2.16.2"
PYTHON_MULTIPART_VERSION = "0.0.32"


def fastapi_version_range(version: str) -> str:
    """Return a bounded dependency range for a supported FastAPI version."""
    major, minor, _patch = (int(part) for part in version.split("."))
    return f">={version},<{major}.{minor + 1}.0"


def core_packages(fastapi_range: str) -> tuple[str, ...]:
    """Return the runtime packages every generated project declares."""
    return (
        f"fastapi{fastapi_range}",
        "fastapi-cli>=0.0.32",
        f"uvicorn[standard]>={UVICORN_VERSION}",
        f"pydantic-settings>={PYDANTIC_SETTINGS_VERSION}",
        f"python-multipart>={PYTHON_MULTIPART_VERSION}",
    )
