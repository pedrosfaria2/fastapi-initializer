"""Template rendering and preview behavior."""

import ast
import tomllib
from typing import Any, cast

import pytest
import yaml  # type: ignore[import-untyped]  # PyYAML ships no inline type hints

from fastapi_initializr.generation.preview import build_preview
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec


def _load_yaml(content: str) -> dict[str, Any]:
    data = yaml.safe_load(content)
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def test_minimal_project_contains_core_files() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "pyproject.toml" in files
    assert "README.md" in files
    assert "HELP.md" in files
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


def test_typescript_client_feature_renders_client_package() -> None:
    files = render_project(
        ProjectSpec(name="my-service", dependencies=frozenset({"typescript-client"}))
    )

    assert "client/package.json" in files
    assert '"openapi-fetch": "latest"' in files["client/package.json"]
    assert '"openapi-typescript": "latest"' in files["client/package.json"]
    assert '"minimatch": "latest"' in files["client/package.json"]
    assert "generate:api" in files["client/package.json"]
    assert "from my_service.main import app" in files["client/export_openapi.py"]
    assert "createClient<paths>" in files["client/src/api/client.ts"]
    assert "export type paths" in files["client/src/api/schema.d.ts"]
    assert "client/node_modules/" in files[".gitignore"]
    assert "## TypeScript client" in files["README.md"]
    assert "cd client && npm install && npm run generate:api" in files["HELP.md"]


def test_schemathesis_feature_renders_contract_test() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "schemathesis"}),
    )

    files = render_project(spec)

    assert "tests/test_contract.py" in files
    contract = files["tests/test_contract.py"]
    assert "from_asgi" in contract
    assert "allow_header_conformance" in contract
    assert 'exclude(path_regex="^/auth")' in contract
    dependencies = tomllib.loads(files["pyproject.toml"])["dependency-groups"]["dev"]
    assert "schemathesis" in dependencies
    assert "## Contract tests" in files["README.md"]
    assert "tests/test_contract.py" in files["HELP.md"]


def test_minimal_structure_keeps_a_small_module_set() -> None:
    files = render_project(ProjectSpec(name="my-service", structure="minimal"))

    assert "src/my_service/main.py" in files
    assert "src/my_service/config.py" in files
    assert "src/my_service/errors.py" in files
    assert "src/my_service/logging.py" in files
    assert "src/my_service/middleware.py" in files
    assert "src/my_service/api/routes/health.py" not in files
    assert "src/my_service/core/config.py" not in files
    assert "def health() -> dict[str, str]:" in files["src/my_service/main.py"]
    assert "├── config.py" in files["README.md"]
    assert "├── api/" not in files["README.md"]


def test_feature_structure_moves_domain_modules() -> None:
    spec = ProjectSpec(
        name="my-service",
        structure="feature",
        dependencies=frozenset({"sqlalchemy", "auth-jwt", "cors"}),
    )

    files = render_project(spec)

    assert "src/my_service/features/items/router.py" in files
    assert "src/my_service/features/items/models.py" in files
    assert "src/my_service/features/items/schemas.py" in files
    assert "src/my_service/features/items/service.py" in files
    assert "src/my_service/features/auth/router.py" in files
    assert "src/my_service/features/auth/models.py" in files
    assert "src/my_service/api/router.py" in files
    assert "src/my_service/models_registry.py" in files
    assert "src/my_service/models/item.py" not in files
    assert "src/my_service/api/routes/items.py" not in files
    assert "src/my_service/schemas/item.py" not in files
    assert "src/my_service/services/items.py" not in files
    assert "from my_service.api.router import api_router" in files["src/my_service/main.py"]
    assert "features.items.router" in files["src/my_service/api/router.py"]
    assert "features.auth.models" in files["src/my_service/models_registry.py"]


def test_feature_structure_keeps_layered_files_by_default() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "src/my_service/api/routes/health.py" in files
    assert not any(path.startswith("src/my_service/features/") for path in files)


