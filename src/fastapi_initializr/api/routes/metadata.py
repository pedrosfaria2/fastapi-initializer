"""Option catalog endpoints."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from fastapi_initializr.generation.catalog import metadata, resolved_dependencies
from fastapi_initializr.generation.constants import (
    DEFAULT_FASTAPI_VERSION,
    SUPPORTED_FASTAPI_VERSIONS,
)
from fastapi_initializr.schemas.metadata import Metadata

router = APIRouter(tags=["metadata"])

MEDIA_TYPE = "application/vnd.fastapi-initializr.v1+json"


@router.get("/api/metadata", response_model=Metadata)
def get_metadata() -> Metadata:
    """Return the option catalog used by the UI and API clients."""
    return metadata()


@router.get("/metadata", include_in_schema=False)
def get_metadata_alias(request: Request) -> JSONResponse:
    """Return the capability document with an optional versioned media type."""
    accept = request.headers.get("accept", "")
    media_type = MEDIA_TYPE if MEDIA_TYPE in accept else "application/json"
    return JSONResponse(
        content=metadata().model_dump(by_alias=True),
        media_type=media_type,
    )


@router.get("/dependencies")
def get_dependencies(
    fastapi_version: Annotated[str, Query(alias="fastapiVersion")] = DEFAULT_FASTAPI_VERSION,
) -> dict[str, object]:
    """Return resolved dependency coordinates for a FastAPI version."""
    if fastapi_version not in SUPPORTED_FASTAPI_VERSIONS:
        allowed = ", ".join(SUPPORTED_FASTAPI_VERSIONS)
        raise HTTPException(
            status_code=400,
            detail=f"Unknown FastAPI version '{fastapi_version}'. Use one of: {allowed}.",
        )
    return resolved_dependencies(fastapi_version)
