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


def test_extended_web_features_render_files_and_settings() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset(
            {
                "cors",
                "static-templates",
                "websockets",
                "prometheus",
                "sentry",
                "rate-limit",
                "redis",
            }
        ),
    )

    files = render_project(spec)

    assert "src/my_service/core/cache.py" in files
    assert "src/my_service/core/observability.py" in files
    assert "src/my_service/core/rate_limit.py" in files
    assert "src/my_service/api/routes/pages.py" in files
    assert "src/my_service/api/routes/ws.py" in files
    assert "src/my_service/api/routes/limited.py" in files
    assert "templates/index.html" in files
    assert "static/style.css" in files
    assert "tests/test_cache.py" in files
    assert "tests/test_sentry.py" in files
    assert "tests/test_prometheus.py" in files
    assert "tests/test_pages.py" in files
    assert "tests/test_websockets.py" in files
    assert "tests/test_rate_limit.py" in files

    config = files["src/my_service/core/config.py"]
    assert 'redis_url: str = "redis://localhost:6379/0"' in config
    assert 'sentry_dsn: str = ""' in config
    assert 'sentry_environment: str = "development"' in config

    main = files["src/my_service/main.py"]
    assert "init_sentry(settings)" in main
    assert "Instrumentator().instrument(app).expose(app)" in main
    assert "app.state.limiter = limiter" in main
    assert "StaticFiles" in main

    env = files[".env.example"]
    assert "REDIS_URL=redis://localhost:6379/0" in env
    assert "SENTRY_DSN=" in env
    assert "SENTRY_ENVIRONMENT=development" in env

    data = tomllib.loads(files["pyproject.toml"])
    dependencies = data["project"]["dependencies"]
    for package in (
        "redis>=5.3.1",
        "sentry-sdk[fastapi]>=2.73.0",
        "prometheus-fastapi-instrumentator>=8.1.0",
        "slowapi>=0.1.10",
        "jinja2>=3.1.6",
    ):
        assert package in dependencies


def test_extended_web_features_are_absent_by_default() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "src/my_service/core/cache.py" not in files
    assert "src/my_service/core/cache_helpers.py" not in files
    assert "src/my_service/tasks/__init__.py" not in files
    assert "src/my_service/tasks/example.py" not in files
    assert "src/my_service/worker.py" not in files
    assert "tests/test_cache_helpers.py" not in files
    assert "tests/test_worker.py" not in files
    assert "src/my_service/core/observability.py" not in files
    assert "src/my_service/core/rate_limit.py" not in files
    assert "src/my_service/api/routes/pages.py" not in files
    assert "src/my_service/api/routes/ws.py" not in files
    assert "src/my_service/api/routes/limited.py" not in files
    assert "templates/index.html" not in files
    assert "Makefile" not in files
    assert "docker-compose.yml" not in files


def test_worker_and_cache_helpers_render_files_and_settings() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"redis", "arq", "cache"}),
    )

    files = render_project(spec)

    assert "src/my_service/worker.py" in files
    assert "src/my_service/tasks/__init__.py" in files
    assert "src/my_service/tasks/example.py" in files
    assert "src/my_service/core/cache_helpers.py" in files
    assert "tests/test_worker.py" in files
    assert "tests/test_cache_helpers.py" in files

    worker = files["src/my_service/worker.py"]
    assert "class WorkerSettings:" in worker
    assert "functions: ClassVar[list[ExampleTask]] = [example_task]" in worker
    assert "RedisSettings.from_dsn(get_settings().redis_url)" in worker
    assert "from my_service.tasks import example_task" in worker

    task = files["src/my_service/tasks/example.py"]
    assert "async def example_task(ctx: dict[str, object], name: str) -> str:" in task
    assert 'return f"Hello, {name}!"' in task

    cache_helpers = files["src/my_service/core/cache_helpers.py"]
    assert "class CacheBackend(Protocol):" in cache_helpers
    assert "class Cache:" in cache_helpers
    assert "def cache_aside(" in cache_helpers
    assert "ParamSpec" in cache_helpers
    assert "cast(T, json.loads(cached))" in cache_helpers

    compose = files["docker-compose.yml"]
    assert "  worker:" in compose
    assert "    build: ." in compose
    assert "    command: arq my_service.worker.WorkerSettings" in compose
    assert "      - .env" in compose
    assert "        condition: service_healthy" in compose

    data = tomllib.loads(files["pyproject.toml"])
    assert "arq>=0.28.0" in data["project"]["dependencies"]

    readme = files["README.md"]
    assert "uv run arq my_service.worker.WorkerSettings" in readme
    assert "ARQ runs background jobs against Redis." in readme
    assert "## Cache helpers" in readme


def test_operations_features_render_makefile_and_compose() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"docker", "compose", "ci", "pre-commit", "makefile"}),
    )

    files = render_project(spec)

    assert "Dockerfile" in files
    assert ".dockerignore" in files
    assert "docker-compose.yml" in files
    assert "Makefile" in files
    assert "tests/test_makefile.py" in files

    makefile = files["Makefile"]
    for target in ("sync", "run", "test", "lint", "typecheck", "format"):
        assert f"{target}:" in makefile

    compose = files["docker-compose.yml"]
    assert "  app:" in compose
    assert "  db:" not in compose
    assert "  redis:" not in compose


def test_compose_includes_postgres_and_redis_healthchecks() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "postgres", "redis"}),
    )

    compose = render_project(spec)["docker-compose.yml"]

    assert "docker-compose.yml" in render_project(spec)
    assert "  db:" in compose
    assert "pg_isready" in compose
    assert "  redis:" in compose
    assert "redis-cli" in compose
    assert "postgres" in compose


def test_compose_is_generated_for_postgres_without_docker() -> None:
    files = render_project(
        ProjectSpec(
            name="my-service",
            dependencies=frozenset({"sqlalchemy", "postgres"}),
        )
    )

    assert "docker-compose.yml" in files
    assert "Dockerfile" not in files


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
    assert "    auth," in routes
    assert "    health," in routes
    assert "    items," in routes
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
        dependencies=frozenset(
            {
                "sqlalchemy",
                "alembic",
                "postgres",
                "cors",
                "redis",
                "cache",
                "arq",
                "sentry",
                "prometheus",
                "static-templates",
                "websockets",
                "rate-limit",
                "makefile",
                "compose",
                "docker",
                "ci",
                "pre-commit",
            }
        ),
    )

    for path, content in render_project(spec).items():
        if path.endswith(".py"):
            ast.parse(content, filename=path)


def test_no_unresolved_template_markers() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset(
            {
                "sqlalchemy",
                "alembic",
                "postgres",
                "redis",
                "sentry",
                "prometheus",
                "static-templates",
                "websockets",
                "rate-limit",
                "docker",
                "compose",
                "makefile",
                "ci",
                "pre-commit",
            }
        ),
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
