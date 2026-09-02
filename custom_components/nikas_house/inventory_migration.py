"""One-time import of the verified House inventory into NikaS House storage."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

LEGACY_SOURCE_DIRECTORY = "contract_generated_ui"
HOUSE_INVENTORY_FILENAME = "house_private_inventory.yaml"
SUPPORTED_SUFFIXES = frozenset({".json", ".yaml", ".yml"})


class InventoryMigrationError(ValueError):
    """Raised when an existing legacy inventory cannot be imported safely."""


@dataclass(frozen=True, slots=True)
class InventoryMigrationResult:
    """Describe the outcome of a non-destructive inventory import."""

    migrated: bool
    source_path: Path | None = None
    target_path: Path | None = None
    reason: str | None = None


def _documents(root: Path) -> Iterable[Path]:
    if not root.exists():
        return ()
    return (
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def _load_object(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            document = json.load(handle)
        else:
            document = yaml.safe_load(handle)
    if not isinstance(document, dict):
        raise InventoryMigrationError(f"inventory document root must be an object: {path}")
    return document


def _required_house_bindings(source_root: Path) -> frozenset[str]:
    manifests: list[dict[str, Any]] = []
    for path in _documents(source_root / "manifests"):
        document = _load_object(path)
        specialized = document.get("spec", {}).get("specialized_panel")
        if (
            document.get("kind") == "PanelManifest"
            and isinstance(specialized, dict)
            and specialized.get("template") == "house_overview_v1"
        ):
            manifests.append(document)
    if len(manifests) != 1:
        raise InventoryMigrationError(
            f"exactly one House manifest is required for inventory migration; found {len(manifests)}"
        )

    required: set[str] = set()
    for view in manifests[0].get("spec", {}).get("views", []):
        if not isinstance(view, dict):
            continue
        for module in view.get("modules", []):
            if not isinstance(module, dict):
                continue
            bindings = module.get("bindings")
            if not isinstance(bindings, dict):
                continue
            for semantic_key in bindings.values():
                if not isinstance(semantic_key, str) or not semantic_key:
                    raise InventoryMigrationError("House manifest contains an invalid semantic key")
                required.add(semantic_key)
    if not required:
        raise InventoryMigrationError("House manifest contains no semantic bindings")
    return frozenset(required)


def _verified_house_document(
    document: dict[str, Any],
    required: frozenset[str],
) -> dict[str, Any] | None:
    if document.get("kind") != "SemanticInventory":
        return None
    metadata = document.get("metadata")
    bindings = document.get("spec", {}).get("bindings")
    if not isinstance(metadata, dict) or metadata.get("scrubbed") is not True:
        return None
    if not isinstance(bindings, dict) or not required.issubset(bindings):
        return None

    selected: dict[str, dict[str, Any]] = {}
    for semantic_key in sorted(required):
        binding = bindings.get(semantic_key)
        if not isinstance(binding, dict) or binding.get("verification") != "verified":
            return None
        entity_id = binding.get("entity_id")
        domain = binding.get("domain")
        if (
            not isinstance(entity_id, str)
            or not isinstance(domain, str)
            or entity_id.partition(".")[0] != domain
        ):
            return None
        selected[semantic_key] = dict(binding)

    return {
        "api_version": document.get("api_version"),
        "kind": "SemanticInventory",
        "metadata": dict(metadata),
        "spec": {"bindings": selected},
    }


def migrate_legacy_house_inventory(
    source_root: Path,
    legacy_source_root: Path,
) -> InventoryMigrationResult:
    """Copy one complete verified House inventory without modifying its source."""
    target_root = source_root / "inventory"
    existing = list(_documents(target_root))
    if existing:
        return InventoryMigrationResult(
            migrated=False,
            target_path=existing[0],
            reason="target inventory already exists",
        )

    legacy_inventory_root = legacy_source_root / "inventory"
    candidates = list(_documents(legacy_inventory_root))
    if not candidates:
        return InventoryMigrationResult(
            migrated=False,
            reason="legacy House inventory is unavailable",
        )

    required = _required_house_bindings(source_root)
    preferred_name = HOUSE_INVENTORY_FILENAME.casefold()
    candidates.sort(key=lambda path: (path.name.casefold() != preferred_name, str(path)))
    for candidate in candidates:
        document = _verified_house_document(_load_object(candidate), required)
        if document is None:
            continue
        target_root.mkdir(parents=True, exist_ok=True)
        target = target_root / HOUSE_INVENTORY_FILENAME
        temporary = target.with_name(f".{target.name}.tmp")
        temporary.write_text(
            yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        os.replace(temporary, target)
        return InventoryMigrationResult(
            migrated=True,
            source_path=candidate,
            target_path=target,
        )

    raise InventoryMigrationError(
        "legacy inventory exists but no single scrubbed document contains every "
        "verified House binding"
    )


__all__ = [
    "HOUSE_INVENTORY_FILENAME",
    "InventoryMigrationError",
    "InventoryMigrationResult",
    "LEGACY_SOURCE_DIRECTORY",
    "migrate_legacy_house_inventory",
]
