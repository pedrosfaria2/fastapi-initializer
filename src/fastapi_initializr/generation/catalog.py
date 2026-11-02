"""Allowlisted dependency catalog and option metadata."""

from dataclasses import dataclass

from fastapi_initializr.generation.constants import (
    DEFAULT_PYTHON_VERSION,
    DEFAULT_STRUCTURE,
    STRUCTURES,
    SUPPORTED_PYTHON_VERSIONS,
)
from fastapi_initializr.schemas.metadata import (
    ActionOption,
    ActionValue,
    DependencyGroup,
    DependencyValue,
    Link,
    Metadata,
    MultiSelectOption,
    PresetOption,
    PresetValue,
    ProjectOptions,
    SelectOption,
    SelectValue,
    TextOption,
)


@dataclass(frozen=True, slots=True)
class Dependency:
    """A selectable project feature."""

    id: str
    name: str
    description: str
    group: str
    requires: tuple[str, ...] = ()
    requires_capabilities: tuple[str, ...] = ()
    provides: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    packages: tuple[str, ...] = ()
    dev_packages: tuple[str, ...] = ()
    files: tuple[str, ...] = ()
    guide: str | None = None
    guide_title: str | None = None
    reference: str | None = None
    home: str | None = None
    plugin: bool = False


DEPENDENCIES: dict[str, Dependency] = {
    "sqlalchemy": Dependency(
        id="sqlalchemy",
        name="SQLAlchemy",
        description="Async SQLAlchemy session and SQLite driver.",
        group="Database",
        provides=("orm",),
        conflicts=("mongodb", "sqlmodel"),
        packages=("sqlalchemy[asyncio]", "aiosqlite"),
        files=(
            "src/{package}/db/base.py",
            "src/{package}/db/session.py",
            "src/{package}/api/dependencies.py",
        ),
        guide="https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html",
        guide_title="SQLAlchemy asyncio ORM",
        reference="https://docs.sqlalchemy.org/en/20/",
    ),
    "sqlmodel": Dependency(
        id="sqlmodel",
        name="SQLModel",
        description="SQLModel ORM on SQLAlchemy with async sessions.",
        group="Database",
        provides=("orm",),
        conflicts=("sqlalchemy", "mongodb"),
        packages=("sqlmodel", "sqlalchemy[asyncio]", "aiosqlite"),
        files=(
            "src/{package}/db/base.py",
            "src/{package}/db/session.py",
            "src/{package}/api/dependencies.py",
            "src/{package}/models/item.py",
            "src/{package}/schemas/item.py",
            "src/{package}/services/items.py",
            "src/{package}/api/routes/items.py",
        ),
        guide="https://sqlmodel.tiangolo.com/tutorial/fastapi/",
        guide_title="SQLModel with FastAPI",
        reference="https://sqlmodel.tiangolo.com/",
    ),
    "alembic": Dependency(
        id="alembic",
        name="Alembic",
        description="Database migrations for SQLAlchemy and SQLModel.",
        group="Database",
        requires_capabilities=("orm",),
        packages=("alembic",),
        files=(
            "alembic.ini",
            "migrations/env.py",
            "migrations/script.py.mako",
            "migrations/versions/.gitkeep",
        ),
        guide="https://alembic.sqlalchemy.org/en/latest/tutorial.html",
        guide_title="Alembic tutorial",
        reference="https://alembic.sqlalchemy.org/en/latest/",
    ),
    "postgres": Dependency(
        id="postgres",
        name="PostgreSQL",
        description="Async PostgreSQL driver.",
        group="Database",
        requires_capabilities=("orm",),
        conflicts=("mysql",),
        packages=("asyncpg",),
        guide="https://magicstack.github.io/asyncpg/current/usage.html",
        guide_title="asyncpg usage",
        reference="https://magicstack.github.io/asyncpg/current/",
    ),
    "mysql": Dependency(
        id="mysql",
        name="MySQL/MariaDB",
        description="Async MySQL and MariaDB driver.",
        group="Database",
        requires_capabilities=("orm",),
        conflicts=("postgres",),
        packages=("aiomysql",),
        guide="https://aiomysql.readthedocs.io/en/stable/",
        guide_title="aiomysql documentation",
        reference="https://docs.sqlalchemy.org/en/20/dialects/mysql.html",
    ),
    "redis": Dependency(
        id="redis",
        name="Redis",
        description="Async Redis client and cache settings.",
        group="Database",
        provides=("broker",),
        packages=("redis",),
        files=("src/{package}/core/cache.py",),
        guide="https://redis.readthedocs.io/en/stable/",
        guide_title="Redis Python client",
        reference="https://redis.io/docs/latest/develop/clients/redis-py/",
    ),
    "mongodb": Dependency(
        id="mongodb",
        name="MongoDB with Beanie",
        description="Async MongoDB documents through Beanie and Motor.",
        group="Database",
        conflicts=("sqlalchemy", "sqlmodel"),
        packages=("beanie", "motor"),
        dev_packages=("mongomock-motor",),
        files=(
            "src/{package}/core/mongo.py",
            "src/{package}/models/document.py",
            "src/{package}/schemas/document.py",
            "src/{package}/services/documents.py",
            "src/{package}/api/routes/documents.py",
            "tests/test_documents.py",
        ),
        guide="https://beanie-odm.dev/tutorial/initialization/",
        guide_title="Beanie initialization",
        reference="https://beanie-odm.dev/",
    ),
    "cache": Dependency(
        id="cache",
        name="Redis cache helpers",
        description="Typed cache-aside helpers with JSON serialization.",
        group="Database",
        requires=("redis",),
        files=(
            "src/{package}/core/cache_helpers.py",
            "tests/test_cache_helpers.py",
        ),
        guide="https://redis.io/docs/latest/develop/clients/redis-py/",
        guide_title="Redis Python client",
        reference="https://redis.io/docs/latest/develop/clients/redis-py/",
    ),
    "arq": Dependency(
        id="arq",
        name="ARQ background jobs",
        description="Redis-backed background job worker.",
        group="Messaging",
        requires=("redis",),
        conflicts=("celery",),
        packages=("arq",),
        files=(
            "src/{package}/worker.py",
            "src/{package}/tasks/__init__.py",
            "src/{package}/tasks/example.py",
            "tests/test_worker.py",
        ),
        guide="https://arq-docs.helpmanual.io/",
        guide_title="ARQ documentation",
        reference="https://github.com/python-arq/arq",
    ),
    "rabbitmq": Dependency(
        id="rabbitmq",
        name="RabbitMQ",
        description="RabbitMQ broker for Celery workers.",
        group="Messaging",
        provides=("broker",),
        guide="https://www.rabbitmq.com/tutorials",
        guide_title="RabbitMQ tutorials",
        reference="https://www.rabbitmq.com/docs",
    ),
    "celery": Dependency(
        id="celery",
        name="Celery workers",
        description="Celery worker and an example task.",
        group="Messaging",
        requires_capabilities=("broker",),
        conflicts=("arq",),
        packages=("celery",),
        files=(
            "src/{package}/worker.py",
            "tests/test_worker.py",
        ),
        guide="https://docs.celeryq.dev/en/stable/getting-started/first-steps-with-celery.html",
        guide_title="Celery first steps",
        reference="https://docs.celeryq.dev/en/stable/",
    ),
    "cors": Dependency(
        id="cors",
        name="CORS",
        description="Configurable CORS middleware.",
        group="Web",
        guide="https://fastapi.tiangolo.com/tutorial/cors/",
        guide_title="FastAPI CORS",
        reference="https://fastapi.tiangolo.com/tutorial/cors/",
    ),
    "typescript-client": Dependency(
        id="typescript-client",
        name="TypeScript API client",
        description="Typed fetch client generated from the app's OpenAPI schema.",
        group="Web",
        files=(
            "client/package.json",
            "client/tsconfig.json",
            "client/export_openapi.py",
            "client/src/api/client.ts",
            "client/src/api/schema.d.ts",
        ),
        guide="https://openapi-ts.dev/",
        guide_title="OpenAPI TypeScript",
        reference="https://github.com/openapi-ts/openapi-typescript",
    ),
    "graphql": Dependency(
        id="graphql",
        name="GraphQL with Strawberry",
        description="Strawberry GraphQL schema mounted at /graphql.",
        group="Web",
        packages=("strawberry-graphql[fastapi]",),
        files=(
            "src/{package}/graphql/__init__.py",
            "src/{package}/graphql/schema.py",
            "tests/test_graphql.py",
        ),
        guide="https://strawberry.rocks/docs/integrations/fastapi",
        guide_title="Strawberry FastAPI integration",
        reference="https://strawberry.rocks/docs/",
    ),
    "static-templates": Dependency(
        id="static-templates",
        name="Static files and templates",
        description="Jinja2 templates, static assets, and a welcome page.",
        group="Web",
        packages=("jinja2",),
        files=(
            "src/{package}/api/routes/pages.py",
            "templates/index.html",
            "static/style.css",
        ),
        guide="https://fastapi.tiangolo.com/advanced/templates/",
        guide_title="FastAPI templates",
        reference="https://www.starlette.io/templates/",
    ),
    "websockets": Dependency(
        id="websockets",
        name="WebSockets",
        description="WebSocket echo endpoint.",
        group="Web",
        files=("src/{package}/api/routes/ws.py",),
        guide="https://fastapi.tiangolo.com/advanced/websockets/",
        guide_title="FastAPI WebSockets",
        reference="https://fastapi.tiangolo.com/advanced/websockets/",
    ),
    "rate-limit": Dependency(
        id="rate-limit",
        name="Rate limiting",
        description="SlowAPI limiter middleware and an example route.",
        group="Web",
        packages=("slowapi",),
        files=(
            "src/{package}/core/rate_limit.py",
            "src/{package}/api/routes/limited.py",
        ),
        guide="https://slowapi.readthedocs.io/en/latest/",
        guide_title="SlowAPI documentation",
        reference="https://slowapi.readthedocs.io/en/latest/",
    ),
    "uploads": Dependency(
        id="uploads",
        name="File uploads",
        description="Authenticated local file storage with upload, download, and delete endpoints.",
        group="Web",
        requires=("auth-jwt",),
        files=(
            "src/{package}/core/storage.py",
            "src/{package}/api/routes/uploads.py",
            "tests/test_uploads.py",
        ),
        guide="https://fastapi.tiangolo.com/tutorial/request-files/",
        guide_title="FastAPI file uploads",
        reference="https://fastapi.tiangolo.com/tutorial/request-files/",
    ),
    "auth-jwt": Dependency(
        id="auth-jwt",
        name="JWT Authentication",
        description="JWT login, password hashing, and a protected route.",
        group="Security",
        requires=("sqlalchemy",),
        packages=(
            "pwdlib[argon2]",
            "pyjwt",
            "email-validator",
        ),
        files=(
            "src/{package}/models/user.py",
            "src/{package}/schemas/user.py",
            "src/{package}/core/auth_throttle.py",
            "src/{package}/core/security.py",
            "src/{package}/services/auth.py",
            "src/{package}/api/routes/auth.py",
            "tests/test_auth.py",
        ),
        guide="https://frankie567.github.io/pwdlib/",
        guide_title="pwdlib password hashing",
        reference="https://pyjwt.readthedocs.io/",
    ),
    "email": Dependency(
        id="email",
        name="Email + password reset",
        description="Email backends, password reset, and account verification.",
        group="Security",
        requires=("auth-jwt",),
        packages=("aiosmtplib", "jinja2"),
        files=(
            "src/{package}/core/email.py",
            "src/{package}/services/auth_email.py",
            "src/{package}/api/routes/auth_email.py",
            "templates/email/password_reset.txt",
            "templates/email/verify_email.txt",
            "templates/email/password_changed.txt",
            "tests/test_email_auth.py",
        ),
        guide="https://aiosmtplib.readthedocs.io/en/stable/",
        guide_title="aiosmtplib documentation",
        reference="https://jinja.palletsprojects.com/en/stable/",
    ),
    "oauth2": Dependency(
        id="oauth2",
        name="OAuth2/OIDC social login",
        description="Google and GitHub login through Authlib with local account linking.",
        group="Security",
        requires=("auth-jwt",),
        packages=("authlib", "itsdangerous"),
        files=(
            "src/{package}/core/oauth.py",
            "src/{package}/services/oauth.py",
            "src/{package}/api/routes/oauth.py",
            "tests/test_oauth.py",
        ),
        guide="https://docs.authlib.org/en/latest/client/starlette.html",
        guide_title="Authlib Starlette integration",
        reference="https://docs.authlib.org/en/latest/",
    ),
    "sentry": Dependency(
        id="sentry",
        name="Sentry",
        description="Sentry error reporting, disabled without a DSN.",
        group="Observability",
        packages=("sentry-sdk[fastapi]",),
        files=("src/{package}/core/observability.py",),
        guide="https://docs.sentry.io/platforms/python/integrations/fastapi/",
        guide_title="Sentry FastAPI integration",
        reference="https://docs.sentry.io/platforms/python/",
    ),
    "prometheus": Dependency(
        id="prometheus",
        name="Prometheus metrics",
        description="Prometheus instrumentation and a /metrics endpoint.",
        group="Observability",
        packages=("prometheus-fastapi-instrumentator",),
        guide="https://github.com/trallnag/prometheus-fastapi-instrumentator",
        guide_title="Prometheus FastAPI instrumentator",
        reference="https://prometheus.io/docs/introduction/overview/",
    ),
    "opentelemetry": Dependency(
        id="opentelemetry",
        name="OpenTelemetry tracing",
        description="OTLP trace export with FastAPI, SQLAlchemy, and Redis instrumentation.",
        group="Observability",
        packages=(
            "opentelemetry-sdk",
            "opentelemetry-exporter-otlp",
            "opentelemetry-instrumentation-fastapi",
            "opentelemetry-instrumentation-sqlalchemy",
            "opentelemetry-instrumentation-redis",
        ),
        files=(
            "src/{package}/core/tracing.py",
            "tests/test_tracing.py",
        ),
        guide="https://opentelemetry.io/docs/languages/python/instrumentation/",
        guide_title="OpenTelemetry Python instrumentation",
        reference="https://opentelemetry.io/docs/",
    ),
    "docker": Dependency(
        id="docker",
        name="Docker",
        description="Dockerfile and .dockerignore.",
        group="Operations",
        files=("Dockerfile", ".dockerignore"),
        guide="https://docs.docker.com/language/python/",
        guide_title="Docker for Python",
        reference="https://docs.docker.com/language/python/",
    ),
    "compose": Dependency(
        id="compose",
        name="Docker Compose",
        description="Compose stack with PostgreSQL and Redis where selected.",
        group="Operations",
        files=("docker-compose.yml", "Dockerfile", ".dockerignore"),
        guide="https://docs.docker.com/compose/",
        guide_title="Docker Compose",
        reference="https://docs.docker.com/compose/",
    ),
    "s3": Dependency(
        id="s3",
        name="S3-compatible storage",
        description="Store uploads in an S3-compatible bucket through boto3.",
        group="Operations",
        requires=("uploads",),
        packages=("boto3",),
        dev_packages=("moto[s3]",),
        files=(
            "src/{package}/core/storage_s3.py",
            "tests/test_storage_s3.py",
        ),
        guide="https://boto3.amazonaws.com/v1/documentation/api/latest/guide/s3.html",
        guide_title="boto3 S3 guide",
        reference="https://boto3.amazonaws.com/v1/documentation/api/latest/index.html",
    ),
    "makefile": Dependency(
        id="makefile",
        name="Makefile",
        description="Common sync, run, test, lint, typecheck, and format targets.",
        group="Operations",
        files=("Makefile",),
        guide="https://www.gnu.org/software/make/manual/make.html",
        guide_title="GNU Make manual",
        reference="https://www.gnu.org/software/make/",
    ),
    "ci": Dependency(
        id="ci",
        name="GitHub Actions",
        description="CI workflow running Ruff, mypy, pyright and pytest.",
        group="Operations",
        files=(".github/workflows/ci.yml",),
        guide="https://docs.github.com/en/actions/quickstart",
        guide_title="GitHub Actions quickstart",
        reference="https://docs.github.com/en/actions",
    ),
    "pre-commit": Dependency(
        id="pre-commit",
        name="pre-commit",
        description="Ruff, mypy and pyright hooks.",
        group="Operations",
        dev_packages=("pre-commit",),
        files=(".pre-commit-config.yaml",),
        guide="https://pre-commit.com/#quick-start",
        guide_title="pre-commit quick start",
        reference="https://pre-commit.com/",
    ),
    "security-scan": Dependency(
        id="security-scan",
        name="Security scanning + SBOM",
        description="Dependency audit, static analysis, secret scanning, and SBOM generation.",
        group="Operations",
        dev_packages=(
            "pip-audit",
            "bandit",
            "detect-secrets",
            "cyclonedx-bom",
        ),
        files=(
            "scripts/security.sh",
            "tests/test_security_tooling.py",
        ),
        guide="https://github.com/pypa/pip-audit",
        guide_title="pip-audit documentation",
        reference="https://cyclonedx.org/tool-center/",
    ),
    "kubernetes": Dependency(
        id="kubernetes",
        name="Kubernetes manifests",
        description="Deployment, service, ConfigMap, and ingress manifests.",
        group="Operations",
        dev_packages=("pyyaml",),
        files=(
            "k8s/deployment.yaml",
            "k8s/service.yaml",
            "k8s/configmap.yaml",
            "k8s/ingress.yaml",
            "tests/test_kubernetes.py",
        ),
        guide="https://kubernetes.io/docs/concepts/workloads/controllers/deployment/",
        guide_title="Kubernetes Deployments",
        reference="https://kubernetes.io/docs/home/",
    ),
    "ci-gitlab": Dependency(
        id="ci-gitlab",
        name="GitLab CI",
        description="GitLab pipeline running Ruff, mypy, pyright, and pytest.",
        group="Operations",
        files=(".gitlab-ci.yml",),
        guide="https://docs.gitlab.com/ci/quick_start/",
        guide_title="GitLab CI/CD quick start",
        reference="https://docs.gitlab.com/ci/",
    ),
    "ci-bitbucket": Dependency(
        id="ci-bitbucket",
        name="Bitbucket Pipelines",
        description="Bitbucket pipeline running Ruff, mypy, pyright, and pytest.",
        group="Operations",
        files=("bitbucket-pipelines.yml",),
        guide="https://support.atlassian.com/bitbucket-cloud/docs/get-started-with-bitbucket-pipelines/",
        guide_title="Bitbucket Pipelines quick start",
        reference="https://support.atlassian.com/bitbucket-cloud/docs/configure-bitbucket-pipelinesyml/",
    ),
    "testcontainers": Dependency(
        id="testcontainers",
        name="Testcontainers integration tests",
        description="Docker-backed PostgreSQL and Redis integration tests.",
        group="Testing",
        requires=("postgres", "redis"),
        dev_packages=("testcontainers[postgres]",),
        files=(
            "tests/integration/conftest.py",
            "tests/integration/test_integration.py",
            "scripts/run_integration.sh",
            ".github/workflows/integration.yml",
        ),
        guide="https://testcontainers-python.readthedocs.io/en/latest/",
        guide_title="Testcontainers for Python",
        reference="https://testcontainers.com/",
    ),
    "schemathesis": Dependency(
        id="schemathesis",
        name="Schemathesis contract tests",
        description="OpenAPI property-based contract tests.",
        group="Testing",
        dev_packages=("schemathesis",),
        files=("tests/test_contract.py",),
        guide="https://schemathesis.readthedocs.io/en/stable/tutorials/pytest/",
        guide_title="Schemathesis pytest tutorial",
        reference="https://schemathesis.readthedocs.io/en/stable/",
    ),
}

