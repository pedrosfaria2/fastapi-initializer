"""Generator image definition invariants."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_pins_tools_and_runs_unprivileged() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "ghcr.io/astral-sh/uv:0.13.6" in dockerfile
    assert "--locked --no-dev --no-editable" in dockerfile
    assert "USER app" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert (
        'CMD ["uvicorn", "fastapi_initializr.main:app", "--host", "0.0.0.0", "--port", "8000"]'
        in dockerfile
    )


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
