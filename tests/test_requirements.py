"""Standalone requirements.txt output."""

import tomllib

from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.requirements import render_requirements
from fastapi_initializr.generation.spec import ProjectSpec


def test_minimal_requirements_contain_core_runtime_packages() -> None:
    content = render_requirements(ProjectSpec(name="my-service"))

    assert content.splitlines() == [
        "fastapi-cli>=0.0.32",
        "fastapi>=0.162.0,<0.163.0",
        "pydantic-settings>=2.16.2",
        "python-multipart>=0.0.32",
        "uvicorn[standard]>=0.54.0",
    ]


def test_feature_packages_follow_the_selected_versions() -> None:
    content = render_requirements(
        ProjectSpec(
            name="my-service",
            fastapi="0.161.1",
            dependencies=frozenset({"sqlalchemy", "postgres"}),
        )
    )
    lines = content.splitlines()

    assert "fastapi>=0.161.1,<0.162.0" in lines
    assert "sqlalchemy[asyncio]>=2.1.6" in lines
    assert "aiosqlite>=0.22.1" in lines
    assert "asyncpg>=0.32.0" in lines
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
