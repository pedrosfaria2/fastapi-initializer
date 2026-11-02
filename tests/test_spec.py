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


def test_accepts_mongodb_with_python_314() -> None:
    spec = ProjectSpec(
        name="my-service",
        python="3.14",
        dependencies=frozenset({"mongodb"}),
    )

    assert spec.has("mongodb")


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


def test_database_url_uses_mysql_driver_with_sqlmodel() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"sqlmodel", "mysql"}),
    )

    assert spec.has_database is True
    assert spec.database_url.startswith("mysql+aiomysql://")


def test_celery_broker_url_uses_rabbitmq() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"celery", "rabbitmq"}),
    )

    assert spec.celery_broker_url == "amqp://guest:guest@localhost:5672//"
    assert spec.has_environment is True


def test_celery_broker_url_uses_redis() -> None:
    spec = ProjectSpec(
        name="my-service",
        dependencies=frozenset({"celery", "redis"}),
    )

    assert spec.celery_broker_url == "redis://localhost:6379/0"


def test_database_url_defaults_to_sqlite() -> None:
    spec = ProjectSpec(name="my-service", dependencies=frozenset({"sqlalchemy"}))

    assert spec.database_url.startswith("sqlite+aiosqlite://")


def test_database_url_defaults_to_sqlite_with_sqlmodel() -> None:
    spec = ProjectSpec(name="my-service", dependencies=frozenset({"sqlmodel"}))

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
        base_dir="custom-root",
        application_name="My Service",
    )

    assert spec.version == "1.2.3"
    assert spec.author == "Ada Lovelace"
    assert spec.archive_root == "custom-root"
    assert spec.app_title == "My Service"


@pytest.mark.parametrize("version", ["1.0", "1.0.0.0", "v1.0.0", ""])
def test_rejects_invalid_project_versions(version: str) -> None:
    with pytest.raises(ValidationError, match=r"MAJOR\.MINOR\.PATCH"):
        ProjectSpec(name="my-service", version=version)


@pytest.mark.parametrize("base_dir", ["../evil", "a/b", "a\\b", ".hidden", "a..b"])
def test_rejects_unsafe_base_dir(base_dir: str) -> None:
    with pytest.raises(ValidationError, match="baseDir"):
        ProjectSpec(name="my-service", base_dir=base_dir)


def test_rejects_control_characters_in_author() -> None:
    with pytest.raises(ValidationError, match="control characters"):
        ProjectSpec(name="my-service", author="bad\x00author")


@pytest.mark.parametrize("field", ["description", "author", "application_name"])
def test_rejects_del_and_c1_control_characters(field: str) -> None:
    for value in ("bad\x7fvalue", "bad\x85value"):
        with pytest.raises(ValidationError, match="control characters"):
            ProjectSpec(name="my-service", **{field: value})


@pytest.mark.parametrize("version", ["\u0661.\u0662.\u0663", "\uff11.\uff12.\uff13"])
def test_rejects_non_ascii_digits_in_version(version: str) -> None:
    with pytest.raises(ValidationError, match=r"MAJOR\.MINOR\.PATCH"):
        ProjectSpec(name="my-service", version=version)


def test_accepts_supported_structures() -> None:
    assert ProjectSpec(name="my-service", structure="layered").structure == "layered"
    assert ProjectSpec(name="my-service", structure="feature").structure == "feature"


def test_rejects_unknown_structure() -> None:
    with pytest.raises(ValidationError, match="Structure"):
        ProjectSpec(name="my-service", structure="unknown")


def test_minimal_structure_rejects_domain_features() -> None:
    with pytest.raises(ValidationError, match="Minimal structure does not support"):
        ProjectSpec(
            name="my-service",
            structure="minimal",
            dependencies=frozenset({"sqlalchemy"}),
        )


def test_accepts_camel_case_aliases() -> None:
    spec = ProjectSpec.model_validate(
        {
            "name": "my-service",
            "baseDir": "custom-root",
            "applicationName": "Acme",
            "pythonVersion": "3.12",
        }
    )

    assert spec.base_dir == "custom-root"
    assert spec.application_name == "Acme"
    assert spec.python == "3.12"


def test_rejects_conflicting_python_aliases() -> None:
    with pytest.raises(ValidationError, match="pythonVersion"):
        ProjectSpec.model_validate(
            {"name": "my-service", "python": "3.11", "pythonVersion": "3.14"}
        )


def test_rejects_control_characters_in_application_name() -> None:
    with pytest.raises(ValidationError, match="applicationName"):
        ProjectSpec(name="my-service", application_name="bad\x00name")


def test_preset_expands_its_dependencies() -> None:
    spec = ProjectSpec(name="my-service", preset="db-auth")

    assert {"sqlalchemy", "alembic", "auth-jwt", "cors"} <= spec.dependencies


def test_preset_unions_explicit_dependencies() -> None:
    spec = ProjectSpec(
        name="my-service",
        preset="api",
        dependencies=frozenset({"redis"}),
    )

    assert spec.dependencies == frozenset({"redis"})


def test_full_preset_selects_every_compatible_feature() -> None:
    spec = ProjectSpec(name="my-service", preset="full")

    assert spec.has("sqlalchemy")
    assert spec.has("arq")
    assert spec.has("testcontainers")
    assert not spec.has("mongodb")


def test_full_preset_accepts_python_314() -> None:
    spec = ProjectSpec(name="my-service", preset="full", python="3.14")

    assert spec.python == "3.14"


def test_custom_preset_selects_nothing() -> None:
    assert ProjectSpec(name="my-service").dependencies == frozenset()


def test_rejects_unknown_preset() -> None:
    with pytest.raises(ValidationError, match="Preset"):
        ProjectSpec(name="my-service", preset="unknown")
