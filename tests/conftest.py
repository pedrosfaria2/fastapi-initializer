"""Shared test fixtures."""

import pytest
from fastapi.testclient import TestClient

from fastapi_initializr.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Return a client bound to a fresh application."""
    return TestClient(create_app())
