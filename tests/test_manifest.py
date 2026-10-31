"""Generated-project template manifest."""

import hashlib
import io
import json
from zipfile import ZipFile

from fastapi_initializr import __version__
from fastapi_initializr.generation.manifest import MANIFEST_NAME, TEMPLATE_VERSION
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec
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
