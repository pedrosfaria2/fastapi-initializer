"""Plan and apply safe project updates from the generated manifest."""

from __future__ import annotations

import difflib
import json
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
    """Write planned changes, preserving locally modified files."""
    if plan.has_conflicts and not force:
        raise UpdateError("Local changes conflict with the update.")
    for path in (*plan.added, *plan.updated, *plan.merged):
        _write(project_dir, path, plan.files[path])
    if force:
        for path in plan.conflicted:
            _write(project_dir, path, plan.files[path])
        for path in plan.obsolete:
            _remove(project_dir, path)
    for path in plan.removable:
        _remove(project_dir, path)
    _write(project_dir, MANIFEST_NAME, plan.files[MANIFEST_NAME])


def _write(project_dir: Path, path: str, content: str) -> None:
    target = _contained(project_dir, path)
    if target.is_symlink():
        raise UpdateError(f"Cannot write {path}: target is a symlink.")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _remove(project_dir: Path, path: str) -> None:
    target = _contained(project_dir, path)
    try:
        if target.is_symlink() or target.is_file():
            target.unlink()
    except OSError as exc:
        raise UpdateError(f"Cannot remove {path}: {exc}") from exc
