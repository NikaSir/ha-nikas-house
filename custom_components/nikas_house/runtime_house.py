from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping

from . import house_base as _base

HOUSE_RENDERER = _base.HOUSE_RENDERER
MAX_COLUMNS = _base.MAX_COLUMNS
RenderError = _base.RenderError
HOUSE_HERO_ASSET_URL = "/nikas_house/frontend/assets/house-hero-photo-day-v3.webp?build=v1_0_0_b001"


def _layout_engine_sha256(base_engine_sha256: str) -> str:
    """Fingerprint the accepted House renderer plus the visual-scene layer."""
    base_sha = _base._layout_engine_sha256(base_engine_sha256)
    layer_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    return hashlib.sha256(f"{base_sha}:{layer_sha}".encode("utf-8")).hexdigest()


def _trace_entities(trace: Mapping[str, Any]) -> dict[str, str]:
    views = trace.get("semantics", {}).get("views")
    if not isinstance(views, list) or len(views) != 1:
        raise RenderError("house_home_v1 visual scene requires exactly one semantic view")
    modules = views[0].get("modules")
    if not isinstance(modules, list) or len(modules) != 1:
        raise RenderError("house_home_v1 visual scene requires exactly one semantic module")
    roles = modules[0].get("roles")
    if not isinstance(roles, list):
        raise RenderError("house_home_v1 visual scene semantic roles missing")

    result: dict[str, str] = {}
    for role in roles:
        if not isinstance(role, dict):
            continue
        name = role.get("role")
        entity_id = role.get("entity_id")
        if isinstance(name, str) and isinstance(entity_id, str):
            result[name] = entity_id
    return result


def _drop_duplicate_title(view: dict[str, Any]) -> None:
    sections = view.get("sections")
    if not isinstance(sections, list) or not sections:
        raise RenderError("house_home_v1 visual scene sections missing")
    first = sections[0]
    cards = first.get("cards") if isinstance(first, dict) else None
    title = view.get("title")
    if (
        not isinstance(cards, list)
        or len(cards) != 1
        or not isinstance(cards[0], dict)
        or cards[0].get("type") != "heading"
        or cards[0].get("heading") != title
    ):
        raise RenderError("house_home_v1 duplicate title section shape changed")
    sections.pop(0)


def _members(entities: Mapping[str, str], prefix: str) -> list[str]:
    return [entities[key] for key in sorted(entities) if key.startswith(prefix)]


def _nav(manifest: Mapping[str, Any], key: str) -> str:
    navigation = manifest.get("spec", {}).get("navigation")
    if not isinstance(navigation, dict):
        raise RenderError("house_home_v1 visual scene requires spec.navigation")
    target = navigation.get(key)
    if not isinstance(target, str) or not target.startswith("/"):
        raise RenderError(f"house_home_v1 visual scene navigation target {key!r} missing")
    return target


def _hero_card(entities: Mapping[str, str], manifest: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "weather",
        "power_a",
        "power_b",
        "power_c",
        "water_drinking",
        "internet",
        "heating_main",
        "heating_reserve",
        "heating_radiators",
        "heating_floor",
        "heating_circulation",
        "access_entrance",
        "access_sectional",
    )
    missing = [name for name in required if name not in entities]
    if missing:
        raise RenderError("house_home_v1 visual scene missing roles: " + ", ".join(missing))

    safety = _members(entities, "safety_")
    openings = _members(entities, "opening_")
    motion = _members(entities, "motion_")
    lights = _members(entities, "light_")
    climate = _members(entities, "climate_")
    cameras = _members(entities, "camera_")
    for name, members in (
        ("safety", safety),
        ("openings", openings),
        ("motion", motion),
        ("lights", lights),
        ("climate", climate),
        ("cameras", cameras),
    ):
        if not members:
            raise RenderError(f"house_home_v1 visual scene requires at least one {name} entity")

    windows = [
        entity_id
        for entity_id in openings
        if any(token in entity_id.lower() for token in ("sensor_wo_", "window", "okno"))
    ]
    if not windows:
        windows = openings
    doors = [
        entities[name]
        for name in ("access_entrance", "access_tambour", "access_garage", "access_veranda", "access_garden")
        if name in entities
    ]

    return {
        "type": "custom:nikas-house-main-hero",
        "title": "Дом сейчас",
        "asset": HOUSE_HERO_ASSET_URL,
        "entities": {
            "safety": safety,
            "openings": openings,
            "windows": windows,
            "doors": doors,
            "motion": motion,
            "lights": lights,
            "climate": climate,
            "cameras": cameras,
            "weather": entities["weather"],
            "power": [entities["power_a"], entities["power_b"], entities["power_c"]],
            "water": entities["water_drinking"],
            "internet": entities["internet"],
            "heating": {
                "main": entities["heating_main"],
                "reserve": entities["heating_reserve"],
                "radiators": entities["heating_radiators"],
                "floor": entities["heating_floor"],
                "circulation": entities["heating_circulation"],
                "main_temp": entities.get("heating_main_temp"),
                "reserve_temp": entities.get("heating_reserve_temp"),
            },
            "access": {
                "entrance": entities["access_entrance"],
                "sectional": entities["access_sectional"],
            },
        },
        "routes": {
            "safety": _nav(manifest, "safety"),
            "open": _nav(manifest, "open"),
            "access": _nav(manifest, "access"),
            "activity": _nav(manifest, "activity"),
            "lights": _nav(manifest, "lights"),
            "climate": _nav(manifest, "climate"),
            "cameras": _nav(manifest, "cameras"),
            "weather": _nav(manifest, "weather"),
            "electricity": _nav(manifest, "electricity"),
            "water": _nav(manifest, "water"),
            "network": _nav(manifest, "network"),
            "heating": _nav(manifest, "heating"),
        },
        "grid_options": {"columns": "full"},
    }


def house_overview_config(
    trace: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the data-only config consumed by the specialized House panel."""
    config = _hero_card(_trace_entities(trace), manifest)
    config.pop("type", None)
    config.pop("grid_options", None)
    config["standalone"] = True
    return config


def _replace_house_now_with_hero(
    view: dict[str, Any],
    entities: Mapping[str, str],
    manifest: Mapping[str, Any],
) -> None:
    sections = view.get("sections")
    if not isinstance(sections, list):
        raise RenderError("house_home_v1 visual scene sections missing")
    for section in sections:
        cards = section.get("cards") if isinstance(section, dict) else None
        if not isinstance(cards, list) or not cards:
            continue
        first = cards[0]
        if isinstance(first, dict) and first.get("type") == "heading" and first.get("heading") == "Дом сейчас":
            section["cards"] = [_hero_card(entities, manifest)]
            return
    raise RenderError("house_home_v1 visual scene target section not found")


def render_house_dashboard(
    dashboard: dict[str, Any],
    trace: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> dict[str, Any]:
    """Render House and replace the first screen with a live visual state scene."""
    rendered = _base.render_house_dashboard(dashboard, trace, manifest)
    views = rendered.get("views")
    if not isinstance(views, list) or len(views) != 1 or not isinstance(views[0], dict):
        raise RenderError("house_home_v1 visual scene requires exactly one rendered view")
    view = views[0]
    entities = _trace_entities(trace)
    _drop_duplicate_title(view)
    _replace_house_now_with_hero(view, entities, manifest)
    return rendered


__all__ = [
    "HOUSE_HERO_ASSET_URL",
    "HOUSE_RENDERER",
    "MAX_COLUMNS",
    "_layout_engine_sha256",
    "house_overview_config",
    "render_house_dashboard",
]
