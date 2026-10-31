"""Generate representative projects and run their real quality gates."""

from __future__ import annotations

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
    "database": ProjectSpec(
        name="database-service",
        dependencies=frozenset({"sqlalchemy", "alembic"}),
    ),
    "auth": ProjectSpec(
        name="auth-service",
        dependencies=frozenset({"sqlalchemy", "auth-jwt"}),
    ),
    "full": ProjectSpec(
        name="full-service",
        dependencies=frozenset(
            {"sqlalchemy", "alembic", "postgres", "cors", "docker", "ci", "pre-commit"}
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
