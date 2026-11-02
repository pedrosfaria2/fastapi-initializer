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


def test_metadata_exposes_presets(client: TestClient) -> None:
    response = client.get("/api/metadata")

    assert response.status_code == 200
    presets = response.json()["preset"]
    assert presets["default"] == "custom"
    assert [value["id"] for value in presets["values"]] == [
        "custom",
        "api",
        "db-auth",
        "worker",
        "full",
    ]
    full = next(value for value in presets["values"] if value["id"] == "full")
    assert "sqlalchemy" in full["dependencies"]
    assert "mongodb" not in full["dependencies"]


def test_generate_expands_a_preset(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "preset": "db-auth"},
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert "my-service/alembic.ini" in names
        assert "my-service/src/my_service/api/routes/auth.py" in names


def test_preview_expands_a_preset(client: TestClient) -> None:
    response = client.get(
        "/api/preview",
        params={"name": "my-service", "preset": "worker"},
    )

    assert response.status_code == 200
    paths = [file["path"] for file in response.json()["files"]]
    assert "src/my_service/worker.py" in paths
    assert "src/my_service/core/cache_helpers.py" in paths


def test_generate_rejects_an_unknown_preset(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "preset": "unknown"},
    )

    assert response.status_code == 422
    assert "Preset" in str(response.json())


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


