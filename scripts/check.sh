#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

uv lock --check
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pyright src
uv run pytest
uv build
