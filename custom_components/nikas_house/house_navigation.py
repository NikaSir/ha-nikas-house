"""Compile external navigation links for the NikaS House overview."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import yaml

SUPPORTED_SUFFIXES = {".json", ".yaml", ".yml"}
NAVIGATION_API_VERSION = "nikas.home-assistant/navigation/v1"
NAVIGATION_KIND = "NavigationContract"
NAVIGATION_REGISTRY_API_VERSION = "nikas.home-assistant/navigation-registry/v1"


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
        document = (
            json.load(handle)
            if path.suffix.lower() == ".json"
            else yaml.safe_load(handle)
        )
    if not isinstance(document, dict):
        raise ValueError(f"navigation document root must be an object: {path}")
    return document


def compile_navigation_registry(source_root: Path) -> dict[str, Any]:
    """Resolve global tabs without claiming ownership of their target routes."""
    contracts: dict[str, dict[str, Any]] = {}
    for path in _documents(source_root / "navigation"):
        document = _load_object(path)
        if (
            document.get("api_version") != NAVIGATION_API_VERSION
            or document.get("kind") != NAVIGATION_KIND
        ):
            raise ValueError(f"unexpected navigation document in {path}")
        nav_id = document.get("metadata", {}).get("id")
        if not isinstance(nav_id, str) or not nav_id:
            raise ValueError(f"navigation contract id missing in {path}")
        if nav_id in contracts:
            raise ValueError(f"duplicate navigation contract id {nav_id!r}")
        contracts[nav_id] = document

    if not contracts:
        raise ValueError("no navigation contracts found")
    navigation = contracts.get("main") or contracts[sorted(contracts)[0]]
    spec = navigation.get("spec")
    if not isinstance(spec, dict):
        raise ValueError("navigation spec missing")
    routes = spec.get("routes")
    tabs = spec.get("global_tabs")
    if not isinstance(routes, dict) or not isinstance(tabs, list):
        raise ValueError("navigation routes/global_tabs missing")

    resolved: list[dict[str, str]] = []
    seen: set[str] = set()
    for tab in tabs:
        if not isinstance(tab, dict):
            raise ValueError("navigation tab must be an object")
        tab_id = tab.get("id")
        route_id = tab.get("route")
        route = routes.get(route_id) if isinstance(route_id, str) else None
        if not isinstance(tab_id, str) or not tab_id or tab_id in seen:
            raise ValueError(f"invalid or duplicate navigation tab id {tab_id!r}")
        if not isinstance(route, dict):
            raise ValueError(f"navigation route {route_id!r} not found")
        title = tab.get("title")
        icon = tab.get("icon")
        path = route.get("path")
        if not all(isinstance(value, str) and value for value in (title, icon, path)):
            raise ValueError(f"navigation tab {tab_id!r} is incomplete")
        if not path.startswith("/"):
            raise ValueError(f"navigation tab {tab_id!r} path must be absolute")
        seen.add(tab_id)
        resolved.append(
            {"id": tab_id, "label": title, "icon": icon, "path": path}
        )

    if not 3 <= len(resolved) <= 5:
        raise ValueError("House overview requires 3–5 global navigation tabs")
    return {
        "api_version": NAVIGATION_REGISTRY_API_VERSION,
        "global_tabs": resolved,
        "subpanels": [],
    }


__all__ = ["compile_navigation_registry"]