HELP_STEPS: dict[str, tuple[str, ...]] = {
    "sqlalchemy": ("CRUD endpoints are available at `/items`.",),
    "sqlmodel": ("CRUD endpoints are available at `/items`.",),
    "alembic": (
        "Apply migrations with `uv run alembic upgrade head`.",
        'Create one with `uv run alembic revision --autogenerate -m "describe the change"`.',
    ),
    "postgres": ("Set `DATABASE_URL` in `.env`; Compose starts PostgreSQL.",),
    "mysql": ("Set `DATABASE_URL` in `.env`; Compose starts MySQL.",),
    "mongodb": ("Set `MONGODB_URL` and `MONGODB_DB` in `.env`.",),
    "redis": ("Set `REDIS_URL` in `.env`.",),
    "cache": ("Use the cache helpers in `core/cache_helpers.py`.",),
    "arq": ("Start the worker with `uv run arq {package}.worker.WorkerSettings`.",),
    "rabbitmq": ("Compose starts RabbitMQ; the management UI is on port 15672.",),
    "celery": (
        "Start the worker with `uv run celery -A {package}.worker.celery_app worker --loglevel=info`.",
        "The example task is `{package}.worker.add`.",
    ),
    "auth-jwt": (
        "Change `SECRET_KEY` in `.env` before deploying.",
        "Endpoints: `/auth/register`, `/auth/login`, and `/auth/me`.",
    ),
    "email": ("Configure `SMTP_*` in `.env`; the console backend is the default.",),
    "oauth2": ("Configure `GOOGLE_*` and `GITHUB_*` in `.env`.",),
    "cors": ("Set `CORS_ORIGINS` in `.env`.",),
    "static-templates": ("The welcome page is at `/`.",),
    "websockets": ("The WebSocket echo endpoint is at `/ws`.",),
    "rate-limit": ("The limiter is wired in `core/rate_limit.py`.",),
    "uploads": ("Uploads require a bearer token; set `UPLOAD_DIR` and `MAX_UPLOAD_BYTES`.",),
    "graphql": ("The GraphQL endpoint is at `/graphql`.",),
    "s3": ("Set `STORAGE_BACKEND=s3` and the `S3_*` variables in `.env`.",),
    "testcontainers": (
        "Run integration tests with `RUN_INTEGRATION=1 bash scripts/run_integration.sh`.",
    ),
    "sentry": ("Set `SENTRY_DSN` to enable error reporting.",),
    "prometheus": ("Metrics are exposed at `/metrics`.",),
    "opentelemetry": ("Set `OTEL_EXPORTER_OTLP_ENDPOINT` to export traces.",),
    "docker": ("Build the image with `docker build -t <name> .`.",),
    "compose": ("Start the stack with `docker compose up --build`.",),
    "makefile": ("Common targets: `make sync`, `make run`, `make test`, `make lint`.",),
    "ci": ("GitHub Actions workflow: `.github/workflows/ci.yml`.",),
    "ci-gitlab": ("GitLab pipeline: `.gitlab-ci.yml`.",),
    "ci-bitbucket": ("Bitbucket pipeline: `bitbucket-pipelines.yml`.",),
    "security-scan": ("Run `bash scripts/security.sh`.",),
    "kubernetes": ("Apply manifests with `kubectl apply -f k8s/`.",),
    "pre-commit": ("Install hooks with `uv run pre-commit install`.",),
    "schemathesis": ("Run contract tests with `uv run pytest tests/test_contract.py`.",),
    "typescript-client": (
        "Generate types with `cd client && npm install && npm run generate:api`.",
    ),
}


