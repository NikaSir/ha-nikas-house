"""Exercise snapshot capture against the public device registry contract."""
import json
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace as Entry

import pytest

from custom_components.nikas_house.registry_snapshot import capture_registry_snapshot
from generator.snapshot import validate_snapshot_document

ROOT = Path(__file__).resolve().parents[1]


class Child(Entry):
    def __getattr__(self, name):
        if name in {"manufacturer", "model", "model_id", "via_device_id", "entry_type"}:
            raise AssertionError(f"Child-only compatibility property read: {name}")
        raise AttributeError(name)


@pytest.fixture
def registry(monkeypatch):
    parent = Entry(id="parent", area_id="bathroom", disabled_by=None, labels={"active"},
                   name="Parent", name_by_user=None, manufacturer="Vendor", model="Model",
                   model_id=None, via_device_id=None, entry_type=None)
    child = Child(id="child", parent_device_id="parent", area_id=None, disabled_by=None,
                  labels={"child_label"}, name="Child", name_by_user=None)
    entity = Entry(entity_id="sensor.child", domain="sensor", platform="demo", disabled_by=None,
                   hidden_by=None, device_id="child", area_id=None, labels=set(), name=None,
                   original_name=None, device_class=None, original_device_class=None,
                   unit_of_measurement=None)
    devices = Entry(devices=(parent,), child_devices=(child,))
    registries = {
        "device_registry": devices,
        "entity_registry": Entry(entities={entity.entity_id: entity}),
        "area_registry": Entry(areas={"bathroom": Entry(id="bathroom", name="Bathroom")}),
        "floor_registry": Entry(floors={}), "label_registry": Entry(labels={}),
    }
    helpers = ModuleType("homeassistant.helpers")
    for name, value in registries.items():
        setattr(helpers, name, Entry(async_get=lambda hass, registry=value: registry))
    monkeypatch.setitem(sys.modules, "homeassistant", ModuleType("homeassistant"))
    monkeypatch.setitem(sys.modules, "homeassistant.helpers", helpers)
    monkeypatch.setitem(sys.modules, "homeassistant.const", Entry(__version__="2026.9.4"))
    return devices, parent, child, entity


def test_capture_collection_includes_child_topology_and_inherited_area(registry):
    document = capture_registry_snapshot(None)
    devices = {item["device_id"]: item for item in document["spec"]["devices"]}
    assert devices["child"] == {
        "device_id": "child", "parent_device_id": "parent", "area_id": "bathroom",
        "disabled": False, "labels": ["child_label"], "name": "Child",
    }
    assert devices["parent"]["manufacturer"] == "Vendor"
    assert document["metadata"]["contents"]["devices"] == 2
    assert document["spec"]["entities"][0]["device_id"] in devices
    for schema_path in (ROOT / "schemas/registry-snapshot.schema.json",
                        ROOT / "custom_components/nikas_house/schemas/registry-snapshot.schema.json"):
        assert validate_snapshot_document(document, json.loads(schema_path.read_text()), path=Path("snapshot.json")) == []


@pytest.mark.parametrize("area,parent_id,expected", [
    ("kitchen", "parent", "kitchen"), (None, "missing", None),
])
def test_child_area_override_and_missing_parent(registry, area, parent_id, expected):
    _, _, child, entity = registry
    child.area_id, child.parent_device_id = area, parent_id
    entity.area_id = "bedroom"
    document = capture_registry_snapshot(None)
    child_out = next(d for d in document["spec"]["devices"] if d["device_id"] == "child")
    assert child_out.get("area_id") == expected
    assert child_out["parent_device_id"] == parent_id
    assert document["spec"]["entities"][0]["area_id"] == "bedroom"


def test_legacy_registry_without_child_devices(registry):
    devices, parent, _, _ = registry
    devices.devices = {"parent": parent}
    del devices.child_devices
    document = capture_registry_snapshot(None)
    assert [d["device_id"] for d in document["spec"]["devices"]] == ["parent"]


def test_inherited_area_changes_snapshot_hash(registry):
    devices, parent, _, _ = registry
    before = capture_registry_snapshot(None)
    parent.area_id = "kitchen"
    after = capture_registry_snapshot(None)
    assert before["metadata"]["snapshot_id"] != after["metadata"]["snapshot_id"]
    child_out = next(d for d in after["spec"]["devices"] if d["device_id"] == "child")
    assert child_out["area_id"] == "kitchen"


def test_snapshot_independent_of_device_order(registry):
    devices, parent, _, _ = registry
    second = Entry(**{**vars(parent), "id": "second"})
    devices.devices = (parent, second)
    before = capture_registry_snapshot(None)
    devices.devices = (second, parent)
    after = capture_registry_snapshot(None)
    assert before["spec"] == after["spec"]
    assert before["metadata"]["snapshot_id"] == after["metadata"]["snapshot_id"]
