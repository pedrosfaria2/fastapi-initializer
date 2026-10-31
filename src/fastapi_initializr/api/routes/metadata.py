"""Option catalog endpoint."""

from fastapi import APIRouter

from fastapi_initializr.generation.catalog import metadata
from fastapi_initializr.schemas.metadata import Metadata

router = APIRouter(prefix="/api", tags=["metadata"])


@router.get("/metadata", response_model=Metadata)
def get_metadata() -> Metadata:
    """Return the option catalog used by the UI and API clients."""
    return metadata()
