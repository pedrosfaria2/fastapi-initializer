"""Render generated project files from templates."""

import ast
import json
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from fastapi_initializr.generation.catalog import (
    DEPENDENCIES,
    HELP_STEPS,
    plugin_files,
    resolve_packages,
)
from fastapi_initializr.generation.constants import core_dev_packages, core_packages
from fastapi_initializr.generation.layout import Layout
from fastapi_initializr.generation.manifest import MANIFEST_NAME, render_manifest
from fastapi_initializr.generation.spec import ProjectSpec

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "project"


def _python_string(value: object) -> str:
    """Return a valid Python string literal for a user-provided value."""
    encoded = json.dumps(str(value), ensure_ascii=False)
    return encoded.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")


_ENVIRONMENT = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    undefined=StrictUndefined,
    autoescape=select_autoescape(
        enabled_extensions=("html", "htm", "xml"),
        default=False,
    ),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)
_ENVIRONMENT.filters["py_string"] = _python_string

_PATH_ENVIRONMENT = Environment(
    undefined=StrictUndefined,
    autoescape=select_autoescape(
        enabled_extensions=("html", "htm", "xml"),
        default=False,
    ),
    keep_trailing_newline=True,
)

_INLINE_ENVIRONMENT = Environment(
    undefined=StrictUndefined,
    autoescape=select_autoescape(
        enabled_extensions=("html", "htm", "xml"),
        default=False,
    ),
    keep_trailing_newline=True,
    trim_blocks=True,
    lstrip_blocks=True,
)


@dataclass(frozen=True, slots=True)
class FileSpec:
    """A template and its destination."""

    template: str
    output: str
    condition: Callable[[ProjectSpec], bool] = lambda _: True
    runtime_template: bool = False


def _has(feature: str) -> Callable[[ProjectSpec], bool]:
    return lambda spec: spec.has(feature)


def _has_database(spec: ProjectSpec) -> bool:
    return spec.has_database


def _has_any(*features: str) -> Callable[[ProjectSpec], bool]:
    return lambda spec: any(spec.has(feature) for feature in features)


def _not_minimal(spec: ProjectSpec) -> bool:
    return spec.structure != "minimal"


def _feature_structure(spec: ProjectSpec) -> bool:
    return spec.structure == "feature"


def _layered_structure(spec: ProjectSpec) -> bool:
    return spec.structure == "layered"


def _feature_with(*features: str) -> Callable[[ProjectSpec], bool]:
    return lambda spec: _feature_structure(spec) and any(spec.has(feature) for feature in features)


def _needs_env(spec: ProjectSpec) -> bool:
    return (
        spec.has_environment
        or spec.has("redis")
        or spec.has("sentry")
        or spec.has("email")
        or spec.has("uploads")
        or spec.has("oauth2")
        or spec.has("opentelemetry")
        or spec.has("mongodb")
        or spec.has("celery")
    )


