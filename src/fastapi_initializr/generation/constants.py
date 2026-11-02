"""Shared generation constants."""

SUPPORTED_PYTHON_VERSIONS: tuple[str, ...] = ("3.11", "3.12", "3.13", "3.14")
DEFAULT_PYTHON_VERSION = "3.13"


def core_packages() -> tuple[str, ...]:
    """Return the runtime packages every generated project declares."""
    return (
        "fastapi",
        "fastapi-cli",
        "uvicorn[standard]",
        "pydantic-settings",
        "python-multipart",
    )


def core_dev_packages() -> tuple[str, ...]:
    """Return the development packages every generated project declares."""
    return (
        "pytest",
        "pytest-cov",
        "httpx2",
        "ruff",
        "mypy",
        "pyright",
    )
