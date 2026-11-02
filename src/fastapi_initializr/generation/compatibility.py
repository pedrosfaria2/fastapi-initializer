"""Feature compatibility rules and availability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi_initializr.generation.catalog import DEPENDENCIES

IssueKind = Literal["unknown", "missing-requirement", "conflict"]


@dataclass(frozen=True, slots=True)
class CompatibilityIssue:
    """One reason a selection cannot be generated."""

    feature: str
    kind: IssueKind
    message: str
    related: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FeatureAvailability:
    """Whether one feature can be selected for a given selection."""

    id: str
    enabled: bool
    selected: bool
    missing: tuple[str, ...]
    conflicts: tuple[str, ...]
    required_by: tuple[str, ...]


def selection_issues(dependencies: frozenset[str]) -> tuple[CompatibilityIssue, ...]:
    """Return every compatibility issue in a selection, without duplicates."""
    issues: list[CompatibilityIssue] = []
    unknown = tuple(sorted(dependencies - DEPENDENCIES.keys()))
    if unknown:
        issues.append(
            CompatibilityIssue(
                feature="dependencies",
                kind="unknown",
                message=f"Unknown dependencies: {', '.join(unknown)}.",
                related=unknown,
            )
        )

    seen: set[tuple[str, frozenset[str]]] = set()
    for feature_id in sorted(dependencies):
        dependency = DEPENDENCIES.get(feature_id)
        if dependency is None:
            continue

        missing = tuple(sorted(set(dependency.requires) - dependencies))
        if missing:
            key = ("missing-requirement", frozenset({feature_id, *missing}))
            if key not in seen:
                seen.add(key)
                issues.append(
                    CompatibilityIssue(
                        feature=feature_id,
                        kind="missing-requirement",
                        message=(f"Dependency '{feature_id}' requires: {', '.join(missing)}."),
                        related=missing,
                    )
                )

        conflicts = tuple(sorted(set(dependency.conflicts) & dependencies))
        if conflicts:
            key = ("conflict", frozenset({feature_id, *conflicts}))
            if key not in seen:
                seen.add(key)
                issues.append(
                    CompatibilityIssue(
                        feature=feature_id,
                        kind="conflict",
                        message=(
                            f"Dependency '{feature_id}' conflicts with: {', '.join(conflicts)}."
                        ),
                        related=conflicts,
                    )
                )
    return tuple(issues)


def feature_availability(
    dependencies: frozenset[str],
) -> tuple[FeatureAvailability, ...]:
    """Return availability and reasons for every catalog feature."""
    available: list[FeatureAvailability] = []
    for feature_id, dependency in DEPENDENCIES.items():
        missing = tuple(sorted(set(dependency.requires) - dependencies))
        conflicts = tuple(sorted(set(dependency.conflicts) & dependencies))
        required_by = tuple(
            sorted(
                other_id
                for other_id in dependencies
                if other_id in DEPENDENCIES and feature_id in DEPENDENCIES[other_id].requires
            )
        )
        available.append(
            FeatureAvailability(
                id=feature_id,
                enabled=not conflicts,
                selected=feature_id in dependencies,
                missing=missing,
                conflicts=conflicts,
                required_by=required_by,
            )
        )
    return tuple(available)