FILES: tuple[FileSpec, ...] = (
    FileSpec("pyproject.toml.j2", "pyproject.toml"),
    FileSpec("README.md.j2", "README.md"),
    FileSpec("HELP.md.j2", "HELP.md"),
    FileSpec("gitignore.j2", ".gitignore"),
    FileSpec("python-version.j2", ".python-version"),
    FileSpec("env.example.j2", ".env.example", _needs_env),
    FileSpec(
        "client/package.json.j2",
        "client/package.json",
        _has("typescript-client"),
    ),
    FileSpec(
        "client/tsconfig.json.j2",
        "client/tsconfig.json",
        _has("typescript-client"),
    ),
    FileSpec(
        "client/export_openapi.py.j2",
        "client/export_openapi.py",
        _has("typescript-client"),
    ),
    FileSpec(
        "client/src/api/client.ts.j2",
        "client/src/api/client.ts",
        _has("typescript-client"),
    ),
    FileSpec(
        "client/src/api/schema.d.ts.j2",
        "client/src/api/schema.d.ts",
        _has("typescript-client"),
    ),
    FileSpec(
        "Dockerfile.j2",
        "Dockerfile",
        _has_any("docker", "compose", "arq", "celery"),
    ),
    FileSpec(
        "dockerignore.j2",
        ".dockerignore",
        _has_any("docker", "compose", "arq", "celery"),
    ),
    FileSpec(
        "docker-compose.yml.j2",
        "docker-compose.yml",
        _has_any(
            "docker",
            "compose",
            "postgres",
            "mysql",
            "rabbitmq",
            "redis",
            "celery",
        ),
    ),
    FileSpec("Makefile.j2", "Makefile", _has("makefile")),
    FileSpec("ci.yml.j2", ".github/workflows/ci.yml", _has("ci")),
    FileSpec("gitlab-ci.yml.j2", ".gitlab-ci.yml", _has("ci-gitlab")),
    FileSpec(
        "bitbucket-pipelines.yml.j2",
        "bitbucket-pipelines.yml",
        _has("ci-bitbucket"),
    ),
    FileSpec(
        "pre-commit-config.yaml.j2",
        ".pre-commit-config.yaml",
        _has("pre-commit"),
    ),
    FileSpec("k8s/deployment.yaml.j2", "k8s/deployment.yaml", _has("kubernetes")),
    FileSpec("k8s/service.yaml.j2", "k8s/service.yaml", _has("kubernetes")),
    FileSpec("k8s/configmap.yaml.j2", "k8s/configmap.yaml", _has("kubernetes")),
    FileSpec("k8s/ingress.yaml.j2", "k8s/ingress.yaml", _has("kubernetes")),
    FileSpec("alembic.ini.j2", "alembic.ini", _has("alembic")),
    FileSpec("migrations/env.py.j2", "migrations/env.py", _has("alembic")),
    FileSpec(
        "migrations/script.py.mako.j2",
        "migrations/script.py.mako",
        _has("alembic"),
    ),
    FileSpec(
        "migrations/versions/gitkeep.j2",
        "migrations/versions/.gitkeep",
        _has("alembic"),
    ),
    FileSpec(
        "migrations/versions/0001_create_items.py.j2",
        "migrations/versions/0001_create_items.py",
        _has("alembic"),
    ),
    FileSpec("src/__init__.py.j2", "src/{{ spec.package }}/__init__.py"),
    FileSpec("src/main.py.j2", "src/{{ spec.package }}/main.py"),
    FileSpec(
        "src/api/__init__.py.j2",
        "src/{{ spec.package }}/api/__init__.py",
        _not_minimal,
    ),
    FileSpec(
        "src/api/dependencies.py.j2",
        "src/{{ spec.package }}/api/dependencies.py",
        _not_minimal,
    ),
    FileSpec(
        "src/api/routes/__init__.py.j2",
        "src/{{ spec.package }}/api/routes/__init__.py",
        _not_minimal,
    ),
    FileSpec(
        "src/api/routes/health.py.j2",
        "src/{{ spec.package }}/api/routes/health.py",
        _not_minimal,
    ),
    FileSpec(
        "src/api/routes/items.py.j2",
        "src/{{ spec.package }}/api/routes/items.py",
        _has_database,
    ),
    FileSpec(
        "src/api/routes/documents.py.j2",
        "src/{{ spec.package }}/api/routes/documents.py",
        _has("mongodb"),
    ),
    FileSpec(
        "src/api/routes/auth.py.j2",
        "src/{{ spec.package }}/api/routes/auth.py",
        _has("auth-jwt"),
    ),
    FileSpec(
        "src/api/routes/oauth.py.j2",
        "src/{{ spec.package }}/api/routes/oauth.py",
        _has("oauth2"),
    ),
    FileSpec(
        "src/api/routes/auth_email.py.j2",
        "src/{{ spec.package }}/api/routes/auth_email.py",
        _has("email"),
    ),
    FileSpec(
        "src/api/routes/pages.py.j2",
        "src/{{ spec.package }}/api/routes/pages.py",
        _has("static-templates"),
    ),
    FileSpec(
        "src/api/routes/ws.py.j2",
        "src/{{ spec.package }}/api/routes/ws.py",
        _has("websockets"),
    ),
    FileSpec(
        "src/api/routes/limited.py.j2",
        "src/{{ spec.package }}/api/routes/limited.py",
        _has("rate-limit"),
    ),
    FileSpec(
        "src/api/routes/uploads.py.j2",
        "src/{{ spec.package }}/api/routes/uploads.py",
        _has("uploads"),
    ),
    FileSpec(
        "src/core/__init__.py.j2",
        "src/{{ spec.package }}/core/__init__.py",
        _not_minimal,
    ),
    FileSpec("src/core/config.py.j2", "src/{{ spec.package }}/core/config.py"),
    FileSpec("src/core/errors.py.j2", "src/{{ spec.package }}/core/errors.py"),
    FileSpec("src/core/logging.py.j2", "src/{{ spec.package }}/core/logging.py"),
    FileSpec("src/core/middleware.py.j2", "src/{{ spec.package }}/core/middleware.py"),
    FileSpec(
        "src/core/cache.py.j2",
        "src/{{ spec.package }}/core/cache.py",
        _has("redis"),
    ),
    FileSpec(
        "src/core/cache_helpers.py.j2",
        "src/{{ spec.package }}/core/cache_helpers.py",
        _has("cache"),
    ),
    FileSpec(
        "src/core/mongo.py.j2",
        "src/{{ spec.package }}/core/mongo.py",
        _has("mongodb"),
    ),
    FileSpec(
        "src/core/observability.py.j2",
        "src/{{ spec.package }}/core/observability.py",
        _has("sentry"),
    ),
    FileSpec(
        "src/core/oauth.py.j2",
        "src/{{ spec.package }}/core/oauth.py",
        _has("oauth2"),
    ),
    FileSpec(
        "src/core/rate_limit.py.j2",
        "src/{{ spec.package }}/core/rate_limit.py",
        _has("rate-limit"),
    ),
    FileSpec(
        "src/core/tracing.py.j2",
        "src/{{ spec.package }}/core/tracing.py",
        _has("opentelemetry"),
    ),
    FileSpec(
        "src/core/auth_throttle.py.j2",
        "src/{{ spec.package }}/core/auth_throttle.py",
        _has("auth-jwt"),
    ),
    FileSpec(
        "src/core/security.py.j2",
        "src/{{ spec.package }}/core/security.py",
        _has("auth-jwt"),
    ),
    FileSpec(
        "src/core/email.py.j2",
        "src/{{ spec.package }}/core/email.py",
        _has("email"),
    ),
    FileSpec(
        "src/core/storage.py.j2",
        "src/{{ spec.package }}/core/storage.py",
        _has("uploads"),
    ),
    FileSpec(
        "src/core/storage_s3.py.j2",
        "src/{{ spec.package }}/core/storage_s3.py",
        _has("s3"),
    ),
    FileSpec(
        "src/graphql/__init__.py.j2",
        "src/{{ spec.package }}/graphql/__init__.py",
        _has("graphql"),
    ),
    FileSpec(
        "src/graphql/schema.py.j2",
        "src/{{ spec.package }}/graphql/schema.py",
        _has("graphql"),
    ),
    FileSpec(
        "src/db/__init__.py.j2",
        "src/{{ spec.package }}/db/__init__.py",
        _has_database,
    ),
    FileSpec(
        "src/db/base.py.j2",
        "src/{{ spec.package }}/db/base.py",
        _has_database,
    ),
    FileSpec(
        "src/db/session.py.j2",
        "src/{{ spec.package }}/db/session.py",
        _has_database,
    ),
    FileSpec(
        "feature_init.py.j2",
        "src/{{ spec.package }}/features/__init__.py",
        _feature_structure,
    ),
    FileSpec(
        "feature_init.py.j2",
        "src/{{ spec.package }}/features/health/__init__.py",
        _feature_structure,
    ),
    FileSpec(
        "feature_init.py.j2",
        "src/{{ spec.package }}/features/items/__init__.py",
        _feature_with("sqlalchemy", "sqlmodel"),
    ),
    FileSpec(
        "feature_init.py.j2",
        "src/{{ spec.package }}/features/auth/__init__.py",
        _feature_with("auth-jwt"),
    ),
    FileSpec(
        "feature_init.py.j2",
        "src/{{ spec.package }}/features/documents/__init__.py",
        _feature_with("mongodb"),
    ),
    FileSpec(
        "feature_init.py.j2",
        "src/{{ spec.package }}/features/pages/__init__.py",
        _feature_with("static-templates"),
    ),
    FileSpec(
        "feature_init.py.j2",
        "src/{{ spec.package }}/features/websockets/__init__.py",
        _feature_with("websockets"),
    ),
    FileSpec(
        "feature_init.py.j2",
        "src/{{ spec.package }}/features/rate_limit/__init__.py",
        _feature_with("rate-limit"),
    ),
    FileSpec(
        "feature_init.py.j2",
        "src/{{ spec.package }}/features/uploads/__init__.py",
        _feature_with("uploads"),
    ),
    FileSpec(
        "src/models/__init__.py.j2",
        "src/{{ spec.package }}/models/__init__.py",
        _has_any("sqlalchemy", "sqlmodel", "mongodb"),
    ),
    FileSpec(
        "src/models/document.py.j2",
        "src/{{ spec.package }}/models/document.py",
        _has("mongodb"),
    ),
    FileSpec(
        "src/models/item.py.j2",
        "src/{{ spec.package }}/models/item.py",
        _has_database,
    ),
    FileSpec(
        "src/models/user.py.j2",
        "src/{{ spec.package }}/models/user.py",
        _has("auth-jwt"),
    ),
    FileSpec(
        "src/schemas/__init__.py.j2",
        "src/{{ spec.package }}/schemas/__init__.py",
        _layered_structure,
    ),
    FileSpec(
        "src/schemas/item.py.j2",
        "src/{{ spec.package }}/schemas/item.py",
        _has_database,
    ),
    FileSpec(
        "src/schemas/user.py.j2",
        "src/{{ spec.package }}/schemas/user.py",
        _has("auth-jwt"),
    ),
    FileSpec(
        "src/schemas/document.py.j2",
        "src/{{ spec.package }}/schemas/document.py",
        _has("mongodb"),
    ),
    FileSpec(
        "src/services/__init__.py.j2",
        "src/{{ spec.package }}/services/__init__.py",
        _layered_structure,
    ),
    FileSpec(
        "src/services/items.py.j2",
        "src/{{ spec.package }}/services/items.py",
        _has_database,
    ),
    FileSpec(
        "src/services/documents.py.j2",
        "src/{{ spec.package }}/services/documents.py",
        _has("mongodb"),
    ),
    FileSpec(
        "src/services/auth.py.j2",
        "src/{{ spec.package }}/services/auth.py",
        _has("auth-jwt"),
    ),
    FileSpec(
        "src/services/oauth.py.j2",
        "src/{{ spec.package }}/services/oauth.py",
        _has("oauth2"),
    ),
    FileSpec(
        "src/services/auth_email.py.j2",
        "src/{{ spec.package }}/services/auth_email.py",
        _has("email"),
    ),
    FileSpec(
        "src/tasks/__init__.py.j2",
        "src/{{ spec.package }}/tasks/__init__.py",
        _has("arq"),
    ),
    FileSpec(
        "src/tasks/example.py.j2",
        "src/{{ spec.package }}/tasks/example.py",
        _has("arq"),
    ),
    FileSpec(
        "src/worker.py.j2",
        "src/{{ spec.package }}/worker.py",
        _has_any("arq", "celery"),
    ),
    FileSpec(
        "templates/index.html.j2",
        "templates/index.html",
        _has("static-templates"),
    ),
    FileSpec(
        "templates/email/password_reset.txt.j2",
        "templates/email/password_reset.txt",
        _has("email"),
        runtime_template=True,
    ),
    FileSpec(
        "templates/email/verify_email.txt.j2",
        "templates/email/verify_email.txt",
        _has("email"),
        runtime_template=True,
    ),
    FileSpec(
        "templates/email/password_changed.txt.j2",
        "templates/email/password_changed.txt",
        _has("email"),
        runtime_template=True,
    ),
    FileSpec(
        "static/style.css.j2",
        "static/style.css",
        _has("static-templates"),
    ),
    FileSpec("tests/conftest.py.j2", "tests/conftest.py"),
    FileSpec("tests/test_health.py.j2", "tests/test_health.py"),
    FileSpec("tests/test_items.py.j2", "tests/test_items.py", _has_database),
    FileSpec("tests/test_documents.py.j2", "tests/test_documents.py", _has("mongodb")),
    FileSpec("tests/test_graphql.py.j2", "tests/test_graphql.py", _has("graphql")),
    FileSpec("tests/test_auth.py.j2", "tests/test_auth.py", _has("auth-jwt")),
    FileSpec("tests/test_email_auth.py.j2", "tests/test_email_auth.py", _has("email")),
    FileSpec("tests/test_oauth.py.j2", "tests/test_oauth.py", _has("oauth2")),
    FileSpec("tests/test_tracing.py.j2", "tests/test_tracing.py", _has("opentelemetry")),
    FileSpec("tests/test_cache.py.j2", "tests/test_cache.py", _has("redis")),
    FileSpec(
        "tests/test_cache_helpers.py.j2",
        "tests/test_cache_helpers.py",
        _has("cache"),
    ),
    FileSpec(
        "tests/test_worker.py.j2",
        "tests/test_worker.py",
        _has_any("arq", "celery"),
    ),
    FileSpec("tests/test_sentry.py.j2", "tests/test_sentry.py", _has("sentry")),
    FileSpec(
        "tests/test_prometheus.py.j2",
        "tests/test_prometheus.py",
        _has("prometheus"),
    ),
    FileSpec(
        "tests/test_pages.py.j2",
        "tests/test_pages.py",
        _has("static-templates"),
    ),
    FileSpec(
        "tests/test_websockets.py.j2",
        "tests/test_websockets.py",
        _has("websockets"),
    ),
    FileSpec(
        "tests/test_rate_limit.py.j2",
        "tests/test_rate_limit.py",
        _has("rate-limit"),
    ),
    FileSpec(
        "tests/test_uploads.py.j2",
        "tests/test_uploads.py",
        _has("uploads"),
    ),
    FileSpec(
        "tests/test_storage_s3.py.j2",
        "tests/test_storage_s3.py",
        _has("s3"),
    ),
    FileSpec(
        "tests/integration/conftest.py.j2",
        "tests/integration/conftest.py",
        _has("testcontainers"),
    ),
    FileSpec(
        "tests/integration/test_integration.py.j2",
        "tests/integration/test_integration.py",
        _has("testcontainers"),
    ),
    FileSpec(
        "scripts/run_integration.sh.j2",
        "scripts/run_integration.sh",
        _has("testcontainers"),
    ),
    FileSpec(
        "scripts/security.sh.j2",
        "scripts/security.sh",
        _has("security-scan"),
    ),
    FileSpec(
        ".github/workflows/integration.yml.j2",
        ".github/workflows/integration.yml",
        _has("testcontainers"),
    ),
    FileSpec("tests/test_makefile.py.j2", "tests/test_makefile.py", _has("makefile")),
    FileSpec(
        "tests/test_kubernetes.py.j2",
        "tests/test_kubernetes.py",
        _has("kubernetes"),
    ),
    FileSpec(
        "tests/test_security_tooling.py.j2",
        "tests/test_security_tooling.py",
        _has("security-scan"),
    ),
    FileSpec(
        "tests/test_contract.py.j2",
        "tests/test_contract.py",
        _has("schemathesis"),
    ),
)


