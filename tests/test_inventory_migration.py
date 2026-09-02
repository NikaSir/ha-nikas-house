from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from custom_components.nikas_house.inventory_migration import (
    HOUSE_INVENTORY_FILENAME,
    InventoryMigrationError,
    migrate_legacy_house_inventory,
)

ROOT = Path(__file__).parents[1]


def _prepare_public_sources(target_root: Path) -> tuple[dict, dict]:
    contract = yaml.safe_load((ROOT / "contracts" / "house_home.yaml").read_text(encoding="utf-8"))
    manifest = yaml.safe_load((ROOT / "manifests" / "house_v13.yaml").read_text(encoding="utf-8"))
    (target_root / "manifests").mkdir(parents=True)
    (target_root / "manifests" / "house_v13.yaml").write_text(
        yaml.safe_dump(manifest, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return contract, manifest


def _legacy_inventory(contract: dict, manifest: dict) -> dict:
    roles = contract["spec"]["roles"]
    module_bindings = manifest["spec"]["views"][0]["modules"][0]["bindings"]
    bindings = {}
    for role, semantic_key in module_bindings.items():
        domain = roles[role]["allowed_domains"][0]
        bindings[semantic_key] = {
            "entity_id": f"{domain}.{role}",
            "domain": domain,
            "verification": "verified",
        }
    bindings["infrastructure.unowned.status"] = {
        "entity_id": "sensor.unowned",
        "domain": "sensor",
        "verification": "verified",
    }
    return {
        "api_version": "nikas.home-assistant/semantic-inventory/v1",
        "kind": "SemanticInventory",
        "metadata": {
            "generated_at": "2026-09-02T10:49:37Z",
            "source": "home_assistant",
            "scrubbed": True,
            "snapshot_id": "sha256:0123456789abcdefabcd",
        },
        "spec": {"bindings": bindings},
    }


def test_migration_copies_only_verified_house_bindings(tmp_path: Path) -> None:
    target_root = tmp_path / "nikas_house"
    legacy_root = tmp_path / "legacy"
    contract, manifest = _prepare_public_sources(target_root)
    document = _legacy_inventory(contract, manifest)
    legacy_path = legacy_root / "inventory" / HOUSE_INVENTORY_FILENAME
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    source_before = legacy_path.read_bytes()

    result = migrate_legacy_house_inventory(target_root, legacy_root)

    assert result.migrated is True
    assert result.source_path == legacy_path
    assert result.target_path == target_root / "inventory" / HOUSE_INVENTORY_FILENAME
    migrated = yaml.safe_load(result.target_path.read_text(encoding="utf-8"))
    expected = set(manifest["spec"]["views"][0]["modules"][0]["bindings"].values())
    assert set(migrated["spec"]["bindings"]) == expected
    assert "infrastructure.unowned.status" not in migrated["spec"]["bindings"]
    assert legacy_path.read_bytes() == source_before


def test_migration_never_overwrites_target_inventory(tmp_path: Path) -> None:
    target_root = tmp_path / "nikas_house"
    legacy_root = tmp_path / "legacy"
    _prepare_public_sources(target_root)
    target = target_root / "inventory" / "existing.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("user-owned\n", encoding="utf-8")

    result = migrate_legacy_house_inventory(target_root, legacy_root)

    assert result.migrated is False
    assert result.reason == "target inventory already exists"
    assert target.read_text(encoding="utf-8") == "user-owned\n"


def test_migration_rejects_incomplete_legacy_inventory(tmp_path: Path) -> None:
    target_root = tmp_path / "nikas_house"
    legacy_root = tmp_path / "legacy"
    contract, manifest = _prepare_public_sources(target_root)
    document = _legacy_inventory(contract, manifest)
    document["spec"]["bindings"].pop("house.home.weather")
    legacy_path = legacy_root / "inventory" / HOUSE_INVENTORY_FILENAME
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )

    with pytest.raises(InventoryMigrationError, match="every verified House binding"):
        migrate_legacy_house_inventory(target_root, legacy_root)
