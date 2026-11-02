"""Transactional application of project updates."""

import json
import os
from pathlib import Path

import pytest

from fastapi_initializr.generation import update
from fastapi_initializr.generation.manifest import MANIFEST_NAME
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec
from fastapi_initializr.generation.update import UpdateError, apply_update, plan_update


def _generated_project(tmp_path: Path) -> Path:
    project = tmp_path / "my-service"
    spec = ProjectSpec(name="my-service", dependencies=frozenset({"cors"}))
    for path, content in render_project(spec).items():
        target = project / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return project


def _plan_with_updated_description(project: Path) -> update.UpdatePlan:
    manifest_path = project / MANIFEST_NAME
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["spec"]["description"] = "Updated description"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    return plan_update(project)


def test_apply_update_rolls_back_a_partial_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = _generated_project(tmp_path)
    plan = _plan_with_updated_description(project)
    before = {
        path: (project / path).read_text() for path in plan.files if (project / path).is_file()
    }

    calls = 0
    real_replace = os.replace

    def failing_replace(source: Path, target: Path) -> None:
        nonlocal calls
        if ".fastapi-initializr-stage" in source.parts:
            calls += 1
            if calls == 2:
                raise OSError("simulated write failure")
        real_replace(source, target)

    monkeypatch.setattr(update, "_replace", failing_replace)

    with pytest.raises(UpdateError, match="rolled back"):
        apply_update(plan, project)

    assert calls == 2
    for path, content in before.items():
        assert (project / path).read_text() == content
    assert not (project / ".fastapi-initializr-stage").exists()
    assert not (project / ".fastapi-initializr-backup").exists()


def test_apply_update_cleans_up_recovery_state(tmp_path: Path) -> None:
    project = _generated_project(tmp_path)
    plan = _plan_with_updated_description(project)

    apply_update(plan, project)

    assert "Updated description" in (project / "README.md").read_text()
    assert not (project / ".fastapi-initializr-stage").exists()
    assert not (project / ".fastapi-initializr-backup").exists()


def test_recover_interrupted_update_restores_the_previous_state(tmp_path: Path) -> None:
    project = _generated_project(tmp_path)
    original = (project / "README.md").read_text()
    backup = project / ".fastapi-initializr-backup"
    backup.mkdir()
    (backup / "journal.json").write_text(
        json.dumps({"targets": {"README.md": True, "new.txt": False}}),
        encoding="utf-8",
    )
    (backup / "README.md").write_text(original, encoding="utf-8")
    (project / "README.md").write_text("partial update", encoding="utf-8")
    (project / "new.txt").write_text("new file", encoding="utf-8")
    stage = project / ".fastapi-initializr-stage"
    stage.mkdir()
    (stage / "junk.txt").write_text("junk", encoding="utf-8")

    update._recover_interrupted(project)

    assert (project / "README.md").read_text() == original
    assert not (project / "new.txt").exists()
    assert not backup.exists()
    assert not stage.exists()


def test_plan_update_recovers_an_interrupted_update(tmp_path: Path) -> None:
    project = _generated_project(tmp_path)
    original = (project / "README.md").read_text()
    backup = project / ".fastapi-initializr-backup"
    backup.mkdir()
    (backup / "journal.json").write_text(
        json.dumps({"targets": {"README.md": True}}),
        encoding="utf-8",
    )
    (backup / "README.md").write_text(original, encoding="utf-8")
    (project / "README.md").write_text("partial update", encoding="utf-8")

    plan_update(project)

    assert (project / "README.md").read_text() == original
    assert not backup.exists()


def test_recover_interrupted_update_discards_a_completed_backup(tmp_path: Path) -> None:
    project = _generated_project(tmp_path)
    backup = project / ".fastapi-initializr-backup"
    backup.mkdir()
    (backup / "README.md").write_text("stale content", encoding="utf-8")
    (project / "README.md").write_text("current content", encoding="utf-8")

    update._recover_interrupted(project)

    assert (project / "README.md").read_text() == "current content"
    assert not backup.exists()


def test_recover_interrupted_update_rejects_a_corrupt_journal(tmp_path: Path) -> None:
    project = _generated_project(tmp_path)
    backup = project / ".fastapi-initializr-backup"
    backup.mkdir()
    (backup / "journal.json").write_text("not json", encoding="utf-8")

    with pytest.raises(UpdateError, match="interrupted update"):
        update._recover_interrupted(project)
