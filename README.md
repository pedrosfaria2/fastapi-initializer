# FastAPI Initializr

A Spring Initializr-style generator for FastAPI projects. Choose a project name,
Python version, and optional features, then download a ready-to-run Python
project using `uv`, Ruff, mypy, pyright, and pytest.

## Features

- Metadata-driven web UI and HTTP API, with a compatibility report for API
  clients and IDE integrations.
- Deterministic zip and tar.gz archives, plus standalone `pyproject.toml` and
  `requirements.txt` outputs.
- Searchable catalog with 36 selectable features, docs links, compatibility
  rules, shift-click selection, Share, Reset, and keyboard generation.
- Presets for API only, database + auth, Redis worker, and full stack.
- Explore preview with server-side Pygments highlighting, language labels, file
  sizes, and an empty-file marker.
- Safe project, package, version, and baseDir validation.
- Generated projects with `src/` layout, FastAPI app factory, health/readiness,
  request IDs, gzip compression, logging, error handlers, tests, and a
  selected-feature `HELP.md` checklist.
- Selectable minimal, layered, or feature-based project structures.
- Optional SQLAlchemy or SQLModel CRUD, Alembic, PostgreSQL or MySQL/MariaDB,
  ARQ or Celery workers, JWT authentication, CORS, Docker/Compose, GitHub
  Actions, pre-commit, and coverage.
- Local CLI: `fastapi-initializr new`, `update`, `add`, `remove`, `diff`,
  `list`, `metadata`, `completion`, `--lock`, `--dry-run`, `--json`, and
  `--preset`.
- Local JSON plugins can add catalog features without changing the generator.
- Optional Schemathesis contract tests generated from the app's OpenAPI schema.
- Optional TypeScript client generation from the same OpenAPI schema.
- Generated projects pass Ruff, mypy, pyright, and pytest.
- Stateless: no accounts, database, saved projects, or server-side execution of
  generated code.

## UI layout

The desktop workspace places project settings, dependencies, and Explore side by
side. Each pane scrolls independently; the download bar stays visible. Filter
dependencies by search, category, or the selected count. Clear resets the filters;
Reset also restores the project defaults. Optional metadata is under Advanced
settings. Explore opens `pyproject.toml` and groups files by directory.

## Quick start

Requires Python 3.12+ and uv.

```sh
uv sync --locked
uv run fastapi dev
```

Open <http://127.0.0.1:8000>. The API documentation is at
<http://127.0.0.1:8000/docs>.

## API

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/` | Web UI |
| `GET` | `/health` | Liveness |
| `GET` | `/ready` | Readiness |
| `GET` | `/metadata` | Capability document |
| `GET` | `/api/metadata` | Option catalog alias |
| `GET` | `/dependencies` | Package names and files for every feature |
| `GET` | `/compatibility` | Selection issues and per-feature availability |
| `GET` | `/preview` | Rendered file list and contents |
| `GET` | `/starter.zip` | Download a zip |
| `GET` | `/starter.tgz` | Download a tar.gz |
| `GET` | `/pyproject.toml` | Download only the build file |
| `GET` | `/requirements.txt` | Download runtime requirements |
| `POST` | `/starter.zip` | Download a zip from JSON |
| `POST` | `/preview` | Preview from JSON |

The `/api/preview` and `/api/generate` aliases remain available.
`POST /api/generate` accepts a JSON object or an
`application/x-www-form-urlencoded` form; the no-JavaScript form submits the
form-encoded variant. JSON accepts the camelCase aliases `baseDir`,
`applicationName`, and `pythonVersion` as well as the field names. Unknown
query/form fields and file uploads for scalar fields are rejected with `422`.

Download a project:

```sh
curl -OJ 'http://127.0.0.1:8000/starter.zip?name=my-service&dependencies=sqlalchemy&dependencies=alembic'
```

Download a tar.gz or a build file:

```sh
curl -OJ 'http://127.0.0.1:8000/starter.tgz?name=my-service'
curl 'http://127.0.0.1:8000/pyproject.toml?name=my-service'
curl 'http://127.0.0.1:8000/requirements.txt?name=my-service&dependencies=sqlalchemy'
```

`requirements.txt` lists the same runtime specs declared in the generated
`pyproject.toml`; it is a standalone output and is not written into the
generated project.

Preview the same project:

```sh
curl 'http://127.0.0.1:8000/preview?name=my-service&dependencies=sqlalchemy&dependencies=alembic'
```

List package names and files for every feature:

```sh
curl 'http://127.0.0.1:8000/dependencies'
```

Check selection compatibility and per-feature availability:

```sh
curl 'http://127.0.0.1:8000/compatibility?dependencies=sqlalchemy&dependencies=alembic'
```

The capability document supports a versioned media type:

```sh
curl -H 'Accept: application/vnd.fastapi-initializr.v1+json' \
  http://127.0.0.1:8000/metadata
