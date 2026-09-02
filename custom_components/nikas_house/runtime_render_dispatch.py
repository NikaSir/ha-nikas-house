"""House-only runtime dispatcher for NikaS House."""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from . import runtime_renderer as base
from .runtime_house import (
    HOUSE_RENDERER,
    _layout_engine_sha256 as _house_layout_engine_sha256,
    render_house_dashboard,
)

RuntimeRenderError = base.RuntimeRenderError
GeneratedArtifact = base.GeneratedArtifact
SUPPORTED_RENDERERS = frozenset({HOUSE_RENDERER})


def manifest_renderer(manifest: Mapping[str, Any]) -> str:
    """Require every manifest in this repository to describe the House panel."""
    views = manifest.get("spec", {}).get("views")
    if not isinstance(views, list) or not views:
        raise RuntimeRenderError("House panel manifest has no views")
    renderers: set[str] = set()
    for view in views:
        if not isinstance(view, dict):
            raise RuntimeRenderError("House panel manifest view must be an object")
        renderer = view.get("renderer")
        if renderer not in SUPPORTED_RENDERERS:
            raise RuntimeRenderError(
                f"this repository supports only {HOUSE_RENDERER!r}, got {renderer!r}"
            )
        modules = view.get("modules")
        if not isinstance(modules, list) or not modules:
            raise RuntimeRenderError("House panel view requires entity modules")
        renderers.add(renderer)
    if renderers != {HOUSE_RENDERER}:
        raise RuntimeRenderError("House panel manifest renderer is inconsistent")
    return HOUSE_RENDERER


def _render_manifest_entry(
    manifest: Mapping[str, Any],
    *,
    contracts: Mapping[str, Any],
    inventory: Mapping[str, Any],
    snapshot_ids: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    dashboard, base_trace = base._render_manifest(
        manifest,
        contracts,
        inventory,
        snapshot_ids=snapshot_ids,
    )
    manifest_renderer(manifest)
    dashboard = render_house_dashboard(dashboard, base_trace, manifest)
    trace = copy.deepcopy(base_trace)
    trace["renderer_engine_sha256"] = _house_layout_engine_sha256(
        base_trace["renderer_engine_sha256"]
    )
    canonical = json.dumps(
        dashboard,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    trace["dashboard_sha256"] = hashlib.sha256(canonical).hexdigest()
    return dashboard, trace


def render_all_manifests(
    source_root: Path,
    generated_root: Path,
) -> list[GeneratedArtifact]:
    """Render the single House manifest without touching Home Assistant YAML."""
    contracts = base._index_contracts(source_root)
    inventory, snapshot_ids = base._index_inventory(source_root)
    manifest_paths = list(base._documents(source_root / "manifests"))
    if len(manifest_paths) != 1:
        raise RuntimeRenderError(
            "House-only repository requires exactly one panel manifest; "
            f"found {len(manifest_paths)}"
        )

    manifest = base._load_object(manifest_paths[0])
    if manifest.get("kind") != "PanelManifest":
        raise RuntimeRenderError("unexpected House manifest kind")
    manifest_id = manifest.get("metadata", {}).get("id")
    if manifest_id != "nikas_house_v13":
        raise RuntimeRenderError(
            f"House-only repository received unexpected manifest {manifest_id!r}"
        )

    dashboard, trace = _render_manifest_entry(
        manifest,
        contracts=contracts,
        inventory=inventory,
        snapshot_ids=snapshot_ids,
    )
    output_path = generated_root / f"{manifest_id}.yaml"
    trace_path = generated_root / f"{manifest_id}.meta.json"
    output_changed = base._atomic_write(
        output_path,
        yaml.safe_dump(dashboard, allow_unicode=True, sort_keys=False),
    )
    trace_changed = base._atomic_write(
        trace_path,
        json.dumps(trace, ensure_ascii=False, indent=2) + "\n",
    )
    return [
        GeneratedArtifact(
            manifest_id=manifest_id,
            output_path=output_path,
            trace_path=trace_path,
            dashboard_sha256=trace["dashboard_sha256"],
            changed=output_changed or trace_changed,
        )
    ]


__all__ = [
    "GeneratedArtifact",
    "RuntimeRenderError",
    "manifest_renderer",
    "render_all_manifests",
]
