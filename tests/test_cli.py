"""CLI contract."""

from pathlib import Path

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
