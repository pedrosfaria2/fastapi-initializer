"""Project preview and generation endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import ValidationError

from fastapi_initializr.generation.constants import DEFAULT_PYTHON_VERSION
from fastapi_initializr.generation.preview import build_preview
from fastapi_initializr.generation.spec import ProjectSpec
from fastapi_initializr.schemas.preview import Preview
from fastapi_initializr.services.generator import GeneratedProject, generate_project

router = APIRouter(prefix="/api", tags=["generate"])


def _split_dependencies(values: list[str] | None) -> frozenset[str]:
    if not values:
        return frozenset()
    dependencies: list[str] = []
    for value in values:
        dependencies.extend(part.strip() for part in value.split(",") if part.strip())
    return frozenset(dependencies)


def _build_spec(
    *,
    name: str,
    package: str | None,
    description: str,
    python: str,
    dependencies: list[str] | None,
) -> ProjectSpec:
    try:
        return ProjectSpec(
            name=name,
            package=package or None,
            description=description,
            python=python,
            dependencies=_split_dependencies(dependencies),
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=exc.errors(
                include_url=False,
                include_context=False,
                include_input=False,
            ),
        ) from exc


def _archive_response(project: GeneratedProject) -> Response:
    return Response(
        content=project.content,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{project.filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/preview", response_model=Preview)
def preview_get(
    name: Annotated[str, Query()] = "my-service",
    package: Annotated[str | None, Query()] = None,
    description: Annotated[str, Query()] = "A FastAPI service",
    python: Annotated[str, Query()] = DEFAULT_PYTHON_VERSION,
    dependencies: Annotated[list[str] | None, Query()] = None,
) -> Preview:
    """Preview the files for a query-string project spec."""
    spec = _build_spec(
        name=name,
        package=package,
        description=description,
        python=python,
        dependencies=dependencies,
    )
    return build_preview(spec)


@router.post("/preview", response_model=Preview)
def preview_post(spec: ProjectSpec) -> Preview:
    """Preview the files for a JSON project spec."""
    return build_preview(spec)


@router.get("/generate")
def generate_get(
    name: Annotated[str, Query()] = "my-service",
    package: Annotated[str | None, Query()] = None,
    description: Annotated[str, Query()] = "A FastAPI service",
    python: Annotated[str, Query()] = DEFAULT_PYTHON_VERSION,
    dependencies: Annotated[list[str] | None, Query()] = None,
) -> Response:
    """Generate a zip from a query-string project spec."""
    spec = _build_spec(
        name=name,
        package=package,
        description=description,
        python=python,
        dependencies=dependencies,
    )
    return _archive_response(generate_project(spec))


@router.post("/generate")
def generate_post(spec: ProjectSpec) -> Response:
    """Generate a zip from a JSON project spec."""
    return _archive_response(generate_project(spec))
