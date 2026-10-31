"""Pip requirements rendering from the same package specs as pyproject.toml."""

from fastapi_initializr.generation.catalog import resolve_packages
from fastapi_initializr.generation.constants import core_packages
from fastapi_initializr.generation.spec import ProjectSpec


def render_requirements(spec: ProjectSpec) -> str:
    """Return runtime requirements in pip's requirements file format."""
    packages, _ = resolve_packages(spec.dependencies)
    lines = sorted({*core_packages(spec.fastapi_range), *packages})
    return "\n".join(lines) + "\n"