def test_application_name_escapes_python_string_content() -> None:
    spec = ProjectSpec(
        name="my-service",
        application_name='Acme "API"',
        dependencies=frozenset({"opentelemetry"}),
    )

    config = render_project(spec)["src/my_service/core/config.py"]

    assert 'app_name: str = "Acme \\"API\\""' in config
    assert 'otel_service_name: str = "Acme \\"API\\""' in config


def test_application_name_preserves_unicode() -> None:
    spec = ProjectSpec(name="my-service", application_name="Service 🚀")

    config = render_project(spec)["src/my_service/core/config.py"]
    line = next(line for line in config.splitlines() if "app_name" in line)
    literal = line.split(" = ", 1)[1]

    assert ast.literal_eval(literal) == "Service 🚀"


@pytest.mark.parametrize(
    ("field", "value", "path", "marker"),
    [
        ("description", "literal {{x}}", "pyproject.toml", "{{x}}"),
        ("author", "literal {%x%}", "pyproject.toml", "{%x%}"),
        (
            "application_name",
            'Acme "{{x}}"',
            "src/my_service/core/config.py",
            "{{x}}",
        ),
    ],
)
def test_user_text_can_contain_template_markers(
    field: str,
    value: str,
    path: str,
    marker: str,
) -> None:
    spec = ProjectSpec(name="my-service", **{field: value})

    content = render_project(spec)[path]

    assert marker in content


def test_help_lists_selected_features_and_links() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "alembic", "redis", "arq"}),
    )

    help_text = render_project(spec)["HELP.md"]

    assert "## Selected features" in help_text
    assert "### Alembic" in help_text
    assert "`uv run alembic upgrade head`" in help_text
    assert "### ARQ" in help_text
    assert "uv run arq my_service.worker.WorkerSettings" in help_text
    assert "https://alembic.sqlalchemy.org/en/latest/tutorial.html" in help_text
    assert "README.md" in help_text
    assert "{package}" not in help_text


def test_help_omits_unselected_features() -> None:
    help_text = render_project(ProjectSpec(name="my-service"))["HELP.md"]

    assert "No optional features selected." in help_text
    assert "Alembic" not in help_text
    assert "Redis" not in help_text


def test_help_includes_environment_auth_and_compose_steps() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "auth-jwt", "docker", "compose"}),
    )

    help_text = render_project(spec)["HELP.md"]

    assert "cp .env.example .env" in help_text
    assert "Change `SECRET_KEY` in `.env` before deploying." in help_text
    assert "docker compose up --build" in help_text


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
    assert "REDIS_URL" in env
    assert "SENTRY_DSN" in env
    assert "SENTRY_ENVIRONMENT" in env

    data = tomllib.loads(files["pyproject.toml"])
    dependencies = data["project"]["dependencies"]
    for package in (
        "redis",
        "sentry-sdk[fastapi]",
        "prometheus-fastapi-instrumentator",
        "slowapi",
        "jinja2",
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
    assert "arq" in data["project"]["dependencies"]

    readme = files["README.md"]
    assert "uv run arq my_service.worker.WorkerSettings" in readme
    assert "ARQ runs background jobs against Redis." in readme
    assert "## Cache helpers" in readme


def test_celery_rabbitmq_renders_worker_and_compose() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"celery", "rabbitmq"}),
    )

    files = render_project(spec)

    worker = files["src/my_service/worker.py"]
    assert "celery_app = Celery(" in worker
    assert "def _add(left: int, right: int) -> int:" in worker
    assert "celery_broker_url" in files["src/my_service/core/config.py"]
    assert (
        "amqp://guest:guest@localhost:5672//"  # pragma: allowlist secret
        in files[".env.example"]
    )
    assert "tests/test_worker.py" in files
    assert "add.delay(2, 3)" in files["tests/test_worker.py"]

    compose = files["docker-compose.yml"]
    assert "  rabbitmq:" in compose
    assert "rabbitmq:management" in compose
    assert "rabbitmq-diagnostics" in compose
    assert "  worker:" in compose
    assert "celery -A my_service.worker.celery_app worker" in compose
    assert "rabbitmq-data" in compose

    assert "## Celery worker" in files["README.md"]
    assert "celery -A my_service.worker.celery_app" in files["HELP.md"]


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


