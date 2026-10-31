"""Static checks for the parity UI assets."""

from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "src" / "fastapi_initializr" / "static"


def test_app_js_contains_parity_behaviors() -> None:
    script = (ASSETS / "app.js").read_text(encoding="utf-8")

    assert "shiftKey" in script
    assert "navigator.clipboard" in script
    assert "history.replaceState" in script
    assert "AbortController" in script
    assert "dependency-search" in script
    assert "selected-count" in script
    assert "textContent" in script
    assert "fileContent.innerHTML = file.highlighted" in script
    assert "Pygments escapes the source server-side" in script
    assert "/requirements.txt" in script


def test_app_css_is_self_contained_and_responsive() -> None:
    stylesheet = (ASSETS / "app.css").read_text(encoding="utf-8")

    assert "prefers-color-scheme" in stylesheet
    assert "@media" in stylesheet
    assert "@import" not in stylesheet
    assert "url(http" not in stylesheet


def test_pygments_stylesheet_has_light_and_dark_tokens() -> None:
    stylesheet = (ASSETS / "pygments.css").read_text(encoding="utf-8")

    assert ".highlight .k" in stylesheet
    assert "prefers-color-scheme: dark" in stylesheet
    assert "@import" not in stylesheet
    assert "url(" not in stylesheet
