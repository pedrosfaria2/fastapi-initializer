"""Build previews from rendered project files."""

from fastapi_initializr.core.config import get_settings
from fastapi_initializr.generation.highlight import highlight_file
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec
from fastapi_initializr.schemas.preview import Preview, PreviewFile


def _preview_file(path: str, content: str) -> PreviewFile:
    highlighted = highlight_file(path, content)
    return PreviewFile(
        path=path,
        content=content,
        size=len(content.encode("utf-8")),
        language=highlighted.language,
        highlighted=highlighted.html,
    )


def build_preview(spec: ProjectSpec) -> Preview:
    """Render a project and return its files for inspection."""
    files = render_project(spec)
    if len(files) > get_settings().max_generated_files:
        raise ValueError("Generated project exceeds the file limit.")

    return Preview(
        name=spec.name,
        files=[_preview_file(path, content) for path, content in files.items()],
    )
