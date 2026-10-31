"""Liveness endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    """Return service liveness."""
    return {"status": "ok"}


@router.get("/ready")
def ready() -> dict[str, str]:
    """Return service readiness."""
    return {"status": "ready"}
