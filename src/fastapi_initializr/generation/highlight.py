"""Server-side syntax highlighting for preview file contents."""

from dataclasses import dataclass

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexer import Lexer
from pygments.lexers import (
    get_lexer_by_name,  # pyright: ignore[reportUnknownVariableType] - typeshed stub options
    get_lexer_for_filename,  # pyright: ignore[reportUnknownVariableType] - typeshed stub options
)
from pygments.util import ClassNotFound

_FORMATTER: HtmlFormatter[str] = HtmlFormatter(nowrap=True)


@dataclass(frozen=True, slots=True)
class HighlightedFile:
    """Highlighted HTML and its display language for one file."""

    language: str
    html: str


def _lexer_for(path: str) -> Lexer:
    try:
        return get_lexer_for_filename(path)
    except ClassNotFound:
        return get_lexer_by_name("text")


def highlight_file(path: str, content: str) -> HighlightedFile:
    """Return escaped HTML and a language label for a rendered file.

    Pygments escapes the source text, so the returned HTML is safe to insert
    into the preview pane.
    """
    lexer = _lexer_for(path)
    return HighlightedFile(
        language=lexer.name,
        html=highlight(content, lexer, _FORMATTER),
    )
