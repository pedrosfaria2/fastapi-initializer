"""Feature compatibility rules."""

from fastapi_initializr.generation.catalog import DEPENDENCIES
from fastapi_initializr.generation.compatibility import (
    feature_availability,
    selection_issues,
)


def test_accepts_a_compatible_selection() -> None:
    selected = frozenset({"sqlalchemy", "alembic", "auth-jwt", "cors"})

    assert selection_issues(selected) == ()


def test_reports_a_missing_capability() -> None:
    issues = selection_issues(frozenset({"alembic"}))

    assert len(issues) == 1
    assert issues[0].feature == "alembic"
    assert issues[0].kind == "missing-capability"
    assert issues[0].related == ("sqlalchemy", "sqlmodel")
    assert issues[0].message == ("Dependency 'alembic' requires one of: sqlalchemy, sqlmodel.")


def test_sqlmodel_satisfies_the_orm_capability() -> None:
    assert selection_issues(frozenset({"sqlmodel", "alembic"})) == ()


def test_sqlmodel_conflicts_with_sqlalchemy() -> None:
    issues = selection_issues(frozenset({"sqlalchemy", "sqlmodel"}))

    assert len(issues) == 1
    assert issues[0].kind == "conflict"


def test_mysql_requires_the_orm_capability() -> None:
    issues = selection_issues(frozenset({"mysql"}))

    assert len(issues) == 1
    assert issues[0].kind == "missing-capability"
    assert issues[0].related == ("sqlalchemy", "sqlmodel")


def test_sqlmodel_satisfies_the_mysql_capability() -> None:
    assert selection_issues(frozenset({"sqlmodel", "mysql"})) == ()


def test_postgres_and_mysql_conflict() -> None:
    issues = selection_issues(frozenset({"sqlalchemy", "postgres", "mysql"}))

    assert len(issues) == 1
    assert issues[0].kind == "conflict"


def test_celery_requires_a_broker() -> None:
    issues = selection_issues(frozenset({"celery"}))

    assert len(issues) == 1
    assert issues[0].kind == "missing-capability"
    assert issues[0].related == ("rabbitmq", "redis")


def test_rabbitmq_satisfies_celery() -> None:
    assert selection_issues(frozenset({"celery", "rabbitmq"})) == ()


def test_redis_satisfies_celery() -> None:
    assert selection_issues(frozenset({"celery", "redis"})) == ()


def test_celery_conflicts_with_arq() -> None:
    issues = selection_issues(frozenset({"celery", "rabbitmq", "arq", "redis"}))

    assert any(issue.kind == "conflict" for issue in issues)


def test_auth_jwt_still_requires_sqlalchemy() -> None:
    issues = selection_issues(frozenset({"sqlmodel", "auth-jwt"}))

    assert len(issues) == 1
    assert issues[0].kind == "missing-requirement"
    assert issues[0].related == ("sqlalchemy",)


def test_reports_one_bidirectional_conflict() -> None:
    issues = selection_issues(frozenset({"sqlalchemy", "mongodb"}))

    assert len(issues) == 1
    assert issues[0].kind == "conflict"
    assert issues[0].related == ("sqlalchemy",)
    assert issues[0].message == "Dependency 'mongodb' conflicts with: sqlalchemy."


def test_reports_unknown_features() -> None:
    issues = selection_issues(frozenset({"missing-feature", "sqlalchemy"}))

    assert len(issues) == 1
    assert issues[0].kind == "unknown"
    assert issues[0].message == "Unknown dependencies: missing-feature."
    assert issues[0].related == ("missing-feature",)


def test_availability_disables_a_conflicting_feature() -> None:
    availability = {
        feature.id: feature for feature in feature_availability(frozenset({"sqlalchemy"}))
    }

    assert availability["mongodb"].enabled is False
    assert availability["mongodb"].conflicts == ("sqlalchemy",)
    assert availability["sqlalchemy"].selected is True


def test_availability_marks_a_required_feature() -> None:
    availability = {
        feature.id: feature for feature in feature_availability(frozenset({"auth-jwt"}))
    }

    assert availability["auth-jwt"].missing == ("sqlalchemy",)
    assert availability["sqlalchemy"].required_by == ("auth-jwt",)


def test_availability_marks_capability_providers() -> None:
    availability = {feature.id: feature for feature in feature_availability(frozenset({"alembic"}))}

    assert availability["alembic"].missing_capabilities == ("orm",)
    assert availability["sqlalchemy"].provides == ("orm",)
    assert availability["sqlalchemy"].required_by == ("alembic",)
    assert availability["sqlmodel"].required_by == ("alembic",)


def test_availability_ignores_unknown_features() -> None:
    availability = {
        feature.id: feature
        for feature in feature_availability(frozenset({"missing-feature", "sqlalchemy"}))
    }

    assert availability["sqlalchemy"].selected is True


def test_every_catalog_reference_exists() -> None:
    provided = {
        capability for dependency in DEPENDENCIES.values() for capability in dependency.provides
    }
    for feature_id, dependency in DEPENDENCIES.items():
        for reference in (*dependency.requires, *dependency.conflicts):
            assert reference in DEPENDENCIES, (feature_id, reference)
            assert reference != feature_id, feature_id
        for capability in dependency.requires_capabilities:
            assert capability in provided, (feature_id, capability)


def test_every_feature_is_available_on_its_own() -> None:
    for feature_id in DEPENDENCIES:
        availability = {
            feature.id: feature for feature in feature_availability(frozenset({feature_id}))
        }
        assert availability[feature_id].enabled is True, feature_id