GROUP_ORDER: tuple[str, ...] = (
    "Database",
    "Messaging",
    "Web",
    "Security",
    "Observability",
    "Operations",
    "Testing",
)


@dataclass(frozen=True, slots=True)
class PluginFile:
    """An inline template contributed by a plugin feature."""

    feature_id: str
    path: str
    template: str


_PLUGIN_FILES: list[PluginFile] = []


def register_plugin(dependency: Dependency, files: tuple[PluginFile, ...]) -> None:
    """Register a validated third-party feature in the active catalog."""
    if dependency.id in DEPENDENCIES:
        raise ValueError(f"Dependency id '{dependency.id}' already exists.")
    if any(file.feature_id != dependency.id for file in files):
        raise ValueError("Plugin files must belong to their feature.")
    DEPENDENCIES[dependency.id] = dependency
    _PLUGIN_FILES.extend(files)


def plugin_files() -> tuple[PluginFile, ...]:
    """Return the registered plugin templates."""
    return tuple(_PLUGIN_FILES)


def clear_plugins() -> None:
    """Remove every registered plugin feature."""
    for dependency in [item for item in DEPENDENCIES.values() if item.plugin]:
        del DEPENDENCIES[dependency.id]
    _PLUGIN_FILES.clear()


def plugin_group_names() -> tuple[str, ...]:
    """Return plugin groups in registration order."""
    names: list[str] = []
    for dependency in DEPENDENCIES.values():
        if dependency.group not in GROUP_ORDER and dependency.group not in names:
            names.append(dependency.group)
    return tuple(names)


