"""Dependency catalog invariants."""

from typing import cast

from fastapi_initializr.generation.catalog import (
    DEPENDENCIES,
    GROUP_ORDER,
    PRESETS_BY_ID,
    dependency_catalog,
    metadata,
    resolve_packages,
)
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec


def test_every_dependency_has_a_unique_id() -> None:
    assert len(DEPENDENCIES) == len(set(DEPENDENCIES))


def test_full_preset_chooses_one_provider_per_capability() -> None:
    full = PRESETS_BY_ID["full"]

    assert "sqlalchemy" in full.dependencies
    assert "sqlmodel" not in full.dependencies
    assert "postgres" in full.dependencies
    assert "mysql" not in full.dependencies
    assert "mongodb" not in full.dependencies
    assert "arq" in full.dependencies
    assert "celery" not in full.dependencies
    assert "rabbitmq" not in full.dependencies


def test_requirements_and_conflicts_reference_known_dependencies() -> None:
    for dependency in DEPENDENCIES.values():
        assert set(dependency.requires) <= DEPENDENCIES.keys()
        assert set(dependency.conflicts) <= DEPENDENCIES.keys()


def test_conflicts_are_symmetric() -> None:
    for dependency in DEPENDENCIES.values():
        for conflict in dependency.conflicts:
            assert dependency.id in DEPENDENCIES[conflict].conflicts


def test_every_dependency_belongs_to_a_known_group() -> None:
    assert {dependency.group for dependency in DEPENDENCIES.values()} <= set(GROUP_ORDER)


def test_metadata_contains_every_dependency_once() -> None:
    catalog = metadata()
    ids = [value.id for group in catalog.dependencies.groups for value in group.values]

    assert sorted(ids) == sorted(DEPENDENCIES)


def test_metadata_defaults_match_the_spec_defaults() -> None:
    catalog = metadata()

    assert catalog.project.name.default == "my-service"
    assert catalog.project.package.default == "my_service"
    assert catalog.python.default == "3.13"


def test_resolves_runtime_and_dev_packages() -> None:
    packages, dev_packages = resolve_packages(frozenset({"sqlalchemy", "alembic", "pre-commit"}))

    assert any(package.startswith("sqlalchemy") for package in packages)
    assert any(package.startswith("aiosqlite") for package in packages)
    assert any(package.startswith("alembic") for package in packages)
    assert any(package.startswith("pre-commit") for package in dev_packages)


def test_resolves_no_extra_packages_for_operations_only() -> None:
    packages, dev_packages = resolve_packages(frozenset({"docker", "ci"}))

    assert packages == []
    assert dev_packages == []


def test_metadata_exposes_spring_style_capabilities() -> None:
    catalog = metadata()

    assert "starter.zip" in catalog.links
    assert catalog.links["starter.zip"].templated is True
    assert catalog.links["compatibility"].templated is True
    assert catalog.type.default == "uv-project"
    assert catalog.language.default == "python"
    assert catalog.structure.default == "layered"
    assert [value.id for value in catalog.structure.values] == [
        "minimal",
        "layered",
        "feature",
    ]
    assert catalog.project.version.default == "0.1.0"
    assert catalog.project.author.default == ""
    assert catalog.base_dir.default == ""
    assert catalog.application_name.default == ""


def test_dependency_metadata_includes_packages_files_and_links() -> None:
    catalog = metadata()
    dependencies = {
        value.id: value for group in catalog.dependencies.groups for value in group.values
    }

    sqlalchemy = dependencies["sqlalchemy"]
    assert any(package.startswith("sqlalchemy") for package in sqlalchemy.packages)
    assert "src/{package}/db/session.py" in sqlalchemy.files
    assert "guide" in sqlalchemy.links
    assert sqlalchemy.links["guide"].href.startswith("https://docs.sqlalchemy.org")
    assert any("uv run alembic upgrade head" in step for step in dependencies["alembic"].help)


def test_dependency_catalog_returns_packages() -> None:
    catalog = dependency_catalog()
    dependencies = cast(dict[str, dict[str, list[str]]], catalog["dependencies"])

    assert dependencies["sqlalchemy"]["packages"] == ["sqlalchemy[asyncio]", "aiosqlite"]
    assert dependencies["alembic"]["packages"] == ["alembic"]
    assert dependencies["docker"]["files"] == ["Dockerfile", ".dockerignore"]


def test_catalog_packages_have_no_version_specifiers() -> None:
    for dependency in DEPENDENCIES.values():
        for package in (*dependency.packages, *dependency.dev_packages):
            assert not any(
                marker in package for marker in (">=", "<=", "==", "~=", "!=", ">", "<")
            ), package


def test_uploads_require_authentication() -> None:
    assert "auth-jwt" in DEPENDENCIES["uploads"].requires


def _selection_for(feature_id: str) -> set[str]:
    selected = {feature_id}
    pending = [feature_id]
    while pending:
        dependency = DEPENDENCIES[pending.pop()]
        for required in dependency.requires:
            if required not in selected:
                selected.add(required)
                pending.append(required)
        for capability in dependency.requires_capabilities:
            provider = next(
                item.id for item in DEPENDENCIES.values() if capability in item.provides
            )
            if provider not in selected:
                selected.add(provider)
                pending.append(provider)
    return selected


def test_every_catalog_feature_file_is_rendered() -> None:
    for feature_id, dependency in DEPENDENCIES.items():
        spec = ProjectSpec(
            name="my-service",
            dependencies=frozenset(_selection_for(feature_id)),
        )

        files = render_project(spec)

        for path in dependency.files:
            assert path.format(package=spec.package) in files, (feature_id, path)