def build_context(spec: ProjectSpec) -> dict[str, object]:
    """Build the template context for a project spec."""
    packages, dev_packages = resolve_packages(spec.dependencies)
    selected_features = [
        {
            "id": dependency.id,
            "name": dependency.name,
            "description": dependency.description,
            "help": HELP_STEPS.get(dependency.id, ()),
            "guide": dependency.guide,
            "guide_title": dependency.guide_title or "Guide",
            "reference": dependency.reference,
        }
        for dependency in sorted(
            (
                DEPENDENCIES[feature_id]
                for feature_id in spec.dependencies
                if feature_id in DEPENDENCIES
            ),
            key=lambda dependency: (dependency.group, dependency.name),
        )
    ]
    layout = Layout(spec.structure, spec.package or "")
    routers: list[dict[str, str]] = [{"module": layout.route("health"), "alias": "health_router"}]
    if spec.has_database:
        routers.append({"module": layout.route("items"), "alias": "items_router"})
    if spec.has("mongodb"):
        routers.append({"module": layout.route("documents"), "alias": "documents_router"})
    if spec.has("auth-jwt"):
        routers.append({"module": layout.route("auth"), "alias": "auth_router"})
    if spec.has("email"):
        routers.append({"module": layout.route("auth_email"), "alias": "auth_email_router"})
    if spec.has("rate-limit"):
        routers.append({"module": layout.route("limited"), "alias": "limited_router"})
    if spec.has("oauth2"):
        routers.append({"module": layout.route("oauth"), "alias": "oauth_router"})
    if spec.has("static-templates"):
        routers.append({"module": layout.route("pages"), "alias": "pages_router"})
    if spec.has("uploads"):
        routers.append({"module": layout.route("uploads"), "alias": "uploads_router"})
    if spec.has("websockets"):
        routers.append({"module": layout.route("ws"), "alias": "ws_router"})
    routers.sort(key=lambda router: router["module"])

    model_imports: list[dict[str, str]] = []
    if spec.has_database:
        model_imports.append({"module": layout.model("item"), "name": "Item"})
    if spec.has("auth-jwt"):
        model_imports.append({"module": layout.model("user"), "name": "User"})
    if spec.has("mongodb"):
        model_imports.append({"module": layout.model("document"), "name": "Document"})
    model_imports.sort(key=lambda model: model["module"])
    model_names = sorted(model["name"] for model in model_imports)

    return {
        "spec": spec,
        "layout": layout,
        "routers": routers,
        "model_imports": model_imports,
        "model_names": model_names,
        "core_packages": core_packages(),
        "core_dev_packages": core_dev_packages(),
        "packages": packages,
        "dev_packages": dev_packages,
        "selected_features": selected_features,
        "needs_env": _needs_env(spec),
        "project_version": spec.version,
        "author": spec.author,
        "app_title": spec.app_title,
        "base_dir": spec.archive_root,
        "supports_pep695": tuple(int(part) for part in spec.python.split(".")) >= (3, 12),
    }


