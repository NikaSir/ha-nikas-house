from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .validation import ValidationIssue, load_document, load_schema, validate_document

SEMANTIC_KEY_RE = re.compile(
    r"^[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*){2,}$"
)
ENTITY_ID_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z0-9_]+$")


class SnapshotBindingError(ValueError):
    """Raised when an explicit semantic binding cannot be verified."""


@dataclass(frozen=True, slots=True)
class ParsedBinding:
    semantic_key: str
    entity_id: str


def canonical_snapshot_id(payload_source: Mapping[str, Any] | Iterable[Mapping[str, Any]]) -> str:
    """Return a stable content ID for v1 entity facts or v2 registry topology."""
    if isinstance(payload_source, Mapping):
        payload_obj: Any = payload_source
    else:
        payload_obj = sorted(
            (dict(entity) for entity in payload_source),
            key=lambda item: item["entity_id"],
        )
    payload = json.dumps(
        payload_obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()[:20]}"


def validate_snapshot_document(
    document: Any,
    schema: dict[str, Any],
    *,
    path: Path,
) -> list[ValidationIssue]:
    """Validate schema plus cross-field registry invariants."""
    issues = validate_document(document, schema, path=path)
    if issues or not isinstance(document, dict):
        return issues

    spec = document.get("spec", {})
    entities = spec.get("entities", [])
    seen: set[str] = set()
    for index, entity in enumerate(entities):
        if not isinstance(entity, dict):
            continue
        entity_id = entity.get("entity_id")
        domain = entity.get("domain")
        if isinstance(entity_id, str) and isinstance(domain, str):
            actual_domain = entity_id.partition(".")[0]
            if actual_domain != domain:
                issues.append(
                    ValidationIssue(
                        path,
                        f"$.spec.entities[{index}].domain",
                        f"domain {domain!r} does not match entity_id {entity_id!r}",
                    )
                )
            if entity_id in seen:
                issues.append(
                    ValidationIssue(
                        path,
                        f"$.spec.entities[{index}].entity_id",
                        f"duplicate entity_id {entity_id!r}",
                    )
                )
            seen.add(entity_id)

    metadata = document.get("metadata", {})
    if document.get("api_version") == "nikas.home-assistant/registry-snapshot/v2":
        expected_snapshot_id = canonical_snapshot_id(spec)
    else:
        expected_snapshot_id = canonical_snapshot_id(entities)
    snapshot_id = metadata.get("snapshot_id")
    if isinstance(snapshot_id, str) and snapshot_id != expected_snapshot_id:
        issues.append(
            ValidationIssue(
                path,
                "$.metadata.snapshot_id",
                f"snapshot_id must match scrubbed content ({expected_snapshot_id})",
            )
        )
    return issues


def load_validated_snapshot(path: Path, schema_path: Path) -> dict[str, Any]:
    """Load one scrubbed registry snapshot or raise with actionable details."""
    document = load_document(path)
    schema = load_schema(schema_path)
    issues = validate_snapshot_document(document, schema, path=path)
    if issues:
        rendered = "\n".join(str(issue) for issue in issues)
        raise SnapshotBindingError(f"invalid registry snapshot:\n{rendered}")
    assert isinstance(document, dict)
    return document


def parse_binding(value: str) -> ParsedBinding:
    """Parse scope.object.role=domain.entity from the CLI."""
    semantic_key, separator, entity_id = value.partition("=")
    if not separator or not semantic_key or not entity_id:
        raise SnapshotBindingError(
            f"invalid binding {value!r}; expected scope.object.role=domain.entity"
        )
    if not SEMANTIC_KEY_RE.fullmatch(semantic_key):
        raise SnapshotBindingError(
            f"invalid semantic key {semantic_key!r}; use at least three dot-separated segments"
        )
    if not ENTITY_ID_RE.fullmatch(entity_id):
        raise SnapshotBindingError(f"invalid Home Assistant entity_id {entity_id!r}")
    return ParsedBinding(semantic_key=semantic_key, entity_id=entity_id)


def build_inventory(
    snapshot: Mapping[str, Any],
    bindings: Iterable[ParsedBinding],
) -> dict[str, Any]:
    """Build deterministic verified inventory from explicit bindings only."""
    entities = {
        entity["entity_id"]: entity
        for entity in snapshot["spec"]["entities"]
    }
    output_bindings: dict[str, dict[str, Any]] = {}
    for binding in bindings:
        if not SEMANTIC_KEY_RE.fullmatch(binding.semantic_key):
            raise SnapshotBindingError(
                f"invalid semantic key {binding.semantic_key!r}; "
                "use at least three dot-separated segments"
            )
        if not ENTITY_ID_RE.fullmatch(binding.entity_id):
            raise SnapshotBindingError(
                f"invalid Home Assistant entity_id {binding.entity_id!r}"
            )
        if binding.semantic_key in output_bindings:
            raise SnapshotBindingError(
                f"semantic key {binding.semantic_key!r} is bound more than once"
            )
        if binding.entity_id not in entities:
            raise SnapshotBindingError(
                f"entity {binding.entity_id!r} is absent from snapshot "
                f"{snapshot['metadata']['snapshot_id']}"
            )
        entity = entities[binding.entity_id]
        if entity.get("disabled"):
            raise SnapshotBindingError(
                f"entity {binding.entity_id!r} is disabled in snapshot "
                f"{snapshot['metadata']['snapshot_id']}"
            )
        output: dict[str, Any] = {
            "entity_id": binding.entity_id,
            "domain": entity["domain"],
            "verification": "verified",
        }
        for source_key, target_key in (
            ("device_class", "device_class"),
            ("unit_of_measurement", "unit_of_measurement"),
            ("area", "area"),
            ("area_id", "area_id"),
            ("device_id", "device_id"),
        ):
            value = entity.get(source_key)
            if value is not None:
                output[target_key] = value
        output_bindings[binding.semantic_key] = output

    if not output_bindings:
        raise SnapshotBindingError("at least one explicit --bind is required")

    metadata = snapshot["metadata"]
    inventory_metadata: dict[str, Any] = {
        "generated_at": metadata["captured_at"],
        "source": "home_assistant",
        "scrubbed": True,
        "snapshot_id": metadata["snapshot_id"],
    }
    if version := metadata.get("home_assistant_version"):
        inventory_metadata["home_assistant_version"] = version

    return {
        "api_version": "nikas.home-assistant/semantic-inventory/v1",
        "kind": "SemanticInventory",
        "metadata": inventory_metadata,
        "spec": {"bindings": dict(sorted(output_bindings.items()))},
    }
