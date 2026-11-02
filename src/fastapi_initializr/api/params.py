"""Shared request parameter parsing."""

from __future__ import annotations


def split_dependencies(values: list[str] | None) -> frozenset[str]:
    """Split repeated or comma-separated dependency query values."""
    if not values:
        return frozenset()
    dependencies: list[str] = []
    for value in values:
        dependencies.extend(part.strip() for part in value.split(",") if part.strip())
    return frozenset(dependencies)
