"""Project request model and validation."""

from __future__ import annotations

import keyword
import re
import sys
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fastapi_initializr.generation.catalog import DEPENDENCIES, PRESETS, PRESETS_BY_ID
from fastapi_initializr.generation.constants import (
    DEFAULT_PYTHON_VERSION,
    SUPPORTED_PYTHON_VERSIONS,
)

PROJECT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
PACKAGE_NAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,63}$")
PROJECT_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
BASE_DIR_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

RESERVED_NAMES = frozenset(
    {
        "app",
        "fastapi",
        "main",
        "src",
        "test",
        "tests",
        *sys.stdlib_module_names,
        *keyword.kwlist,
    }
)


def derive_package_name(name: str) -> str:
    """Derive an import package name from a project name."""
    return name.replace("-", "_").lower()


class ProjectSpec(BaseModel):
    """Validated description of the project to generate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(default="my-service", min_length=1, max_length=64)
    package: str | None = Field(default=None, max_length=64)
    description: str = Field(default="A FastAPI service", max_length=200)
    version: str = Field(default="0.1.0", max_length=32)
    author: str = Field(default="", max_length=100)
    python: str = Field(default=DEFAULT_PYTHON_VERSION)
    base_dir: str | None = Field(default=None, max_length=64)
    application_name: str | None = Field(default=None, max_length=100)
    preset: str = Field(default="custom", max_length=32)
    dependencies: frozenset[str] = Field(default_factory=frozenset)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not PROJECT_NAME_PATTERN.fullmatch(value):
            raise ValueError("Use lowercase letters, digits, '-' or '_' and start with a letter.")
        return value

    @field_validator("description", "author")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()
        if any(ord(character) < 32 for character in value):
            raise ValueError("Text fields cannot contain control characters.")
        return value

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        value = value.strip()
        if not PROJECT_VERSION_PATTERN.fullmatch(value):
            raise ValueError("Project version must use MAJOR.MINOR.PATCH, for example 0.1.0.")
        return value

    @field_validator("base_dir")
    @classmethod
    def validate_base_dir(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        value = value.strip()
        if not BASE_DIR_PATTERN.fullmatch(value) or ".." in value:
            raise ValueError(
                "baseDir must be a single directory name without path separators or '..'."
            )
        return value

    @field_validator("application_name")
    @classmethod
    def validate_application_name(cls, value: str | None) -> str | None:
        if value is None or value.strip() == "":
            return None
        value = value.strip()
        if any(ord(character) < 32 for character in value):
            raise ValueError("applicationName cannot contain control characters.")
        return value

    @model_validator(mode="after")
    def validate_project(self) -> Self:
        package = self.package or derive_package_name(self.name)
        if not PACKAGE_NAME_PATTERN.fullmatch(package):
            raise ValueError(
                "Package must use lowercase letters, digits and '_' and start with a letter."
            )
        if package in RESERVED_NAMES:
            raise ValueError(f"Package name '{package}' is reserved.")
        if self.python not in SUPPORTED_PYTHON_VERSIONS:
            allowed = ", ".join(SUPPORTED_PYTHON_VERSIONS)
            raise ValueError(f"Python version must be one of: {allowed}.")

        preset = PRESETS_BY_ID.get(self.preset)
        if preset is None:
            allowed = ", ".join(p.id for p in PRESETS)
            raise ValueError(f"Preset must be one of: {allowed}.")

        dependencies = self.dependencies | frozenset(preset.dependencies)
        if dependencies != self.dependencies:
            object.__setattr__(self, "dependencies", dependencies)

        unknown = sorted(self.dependencies - DEPENDENCIES.keys())
        if unknown:
            raise ValueError(f"Unknown dependencies: {', '.join(unknown)}.")

        for dependency_id in sorted(self.dependencies):
            dependency = DEPENDENCIES[dependency_id]
            missing = sorted(set(dependency.requires) - self.dependencies)
            if missing:
                raise ValueError(f"Dependency '{dependency_id}' requires: {', '.join(missing)}.")
            conflicts = sorted(set(dependency.conflicts) & self.dependencies)
            if conflicts:
                raise ValueError(
                    f"Dependency '{dependency_id}' conflicts with: {', '.join(conflicts)}."
                )

        object.__setattr__(self, "package", package)
        return self

    def has(self, dependency_id: str) -> bool:
        """Return whether a feature is selected."""
        return dependency_id in self.dependencies

    @property
    def has_database(self) -> bool:
        """Return whether a database feature is selected."""
        return self.has("sqlalchemy")

    @property
    def has_environment(self) -> bool:
        """Return whether the generated project needs an environment file."""
        return self.has_database or self.has("cors")

    @property
    def database_url(self) -> str:
        """Return the default database URL for the selected driver."""
        if self.has("postgres"):
            return "postgresql+asyncpg://postgres:postgres@localhost:5432/app"
        return "sqlite+aiosqlite:///./app.db"

    @property
    def cors_origins(self) -> list[str]:
        """Return the default local CORS origins."""
        return ["http://localhost:3000"]

    @property
    def archive_root(self) -> str:
        """Return the root directory inside the generated archive."""
        return self.base_dir or self.name

    @property
    def app_title(self) -> str:
        """Return the application title used by FastAPI."""
        return self.application_name or self.name
