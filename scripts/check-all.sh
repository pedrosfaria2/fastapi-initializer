#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

bash scripts/check.sh
uv run python scripts/check_generated_projects.py --case all