def test_security_scan_feature_renders_hard_gate_and_wiring() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"security-scan", "ci", "pre-commit", "docker"}),
    )

    files = render_project(spec)

    assert "scripts/security.sh" in files
    assert "tests/test_security_tooling.py" in files
    script = files["scripts/security.sh"]
    assert "set -euo pipefail" in script
    for command in (
        "uv run pip-audit",
        "uv run bandit -r src -q",
        "uv run detect-secrets scan --all-files",
        "uv run cyclonedx-py environment -o sbom.json",
    ):
        assert command in script
    assert "mktemp" in script
    assert "trap" in script
    assert "raise SystemExit(1 if results else 0)" in script

    workflow = files[".github/workflows/ci.yml"]
    assert "Security scan" in workflow
    assert "bash scripts/security.sh" in workflow

    pre_commit = files[".pre-commit-config.yaml"]
    assert "id: pip-audit" in pre_commit
    assert "entry: uv run pip-audit" in pre_commit
    assert "id: bandit" in pre_commit
    assert "entry: uv run bandit -r src -q" in pre_commit

    data = tomllib.loads(files["pyproject.toml"])
    dev_dependencies = data["dependency-groups"]["dev"]
    for package in (
        "pip-audit",
        "bandit",
        "detect-secrets",
        "cyclonedx-bom",
    ):
        assert package in dev_dependencies

    assert "sbom.json" in files[".gitignore"]

    readme = files["README.md"]
    assert "## Security scanning and SBOM" in readme
    assert "bash scripts/security.sh" in readme
    assert "pip-audit" in readme
    assert "cyclonedx-py environment -o sbom.json" in readme


def test_security_scan_feature_is_absent_by_default() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "scripts/security.sh" not in files
    assert "tests/test_security_tooling.py" not in files
    assert "sbom.json" not in files[".gitignore"]
    assert "## Security scanning and SBOM" not in files["README.md"]


def test_kubernetes_feature_renders_manifests() -> None:
    files = render_project(ProjectSpec(name="my-service", dependencies=frozenset({"kubernetes"})))

    for name in ("configmap.yaml", "deployment.yaml", "ingress.yaml", "service.yaml"):
        assert f"k8s/{name}" in files
    assert "tests/test_kubernetes.py" in files

    deployment = _load_yaml(files["k8s/deployment.yaml"])
    pod_spec = deployment["spec"]["template"]["spec"]
    container = pod_spec["containers"][0]
    assert deployment["kind"] == "Deployment"
    assert container["image"] == "ghcr.io/example/my-service:latest"
    assert container["ports"][0]["containerPort"] == 8000
    assert container["envFrom"][0]["configMapRef"]["name"] == "my-service-config"
    assert container["readinessProbe"]["httpGet"]["path"] == "/ready"
    assert container["livenessProbe"]["httpGet"]["path"] == "/health"
    assert container["resources"]["requests"]
    assert container["resources"]["limits"]

    service = _load_yaml(files["k8s/service.yaml"])
    port = service["spec"]["ports"][0]
    assert service["kind"] == "Service"
    assert service["spec"]["type"] == "ClusterIP"
    assert port["port"] == 80
    assert port["targetPort"] == 8000

    config_map = _load_yaml(files["k8s/configmap.yaml"])
    assert config_map["kind"] == "ConfigMap"
    assert config_map["data"] == {"ENVIRONMENT": "production", "LOG_LEVEL": "INFO"}

    ingress = _load_yaml(files["k8s/ingress.yaml"])
    rule = ingress["spec"]["rules"][0]
    path = rule["http"]["paths"][0]
    assert ingress["kind"] == "Ingress"
    assert rule["host"] == "my-service.example.com"
    assert path["path"] == "/"
    assert path["backend"]["service"]["port"]["number"] == 80

    data = tomllib.loads(files["pyproject.toml"])
    assert "pyyaml" in data["dependency-groups"]["dev"]

    readme = files["README.md"]
    assert "## Kubernetes" in readme
    assert "kubectl apply -f k8s/deployment.yaml" in readme
    assert "{{ spec.name }}" not in readme