def test_post_generate_accepts_form_data(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        data={
            "name": "my-service",
            "dependencies": ["sqlalchemy", "alembic"],
        },
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert "my-service/pyproject.toml" in names
        assert "my-service/alembic.ini" in names


def test_post_generate_form_keeps_quotes_and_markers(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        data={
            "name": "my-service",
            "applicationName": 'Acme "API"',
            "description": "literal {{x}}",
        },
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        config = archive.read("my-service/src/my_service/core/config.py").decode()
        pyproject = archive.read("my-service/pyproject.toml").decode()
    assert 'app_name: str = "Acme \\"API\\""' in config
    assert "literal {{x}}" in pyproject


def test_post_generate_accepts_camel_case_json(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        json={
            "name": "my-service",
            "baseDir": "custom-root",
            "applicationName": "Acme",
            "pythonVersion": "3.12",
        },
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        assert "custom-root/pyproject.toml" in archive.namelist()
        config = archive.read("custom-root/src/my_service/core/config.py").decode()
        python_version = archive.read("custom-root/.python-version").decode().strip()
    assert 'app_name: str = "Acme"' in config
    assert python_version == "3.12"


def test_post_generate_accepts_snake_case_json(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        json={"name": "my-service", "base_dir": "snake-root"},
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        assert "snake-root/pyproject.toml" in archive.namelist()


def test_get_rejects_unknown_query_fields(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "dependecies": "sqlalchemy"},
    )

    assert response.status_code == 422
    assert "Unknown fields" in str(response.json())


def test_form_rejects_unknown_fields(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        data={"name": "my-service", "dependecies": "sqlalchemy"},
    )

    assert response.status_code == 422
    assert "Unknown fields" in str(response.json())


def test_form_rejects_file_values_for_scalar_fields(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        files={"name": ("name.txt", b"bad", "text/plain")},
    )

    assert response.status_code == 422
    assert "must be a string" in str(response.json())


def test_form_rejects_file_values_for_dependencies(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        files={"dependencies": ("deps.txt", b"sqlalchemy", "text/plain")},
    )

    assert response.status_code == 422
    assert "must be a string" in str(response.json())


def test_get_and_form_reject_conflicting_python_aliases(client: TestClient) -> None:
    query_response = client.get(
        "/api/generate",
        params={"python": "3.11", "pythonVersion": "3.14"},
    )
    form_response = client.post(
        "/api/generate",
        data={"python": "3.11", "pythonVersion": "3.14"},
    )

    assert query_response.status_code == 422
    assert form_response.status_code == 422
    assert "pythonVersion" in str(query_response.json())
    assert "pythonVersion" in str(form_response.json())


def test_post_generate_form_rejects_invalid_input(client: TestClient) -> None:
    response = client.post("/api/generate", data={"name": "Bad Name"})

    assert response.status_code == 422


def test_post_generate_rejects_unsupported_content_type(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        content="name=my-service",
        headers={"content-type": "text/plain"},
    )

    assert response.status_code == 415


def test_post_generate_rejects_invalid_json(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        content="{",
        headers={"content-type": "application/json"},
    )

    assert response.status_code == 422


def test_index_renders_a_working_form(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "<form" in response.text
    assert 'action="/api/generate"' in response.text
    assert 'method="post"' in response.text
    assert 'name="name"' in response.text
    assert 'id="dependency-groups"' in response.text


def test_index_server_renders_options_without_javascript(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Python 3.11" in response.text
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
    assert 'value="requirements"' in response.text
    assert 'id="structure"' in response.text
    assert 'id="preset"' in response.text
    assert 'name="preset"' in response.text


def test_metadata_supports_versioned_media_type(client: TestClient) -> None:
    response = client.get(
        "/metadata",
        headers={"Accept": "application/vnd.fastapi-initializr.v1+json"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.fastapi-initializr.v1+json")
    body = response.json()
    assert "starter.zip" in body["links"]
    assert "requirements.txt" in body["links"]
    assert body["type"]["default"] == "uv-project"
    assert body["structure"]["default"] == "layered"
    assert "fastapi" not in body


def test_metadata_defaults_to_json(client: TestClient) -> None:
    response = client.get("/metadata")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_dependencies_returns_resolved_coordinates(client: TestClient) -> None:
    response = client.get("/dependencies")

    assert response.status_code == 200
    body = response.json()
    assert body["dependencies"]["sqlalchemy"]["packages"] == [
        "sqlalchemy[asyncio]",
        "aiosqlite",
    ]
    assert "fastapiVersion" not in body


def test_generate_accepts_feature_structure(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "structure": "feature", "dependencies": ["sqlalchemy"]},
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
    assert "my-service/src/my_service/features/items/router.py" in names
    assert "my-service/src/my_service/api/routes/items.py" not in names


def test_generate_accepts_minimal_structure(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "structure": "minimal"},
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
    assert "my-service/src/my_service/main.py" in names
    assert "my-service/src/my_service/config.py" in names
    assert "my-service/src/my_service/api/routes/health.py" not in names


def test_minimal_structure_rejects_domain_features(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={"name": "my-service", "structure": "minimal", "dependencies": ["sqlalchemy"]},
    )

    assert response.status_code == 422
    assert "Minimal structure does not support" in str(response.json())


def test_post_generate_accepts_structure(client: TestClient) -> None:
    response = client.post(
        "/api/generate",
        json={"name": "my-service", "structure": "feature"},
    )

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        assert "my-service/src/my_service/features/health/router.py" in archive.namelist()


def test_compatibility_reports_a_compatible_selection(client: TestClient) -> None:
    response = client.get(
        "/compatibility",
        params={"dependencies": ["sqlalchemy,alembic"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["compatible"] is True
    assert body["issues"] == []
    assert any(feature["id"] == "sqlalchemy" for feature in body["features"])


def test_compatibility_reports_a_missing_capability(client: TestClient) -> None:
    response = client.get("/compatibility", params={"dependencies": ["alembic"]})

    assert response.status_code == 200
    body = response.json()
    assert body["compatible"] is False
    assert body["issues"] == [
        {
            "feature": "alembic",
            "kind": "missing-capability",
            "message": ("Dependency 'alembic' requires one of: sqlalchemy, sqlmodel."),
            "related": ["sqlalchemy", "sqlmodel"],
        }
    ]


def test_compatibility_reports_a_conflict(client: TestClient) -> None:
    response = client.get(
        "/compatibility",
        params={"dependencies": ["sqlalchemy", "mongodb"]},
    )

    body = response.json()
    assert body["compatible"] is False
    assert body["issues"] == [
        {
            "feature": "mongodb",
            "kind": "conflict",
            "message": "Dependency 'mongodb' conflicts with: sqlalchemy.",
            "related": ["sqlalchemy"],
        }
    ]


def test_compatibility_accepts_sqlmodel_with_alembic_and_mysql(
    client: TestClient,
) -> None:
    response = client.get(
        "/compatibility",
        params={"dependencies": ["sqlmodel,alembic,mysql"]},
    )

    body = response.json()
    assert body["compatible"] is True
    assert body["issues"] == []


def test_compatibility_reports_unknown_features(client: TestClient) -> None:
    response = client.get("/compatibility", params={"dependencies": ["missing"]})

    body = response.json()
    assert body["compatible"] is False
    assert body["issues"][0]["kind"] == "unknown"


def test_starter_zip_alias(client: TestClient) -> None:
    response = client.get("/starter.zip", params={"name": "my-service"})

    assert response.status_code == 200
    with ZipFile(io.BytesIO(response.content)) as archive:
        assert "my-service/pyproject.toml" in archive.namelist()
        assert "my-service/HELP.md" in archive.namelist()


def test_starter_tgz_returns_tar_gz(client: TestClient) -> None:
    response = client.get("/starter.tgz", params={"name": "my-service"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/gzip")
    with tarfile.open(fileobj=io.BytesIO(response.content), mode="r:gz") as archive:
        assert "my-service/pyproject.toml" in archive.getnames()


def test_pyproject_output(client: TestClient) -> None:
    response = client.get("/pyproject.toml", params={"name": "my-service"})

    assert response.status_code == 200
    assert 'name = "my-service"' in response.text
    assert '"fastapi",' in response.text
    assert "fastapi>=" not in response.text


def test_requirements_output(client: TestClient) -> None:
    response = client.get(
        "/requirements.txt",
        params={
            "name": "my-service",
            "dependencies": ["sqlalchemy", "postgres"],
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert 'filename="requirements.txt"' in response.headers["content-disposition"]
    lines = response.text.splitlines()
    assert "fastapi" in lines
    assert "sqlalchemy[asyncio]" in lines
    assert "asyncpg" in lines
    assert response.headers["x-content-type-options"] == "nosniff"


def test_requirements_post_accepts_json(client: TestClient) -> None:
    response = client.post(
        "/requirements.txt",
        json={"name": "my-service", "dependencies": ["redis", "arq"]},
    )

    assert response.status_code == 200
    lines = response.text.splitlines()
    assert "redis" in lines
    assert "arq" in lines


def test_generate_uses_base_dir_version_and_author(client: TestClient) -> None:
    response = client.get(
        "/api/generate",
        params={
            "name": "my-service",
            "version": "1.2.3",
            "author": "Ada Lovelace",
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
        assert '"fastapi",' in pyproject


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
