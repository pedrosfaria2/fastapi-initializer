"""Generate representative projects and run their real quality gates."""

import argparse
import io
import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

from fastapi_initializr.generation.spec import ProjectSpec
from fastapi_initializr.services.generator import generate_project

CASES: dict[str, ProjectSpec] = {
    "minimal": ProjectSpec(name="minimal-service"),
    "minimal-core": ProjectSpec(
        name="minimal-core-service",
        structure="minimal",
    ),
    "minimal-ops": ProjectSpec(
        name="minimal-ops-service",
        structure="minimal",
        dependencies=frozenset({"cors", "sentry", "prometheus", "opentelemetry", "docker", "ci"}),
    ),
    "unicode": ProjectSpec(
        name="unicode-service",
        application_name="Service 🚀",
    ),
    "database": ProjectSpec(
        name="database-service",
        dependencies=frozenset({"sqlalchemy", "alembic"}),
    ),
    "mongo": ProjectSpec(
        name="mongo-service",
        dependencies=frozenset({"mongodb"}),
    ),
    "sqlmodel": ProjectSpec(
        name="sqlmodel-service",
        dependencies=frozenset({"sqlmodel", "alembic"}),
    ),
    "mysql": ProjectSpec(
        name="mysql-service",
        dependencies=frozenset({"sqlalchemy", "mysql"}),
    ),
    "sqlmodel-mysql": ProjectSpec(
        name="sqlmodel-mysql-service",
        dependencies=frozenset({"sqlmodel", "mysql", "alembic"}),
    ),
    "feature": ProjectSpec(
        name="feature-service",
        structure="feature",
        dependencies=frozenset(
            {
                "sqlalchemy",
                "alembic",
                "auth-jwt",
                "email",
                "oauth2",
                "cors",
                "static-templates",
                "websockets",
                "graphql",
                "rate-limit",
                "uploads",
                "schemathesis",
            }
        ),
    ),
    "feature-mongo": ProjectSpec(
        name="feature-mongo-service",
        structure="feature",
        dependencies=frozenset({"mongodb", "cors"}),
    ),
    "contract": ProjectSpec(
        name="contract-service",
        dependencies=frozenset({"sqlalchemy", "schemathesis"}),
    ),
    "typescript": ProjectSpec(
        name="typescript-service",
        dependencies=frozenset({"typescript-client"}),
    ),
    "migration": ProjectSpec(
        name="migration-service",
        dependencies=frozenset({"sqlalchemy", "alembic", "auth-jwt", "email", "oauth2"}),
    ),
    "auth": ProjectSpec(
        name="auth-service",
        dependencies=frozenset({"sqlalchemy", "auth-jwt"}),
    ),
    "email": ProjectSpec(
        name="email-service",
        dependencies=frozenset({"sqlalchemy", "auth-jwt", "email"}),
    ),
    "oauth": ProjectSpec(
        name="oauth-service",
        dependencies=frozenset({"sqlalchemy", "auth-jwt", "oauth2"}),
    ),
    "otel": ProjectSpec(
        name="otel-service",
        dependencies=frozenset({"sqlalchemy", "redis", "opentelemetry"}),
    ),
    "web": ProjectSpec(
        name="web-service",
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
    ),
    "worker": ProjectSpec(
        name="worker-service",
        dependencies=frozenset({"redis", "arq", "cache"}),
    ),
    "celery": ProjectSpec(
        name="celery-service",
        dependencies=frozenset({"celery", "rabbitmq"}),
    ),
    "celery-redis": ProjectSpec(
        name="celery-redis-service",
        dependencies=frozenset({"celery", "redis"}),
    ),
    "graphql": ProjectSpec(
        name="graphql-service",
        dependencies=frozenset({"graphql"}),
    ),
    "operations": ProjectSpec(
        name="operations-service",
        dependencies=frozenset({"docker", "compose", "ci", "pre-commit", "makefile"}),
    ),
    "uploads": ProjectSpec(
        name="uploads-service",
        dependencies=frozenset({"sqlalchemy", "auth-jwt", "uploads", "s3"}),
    ),
    "deploy": ProjectSpec(
        name="deploy-service",
        dependencies=frozenset(
            {
                "kubernetes",
                "ci-gitlab",
                "ci-bitbucket",
                "security-scan",
                "ci",
                "pre-commit",
                "docker",
                "compose",
            }
        ),
    ),
    "integration": ProjectSpec(
        name="integration-service",
        dependencies=frozenset({"sqlalchemy", "postgres", "redis", "testcontainers"}),
    ),
    "full": ProjectSpec(
        name="full-service",
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
                "graphql",
                "rate-limit",
                "uploads",
                "s3",
                "schemathesis",
                "typescript-client",
                "testcontainers",
                "docker",
                "compose",
                "ci",
                "pre-commit",
                "makefile",
                "security-scan",
                "kubernetes",
                "ci-gitlab",
                "ci-bitbucket",
            }
        ),
    ),
}

