"""HTTP API contract."""

import io
import tarfile
from zipfile import ZipFile

from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready(client: TestClient) -> None:
    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


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
    main_file = next(file for file in body["files"] if file["path"] == "src/my_service/main.py")
    assert main_file["language"] == "Python"
    assert "<span" in main_file["highlighted"]


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


def test_index_server_renders_options_without_javascript(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Python 3.11" in response.text
    assert "FastAPI 0.162.0" in response.text
    assert "SQLAlchemy" in response.text
    assert 'name="dependencies"' in response.text
    assert 'name="version"' in response.text
    assert 'name="author"' in response.text
    assert 'name="baseDir"' in response.text
    assert 'name="applicationName"' in response.text
    assert 'id="dependency-search"' in response.text
    assert 'id="selected-count"' in response.text
    assert 'id="share"' in response.text
    assert 'id="reset"' in response.text
    assert 'id="output"' in response.text
    assert 'id="fastapi"' in response.text


def test_metadata_supports_versioned_media_type(client: TestClient) -> None:
    response = client.get(
        "/metadata",
        headers={"Accept": "application/vnd.fastapi-initializr.v1+json"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.fastapi-initializr.v1+json")
    body = response.json()
    assert "starter.zip" in body["links"]
    assert body["type"]["default"] == "uv-project"
    assert body["fastapi"]["default"] == "0.162.0"


def test_metadata_defaults_to_json(client: TestClient) -> None:
    response = client.get("/metadata")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_dependencies_returns_resolved_coordinates(client: TestClient) -> None:
    response = client.get("/dependencies", params={"fastapiVersion": "0.161.1"})

    assert response.status_code == 200
    body = response.json()
    assert body["fastapiVersion"] == "0.161.1"
    assert body["dependencies"]["sqlalchemy"]["packages"]


def test_dependencies_rejects_unknown_fastapi_version(client: TestClient) -> None:
    response = client.get("/dependencies", params={"fastapiVersion": "0.100.0"})

    assert response.status_code == 400
    assert "Unknown FastAPI version" in response.json()["detail"]


def test_starter_zip_alias(client: TestClient) -> None:
    response = client.get("/starter.zip", params={"name": "my-service"})

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        assert "my-service/pyproject.toml" in archive.namelist()


def test_starter_tgz_returns_tar_gz(client: TestClient) -> None:
    response = client.get("/starter.tgz", params={"name": "my-service"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/gzip")
    with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as archive:
        assert "my-service/pyproject.toml" in archive.getnames()


def test_pyproject_output(client: TestClient) -> None:
    response = client.get(
        "/pyproject.toml",
        params={"name": "my-service", "fastapiVersion": "0.161.1"},
    )

    assert response.status_code == 200
    assert 'name = "my-service"' in response.text
    assert "fastapi>=0.161.1,<0.162.0" in response.text


def test_generate_uses_base_dir_version_author_and_fastapi_version(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/generate",
        params={
            "name": "my-service",
            "version": "1.2.3",
            "author": "Ada Lovelace",
            "fastapiVersion": "0.161.1",
            "baseDir": "custom-root",
        },
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert "custom-root/pyproject.toml" in names
        pyproject = archive.read("custom-root/pyproject.toml").decode()
        assert 'version = "1.2.3"' in pyproject
        assert 'name = "Ada Lovelace"' in pyproject
        assert "fastapi>=0.161.1,<0.162.0" in pyproject


def test_generate_rejects_unknown_fastapi_version(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "fastapi": "0.100.0"},
    )

    assert response.status_code == 422
    assert "FastAPI version" in str(response.json())


def test_generate_rejects_unsafe_base_dir(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "baseDir": "../evil"},
    )

    assert response.status_code == 422
    assert "baseDir" in str(response.json())


def test_generate_uses_application_name(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "applicationName": "My Public API"},
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        config = archive.read("my-service/src/my_service/core/config.py").decode()
        assert 'app_name: str = "My Public API"' in config
