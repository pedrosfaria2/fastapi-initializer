"""Dependency catalog invariants."""

from fastapi_initializr.generation.catalog import (
    DEPENDENCIES,
    GROUP_ORDER,
    metadata,
    resolve_packages,
)


def test_every_dependency_has_a_unique_id() -> None:
    assert len(DEPENDENCIES) == len(set(DEPENDENCIES))


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
