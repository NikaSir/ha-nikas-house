from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
FRONTEND = ROOT / "custom_components" / "nikas_house" / "frontend"


def test_house_visual_scene_is_local_layered_and_fail_closed() -> None:
    bundle = (FRONTEND / "nikas-house-hero.js").read_text(encoding="utf-8")
    asset_path = FRONTEND / "assets" / "house-hero-photo-day-v3.webp"
    asset = asset_path.read_bytes()

    assert 'const ELEMENT_NAME = "nikas-house-main-hero"' in bundle
    assert "base64" not in bundle.lower()
    assert "https://" not in bundle
    assert '"unknown"' in bundle
    assert '"unavailable"' in bundle
    assert "min < 125 || max > 275" in bundle
    assert "min < 150 || max > 265" in bundle
    assert "Нет данных" in bundle
    assert "Авария" in bundle
    assert "Рабочий предел" in bundle
    assert "Внимание" in bundle

    # The decorative asset is a local binary image, not Base64 or an external URL.
    assert asset_path.suffix == ".webp"
    assert len(asset) > 10_000
    assert asset[:4] == b"RIFF"
    assert b"WEBP" in asset[:16]
    assert int.from_bytes(asset[4:8], "little") + 8 == len(asset)
    assert asset[12:16] in {b"VP8 ", b"VP8L", b"VP8X"}


def test_house_visual_scene_keeps_data_and_art_separate() -> None:
    renderer = (ROOT / "generator" / "render_house.py").read_text(encoding="utf-8")
    assert '"type": "custom:nikas-house-main-hero"' in renderer
    assert '"power": [entities["power_a"], entities["power_b"], entities["power_c"]]' in renderer
    assert '"water": entities["water_drinking"]' in renderer
    assert '"internet": entities["internet"]' in renderer
    assert '"access": {' in renderer
    assert "HOUSE_HERO_ASSET_URL" in renderer
    assert "house-hero-photo-day-v3.webp?build=v1_0_0_b001" in renderer


def test_house_frontend_anchors_zones_in_source_image_space() -> None:
    frontend = (ROOT / "custom_components" / "nikas_house" / "frontend" / "nikas-house-hero.js").read_text(encoding="utf-8")
    assert 'viewBox="0 0 1024 1536"' in frontend
    assert 'preserveAspectRatio="xMidYMid slice"' in frontend
    assert "vector-effect:non-scaling-stroke" in frontend
    assert "camera-pill" not in frontend
    assert "info-grid" in frontend
    assert "Дата и время" in frontend
    assert "min < 125 || max > 275" in frontend
    assert "min < 150 || max > 265" in frontend


def test_house_generated_fallback_uses_upstream_stabilizer_policy() -> None:
    renderer = (ROOT / "generator" / "house_base.py").read_text(encoding="utf-8")
    assert "(pe.v|min)<125" in renderer
    assert "(pe.v|max)>275" in renderer
    assert "(pe.v|min)<150" in renderer
    assert "(pe.v|max)>265" in renderer
    assert "(pe.v|min)<198" not in renderer


def test_house_visual_scene_is_daytime_light_and_mobile_first() -> None:
    bundle = (FRONTEND / "nikas-house-hero.js").read_text(encoding="utf-8")
    asset_path = FRONTEND / "assets" / "house-hero-photo-day-v3.webp"

    # The first screen still ends above the fixed global tab bar.
    assert "height:var(--house-hero-available-height,calc(100dvh - 224px))" in bundle
    assert "min-height:0" in bundle
    assert 'const GLOBAL_TABBAR_ID = "nikas-house-global-tabbar"' in bundle
    assert "tabBar.getBoundingClientRect().top" in bundle
    assert "bottom - top" in bundle

    # The photoreal daytime art is local and mobile-oriented; the live card keeps cover positioning.
    assert asset_path.exists()
    assert "background-size:cover" in bundle
    assert "background-position:center 50%" in bundle

    # The light theme is deliberate; dark mode is a later independent pass.
    assert "background:rgba(255,255,255,.86)" in bundle
    assert "--ink:#15202b" in bundle
    assert "--muted:#4f5d69" in bundle

    # Five top statuses remain legible by stacking icon/text vertically on mobile.
    assert "flex-direction:column" in bundle
    assert "justify-content:center" in bundle

    # Zones are calibrated in source-image coordinates and share its cover crop.
    assert 'viewBox="0 0 1024 1536"' in bundle
    assert 'preserveAspectRatio="xMidYMid slice"' in bundle
    assert 'x="182" y="738" width="170" height="158"' in bundle
    assert 'x="112" y="986" width="260" height="188"' in bundle
    assert 'x="724" y="974" width="128" height="200"' in bundle


