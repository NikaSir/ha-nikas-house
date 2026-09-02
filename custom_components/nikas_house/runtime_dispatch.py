"""Runtime dispatch for the NikaS House renderer."""

from __future__ import annotations

from pathlib import Path

from .runtime_render_dispatch import (
    GeneratedArtifact,
    RuntimeRenderError,
    render_all_manifests as render_current,
)
from .runtime_source_sync import sync_bundled_public_sources


def render_all_manifests(
    source_root: Path,
    generated_root: Path,
) -> list[GeneratedArtifact]:
    """Synchronize public House sources and render its review artifacts."""
    if source_root.name == "nikas_house":
        sync_bundled_public_sources(source_root)
    return render_current(source_root, generated_root)


__all__ = ["GeneratedArtifact", "RuntimeRenderError", "render_all_manifests"]
