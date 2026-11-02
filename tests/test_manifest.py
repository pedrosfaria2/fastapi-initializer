"""Generated-project template manifest."""

import hashlib
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from fastapi_initializr import __version__
from fastapi_initializr.generation.manifest import MANIFEST_NAME, TEMPLATE_VERSION
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec
from fastapi_initializr.generation.update import UpdateError, plan_update
from fastapi_initializr.services.generator import generate_project


def test_manifest_describes_every_other_file() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "auth-jwt"}),
    )
    files = render_project(spec)
    manifest = json.loads(files[MANIFEST_NAME])
    expected = set(files) - {MANIFEST_NAME}

    assert manifest["templateVersion"] == TEMPLATE_VERSION
    assert manifest["generatorVersion"] == __version__
    assert set(manifest["files"]) == expected
    for path in expected:
        digest = hashlib.sha256(files[path].encode("utf-8")).hexdigest()
        assert manifest["files"][path] == digest


def test_manifest_records_the_resolved_spec() -> None:
    spec = ProjectSpec(
        name="my-service",
        preset="db-auth",
        base_dir="custom-root",
        application_name="My API",
    )
    manifest = json.loads(render_project(spec)[MANIFEST_NAME])

    assert manifest["spec"]["name"] == "my-service"
    assert manifest["spec"]["package"] == "my_service"
    assert manifest["spec"]["base_dir"] == "custom-root"
    assert manifest["spec"]["application_name"] == "My API"
    assert manifest["spec"]["preset"] == "db-auth"
    assert manifest["spec"]["dependencies"] == sorted(spec.dependencies)


def test_manifest_is_deterministic() -> None:
    spec = ProjectSpec(name="my-service", dependencies=frozenset({"docker", "ci"}))

    assert render_project(spec)[MANIFEST_NAME] == render_project(spec)[MANIFEST_NAME]


def test_manifest_is_valid_json_with_a_trailing_newline() -> None:
    content = render_project(ProjectSpec(name="my-service"))[MANIFEST_NAME]

    assert content.endswith("\n")
    assert json.loads(content)["spec"]["name"] == "my-service"


def test_archive_contains_the_manifest() -> None:
    project = generate_project(ProjectSpec(name="my-service"))

    with ZipFile(io.BytesIO(project.content)) as archive:
        assert "my-service/.fastapi-initializr.json" in archive.namelist()


def _write_project(root: Path, spec: ProjectSpec) -> dict[str, str]:
    files = render_project(spec)
    for path, content in files.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return files


def test_update_plan_has_no_changes_for_a_fresh_project(tmp_path: Path) -> None:
    _write_project(tmp_path, ProjectSpec(name="my-service"))

    plan = plan_update(tmp_path)

    assert plan.added == ()
    assert plan.updated == ()
    assert plan.conflicted == ()
    assert plan.obsolete == ()


def test_update_plan_preserves_local_edits_when_the_template_is_unchanged(
    tmp_path: Path,
) -> None:
    _write_project(tmp_path, ProjectSpec(name="my-service"))
    (tmp_path / "README.md").write_text("local notes\n", encoding="utf-8")

    plan = plan_update(tmp_path)

    assert "README.md" in plan.unchanged


def test_update_plan_ignores_unsafe_manifest_paths(tmp_path: Path) -> None:
    files = _write_project(tmp_path, ProjectSpec(name="my-service"))
    manifest = json.loads(files[MANIFEST_NAME])
    manifest["files"]["../escape.txt"] = "0" * 64
    (tmp_path / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")

    plan = plan_update(tmp_path)

    assert "../escape.txt" not in plan.obsolete


def test_update_plan_accepts_a_legacy_fastapi_selector(tmp_path: Path) -> None:
    files = _write_project(tmp_path, ProjectSpec(name="my-service"))
    manifest = json.loads(files[MANIFEST_NAME])
    manifest["spec"]["fastapi"] = "0.161.1"
    (tmp_path / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")

    plan = plan_update(tmp_path)

    assert plan.has_conflicts is False


def test_update_plan_rejects_unknown_template_versions(tmp_path: Path) -> None:
    files = _write_project(tmp_path, ProjectSpec(name="my-service"))
    manifest = json.loads(files[MANIFEST_NAME])
    manifest["templateVersion"] = "999"
    (tmp_path / MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(UpdateError, match="Unsupported template version"):
        plan_update(tmp_path)
