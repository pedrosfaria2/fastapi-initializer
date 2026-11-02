"""Option catalog endpoints."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from fastapi_initializr.generation.catalog import dependency_catalog, metadata
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
def get_dependencies() -> dict[str, object]:
    """Return package names and files for every catalog feature."""
    return dependency_catalog()
