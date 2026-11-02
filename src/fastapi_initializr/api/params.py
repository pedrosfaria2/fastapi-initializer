"""Shared request parameter parsing."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from pydantic import ValidationError
from starlette.datastructures import FormData

from fastapi_initializr.generation.constants import DEFAULT_PYTHON_VERSION
from fastapi_initializr.generation.spec import ProjectSpec


def split_dependencies(values: list[str] | None) -> frozenset[str]:
    """Split repeated or comma-separated dependency query values."""
    if not values:
        return frozenset()
    dependencies: list[str] = []
    for value in values:
        dependencies.extend(part.strip() for part in value.split(",") if part.strip())
    return frozenset(dependencies)


def _validation_error(exc: ValidationError) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail=exc.errors(
            include_url=False,
            include_context=False,
            include_input=False,
        ),
    )


def build_spec(
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
    """Build and validate a project spec from request values."""
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
        raise _validation_error(exc) from exc


def _form_value(form: FormData, key: str, default: str = "") -> str:
    value: Any = form.get(key)
    return value if isinstance(value, str) else default


def _spec_from_form(form: FormData) -> ProjectSpec:
    dependencies = [value for value in form.getlist("dependencies") if isinstance(value, str)]
    return build_spec(
        name=_form_value(form, "name", "my-service"),
        package=_form_value(form, "package") or None,
        description=_form_value(form, "description", "A FastAPI service"),
        version=_form_value(form, "version", "0.1.0"),
        author=_form_value(form, "author"),
        python=(
            _form_value(form, "python")
            or _form_value(form, "pythonVersion")
            or DEFAULT_PYTHON_VERSION
        ),
        preset=_form_value(form, "preset", "custom"),
        base_dir=_form_value(form, "baseDir") or _form_value(form, "base_dir") or None,
        application_name=(
            _form_value(form, "applicationName") or _form_value(form, "application_name") or None
        ),
        dependencies=dependencies,
    )


async def spec_from_request(request: Request) -> ProjectSpec:
    """Build a spec from a JSON or form-encoded request body."""
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type == "application/json":
        try:
            payload: object = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid JSON body.") from exc
        try:
            return ProjectSpec.model_validate(payload)
        except ValidationError as exc:
            raise _validation_error(exc) from exc
    if content_type in {"application/x-www-form-urlencoded", "multipart/form-data"}:
        return _spec_from_form(await request.form())
    raise HTTPException(
        status_code=415,
        detail="Use application/json or form data.",
    )
