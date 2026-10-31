"""Project request model and validation."""

from __future__ import annotations

import keyword
import re
import sys
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fastapi_initializr.generation.catalog import DEPENDENCIES
from fastapi_initializr.generation.constants import (
    DEFAULT_PYTHON_VERSION,
    SUPPORTED_PYTHON_VERSIONS,
)

PROJECT_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
PACKAGE_NAME_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,63}$")

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
    python: str = Field(default=DEFAULT_PYTHON_VERSION)
    dependencies: frozenset[str] = Field(default_factory=frozenset)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not PROJECT_NAME_PATTERN.fullmatch(value):
            raise ValueError("Use lowercase letters, digits, '-' or '_' and start with a letter.")
        return value

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        value = value.strip()
        if any(ord(character) < 32 for character in value):
            raise ValueError("Description cannot contain control characters.")
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
