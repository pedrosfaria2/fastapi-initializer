"""Metadata schemas for the option catalog."""

from typing import Literal

from pydantic import BaseModel, Field


class TextOption(BaseModel):
    """A free-text option."""

    type: Literal["text"] = "text"
    default: str
    max_length: int = Field(serialization_alias="maxLength")


class SelectValue(BaseModel):
    """One value in a single-select option."""

    id: str
    name: str


class SelectOption(BaseModel):
    """A single-select option."""

    type: Literal["single-select"] = "single-select"
    default: str
    values: list[SelectValue]


class DependencyValue(BaseModel):
    """One selectable dependency."""

    id: str
    name: str
    description: str
    requires: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


class DependencyGroup(BaseModel):
    """A group of dependencies."""

    name: str
    values: list[DependencyValue]


class MultiSelectOption(BaseModel):
    """A grouped multi-select option."""

    type: Literal["multi-select"] = "multi-select"
    groups: list[DependencyGroup]


class ProjectOptions(BaseModel):
    """Project text options."""

    name: TextOption
    package: TextOption
    description: TextOption


class Metadata(BaseModel):
    """The complete option catalog."""

    project: ProjectOptions
    python: SelectOption
    dependencies: MultiSelectOption
