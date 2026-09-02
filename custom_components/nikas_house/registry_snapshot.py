"""Scrubbed Home Assistant registry snapshot support."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Mapping

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

CURRENT_SNAPSHOT = "current.json"
PREVIOUS_SNAPSHOT = "previous.json"
SNAPSHOT_API_VERSION = "nikas.home-assistant/registry-snapshot/v2"


@dataclass(frozen=True, slots=True)
class SnapshotWriteResult:
    """Result of atomically writing a registry snapshot."""

    current_path: Path
    previous_path: Path | None
    changed: bool


def _ordered_records(
    records: Iterable[Mapping[str, Any]],
    key: str,
) -> list[dict[str, Any]]:
    return sorted((dict(record) for record in records), key=lambda item: str(item[key]))


def _labels(value: Any) -> list[str]:
    """Return deterministic label IDs without depending on registry container type."""
    if not value:
        return []
    return sorted(str(item) for item in value)


def canonical_snapshot_id(spec: Mapping[str, Any] | Iterable[Mapping[str, Any]]) -> str:
    """Return a stable content ID for scrubbed registry topology.

    Iterable input is retained for compatibility with v1 callers and is treated as
    an entity-only snapshot.
    """
    if isinstance(spec, Mapping):
        payload_obj: Any = spec
    else:
        payload_obj = {
            "entities": _ordered_records(spec, "entity_id"),
            "devices": [],
            "areas": [],
            "floors": [],
            "labels": [],
        }
    payload = json.dumps(
        payload_obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()[:20]}"


def build_snapshot_document(
    entities: Iterable[Mapping[str, Any]],
    *,
    captured_at: str,
    home_assistant_version: str,
    devices: Iterable[Mapping[str, Any]] = (),
    areas: Iterable[Mapping[str, Any]] = (),
    floors: Iterable[Mapping[str, Any]] = (),
    labels: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Create a deterministic, scrubbed registry topology snapshot."""
    spec = {
        "entities": _ordered_records(entities, "entity_id"),
        "devices": _ordered_records(devices, "device_id"),
        "areas": _ordered_records(areas, "area_id"),
        "floors": _ordered_records(floors, "floor_id"),
        "labels": _ordered_records(labels, "label_id"),
    }
    return {
        "api_version": SNAPSHOT_API_VERSION,
        "kind": "RegistrySnapshot",
        "metadata": {
            "captured_at": captured_at,
            "source": "home_assistant",
            "scrubbed": True,
            "snapshot_id": canonical_snapshot_id(spec),
            "home_assistant_version": home_assistant_version,
            "contents": {
                "entities": len(spec["entities"]),
                "devices": len(spec["devices"]),
                "areas": len(spec["areas"]),
                "floors": len(spec["floors"]),
                "labels": len(spec["labels"]),
            },
        },
        "spec": spec,
    }


