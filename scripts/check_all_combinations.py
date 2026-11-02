"""Render every compatible pair of generated-project features."""

from __future__ import annotations

import itertools
from collections.abc import Iterator

from fastapi_initializr.generation.catalog import DEPENDENCIES
from fastapi_initializr.generation.compatibility import selection_issues
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec


def _expand_requires(selected: set[str]) -> set[str]:
    result = set(selected)
    changed = True
    while changed:
        changed = False
        for dependency_id in list(result):
            for requirement in DEPENDENCIES[dependency_id].requires:
                if requirement not in result:
                    result.add(requirement)
                    changed = True
    return result


def _provided_capabilities(selected: set[str]) -> set[str]:
    return {
        capability
        for dependency_id in selected
        for capability in DEPENDENCIES[dependency_id].provides
    }


def _missing_capabilities(selected: set[str]) -> set[str]:
    provided = _provided_capabilities(selected)
    return {
        capability
        for dependency_id in selected
        for capability in DEPENDENCIES[dependency_id].requires_capabilities
        if capability not in provided
    }


def _closures(selected: set[str]) -> Iterator[set[str]]:
    missing = _missing_capabilities(selected)
    if not missing:
        yield selected
        return
    capability = sorted(missing)[0]
    providers = sorted(
        dependency_id
        for dependency_id, dependency in DEPENDENCIES.items()
        if capability in dependency.provides
    )
    for provider in providers:
        yield from _closures(selected | {provider})


def _compatible(selected: set[str]) -> bool:
    return not selection_issues(frozenset(selected))


def main() -> int:
    """Render single features and every compatible pair."""
    ids = sorted(DEPENDENCIES)
    cases: set[frozenset[str]] = set()
    for dependency_id in ids:
        for selected in _closures(_expand_requires({dependency_id})):
            if _compatible(selected):
                cases.add(frozenset(selected))
    for first, second in itertools.combinations(ids, 2):
        for selected in _closures(_expand_requires({first, second})):
            if _compatible(selected):
                cases.add(frozenset(selected))

    for dependencies in sorted(cases, key=lambda case: (len(case), sorted(case))):
        render_project(ProjectSpec(name="combo-service", dependencies=dependencies))

    print(f"Rendered {len(cases)} compatible feature combinations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
