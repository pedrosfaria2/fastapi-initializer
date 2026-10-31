"""Project spec validation."""

import pytest
from pydantic import ValidationError

from fastapi_initializr.generation.spec import ProjectSpec, derive_package_name


def test_derives_package_from_name() -> None:
    spec = ProjectSpec(name="my-service")

    assert spec.package == "my_service"


@pytest.mark.parametrize("name", ["my-service", "my_service", "service2", "a"])
def test_accepts_valid_names(name: str) -> None:
    assert ProjectSpec(name=name).name == name


@pytest.mark.parametrize("name", ["My-Service", "1service", "service!", "", "a b"])
def test_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValidationError):
        ProjectSpec(name=name)


def test_rejects_reserved_package() -> None:
    with pytest.raises(ValidationError, match="reserved"):
        ProjectSpec(name="test")


def test_accepts_explicit_package() -> None:
    spec = ProjectSpec(name="my-service", package="custom_package")

    assert spec.package == "custom_package"


def test_rejects_invalid_package() -> None:
    with pytest.raises(ValidationError, match="Package"):
        ProjectSpec(name="my-service", package="Bad-Package")


def test_rejects_unknown_dependency() -> None:
    with pytest.raises(ValidationError, match="Unknown dependencies"):
        ProjectSpec(name="my-service", dependencies=frozenset({"unknown"}))


def test_rejects_missing_dependency() -> None:
    with pytest.raises(ValidationError, match="requires"):
        ProjectSpec(name="my-service", dependencies=frozenset({"alembic"}))


def test_accepts_dependency_with_requirement() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "alembic"}),
    )

    assert spec.has("alembic")
    assert spec.has_database


def test_rejects_invalid_python_version() -> None:
    with pytest.raises(ValidationError, match="Python version"):
        ProjectSpec(name="my-service", python="3.10")


def test_rejects_mongodb_with_python_314() -> None:
    with pytest.raises(ValidationError, match=r"MongoDB with Beanie requires Python <3\.14"):
        ProjectSpec(
            name="my-service",
            python="3.14",
            dependencies=frozenset({"mongodb"}),
        )


def test_accepts_mongodb_with_python_313() -> None:
    spec = ProjectSpec(
        name="my-service",
        python="3.13",
        dependencies=frozenset({"mongodb"}),
    )

    assert spec.has("mongodb")


def test_rejects_control_characters_in_description() -> None:
    with pytest.raises(ValidationError, match="control characters"):
        ProjectSpec(name="my-service", description="bad\x00description")


def test_database_url_uses_postgres_driver() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlalchemy", "postgres"}),
    )

    assert spec.database_url.startswith("postgresql+asyncpg://")


def test_database_url_defaults_to_sqlite() -> None:
    spec = ProjectSpec(name="my-service", dependencies=frozenset({"sqlalchemy"}))

    assert spec.database_url.startswith("sqlite+aiosqlite://")


def test_environment_is_needed_for_database_or_cors() -> None:
    assert ProjectSpec(name="my-service", dependencies=frozenset({"sqlalchemy"})).has_environment
    assert ProjectSpec(name="my-service", dependencies=frozenset({"cors"})).has_environment
    assert not ProjectSpec(name="my-service").has_environment


def test_derives_package_name_for_hyphenated_name() -> None:
    assert derive_package_name("my-cool-service") == "my_cool_service"


def test_accepts_project_metadata() -> None:
    spec = ProjectSpec(
        name="my-service",
        version="1.2.3",
        author="Ada Lovelace",
        fastapi="0.161.1",
        base_dir="custom-root",
        application_name="My Service",
    )

    assert spec.version == "1.2.3"
    assert spec.author == "Ada Lovelace"
    assert spec.fastapi_range == ">=0.161.1,<0.162.0"
    assert spec.archive_root == "custom-root"
    assert spec.app_title == "My Service"


@pytest.mark.parametrize("version", ["1.0", "1.0.0.0", "v1.0.0", ""])
def test_rejects_invalid_project_versions(version: str) -> None:
    with pytest.raises(ValidationError, match=r"MAJOR\.MINOR\.PATCH"):
        ProjectSpec(name="my-service", version=version)


def test_rejects_unknown_fastapi_version() -> None:
    with pytest.raises(ValidationError, match="FastAPI version"):
        ProjectSpec(name="my-service", fastapi="0.100.0")


@pytest.mark.parametrize("base_dir", ["../evil", "a/b", "a\\b", ".hidden", "a..b"])
def test_rejects_unsafe_base_dir(base_dir: str) -> None:
    with pytest.raises(ValidationError, match="baseDir"):
        ProjectSpec(name="my-service", base_dir=base_dir)


def test_rejects_control_characters_in_author() -> None:
    with pytest.raises(ValidationError, match="control characters"):
        ProjectSpec(name="my-service", author="bad\x00author")


def test_rejects_control_characters_in_application_name() -> None:
    with pytest.raises(ValidationError, match="applicationName"):
        ProjectSpec(name="my-service", application_name="bad\x00name")