def test_kubernetes_feature_is_absent_by_default() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "k8s/deployment.yaml" not in files
    assert "k8s/service.yaml" not in files
    assert "k8s/configmap.yaml" not in files
    assert "k8s/ingress.yaml" not in files
    assert "tests/test_kubernetes.py" not in files
    assert "## Kubernetes" not in files["README.md"]


def test_gitlab_ci_feature_renders_pipeline() -> None:
    files = render_project(ProjectSpec(name="my-service", dependencies=frozenset({"ci-gitlab"})))

    pipeline = _load_yaml(files[".gitlab-ci.yml"])

    assert pipeline["stages"] == ["lint", "typecheck", "test"]
    assert pipeline["default"]["image"] == "ghcr.io/astral-sh/uv:latest"
    assert pipeline["default"]["before_script"] == ["uv sync"]
    assert pipeline["lint"]["stage"] == "lint"
    assert pipeline["lint"]["script"] == [
        "uv run ruff format --check .",
        "uv run ruff check .",
    ]
    assert pipeline["typecheck"]["stage"] == "typecheck"
    assert pipeline["typecheck"]["script"] == [
        "uv run mypy src",
        "uv run pyright src",
    ]
    assert pipeline["test"]["stage"] == "test"
    assert pipeline["test"]["script"] == ["uv run pytest"]

    assert "## GitLab CI" in files["README.md"]
    assert ".gitlab-ci.yml" in files["README.md"]


def test_bitbucket_pipelines_feature_renders_pipeline() -> None:
    files = render_project(ProjectSpec(name="my-service", dependencies=frozenset({"ci-bitbucket"})))

    pipeline = _load_yaml(files["bitbucket-pipelines.yml"])
    step = pipeline["pipelines"]["default"][0]["step"]

    assert pipeline["image"] == "python:3.13-slim"
    assert step["name"] == "Quality gates"
    assert step["script"] == [
        "python -m pip install --upgrade uv",
        "uv sync",
        "uv run ruff format --check .",
        "uv run ruff check .",
        "uv run mypy src",
        "uv run pyright src",
        "uv run pytest",
    ]

    assert "## Bitbucket Pipelines" in files["README.md"]
    assert "bitbucket-pipelines.yml" in files["README.md"]


def test_gitlab_and_bitbucket_pipelines_are_absent_by_default() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert ".gitlab-ci.yml" not in files
    assert "bitbucket-pipelines.yml" not in files
    assert "## GitLab CI" not in files["README.md"]
    assert "## Bitbucket Pipelines" not in files["README.md"]


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
    assert "from my_service.api.routes.auth import router as auth_router" in routes
    assert "from my_service.api.routes.health import router as health_router" in routes
    assert "from my_service.api.routes.items import router as items_router" in routes
    assert "api_router.include_router(auth_router)" in routes
    assert (
        'OAuth2PasswordBearer(tokenUrl="/auth/login")' in files["src/my_service/services/auth.py"]
    )
    assert "from my_service.models import Base" in files["tests/conftest.py"]

    config = files["src/my_service/core/config.py"]
    assert 'secret_key: str = "dev-secret-change-me-32-bytes-minimum"' in config
    assert "access_token_expire_minutes: int = 5" in config
    assert 'jwt_algorithm: str = "HS256"' in config
    env = files[".env.example"]
    assert "SECRET_KEY" in env
    assert "ACCESS_TOKEN_EXPIRE_MINUTES" in env

    data = tomllib.loads(files["pyproject.toml"])
    dependencies = data["project"]["dependencies"]
    assert "pwdlib[argon2]" in dependencies
    assert "pyjwt" in dependencies
    assert "email-validator" in dependencies


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
    assert "templates/email/password_changed.txt" in files
    assert "tests/test_email_auth.py" in files

    routes = files["src/my_service/api/routes/__init__.py"]
    assert "from my_service.api.routes.auth_email import router as auth_email_router" in routes
    assert "api_router.include_router(auth_email_router)" in routes

    config = files["src/my_service/core/config.py"]
    for setting in (
        'email_backend: str = "console"',
        'smtp_host: str = "localhost"',
        "smtp_port: int = 587",
        "smtp_starttls: bool = True",
    ):
        assert setting in config

    assert "is_verified: Mapped[bool]" in files["src/my_service/models/user.py"]
    assert "password_reset_version: Mapped[int]" in files["src/my_service/models/user.py"]
    assert "email_verification_version: Mapped[int]" in files["src/my_service/models/user.py"]
    assert "is_verified: bool" in files["src/my_service/schemas/user.py"]
    assert "def _validate_production_settings(" in config

    security = files["src/my_service/core/security.py"]
    assert "def create_action_token(" in security
    assert "def decode_action_token(" in security

    assert "{{ token }}" in files["templates/email/password_reset.txt"]
    assert "{{ token }}" in files["templates/email/verify_email.txt"]

    env = files[".env.example"]
    assert "EMAIL_BACKEND" in env
    assert "SMTP_HOST" in env
    assert "SMTP_FROM" in env

    data = tomllib.loads(files["pyproject.toml"])
    dependencies = data["project"]["dependencies"]
    assert "aiosmtplib" in dependencies
    assert "jinja2" in dependencies

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


