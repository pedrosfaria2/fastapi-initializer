"""Plan and apply safe project updates from the generated manifest."""

import difflib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

from fastapi_initializr.generation.manifest import (
    MANIFEST_NAME,
    TEMPLATE_VERSION,
    file_digest,
)
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec


class UpdateError(Exception):
    """The project cannot be updated safely."""


_STAGE_DIR = ".fastapi-initializr-stage"
_BACKUP_DIR = ".fastapi-initializr-backup"
_JOURNAL_NAME = "journal.json"


@dataclass(frozen=True, slots=True)
class UpdatePlan:
    """Files to change, merge, remove, or leave untouched."""

    added: tuple[str, ...]
    updated: tuple[str, ...]
    merged: tuple[str, ...]
    conflicted: tuple[str, ...]
    unchanged: tuple[str, ...]
    removable: tuple[str, ...]
    obsolete: tuple[str, ...]
    files: dict[str, str]

    @property
    def has_conflicts(self) -> bool:
        """Return whether any local edits block an update."""
        return len(self.conflicted) > 0

    @property
    def has_changes(self) -> bool:
        """Return whether applying the plan changes the project."""
        return bool(self.added or self.updated or self.merged or self.removable)


def _safe_path(path: str) -> bool:
    pure = PurePosixPath(path)
    return (
        bool(path)
        and "\x00" not in path
        and "\\" not in path
        and not pure.is_absolute()
        and ".." not in pure.parts
        and pure.name not in {"", "."}
    )


def _contained(project_dir: Path, path: str) -> Path:
    if not _safe_path(path):
        raise UpdateError(f"Unsafe manifest path: {path!r}.")
    root = project_dir.resolve()
    target = (project_dir / path).resolve()
    if target != root and root not in target.parents:
        raise UpdateError(f"Manifest path escapes the project: {path!r}.")
    return project_dir / path


def _read_manifest(project_dir: Path) -> dict[str, Any]:
    path = project_dir / MANIFEST_NAME
    if not path.is_file():
        raise UpdateError(f"No {MANIFEST_NAME} found in {project_dir}.")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateError(f"Cannot read {MANIFEST_NAME}: {exc}") from exc
    if not isinstance(raw, dict):
        raise UpdateError(f"{MANIFEST_NAME} must contain a JSON object.")
    manifest = cast("dict[str, Any]", raw)
    if manifest.get("templateVersion") != TEMPLATE_VERSION:
        raise UpdateError(
            f"Unsupported template version {manifest.get('templateVersion')!r}; "
            f"this generator supports {TEMPLATE_VERSION}."
        )
    return manifest


def _spec_from_manifest(manifest: dict[str, Any]) -> ProjectSpec:
    spec_data = manifest.get("spec")
    if not isinstance(spec_data, dict):
        raise UpdateError(f"{MANIFEST_NAME} is missing the spec.")
    spec_values = cast("dict[str, Any]", spec_data)
    # Older manifests recorded the removed FastAPI selector.
    spec_values.pop("fastapi", None)
    try:
        return ProjectSpec(**spec_values)
    except (TypeError, ValueError) as exc:
        raise UpdateError(f"Manifest spec is invalid: {exc}") from exc


def read_project_spec(project_dir: Path) -> ProjectSpec:
    """Read and validate the spec recorded in a project manifest."""
    return _spec_from_manifest(_read_manifest(project_dir))


def _hunks(base: list[str], other: list[str]) -> list[tuple[int, int, list[str]]]:
    hunks: list[tuple[int, int, list[str]]] = []
    matcher = difflib.SequenceMatcher(None, base, other, autojunk=False)
    for tag, first, last, other_first, other_last in matcher.get_opcodes():
        if tag != "equal":
            hunks.append((first, last, other[other_first:other_last]))
    return hunks


def _overlaps(
    first: tuple[int, int, list[str]],
    second: tuple[int, int, list[str]],
) -> bool:
    first_start, first_end, _ = first
    second_start, second_end, _ = second
    if first_start == first_end and second_start == second_end:
        return first_start == second_start
    if first_start == first_end:
        return second_start < first_start < second_end
    if second_start == second_end:
        return first_start < second_start < first_end
    return max(first_start, second_start) < min(first_end, second_end)


