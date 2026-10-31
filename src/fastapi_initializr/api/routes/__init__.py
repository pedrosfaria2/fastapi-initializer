"""API route registration."""

from fastapi import APIRouter

from fastapi_initializr.api.routes import generate, health, metadata

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(metadata.router)
api_router.include_router(generate.router)
