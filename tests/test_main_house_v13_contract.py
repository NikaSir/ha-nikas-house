from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_house_contract_is_public_semantic_only() -> None:
    contract_path = ROOT / "contracts" / "house_home.yaml"
    packaged_path = (
        ROOT
        / "custom_components"
        / "nikas_house"
        / "bundled_sources"
        / "contracts"
        / "house_home.yaml"
    )
    assert contract_path.read_bytes() == packaged_path.read_bytes()

    contract = _load(contract_path)
    assert contract["metadata"]["id"] == "house.home"
    roles = contract["spec"]["roles"]
    assert len(roles) == 128
    assert len(contract["spec"]["actions"]) == len(roles)
    assert contract["spec"]["presentation"]["role_order"] == list(roles)
    # The schema-mandated safety flag is named `invent_entity_ids`; reject only
    # concrete binding-style `entity_id:` fields in the public semantic contract.
    assert "entity_id:" not in contract_path.read_text(encoding="utf-8")


def test_house_v13_overview_is_an_integration_owned_specialized_panel() -> None:
    manifest = _load(ROOT / "manifests" / "house_v13.yaml")
    assert manifest["metadata"]["id"] == "nikas_house_v13"
    assert manifest["spec"]["dashboard_path"] == "/dashboard-house-v13"
    assert manifest["spec"]["specialized_panel"] == {"template": "house_overview_v1"}
    assert "app_shell" not in manifest["spec"]
    assert "subpanel" not in manifest["spec"]
    assert manifest["spec"]["views"][0]["renderer"] == "house_home_v1"
    assert not (ROOT / "manifests" / "house.yaml").exists()


def test_house_preview_bindings_cover_contract_exactly() -> None:
    contract = _load(ROOT / "contracts" / "house_home.yaml")
    manifest = _load(ROOT / "manifests" / "house_v13.yaml")
    roles = set(contract["spec"]["roles"])
    bindings = manifest["spec"]["views"][0]["modules"][0]["bindings"]
    assert set(bindings) == roles
    assert all(value == f"house.home.{role}" for role, value in bindings.items())


def test_house_preview_keeps_protected_main_panel_routes() -> None:
    manifest = _load(ROOT / "manifests" / "house_v13.yaml")
    navigation = manifest["spec"]["navigation"]
    assert navigation["heating"] == "/dashboard-zont"
    assert navigation["cars"] == "/starline"
    assert navigation["infrastructure"] == "/dashboard-infrastructure/overview"
    assert navigation["actions"] == "/dashboard-actions/home"
    assert navigation["safety"] == "/dashboard-house/safety"
    assert navigation["open"] == "/dashboard-house/open"
    assert navigation["access"] == "/dashboard-access-v1/home"
    assert navigation["rooms"] == "/dashboard-rooms-v11/rooms"
