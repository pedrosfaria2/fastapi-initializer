"""Shared request parameter parsing."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from fastapi import HTTPException, Request
from pydantic import ValidationError
from starlette.datastructures import FormData

from fastapi_initializr.generation.constants import DEFAULT_PYTHON_VERSION
from fastapi_initializr.generation.spec import ProjectSpec

ALLOWED_KEYS = frozenset(
    {
        "name",
        "package",
        "description",
        "version",
        "author",
        "python",
        "pythonVersion",
        "preset",
        "baseDir",
        "base_dir",
        "applicationName",
        "application_name",
        "dependencies",
    }
)


def reject_unknown_keys(keys: Iterable[str]) -> None:
    """Reject query or form fields that are not part of the contract."""
    unknown = sorted(set(keys) - ALLOWED_KEYS)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown fields: {', '.join(unknown)}.",
        )


def resolve_python(python: str | None, python_version: str | None) -> str:
    """Resolve the python/pythonVersion aliases consistently."""
    if python and python_version and python != python_version:
        raise HTTPException(
            status_code=422,
            detail="Use either python or pythonVersion, not both with different values.",
        )
    return python_version or python or DEFAULT_PYTHON_VERSION


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
    if value is None:
        return default
    if not isinstance(value, str):
        raise HTTPException(
            status_code=422,
            detail=f"Field '{key}' must be a string.",
        )
    return value


def _spec_from_form(form: FormData) -> ProjectSpec:
    reject_unknown_keys(form.keys())
    dependencies: list[str] = []
    for value in form.getlist("dependencies"):
        if not isinstance(value, str):
            raise HTTPException(
                status_code=422,
                detail="Field 'dependencies' must be a string.",
            )
        dependencies.append(value)
    python = _form_value(form, "python") or None
    python_version = _form_value(form, "pythonVersion") or None
    return build_spec(
        name=_form_value(form, "name", "my-service"),
        package=_form_value(form, "package") or None,
        description=_form_value(form, "description", "A FastAPI service"),
        version=_form_value(form, "version", "0.1.0"),
        author=_form_value(form, "author"),
        python=resolve_python(python, python_version),
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
