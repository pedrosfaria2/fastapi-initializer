"""Metadata schemas for the option catalog."""

from typing import Literal

from pydantic import BaseModel, Field


class Link(BaseModel):
    """A hyperlink in the capability document."""

    href: str
    title: str | None = None
    templated: bool = False


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


class ActionValue(BaseModel):
    """One action in an action option."""

    id: str
    name: str
    action: str
    tags: dict[str, str] = Field(default_factory=dict)


class ActionOption(BaseModel):
    """An action option such as the project type."""

    type: Literal["action"] = "action"
    default: str
    values: list[ActionValue]


class DependencyValue(BaseModel):
    """One selectable dependency."""

    id: str
    name: str
    description: str
    requires: list[str] = Field(default_factory=list)
    requires_capabilities: list[str] = Field(
        default_factory=list,
        serialization_alias="requiresCapabilities",
    )
    provides: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    packages: list[str] = Field(default_factory=list)
    dev_packages: list[str] = Field(default_factory=list, serialization_alias="devPackages")
    help: list[str] = Field(default_factory=list)
    files: list[str] = Field(default_factory=list)
    links: dict[str, Link] = Field(default_factory=dict)


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
    version: TextOption
    author: TextOption


class PresetValue(SelectValue):
    """One preset and the dependencies it selects."""

    dependencies: list[str]


class PresetOption(BaseModel):
    """A single-select preset option."""

    type: Literal["single-select"] = "single-select"
    default: str
    values: list[PresetValue]


class Metadata(BaseModel):
    """The complete option catalog."""

    links: dict[str, Link]
    type: ActionOption
    language: SelectOption
    structure: SelectOption
    python: SelectOption
    preset: PresetOption
    base_dir: TextOption = Field(serialization_alias="baseDir")
    application_name: TextOption = Field(serialization_alias="applicationName")
    project: ProjectOptions
    dependencies: MultiSelectOption
