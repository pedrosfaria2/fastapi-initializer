"""Feature compatibility rules and availability."""

from dataclasses import dataclass
from typing import Literal

from fastapi_initializr.generation.catalog import DEPENDENCIES

IssueKind = Literal[
    "unknown",
    "missing-requirement",
    "missing-capability",
    "conflict",
]


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
    provides: tuple[str, ...]
    missing: tuple[str, ...]
    missing_capabilities: tuple[str, ...]
    conflicts: tuple[str, ...]
    required_by: tuple[str, ...]


def _provided_capabilities(dependencies: frozenset[str]) -> frozenset[str]:
    return frozenset(
        capability
        for feature_id in dependencies
        if (dependency := DEPENDENCIES.get(feature_id)) is not None
        for capability in dependency.provides
    )


def _capability_providers(capability: str) -> tuple[str, ...]:
    return tuple(
        sorted(
            feature_id
            for feature_id, dependency in DEPENDENCIES.items()
            if capability in dependency.provides
        )
    )


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

    provided = _provided_capabilities(dependencies)
    seen: set[tuple[str, frozenset[str]]] = set()
    seen_capabilities: set[tuple[str, str]] = set()
    for feature_id in sorted(dependencies):
        dependency = DEPENDENCIES.get(feature_id)
        if dependency is None:
            continue

        for capability in sorted(set(dependency.requires_capabilities) - provided):
            capability_key = (feature_id, capability)
            if capability_key in seen_capabilities:
                continue
            seen_capabilities.add(capability_key)
            providers = _capability_providers(capability)
            if providers:
                message = f"Dependency '{feature_id}' requires one of: {', '.join(providers)}."
            else:
                message = (
                    f"Dependency '{feature_id}' requires capability "
                    f"'{capability}', but no feature provides it."
                )
            issues.append(
                CompatibilityIssue(
                    feature=feature_id,
                    kind="missing-capability",
                    message=message,
                    related=providers,
                )
            )

        missing = tuple(sorted(set(dependency.requires) - dependencies))
        if missing:
            missing_key = ("missing-requirement", frozenset({feature_id, *missing}))
            if missing_key not in seen:
                seen.add(missing_key)
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
            conflict_key = ("conflict", frozenset({feature_id, *conflicts}))
            if conflict_key not in seen:
                seen.add(conflict_key)
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
    provided = _provided_capabilities(dependencies)
    available: list[FeatureAvailability] = []
    for feature_id, dependency in DEPENDENCIES.items():
        missing = tuple(sorted(set(dependency.requires) - dependencies))
        missing_capabilities = tuple(sorted(set(dependency.requires_capabilities) - provided))
        conflicts = tuple(sorted(set(dependency.conflicts) & dependencies))
        required_by = tuple(
            sorted(
                other_id
                for other_id in dependencies
                if other_id in DEPENDENCIES
                and (
                    feature_id in DEPENDENCIES[other_id].requires
                    or bool(
                        set(DEPENDENCIES[other_id].requires_capabilities) & set(dependency.provides)
                    )
                )
            )
        )
        available.append(
            FeatureAvailability(
                id=feature_id,
                enabled=not conflicts,
                selected=feature_id in dependencies,
                provides=dependency.provides,
                missing=missing,
                missing_capabilities=missing_capabilities,
                conflicts=conflicts,
                required_by=required_by,
            )
        )
    return tuple(available)
