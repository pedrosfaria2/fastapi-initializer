"""Build previews from rendered project files."""

from fastapi_initializr.core.config import get_settings
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec
from fastapi_initializr.schemas.preview import Preview, PreviewFile


def build_preview(spec: ProjectSpec) -> Preview:
    """Render a project and return its files for inspection."""
    files = render_project(spec)
    if len(files) > get_settings().max_generated_files:
        raise ValueError("Generated project exceeds the file limit.")

    return Preview(
        name=spec.name,
        files=[
            PreviewFile(path=path, content=content, size=len(content.encode("utf-8")))
            for path, content in files.items()
        ],
    )
