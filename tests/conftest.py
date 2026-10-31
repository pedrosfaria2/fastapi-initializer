"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from fastapi_initializr.generation.plugins import reset_plugins
from fastapi_initializr.main import create_app


@pytest.fixture(autouse=True)
def _clear_plugin_registry() -> None:
    reset_plugins()


@pytest.fixture
def client() -> TestClient:
    """Return a client bound to a fresh application."""
    return TestClient(create_app())
