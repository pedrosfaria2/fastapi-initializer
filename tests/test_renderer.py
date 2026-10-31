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


def test_email_feature_renders_reset_and_verification_slice() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "auth-jwt", "email"}),
    )

    files = render_project(spec)

    assert "src/my_service/core/email.py" in files
    assert "src/my_service/services/auth_email.py" in files
    assert "src/my_service/api/routes/auth_email.py" in files
    assert "templates/email/password_reset.txt" in files
    assert "templates/email/verify_email.txt" in files
    assert "tests/test_email_auth.py" in files

    routes = files["src/my_service/api/routes/__init__.py"]
    assert "    auth_email," in routes
    assert "api_router.include_router(auth_email.router)" in routes

    config = files["src/my_service/core/config.py"]
    for setting in (
        'email_backend: str = "console"',
        'smtp_host: str = "localhost"',
        "smtp_port: int = 587",
        "smtp_starttls: bool = True",
    ):
        assert setting in config

    assert "is_verified: Mapped[bool]" in files["src/my_service/models/user.py"]
    assert "is_verified: bool" in files["src/my_service/schemas/user.py"]

    security = files["src/my_service/core/security.py"]
    assert "def create_action_token(" in security
    assert "def decode_action_token(" in security

    assert "{{ token }}" in files["templates/email/password_reset.txt"]
    assert "{{ token }}" in files["templates/email/verify_email.txt"]

    env = files[".env.example"]
    assert "EMAIL_BACKEND=console" in env
    assert "SMTP_HOST=localhost" in env
    assert "SMTP_FROM=noreply@example.com" in env

    data = tomllib.loads(files["pyproject.toml"])
    dependencies = data["project"]["dependencies"]
    assert "aiosmtplib>=5.1.3" in dependencies
    assert "jinja2>=3.1.6" in dependencies

    readme = files["README.md"]
    assert "## Email, password reset, and verification" in readme
    assert "/auth/request-password-reset" in readme
    assert "/auth/verify-email" in readme
    assert "EMAIL_BACKEND" in readme


def test_email_feature_is_absent_without_email() -> None:
    files = render_project(
        ProjectSpec(
            name="my-service",
            dependencies=frozenset({"sqlalchemy", "auth-jwt"}),
        )
    )

    assert "src/my_service/core/email.py" not in files
    assert "src/my_service/services/auth_email.py" not in files
    assert "src/my_service/api/routes/auth_email.py" not in files
    assert "templates/email/password_reset.txt" not in files
    assert "templates/email/verify_email.txt" not in files
    assert "tests/test_email_auth.py" not in files
    assert "is_verified" not in files["src/my_service/models/user.py"]
    assert "is_verified" not in files["src/my_service/schemas/user.py"]
    assert "auth_email" not in files["src/my_service/api/routes/__init__.py"]


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
                "auth-jwt",
                "email",
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
                "uploads",
                "s3",
                "testcontainers",
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
                "uploads",
                "s3",
                "testcontainers",
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


def test_uploads_feature_renders_storage_and_routes() -> None:
    spec = ProjectSpec(name="my-service", dependencies=frozenset({"uploads"}))

    files = render_project(spec)

    assert "src/my_service/core/storage.py" in files
    assert "src/my_service/api/routes/uploads.py" in files
    assert "tests/test_uploads.py" in files
    assert ".env.example" in files

    routes = files["src/my_service/api/routes/__init__.py"]
    assert "    uploads," in routes
    assert "api_router.include_router(uploads.router)" in routes

    storage = files["src/my_service/core/storage.py"]
    assert "class Storage(Protocol):" in storage
    assert "class LocalStorage:" in storage
    assert "def new_storage_key(filename: str) -> str:" in storage
    assert "def get_storage(" in storage
    assert "is_relative_to(root)" in storage

    config = files["src/my_service/core/config.py"]
    assert 'upload_dir: str = "uploads"' in config
    assert "max_upload_bytes: int = 5_000_000" in config
    assert '"image/png"' in config
    assert '"application/pdf"' in config

    env = files[".env.example"]
    assert "UPLOAD_DIR=uploads" in env
    assert "MAX_UPLOAD_BYTES=5000000" in env
    assert "ALLOWED_UPLOAD_TYPES" in env

    data = tomllib.loads(files["pyproject.toml"])
    assert any(
        dependency.startswith("python-multipart") for dependency in data["project"]["dependencies"]
    )

    readme = files["README.md"]
    assert "## File uploads" in readme
    assert "/uploads/{key}" in readme
    assert "## S3-compatible storage" not in readme


