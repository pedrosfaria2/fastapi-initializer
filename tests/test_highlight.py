"""Server-side preview highlighting."""

from fastapi_initializr.generation.highlight import highlight_file
from fastapi_initializr.generation.preview import build_preview
from fastapi_initializr.generation.spec import ProjectSpec


def test_python_source_is_highlighted_as_python() -> None:
    highlighted = highlight_file("src/app/main.py", 'def greet() -> str:\n    return "hi"\n')

    assert highlighted.language == "Python"
    assert '<span class="k">def</span>' in highlighted.html
    assert '<span class="s2">"hi"</span>' in highlighted.html


def test_unknown_file_type_falls_back_to_text() -> None:
    highlighted = highlight_file("notes.unknown", "plain text")

    assert highlighted.language == "Text only"
    assert highlighted.html == "plain text\n"


def test_html_in_source_is_escaped() -> None:
    highlighted = highlight_file(
        "src/app/config.py",
        'app_name = "<img src=x onerror=alert(1)>"\n',
    )

    assert "&lt;img src=x onerror=alert(1)&gt;" in highlighted.html
    assert "<img " not in highlighted.html


def test_preview_includes_highlighting_metadata() -> None:
    preview = build_preview(ProjectSpec(name="my-service"))
    python_file = next(file for file in preview.files if file.path.endswith("main.py"))

    assert python_file.language == "Python"
    assert '<span class="k">def</span>' in python_file.highlighted
    assert python_file.size == len(python_file.content.encode("utf-8"))


def test_preview_escapes_user_text_in_highlighted_html() -> None:
    preview = build_preview(
        ProjectSpec(
            name="my-service",
            application_name="<script>alert(1)</script>",
        )
    )
    config = next(file for file in preview.files if file.path == "src/my_service/core/config.py")

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in config.highlighted
    assert "<script>" not in config.highlighted


def test_preview_highlighting_is_deterministic() -> None:
    spec = ProjectSpec(name="my-service", dependencies=frozenset({"sqlalchemy"}))

    assert build_preview(spec) == build_preview(spec)