@dataclass(frozen=True, slots=True)
class Preset:
    """A named dependency selection."""

    id: str
    name: str
    description: str
    dependencies: tuple[str, ...]


_FULL_PRESET_IDS = tuple(
    dependency_id
    for dependency_id in DEPENDENCIES
    if dependency_id not in {"mongodb", "sqlmodel", "mysql", "celery", "rabbitmq"}
)

PRESETS: tuple[Preset, ...] = (
    Preset(
        id="custom",
        name="Custom",
        description="Choose dependencies individually.",
        dependencies=(),
    ),
    Preset(
        id="api",
        name="API only",
        description="Core FastAPI service with health, readiness, and request IDs.",
        dependencies=(),
    ),
    Preset(
        id="db-auth",
        name="Database + auth",
        description="SQLAlchemy CRUD, Alembic migrations, JWT auth, and CORS.",
        dependencies=("sqlalchemy", "alembic", "auth-jwt", "cors"),
    ),
    Preset(
        id="worker",
        name="Redis worker",
        description="Redis client, cache helpers, and an ARQ background worker.",
        dependencies=("redis", "cache", "arq"),
    ),
    Preset(
        id="full",
        name="Full stack",
        description="Every compatible feature; MongoDB is excluded because it conflicts.",
        dependencies=_FULL_PRESET_IDS,
    ),
)

