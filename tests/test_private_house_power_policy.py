from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_house_power_rebind_policy_stays_semantic_only_in_public_sources() -> None:
    doc = (ROOT / "docs" / "RUNTIME_PRIVATE_INVENTORY.md").read_text(
        encoding="utf-8"
    )
    manifest = (ROOT / "manifests" / "house_v13.yaml").read_text(encoding="utf-8")

    assert "infrastructure.power.voltage_a/b/c" in doc
    assert "house.home.power_a/b/c" in doc
    assert "Concrete Home Assistant entity ids remain exclusively" in doc
    assert "sensor.power_monitor_voltage" not in doc
    assert "sensor.power_monitor_voltage" not in manifest