def test_house_visual_scene_point_patches_without_optional_indicator() -> None:
    bundle = (FRONTEND / "nikas-house-hero.js").read_text(encoding="utf-8")

    # The only direct innerHTML write is the pre-live loading placeholder.
    assert bundle.count("this.shadowRoot.innerHTML") == 1
    assert "commitStableMarkup(this.shadowRoot, markup)" in bundle
    assert "sameTreeShape" in bundle
    assert "syncTree" in bundle
    assert "_nikasRouteBound" in bundle
    assert "commitStableMarkup(this.shadowRoot, markup);\n    // Stable state updates" in bundle
    assert "this._bindRoutes();\n    this._scheduleViewportFit();" in bundle
    assert "if (replaced) this._bindRoutes()" not in bundle
    assert "connection-primary" not in bundle
    assert "connection-secondary" not in bundle
    top = bundle[bundle.index('<div class="top-grid">'):bundle.index('</div>', bundle.index('<div class="top-grid">'))]
    assert top.index('"Окна"') < top.index('"Двери"') < top.index('"Свет"') < top.index('"Движение"') < top.index('"Климат"')
    info = bundle[bundle.index('<div class="info-grid">'):bundle.index('<svg class="zones"')]
    assert info.index("Погода") < info.index("Защита") < info.index("Дата и время") < info.index("Камеры")
    assert 'this._card(security.icon,"Безопасность",security.label,security.tone,routes.safety)' not in bundle

    # Meaningful mobile text never falls below the v1.7 12px floor.
    for forbidden in (
        "font-size:8px",
        "font-size:9px",
        "font-size:9.5px",
        "font-size:10px",
        "font-size:11px",
    ):
        assert forbidden not in bundle


def test_house_climate_summary_distinguishes_missing_and_unavailable() -> None:
    bundle = (FRONTEND / "nikas-house-hero.js").read_text(encoding="utf-8")

    assert "_climate(ids)" in bundle
    assert 'state === "unknown" || state === "unavailable"' in bundle
    assert "missing: source.length - resolved" in bundle
    assert 'resolved > 0 ? "green" : "grey"' in bundle


def test_house_water_uses_verified_irrigation_pressure() -> None:
    bundle = (FRONTEND / "nikas-house-hero.js").read_text(encoding="utf-8")

    assert 'const IRRIGATION_PRESSURE_ENTITY = "sensor.nikas_h2000_pro_voda_na_poliv_2"' in bundle
    assert "_irrigationPressureEntity()" in bundle
    assert 'if (value <= 0) return { label: "Нет воды", tone: "red"' in bundle
    assert 'return { label: "Есть", tone: "green"' in bundle
    assert "value < 2.4" not in bundle


def test_house_utility_cards_are_text_only_state_plaques() -> None:
    bundle = (FRONTEND / "nikas-house-hero.js").read_text(encoding="utf-8")

    assert "_utility(title, tone, route)" in bundle
    assert '<button class="utility-card ${tone}"' in bundle
    assert ".utility-card{min-height:48px" in bundle
    assert ".utility-card strong{font-size:16px}" in bundle
    assert "utility-copy" not in bundle
    assert "utility-card ha-icon" not in bundle
    assert 'this._utility("Электросеть",power.tone,routes.electricity)' in bundle
    assert 'this._utility("Вода",water.tone,routes.water)' in bundle
    assert 'this._utility("Интернет",internet.tone,routes.network)' in bundle
    assert 'this._utility("Отопление",heating.tone,routes.heating)' in bundle
    assert 'this._card("mdi:thermostat","Климат",climate.value,climate.tone,routes.climate)' in bundle
    assert "climateBad" not in bundle
    assert "climateActive" not in bundle


def test_access_cards_use_the_verified_autonomous_access_route() -> None:
    bundle = (FRONTEND / "nikas-house-hero.js").read_text(encoding="utf-8")

    assert "const accessRoute = routes.access || routes.open" in bundle
    assert '"Двери",String(doors),doorTone,accessRoute' in bundle
    assert 'gate.tone}" data-route="${escapeHtml(accessRoute)}' in bundle
    assert 'entrance.tone}" data-route="${escapeHtml(accessRoute)}' in bundle
    assert 'windowTone}" data-route="${escapeHtml(routes.open)}' in bundle
