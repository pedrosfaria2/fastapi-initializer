"""Render generated project files from templates."""

from __future__ import annotations

import ast
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from fastapi_initializr.generation.catalog import resolve_packages
from fastapi_initializr.generation.spec import ProjectSpec

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "project"

_ENVIRONMENT = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    undefined=StrictUndefined,
    autoescape=False,  # noqa: S701 - code/TOML/YAML templates, never HTML
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)

_PATH_ENVIRONMENT = Environment(
    undefined=StrictUndefined,
    autoescape=False,  # noqa: S701 - renders relative paths only
    keep_trailing_newline=True,
)


@dataclass(frozen=True, slots=True)
class FileSpec:
    """A template and its destination."""

    template: str
    output: str
    condition: Callable[[ProjectSpec], bool] = lambda _: True


def _has(feature: str) -> Callable[[ProjectSpec], bool]:
    return lambda spec: spec.has(feature)


def _has_database(spec: ProjectSpec) -> bool:
    return spec.has_database


FILES: tuple[FileSpec, ...] = (
    FileSpec("pyproject.toml.j2", "pyproject.toml"),
    FileSpec("README.md.j2", "README.md"),
    FileSpec("gitignore.j2", ".gitignore"),
    FileSpec("python-version.j2", ".python-version"),
    FileSpec("env.example.j2", ".env.example", lambda spec: spec.has_environment),
    FileSpec("Dockerfile.j2", "Dockerfile", _has("docker")),
    FileSpec("dockerignore.j2", ".dockerignore", _has("docker")),
    FileSpec("ci.yml.j2", ".github/workflows/ci.yml", _has("ci")),
    FileSpec(
        "pre-commit-config.yaml.j2",
        ".pre-commit-config.yaml",
        _has("pre-commit"),
    ),
    FileSpec("alembic.ini.j2", "alembic.ini", _has("alembic")),
    FileSpec("migrations/env.py.j2", "migrations/env.py", _has("alembic")),
    FileSpec(
        "migrations/script.py.mako.j2",
        "migrations/script.py.mako",
        _has("alembic"),
    ),
    FileSpec(
        "migrations/versions/gitkeep.j2",
        "migrations/versions/.gitkeep",
        _has("alembic"),
    ),
    FileSpec("src/__init__.py.j2", "src/{{ spec.package }}/__init__.py"),
    FileSpec("src/main.py.j2", "src/{{ spec.package }}/main.py"),
    FileSpec("src/api/__init__.py.j2", "src/{{ spec.package }}/api/__init__.py"),
    FileSpec(
        "src/api/dependencies.py.j2",
        "src/{{ spec.package }}/api/dependencies.py",
    ),
    FileSpec(
        "src/api/routes/__init__.py.j2",
        "src/{{ spec.package }}/api/routes/__init__.py",
    ),
    FileSpec(
        "src/api/routes/health.py.j2",
        "src/{{ spec.package }}/api/routes/health.py",
    ),
    FileSpec("src/core/__init__.py.j2", "src/{{ spec.package }}/core/__init__.py"),
    FileSpec("src/core/config.py.j2", "src/{{ spec.package }}/core/config.py"),
    FileSpec(
        "src/db/__init__.py.j2",
        "src/{{ spec.package }}/db/__init__.py",
        _has_database,
    ),
    FileSpec(
        "src/db/base.py.j2",
        "src/{{ spec.package }}/db/base.py",
        _has_database,
    ),
    FileSpec(
        "src/db/session.py.j2",
        "src/{{ spec.package }}/db/session.py",
        _has_database,
    ),
    FileSpec(
        "src/schemas/__init__.py.j2",
        "src/{{ spec.package }}/schemas/__init__.py",
    ),
    FileSpec(
        "src/services/__init__.py.j2",
        "src/{{ spec.package }}/services/__init__.py",
    ),
    FileSpec("tests/conftest.py.j2", "tests/conftest.py"),
    FileSpec("tests/test_health.py.j2", "tests/test_health.py"),
)


def build_context(spec: ProjectSpec) -> dict[str, object]:
    """Build the template context for a project spec."""
    packages, dev_packages = resolve_packages(spec.dependencies)
    return {
        "spec": spec,
        "packages": packages,
        "dev_packages": dev_packages,
        "fastapi_version": spec.fastapi,
        "fastapi_range": spec.fastapi_range,
        "project_version": spec.version,
        "author": spec.author,
        "app_title": spec.app_title,
        "base_dir": spec.archive_root,
        "uvicorn_version": "0.54.0",
        "pydantic_settings_version": "2.16.2",
        "jinja2_version": "3.1.6",
        "python_multipart_version": "0.0.32",
        "pytest_version": "9.2.0",
        "httpx2_version": "2.16.0",
        "ruff_version": "0.17.3",
        "mypy_version": "2.4.1",
        "pyright_version": "1.1.414",
        "uv_build_version": "0.13.6",
    }


def _validate_output_path(path: str) -> str:
    if not path or "\x00" in path or "\\" in path:
        raise ValueError(f"Invalid output path: {path!r}")
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or pure.name in {"", "."}:
        raise ValueError(f"Invalid output path: {path!r}")
    return pure.as_posix()


def _validate_content(path: str, content: str) -> None:
    if any(marker in content for marker in ("{{", "{%", "{#")):
        raise ValueError(f"Unresolved template marker in {path}")
    if path.endswith(".py"):
        ast.parse(content, filename=path)
    elif path == "pyproject.toml":
        tomllib.loads(content)


def render_project(spec: ProjectSpec) -> dict[str, str]:
    """Render every selected file for a project spec."""
    context = build_context(spec)
    rendered: dict[str, str] = {}
    for file_spec in FILES:
        if not file_spec.condition(spec):
            continue
        output = _PATH_ENVIRONMENT.from_string(file_spec.output).render(context)
        output = _validate_output_path(output)
        if output in rendered:
            raise ValueError(f"Duplicate output path: {output}")
        template = _ENVIRONMENT.get_template(file_spec.template)
        content = template.render(context)
        _validate_content(output, content)
        rendered[output] = content
    return dict(sorted(rendered.items()))
