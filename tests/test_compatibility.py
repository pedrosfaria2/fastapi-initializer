"""Feature compatibility rules."""

from fastapi_initializr.generation.catalog import DEPENDENCIES
from fastapi_initializr.generation.compatibility import (
    feature_availability,
    selection_issues,
)


def test_accepts_a_compatible_selection() -> None:
    selected = frozenset({"sqlalchemy", "alembic", "auth-jwt", "cors"})

    assert selection_issues(selected) == ()


def test_reports_a_missing_requirement() -> None:
    issues = selection_issues(frozenset({"alembic"}))

    assert len(issues) == 1
    assert issues[0].feature == "alembic"
    assert issues[0].kind == "missing-requirement"
    assert issues[0].related == ("sqlalchemy",)
    assert issues[0].message == "Dependency 'alembic' requires: sqlalchemy."


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


def test_availability_ignores_unknown_features() -> None:
    availability = {
        feature.id: feature
        for feature in feature_availability(frozenset({"missing-feature", "sqlalchemy"}))
    }

    assert availability["sqlalchemy"].selected is True


def test_every_catalog_reference_exists() -> None:
    for feature_id, dependency in DEPENDENCIES.items():
        for reference in (*dependency.requires, *dependency.conflicts):
            assert reference in DEPENDENCIES, (feature_id, reference)
            assert reference != feature_id, feature_id


def test_every_feature_is_available_on_its_own() -> None:
    for feature_id in DEPENDENCIES:
        availability = {
            feature.id: feature for feature in feature_availability(frozenset({feature_id}))
        }
        assert availability[feature_id].enabled is True, feature_id
