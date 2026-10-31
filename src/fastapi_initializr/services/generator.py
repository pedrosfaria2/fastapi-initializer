"""Generation service used by the HTTP layer."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi_initializr.core.config import get_settings
from fastapi_initializr.generation.archive import archive_filename, build_zip
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec


@dataclass(frozen=True, slots=True)
class GeneratedProject:
    """A generated archive ready to download."""

    filename: str
    content: bytes


def generate_project(spec: ProjectSpec) -> GeneratedProject:
    """Render and archive a project within the configured size limits."""
    files = render_project(spec)
    settings = get_settings()
    if len(files) > settings.max_generated_files:
        raise ValueError("Generated project exceeds the file limit.")

    content = build_zip(files, root=spec.name)
    if len(content) > settings.max_zip_bytes:
        raise ValueError("Generated project exceeds the archive size limit.")

    return GeneratedProject(filename=archive_filename(spec.name), content=content)
