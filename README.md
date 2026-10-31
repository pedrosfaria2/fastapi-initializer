# FastAPI Initializr

A Spring Initializr-style generator for FastAPI projects. Choose a project name,
Python version, and optional features, then download a ready-to-run Python
project using `uv`, Ruff, mypy, pyright, and pytest.

## Features

- Metadata-driven web UI and HTTP API.
- Deterministic zip and tar.gz archives, plus standalone `pyproject.toml`.
- Searchable dependency catalog with docs links, compatibility rules, shift-click
  selection, Share, Reset, and keyboard generation.
- Safe project, package, version, and baseDir validation.
- Generated projects with `src/` layout, FastAPI app factory, health/readiness,
  request IDs, logging, error handlers, and tests.
- Optional SQLAlchemy CRUD, Alembic, PostgreSQL, JWT authentication, CORS,
  Docker/Compose, GitHub Actions, pre-commit, and coverage.
- Local CLI: `fastapi-initializr new`, `list`, `metadata`, and `--lock`.
- Generated projects pass Ruff, mypy, pyright, and pytest.
- Stateless: no accounts, database, saved projects, or server-side execution of
  generated code.

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
| `POST` | `/starter.zip` | Download a zip from JSON |
| `POST` | `/preview` | Preview from JSON |

The `/api/preview` and `/api/generate` aliases remain available.

Download a project:

```sh
curl -OJ 'http://127.0.0.1:8000/starter.zip?name=my-service&dependencies=sqlalchemy&dependencies=alembic'
```

Download a tar.gz or the build file:

```sh
curl -OJ 'http://127.0.0.1:8000/starter.tgz?name=my-service'
curl 'http://127.0.0.1:8000/pyproject.toml?name=my-service'
```

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
- `baseDir`: root directory inside the archive (defaults to `name`).
- `applicationName`: OpenAPI application title (defaults to `name`).
- `dependencies`: repeated ids or a comma-separated list.

## Options

| ID | Adds | Requires |
| --- | --- | --- |
| `sqlalchemy` | Async SQLAlchemy session and SQLite driver | — |
| `alembic` | Alembic configuration and migrations | `sqlalchemy` |
| `postgres` | Async PostgreSQL driver | `sqlalchemy` |
| `auth-jwt` | JWT registration, login, and protected `/auth/me` | `sqlalchemy` |
| `cors` | CORS middleware and settings | — |
| `docker` | Dockerfile and .dockerignore | — |
| `ci` | GitHub Actions workflow | — |
| `pre-commit` | Ruff, mypy, and pyright hooks | — |

Every generated project includes FastAPI, Uvicorn, Pydantic Settings,
`python-multipart`, pytest, httpx2, Ruff, mypy, and pyright.

## Generated project

```text
my-service/
├── pyproject.toml
├── .python-version
├── .gitignore
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
  --dependency sqlalchemy \
  --dependency alembic \
  --output .
```

Useful commands:

```sh
uv run fastapi-initializr list
uv run fastapi-initializr metadata
uv run fastapi-initializr new my-service --force
uv run fastapi-initializr new my-service --lock
```

The CLI uses the same validation and templates as the API. `--lock` runs
`uv lock` in the generated project.

## Development

```sh
uv sync --locked
bash scripts/check.sh
```

`scripts/check.sh` runs the lockfile check, Ruff, mypy, pyright, pytest, and
`uv build`.

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
