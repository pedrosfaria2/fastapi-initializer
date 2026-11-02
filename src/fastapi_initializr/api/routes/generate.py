"""Project preview and generation endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import ValidationError

from fastapi_initializr.api.params import split_dependencies
from fastapi_initializr.generation.constants import DEFAULT_PYTHON_VERSION
from fastapi_initializr.generation.preview import build_preview
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.requirements import render_requirements
from fastapi_initializr.generation.spec import ProjectSpec
from fastapi_initializr.schemas.preview import Preview
from fastapi_initializr.services.generator import (
    GeneratedProject,
    generate_project,
    generate_tar_project,
)

router = APIRouter(tags=["generate"])


def _build_spec(
    *,
    name: str,
    package: str | None,
    description: str,
    version: str,
    author: str,
    python: str,
    preset: str,
    base_dir: str | None,
    application_name: str | None,
    dependencies: list[str] | None,
) -> ProjectSpec:
    try:
        return ProjectSpec(
            name=name,
            package=package or None,
            description=description,
            version=version,
            author=author,
            python=python,
            preset=preset,
            base_dir=base_dir,
            application_name=application_name,
            dependencies=split_dependencies(dependencies),
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


def query_spec(
    name: Annotated[str, Query()] = "my-service",
    package: Annotated[str | None, Query()] = None,
    description: Annotated[str, Query()] = "A FastAPI service",
    version: Annotated[str, Query()] = "0.1.0",
    author: Annotated[str, Query()] = "",
    python: Annotated[str, Query()] = DEFAULT_PYTHON_VERSION,
    python_version: Annotated[str | None, Query(alias="pythonVersion")] = None,
    preset: Annotated[str, Query()] = "custom",
    base_dir: Annotated[str | None, Query(alias="baseDir")] = None,
    application_name: Annotated[str | None, Query(alias="applicationName")] = None,
    dependencies: Annotated[list[str] | None, Query()] = None,
) -> ProjectSpec:
    """Build a validated project spec from query parameters."""
    return _build_spec(
        name=name,
        package=package,
        description=description,
        version=version,
        author=author,
        python=python_version or python,
        preset=preset,
        base_dir=base_dir,
        application_name=application_name,
        dependencies=dependencies,
    )


SpecDep = Annotated[ProjectSpec, Depends(query_spec)]


def _archive_response(project: GeneratedProject) -> Response:
    return Response(
        content=project.content,
        media_type="application/zip" if project.filename.endswith(".zip") else "application/gzip",
        headers={
            "Content-Disposition": f'attachment; filename="{project.filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


def _pyproject_response(spec: ProjectSpec) -> Response:
    content = render_project(spec)["pyproject.toml"]
    return Response(
        content=content,
        media_type="application/toml",
        headers={"X-Content-Type-Options": "nosniff"},
    )


def _requirements_response(spec: ProjectSpec) -> Response:
    return Response(
        content=render_requirements(spec),
        media_type="text/plain",
        headers={
            "Content-Disposition": 'attachment; filename="requirements.txt"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/api/preview", response_model=Preview)
def preview_get(spec: SpecDep) -> Preview:
    """Preview the files for a query-string project spec."""
    return build_preview(spec)


@router.post("/api/preview", response_model=Preview)
def preview_post(spec: ProjectSpec) -> Preview:
    """Preview the files for a JSON project spec."""
    return build_preview(spec)


@router.get("/api/generate")
def generate_get(spec: SpecDep) -> Response:
    """Generate a zip from a query-string project spec."""
    return _archive_response(generate_project(spec))


@router.post("/api/generate")
def generate_post(spec: ProjectSpec) -> Response:
    """Generate a zip from a JSON project spec."""
    return _archive_response(generate_project(spec))


@router.get("/preview", response_model=Preview, include_in_schema=False)
def preview_alias(spec: SpecDep) -> Preview:
    """Spring-style preview alias."""
    return build_preview(spec)


@router.post("/preview", response_model=Preview, include_in_schema=False)
def preview_alias_post(spec: ProjectSpec) -> Preview:
    """Spring-style preview alias for JSON bodies."""
    return build_preview(spec)


@router.get("/starter.zip", include_in_schema=False)
def starter_zip(spec: SpecDep) -> Response:
    """Spring-style zip generation alias."""
    return _archive_response(generate_project(spec))


@router.post("/starter.zip", include_in_schema=False)
def starter_zip_post(spec: ProjectSpec) -> Response:
    """Spring-style zip generation alias for JSON bodies."""
    return _archive_response(generate_project(spec))


@router.get("/starter.tgz", include_in_schema=False)
def starter_tgz(spec: SpecDep) -> Response:
    """Generate a tar.gz archive."""
    return _archive_response(generate_tar_project(spec))


@router.post("/starter.tgz", include_in_schema=False)
def starter_tgz_post(spec: ProjectSpec) -> Response:
    """Generate a tar.gz archive from a JSON body."""
    return _archive_response(generate_tar_project(spec))


@router.get("/pyproject.toml", include_in_schema=False)
def pyproject_toml(spec: SpecDep) -> Response:
    """Return only the generated pyproject.toml."""
    return _pyproject_response(spec)


@router.post("/pyproject.toml", include_in_schema=False)
def pyproject_toml_post(spec: ProjectSpec) -> Response:
    """Return only the generated pyproject.toml from a JSON body."""
    return _pyproject_response(spec)


@router.get("/requirements.txt", include_in_schema=False)
def requirements_txt(spec: SpecDep) -> Response:
    """Return runtime requirements for the selected options."""
    return _requirements_response(spec)


@router.post("/requirements.txt", include_in_schema=False)
def requirements_txt_post(spec: ProjectSpec) -> Response:
    """Return runtime requirements from a JSON body."""
    return _requirements_response(spec)
