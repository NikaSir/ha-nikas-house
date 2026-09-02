from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True, slots=True)
class SemanticChange:
    """One meaning-level change in a generated input."""

    kind: str
    key: str
    before: Any
    after: Any

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _diff_keyed(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    rebind_field: str | None = None,
) -> list[SemanticChange]:
    changes: list[SemanticChange] = []
    for key in sorted(before.keys() | after.keys()):
        old = before.get(key)
        new = after.get(key)
        if key not in before:
            changes.append(SemanticChange("added", key, None, new))
        elif key not in after:
            changes.append(SemanticChange("removed", key, old, None))
        elif old != new:
            kind = "changed"
            if (
                rebind_field
                and isinstance(old, Mapping)
                and isinstance(new, Mapping)
                and old.get(rebind_field) != new.get(rebind_field)
            ):
                kind = "rebound"
            changes.append(SemanticChange(kind, key, old, new))
    return changes


def diff_inventories(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> list[SemanticChange]:
    """Compare semantic bindings independently of formatting or metadata."""
    return _diff_keyed(
        before["spec"]["bindings"],
        after["spec"]["bindings"],
        rebind_field="entity_id",
    )


def _records_by_id(
    spec: Mapping[str, Any],
    collection: str,
    id_field: str,
) -> dict[str, Any]:
    return {
        str(record[id_field]): record
        for record in spec.get(collection, [])
        if isinstance(record, Mapping) and id_field in record
    }


def diff_registry_snapshots(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> list[SemanticChange]:
    """Compare scrubbed registry topology independently of capture time.

    Entity keys remain unprefixed for v1 compatibility. Topology collections added
    in snapshot v2 use explicit prefixes so an area/device/label change is visible
    and cannot collide with a Home Assistant entity_id.
    """
    old_spec = before["spec"]
    new_spec = after["spec"]
    changes = _diff_keyed(
        _records_by_id(old_spec, "entities", "entity_id"),
        _records_by_id(new_spec, "entities", "entity_id"),
    )

    for collection, id_field, prefix in (
        ("devices", "device_id", "device:"),
        ("areas", "area_id", "area:"),
        ("floors", "floor_id", "floor:"),
        ("labels", "label_id", "label:"),
    ):
        scoped = _diff_keyed(
            _records_by_id(old_spec, collection, id_field),
            _records_by_id(new_spec, collection, id_field),
        )
        changes.extend(
            SemanticChange(
                change.kind,
                f"{prefix}{change.key}",
                change.before,
                change.after,
            )
            for change in scoped
        )
    return changes


def render_text(changes: list[SemanticChange]) -> str:
    """Render a compact deterministic human review."""
    if not changes:
        return "No semantic changes."
    lines = [f"{len(changes)} semantic change(s):"]
    for change in changes:
        lines.append(f"- {change.kind}: {change.key}")
    return "\n".join(lines)