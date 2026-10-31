"""HTTP API contract."""

import io
from zipfile import ZipFile

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_metadata_returns_catalog(client: TestClient) -> None:
    response = client.get("/api/metadata")

    assert response.status_code == 200
    body = response.json()
    assert body["project"]["name"]["default"] == "my-service"
    assert body["python"]["default"] == "3.13"
    groups = body["dependencies"]["groups"]
    ids = [value["id"] for group in groups for value in group["values"]]
    assert "sqlalchemy" in ids
    assert "docker" in ids


def test_preview_returns_rendered_files(client: TestClient) -> None:
    response = client.get("/api/preview", params={"name": "my-service"})

    assert response.status_code == 200
    body = response.json()
    paths = [file["path"] for file in body["files"]]
    assert body["name"] == "my-service"
    assert "pyproject.toml" in paths
    assert "src/my_service/main.py" in paths


def test_preview_rejects_invalid_input(client: TestClient) -> None:
    response = client.get("/api/preview", params={"name": "Bad Name"})

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_generate_returns_zip(client: TestClient) -> None:
    response = client.get("/api/generate", params={"name": "my-service"})

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert 'filename="my-service.zip"' in response.headers["content-disposition"]
    assert response.headers["x-content-type-options"] == "nosniff"

    with ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert "my-service/pyproject.toml" in names
        assert "my-service/src/my_service/main.py" in names
        assert "my-service/README.md" in names


def test_generate_includes_selected_dependencies(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={
            "name": "my-service",
            "dependencies": ["sqlalchemy", "alembic", "docker"],
        },
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert "my-service/alembic.ini" in names
        assert "my-service/Dockerfile" in names
        assert "my-service/src/my_service/db/session.py" in names


def test_generate_rejects_unknown_dependency(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "dependencies": ["unknown"]},
    )

    assert response.status_code == 422
    assert "Unknown dependencies" in str(response.json())


def test_post_generate_accepts_json(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        json={
            "name": "my-service",
            "dependencies": ["cors"],
        },
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert "my-service/.env.example" in names


def test_index_renders_a_working_form(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "<form" in response.text
    assert 'action="/api/generate"' in response.text
    assert 'name="name"' in response.text
    assert 'id="dependency-groups"' in response.text
