"""Feature compatibility endpoint."""

from typing import Annotated

from fastapi import APIRouter, Query

from fastapi_initializr.api.params import split_dependencies
from fastapi_initializr.generation.compatibility import (
    feature_availability,
    selection_issues,
)
from fastapi_initializr.schemas.compatibility import (
    CompatibilityIssueModel,
    CompatibilityReport,
    FeatureAvailabilityModel,
)

router = APIRouter(tags=["compatibility"])


@router.get("/compatibility", response_model=CompatibilityReport)
def get_compatibility(
    dependencies: Annotated[list[str] | None, Query()] = None,
) -> CompatibilityReport:
    """Report selection issues and availability for every catalog feature."""
    selected = split_dependencies(dependencies)
    issues = selection_issues(selected)
    return CompatibilityReport(
        compatible=not issues,
        issues=[
            CompatibilityIssueModel(
                feature=issue.feature,
                kind=issue.kind,
                message=issue.message,
                related=list(issue.related),
            )
            for issue in issues
        ],
        features=[
            FeatureAvailabilityModel(
                id=feature.id,
                enabled=feature.enabled,
                selected=feature.selected,
                missing=list(feature.missing),
                conflicts=list(feature.conflicts),
                required_by=list(feature.required_by),
            )
            for feature in feature_availability(selected)
        ],
    )