def capture_registry_snapshot(hass: HomeAssistant) -> dict[str, Any]:
    """Capture scrubbed registry topology required for binding and drift review."""
    from homeassistant.const import __version__
    from homeassistant.helpers import area_registry as ar
    from homeassistant.helpers import device_registry as dr
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers import floor_registry as fr
    from homeassistant.helpers import label_registry as lr

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    area_registry = ar.async_get(hass)
    floor_registry = fr.async_get(hass)
    label_registry = lr.async_get(hass)

    entities: list[dict[str, Any]] = []
    for entry in entity_registry.entities.values():
        entity: dict[str, Any] = {
            "entity_id": entry.entity_id,
            "domain": entry.domain,
            "platform": entry.platform,
            "disabled": entry.disabled_by is not None,
            "hidden": entry.hidden_by is not None,
        }
        if entry.device_id is not None:
            entity["device_id"] = entry.device_id
        if entry.area_id is not None:
            entity["area_id"] = entry.area_id
        entity_labels = _labels(getattr(entry, "labels", None))
        if entity_labels:
            entity["labels"] = entity_labels
        if entry.name is not None:
            entity["name"] = entry.name
        if entry.original_name is not None:
            entity["original_name"] = entry.original_name
        device_class = entry.device_class or entry.original_device_class
        if device_class is not None:
            entity["device_class"] = device_class
        if entry.unit_of_measurement is not None:
            entity["unit_of_measurement"] = entry.unit_of_measurement
        entities.append(entity)

    devices: list[dict[str, Any]] = []
    for entry in device_registry.devices.values():
        device: dict[str, Any] = {
            "device_id": entry.id,
            "disabled": entry.disabled_by is not None,
        }
        if entry.area_id is not None:
            device["area_id"] = entry.area_id
        device_labels = _labels(getattr(entry, "labels", None))
        if device_labels:
            device["labels"] = device_labels
        if entry.name_by_user is not None:
            device["name_by_user"] = entry.name_by_user
        if entry.name is not None:
            device["name"] = entry.name
        if entry.manufacturer is not None:
            device["manufacturer"] = entry.manufacturer
        if entry.model is not None:
            device["model"] = entry.model
        if getattr(entry, "model_id", None) is not None:
            device["model_id"] = entry.model_id
        if entry.via_device_id is not None:
            device["via_device_id"] = entry.via_device_id
        entry_type = getattr(entry, "entry_type", None)
        if entry_type is not None:
            device["entry_type"] = str(getattr(entry_type, "value", entry_type))
        devices.append(device)

    areas: list[dict[str, Any]] = []
    for entry in area_registry.areas.values():
        area: dict[str, Any] = {
            "area_id": entry.id,
            "name": entry.name,
        }
        if getattr(entry, "floor_id", None) is not None:
            area["floor_id"] = entry.floor_id
        if getattr(entry, "icon", None) is not None:
            area["icon"] = entry.icon
        aliases = sorted(str(item) for item in (getattr(entry, "aliases", None) or []))
        if aliases:
            area["aliases"] = aliases
        area_labels = _labels(getattr(entry, "labels", None))
        if area_labels:
            area["labels"] = area_labels
        areas.append(area)

    floors: list[dict[str, Any]] = []
    for entry in floor_registry.floors.values():
        floor: dict[str, Any] = {
            "floor_id": entry.floor_id,
            "name": entry.name,
        }
        if getattr(entry, "level", None) is not None:
            floor["level"] = entry.level
        if getattr(entry, "icon", None) is not None:
            floor["icon"] = entry.icon
        aliases = sorted(str(item) for item in (getattr(entry, "aliases", None) or []))
        if aliases:
            floor["aliases"] = aliases
        floors.append(floor)

    labels: list[dict[str, Any]] = []
    for entry in label_registry.labels.values():
        label: dict[str, Any] = {
            "label_id": entry.label_id,
            "name": entry.name,
        }
        if getattr(entry, "color", None) is not None:
            label["color"] = entry.color
        if getattr(entry, "icon", None) is not None:
            label["icon"] = entry.icon
        if getattr(entry, "description", None):
            label["description"] = entry.description
        labels.append(label)

    captured_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return build_snapshot_document(
        entities,
        devices=devices,
        areas=areas,
        floors=floors,
        labels=labels,
        captured_at=captured_at,
        home_assistant_version=__version__,
    )


def write_registry_snapshot(
    snapshot_root: Path,
    document: Mapping[str, Any],
) -> SnapshotWriteResult:
    """Atomically rotate current to previous only when registry facts changed."""
    snapshot_root.mkdir(parents=True, exist_ok=True)
    current_path = snapshot_root / CURRENT_SNAPSHOT
    previous_path = snapshot_root / PREVIOUS_SNAPSHOT
    new_snapshot_id = document["metadata"]["snapshot_id"]
    changed = True

    if current_path.exists():
        try:
            existing = json.loads(current_path.read_text(encoding="utf-8"))
            old_snapshot_id = existing.get("metadata", {}).get("snapshot_id")
        except (json.JSONDecodeError, OSError):
            old_snapshot_id = None
        if old_snapshot_id == new_snapshot_id:
            changed = False
        elif old_snapshot_id is not None:
            os.replace(current_path, previous_path)

    temp_path = snapshot_root / f".{CURRENT_SNAPSHOT}.tmp"
    temp_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temp_path, current_path)

    return SnapshotWriteResult(
        current_path=current_path,
        previous_path=previous_path if previous_path.exists() else None,
        changed=changed,
    )
