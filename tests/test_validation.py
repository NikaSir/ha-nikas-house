from __future__ import annotations

import json
from pathlib import Path

import yaml

from generator.validation import load_schema, validate_document, validate_repository


def _contract() -> dict:
    return {
        "api_version": "nikas.home-assistant/ui-contract/v1",
        "kind": "UIContract",
        "metadata": {
            "id": "example_subsystem",
            "title": "Synthetic subsystem",
            "version": "1.0",
        },
        "spec": {
            "roles": {
                "status": {
                    "label": "Status",
                    "description": "Synthetic status source",
                    "required": True,
                    "allowed_domains": ["sensor"],
                }
            },
            "states": {
                "normal": {"description": "Normal factual state", "rules": []},
                "event": {"description": "Active event state", "rules": []},
                "unreliable": {
                    "description": "Source cannot establish a factual state",
                    "rules": [],
                },
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


def _inventory() -> dict:
    return {
        "api_version": "nikas.home-assistant/semantic-inventory/v1",
        "kind": "SemanticInventory",
        "metadata": {
            "generated_at": "2026-08-21T09:00:00Z",
            "source": "home_assistant",
            "scrubbed": True,
        },
        "spec": {
            "bindings": {
                "example.synthetic.status": {
                    "entity_id": "sensor.synthetic_status",
                    "domain": "sensor",
                    "verification": "verified",
                }
            }
        },
    }


def _manifest() -> dict:
    return {
        "api_version": "nikas.home-assistant/panel-manifest/v1",
        "kind": "PanelManifest",
        "metadata": {
            "id": "example_panel",
            "title": "Synthetic panel",
            "version": "1.0",
        },
        "spec": {
            "dashboard_path": "/dashboard-example",
            "views": [
                {
                    "id": "overview",
                    "title": "Overview",
                    "path": "overview",
                    "order": 0,
                    "modules": [
                        {
                            "contract": "example_subsystem",
                            "order": 0,
                            "bindings": {"status": "example.synthetic.status"},
                        }
                    ],
                }
            ],
        },
    }


def test_contract_schema_accepts_explicit_reliability_semantics() -> None:
    schema = load_schema(Path("schemas/contract.schema.json"))
    assert validate_document(_contract(), schema, path=Path("contract.yaml")) == []


def test_contract_rejects_missing_unreliable_state() -> None:
    document = _contract()
    del document["spec"]["states"]["unreliable"]
    schema = load_schema(Path("schemas/contract.schema.json"))
    issues = validate_document(document, schema, path=Path("contract.yaml"))
    assert any("unreliable" in issue.message for issue in issues)


def test_manifest_policy_rejects_concrete_entity_binding() -> None:
    document = _manifest()
    document["spec"]["views"][0]["modules"][0]["bindings"]["entity_id"] = (
        "sensor.synthetic_status"
    )
    schema = load_schema(Path("schemas/manifest.schema.json"))
    issues = validate_document(
        document,
        schema,
        path=Path("manifest.yaml"),
        forbid_bindings=True,
    )
    assert any("binding key 'entity_id' is forbidden" in issue.message for issue in issues)


def test_inventory_schema_accepts_verified_binding() -> None:
    schema = load_schema(Path("schemas/inventory.schema.json"))
    assert validate_document(_inventory(), schema, path=Path("inventory.yaml")) == []


def test_repository_validation_routes_documents_to_correct_schema(tmp_path: Path) -> None:
    for directory in ("contracts", "inventory", "manifests", "schemas"):
        (tmp_path / directory).mkdir()

    for schema_name in (
        "contract.schema.json",
        "inventory.schema.json",
        "manifest.schema.json",
        "navigation.schema.json",
        "registry-snapshot.schema.json",
    ):
        source = Path("schemas") / schema_name
        (tmp_path / "schemas" / schema_name).write_text(
            source.read_text(encoding="utf-8"),
            encoding="utf-8",
        )

    (tmp_path / "contracts" / "example.yaml").write_text(
        yaml.safe_dump(_contract(), sort_keys=False), encoding="utf-8"
    )
    (tmp_path / "inventory" / "example.json").write_text(
        json.dumps(_inventory()), encoding="utf-8"
    )
    (tmp_path / "manifests" / "example.yml").write_text(
        yaml.safe_dump(_manifest(), sort_keys=False), encoding="utf-8"
    )

    assert validate_repository(tmp_path) == []
