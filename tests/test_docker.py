"""Generator image definition invariants."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_pins_tools_and_runs_unprivileged() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "ghcr.io/astral-sh/uv:latest" in dockerfile
    assert "--locked --no-dev --no-editable" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert (
        'CMD ["uvicorn", "fastapi_initializr.main:app", "--host", "0.0.0.0", "--port", "8000"]'
        in dockerfile
    )


def test_dockerfile_python_matches_the_project_pin() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    bases = [
        line.split(":")[1].split("-")[0]
        for line in dockerfile.splitlines()
        if line.startswith("FROM python:")
    ]
    project_python = (ROOT / ".python-version").read_text(encoding="utf-8").strip()

    assert bases, "Dockerfile must use a python base image"
    assert all(base == project_python for base in bases)
    assert "UV_PYTHON_DOWNLOADS=0" in dockerfile


def test_dockerignore_excludes_local_artifacts() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

    for entry in (
        ".git",
        ".venv",
        ".agents",
        "agent-reports",
        ".pytest_cache",
        "dist",
    ):
        assert entry in dockerignore