PRESETS_BY_ID: dict[str, Preset] = {preset.id: preset for preset in PRESETS}

_GENERATION_PARAMS = (
    "name,package,description,version,author,structure,python,preset,"
    "baseDir,applicationName,dependencies"
)


def _dependency_links(dependency: Dependency) -> dict[str, Link]:
    links: dict[str, Link] = {}
    if dependency.guide:
        links["guide"] = Link(
            href=dependency.guide,
            title=dependency.guide_title,
        )
    if dependency.reference:
        links["reference"] = Link(href=dependency.reference)
    if dependency.home:
        links["home"] = Link(href=dependency.home)
    return links


def metadata() -> Metadata:
    """Return the option catalog used by the API and UI."""
    groups: list[DependencyGroup] = []
    for group_name in (*GROUP_ORDER, *plugin_group_names()):
        values = [
            DependencyValue(
                id=dependency.id,
                name=dependency.name,
                description=dependency.description,
                requires=list(dependency.requires),
                requires_capabilities=list(dependency.requires_capabilities),
                provides=list(dependency.provides),
                conflicts=list(dependency.conflicts),
                packages=list(dependency.packages),
                dev_packages=list(dependency.dev_packages),
                help=list(HELP_STEPS.get(dependency.id, ())),
                files=list(dependency.files),
                links=_dependency_links(dependency),
            )
            for dependency in DEPENDENCIES.values()
            if dependency.group == group_name
        ]
        groups.append(DependencyGroup(name=group_name, values=values))

    return Metadata(
        links={
            "starter.zip": Link(
                href=f"/starter.zip{{?{_GENERATION_PARAMS}}}",
                templated=True,
            ),
            "starter.tgz": Link(
                href=f"/starter.tgz{{?{_GENERATION_PARAMS}}}",
                templated=True,
            ),
            "pyproject.toml": Link(
                href=f"/pyproject.toml{{?{_GENERATION_PARAMS}}}",
                templated=True,
            ),
            "requirements.txt": Link(
                href=f"/requirements.txt{{?{_GENERATION_PARAMS}}}",
                templated=True,
            ),
            "preview": Link(
                href=f"/preview{{?{_GENERATION_PARAMS}}}",
                templated=True,
            ),
            "dependencies": Link(href="/dependencies"),
            "compatibility": Link(
                href="/compatibility{?dependencies}",
                templated=True,
            ),
        },
        type=ActionOption(
            default="uv-project",
            values=[
                ActionValue(
                    id="uv-project",
                    name="uv project",
                    action="/starter.zip",
                    tags={"build": "uv", "format": "project"},
                )
            ],
        ),
        language=SelectOption(
            default="python",
            values=[SelectValue(id="python", name="Python")],
        ),
        structure=SelectOption(
            default=DEFAULT_STRUCTURE,
            values=[
                SelectValue(
                    id=structure,
                    name=structure.capitalize(),
                )
                for structure in STRUCTURES
            ],
        ),
        python=SelectOption(
            default=DEFAULT_PYTHON_VERSION,
            values=[
                SelectValue(id=version, name=f"Python {version}")
                for version in SUPPORTED_PYTHON_VERSIONS
            ],
        ),
        base_dir=TextOption(default="", max_length=64),
        application_name=TextOption(default="", max_length=100),
        preset=PresetOption(
            default="custom",
            values=[
                PresetValue(
                    id=preset.id,
                    name=preset.name,
                    dependencies=list(preset.dependencies),
                )
                for preset in PRESETS
            ],
        ),
        project=ProjectOptions(
            name=TextOption(default="my-service", max_length=64),
            package=TextOption(default="my_service", max_length=64),
            description=TextOption(default="A FastAPI service", max_length=200),
            version=TextOption(default="0.1.0", max_length=32),
            author=TextOption(default="", max_length=100),
        ),
        dependencies=MultiSelectOption(groups=groups),
    )


def resolve_packages(dependencies: frozenset[str]) -> tuple[list[str], list[str]]:
    """Return runtime and development packages for the selected features."""
    packages: set[str] = set()
    dev_packages: set[str] = set()
    for dependency_id in dependencies:
        dependency = DEPENDENCIES[dependency_id]
        packages.update(dependency.packages)
        dev_packages.update(dependency.dev_packages)
    return sorted(packages), sorted(dev_packages)


def dependency_catalog() -> dict[str, object]:
    """Return package names and files for every dependency."""
    return {
        "dependencies": {
            dependency.id: {
                "packages": list(dependency.packages),
                "devPackages": list(dependency.dev_packages),
                "files": list(dependency.files),
            }
            for dependency in DEPENDENCIES.values()
        },
    }
