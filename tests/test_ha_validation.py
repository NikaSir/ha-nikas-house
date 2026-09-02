from __future__ import annotations

import json
from pathlib import Path

import yaml

from custom_components.nikas_house.validation import validate_source_tree

REPO_ROOT = Path(__file__).parents[1]
PACKAGED_SCHEMAS = REPO_ROOT / "custom_components" / "nikas_house" / "schemas"
ROOT_SCHEMAS = REPO_ROOT / "schemas"


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _valid_documents() -> tuple[dict, dict, dict, dict]:
    contract = {
        "api_version": "nikas.home-assistant/ui-contract/v1",
        "kind": "UIContract",
        "metadata": {"id": "test.contract", "title": "Test", "version": "1.0"},
        "spec": {
            "roles": {
                "status": {
                    "label": "Status",
                    "description": "Status",
                    "required": True,
                    "allowed_domains": ["sensor"],
                }
            },
            "states": {
                "normal": {"description": "Normal", "rules": []},
                "event": {"description": "Event", "rules": []},
                "unreliable": {"description": "Unreliable", "rules": []},
            },
            "actions": [
                {
                    "id": "status_info",
                    "kind": "more_info",
                    "description": "Open status details",
                    "role": "status",
                }
            ],
            "presentation": {
                "renderer": "tiles_v1",
                "columns": 1,
                "role_order": ["status"],
            },
            "safety": {
                "unknown_is_unreliable": True,
                "unavailable_is_unreliable": True,
                "invent_entity_ids": False,
            },
        },
    }
    inventory = {
        "api_version": "nikas.home-assistant/semantic-inventory/v1",
        "kind": "SemanticInventory",
        "metadata": {
            "generated_at": "2026-08-21T09:00:00Z",
            "source": "home_assistant",
            "scrubbed": True,
        },
        "spec": {
            "bindings": {
                "test.synthetic.status": {
                    "entity_id": "sensor.test",
                    "domain": "sensor",
                    "verification": "verified",
                }
            }
        },
    }
    manifest = {
        "api_version": "nikas.home-assistant/panel-manifest/v1",
        "kind": "PanelManifest",
        "metadata": {"id": "test.panel", "title": "Test panel", "version": "1.0"},
        "spec": {
            "dashboard_path": "/dashboard-test",
            "views": [
                {
                    "id": "home",
                    "title": "Home",
                    "path": "home",
                    "order": 0,
                    "modules": [
                        {
                            "contract": "test.contract",
                            "order": 0,
                            "bindings": {"status": "test.synthetic.status"},
                        }
                    ],
                }
            ],
        },
    }
    navigation = {
        "api_version": "nikas.home-assistant/navigation/v1",
        "kind": "NavigationContract",
        "metadata": {"id": "main", "version": "1.0"},
        "spec": {
            "routes": {
                "home": {"title": "Home", "path": "/dashboard-test"},
            },
            "global_tabs": [
                {
                    "id": "home",
                    "route": "home",
                    "title": "Home",
                    "icon": "mdi:home-outline",
                }
            ],
        },
    }
    return contract, inventory, manifest, navigation


def test_packaged_schemas_match_repository_schemas() -> None:
    for name in (
        "contract.schema.json",
        "inventory.schema.json",
        "manifest.schema.json",
        "navigation.schema.json",
        "registry-snapshot.schema.json",
    ):
        assert json.loads((PACKAGED_SCHEMAS / name).read_text(encoding="utf-8")) == json.loads(
            (ROOT_SCHEMAS / name).read_text(encoding="utf-8")
        )


def test_source_tree_status_progression(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    assert validate_source_tree(missing, PACKAGED_SCHEMAS).status == "missing"

    source_root = tmp_path / "source"
    source_root.mkdir()
    assert validate_source_tree(source_root, PACKAGED_SCHEMAS).status == "empty"

    contract, inventory, manifest, navigation = _valid_documents()
    _write_yaml(source_root / "contracts" / "test.yaml", contract)
    assert validate_source_tree(source_root, PACKAGED_SCHEMAS).status == "incomplete"

    _write_yaml(source_root / "inventory" / "test.yaml", inventory)
    _write_yaml(source_root / "manifests" / "test.yaml", manifest)
    assert validate_source_tree(source_root, PACKAGED_SCHEMAS).status == "incomplete"

    _write_yaml(source_root / "navigation" / "main.yaml", navigation)

    snapshot = validate_source_tree(source_root, PACKAGED_SCHEMAS)
    assert snapshot.status == "valid"
    assert snapshot.document_count == 4
    assert snapshot.issues == ()


def test_direct_binding_in_manifest_is_invalid(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    contract, inventory, manifest, navigation = _valid_documents()
    manifest["spec"]["views"][0]["modules"][0]["bindings"]["entity_id"] = (
        "sensor.forbidden"
    )

    _write_yaml(source_root / "contracts" / "test.yaml", contract)
    _write_yaml(source_root / "inventory" / "test.yaml", inventory)
    _write_yaml(source_root / "manifests" / "test.yaml", manifest)
    _write_yaml(source_root / "navigation" / "main.yaml", navigation)

    snapshot = validate_source_tree(source_root, PACKAGED_SCHEMAS)
    assert snapshot.status == "invalid"
    assert any(
        "binding key 'entity_id' is forbidden" in issue.message
        for issue in snapshot.issues
    )