def test_oauth_feature_renders_provider_slice() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "auth-jwt", "oauth2"}),
    )

    files = render_project(spec)

    assert "src/my_service/core/oauth.py" in files
    assert "src/my_service/services/oauth.py" in files
    assert "src/my_service/api/routes/oauth.py" in files
    assert "tests/test_oauth.py" in files

    routes = files["src/my_service/api/routes/__init__.py"]
    assert "from my_service.api.routes.oauth import router as oauth_router" in routes
    assert "api_router.include_router(oauth_router)" in routes

    oauth = files["src/my_service/core/oauth.py"]
    assert "OAuthClient" in oauth
    assert "authorize_redirect" in oauth
    assert "server_metadata_url" in oauth
    assert "api_base_url" in oauth
    assert "get_oauth_client" in oauth

    service = files["src/my_service/services/oauth.py"]
    assert "fetch_provider_identity" in service
    assert "get_or_create_oauth_user" in service
    assert "OAuthAccountExistsError" in service
    assert "email_verified" in service
    assert 'client.get_json("user/emails"' in service
    assert 'client.get_json("user"' in service
    assert 'profile.get("id")' in service
    assert "oauth_provider" in files["src/my_service/models/user.py"]
    assert "oauth_subject" in files["src/my_service/models/user.py"]

    config = files["src/my_service/core/config.py"]
    for setting in (
        'oauth_redirect_base_url: str = "http://localhost:8000"',
        'google_client_id: str = ""',
        'google_client_secret: str = ""',
        'github_client_id: str = ""',
        'github_client_secret: str = ""',
    ):
        assert setting in config

    env = files[".env.example"]
    for setting in (
        "OAUTH_REDIRECT_BASE_URL",
        "GOOGLE_CLIENT_ID",
        "GOOGLE_CLIENT_SECRET",
        "GITHUB_CLIENT_ID",
        "GITHUB_CLIENT_SECRET",
    ):
        assert setting in env

    data = tomllib.loads(files["pyproject.toml"])
    dependencies = data["project"]["dependencies"]
    assert "authlib" in dependencies
    assert "itsdangerous" in dependencies

    readme = files["README.md"]
    assert "## OAuth2 and OIDC login" in readme
    assert "/auth/oauth/{provider}/login" in readme
    assert "/auth/oauth/{provider}/callback" in readme
    assert "OAUTH_REDIRECT_BASE_URL" in readme


def test_oauth_feature_is_absent_by_default() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "src/my_service/core/oauth.py" not in files
    assert "src/my_service/services/oauth.py" not in files
    assert "src/my_service/api/routes/oauth.py" not in files
    assert "tests/test_oauth.py" not in files
    assert "oauth" not in files["src/my_service/api/routes/__init__.py"]


