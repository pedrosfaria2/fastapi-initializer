"""Template rendering and preview behavior."""

import ast
import tomllib

from fastapi_initializr.generation.preview import build_preview
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec


def test_minimal_project_contains_core_files() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "pyproject.toml" in files
    assert "README.md" in files
    assert ".gitignore" in files
    assert ".python-version" in files
    assert "src/my_service/main.py" in files
    assert "src/my_service/api/routes/health.py" in files
    assert "tests/test_health.py" in files
    assert "Dockerfile" not in files
    assert "alembic.ini" not in files
    assert ".env.example" not in files


def test_all_features_include_conditional_files() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset(
            {"sqlalchemy", "alembic", "postgres", "cors", "docker", "ci", "pre-commit"}
        ),
    )

    files = render_project(spec)

    assert "Dockerfile" in files
    assert ".dockerignore" in files
    assert ".github/workflows/ci.yml" in files
    assert ".pre-commit-config.yaml" in files
    assert "alembic.ini" in files
    assert "migrations/env.py" in files
    assert "migrations/versions/.gitkeep" in files
    assert "src/my_service/db/session.py" in files
    assert ".env.example" in files


def test_pyproject_parses_and_contains_selected_packages() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "alembic", "postgres"}),
    )

    files = render_project(spec)
    data = tomllib.loads(files["pyproject.toml"])

    assert data["project"]["name"] == "my-service"
    assert data["project"]["requires-python"] == ">=3.13"
    dependencies = data["project"]["dependencies"]
    assert any(dependency.startswith("fastapi") for dependency in dependencies)
    assert any(dependency.startswith("sqlalchemy") for dependency in dependencies)
    assert any(dependency.startswith("alembic") for dependency in dependencies)
    assert any(dependency.startswith("asyncpg") for dependency in dependencies)
    dev_dependencies = data["dependency-groups"]["dev"]
    assert any(dependency.startswith("pytest") for dependency in dev_dependencies)
    assert any(dependency.startswith("mypy") for dependency in dev_dependencies)
    assert any(dependency.startswith("pyright") for dependency in dev_dependencies)
    assert data["tool"]["ruff"]["target-version"] == "py313"
    assert data["tool"]["mypy"]["strict"] is True
    assert data["tool"]["pyright"]["typeCheckingMode"] == "strict"


def test_generated_python_parses() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "alembic", "postgres", "cors"}),
    )

    for path, content in render_project(spec).items():
        if path.endswith(".py"):
            ast.parse(content, filename=path)


def test_no_unresolved_template_markers() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "alembic", "docker", "ci"}),
    )

    for path, content in render_project(spec).items():
        assert "{{" not in content, path
        assert "{%" not in content, path
        assert "{#" not in content, path


def test_render_is_deterministic() -> None:
    spec = ProjectSpec(name="my-service", dependencies=frozenset({"sqlalchemy"}))

    assert render_project(spec) == render_project(spec)


def test_explicit_package_is_used_in_paths() -> None:
    files = render_project(ProjectSpec(name="my-service", package="custom"))

    assert "src/custom/main.py" in files
    assert "src/my_service/main.py" not in files


def test_python_version_changes_requires_python_and_ruff_target() -> None:
    files = render_project(ProjectSpec(name="my-service", python="3.11"))
    data = tomllib.loads(files["pyproject.toml"])

    assert data["project"]["requires-python"] == ">=3.11"
    assert data["tool"]["ruff"]["target-version"] == "py311"


def test_preview_lists_rendered_files() -> None:
    preview = build_preview(ProjectSpec(name="my-service"))

    assert preview.name == "my-service"
    assert any(file.path == "pyproject.toml" for file in preview.files)
    assert all(file.size > 0 for file in preview.files)
