from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from custom_components.nikas_house.house_panel import (
    HOUSE_PANEL_TEMPLATE,
    HOUSE_PANEL_WEB_COMPONENT,
    build_house_panel_spec,
    materialize_house_panel_spec,
    select_house_panel_route,
)
from custom_components.nikas_house.const import HOUSE_PANEL_URL_PATH

ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "custom_components" / "nikas_house" / "frontend"


def _source_tree(tmp_path: Path) -> Path:
    source = tmp_path / "nikas_house"
    (source / "contracts").mkdir(parents=True)
    (source / "manifests").mkdir()
    (source / "navigation").mkdir()
    shutil.copy2(ROOT / "contracts" / "house_home.yaml", source / "contracts" / "house_home.yaml")
    shutil.copy2(ROOT / "manifests" / "house_v13.yaml", source / "manifests" / "house_v13.yaml")
    shutil.copy2(ROOT / "navigation" / "main.yaml", source / "navigation" / "main.yaml")

    contract = yaml.safe_load((source / "contracts" / "house_home.yaml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((source / "manifests" / "house_v13.yaml").read_text(encoding="utf-8"))
    roles = contract["spec"]["roles"]
    module = manifest["spec"]["views"][0]["modules"][0]
    bindings = {}
    for role, semantic_key in module["bindings"].items():
        domain = roles[role]["allowed_domains"][0]
        bindings[semantic_key] = {
            "entity_id": f"{domain}.{role}",
            "domain": domain,
            "verification": "verified",
        }
    inventory = {
        "api_version": "nikas.home-assistant/semantic-inventory/v1",
        "kind": "SemanticInventory",
        "metadata": {
            "id": "house-test",
            "version": "1.0.0",
            "scrubbed": True,
            "snapshot_id": "sha256:test",
        },
        "spec": {"bindings": bindings},
    }
    (source / "inventory").mkdir()
    (source / "inventory" / "house.yaml").write_text(
        yaml.safe_dump(inventory, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return source


def test_house_panel_spec_resolves_verified_semantics(tmp_path: Path) -> None:
    panel = build_house_panel_spec(_source_tree(tmp_path))

    assert panel["id"] == "nikas_house_v13"
    assert panel["title"] == "Дом сейчас"
    assert panel["url_path"] == "dashboard-house-v13"
    assert panel["view_path"] == "home"
    assert panel["default_path"] == "/dashboard-house-v13/home"
    assert [tab["id"] for tab in panel["tabs"]] == ["home", "rooms", "actions", "infrastructure"]
    assert panel["hero"]["standalone"] is True
    assert "type" not in panel["hero"]
    assert "grid_options" not in panel["hero"]
    assert len(panel["hero"]["entities"]["safety"]) == 5
    assert len(panel["hero"]["entities"]["cameras"]) == 8
    assert panel["hero"]["routes"]["access"] == "/dashboard-access-v1/home"


def test_house_panel_uses_only_the_declared_parallel_route(tmp_path: Path) -> None:
    selected = select_house_panel_route(set().__contains__, HOUSE_PANEL_URL_PATH)
    assert selected == HOUSE_PANEL_URL_PATH

    panel = materialize_house_panel_spec(build_house_panel_spec(_source_tree(tmp_path)), selected)
    assert panel["url_path"] == "dashboard-house-v13"
    assert panel["default_path"] == "/dashboard-house-v13/home"
    assert panel["sidebar_title"] == "Дом · новая"
    assert panel["tabs"][0]["path"] == "/dashboard-house-v13/home"
    assert panel["tabs"][1]["path"] == "/dashboard-rooms-v11/rooms"


def test_house_panel_never_replaces_an_existing_v13_owner() -> None:
    occupied = {"dashboard-house-v13"}
    assert select_house_panel_route(occupied.__contains__, HOUSE_PANEL_URL_PATH) is None
    assert select_house_panel_route(set().__contains__, "dashboard-house-v12") is None


def test_house_manifest_declares_integration_owned_specialized_panel() -> None:
    manifest = yaml.safe_load((ROOT / "manifests" / "house_v13.yaml").read_text(encoding="utf-8"))
    assert manifest["metadata"]["version"] == "1.0.0"
    assert manifest["spec"]["specialized_panel"] == {"template": HOUSE_PANEL_TEMPLATE}
    assert HOUSE_PANEL_WEB_COMPONENT == "nikas-house-panel"


def test_house_panel_uses_one_transform_owned_canvas_and_native_chrome() -> None:
    frontend = (FRONTEND / "nikas-house-overview.js").read_text(encoding="utf-8")

    assert 'const ELEMENT_NAME = "nikas-house-panel"' in frontend
    assert 'const UI_VERSION = "1.0.0"' in frontend
    assert frontend.count('class="canvas-viewport"') == 1
    assert frontend.count('class="work-canvas"') == 1
    assert "translate3d(${x}px, ${y}px, 0) scale(${scale})" in frontend
    assert "transform-origin:0 0" in frontend
    assert "scrollLeft" not in frontend
    assert "overflow-x:hidden;overflow-y:auto" in frontend
    assert "if (this._state.scale <= 1) return;" in frontend
    assert "viewport.scrollTop = 0" in frontend
    assert "style.zoom" not in frontend
    assert "window.localStorage" in frontend
    assert "pointercancel" in frontend
    assert "CLICK_GUARD" in frontend
    assert "this._state.scale >= 0.97 && this._state.scale <= 1.03" in frontend
    assert "Масштаб 100%" in frontend
    assert "_lastTwoFingerTap" in frontend

    assert 'icon="mdi:menu"' in frontend
    assert 'new CustomEvent("hass-toggle-menu"' in frontend
    assert "mdi:arrow-left" not in frontend
    assert frontend.index('<header class="header">') < frontend.index('class="canvas-viewport"')
    assert frontend.index('class="canvas-viewport"') < frontend.index('<div class="bottom">')
    assert ".tab ha-icon{--mdc-icon-size:28px" in frontend
    assert "min-height:52px" in frontend
    assert "box-shadow:0 7px 20px rgba(23,45,76,.08)" in frontend
    assert "nikas-house-main-hero{position:absolute;inset:0;display:block;width:auto;height:auto;min-height:0}" in frontend


def test_house_panel_has_no_permanent_scale_controls() -> None:
    frontend = (FRONTEND / "nikas-house-overview.js").read_text(encoding="utf-8")
    assert "data-zoom" not in frontend
    assert "zoom-in" not in frontend
    assert "zoom-out" not in frontend
    assert "mdi:magnify-plus" not in frontend
    assert "mdi:magnify-minus" not in frontend
