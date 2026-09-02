from custom_components.nikas_house.registry_snapshot import (
    SNAPSHOT_API_VERSION,
    build_snapshot_document,
)
from generator.semantic_diff import diff_registry_snapshots


def _snapshot(*, device_area: str = "bathroom", device_labels=None, entity_labels=None):
    return build_snapshot_document(
        [
            {
                "entity_id": "sensor.bathroom_temperature",
                "domain": "sensor",
                "platform": "mqtt",
                "device_id": "dev-temp",
                "labels": list(entity_labels or ["environment"]),
                "disabled": False,
                "hidden": False,
            }
        ],
        devices=[
            {
                "device_id": "dev-temp",
                "area_id": device_area,
                "labels": list(device_labels or ["in_service"]),
                "name": "Bathroom sensor",
                "disabled": False,
            }
        ],
        areas=[
            {
                "area_id": "bathroom",
                "name": "Ванная",
                "floor_id": "floor-2",
                "labels": ["living_area"],
            }
        ],
        floors=[{"floor_id": "floor-2", "name": "Второй этаж", "level": 2}],
        labels=[
            {"label_id": "environment", "name": "Климат"},
            {"label_id": "in_service", "name": "В эксплуатации"},
            {"label_id": "living_area", "name": "Жилое помещение"},
        ],
        captured_at="2026-08-29T10:00:00Z",
        home_assistant_version="2026.8.3",
    )


def test_snapshot_contains_full_registry_topology():
    document = _snapshot()

    assert document["api_version"] == SNAPSHOT_API_VERSION
    assert document["metadata"]["contents"] == {
        "entities": 1,
        "devices": 1,
        "areas": 1,
        "floors": 1,
        "labels": 3,
    }
    assert document["spec"]["entities"][0]["device_id"] == "dev-temp"
    assert document["spec"]["devices"][0]["area_id"] == "bathroom"
    assert document["spec"]["areas"][0]["floor_id"] == "floor-2"
    assert document["spec"]["labels"][1]["name"] == "В эксплуатации"


def test_snapshot_id_changes_when_area_binding_changes():
    before = _snapshot(device_area="bathroom")
    after = _snapshot(device_area="bedroom")
    assert before["metadata"]["snapshot_id"] != after["metadata"]["snapshot_id"]


def test_snapshot_id_changes_when_labels_change():
    before = _snapshot(device_labels=["in_service"])
    after = _snapshot(device_labels=["maintenance"])
    assert before["metadata"]["snapshot_id"] != after["metadata"]["snapshot_id"]


def test_topology_diff_reports_device_area_and_label_changes():
    before = _snapshot(device_area="bathroom", device_labels=["in_service"])
    after = _snapshot(device_area="bedroom", device_labels=["maintenance"])

    changes = diff_registry_snapshots(before, after)
    assert [(change.kind, change.key) for change in changes] == [
        ("changed", "device:dev-temp")
    ]
    assert changes[0].before["area_id"] == "bathroom"
    assert changes[0].after["area_id"] == "bedroom"
    assert changes[0].before["labels"] == ["in_service"]
    assert changes[0].after["labels"] == ["maintenance"]
