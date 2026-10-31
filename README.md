# FastAPI Initializr

A Spring Initializr-style generator for FastAPI projects. Choose a project name,
Python version, and optional features, then download a ready-to-run Python
project using `uv`, Ruff, mypy, pyright, and pytest.

## Features

- Metadata-driven web UI and HTTP API.
- Deterministic zip and tar.gz archives, plus standalone `pyproject.toml` and
  `requirements.txt` outputs.
- Searchable catalog with 30 selectable features, docs links, compatibility
  rules, shift-click selection, Share, Reset, and keyboard generation.
- Presets for API only, database + auth, Redis worker, and full stack.
- Explore preview with server-side Pygments highlighting, language labels, file
  sizes, and an empty-file marker.
- Safe project, package, version, and baseDir validation.
- Generated projects with `src/` layout, FastAPI app factory, health/readiness,
  request IDs, gzip compression, logging, error handlers, and tests.
- Optional SQLAlchemy CRUD, Alembic, PostgreSQL, JWT authentication, CORS,
  Docker/Compose, GitHub Actions, pre-commit, and coverage.
- Local CLI: `fastapi-initializr new`, `update`, `list`, `metadata`,
  `completion`, `--lock`, `--dry-run`, `--json`, and `--preset`.
- Local JSON plugins can add catalog features without changing the generator.
- Generated projects pass Ruff, mypy, pyright, and pytest.
- Stateless: no accounts, database, saved projects, or server-side execution of
  generated code.

## UI layout

The project form and generation actions occupy the first row. The Generate
panel scrolls with the form and cannot overlap Explore. Explore is a full-width
panel below, with its own scrollable file tree and code pane. The code pane takes
the remaining width, long lines scroll horizontally without wrapping, and the
panels stack on narrow screens.

## Quick start

Requires Python 3.12+ and uv 0.13.6 (0.13.x).

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
| `GET` | `/dependencies` | Resolved dependency coordinates |
| `GET` | `/preview` | Rendered file list and contents |
| `GET` | `/starter.zip` | Download a zip |
| `GET` | `/starter.tgz` | Download a tar.gz |
| `GET` | `/pyproject.toml` | Download only the build file |
| `GET` | `/requirements.txt` | Download runtime requirements |
| `POST` | `/starter.zip` | Download a zip from JSON |
| `POST` | `/preview` | Preview from JSON |

The `/api/preview` and `/api/generate` aliases remain available.

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

Resolve dependency coordinates:

```sh
curl 'http://127.0.0.1:8000/dependencies?fastapiVersion=0.161.1'
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
- `python` / `pythonVersion`: `3.11`, `3.12`, `3.13`, or `3.14`.
- `fastapi` / `fastapiVersion`: supported FastAPI version.
- `preset`: `custom` (default), `api`, `db-auth`, `worker`, or `full`.
- `baseDir`: root directory inside the archive (defaults to `name`).
- `applicationName`: OpenAPI application title (defaults to `name`).
- `dependencies`: repeated ids or a comma-separated list.

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
must not collide with the built-in catalog.

## Options

| ID | Group | Adds | Requires |
| --- | --- | --- | --- |
| `sqlalchemy` | Database | Async SQLAlchemy session and SQLite driver | — |
| `alembic` | Database | Alembic configuration and migrations | `sqlalchemy` |
| `postgres` | Database | Async PostgreSQL driver | `sqlalchemy` |
| `mongodb` | Database | Beanie ODM, document CRUD, and MongoDB settings | — |
| `redis` | Database | Async Redis client and settings | — |
| `cache` | Database | Typed cache-aside helpers with TTL and invalidation | `redis` |
| `arq` | Messaging | ARQ worker and example background task | `redis` |
| `auth-jwt` | Security | JWT registration, login, and protected `/auth/me` | `sqlalchemy` |
| `email` | Security | Console/SMTP email, password reset, and verification | `auth-jwt` |
| `oauth2` | Security | Google/GitHub OAuth2 login linked to local users | `auth-jwt` |
| `cors` | Web | CORS middleware and settings | — |
| `static-templates` | Web | Jinja2 templates, static assets, and a welcome page | — |
| `websockets` | Web | WebSocket echo endpoint | — |
| `rate-limit` | Web | SlowAPI limiter and example route | — |
| `uploads` | Web | Local file uploads with size/type validation | — |
| `graphql` | Web | Strawberry GraphQL query and mutation | — |
| `s3` | Operations | S3-compatible storage backend | `uploads` |
| `testcontainers` | Testing | PostgreSQL/Redis integration fixtures | `postgres`, `redis` |
| `sentry` | Observability | Sentry error reporting, disabled without a DSN | — |
| `prometheus` | Observability | Prometheus instrumentation and `/metrics` | — |
| `opentelemetry` | Observability | OTLP tracing for FastAPI, SQLAlchemy, and Redis | — |
| `docker` | Operations | Dockerfile and .dockerignore | — |
| `compose` | Operations | Compose stack for the app, PostgreSQL, and Redis | — |
| `makefile` | Operations | Common development targets | — |
| `ci` | Operations | GitHub Actions workflow | — |
| `ci-gitlab` | Operations | GitLab CI pipeline | — |
| `ci-bitbucket` | Operations | Bitbucket Pipelines configuration | — |
| `security-scan` | Operations | pip-audit, Bandit, detect-secrets, and CycloneDX SBOM | — |
| `kubernetes` | Operations | Deployment, Service, ConfigMap, and Ingress | — |
| `pre-commit` | Operations | Ruff, mypy, and pyright hooks | — |

Every generated project includes FastAPI, Uvicorn, Pydantic Settings,
`python-multipart`, pytest, httpx2, Ruff, mypy, and pyright.

## Generated project

```text
my-service/
├── pyproject.toml
├── .python-version
├── .gitignore
├── .fastapi-initializr.json
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

Run it:

```sh
unzip my-service.zip
cd my-service
uv sync
uv run fastapi dev
```

`.fastapi-initializr.json` records the template version, the resolved options,
and a SHA-256 digest for every generated file. Keep it in version control; the
`update` command uses it to detect local edits before overwriting files.

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
```

The CLI uses the same validation and templates as the API. `--lock` runs
`uv lock` in the generated project. `--dry-run` prints the file plan without
writing, and `--json` prints a machine-readable summary.

`update` re-renders the project from `.fastapi-initializr.json` and writes files
that still match the recorded digests. It aborts with exit code `3` when a file
was edited locally; rerun with `--force` to overwrite those files. `--dry-run`
prints the plan without writing.

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

The image uses `python:3.13-slim-trixie` with a pinned uv 0.13.6 binary,
installs the project non-editable from `uv.lock`, runs as the unprivileged
`app` user, and exposes `/health` for its healthcheck. CI builds the image,
records its size, and smoke-tests `/health`.

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
├── generation/          # spec, catalog, renderer, archive, preview
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
- Generated projects are never executed inside a web request.
- Generation is bounded by file-count and archive-size limits.

## Status

Local-first MVP. The generator is stateless and intended to run on your machine
or a trusted local network. Public deployment is not a goal. If you expose it
beyond localhost, add rate limiting and hardening first.
