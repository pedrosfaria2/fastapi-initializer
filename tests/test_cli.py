"""CLI contract."""

import json
from pathlib import Path

import pytest

from fastapi_initializr.cli import main


def test_list_prints_dependencies() -> None:
    assert main(["list"]) == 0


def test_metadata_prints_json() -> None:
    assert main(["metadata"]) == 0


def test_new_writes_a_project(tmp_path: Path) -> None:
    exit_code = main(
        [
            "new",
            "my-service",
            "--output",
            str(tmp_path),
            "--dependency",
            "sqlalchemy",
        ]
    )

    assert exit_code == 0
    project = tmp_path / "my-service"
    assert (project / "pyproject.toml").exists()
    assert (project / "src" / "my_service" / "main.py").exists()
    assert (project / "src" / "my_service" / "db" / "session.py").exists()


def test_new_rejects_existing_target_without_force(tmp_path: Path) -> None:
    target = tmp_path / "my-service"
    target.mkdir()

    assert main(["new", "my-service", "--output", str(tmp_path)]) == 1


def test_new_overwrites_with_force(tmp_path: Path) -> None:
    target = tmp_path / "my-service"
    target.mkdir()

    assert main(["new", "my-service", "--output", str(tmp_path), "--force"]) == 0
    assert (target / "pyproject.toml").exists()


def test_new_rejects_invalid_dependency(tmp_path: Path) -> None:
    exit_code = main(
        [
            "new",
            "my-service",
            "--output",
            str(tmp_path),
            "--dependency",
            "unknown",
        ]
    )

    assert exit_code == 2
    assert not (tmp_path / "my-service").exists()


def test_new_with_lock_invokes_uv_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        *,
        cwd: Path,
        check: bool,
        env: dict[str, str],
    ) -> None:
        _ = (cwd, check, env)
        calls.append(command)

    monkeypatch.setattr("fastapi_initializr.cli.subprocess.run", fake_run)

    exit_code = main(["new", "my-service", "--output", str(tmp_path), "--lock"])

    assert exit_code == 0
    assert len(calls) == 1
    assert Path(calls[0][0]).name == "uv"
    assert calls[0][1:] == ["lock"]


def test_new_with_preset_writes_the_preset_features(tmp_path: Path) -> None:
    exit_code = main(
        [
            "new",
            "my-service",
            "--output",
            str(tmp_path),
            "--preset",
            "worker",
        ]
    )

    assert exit_code == 0
    project = tmp_path / "my-service"
    assert (project / "src" / "my_service" / "worker.py").exists()
    assert (project / "src" / "my_service" / "core" / "cache_helpers.py").exists()


def test_new_rejects_an_unknown_preset(tmp_path: Path) -> None:
    exit_code = main(["new", "my-service", "--output", str(tmp_path), "--preset", "unknown"])

    assert exit_code == 2
    assert not (tmp_path / "my-service").exists()


def _generated_project(tmp_path: Path) -> Path:
    assert main(["new", "my-service", "--output", str(tmp_path)]) == 0
    return tmp_path / "my-service"


def _manifest(project: Path) -> dict[str, object]:
    data = json.loads((project / ".fastapi-initializr.json").read_text())
    assert isinstance(data, dict)
    return data


def test_update_reports_no_changes(tmp_path: Path) -> None:
    project = _generated_project(tmp_path)

    assert main(["update", str(project)]) == 0


def test_update_restores_missing_files(tmp_path: Path) -> None:
    project = _generated_project(tmp_path)
    readme = project / "README.md"
    readme.unlink()

    assert main(["update", str(project)]) == 0
    assert readme.exists()


def test_update_requires_a_manifest(tmp_path: Path) -> None:
    assert main(["update", str(tmp_path)]) == 1


def test_update_applies_manifest_spec_changes(tmp_path: Path) -> None:
    project = _generated_project(tmp_path)
    data = _manifest(project)
    spec = data["spec"]
    assert isinstance(spec, dict)
    spec["description"] = "Updated description"
    (project / ".fastapi-initializr.json").write_text(json.dumps(data))

    assert main(["update", str(project)]) == 0
    assert 'description = "Updated description"' in (project / "pyproject.toml").read_text()
    assert _manifest(project)["spec"]["description"] == "Updated description"


def test_update_stops_on_local_changes(tmp_path: Path) -> None:
    project = _generated_project(tmp_path)
    pyproject = project / "pyproject.toml"
    pyproject.write_text("local notes\n")
    data = _manifest(project)
    spec = data["spec"]
    assert isinstance(spec, dict)
    spec["description"] = "Updated description"
    (project / ".fastapi-initializr.json").write_text(json.dumps(data))

    assert main(["update", str(project)]) == 3
    assert pyproject.read_text() == "local notes\n"


def test_update_force_overwrites_local_changes(tmp_path: Path) -> None:
    project = _generated_project(tmp_path)
    pyproject = project / "pyproject.toml"
    pyproject.write_text("local notes\n")
    data = _manifest(project)
    spec = data["spec"]
    assert isinstance(spec, dict)
    spec["description"] = "Updated description"
    (project / ".fastapi-initializr.json").write_text(json.dumps(data))

    assert main(["update", str(project), "--force"]) == 0
    assert 'description = "Updated description"' in pyproject.read_text()


def test_update_dry_run_writes_nothing(tmp_path: Path) -> None:
    project = _generated_project(tmp_path)
    data = _manifest(project)
    spec = data["spec"]
    assert isinstance(spec, dict)
    spec["description"] = "Updated description"
    (project / ".fastapi-initializr.json").write_text(json.dumps(data))
    before = (project / "pyproject.toml").read_text()

    assert main(["update", str(project), "--dry-run"]) == 0
    assert (project / "pyproject.toml").read_text() == before


def test_new_dry_run_writes_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(["new", "my-service", "--output", str(tmp_path), "--dry-run"])

    assert exit_code == 0
    assert not (tmp_path / "my-service").exists()
    assert "pyproject.toml" in capsys.readouterr().out


def test_new_json_summary(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main(
        [
            "new",
            "my-service",
            "--output",
            str(tmp_path),
            "--dependency",
            "sqlalchemy",
            "--json",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["target"] == str(tmp_path / "my-service")
    assert payload["dependencies"] == ["sqlalchemy"]
    assert payload["dryRun"] is False
    assert "pyproject.toml" in payload["files"]


def test_new_lists_dependencies_without_a_name(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["new", "--list-dependencies"]) == 0
    output = capsys.readouterr().out
    assert "Database:" in output
    assert "sqlalchemy" in output


def test_new_list_dependencies_json(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["new", "--list-dependencies", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)

    assert {"id": "sqlalchemy", "name": "SQLAlchemy", "group": "Database"} in rows


def test_new_requires_a_name() -> None:
    assert main(["new"]) == 2


def test_list_supports_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list", "--json"]) == 0
    rows = json.loads(capsys.readouterr().out)

    assert any(row["id"] == "docker" for row in rows)


@pytest.mark.parametrize(
    ("shell", "marker"),
    [("bash", "complete -F"), ("zsh", "#compdef"), ("fish", "complete -c")],
)
def test_completion_scripts_include_catalog_values(
    shell: str,
    marker: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["completion", shell]) == 0
    output = capsys.readouterr().out

    assert marker in output
    assert "sqlalchemy" in output
    assert "db-auth" in output


def test_completion_rejects_an_unknown_shell() -> None:
    with pytest.raises(SystemExit):
        main(["completion", "powershell"])