def merge_three_way(base: str, local: str, new: str) -> str | None:
    """Merge disjoint local and template changes; return None on overlap."""
    if local == base:
        return new
    if new == base:
        return local
    if local == new:
        return local
    base_lines = base.splitlines(keepends=True)
    local_lines = local.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    local_hunks = _hunks(base_lines, local_lines)
    new_hunks = _hunks(base_lines, new_lines)
    if any(_overlaps(local_hunk, new_hunk) for local_hunk in local_hunks for new_hunk in new_hunks):
        return None
    combined = sorted(
        (*local_hunks, *new_hunks),
        key=lambda hunk: (hunk[0], hunk[1]),
        reverse=True,
    )
    result = list(base_lines)
    for start, end, replacement in combined:
        result[start:end] = replacement
    return "".join(result)


def plan_update(project_dir: Path, new_spec: ProjectSpec | None = None) -> UpdatePlan:
    """Compare the project on disk with a fresh render of the target spec."""
    _recover_interrupted(project_dir)
    manifest = _read_manifest(project_dir)
    old_spec = _spec_from_manifest(manifest)
    target_spec = new_spec or old_spec
    file_data = manifest.get("files")
    if not isinstance(file_data, dict):
        raise UpdateError(f"{MANIFEST_NAME} is missing file digests.")
    file_values = cast("dict[str, Any]", file_data)
    recorded: dict[str, str] = {}
    for path, digest in file_values.items():
        if _safe_path(path) and isinstance(digest, str):
            recorded[path] = digest

    old_files = render_project(old_spec)
    new_files = render_project(target_spec)
    old_files.pop(MANIFEST_NAME, None)
    new_files_without_manifest = dict(new_files)
    new_files_without_manifest.pop(MANIFEST_NAME, None)

    added: list[str] = []
    updated: list[str] = []
    merged: list[str] = []
    conflicted: list[str] = []
    unchanged: list[str] = []
    files: dict[str, str] = {}
    for path, new_content in new_files_without_manifest.items():
        files[path] = new_content
        target = _contained(project_dir, path)
        if not target.exists():
            added.append(path)
            continue
        if target.is_symlink() or not target.is_file():
            conflicted.append(path)
            files[path] = new_content
            continue
        try:
            local = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise UpdateError(f"Cannot read {path}: {exc}") from exc
        if local == new_content:
            unchanged.append(path)
            continue
        recorded_digest = recorded.get(path)
        if recorded_digest == file_digest(local):
            updated.append(path)
            files[path] = new_content
            continue
        base = old_files.get(path)
        if base is None or file_digest(base) != recorded_digest:
            conflicted.append(path)
            files[path] = new_content
            continue
        if new_content == base:
            unchanged.append(path)
            continue
        merged_content = merge_three_way(base, local, new_content)
        if merged_content is None:
            conflicted.append(path)
            files[path] = new_content
            continue
        merged.append(path)
        files[path] = merged_content

    removable: list[str] = []
    obsolete: list[str] = []
    candidates = (set(recorded) | set(old_files)) - set(new_files_without_manifest)
    candidates.discard(MANIFEST_NAME)
    for path in sorted(candidates):
        target = _contained(project_dir, path)
        if not target.exists():
            continue
        if target.is_symlink() or not target.is_file():
            obsolete.append(path)
            continue
        try:
            local = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            obsolete.append(path)
            continue
        if recorded.get(path) == file_digest(local):
            removable.append(path)
        else:
            obsolete.append(path)

    files[MANIFEST_NAME] = new_files[MANIFEST_NAME]
    return UpdatePlan(
        added=tuple(added),
        updated=tuple(updated),
        merged=tuple(merged),
        conflicted=tuple(conflicted),
        unchanged=tuple(unchanged),
        removable=tuple(removable),
        obsolete=tuple(obsolete),
        files=files,
    )


