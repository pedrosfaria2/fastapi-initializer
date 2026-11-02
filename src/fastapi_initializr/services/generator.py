"""Generation service used by the HTTP layer."""

from dataclasses import dataclass

from fastapi_initializr.core.config import get_settings
from fastapi_initializr.generation.archive import (
    archive_filename,
    build_tar_gz,
    build_zip,
    tar_filename,
)
from fastapi_initializr.generation.limits import ProjectLimitError
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec


@dataclass(frozen=True, slots=True)
class GeneratedProject:
    """A generated archive ready to download."""

    filename: str
    content: bytes


def _rendered_files(spec: ProjectSpec) -> dict[str, str]:
    files = render_project(spec)
    if len(files) > get_settings().max_generated_files:
        raise ProjectLimitError("Generated project exceeds the file limit.")
    return files


def generate_project(spec: ProjectSpec) -> GeneratedProject:
    """Render and archive a project within the configured size limits."""
    files = _rendered_files(spec)
    content = build_zip(files, root=spec.archive_root)
    if len(content) > get_settings().max_zip_bytes:
        raise ProjectLimitError("Generated project exceeds the archive size limit.")
    return GeneratedProject(filename=archive_filename(spec.name), content=content)


def generate_tar_project(spec: ProjectSpec) -> GeneratedProject:
    """Render and archive a project as tar.gz."""
    files = _rendered_files(spec)
    content = build_tar_gz(files, root=spec.archive_root)
    if len(content) > get_settings().max_zip_bytes:
        raise ProjectLimitError("Generated project exceeds the archive size limit.")
    return GeneratedProject(filename=tar_filename(spec.name), content=content)
