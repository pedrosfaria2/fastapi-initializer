"""Three-way merge behavior for project updates."""

from fastapi_initializr.generation.update import merge_three_way


def test_merges_disjoint_changes() -> None:
    base = "one\ntwo\nthree\n"
    local = "ONE\ntwo\nthree\n"
    new = "one\ntwo\nTHREE\n"

    assert merge_three_way(base, local, new) == "ONE\ntwo\nTHREE\n"


def test_keeps_local_changes_when_the_template_is_unchanged() -> None:
    base = "one\ntwo\n"
    local = "one local\ntwo\n"

    assert merge_three_way(base, local, base) == local


def test_keeps_template_changes_when_the_local_file_is_unchanged() -> None:
    base = "one\ntwo\n"
    new = "one template\ntwo\n"

    assert merge_three_way(base, base, new) == new


def test_returns_none_for_overlapping_changes() -> None:
    base = "one\ntwo\nthree\n"
    local = "one\nlocal\nthree\n"
    new = "one\ntemplate\nthree\n"

    assert merge_three_way(base, local, new) is None


def test_returns_none_for_insertions_at_the_same_point() -> None:
    base = "one\ntwo\n"
    local = "one\nlocal\ntwo\n"
    new = "one\ntemplate\ntwo\n"

    assert merge_three_way(base, local, new) is None
