"""Preview schemas."""

from pydantic import BaseModel


class PreviewFile(BaseModel):
    """One rendered file in the preview."""

    path: str
    content: str
    size: int
    language: str
    highlighted: str


class Preview(BaseModel):
    """The rendered project preview."""

    name: str
    files: list[PreviewFile]
