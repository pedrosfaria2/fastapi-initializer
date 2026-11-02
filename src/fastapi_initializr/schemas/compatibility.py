"""Compatibility report schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class CompatibilityIssueModel(BaseModel):
    """One incompatibility in a feature selection."""

    feature: str
    kind: Literal[
        "unknown",
        "missing-requirement",
        "missing-capability",
        "conflict",
    ]
    message: str
    related: list[str] = Field(default_factory=list)


class FeatureAvailabilityModel(BaseModel):
    """Availability and reasons for one catalog feature."""

    id: str
    enabled: bool
    selected: bool
    provides: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    required_by: list[str] = Field(default_factory=list)


class CompatibilityReport(BaseModel):
    """Compatibility of a selection and availability of every feature."""

    compatible: bool
    issues: list[CompatibilityIssueModel]
    features: list[FeatureAvailabilityModel]