def apply_update(plan: UpdatePlan, project_dir: Path, *, force: bool = False) -> None:
    """Apply planned changes atomically, preserving locally modified files."""
    if plan.has_conflicts and not force:
        raise UpdateError("Local changes conflict with the update.")

    writes = [*plan.added, *plan.updated, *plan.merged]
    removals = [*plan.removable]
    if force:
        writes.extend(plan.conflicted)
        removals.extend(plan.obsolete)

    _recover_interrupted(project_dir)
    _prepare_targets(project_dir, (*writes, *removals, MANIFEST_NAME))

    staged = {path: plan.files[path] for path in writes}
    staged[MANIFEST_NAME] = plan.files[MANIFEST_NAME]
    try:
        stage = _stage_files(project_dir, staged)
        backup = _create_backup(project_dir)
        _write_journal(
            backup,
            {
                path: _contained(project_dir, path).exists()
                for path in (*writes, *removals, MANIFEST_NAME)
            },
        )
    except Exception as exc:
        _remove_tree(project_dir / _STAGE_DIR)
        _remove_tree(project_dir / _BACKUP_DIR)
        raise UpdateError(f"Cannot prepare the update: {exc}") from exc

    try:
        for path in writes:
            target = _contained(project_dir, path)
            _backup_file(project_dir, backup, path)
            target.parent.mkdir(parents=True, exist_ok=True)
            _replace(_contained(stage, path), target)
        for path in removals:
            _backup_file(project_dir, backup, path)
        _backup_file(project_dir, backup, MANIFEST_NAME)
        _replace(_contained(stage, MANIFEST_NAME), project_dir / MANIFEST_NAME)
    except Exception as exc:
        try:
            _restore_backup(project_dir, backup)
        except Exception as rollback_error:
            raise UpdateError(f"Update failed and rollback also failed: {rollback_error}") from exc
        _remove_tree(stage)
        raise UpdateError(f"Update failed and was rolled back: {exc}") from exc

    _remove_tree(stage)
    # Removing the journal commits the update. A leftover backup without a
    # journal is discarded on the next run instead of restoring stale files.
    _remove_tree(backup / _JOURNAL_NAME)
    _remove_tree(backup)


def _remove_tree(path: Path) -> None:
    """Remove a file, symlink, or directory tree when it exists."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def _prepare_targets(project_dir: Path, paths: tuple[str, ...]) -> None:
    """Reject unsafe or non-regular targets before any mutation."""
    for path in paths:
        target = _contained(project_dir, path)
        if target.is_symlink():
            raise UpdateError(f"Cannot update {path}: target is a symlink.")
        if target.exists() and not target.is_file():
            raise UpdateError(f"Cannot update {path}: target is not a regular file.")


def _stage_files(project_dir: Path, files: dict[str, str]) -> Path:
    """Write every new file into a staging directory first."""
    stage = project_dir / _STAGE_DIR
    _remove_tree(stage)
    stage.mkdir()
    for path, content in files.items():
        target = _contained(stage, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return stage


def _create_backup(project_dir: Path) -> Path:
    """Create an empty backup directory inside the project."""
    backup = project_dir / _BACKUP_DIR
    _remove_tree(backup)
    backup.mkdir()
    return backup


def _write_journal(backup: Path, targets: dict[str, bool]) -> None:
    """Record which targets existed before the update started."""
    (backup / _JOURNAL_NAME).write_text(
        json.dumps({"targets": targets}),
        encoding="utf-8",
    )


def _read_journal(backup: Path) -> dict[str, bool]:
    """Read and validate the recovery journal."""
    try:
        raw = cast(object, json.loads((backup / _JOURNAL_NAME).read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError) as exc:
        raise UpdateError(f"Cannot recover an interrupted update: {exc}") from exc
    if not isinstance(raw, dict):
        raise UpdateError("Cannot recover an interrupted update: invalid journal.")
    data = cast("dict[object, object]", raw)
    targets = data.get("targets")
    if not isinstance(targets, dict):
        raise UpdateError("Cannot recover an interrupted update: invalid journal.")
    values = cast("dict[object, object]", targets)
    journal: dict[str, bool] = {}
    for path, existed in values.items():
        if not isinstance(path, str) or not isinstance(existed, bool):
            raise UpdateError("Cannot recover an interrupted update: invalid journal.")
        journal[path] = existed
    return journal


def _backup_file(project_dir: Path, backup: Path, path: str) -> None:
    """Move an existing target into the backup directory."""
    target = _contained(project_dir, path)
    if not target.exists():
        return
    destination = _contained(backup, path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    _replace(target, destination)


def _restore_backup(project_dir: Path, backup: Path) -> None:
    """Restore every journal target from the backup and remove new files."""
    for path, existed in _read_journal(backup).items():
        target = _contained(project_dir, path)
        source = _contained(backup, path)
        if source.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            _replace(source, target)
        elif not existed and target.is_file():
            target.unlink()
    _remove_tree(backup)


def _recover_interrupted(project_dir: Path) -> None:
    """Restore an interrupted update, or discard a completed backup."""
    backup = project_dir / _BACKUP_DIR
    stage = project_dir / _STAGE_DIR
    if backup.is_symlink():
        raise UpdateError("Cannot recover an interrupted update: backup is a symlink.")
    if backup.is_dir():
        if (backup / _JOURNAL_NAME).is_file():
            _restore_backup(project_dir, backup)
        else:
            _remove_tree(backup)
    _remove_tree(stage)


def _replace(source: Path, target: Path) -> None:
    source.replace(target)