GATES: tuple[tuple[str, ...], ...] = (
    ("uv", "sync"),
    ("uv", "run", "ruff", "format", "--check", "."),
    ("uv", "run", "ruff", "check", "."),
    ("uv", "run", "mypy", "src"),
    ("uv", "run", "pyright", "src"),
    ("uv", "run", "pytest", "-q"),
)

_MIGRATION_CHECK = """import sqlite3; connection=sqlite3.connect('app.db'); tables={row[0] for row in connection.execute("select name from sqlite_master where type='table'")}; assert {'alembic_version', 'items', 'users'} <= tables, tables; columns={row[1] for row in connection.execute('pragma table_info(users)')}; assert {'token_version', 'oauth_provider', 'oauth_subject', 'is_verified', 'password_reset_version', 'email_verification_version'} <= columns, columns"""
MIGRATION_GATES: tuple[tuple[str, ...], ...] = (
    ("uv", "run", "alembic", "upgrade", "head"),
    ("uv", "run", "python", "-c", _MIGRATION_CHECK),
)


def run(command: tuple[str, ...], cwd: Path) -> None:
    """Run one command and fail immediately on error."""
    print(f"$ {' '.join(command)}", flush=True)
    environment = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
    environment.update({"UV_NO_PROGRESS": "1", "UV_LINK_MODE": "copy"})
    subprocess.run(
        command,
        cwd=cwd,
        check=True,
        env=environment,
    )


def extract_project(spec: ProjectSpec, root: Path) -> Path:
    """Generate a project and extract it under a case directory."""
    generated = generate_project(spec)
    case_dir = root / spec.name
    case_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(generated.content)) as archive:
        archive.extractall(case_dir)
    return case_dir / spec.name


def check_case(name: str, spec: ProjectSpec, root: Path) -> None:
    """Generate one case and run every generated-project gate."""
    print(f"===== {name}: {spec.name}", flush=True)
    project_dir = extract_project(spec, root / name)
    for command in GATES:
        run(command, project_dir)
    if name == "migration":
        for command in MIGRATION_GATES:
            run(command, project_dir)
    print(f"===== {name}: PASS", flush=True)


def main() -> None:
    """Run the selected generated-project matrix."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        choices=(*CASES, "all"),
        default="all",
        help="Case to run (default: all).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Keep generated projects under this directory.",
    )
    args = parser.parse_args()

    selected = CASES if args.case == "all" else {args.case: CASES[args.case]}
    if args.output is not None:
        args.output.mkdir(parents=True, exist_ok=True)
        for name, spec in selected.items():
            check_case(name, spec, args.output)
        print(f"Generated projects kept in {args.output}", flush=True)
        return

    with tempfile.TemporaryDirectory(prefix="fastapi-initializr-") as temporary:
        root = Path(temporary)
        for name, spec in selected.items():
            check_case(name, spec, root)


if __name__ == "__main__":
    main()
