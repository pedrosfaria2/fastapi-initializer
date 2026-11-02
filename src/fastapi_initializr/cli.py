"""Local command-line interface for the FastAPI Initializr."""

import argparse
import difflib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from fastapi_initializr.generation.catalog import (
    DEPENDENCIES,
    GROUP_ORDER,
    PRESETS,
    metadata,
)
from fastapi_initializr.generation.constants import (
    DEFAULT_PYTHON_VERSION,
    DEFAULT_STRUCTURE,
    SUPPORTED_PYTHON_VERSIONS,
)
from fastapi_initializr.generation.manifest import MANIFEST_NAME
from fastapi_initializr.generation.plugins import install_plugins
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec
from fastapi_initializr.generation.update import (
    UpdateError,
    UpdatePlan,
    apply_update,
    plan_update,
    read_project_spec,
)

_COMMANDS = ("new", "update", "add", "remove", "diff", "list", "metadata", "completion")
_NEW_OPTIONS = (
    "--package",
    "--description",
    "--version",
    "--author",
    "--structure",
    "--python",
    "--preset",
    "--base-dir",
    "--application-name",
    "--dependency",
    "--output",
    "--force",
    "--lock",
    "--dry-run",
    "--json",
    "--list-dependencies",
)
_CHANGE_OPTIONS = ("--dry-run", "--json", "--force", "--plugin-dir")


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "name",
        nargs="?",
        default=None,
        help="Project and distribution name.",
    )
    parser.add_argument("--package", default=None, help="Import package name.")
    parser.add_argument("--description", default="A FastAPI service")
    parser.add_argument("--version", default="0.1.0", help="Project version.")
    parser.add_argument("--author", default="", help="Optional author name.")
    parser.add_argument("--structure", default=DEFAULT_STRUCTURE)
    parser.add_argument("--python", default=DEFAULT_PYTHON_VERSION)
    parser.add_argument(
        "--preset",
        default="custom",
        help="Preset id: api, db-auth, worker, full, or custom.",
    )
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Print the planned files without writing them.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print a machine-readable summary.",
    )
    parser.add_argument(
        "--list-dependencies",
        action="store_true",
        dest="list_dependencies",
        help="List dependency ids and exit.",
    )
    parser.add_argument(
        "--plugin-dir",
        type=Path,
        default=None,
        dest="plugin_dir",
        help="Directory of local JSON plugin features.",
    )


def _add_change_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "items",
        nargs="+",
        metavar="FEATURE... PROJECT",
        help="One or more feature ids followed by the project directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Print the plan without writing files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print a machine-readable plan.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite conflicting files and remove obsolete ones.",
    )
    parser.add_argument(
        "--plugin-dir",
        type=Path,
        default=None,
        dest="plugin_dir",
        help="Directory of local JSON plugin features.",
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

    update_parser = subparsers.add_parser(
        "update",
        help="Update a generated project from its manifest.",
    )
    update_parser.add_argument("project", type=Path, nargs="?", default=Path())
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Report planned changes without writing files.",
    )
    update_parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite files that changed since generation.",
    )
    update_parser.add_argument(
        "--plugin-dir",
        type=Path,
        default=None,
        dest="plugin_dir",
        help="Directory of local JSON plugin features.",
    )

    add_parser = subparsers.add_parser(
        "add",
        help="Add features to an existing generated project.",
    )
    _add_change_options(add_parser)

    remove_parser = subparsers.add_parser(
        "remove",
        help="Remove features from an existing generated project.",
    )
    _add_change_options(remove_parser)

    diff_parser = subparsers.add_parser(
        "diff",
        help="Show template differences for an existing project.",
    )
    diff_parser.add_argument("project", type=Path, nargs="?", default=Path())
    diff_parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print a machine-readable plan.",
    )
    diff_parser.add_argument(
        "--plugin-dir",
        type=Path,
        default=None,
        dest="plugin_dir",
        help="Directory of local JSON plugin features.",
    )

    list_parser = subparsers.add_parser("list", help="List dependency ids and groups.")
    list_parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print the catalog as JSON.",
    )

    subparsers.add_parser("metadata", help="Print the metadata document as JSON.")

    completion_parser = subparsers.add_parser(
        "completion",
        help="Print a shell completion script.",
    )
    completion_parser.add_argument(
        "shell",
        nargs="?",
        default="bash",
        choices=("bash", "zsh", "fish"),
    )
    return parser


