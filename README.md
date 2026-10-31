# FastAPI Initializr

A Spring Initializr-style generator for FastAPI projects. Choose a project name,
Python version, and optional features, then download a ready-to-run Python
project using `uv`, Ruff, mypy, pyright, and pytest.

## Features

- Metadata-driven web UI and HTTP API.
- Downloadable, deterministic zip archive.
- Safe project and package name validation.
- Allowlisted dependency catalog.
- Generated projects with `src/` layout, FastAPI app factory, health endpoint,
  and tests.
- Optional SQLAlchemy, Alembic, PostgreSQL, CORS, Docker, GitHub Actions, and
  pre-commit.
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
| `GET` | `/api/metadata` | Option catalog |
| `GET` | `/api/preview` | Rendered file list and contents |
| `GET` | `/api/generate` | Download a zip |
| `POST` | `/api/generate` | Download a zip from JSON |

Download a project:

```sh
curl -OJ 'http://127.0.0.1:8000/api/generate?name=my-service&dependencies=sqlalchemy&dependencies=alembic'
```

Preview the same project:

```sh
curl 'http://127.0.0.1:8000/api/preview?name=my-service&dependencies=sqlalchemy&dependencies=alembic'
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
- `python`: `3.11`, `3.12`, `3.13`, or `3.14`.
- `dependencies`: repeated ids or a comma-separated list.

## Options

| ID | Adds | Requires |
| --- | --- | --- |
| `sqlalchemy` | Async SQLAlchemy session and SQLite driver | — |
| `alembic` | Alembic configuration and migrations | `sqlalchemy` |
| `postgres` | Async PostgreSQL driver | `sqlalchemy` |
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
│   ├── core/config.py
│   ├── schemas/
│   └── services/
└── tests/
    ├── conftest.py
    └── test_health.py
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

## Development

```sh
uv sync --locked
bash scripts/check.sh
```

`scripts/check.sh` runs the lockfile check, Ruff, mypy, pyright, pytest, and
`uv build`.

Validate the generated-project matrix:

```sh
uv run python scripts/check_generated_projects.py --case all
```

This generates minimal, database, and full-feature projects in a temporary
directory and runs each project's real `uv sync`, Ruff, mypy, pyright, and pytest
commands.

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
