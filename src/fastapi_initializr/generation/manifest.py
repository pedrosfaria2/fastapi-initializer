"""Generated-project manifest for safe upgrades."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi_initializr import __version__
from fastapi_initializr.generation.spec import ProjectSpec

MANIFEST_NAME = ".fastapi-initializr.json"
TEMPLATE_VERSION = "1"


def file_digest(content: str) -> str:
    """Return the SHA-256 digest of rendered UTF-8 content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def manifest_spec(spec: ProjectSpec) -> dict[str, Any]:
    """Return the reproducible subset of a project spec."""
    data: dict[str, Any] = spec.model_dump(mode="json", by_alias=True)
    data["dependencies"] = sorted(spec.dependencies)
    return data


def render_manifest(spec: ProjectSpec, files: dict[str, str]) -> str:
    """Serialize the manifest for the rendered project files."""
    document = {
        "templateVersion": TEMPLATE_VERSION,
        "generatorVersion": __version__,
        "spec": manifest_spec(spec),
        "files": {path: file_digest(content) for path, content in files.items()},
    }
    return json.dumps(document, indent=2, sort_keys=True) + "\n"
