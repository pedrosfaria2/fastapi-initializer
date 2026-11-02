"""Local JSON plugin features."""

import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from fastapi_initializr.cli import main
from fastapi_initializr.generation.catalog import metadata
from fastapi_initializr.generation.plugins import install_plugins
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.requirements import render_requirements
from fastapi_initializr.generation.spec import ProjectSpec


def _plugin_directory(tmp_path: Path, **overrides: Any) -> Path:
    payload: dict[str, Any] = {
        "id": "custom-feature",
        "name": "Custom feature",
        "description": "Adds a custom module and dependency.",
        "group": "Custom",
        "packages": ["example-lib"],
        "devPackages": ["example-dev"],
        "files": [
            {
                "path": "src/{{ spec.package }}/custom.py",
                "template": 'FEATURE = "{{ spec.name }}"\n',
            }
        ],
    }
    payload.update(overrides)
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    (plugin_dir / f"{payload['id']}.json").write_text(json.dumps(payload), encoding="utf-8")
    return plugin_dir


def test_install_adds_the_feature_to_metadata_and_rendering(tmp_path: Path) -> None:
    plugin_dir = _plugin_directory(tmp_path)

    assert install_plugins(plugin_dir) == 1

    catalog = metadata()
    groups = {group.name: group for group in catalog.dependencies.groups}
    assert "Custom" in groups
    assert [value.id for value in groups["Custom"].values] == ["custom-feature"]

    spec = ProjectSpec(name="my-service", dependencies=frozenset({"custom-feature"}))
    files = render_project(spec)
    assert files["src/my_service/custom.py"] == 'FEATURE = "my-service"\n'
    assert "example-lib" in files["pyproject.toml"]
    assert "example-dev" in files["pyproject.toml"]
    assert "example-lib" in render_requirements(spec).splitlines()
    manifest = json.loads(files[".fastapi-initializr.json"])
    assert "src/my_service/custom.py" in manifest["files"]


def test_install_is_idempotent(tmp_path: Path) -> None:
    plugin_dir = _plugin_directory(tmp_path)

    assert install_plugins(plugin_dir) == 1
    assert install_plugins(plugin_dir) == 0
    ids = [
        value.id
        for group in metadata().dependencies.groups
        for value in group.values
        if value.id == "custom-feature"
    ]
    assert ids == ["custom-feature"]


def test_plugin_requirements_are_validated(tmp_path: Path) -> None:
    install_plugins(_plugin_directory(tmp_path, requires=["sqlalchemy"]))

    with pytest.raises(ValidationError, match="requires"):
        ProjectSpec(name="my-service", dependencies=frozenset({"custom-feature"}))
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"custom-feature", "sqlalchemy"}),
    )
    assert spec.has("custom-feature")


def test_plugin_rejects_unknown_references(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unknown dependency"):
        install_plugins(_plugin_directory(tmp_path, requires=["missing"]))


def test_plugin_rejects_duplicate_ids(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Duplicate dependency id"):
        install_plugins(_plugin_directory(tmp_path, id="sqlalchemy"))


def test_plugin_rejects_unsafe_file_paths(tmp_path: Path) -> None:
    files = [{"path": "../escape.py", "template": "x = 1\n"}]

    with pytest.raises(ValueError, match="Invalid plugin file path"):
        install_plugins(_plugin_directory(tmp_path, files=files))


def test_cli_new_uses_a_plugin_directory(tmp_path: Path) -> None:
    plugin_dir = _plugin_directory(tmp_path)
    output = tmp_path / "output"

    exit_code = main(
        [
            "new",
            "my-service",
            "--output",
            str(output),
            "--plugin-dir",
            str(plugin_dir),
            "--dependency",
            "custom-feature",
        ]
    )

    assert exit_code == 0
    assert (output / "my-service" / "src" / "my_service" / "custom.py").exists()


def test_cli_update_accepts_a_plugin_directory(tmp_path: Path) -> None:
    plugin_dir = _plugin_directory(tmp_path)
    output = tmp_path / "output"
    assert (
        main(
            [
                "new",
                "my-service",
                "--output",
                str(output),
                "--plugin-dir",
                str(plugin_dir),
                "--dependency",
                "custom-feature",
            ]
        )
        == 0
    )

    assert (
        main(
            [
                "update",
                str(output / "my-service"),
                "--plugin-dir",
                str(plugin_dir),
            ]
        )
        == 0
    )
