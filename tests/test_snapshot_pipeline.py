from __future__ import annotations

import json
from pathlib import Path

import yaml

from custom_components.nikas_house.registry_snapshot import (
    build_snapshot_document,
    write_registry_snapshot,
)
from generator.cli import main
from generator.semantic_diff import diff_inventories, diff_registry_snapshots
from generator.snapshot import (
    ParsedBinding,
    SnapshotBindingError,
    build_inventory,
    canonical_snapshot_id,
    parse_binding,
    validate_snapshot_document,
)
from generator.validation import load_schema, validate_document

ROOT = Path(__file__).parents[1]


def entity(entity_id: str, **extra: object) -> dict[str, object]:
    domain = entity_id.split(".", 1)[0]
    data: dict[str, object] = {
        "entity_id": entity_id,
        "domain": domain,
        "platform": "synthetic",
        "disabled": False,
        "hidden": False,
    }
    data.update(extra)
    return data


def snapshot(
    *entities: dict[str, object],
    captured_at: str = "2026-08-21T10:00:00Z",
) -> dict:
    entity_list = list(entities)
    return {
        "api_version": "nikas.home-assistant/registry-snapshot/v1",
        "kind": "RegistrySnapshot",
        "metadata": {
            "captured_at": captured_at,
            "source": "home_assistant",
            "scrubbed": True,
            "snapshot_id": canonical_snapshot_id(entity_list),
            "home_assistant_version": "2026.8.1",
        },
        "spec": {"entities": entity_list},
    }


def test_snapshot_schema_and_content_hash_are_valid() -> None:
    document = snapshot(entity("binary_sensor.door", device_class="door"))
    schema = load_schema(ROOT / "schemas/registry-snapshot.schema.json")
    assert validate_snapshot_document(document, schema, path=Path("snapshot.json")) == []


def test_snapshot_rejects_domain_mismatch_and_duplicate_entity() -> None:
    first = entity("sensor.temperature")
    second = entity("sensor.temperature")
    second["domain"] = "binary_sensor"
    document = snapshot(first, second)
    schema = load_schema(ROOT / "schemas/registry-snapshot.schema.json")
    issues = validate_snapshot_document(document, schema, path=Path("snapshot.json"))
    assert any("does not match entity_id" in issue.message for issue in issues)
    assert any("duplicate entity_id" in issue.message for issue in issues)


def test_semantic_key_namespace_cannot_be_home_assistant_entity_id() -> None:
    parsed = parse_binding("infrastructure.router.status=sensor.router_status")
    assert parsed.semantic_key == "infrastructure.router.status"

    try:
        parse_binding("sensor.router_status=sensor.router_status")
    except SnapshotBindingError as exc:
        assert "at least three dot-separated segments" in str(exc)
    else:
        raise AssertionError("entity-shaped semantic key must be rejected")


def test_inventory_build_rejects_entities_absent_from_snapshot() -> None:
    document = snapshot(entity("binary_sensor.door", device_class="door"))
    inventory = build_inventory(
        document,
        [ParsedBinding("access.garden.door", "binary_sensor.door")],
    )
    schema = load_schema(ROOT / "schemas/inventory.schema.json")
    assert validate_document(inventory, schema, path=Path("inventory.yaml")) == []
    assert inventory["metadata"]["snapshot_id"] == document["metadata"]["snapshot_id"]

    try:
        build_inventory(
            document,
            [ParsedBinding("access.missing.entity", "binary_sensor.missing")],
        )
    except SnapshotBindingError as exc:
        assert "absent from snapshot" in str(exc)
    else:
        raise AssertionError("missing entity must be rejected")


def test_inventory_diff_reports_rebinding() -> None:
    document = snapshot(entity("binary_sensor.door"), entity("binary_sensor.door_new"))
    before = build_inventory(
        document,
        [ParsedBinding("access.entry.door", "binary_sensor.door")],
    )
    after = build_inventory(
        document,
        [ParsedBinding("access.entry.door", "binary_sensor.door_new")],
    )
    assert [(change.kind, change.key) for change in diff_inventories(before, after)] == [
        ("rebound", "access.entry.door")
    ]


def test_snapshot_diff_ignores_capture_time() -> None:
    before = snapshot(entity("sensor.temperature", unit_of_measurement="°C"))
    after = snapshot(
        entity("sensor.temperature", unit_of_measurement="°C"),
        entity("binary_sensor.door", device_class="door"),
        captured_at="2026-08-21T11:00:00Z",
    )
    assert [(change.kind, change.key) for change in diff_registry_snapshots(before, after)] == [
        ("added", "binary_sensor.door")
    ]


def test_ha_snapshot_id_is_order_independent() -> None:
    first = build_snapshot_document(
        [entity("sensor.b"), entity("sensor.a")],
        captured_at="2026-08-21T10:00:00Z",
        home_assistant_version="2026.8.1",
    )
    second = build_snapshot_document(
        [entity("sensor.a"), entity("sensor.b")],
        captured_at="2026-08-21T11:00:00Z",
        home_assistant_version="2026.8.1",
    )
    assert first["metadata"]["snapshot_id"] == second["metadata"]["snapshot_id"]


def test_snapshot_rotation_only_on_registry_change(tmp_path: Path) -> None:
    first = build_snapshot_document(
        [entity("sensor.a")],
        captured_at="2026-08-21T10:00:00Z",
        home_assistant_version="2026.8.1",
    )
    assert write_registry_snapshot(tmp_path, first).changed is True

    same = build_snapshot_document(
        [entity("sensor.a")],
        captured_at="2026-08-21T11:00:00Z",
        home_assistant_version="2026.8.1",
    )
    same_result = write_registry_snapshot(tmp_path, same)
    assert same_result.changed is False
    assert same_result.previous_path is None

    changed = build_snapshot_document(
        [entity("sensor.a"), entity("sensor.b")],
        captured_at="2026-08-21T12:00:00Z",
        home_assistant_version="2026.8.1",
    )
    changed_result = write_registry_snapshot(tmp_path, changed)
    assert changed_result.changed is True
    previous = json.loads((tmp_path / "previous.json").read_text(encoding="utf-8"))
    assert previous["metadata"]["snapshot_id"] == same["metadata"]["snapshot_id"]


def test_packaged_snapshot_schema_matches_repository_schema() -> None:
    repository = ROOT / "schemas" / "registry-snapshot.schema.json"
    packaged = (
        ROOT
        / "custom_components"
        / "nikas_house"
        / "schemas"
        / "registry-snapshot.schema.json"
    )
    assert json.loads(repository.read_text(encoding="utf-8")) == json.loads(
        packaged.read_text(encoding="utf-8")
    )


def test_cli_inventory_build(monkeypatch, tmp_path: Path) -> None:
    snapshot_path = tmp_path / "snapshot.yaml"
    output = tmp_path / "inventory.yaml"
    snapshot_path.write_text(
        yaml.safe_dump(snapshot(entity("binary_sensor.garden_door")), sort_keys=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "ha-contract-ui",
            "inventory",
            "build",
            str(snapshot_path),
            str(output),
            "--snapshot-schema",
            str(ROOT / "schemas/registry-snapshot.schema.json"),
            "--inventory-schema",
            str(ROOT / "schemas/inventory.schema.json"),
            "--bind",
            "access.garden.door=binary_sensor.garden_door",
        ],
    )
    assert main() == 0
    built = yaml.safe_load(output.read_text(encoding="utf-8"))
    assert (
        built["spec"]["bindings"]["access.garden.door"]["entity_id"]
        == "binary_sensor.garden_door"
    )