def _validate_output_path(path: str) -> str:
    if not path or "\x00" in path or "\\" in path:
        raise ValueError(f"Invalid output path: {path!r}")
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts or pure.name in {"", "."}:
        raise ValueError(f"Invalid output path: {path!r}")
    return pure.as_posix()


def _user_markers(spec: ProjectSpec) -> frozenset[str]:
    values = (spec.description, spec.author, spec.application_name or "")
    return frozenset(marker for value in values for marker in ("{{", "{%", "{#") if marker in value)


def _validate_content(
    path: str,
    content: str,
    *,
    allow_template_markers: bool = False,
    allowed_markers: frozenset[str] = frozenset(),
) -> None:
    if not allow_template_markers:
        unresolved = [
            marker
            for marker in ("{{", "{%", "{#")
            if marker in content and marker not in allowed_markers
        ]
        if unresolved:
            raise ValueError(f"Unresolved template marker in {path}")
    if path.endswith(".py"):
        ast.parse(content, filename=path)
    elif path == "pyproject.toml":
        tomllib.loads(content)


def render_project(spec: ProjectSpec) -> dict[str, str]:
    """Render every selected file for a project spec."""
    context = build_context(spec)
    layout = Layout(spec.structure, spec.package or "")
    allowed_markers = _user_markers(spec)
    rendered: dict[str, str] = {}
    for file_spec in FILES:
        if not file_spec.condition(spec):
            continue
        output = _PATH_ENVIRONMENT.from_string(file_spec.output).render(context)
        output = _validate_output_path(output)
        output = _validate_output_path(layout.output_path(output))
        if output in rendered:
            raise ValueError(f"Duplicate output path: {output}")
        template = _ENVIRONMENT.get_template(file_spec.template)
        content = template.render(context)
        _validate_content(
            output,
            content,
            allow_template_markers=file_spec.runtime_template,
            allowed_markers=allowed_markers,
        )
        rendered[output] = content
    for plugin_file in plugin_files():
        if not spec.has(plugin_file.feature_id):
            continue
        output = _PATH_ENVIRONMENT.from_string(plugin_file.path).render(context)
        output = _validate_output_path(output)
        if output in rendered:
            raise ValueError(f"Duplicate output path: {output}")
        content = _INLINE_ENVIRONMENT.from_string(plugin_file.template).render(context)
        _validate_content(output, content, allowed_markers=allowed_markers)
        rendered[output] = content
    rendered[MANIFEST_NAME] = render_manifest(spec, rendered)
    return dict(sorted(rendered.items()))
