from __future__ import annotations

from pathlib import Path

from custom_components.nikas_house.house_navigation import (
    compile_navigation_registry,
)


ROOT = Path(__file__).parents[1]


def test_house_navigation_keeps_external_route_ownership() -> None:
    registry = compile_navigation_registry(ROOT)
    assert registry["subpanels"] == []
    assert registry["global_tabs"] == [
        {
            "id": "home",
            "label": "Дом",
            "icon": "mdi:home-outline",
            "path": "/dashboard-house-v13/home",
        },
        {
            "id": "rooms",
            "label": "Помещения",
            "icon": "mdi:floor-plan",
            "path": "/dashboard-rooms-v11/rooms",
        },
        {
            "id": "actions",
            "label": "Действия",
            "icon": "mdi:lightning-bolt-outline",
            "path": "/dashboard-actions/home",
        },
        {
            "id": "infrastructure",
            "label": "Инфра",
            "icon": "mdi:server-network",
            "path": "/dashboard-infrastructure/overview",
        },
    ]


def test_navigation_source_is_packaged_byte_for_byte() -> None:
    assert (ROOT / "navigation" / "main.yaml").read_bytes() == (
        ROOT
        / "custom_components"
        / "nikas_house"
        / "bundled_sources"
        / "navigation"
        / "main.yaml"
    ).read_bytes()
