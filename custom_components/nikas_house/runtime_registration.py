"""Export official Home Assistant YAML dashboard registration snippets."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

SUPPORTED_SUFFIXES = {".json", ".yaml", ".yml"}
SNIPPET_FILENAME = "lovelace_configuration_snippet.yaml"


class RuntimeRegistrationError(ValueError):
    """Raised when dashboard registration metadata cannot be exported safely."""


@dataclass(frozen=True, slots=True)
class RegistrationExport:
    """Result of writing the Home Assistant Lovelace registration snippet."""

    path: Path
    dashboard_count: int
    changed: bool


def _documents(base: Path) -> Iterable[Path]:
    if not base.exists():
        return ()
    return (
        path
        for path in sorted(base.rglob("*"))
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def _load_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            document = json.load(handle)
        else:
            document = yaml.safe_load(handle)
    if not isinstance(document, dict):
        raise RuntimeRegistrationError(f"document root must be an object: {path}")
    return document


def _atomic_write(path: Path, text: str) -> bool:
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)
    return True


def write_lovelace_registration_snippet(
    source_root: Path,
    generated_root: Path,
) -> RegistrationExport:
    """Write deterministic registration for CGUI-owned Lovelace dashboards only."""
    dashboards: dict[str, dict[str, Any]] = {}
    manifest_paths = list(_documents(source_root / "manifests"))
    if not manifest_paths:
        raise RuntimeRegistrationError("no panel manifests found")

    for manifest_path in manifest_paths:
        manifest = _load_object(manifest_path)
        if manifest.get("kind") != "PanelManifest":
            raise RuntimeRegistrationError(
                f"unexpected manifest document kind in {manifest_path}"
            )
        metadata = manifest.get("metadata")
        spec = manifest.get("spec")
        if not isinstance(metadata, dict) or not isinstance(spec, dict):
            raise RuntimeRegistrationError(f"manifest metadata/spec missing in {manifest_path}")

        # The House custom panel is registered dynamically by the integration.
        # It must never require a manual `lovelace.dashboards` entry in
        # configuration.yaml.
        if spec.get("subpanel") is not None or spec.get("specialized_panel") is not None:
            continue

        manifest_id = metadata.get("id")
        title = metadata.get("title")
        dashboard_path = spec.get("dashboard_path")
        if not all(
            isinstance(value, str) and value
            for value in (manifest_id, title, dashboard_path)
        ):
            raise RuntimeRegistrationError(
                f"manifest registration fields missing in {manifest_path}"
            )
        if not dashboard_path.startswith("/"):
            raise RuntimeRegistrationError(
                f"dashboard path must be absolute in {manifest_path}: {dashboard_path!r}"
            )
        url_path = dashboard_path[1:]
        if url_path != "lovelace" and "-" not in url_path:
            raise RuntimeRegistrationError(
                f"Home Assistant YAML dashboard url path must contain a hyphen: {url_path!r}"
            )
        if url_path in dashboards:
            raise RuntimeRegistrationError(f"duplicate dashboard url path {url_path!r}")

        filename = f"{source_root.name}/{generated_root.name}/{manifest_id}.yaml"
        dashboards[url_path] = {
            "mode": "yaml",
            "filename": filename,
            "title": title,
            "show_in_sidebar": True,
            "require_admin": False,
        }

    document = {"lovelace": {"dashboards": dashboards}}
    header = (
        "# NikaS House — registration snippet only.\n"
        "# Merge this with any existing top-level `lovelace:` configuration;\n"
        "# do not replace existing Lovelace resources or dashboards blindly.\n"
        "# The House custom panel is registered automatically.\n"
        "# Home Assistant must reload/restart after configuration.yaml changes.\n"
    )
    text = header + yaml.safe_dump(document, allow_unicode=True, sort_keys=False)
    output_path = generated_root / SNIPPET_FILENAME
    changed = _atomic_write(output_path, text)
    return RegistrationExport(
        path=output_path,
        dashboard_count=len(dashboards),
        changed=changed,
    )