```

Use JSON for API clients:

```sh
curl -OJ -X POST 'http://127.0.0.1:8000/api/generate' \
  -H 'Content-Type: application/json' \
  -d '{"name":"my-service","python":"3.13","dependencies":["sqlalchemy","alembic","docker"]}'
```

Parameters:

- `name`: project and distribution name.
- `package`: import package; derived from `name` when omitted.
- `description`: project summary.
- `version`: project version, `MAJOR.MINOR.PATCH` (default `0.1.0`).
- `author`: optional author name.
- `structure`: `minimal`, `layered` (default), or `feature`.
- `python` / `pythonVersion`: `3.11`, `3.12`, `3.13`, or `3.14`.
- `preset`: `custom` (default), `api`, `db-auth`, `worker`, or `full`.
- `baseDir`: root directory inside the archive (defaults to `name`).
- `applicationName`: OpenAPI application title (defaults to `name`).
- `dependencies`: repeated ids or a comma-separated list.

## Project structures

- `layered` keeps the familiar `api/`, `core/`, `db/`, `models/`, `schemas/`,
  and `services/` packages.
- `feature` groups each domain under `features/<name>/` with its models,
  schemas, service, and router; shared infrastructure stays in `core/`, `db/`,
  and `api/`.
- `minimal` uses a small `main.py` and top-level `config.py`, `errors.py`,
  `logging.py`, and `middleware.py`. It supports cors, observability,
  operations, and the TypeScript client; database, auth, workers, GraphQL,
  uploads, WebSockets, and similar domain features require `layered` or
  `feature`.

## Dependency versions

Generated `pyproject.toml` files declare package names and extras without version
specifiers. `uv sync` resolves the newest compatible versions at install time,
and the generated project's tests run against that resolution. Run `uv lock` in
the generated project when you need a reproducible snapshot; the CLI `--lock`
does this after generation.

## Presets

A preset is a named dependency selection. Combine it with individual
`dependencies`; the server takes the union.

| Preset | Selects |
| --- | --- |
| `custom` | Nothing; choose dependencies manually. |
| `api` | Core service only. |
| `db-auth` | `sqlalchemy`, `alembic`, `auth-jwt`, `cors`. |
| `worker` | `redis`, `cache`, `arq`. |
| `full` | Every compatible feature. MongoDB is excluded because it conflicts with SQLAlchemy. |

```sh
curl -OJ 'http://127.0.0.1:8000/starter.zip?name=my-service&preset=db-auth'
```

## Plugins

A plugin directory adds local features without changing the generator. Point the
server at it with `FASTAPI_INITIALIZR_PLUGIN_DIR=./plugins`, or pass
`--plugin-dir ./plugins` to `new` and `update`.

Each `*.json` file defines one feature:

```json
{
  "id": "custom-feature",
  "name": "Custom feature",
  "description": "Adds a custom module and dependency.",
  "group": "Custom",
  "packages": ["example-lib>=1.0"],
  "devPackages": [],
  "requires": [],
  "conflicts": [],
  "files": [
    {
      "path": "src/{{ spec.package }}/custom.py",
      "template": "FEATURE = \"{{ spec.name }}\"\n"
    }
  ]
}
```

Plugin files render with the same Jinja context as built-in templates. Generated
Python and TOML are validated before an archive is returned. Plugin directories
are trusted local input and are never fetched from the network; the plugin id
must not collide with the built-in catalog. The `full` preset covers built-in
features only, so select plugin features explicitly.

## Options

| ID | Group | Adds | Requires |
| --- | --- | --- | --- |
| `sqlalchemy` | Database | Async SQLAlchemy session and SQLite driver | — |
| `sqlmodel` | Database | SQLModel ORM on SQLAlchemy with async sessions | — |
| `alembic` | Database | Alembic configuration and migrations | SQLAlchemy or SQLModel |
| `postgres` | Database | Async PostgreSQL driver | SQLAlchemy or SQLModel |
| `mysql` | Database | Async MySQL/MariaDB driver | SQLAlchemy or SQLModel |
| `mongodb` | Database | Beanie ODM, document CRUD, and MongoDB settings | — |
| `redis` | Database | Async Redis client and settings | — |
| `cache` | Database | Typed cache-aside helpers with TTL and invalidation | `redis` |
| `arq` | Messaging | ARQ worker and example background task | `redis` |
| `celery` | Messaging | Celery worker and example task | RabbitMQ or Redis |
| `rabbitmq` | Messaging | RabbitMQ broker and management UI | — |
| `auth-jwt` | Security | JWT registration, login, and protected `/auth/me` | `sqlalchemy` |
| `email` | Security | Console/SMTP email, password reset, and verification | `auth-jwt` |
| `oauth2` | Security | Google/GitHub OAuth2 login linked to local users | `auth-jwt` |
| `cors` | Web | CORS middleware and settings | — |
| `static-templates` | Web | Jinja2 templates, static assets, and a welcome page | — |
| `websockets` | Web | WebSocket echo endpoint | — |
| `rate-limit` | Web | SlowAPI limiter and example route | — |
| `uploads` | Web | Authenticated local file uploads with owner-scoped keys | `auth-jwt` |
| `graphql` | Web | Strawberry GraphQL query and mutation | — |
| `typescript-client` | Web | Typed `openapi-fetch` client and generated types | — |
| `s3` | Operations | S3-compatible storage backend | `uploads` |
| `testcontainers` | Testing | PostgreSQL/Redis integration fixtures | `postgres`, `redis` |
| `schemathesis` | Testing | OpenAPI property-based contract tests | — |
| `sentry` | Observability | Sentry error reporting, disabled without a DSN | — |
| `prometheus` | Observability | Prometheus instrumentation and `/metrics` | — |
| `opentelemetry` | Observability | OTLP tracing for FastAPI, SQLAlchemy, and Redis | — |
| `docker` | Operations | Dockerfile and .dockerignore | — |
| `compose` | Operations | Compose stack for the app, databases, RabbitMQ, and Redis | — |
| `makefile` | Operations | Common development targets | — |
| `ci` | Operations | GitHub Actions workflow | — |
| `ci-gitlab` | Operations | GitLab CI pipeline | — |
| `ci-bitbucket` | Operations | Bitbucket Pipelines configuration | — |
| `security-scan` | Operations | pip-audit, Bandit, detect-secrets, and CycloneDX SBOM | — |
| `kubernetes` | Operations | Deployment, Service, ConfigMap, and Ingress | — |
| `pre-commit` | Operations | Ruff, mypy, and pyright hooks | — |

Every generated project includes FastAPI, Uvicorn, Pydantic Settings,
`python-multipart`, pytest, httpx2, Ruff, mypy, and pyright.

`sqlmodel` covers the relational CRUD, Alembic, and database-driver slices.
The JWT auth, email, and OAuth2 slices currently require `sqlalchemy`.
`testcontainers` currently provides PostgreSQL and Redis fixtures, not MySQL.
`arq` and `celery` are alternative workers; `celery` uses RabbitMQ or Redis as
its broker.

## Generated project

```text
my-service/
├── pyproject.toml
├── .python-version
├── .gitignore
├── .fastapi-initializr.json
├── HELP.md
├── README.md
├── src/my_service/
│   ├── main.py
│   ├── api/
│   ├── core/
│   │   ├── config.py
│   │   ├── errors.py
│   │   ├── logging.py
│   │   └── middleware.py
│   ├── db/
│   ├── models/
│   ├── schemas/
│   └── services/
└── tests/
    ├── conftest.py
    ├── test_health.py
    ├── test_items.py
    └── test_auth.py
