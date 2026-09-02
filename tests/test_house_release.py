from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
PACKAGE = ROOT / "custom_components" / "nikas_house"


def test_release_is_house_only() -> None:
    manifest = json.loads((PACKAGE / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["version"] == "0.1.0"
    assert set(manifest["dependencies"]) == {"frontend", "http"}
    assert manifest["after_dependencies"] == ["lovelace"]

    assert sorted(path.name for path in (ROOT / "contracts").glob("*.yaml")) == [
        "house_home.yaml"
    ]
    assert sorted(path.name for path in (ROOT / "manifests").glob("*.yaml")) == [
        "house_v13.yaml"
    ]
    assert sorted(
        path.name
        for path in (PACKAGE / "bundled_sources" / "contracts").glob("*.yaml")
    ) == ["house_home.yaml"]
    assert sorted(
        path.name
        for path in (PACKAGE / "bundled_sources" / "manifests").glob("*.yaml")
    ) == ["house_v13.yaml"]


def test_only_house_frontend_is_packaged() -> None:
    frontend = PACKAGE / "frontend"
    assert sorted(path.name for path in frontend.glob("*.js")) == [
        "nikas-house-hero.js",
        "nikas-house-overview.js",
        "nikas-ui.js",
    ]
    assert sorted(path.name for path in (frontend / "dist").glob("*.js")) == [
        "nikas-house-overview.js"
    ]
    assert sorted(path.name for path in (frontend / "assets").iterdir()) == [
        "house-hero-photo-day-v3.webp"
    ]
    packaged = (frontend / "dist" / "nikas-house-overview.js").read_text(
        encoding="utf-8"
    )
    assert not any(line.lstrip().startswith("import ") for line in packaged.splitlines())


def test_global_frontend_does_not_modify_legacy_yaml_dashboards() -> None:
    bundle = (PACKAGE / "frontend" / "nikas-ui.js").read_text(encoding="utf-8")
    assert "NikasHouseNavigation" in bundle
    assert "history.pushState" in bundle
    assert "location-changed" in bundle
    assert "MutationObserver" not in bundle
    assert "querySelector" not in bundle
    assert "createElement" not in bundle
    assert "appendChild" not in bundle
    assert "innerHTML" not in bundle
    assert 'return "/dashboard-house-v13/home"' in bundle
    assert '"/dashboard-access-v1"' in bundle
    assert 'return "/dashboard-rooms-v11/rooms"' in bundle


def test_setup_registers_only_house_panel() -> None:
    init = (PACKAGE / "__init__.py").read_text(encoding="utf-8")
    constants = (PACKAGE / "const.py").read_text(encoding="utf-8")
    assert "async_register_house_panel" in init
    assert "async_register_infrastructure_panel" not in init
    assert "async_register_generated_subpanels" not in init
    assert "async_register_rooms_panel" not in init
    assert "INFRASTRUCTURE_PANEL" not in constants
    assert "ROOMS_PANEL" not in constants
    assert "GENERATED_SUBPANEL" not in constants


def test_runtime_namespaces_are_parallel_safe_and_frontend_is_autonomous() -> None:
    constants = (PACKAGE / "const.py").read_text(encoding="utf-8")
    panel = (PACKAGE / "house_panel.py").read_text(encoding="utf-8")
    frontend_sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (PACKAGE / "frontend").rglob("*.js")
    )

    assert 'DOMAIN = "nikas_house"' in constants
    assert 'HOUSE_PANEL_URL_PATH = "dashboard-house-v13"' in constants
    assert 'HOUSE_PANEL_WEB_COMPONENT = "nikas-house-panel"' in panel
    assert "/contract_generated_ui/" not in frontend_sources
    assert "NikasPanelNavigation" not in frontend_sources
    assert 'const ELEMENT_NAME = "nikas-house-main-hero"' in frontend_sources
    assert 'const ELEMENT_NAME = "nikas-house-panel"' in frontend_sources
    assert "window.NikasHouseNavigation" in frontend_sources


def test_source_provenance_and_repository_boundary_are_documented() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    scope = (ROOT / "docs" / "REPOSITORY_SCOPE.md").read_text(encoding="utf-8")
    assert "f5bff8145eef20475cf3e3f9f470e94d564b72fc" in readme
    assert "/dashboard-house-v12/home" in readme
    assert "owns only the new main **Дом** overview" in scope
    assert "must never unload or replace a route" in scope
