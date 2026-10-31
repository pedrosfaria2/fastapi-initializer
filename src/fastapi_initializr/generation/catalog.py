"""Allowlisted dependency catalog and option metadata."""

from dataclasses import dataclass

from fastapi_initializr.generation.constants import (
    DEFAULT_FASTAPI_VERSION,
    DEFAULT_PYTHON_VERSION,
    SUPPORTED_FASTAPI_VERSIONS,
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
    conflicts: tuple[str, ...] = ()
    version_range: str | None = None
    packages: tuple[str, ...] = ()
    dev_packages: tuple[str, ...] = ()
    files: tuple[str, ...] = ()
    guide: str | None = None
    guide_title: str | None = None
    reference: str | None = None
    home: str | None = None


DEPENDENCIES: dict[str, Dependency] = {
    "sqlalchemy": Dependency(
        id="sqlalchemy",
        name="SQLAlchemy",
        description="Async SQLAlchemy session and SQLite driver.",
        group="Database",
        packages=("sqlalchemy[asyncio]>=2.1.6", "aiosqlite>=0.22.1"),
        files=(
            "src/{package}/db/base.py",
            "src/{package}/db/session.py",
            "src/{package}/api/dependencies.py",
        ),
        guide="https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html",
        guide_title="SQLAlchemy asyncio ORM",
        reference="https://docs.sqlalchemy.org/en/20/",
    ),
    "alembic": Dependency(
        id="alembic",
        name="Alembic",
        description="Database migrations for SQLAlchemy.",
        group="Database",
        requires=("sqlalchemy",),
        packages=("alembic>=1.20.1",),
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
        requires=("sqlalchemy",),
        packages=("asyncpg>=0.32.0",),
        guide="https://magicstack.github.io/asyncpg/current/usage.html",
        guide_title="asyncpg usage",
        reference="https://magicstack.github.io/asyncpg/current/",
    ),
    "redis": Dependency(
        id="redis",
        name="Redis",
        description="Async Redis client and cache settings.",
        group="Database",
        packages=("redis>=5.3.1",),
        files=("src/{package}/core/cache.py",),
        guide="https://redis.readthedocs.io/en/stable/",
        guide_title="Redis Python client",
        reference="https://redis.io/docs/latest/develop/clients/redis-py/",
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
        packages=("arq>=0.28.0",),
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
    "cors": Dependency(
        id="cors",
        name="CORS",
        description="Configurable CORS middleware.",
        group="Web",
        guide="https://fastapi.tiangolo.com/tutorial/cors/",
        guide_title="FastAPI CORS",
        reference="https://fastapi.tiangolo.com/tutorial/cors/",
    ),
    "static-templates": Dependency(
        id="static-templates",
        name="Static files and templates",
        description="Jinja2 templates, static assets, and a welcome page.",
        group="Web",
        packages=("jinja2>=3.1.6",),
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
        packages=("slowapi>=0.1.10",),
        files=(
            "src/{package}/core/rate_limit.py",
            "src/{package}/api/routes/limited.py",
        ),
        guide="https://slowapi.readthedocs.io/en/latest/",
        guide_title="SlowAPI documentation",
        reference="https://slowapi.readthedocs.io/en/latest/",
    ),
    "auth-jwt": Dependency(
        id="auth-jwt",
        name="JWT Authentication",
        description="JWT login, password hashing, and a protected route.",
        group="Security",
        requires=("sqlalchemy",),
        packages=(
            "pwdlib[argon2]>=0.3.1",
            "pyjwt>=2.15.1",
            "email-validator>=2.3.0",
        ),
        files=(
            "src/{package}/models/user.py",
            "src/{package}/schemas/user.py",
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
        packages=("aiosmtplib>=5.1.3", "jinja2>=3.1.6"),
        files=(
            "src/{package}/core/email.py",
            "src/{package}/services/auth_email.py",
            "src/{package}/api/routes/auth_email.py",
            "templates/email/password_reset.txt",
            "templates/email/verify_email.txt",
            "tests/test_email_auth.py",
        ),
        guide="https://aiosmtplib.readthedocs.io/en/stable/",
        guide_title="aiosmtplib documentation",
        reference="https://jinja.palletsprojects.com/en/stable/",
    ),
    "sentry": Dependency(
        id="sentry",
        name="Sentry",
        description="Sentry error reporting, disabled without a DSN.",
        group="Observability",
        packages=("sentry-sdk[fastapi]>=2.73.0",),
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
        packages=("prometheus-fastapi-instrumentator>=8.1.0",),
        guide="https://github.com/trallnag/prometheus-fastapi-instrumentator",
        guide_title="Prometheus FastAPI instrumentator",
        reference="https://prometheus.io/docs/introduction/overview/",
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
        dev_packages=("pre-commit>=4.7.0",),
        files=(".pre-commit-config.yaml",),
        guide="https://pre-commit.com/#quick-start",
        guide_title="pre-commit quick start",
        reference="https://pre-commit.com/",
    ),
}

GROUP_ORDER: tuple[str, ...] = (
    "Database",
    "Messaging",
    "Web",
    "Security",
    "Observability",
    "Operations",
)

_GENERATION_PARAMS = (
    "name,package,description,version,author,python,fastapi,baseDir,applicationName,dependencies"
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
    for group_name in GROUP_ORDER:
        values = [
            DependencyValue(
                id=dependency.id,
                name=dependency.name,
                description=dependency.description,
                requires=list(dependency.requires),
                conflicts=list(dependency.conflicts),
                version_range=dependency.version_range,
                packages=list(dependency.packages),
                dev_packages=list(dependency.dev_packages),
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
            "preview": Link(
                href=f"/preview{{?{_GENERATION_PARAMS}}}",
                templated=True,
            ),
            "dependencies": Link(
                href="/dependencies{?fastapiVersion}",
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
        fastapi=SelectOption(
            default=DEFAULT_FASTAPI_VERSION,
            values=[
                SelectValue(id=version, name=f"FastAPI {version}")
                for version in SUPPORTED_FASTAPI_VERSIONS
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


def resolved_dependencies(fastapi_version: str) -> dict[str, object]:
    """Return resolved coordinates for every dependency."""
    return {
        "fastapiVersion": fastapi_version,
        "dependencies": {
            dependency.id: {
                "packages": list(dependency.packages),
                "devPackages": list(dependency.dev_packages),
                "files": list(dependency.files),
            }
            for dependency in DEPENDENCIES.values()
        },
    }
