"""Validate NikaS House source documents."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from .const import SOURCE_KINDS

SCHEMA_BY_DIRECTORY = {
    "contracts": "contract.schema.json",
    "inventory": "inventory.schema.json",
    "manifests": "manifest.schema.json",
    "navigation": "navigation.schema.json",
}

FORBIDDEN_BINDING_KEYS = {"entity_id", "device_id", "area_id"}
BINDING_FREE_DIRECTORIES = {"contracts", "manifests", "navigation"}
SUPPORTED_SUFFIXES = {".json", ".yaml", ".yml"}

SourceStatus = Literal["missing", "empty", "incomplete", "valid", "invalid"]


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One validation issue safe to expose as an entity attribute."""

    path: str
    location: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return a serializable representation."""
        return {
            "path": self.path,
            "location": self.location,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class ValidationSnapshot:
    """Validation result for the complete source tree."""

    status: SourceStatus
    counts: dict[str, int]
    issues: tuple[ValidationIssue, ...]

    @property
    def document_count(self) -> int:
        """Return the total number of source documents."""
        return sum(self.counts.values())


def load_document(path: Path) -> Any:
    """Load one JSON or YAML document."""
    suffix = path.suffix.lower()
    with path.open("r", encoding="utf-8") as handle:
        if suffix == ".json":
            return json.load(handle)
        if suffix in {".yaml", ".yml"}:
            return yaml.safe_load(handle)
    raise ValueError(f"Unsupported document type: {path}")


def load_schema(path: Path) -> dict[str, Any]:
    """Load and self-check one bundled JSON Schema."""
    data = load_document(path)
    if not isinstance(data, dict):
        raise ValueError(f"Schema root must be an object: {path}")
    Draft202012Validator.check_schema(data)
    return data


def _location(parts: Iterable[Any]) -> str:
    rendered = "$"
    for part in parts:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            rendered += f".{part}"
    return rendered


def _find_forbidden_keys(
    value: Any,
    path: tuple[Any, ...] = (),
) -> Iterable[tuple[tuple[Any, ...], str]]:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_BINDING_KEYS:
                yield path + (key,), key
            yield from _find_forbidden_keys(child, path + (key,))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _find_forbidden_keys(child, path + (index,))


def _validate_document(
    document: Any,
    schema: dict[str, Any],
    *,
    path: Path,
    source_root: Path,
    forbid_bindings: bool,
) -> list[ValidationIssue]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    relative_path = path.relative_to(source_root).as_posix()
    issues = [
        ValidationIssue(
            relative_path,
            _location(error.absolute_path),
            error.message,
        )
        for error in sorted(
            validator.iter_errors(document),
            key=lambda item: _location(item.absolute_path),
        )
    ]

    if forbid_bindings:
        for key_path, key in _find_forbidden_keys(document):
            issues.append(
                ValidationIssue(
                    relative_path,
                    _location(key_path),
                    (
                        f"concrete Home Assistant binding key {key!r} is forbidden "
                        "here; bind it in inventory"
                    ),
                )
            )

    return issues


def _discover_documents(source_root: Path) -> Iterable[tuple[str, Path]]:
    for directory in SOURCE_KINDS:
        base = source_root / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                yield directory, path


def validate_source_tree(source_root: Path, schema_root: Path) -> ValidationSnapshot:
    """Validate a Home Assistant NikaS House source directory."""
    counts = {directory: 0 for directory in SOURCE_KINDS}

    if not source_root.exists():
        return ValidationSnapshot("missing", counts, ())

    schemas = {
        directory: load_schema(schema_root / schema_name)
        for directory, schema_name in SCHEMA_BY_DIRECTORY.items()
    }

    issues: list[ValidationIssue] = []
    for directory, path in _discover_documents(source_root):
        counts[directory] += 1
        try:
            document = load_document(path)
        except (
            json.JSONDecodeError,
            yaml.YAMLError,
            UnicodeDecodeError,
            OSError,
            ValueError,
        ) as exc:
            issues.append(
                ValidationIssue(
                    path.relative_to(source_root).as_posix(),
                    "$",
                    f"cannot parse document: {exc}",
                )
            )
            continue

        issues.extend(
            _validate_document(
                document,
                schemas[directory],
                path=path,
                source_root=source_root,
                forbid_bindings=directory in BINDING_FREE_DIRECTORIES,
            )
        )

    ordered_issues = tuple(
        sorted(issues, key=lambda item: (item.path, item.location, item.message))
    )
    document_count = sum(counts.values())

    if ordered_issues:
        status: SourceStatus = "invalid"
    elif document_count == 0:
        status = "empty"
    elif any(counts[directory] == 0 for directory in SOURCE_KINDS):
        status = "incomplete"
    else:
        status = "valid"

    return ValidationSnapshot(status, counts, ordered_issues)