```

With `structure=feature`, domain modules live under
`src/<package>/features/<name>/`. With `structure=minimal`, the app uses
top-level `config.py`, `errors.py`, `logging.py`, and `middleware.py`.

Run it:

```sh
unzip my-service.zip
cd my-service
uv sync
uv run fastapi dev
```

`.fastapi-initializr.json` records the template version, the resolved options,
and a SHA-256 digest for every generated file. Keep it in version control; the
CLI uses it to detect local edits and merge disjoint template changes.

Quality gates:

```sh
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pyright src
uv run pytest
```

If the project includes a database, copy `.env.example` to `.env` and adjust
`DATABASE_URL`. If it includes Alembic, run:

```sh
uv run alembic upgrade head
```

If it includes JWT authentication, change `SECRET_KEY` in `.env` before using it
outside local development. The generated endpoints are `/auth/register`,
`/auth/login`, and `/auth/me`.

## CLI

Generate a project directory without the web server:

```sh
uv run fastapi-initializr new my-service \
  --structure feature \
  --preset db-auth \
  --dependency redis \
  --output .
```

Useful commands:

```sh
uv run fastapi-initializr list
uv run fastapi-initializr list --json
uv run fastapi-initializr metadata
uv run fastapi-initializr new my-service --force
uv run fastapi-initializr new my-service --lock
uv run fastapi-initializr new my-service --dry-run
uv run fastapi-initializr new my-service --json
uv run fastapi-initializr new --list-dependencies
uv run fastapi-initializr update ./my-service
uv run fastapi-initializr add cors ./my-service
uv run fastapi-initializr remove cors ./my-service
uv run fastapi-initializr diff ./my-service
uv run fastapi-initializr add celery ./my-service --dry-run --json
```

The CLI uses the same validation and templates as the API. `--lock` runs
`uv lock` in the generated project. `--dry-run` prints the file plan without
writing, and `--json` prints a machine-readable summary.

`update` re-renders the project from `.fastapi-initializr.json`. Local edits are
preserved; disjoint template changes are merged line by line. Changes are staged
and backed up before they replace files, and a failed write restores the
previous state. A backup left by an interrupted process is recovered on the next
run. `add` and `remove` change the dependency set, switch the preset to
`custom`, and apply the same plan. Overlapping edits abort with exit code `3`;
rerun with `--force` to overwrite conflicts and remove locally modified obsolete
files. Removed files are deleted only when they still match the recorded digest.
`diff` prints the plan and unified diffs without writing.

Shell completion scripts are generated from the catalog:

```sh
# bash
source <(uv run fastapi-initializr completion bash)

