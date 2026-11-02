"""Render every compatible pair of generated-project features."""

from __future__ import annotations

import itertools

from fastapi_initializr.generation.catalog import DEPENDENCIES
from fastapi_initializr.generation.compatibility import selection_issues
from fastapi_initializr.generation.renderer import render_project
from fastapi_initializr.generation.spec import ProjectSpec


def _closure(selected: set[str]) -> set[str]:
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


def _compatible(selected: set[str]) -> bool:
    return not selection_issues(frozenset(selected))


def main() -> int:
    """Render single features and every compatible pair."""
    ids = sorted(DEPENDENCIES)
    cases: set[frozenset[str]] = set()
    for dependency_id in ids:
        selected = _closure({dependency_id})
        if _compatible(selected):
            cases.add(frozenset(selected))
    for first, second in itertools.combinations(ids, 2):
        selected = _closure({first, second})
        if _compatible(selected):
            cases.add(frozenset(selected))

    for dependencies in sorted(cases, key=lambda case: (len(case), sorted(case))):
        render_project(ProjectSpec(name="combo-service", dependencies=dependencies))

    print(f"Rendered {len(cases)} compatible feature combinations.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