def test_s3_feature_renders_backend_and_test_dependencies() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"uploads", "s3"}),
    )

    files = render_project(spec)

    assert "src/my_service/core/storage.py" in files
    assert "src/my_service/core/storage_s3.py" in files
    assert "tests/test_storage_s3.py" in files

    storage = files["src/my_service/core/storage.py"]
    assert "from my_service.core.storage_s3 import S3Storage" in storage
    assert 'if settings.storage_backend == "s3":' in storage

    s3_storage = files["src/my_service/core/storage_s3.py"]
    assert "class S3Storage:" in s3_storage
    assert "boto3.client(" in s3_storage
    assert "asyncio.to_thread(" in s3_storage

    config = files["src/my_service/core/config.py"]
    for setting in (
        'storage_backend: str = "local"',
        's3_bucket: str = "uploads"',
        's3_endpoint_url: str = ""',
        's3_region: str = "us-east-1"',
        's3_access_key_id: str = ""',
        's3_secret_access_key: str = ""',
    ):
        assert setting in config

    env = files[".env.example"]
    assert "STORAGE_BACKEND=local" in env
    assert "S3_BUCKET=uploads" in env
    assert "S3_REGION=us-east-1" in env

    data = tomllib.loads(files["pyproject.toml"])
    assert "boto3>=1.43.123" in data["project"]["dependencies"]
    assert "moto[s3]>=5.2.5" in data["dependency-groups"]["dev"]
    overrides = data["tool"]["mypy"]["overrides"]
    assert any("boto3" in override["module"] for override in overrides)

    readme = files["README.md"]
    assert "## S3-compatible storage" in readme
    assert "STORAGE_BACKEND=s3" in readme


def test_uploads_and_s3_are_absent_by_default() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "src/my_service/core/storage.py" not in files
    assert "src/my_service/core/storage_s3.py" not in files
    assert "src/my_service/api/routes/uploads.py" not in files
    assert "tests/test_uploads.py" not in files
    assert "tests/test_storage_s3.py" not in files
    assert "uploads" not in files["src/my_service/api/routes/__init__.py"]


def test_testcontainers_feature_renders_integration_suite() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "postgres", "redis", "testcontainers"}),
    )

    files = render_project(spec)

    assert "tests/integration/conftest.py" in files
    assert "tests/integration/test_integration.py" in files
    assert "scripts/run_integration.sh" in files
    assert ".github/workflows/integration.yml" in files

    conftest = files["tests/integration/conftest.py"]
    assert 'PostgresContainer("postgres:17")' in conftest
    assert 'RedisContainer("redis:7-alpine")' in conftest
    assert 'os.environ.get("RUN_INTEGRATION") == "1"' in conftest
    assert "pytest.skip(SKIP_REASON)" in conftest

    integration = files["tests/integration/test_integration.py"]
    assert "pytestmark = pytest.mark.integration" in integration
    assert "get_connection_url()" in integration
    assert "client.ping() is True" in integration

    script = files["scripts/run_integration.sh"]
    assert "RUN_INTEGRATION=1 uv run pytest -m integration" in script

    workflow = files[".github/workflows/integration.yml"]
    assert "workflow_dispatch:" in workflow
    assert "bash scripts/run_integration.sh" in workflow

    data = tomllib.loads(files["pyproject.toml"])
    assert "testcontainers[postgres]>=4.15.0" in data["dependency-groups"]["dev"]
    assert data["tool"]["pytest"]["ini_options"]["markers"] == ["integration"]

    readme = files["README.md"]
    assert "### Integration tests" in readme
    assert "bash scripts/run_integration.sh" in readme


def test_testcontainers_files_are_absent_by_default() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "tests/integration/conftest.py" not in files
    assert "tests/integration/test_integration.py" not in files
    assert "scripts/run_integration.sh" not in files
    assert ".github/workflows/integration.yml" not in files


def test_preview_lists_rendered_files() -> None:
    preview = build_preview(ProjectSpec(name="my-service"))

    assert preview.name == "my-service"
    assert any(file.path == "pyproject.toml" for file in preview.files)
    assert all(file.size > 0 for file in preview.files)
