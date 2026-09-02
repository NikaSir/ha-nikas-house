from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_native_diagnostics_exports_fresh_registry_snapshot() -> None:
    source = (
        ROOT
        / "custom_components"
        / "nikas_house"
        / "diagnostics.py"
    ).read_text(encoding="utf-8")
    assert "async_get_config_entry_diagnostics" in source
    assert "capture_registry_snapshot(hass)" in source
