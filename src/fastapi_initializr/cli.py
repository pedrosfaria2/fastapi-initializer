"""Local command-line interface for the FastAPI Initializr."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from fastapi_initializr.generation.catalog import metadata
from fastapi_initializr.generation.constants import (
    DEFAULT_FASTAPI_VERSION,
    DEFAULT_PYTHON_VERSION,
)
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("name", help="Project and distribution name.")
    parser.add_argument("--package", default=None, help="Import package name.")
    parser.add_argument("--description", default="A FastAPI service")
    parser.add_argument("--version", default="0.1.0", help="Project version.")
    parser.add_argument("--author", default="", help="Optional author name.")
    parser.add_argument("--python", default=DEFAULT_PYTHON_VERSION)
    parser.add_argument("--fastapi", default=DEFAULT_FASTAPI_VERSION)
    parser.add_argument("--base-dir", default=None, dest="base_dir")
    parser.add_argument("--application-name", default=None, dest="application_name")
    parser.add_argument(
        "--dependency",
        action="append",
        default=[],
        dest="dependencies",
        help="Dependency id; repeat for multiple features.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(),
        help="Parent directory for the generated project.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing project directory.",
    )
    parser.add_argument(
        "--lock",
        action="store_true",
        help="Run `uv lock` after writing the project.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="fastapi-initializr",
        description="Generate a ready-to-run FastAPI project.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    new_parser = subparsers.add_parser("new", help="Generate a project directory.")
    _add_common_options(new_parser)

    subparsers.add_parser("list", help="List dependency ids and groups.")
    subparsers.add_parser("metadata", help="Print the metadata document as JSON.")
    return parser


def _new(args: argparse.Namespace) -> int:
    try:
        spec = ProjectSpec(
            name=args.name,
            package=args.package,
            description=args.description,
            version=args.version,
            author=args.author,
            python=args.python,
            fastapi=args.fastapi,
            base_dir=args.base_dir,
            application_name=args.application_name,
            dependencies=frozenset(args.dependencies),
        )
    except ValidationError as exc:
        print("Invalid project options:", file=sys.stderr)
        for error in exc.errors(include_url=False, include_context=False):
            print(f"- {error['msg']}", file=sys.stderr)
        return 2

    target = Path(args.output) / spec.archive_root
    if target.exists() and not args.force:
        print(f"Target already exists: {target}. Use --force to overwrite.", file=sys.stderr)
        return 1

    files = render_project(spec)
    target.mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    if args.lock:
        environment = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
        environment["UV_NO_PROGRESS"] = "1"
        uv = shutil.which("uv")
        if uv is None:
            print("uv was not found in PATH", file=sys.stderr)
            return 1
        try:
            subprocess.run(  # noqa: S603 - fixed uv executable, not user input
                [uv, "lock"],
                cwd=target,
                check=True,
                env=environment,
            )
        except subprocess.CalledProcessError:
            print("uv lock failed", file=sys.stderr)
            return 1

    print(target)
    return 0


def _list() -> int:
    catalog = metadata()
    for group in catalog.dependencies.groups:
        print(f"{group.name}:")
        for dependency in group.values:
            print(f"  {dependency.id:<16} {dependency.name}")
    return 0


def _metadata() -> int:
    print(metadata().model_dump_json(by_alias=True, indent=2))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI and return an exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "new":
        return _new(args)
    if args.command == "list":
        return _list()
    if args.command == "metadata":
        return _metadata()
    raise AssertionError(f"Unknown command: {args.command}")
