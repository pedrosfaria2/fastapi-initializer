"""Security boundaries for generation requests."""

import io
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient


@pytest.mark.parametrize("base_dir", ["../evil", "a/b", "a\\b"])
def test_generate_rejects_unsafe_base_dir(client: TestClient, base_dir: str) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "baseDir": base_dir},
    )

    assert response.status_code == 422


@pytest.mark.parametrize("name", ["../evil", "a/b", "a\\b", ".hidden"])
def test_generate_rejects_path_like_names(client: TestClient, name: str) -> None:
    response = client.get("/api/generate", params={"name": name})

    assert response.status_code == 422


def test_generate_rejects_unknown_dependency(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "dependencies": ["unknown"]},
    )

    assert response.status_code == 422


def test_generate_rejects_control_characters(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "description": "bad\x00description"},
    )

    assert response.status_code == 422


def test_zip_entries_stay_under_the_archive_root(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "baseDir": "safe-root"},
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        for name in archive.namelist():
            assert name.startswith("safe-root/")
            assert ".." not in name.split("/")
            assert not name.startswith("/")
