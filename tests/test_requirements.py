"""Standalone requirements.txt output."""

import tomllib

from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.requirements import render_requirements
from fastapi_initializr.generation.spec import ProjectSpec


def test_minimal_requirements_contain_core_runtime_packages() -> None:
    content = render_requirements(ProjectSpec(name="my-service"))

    assert content.splitlines() == [
        "fastapi",
        "fastapi-cli",
        "pydantic-settings",
        "python-multipart",
        "uvicorn[standard]",
    ]


def test_feature_packages_are_unpinned() -> None:
    content = render_requirements(
        ProjectSpec(
            name="my-service",
            dependencies=frozenset({"sqlalchemy", "postgres"}),
        )
    )
    lines = content.splitlines()

    assert "fastapi" in lines
    assert "sqlalchemy[asyncio]" in lines
    assert "aiosqlite" in lines
    assert "asyncpg" in lines
    assert not any(line.startswith("pytest") for line in lines)


def test_requirements_match_pyproject_runtime_dependencies() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "auth-jwt", "redis"}),
    )
    pyproject = tomllib.loads(render_project(spec)["pyproject.toml"])

    assert render_requirements(spec).splitlines() == sorted(pyproject["project"]["dependencies"])


def test_requirements_are_sorted_and_end_with_a_newline() -> None:
    content = render_requirements(
        ProjectSpec(name="my-service", dependencies=frozenset({"docker", "sqlalchemy"}))
    )
    lines = content.splitlines()

    assert lines == sorted(lines)
    assert content.endswith("\n")


def test_requirements_are_deterministic() -> None:
    spec = ProjectSpec(name="my-service", dependencies=frozenset({"uploads", "s3"}))

    assert render_requirements(spec) == render_requirements(spec)