def test_opentelemetry_feature_renders_tracing_slice() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "redis", "opentelemetry"}),
    )

    files = render_project(spec)

    assert "src/my_service/core/tracing.py" in files
    assert "tests/test_tracing.py" in files

    tracing = files["src/my_service/core/tracing.py"]
    assert "def configure_tracing(" in tracing
    assert "TracerProvider" in tracing
    assert "OTLPSpanExporter" in tracing
    assert "FastAPIInstrumentor" in tracing
    assert "SQLAlchemyInstrumentor" in tracing
    assert "RedisInstrumentor" in tracing

    main = files["src/my_service/main.py"]
    assert "from my_service.core.tracing import configure_tracing" in main
    assert "configure_tracing(app, settings)" in main

    config = files["src/my_service/core/config.py"]
    for setting in (
        'otel_exporter_otlp_endpoint: str = ""',
        'otel_service_name: str = "my-service"',
        'otel_environment: str = "development"',
    ):
        assert setting in config

    env = files[".env.example"]
    for setting in (
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "OTEL_SERVICE_NAME",
        "OTEL_ENVIRONMENT",
    ):
        assert setting in env

    data = tomllib.loads(files["pyproject.toml"])
    dependencies = data["project"]["dependencies"]
    for package in (
        "opentelemetry-sdk",
        "opentelemetry-exporter-otlp",
        "opentelemetry-instrumentation-fastapi",
        "opentelemetry-instrumentation-sqlalchemy",
        "opentelemetry-instrumentation-redis",
    ):
        assert package in dependencies

    readme = files["README.md"]
    assert "## Tracing" in readme
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" in readme


def test_opentelemetry_feature_is_absent_by_default() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "src/my_service/core/tracing.py" not in files
    assert "tests/test_tracing.py" not in files
    assert "configure_tracing" not in files["src/my_service/main.py"]


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
                "oauth2",
                "redis",
                "cache",
                "arq",
                "sentry",
                "prometheus",
                "opentelemetry",
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
                "security-scan",
                "kubernetes",
                "ci-gitlab",
                "ci-bitbucket",
                "graphql",
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
                "auth-jwt",
                "oauth2",
                "redis",
                "sentry",
                "prometheus",
                "opentelemetry",
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
                "security-scan",
                "kubernetes",
                "ci-gitlab",
                "ci-bitbucket",
                "graphql",
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


