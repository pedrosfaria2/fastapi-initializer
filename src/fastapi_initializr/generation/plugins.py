"""Local JSON plugins that extend the dependency catalog."""

from __future__ import annotations

import json
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from fastapi_initializr.generation.catalog import (
    DEPENDENCIES,
    Dependency,
    PluginFile,
    clear_plugins,
    register_plugin,
)

_INSTALLED: set[Path] = set()


class PluginFileModel(BaseModel):
    """One inline template contributed by a plugin."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1, max_length=200)
    template: str


class PluginManifest(BaseModel):
    """A plugin feature definition."""

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    id: str = Field(pattern=r"^[a-z][a-z0-9-]{1,63}$")
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)
    group: str = Field(min_length=1, max_length=40)
    requires: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    packages: list[str] = Field(default_factory=list)
    dev_packages: list[str] = Field(default_factory=list, alias="devPackages")
    guide: str | None = None
    guide_title: str | None = Field(default=None, alias="guideTitle")
    reference: str | None = None
    files: list[PluginFileModel] = Field(default_factory=list[PluginFileModel])


def _validate_path(path: str) -> None:
    pure = PurePosixPath(path)
    if (
        pure.is_absolute()
        or ".." in pure.parts
        or pure.name in {"", "."}
        or "\\" in path
        or "\x00" in path
    ):
        raise ValueError(f"Invalid plugin file path: {path!r}")


def _read_manifest(path: Path) -> PluginManifest:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        manifest = PluginManifest.model_validate(data)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"Invalid plugin {path.name}: {exc}") from exc
    for file in manifest.files:
        _validate_path(file.path)
    return manifest


def load_plugin_directory(directory: Path) -> list[PluginManifest]:
    """Read and validate every ``*.json`` plugin in a directory."""
    if not directory.is_dir():
        raise ValueError(f"Plugin directory does not exist: {directory}")
    return [_read_manifest(path) for path in sorted(directory.glob("*.json"))]


def install_plugins(directory: Path) -> int:
    """Register a plugin directory in the active catalog.

    Installation is idempotent per resolved directory. Plugin directories are
    trusted local input: their templates render with the same Jinja environment
    as built-in templates.
    """
    resolved = directory.resolve()
    if resolved in _INSTALLED:
        return 0
    manifests = load_plugin_directory(resolved)
    available = set(DEPENDENCIES) | {manifest.id for manifest in manifests}
    known: set[str] = set()
    for manifest in manifests:
        if manifest.id in DEPENDENCIES or manifest.id in known:
            raise ValueError(f"Duplicate dependency id '{manifest.id}'.")
        for reference in (*manifest.requires, *manifest.conflicts):
            if reference not in available:
                raise ValueError(
                    f"Plugin '{manifest.id}' references unknown dependency '{reference}'."
                )
        known.add(manifest.id)

    for manifest in manifests:
        register_plugin(
            Dependency(
                id=manifest.id,
                name=manifest.name,
                description=manifest.description,
                group=manifest.group,
                requires=tuple(manifest.requires),
                conflicts=tuple(manifest.conflicts),
                packages=tuple(manifest.packages),
                dev_packages=tuple(manifest.dev_packages),
                files=tuple(file.path for file in manifest.files),
                guide=manifest.guide,
                guide_title=manifest.guide_title,
                reference=manifest.reference,
                plugin=True,
            ),
            tuple(
                PluginFile(
                    feature_id=manifest.id,
                    path=file.path,
                    template=file.template,
                )
                for file in manifest.files
            ),
        )
    _INSTALLED.add(resolved)
    return len(manifests)


def reset_plugins() -> None:
    """Remove installed plugins; intended for tests and explicit reloads."""
    clear_plugins()
    _INSTALLED.clear()
