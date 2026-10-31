"""Generation service used by the HTTP layer."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi_initializr.generation.archive import archive_filename, build_zip
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec


@dataclass(frozen=True, slots=True)
class GeneratedProject:
    """A generated archive ready to download."""

    filename: str
    content: bytes


def generate_project(spec: ProjectSpec) -> GeneratedProject:
    """Render and archive a project."""
    files = render_project(spec)
    return GeneratedProject(
        filename=archive_filename(spec.name),
        content=build_zip(files, root=spec.name),
    )