def test_pyproject_uses_project_metadata_without_version_pins() -> None:
    spec = ProjectSpec(
        name="my-service",
        version="1.2.3",
        author="Ada Lovelace",
    )
    files = render_project(spec)
    data = tomllib.loads(files["pyproject.toml"])

    assert data["project"]["version"] == "1.2.3"
    assert data["project"]["authors"] == [{"name": "Ada Lovelace"}]
    assert data["project"]["dependencies"] == [
        "fastapi",
        "fastapi-cli",
        "uvicorn[standard]",
        "pydantic-settings",
        "python-multipart",
    ]
    assert data["dependency-groups"]["dev"] == [
        "pytest",
        "pytest-cov",
        "httpx2",
        "ruff",
        "mypy",
        "pyright",
    ]
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
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "auth-jwt", "uploads"}),
    )

    files = render_project(spec)

    assert "src/my_service/core/storage.py" in files
    assert "src/my_service/api/routes/uploads.py" in files
    assert "tests/test_uploads.py" in files
    assert ".env.example" in files

    routes = files["src/my_service/api/routes/__init__.py"]
    assert "from my_service.api.routes.uploads import router as uploads_router" in routes
    assert "api_router.include_router(uploads_router)" in routes

    storage = files["src/my_service/core/storage.py"]
    assert "class Storage(Protocol):" in storage
    assert "class LocalStorage:" in storage
    assert "def new_storage_key(filename: str, owner_id: int) -> str:" in storage
    assert "def get_storage(" in storage
    assert "is_relative_to(root)" in storage

    uploads = files["src/my_service/api/routes/uploads.py"]
    assert "current_user: CurrentUser" in uploads
    assert "def _owned_key(owner_id: int, key: str) -> str:" in uploads

    config = files["src/my_service/core/config.py"]
    assert 'upload_dir: str = "uploads"' in config
    assert "max_upload_bytes: int = 5_000_000" in config
    assert '"image/png"' in config
    assert '"application/pdf"' in config

    env = files[".env.example"]
    assert "UPLOAD_DIR" in env
    assert "MAX_UPLOAD_BYTES" in env
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
        dependencies=frozenset({"sqlalchemy", "auth-jwt", "uploads", "s3"}),
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
    assert "STORAGE_BACKEND" in env
    assert "S3_BUCKET" in env
    assert "S3_REGION" in env

    data = tomllib.loads(files["pyproject.toml"])
    assert "boto3" in data["project"]["dependencies"]
    assert "moto[s3]" in data["dependency-groups"]["dev"]
    overrides = data["tool"]["mypy"]["overrides"]
    assert any("boto3" in override["module"] for override in overrides)

    readme = files["README.md"]
    assert "## S3-compatible storage" in readme
    assert "STORAGE_BACKEND" in readme


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
    assert 'PostgresContainer("postgres:latest")' in conftest
    assert 'RedisContainer("redis:alpine")' in conftest
    assert 'os.environ.get("RUN_INTEGRATION") == "1"' in conftest
    assert "pytest.skip(SKIP_REASON)" in conftest

    integration = files["tests/integration/test_integration.py"]
    assert "pytestmark = pytest.mark.integration" in integration
    assert "get_connection_url()" in integration
    assert "client.ping() is True" in integration

    script = files["scripts/run_integration.sh"]
    assert "RUN_INTEGRATION" in script

    workflow = files[".github/workflows/integration.yml"]
    assert "workflow_dispatch:" in workflow
    assert "bash scripts/run_integration.sh" in workflow

    data = tomllib.loads(files["pyproject.toml"])
    assert "testcontainers[postgres]" in data["dependency-groups"]["dev"]
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


def test_mongodb_feature_renders_beanie_slice() -> None:
    spec = ProjectSpec(name="my-service", dependencies=frozenset({"mongodb"}))

    files = render_project(spec)

    assert "src/my_service/core/mongo.py" in files
    assert "src/my_service/models/document.py" in files
    assert "src/my_service/schemas/document.py" in files
    assert "src/my_service/services/documents.py" in files
    assert "src/my_service/api/routes/documents.py" in files
    assert "tests/test_documents.py" in files
    assert "src/my_service/db/session.py" not in files

    config = files["src/my_service/core/config.py"]
    assert 'mongodb_url: str = "mongodb://localhost:27017"' in config
    assert 'mongodb_db: str = "app"' in config

    env = files[".env.example"]
    assert "MONGODB_URL" in env
    assert "MONGODB_DB" in env

    models = files["src/my_service/models/__init__.py"]
    assert "from my_service.models.document import Document" in models
    assert '"Document"' in models

    routes = files["src/my_service/api/routes/__init__.py"]
    assert "from my_service.api.routes.documents import router as documents_router" in routes
    assert "api_router.include_router(documents_router)" in routes

    main = files["src/my_service/main.py"]
    assert "from my_service.core.mongo import close_mongo, init_mongo" in main
    assert "await init_mongo()" in main
    assert "await close_mongo()" in main

    mongo = files["src/my_service/core/mongo.py"]
    assert "async def init_mongo(client: AsyncIOMotorClient[Any] | None = None) -> None:" in mongo
    assert "await init_beanie(" in mongo
    assert "async def close_mongo() -> None:" in mongo

    data = tomllib.loads(files["pyproject.toml"])
    assert "beanie" in data["project"]["dependencies"]
    assert "motor" in data["project"]["dependencies"]
    assert "mongomock-motor" in data["dependency-groups"]["dev"]

    readme = files["README.md"]
    assert "## MongoDB and Beanie" in readme
    assert "mongodb://localhost:27017" in readme
    assert "tests use `mongomock-motor`" in readme


