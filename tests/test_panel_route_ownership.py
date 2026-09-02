from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "custom_components" / "nikas_house"


def test_house_registration_preserves_existing_routes_and_uses_v13_path() -> None:
    house = (PACKAGE / "house_panel.py").read_text(encoding="utf-8")
    constants = (PACKAGE / "const.py").read_text(encoding="utf-8")

    assert "frontend.async_panel_exists" in house
    assert "select_house_panel_route" in house
    assert "HOUSE_PANEL_URL_PATH" in house
    assert 'HOUSE_PANEL_URL_PATH = "dashboard-house-v13"' in constants
    assert "async_remove_panel" not in house.split("async_register_house_panel", 1)[1].split(
        "async_unregister_house_panel", 1
    )[0]


def test_unload_removes_only_the_recorded_house_fallback() -> None:
    house = (PACKAGE / "house_panel.py").read_text(encoding="utf-8")
    init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")

    assert "hass.data.setdefault(DOMAIN, {})[HOUSE_PANEL_PATH] = url_path" in house
    assert "pop(HOUSE_PANEL_PATH, None)" in house
    assert "async_unregister_house_panel(hass)" in init
    assert "async_unregister_infrastructure_panel" not in init
    assert "async_unregister_generated_subpanels" not in init
    assert "async_unregister_rooms_panel" not in init


def test_non_house_panel_owners_are_not_shipped() -> None:
    for name in ("infrastructure_panel.py", "rooms_panel.py", "generated_panels.py"):
        assert not (PACKAGE / name).exists()