def _list_dependencies(as_json: bool) -> int:
    if as_json:
        rows = [
            {"id": dependency.id, "name": dependency.name, "group": dependency.group}
            for dependency in DEPENDENCIES.values()
        ]
        print(json.dumps(rows, indent=2))
        return 0
    for group_name in GROUP_ORDER:
        print(f"{group_name}:")
        for dependency in DEPENDENCIES.values():
            if dependency.group == group_name:
                print(f"  {dependency.id:<16} {dependency.name}")
    return 0


def _install_plugin_dir(directory: Path | None) -> int | None:
    if directory is None:
        return None
    try:
        install_plugins(directory)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return None


def _new(args: argparse.Namespace) -> int:
    if args.list_dependencies:
        return _list_dependencies(args.as_json)
    if args.name is None:
        print("A project name is required.", file=sys.stderr)
        return 2
    plugin_error = _install_plugin_dir(args.plugin_dir)
    if plugin_error is not None:
        return plugin_error
    try:
        spec = ProjectSpec(
            name=args.name,
            package=args.package,
            description=args.description,
            version=args.version,
            author=args.author,
            structure=args.structure,
            python=args.python,
            preset=args.preset,
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
    files = render_project(spec)
    if args.dry_run:
        if args.as_json:
            print(
                json.dumps(
                    {"target": str(target), "files": sorted(files), "dryRun": True},
                    indent=2,
                )
            )
        else:
            for relative in files:
                print(target / relative)
        return 0

    if target.exists() and not args.force:
        print(f"Target already exists: {target}. Use --force to overwrite.", file=sys.stderr)
        return 1

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

    if args.as_json:
        print(
            json.dumps(
                {
                    "target": str(target),
                    "files": sorted(files),
                    "dependencies": sorted(spec.dependencies),
                    "preset": spec.preset,
                    "dryRun": False,
                },
                indent=2,
            )
        )
    else:
        print(target)
    return 0


def _plan_payload(
    plan: UpdatePlan,
    project: Path,
    *,
    dry_run: bool,
) -> dict[str, object]:
    return {
        "project": str(project),
        "dryRun": dry_run,
        "added": list(plan.added),
        "updated": list(plan.updated),
        "merged": list(plan.merged),
        "conflicted": list(plan.conflicted),
        "unchanged": list(plan.unchanged),
        "removable": list(plan.removable),
        "obsolete": list(plan.obsolete),
        "hasConflicts": plan.has_conflicts,
    }


def _print_plan(
    plan: UpdatePlan,
    project: Path,
    *,
    dry_run: bool,
    as_json: bool,
    force: bool,
) -> None:
    if as_json:
        print(json.dumps(_plan_payload(plan, project, dry_run=dry_run), indent=2))
        return
    prefix = "would " if dry_run else ""
    for path in plan.added:
        print(f"{prefix}add {path}")
    for path in plan.updated:
        print(f"{prefix}update {path}")
    for path in plan.merged:
        print(f"{prefix}merge {path}")
    for path in plan.conflicted:
        print(f"conflict {path} (locally modified)")
    for path in plan.removable:
        print(f"{prefix}remove {path}")
    for path in plan.obsolete:
        action = "remove" if force else "keep"
        print(f"{action} {path} (locally modified, obsolete)")
    print(f"{len(plan.unchanged)} unchanged")


def _split_features(features: list[str]) -> list[str]:
    result: list[str] = []
    for value in features:
        result.extend(part.strip() for part in value.split(",") if part.strip())
    return result


def _changed_spec(
    spec: ProjectSpec,
    features: list[str],
    *,
    remove: bool,
) -> ProjectSpec:
    selected = set(spec.dependencies)
    for feature_id in _split_features(features):
        if feature_id not in DEPENDENCIES:
            raise ValueError(f"Unknown dependency: {feature_id}.")
        if remove:
            if feature_id not in selected:
                raise ValueError(f"Feature '{feature_id}' is not selected.")
            selected.remove(feature_id)
        else:
            selected.add(feature_id)
    data = spec.model_dump(mode="json")
    data["dependencies"] = sorted(selected)
    data["preset"] = "custom"
    try:
        return ProjectSpec.model_validate(data)
    except ValidationError as exc:
        messages = "; ".join(
            str(error["msg"]) for error in exc.errors(include_url=False, include_context=False)
        )
        raise ValueError(messages) from exc


def _project_and_features(items: list[str]) -> tuple[Path, list[str]]:
    if len(items) < 2:
        raise ValueError("Provide one or more features followed by the project directory.")
    project = Path(items[-1])
    if not project.is_dir():
        raise ValueError(f"Project directory not found: {project}")
    return project, items[:-1]


def _change(args: argparse.Namespace, *, remove: bool) -> int:
    plugin_error = _install_plugin_dir(args.plugin_dir)
    if plugin_error is not None:
        return plugin_error
    try:
        project, features = _project_and_features(args.items)
        new_spec = _changed_spec(
            read_project_spec(project),
            features,
            remove=remove,
        )
        plan = plan_update(project, new_spec)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except UpdateError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    _print_plan(
        plan,
        project,
        dry_run=args.dry_run,
        as_json=args.as_json,
        force=args.force,
    )
    if plan.has_conflicts and not args.force:
        print(
            "Local changes block the change; rerun with --force to overwrite them.",
            file=sys.stderr,
        )
        return 3
    if not plan.has_changes and not plan.has_conflicts:
        if not args.as_json:
            print("No file changes.")
        if args.dry_run:
            return 0
    if args.dry_run:
        return 0
    try:
        apply_update(plan, project, force=args.force)
    except UpdateError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not args.as_json:
        action = "Removed" if remove else "Added"
        print(f"{action} features in {project} ({len(plan.unchanged)} unchanged)")
    return 0


def _print_unified_diffs(project: Path, plan: UpdatePlan) -> None:
    for path, new_content in plan.files.items():
        if path == MANIFEST_NAME:
            continue
        target = project / path
        old_content = target.read_text(encoding="utf-8") if target.is_file() else ""
        if old_content == new_content:
            continue
        diff = difflib.unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
        print("".join(diff), end="")
    for path in plan.removable:
        print(f"remove {path}")
    for path in plan.obsolete:
        print(f"keep {path} (locally modified, obsolete)")


def _diff(args: argparse.Namespace) -> int:
    plugin_error = _install_plugin_dir(args.plugin_dir)
    if plugin_error is not None:
        return plugin_error
    try:
        plan = plan_update(args.project)
    except UpdateError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if args.as_json:
        print(json.dumps(_plan_payload(plan, args.project, dry_run=True), indent=2))
        return 0
    _print_plan(
        plan,
        args.project,
        dry_run=True,
        as_json=False,
        force=False,
    )
    _print_unified_diffs(args.project, plan)
    return 0


def _update(args: argparse.Namespace) -> int:
    plugin_error = _install_plugin_dir(args.plugin_dir)
    if plugin_error is not None:
        return plugin_error
    try:
        plan = plan_update(args.project)
    except UpdateError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    _print_plan(
        plan,
        args.project,
        dry_run=args.dry_run,
        as_json=False,
        force=args.force,
    )
    if plan.has_conflicts and not args.force:
        print(
            "Local changes block the update; rerun with --force to overwrite them.",
            file=sys.stderr,
        )
        return 3
    if args.dry_run:
        return 0

    try:
        apply_update(plan, args.project, force=args.force)
    except UpdateError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Updated {args.project} ({len(plan.unchanged)} unchanged)")
    return 0


def _bash_completion() -> str:
    dependencies = " ".join(sorted(DEPENDENCIES))
    presets = " ".join(preset.id for preset in PRESETS)
    pythons = " ".join(SUPPORTED_PYTHON_VERSIONS)
    options = " ".join((*_NEW_OPTIONS, *_CHANGE_OPTIONS))
    commands = " ".join(_COMMANDS)
    return f"""\
_fastapi_initializr() {{
    local cur prev
    cur="${{COMP_WORDS[COMP_CWORD]}}"
    prev="${{COMP_WORDS[COMP_CWORD-1]}}"
    case "$prev" in
        --dependency) COMPREPLY=($(compgen -W "{dependencies}" -- "$cur")); return ;;
        --preset) COMPREPLY=($(compgen -W "{presets}" -- "$cur")); return ;;
        --python) COMPREPLY=($(compgen -W "{pythons}" -- "$cur")); return ;;
    esac
    if [[ "$cur" == -* ]]; then
        COMPREPLY=($(compgen -W "{options}" -- "$cur")); return
    fi
    if [[ "$COMP_CWORD" -eq 1 ]]; then
        COMPREPLY=($(compgen -W "{commands}" -- "$cur")); return
    fi
}}
complete -F _fastapi_initializr fastapi-initializr
"""


def _zsh_completion() -> str:
    dependencies = " ".join(sorted(DEPENDENCIES))
    presets = " ".join(preset.id for preset in PRESETS)
    commands = " ".join(_COMMANDS)
    return f"""\
#compdef fastapi-initializr
_fastapi_initializr() {{
  local -a commands
  commands=({commands})
  _arguments -C '1:command:->command' '*::arg:->args'
  case $state in
    command) _describe 'command' commands ;;
    args) _values 'dependency' {dependencies} ;;
  esac
  case $words[2] in
    new) _values 'preset' {presets} ;;
  esac
}}
_fastapi_initializr "$@"
"""


def _fish_completion() -> str:
    dependencies = " ".join(sorted(DEPENDENCIES))
    presets = " ".join(preset.id for preset in PRESETS)
    lines = [
        "complete -c fastapi-initializr -f -n __fish_use_subcommand "
        f'-a "{command}" -d "{description}"'
        for command, description in (
            ("new", "Generate a project directory"),
            ("update", "Update a generated project"),
            ("add", "Add features to a project"),
            ("remove", "Remove features from a project"),
            ("diff", "Show template differences"),
            ("list", "List dependencies"),
            ("metadata", "Print metadata"),
            ("completion", "Print shell completion"),
        )
    ]
    lines.append(f'complete -c fastapi-initializr -l dependency -x -a "{dependencies}"')
    lines.append(f'complete -c fastapi-initializr -l preset -x -a "{presets}"')
    lines.append("complete -c fastapi-initializr -l dry-run")
    lines.append("complete -c fastapi-initializr -l json")
    return "\n".join(lines) + "\n"


def _completion(shell: str) -> int:
    scripts = {
        "bash": _bash_completion,
        "zsh": _zsh_completion,
        "fish": _fish_completion,
    }
    print(scripts[shell](), end="")
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
    if args.command == "update":
        return _update(args)
    if args.command == "add":
        return _change(args, remove=False)
    if args.command == "remove":
        return _change(args, remove=True)
    if args.command == "diff":
        return _diff(args)
    if args.command == "list":
        return _list_dependencies(args.as_json)
    if args.command == "metadata":
        return _metadata()
    if args.command == "completion":
        return _completion(args.shell)
    raise AssertionError(f"Unknown command: {args.command}")