def test_mongodb_is_absent_by_default() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "src/my_service/core/mongo.py" not in files
    assert "src/my_service/models/document.py" not in files
    assert "src/my_service/services/documents.py" not in files
    assert "src/my_service/api/routes/documents.py" not in files
    assert "tests/test_documents.py" not in files
    assert ".env.example" not in files
    assert "## MongoDB and Beanie" not in files["README.md"]


def test_mongodb_renders_with_python_314() -> None:
    files = render_project(
        ProjectSpec(
            name="my-service",
            python="3.14",
            dependencies=frozenset({"mongodb"}),
        )
    )

    assert "src/my_service/core/mongo.py" in files


def test_sqlmodel_mysql_feature_renders_the_relational_slice() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlmodel", "alembic", "mysql"}),
    )

    files = render_project(spec)

    assert "Base = SQLModel" in files["src/my_service/db/base.py"]
    assert (
        "from sqlmodel.ext.asyncio.session import AsyncSession"
        in files["src/my_service/db/session.py"]
    )
    assert "class Item(SQLModel, table=True)" in files["src/my_service/models/item.py"]
    assert "await session.exec(statement)" in files["src/my_service/services/items.py"]
    assert (
        "from sqlmodel.ext.asyncio.session import AsyncSession"
        in files["src/my_service/api/dependencies.py"]
    )
    assert "create_session_factory(engine)" in files["src/my_service/main.py"]
    assert "class_=AsyncSession" in files["src/my_service/db/session.py"]
    assert "tests/test_items.py" in files
    assert "mysql+aiomysql://" in files["src/my_service/core/config.py"]
    assert "mysql+aiomysql://" in files[".env.example"]

    compose = files["docker-compose.yml"]
    assert "  db:" in compose
    assert "image: mysql:latest" in compose
    assert "mysql-data" in compose
    assert "postgres:latest" not in compose

    readme = files["README.md"]
    assert "## Database setup" in readme
    assert "MySQL/MariaDB" in readme

    dependencies = tomllib.loads(files["pyproject.toml"])["project"]["dependencies"]
    assert "sqlmodel" in dependencies
    assert "aiomysql" in dependencies
    assert "alembic" in dependencies


def test_graphql_feature_renders_schema_and_route() -> None:
    spec = ProjectSpec(name="my-service", dependencies=frozenset({"graphql"}))

    files = render_project(spec)

    assert "src/my_service/graphql/__init__.py" in files
    assert "src/my_service/graphql/schema.py" in files
    assert "tests/test_graphql.py" in files

    schema = files["src/my_service/graphql/schema.py"]
    assert "class Query:" in schema
    assert 'def hello(self, name: str = "world") -> str:' in schema
    assert "class Mutation:" in schema
    assert "def echo(self, message: str) -> str:" in schema

    main = files["src/my_service/main.py"]
    assert "from strawberry.fastapi import GraphQLRouter" in main
    assert "from my_service.graphql.schema import schema" in main
    assert 'app.include_router(GraphQLRouter(schema), prefix="/graphql")' in main

    data = tomllib.loads(files["pyproject.toml"])
    assert "strawberry-graphql[fastapi]" in data["project"]["dependencies"]

    readme = files["README.md"]
    assert "## GraphQL" in readme
    assert "/graphql" in readme


def test_graphql_is_absent_by_default() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    assert "src/my_service/graphql/__init__.py" not in files
    assert "src/my_service/graphql/schema.py" not in files
    assert "tests/test_graphql.py" not in files
    assert "GraphQLRouter" not in files["src/my_service/main.py"]
    assert "## GraphQL" not in files["README.md"]


def test_generated_app_compresses_large_responses() -> None:
    files = render_project(ProjectSpec(name="my-service"))

    main = files["src/my_service/main.py"]
    assert "from fastapi.middleware.gzip import GZipMiddleware" in main
    assert "app.add_middleware(GZipMiddleware, minimum_size=1024)" in main
    assert "content-encoding" in files["tests/test_health.py"]


def test_preview_lists_rendered_files() -> None:
    preview = build_preview(ProjectSpec(name="my-service"))

    assert preview.name == "my-service"
    assert any(file.path == "pyproject.toml" for file in preview.files)
    assert all(file.size > 0 for file in preview.files)
