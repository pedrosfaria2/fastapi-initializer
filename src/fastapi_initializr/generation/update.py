"""Plan and apply safe project updates from the generated manifest."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

from fastapi_initializr.generation.manifest import MANIFEST_NAME, TEMPLATE_VERSION
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec


class UpdateError(Exception):
    """The project cannot be updated safely."""


@dataclass(frozen=True, slots=True)
class UpdatePlan:
    """Files to change and files left untouched."""

    added: tuple[str, ...]
    updated: tuple[str, ...]
    conflicted: tuple[str, ...]
    unchanged: tuple[str, ...]
    obsolete: tuple[str, ...]
    files: dict[str, str]

    @property
    def has_conflicts(self) -> bool:
        """Return whether any local edits block an update."""
        return len(self.conflicted) > 0


def _digest_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _safe_path(path: str) -> bool:
    pure = PurePosixPath(path)
    return bool(path) and not pure.is_absolute() and ".." not in pure.parts


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


def plan_update(project_dir: Path) -> UpdatePlan:
    """Compare the project on disk with a fresh render."""
    manifest = _read_manifest(project_dir)
    spec_data = manifest.get("spec")
    file_data = manifest.get("files")
    if not isinstance(spec_data, dict) or not isinstance(file_data, dict):
        raise UpdateError(f"{MANIFEST_NAME} is missing the spec or file digests.")
    spec_values = cast("dict[str, Any]", spec_data)
    file_values = cast("dict[str, Any]", file_data)
    # Older manifests recorded the removed FastAPI selector.
    spec_values.pop("fastapi", None)
    try:
        spec = ProjectSpec(**spec_values)
    except (TypeError, ValueError) as exc:
        raise UpdateError(f"Manifest spec is invalid: {exc}") from exc

    files = render_project(spec)
    recorded: dict[str, str] = {}
    for path, digest in file_values.items():
        if _safe_path(path) and isinstance(digest, str):
            recorded[path] = digest
    added: list[str] = []
    updated: list[str] = []
    conflicted: list[str] = []
    unchanged: list[str] = []
    for path, content in files.items():
        if path == MANIFEST_NAME:
            continue
        target = project_dir / path
        if target.exists() and not target.is_file():
            raise UpdateError(f"Cannot update {path}: target is not a file.")
        new_digest = _digest_bytes(content.encode("utf-8"))
        if not target.is_file():
            added.append(path)
            continue
        current = _digest_bytes(target.read_bytes())
        if current == new_digest:
            unchanged.append(path)
        elif current == recorded.get(path):
            updated.append(path)
        else:
            conflicted.append(path)
    obsolete = sorted(set(recorded) - set(files))
    return UpdatePlan(
        added=tuple(added),
        updated=tuple(updated),
        conflicted=tuple(conflicted),
        unchanged=tuple(unchanged),
        obsolete=tuple(obsolete),
        files=files,
    )


def apply_update(plan: UpdatePlan, project_dir: Path, *, force: bool = False) -> None:
    """Write planned changes, preserving locally modified files."""
    if plan.has_conflicts and not force:
        raise UpdateError("Local changes conflict with the update.")
    for path in (*plan.added, *plan.updated):
        _write(project_dir, path, plan.files[path])
    if force:
        for path in plan.conflicted:
            _write(project_dir, path, plan.files[path])
    _write(project_dir, MANIFEST_NAME, plan.files[MANIFEST_NAME])


def _write(project_dir: Path, path: str, content: str) -> None:
    target = project_dir / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
