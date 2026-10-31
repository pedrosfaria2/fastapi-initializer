"""Allowlisted dependency catalog and option metadata."""

from dataclasses import dataclass

from fastapi_initializr.generation.constants import (
    DEFAULT_PYTHON_VERSION,
    SUPPORTED_PYTHON_VERSIONS,
)
from fastapi_initializr.schemas.metadata import (
    DependencyGroup,
    DependencyValue,
    Metadata,
    MultiSelectOption,
    ProjectOptions,
    SelectOption,
    SelectValue,
    TextOption,
)


@dataclass(frozen=True, slots=True)
class Dependency:
    """A selectable project feature."""

    id: str
    name: str
    description: str
    group: str
    requires: tuple[str, ...] = ()
    conflicts: tuple[str, ...] = ()
    packages: tuple[str, ...] = ()
    dev_packages: tuple[str, ...] = ()


DEPENDENCIES: dict[str, Dependency] = {
    "sqlalchemy": Dependency(
        id="sqlalchemy",
        name="SQLAlchemy",
        description="Async SQLAlchemy session and SQLite driver.",
        group="Database",
        packages=("sqlalchemy[asyncio]>=2.1.6", "aiosqlite>=0.22.1"),
    ),
    "alembic": Dependency(
        id="alembic",
        name="Alembic",
        description="Database migrations for SQLAlchemy.",
        group="Database",
        requires=("sqlalchemy",),
        packages=("alembic>=1.20.1",),
    ),
    "postgres": Dependency(
        id="postgres",
        name="PostgreSQL",
        description="Async PostgreSQL driver.",
        group="Database",
        requires=("sqlalchemy",),
        packages=("asyncpg>=0.32.0",),
    ),
    "cors": Dependency(
        id="cors",
        name="CORS",
        description="Configurable CORS middleware.",
        group="Web",
    ),
    "docker": Dependency(
        id="docker",
        name="Docker",
        description="Dockerfile and .dockerignore.",
        group="Operations",
    ),
    "ci": Dependency(
        id="ci",
        name="GitHub Actions",
        description="CI workflow running Ruff, mypy, pyright and pytest.",
        group="Operations",
    ),
    "pre-commit": Dependency(
        id="pre-commit",
        name="pre-commit",
        description="Ruff, mypy and pyright hooks.",
        group="Operations",
        dev_packages=("pre-commit>=4.7.0",),
    ),
}

GROUP_ORDER: tuple[str, ...] = ("Database", "Web", "Operations")


def metadata() -> Metadata:
    """Return the option catalog used by the API and UI."""
    groups: list[DependencyGroup] = []
    for group_name in GROUP_ORDER:
        values = [
            DependencyValue(
                id=dependency.id,
                name=dependency.name,
                description=dependency.description,
                requires=list(dependency.requires),
                conflicts=list(dependency.conflicts),
            )
            for dependency in DEPENDENCIES.values()
            if dependency.group == group_name
        ]
        groups.append(DependencyGroup(name=group_name, values=values))

    return Metadata(
        project=ProjectOptions(
            name=TextOption(default="my-service", max_length=64),
            package=TextOption(default="my_service", max_length=64),
            description=TextOption(default="A FastAPI service", max_length=200),
        ),
        python=SelectOption(
            default=DEFAULT_PYTHON_VERSION,
            values=[
                SelectValue(id=version, name=f"Python {version}")
                for version in SUPPORTED_PYTHON_VERSIONS
            ],
        ),
        dependencies=MultiSelectOption(groups=groups),
    )


def resolve_packages(dependencies: frozenset[str]) -> tuple[list[str], list[str]]:
    """Return runtime and development packages for the selected features."""
    packages: set[str] = set()
    dev_packages: set[str] = set()
    for dependency_id in dependencies:
        dependency = DEPENDENCIES[dependency_id]
        packages.update(dependency.packages)
        dev_packages.update(dependency.dev_packages)
    return sorted(packages), sorted(dev_packages)
