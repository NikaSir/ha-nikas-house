"""House-only deterministic renderer dispatch."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .render import (
    RenderError,
    RenderResult,
    render_repository_manifest as render_base_manifest,
    write_render_result,
)
from .render_house import (
    HOUSE_RENDERER,
    _layout_engine_sha256 as _house_layout_engine_sha256,
    render_house_dashboard,
)
from .validation import load_document

SUPPORTED_RENDERERS = frozenset({HOUSE_RENDERER})


def manifest_renderer(manifest: Mapping[str, Any]) -> str:
    """Return the only renderer allowed in this House repository."""
    views = manifest.get("spec", {}).get("views")
    if not isinstance(views, list) or not views:
        raise RenderError("House panel manifest has no views")
    for view in views:
        if not isinstance(view, dict):
            raise RenderError("House panel manifest view must be an object")
        renderer = view.get("renderer")
        if renderer != HOUSE_RENDERER:
            raise RenderError(
                f"this repository supports only {HOUSE_RENDERER!r}, got {renderer!r}"
            )
        modules = view.get("modules")
        if not isinstance(modules, list) or not modules:
            raise RenderError("House panel view requires entity modules")
    return HOUSE_RENDERER


def render_repository_manifest(repo_root: Path, manifest_path: Path) -> RenderResult:
    """Render one validated House manifest and its deterministic trace."""
    manifest = load_document(manifest_path)
    if not isinstance(manifest, dict):
        raise RenderError("House panel manifest root must be an object")
    if manifest.get("metadata", {}).get("id") != "nikas_house_v13":
        raise RenderError("this repository renders only nikas_house_v13")
    manifest_renderer(manifest)

    base = render_base_manifest(repo_root, manifest_path)
    dashboard = render_house_dashboard(base.dashboard, base.trace, manifest)
    trace = copy.deepcopy(base.trace)
    trace["renderer_engine_sha256"] = _house_layout_engine_sha256(
        base.trace["renderer_engine_sha256"]
    )
    canonical = json.dumps(
        dashboard,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    trace["dashboard_sha256"] = hashlib.sha256(canonical).hexdigest()
    return RenderResult(dashboard=dashboard, trace=trace)


__all__ = [
    "RenderError",
    "RenderResult",
    "manifest_renderer",
    "render_repository_manifest",
    "write_render_result",
]
