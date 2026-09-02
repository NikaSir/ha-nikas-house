"""Register the integration-owned House overview specialized panel."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from .const import (
    DOMAIN,
    HOUSE_PANEL_MODULE_URL,
    HOUSE_PANEL_PATH,
    HOUSE_PANEL_URL_PATH,
)
from .runtime_house import HOUSE_RENDERER, house_overview_config
from .runtime_renderer import (
    _index_contracts,
    _index_inventory,
    _load_object,
    _render_manifest,
)
from .house_navigation import compile_navigation_registry

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

HOUSE_PANEL_TEMPLATE = "house_overview_v1"
HOUSE_PANEL_WEB_COMPONENT = "nikas-house-panel"
_LOGGER = logging.getLogger(__name__)


def _house_manifest(source_root: Path) -> dict[str, Any]:
    matches: list[dict[str, Any]] = []
    manifests_root = source_root / "manifests"
    if manifests_root.exists():
        for path in sorted(manifests_root.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".yaml", ".yml"}:
                continue
            manifest = _load_object(path)
            panel = manifest.get("spec", {}).get("specialized_panel")
            if (
                manifest.get("kind") == "PanelManifest"
                and isinstance(panel, dict)
                and panel.get("template") == HOUSE_PANEL_TEMPLATE
            ):
                matches.append(manifest)
    if len(matches) != 1:
        raise ValueError(
            "exactly one specialized House manifest is required; "
            f"found {len(matches)}"
        )
    return matches[0]


def build_house_panel_spec(source_root: Path) -> dict[str, Any]:
    """Resolve the House panel config from verified private semantic inventory."""
    manifest = _house_manifest(source_root)
    metadata = manifest.get("metadata", {})
    spec = manifest.get("spec", {})
    views = spec.get("views")
    if not isinstance(views, list) or len(views) != 1 or not isinstance(views[0], dict):
        raise ValueError("specialized House panel requires exactly one view")
    view = views[0]
    if view.get("renderer") != HOUSE_RENDERER:
        raise ValueError("specialized House panel requires house_home_v1")

    dashboard_path = spec.get("dashboard_path")
    if not isinstance(dashboard_path, str) or not dashboard_path.startswith("/"):
        raise ValueError("specialized House panel dashboard_path is invalid")
    url_path = dashboard_path.removeprefix("/")
    if not url_path or "/" in url_path:
        raise ValueError("specialized House panel requires one top-level URL path")
    if url_path != HOUSE_PANEL_URL_PATH:
        raise ValueError(
            f"specialized House panel must own /{HOUSE_PANEL_URL_PATH}, got {dashboard_path}"
        )

    contracts = _index_contracts(source_root)
    inventory, snapshot_ids = _index_inventory(source_root)
    _, trace = _render_manifest(
        manifest,
        contracts,
        inventory,
        snapshot_ids=snapshot_ids,
    )
    navigation = compile_navigation_registry(source_root)
    tabs = navigation.get("global_tabs")
    if not isinstance(tabs, list) or not 3 <= len(tabs) <= 5:
        raise ValueError("specialized House panel requires 3–5 global tabs")

    hero = house_overview_config(trace, manifest)
    title = view.get("title")
    if not isinstance(title, str) or not title:
        raise ValueError("specialized House panel title is missing")
    view_path = view.get("path")
    if not isinstance(view_path, str) or not view_path:
        raise ValueError("specialized House panel view path is missing")

    return {
        "id": metadata.get("id", "nikas_house_v13"),
        "title": title,
        "sidebar_title": metadata.get("title", "Дом"),
        "sidebar_icon": "mdi:home-outline",
        "url_path": url_path,
        "view_path": view_path,
        "default_path": f"{dashboard_path}/{view_path}",
        "hero": hero,
        "tabs": tabs,
    }


def select_house_panel_route(
    panel_exists: Callable[[str], bool],
    preferred_url_path: str,
) -> str | None:
    """Select only the declared v13 route and never replace an existing owner."""
    if preferred_url_path == HOUSE_PANEL_URL_PATH and not panel_exists(preferred_url_path):
        return preferred_url_path
    return None


def materialize_house_panel_spec(
    panel_spec: dict[str, Any],
    url_path: str,
) -> dict[str, Any]:
    """Adapt Home and sidebar navigation to the route selected at runtime."""
    view_path = panel_spec["view_path"]
    default_path = f"/{url_path}/{view_path}"
    tabs = [dict(tab) for tab in panel_spec["tabs"]]
    for tab in tabs:
        if tab.get("id") == "home":
            tab["path"] = default_path
    return {
        **panel_spec,
        "url_path": url_path,
        "default_path": default_path,
        "tabs": tabs,
        "sidebar_title": "Дом · новая",
    }


async def async_register_house_panel(hass: HomeAssistant, source_root: Path) -> None:
    """Register House beside an existing YAML owner without replacing it."""
    from homeassistant.components import frontend, panel_custom

    panel_spec = await hass.async_add_executor_job(build_house_panel_spec, source_root)
    preferred_url_path = panel_spec["url_path"]
    url_path = select_house_panel_route(
        lambda candidate: frontend.async_panel_exists(hass, candidate),
        preferred_url_path,
    )
    if url_path is None:
        _LOGGER.warning(
            "Cannot register NikaS House panel: route %s is already owned or invalid",
            preferred_url_path,
        )
        return
    panel_spec = materialize_house_panel_spec(panel_spec, url_path)

    await panel_custom.async_register_panel(
        hass=hass,
        frontend_url_path=url_path,
        webcomponent_name=HOUSE_PANEL_WEB_COMPONENT,
        sidebar_title=panel_spec["sidebar_title"],
        sidebar_icon=panel_spec["sidebar_icon"],
        module_url=HOUSE_PANEL_MODULE_URL,
        embed_iframe=False,
        require_admin=False,
        handle_safe_area=True,
        config={
            "id": panel_spec["id"],
            "title": panel_spec["title"],
            "default_path": panel_spec["default_path"],
            "hero": panel_spec["hero"],
            "tabs": panel_spec["tabs"],
        },
    )
    hass.data.setdefault(DOMAIN, {})[HOUSE_PANEL_PATH] = url_path


def async_unregister_house_panel(hass: HomeAssistant) -> None:
    """Remove only the House fallback registered by this integration."""
    from homeassistant.components import frontend

    url_path = hass.data.get(DOMAIN, {}).pop(HOUSE_PANEL_PATH, None)
    if isinstance(url_path, str):
        frontend.async_remove_panel(hass, url_path, warn_if_unknown=False)


__all__ = [
    "HOUSE_PANEL_TEMPLATE",
    "HOUSE_PANEL_WEB_COMPONENT",
    "async_register_house_panel",
    "async_unregister_house_panel",
    "build_house_panel_spec",
    "materialize_house_panel_spec",
    "select_house_panel_route",
]