# zsh
uv run fastapi-initializr completion zsh > ~/.zfunc/_fastapi-initializr

# fish
uv run fastapi-initializr completion fish | source
```

## Docker

Build and run the generator locally:

```sh
docker build -t fastapi-initializr .
docker run --rm -p 8000:8000 fastapi-initializr
```

The image uses `python:3.14-slim-trixie` with the current uv image,
installs the project non-editable from `uv.lock`, runs as the unprivileged
numeric user `10001`, and exposes `/health` for its healthcheck. Build it with
the commands above; the repository gate covers the Dockerfile invariants but
does not build the image.

## Development

```sh
uv sync --locked
uv run playwright install chromium
bash scripts/check.sh
```

`scripts/check.sh` runs the lockfile check, Ruff, mypy, pyright, pytest, and
`uv build`. Browser tests cover search, shift-click, presets, Share, Reset,
Ctrl/Cmd+Enter, and Explore highlighting/scrolling against a real server. Install
system browser dependencies with
`uv run playwright install --with-deps chromium` when they are missing.

When templates or generated-project behavior change, run the combined gate:

```sh
bash scripts/check-all.sh
```

This runs the generator gate and the complete generated-project matrix:
minimal, database, auth, web, operations, and full-feature projects. Each
generated project runs its real `uv sync`, Ruff, mypy, pyright, and pytest
commands. Generated projects also include coverage configuration and run it in
their CI workflow.

## Project layout

```text
src/fastapi_initializr/
├── main.py
├── api/routes/          # metadata, preview, generate
├── core/config.py
├── generation/          # spec, catalog, plugins, renderer, archive, preview,
│                        # highlight, requirements, manifest, update
├── schemas/
├── services/
├── static/
└── templates/
    ├── index.html
    └── project/         # generated-project templates
```

## Security

- Project names, package names, Python versions, and dependency ids are
  validated on the server.
- Only allowlisted dependencies are accepted; arbitrary package names, URLs, and
  paths are rejected.
- Archives are built from a fixed relative manifest with a constant timestamp.
  Path traversal, absolute paths, and symlinks are rejected.
- Generated auth links OAuth accounts by the provider subject and a verified
  email, refuses to merge an existing password account automatically, uses
  PKCE, and rejects an invalid or cross-session callback state with `400`.
- Access tokens carry issuer, audience, type, and account version claims;
  password reset and logout revoke older access tokens. Password-reset and
  verification tokens are typed separately and consumed atomically, so
  concurrent reuse succeeds once.
- Registration and password reset use a minimum of 12 characters. Registration
  returns the same response for new and existing emails, and a password reset
  sends a notification. Auth endpoints are rate-limited when selected.
- Generated uploads require a bearer token, and storage keys are scoped to the
  owning user. Item CRUD is owner-scoped when JWT auth is selected. Production
  startup rejects placeholder or short JWT secrets and the console email backend.
- Generated responses set `nosniff`, `X-Frame-Options`, and `Referrer-Policy`;
  HTTPS also gets HSTS. Proxy headers are rejected unless trusted proxy IPs are
  configured.
- The initial Alembic migration creates the selected users, OAuth columns, item
  owner column, and items tables. Project updates stage and back up every
  changed file, roll back on failure, and recover an interrupted update on the
  next run.
- Generated projects are never executed inside a web request.
- Generation is bounded by file-count, preview-byte, and archive-size limits.

## Status

Local-first MVP. The generator is stateless and intended to run on your machine
or a trusted local network. Public deployment is not a goal. If you expose it
beyond localhost, add rate limiting and hardening first.
