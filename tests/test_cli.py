"""CLI contract."""

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
