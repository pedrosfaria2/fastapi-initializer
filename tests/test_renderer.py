"""Template rendering and preview behavior."""

import ast
import tomllib

from fastapi_initializr.generation.preview import build_preview
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec


def test_minimal_project_contains_core_files() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "pyproject.toml" in files
    assert "README.md" in files
    assert ".gitignore" in files
    assert ".python-version" in files
    assert "src/my_service/main.py" in files
    assert "src/my_service/api/routes/health.py" in files
    assert "tests/test_health.py" in files
    assert "Dockerfile" not in files
    assert "alembic.ini" not in files
    assert ".env.example" not in files
    assert "docker-compose.yml" not in files
    assert "src/my_service/models/item.py" not in files
    assert "tests/test_items.py" not in files


def test_all_features_include_conditional_files() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset(
            {"sqlalchemy", "alembic", "postgres", "cors", "docker", "ci", "pre-commit"}
        ),
    )

    files = render_project(spec)

    assert "Dockerfile" in files
    assert ".dockerignore" in files
    assert ".github/workflows/ci.yml" in files
    assert ".pre-commit-config.yaml" in files
    assert "alembic.ini" in files
    assert "migrations/env.py" in files
    assert "migrations/versions/.gitkeep" in files
    assert "migrations/versions/0001_create_items.py" in files
    assert "docker-compose.yml" in files
    assert "src/my_service/db/session.py" in files
    assert "src/my_service/models/item.py" in files
    assert "src/my_service/schemas/item.py" in files
    assert "src/my_service/services/items.py" in files
    assert "src/my_service/api/routes/items.py" in files
    assert "tests/test_items.py" in files
    assert ".env.example" in files


def test_auth_feature_renders_security_slice() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "auth-jwt"}),
    )

    files = render_project(spec)

    assert "src/my_service/models/user.py" in files
    assert "src/my_service/schemas/user.py" in files
    assert "src/my_service/core/security.py" in files
    assert "src/my_service/services/auth.py" in files
    assert "src/my_service/api/routes/auth.py" in files
    assert "tests/test_auth.py" in files
    assert "tests/test_items.py" in files
    assert "src/my_service/models/__init__.py" in files
    assert "from my_service.models.item import Item" in files["src/my_service/models/__init__.py"]
    assert "from my_service.models.user import User" in files["src/my_service/models/__init__.py"]
    routes = files["src/my_service/api/routes/__init__.py"]
    assert "from my_service.api.routes import auth, health, items" in routes
    assert "api_router.include_router(auth.router)" in routes
    assert (
        'OAuth2PasswordBearer(tokenUrl="/auth/login")' in files["src/my_service/services/auth.py"]
    )
    assert "from my_service.models import Base" in files["tests/conftest.py"]

    config = files["src/my_service/core/config.py"]
    assert 'secret_key: str = "dev-secret-change-me-32-bytes-minimum"' in config
    assert "access_token_expire_minutes: int = 30" in config
    assert 'jwt_algorithm: str = "HS256"' in config
    env = files[".env.example"]
    assert "SECRET_KEY=change-me" in env
    assert "ACCESS_TOKEN_EXPIRE_MINUTES=30" in env

    data = tomllib.loads(files["pyproject.toml"])
    dependencies = data["project"]["dependencies"]
    assert "pwdlib[argon2]>=0.3.1" in dependencies
    assert "pyjwt>=2.15.1" in dependencies
    assert "email-validator>=2.3.0" in dependencies


def test_auth_feature_is_absent_without_auth_jwt() -> None:
    files = render_project(ProjectSpec(name="my-service", dependencies=frozenset({"sqlalchemy"})))

    assert "src/my_service/models/user.py" not in files
    assert "src/my_service/core/security.py" not in files
    assert "src/my_service/api/routes/auth.py" not in files
    assert "tests/test_auth.py" not in files
    assert (
        "from my_service.models.user import User" not in files["src/my_service/models/__init__.py"]
    )


def test_pyproject_parses_and_contains_selected_packages() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "alembic", "postgres"}),
    )

    files = render_project(spec)
    data = tomllib.loads(files["pyproject.toml"])

    assert data["project"]["name"] == "my-service"
    assert data["project"]["requires-python"] == ">=3.13"
    dependencies = data["project"]["dependencies"]
    assert any(dependency.startswith("fastapi") for dependency in dependencies)
    assert any(dependency.startswith("sqlalchemy") for dependency in dependencies)
    assert any(dependency.startswith("alembic") for dependency in dependencies)
    assert any(dependency.startswith("asyncpg") for dependency in dependencies)
    dev_dependencies = data["dependency-groups"]["dev"]
    assert any(dependency.startswith("pytest") for dependency in dev_dependencies)
    assert any(dependency.startswith("mypy") for dependency in dev_dependencies)
    assert any(dependency.startswith("pyright") for dependency in dev_dependencies)
    assert data["tool"]["ruff"]["target-version"] == "py313"
    assert data["tool"]["mypy"]["strict"] is True
    assert data["tool"]["pyright"]["typeCheckingMode"] == "strict"


def test_generated_python_parses() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "alembic", "postgres", "cors"}),
    )

    for path, content in render_project(spec).items():
        if path.endswith(".py"):
            ast.parse(content, filename=path)


def test_no_unresolved_template_markers() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "alembic", "docker", "ci"}),
    )

    for path, content in render_project(spec).items():
        assert "{{" not in content, path
        assert "{%" not in content, path
        assert "{#" not in content, path


def test_render_is_deterministic() -> None:
    spec = ProjectSpec(name="my-service", dependencies=frozenset({"sqlalchemy"}))

    assert render_project(spec) == render_project(spec)


def test_explicit_package_is_used_in_paths() -> None:
    files = render_project(ProjectSpec(name="my-service", package="custom"))

    assert "src/custom/main.py" in files
    assert "src/my_service/main.py" not in files


def test_pyproject_uses_project_metadata_and_fastapi_range() -> None:
    spec = ProjectSpec(
        name="my-service",
        version="1.2.3",
        author="Ada Lovelace",
        fastapi="0.161.1",
    )
    files = render_project(spec)
    data = tomllib.loads(files["pyproject.toml"])

    assert data["project"]["version"] == "1.2.3"
    assert data["project"]["authors"] == [{"name": "Ada Lovelace"}]
    assert "fastapi>=0.161.1,<0.162.0" in data["project"]["dependencies"]
    assert '__version__ = "1.2.3"' in files["src/my_service/__init__.py"]
    assert 'app_name: str = "my-service"' in files["src/my_service/core/config.py"]


def test_application_name_controls_app_title() -> None:
    files = render_project(ProjectSpec(name="my-service", application_name="My Public API"))

    assert 'app_name: str = "My Public API"' in files["src/my_service/core/config.py"]


def test_description_with_quotes_is_escaped_in_toml() -> None:
    description = 'A "quoted" \\ service'
    files = render_project(ProjectSpec(name="my-service", description=description))
    data = tomllib.loads(files["pyproject.toml"])

    assert data["project"]["description"] == description


def test_python_version_changes_requires_python_and_ruff_target() -> None:
    files = render_project(ProjectSpec(name="my-service", python="3.11"))
    data = tomllib.loads(files["pyproject.toml"])

    assert data["project"]["requires-python"] == ">=3.11"
    assert data["tool"]["ruff"]["target-version"] == "py311"


def test_preview_lists_rendered_files() -> None:
    preview = build_preview(ProjectSpec(name="my-service"))

    assert preview.name == "my-service"
    assert any(file.path == "pyproject.toml" for file in preview.files)
    assert all(file.size > 0 for file in preview.files)
