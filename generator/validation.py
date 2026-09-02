from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml
from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_BY_DIRECTORY = {
    "contracts": "contract.schema.json",
    "inventory": "inventory.schema.json",
    "manifests": "manifest.schema.json",
    "navigation": "navigation.schema.json",
    "snapshots": "registry-snapshot.schema.json",
}

FORBIDDEN_BINDING_KEYS = {"entity_id", "device_id", "area_id"}
BINDING_FREE_DIRECTORIES = {"contracts", "manifests", "navigation"}
SUPPORTED_SUFFIXES = {".json", ".yaml", ".yml"}


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    path: Path
    location: str
    message: str

    def __str__(self) -> str:
        prefix = f"{self.path}:{self.location}" if self.location else str(self.path)
        return f"{prefix}: {self.message}"


def load_document(path: Path) -> Any:
    suffix = path.suffix.lower()
    with path.open("r", encoding="utf-8") as handle:
        if suffix == ".json":
            return json.load(handle)
        if suffix in {".yaml", ".yml"}:
            return yaml.safe_load(handle)
    raise ValueError(f"Unsupported document type: {path}")


def load_schema(path: Path) -> dict[str, Any]:
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


def validate_document(
    document: Any,
    schema: dict[str, Any],
    *,
    path: Path,
    forbid_bindings: bool = False,
) -> list[ValidationIssue]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    issues = [
        ValidationIssue(path, _location(error.absolute_path), error.message)
        for error in sorted(
            validator.iter_errors(document),
            key=lambda item: list(item.absolute_path),
        )
    ]

    if forbid_bindings:
        for key_path, key in _find_forbidden_keys(document):
            issues.append(
                ValidationIssue(
                    path,
                    _location(key_path),
                    (
                        f"concrete Home Assistant binding key {key!r} is forbidden "
                        "here; bind it in inventory"
                    ),
                )
            )

    return issues


def discover_documents(repo_root: Path) -> Iterable[tuple[str, Path]]:
    for directory in SCHEMA_BY_DIRECTORY:
        base = repo_root / directory
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES:
                yield directory, path


def validate_repository(repo_root: Path) -> list[ValidationIssue]:
    repo_root = repo_root.resolve()
    schema_root = repo_root / "schemas"
    schemas = {
        directory: load_schema(schema_root / schema_name)
        for directory, schema_name in SCHEMA_BY_DIRECTORY.items()
    }

    issues: list[ValidationIssue] = []
    for directory, path in discover_documents(repo_root):
        try:
            document = load_document(path)
        except (json.JSONDecodeError, yaml.YAMLError, UnicodeDecodeError, OSError) as exc:
            issues.append(ValidationIssue(path, "$", f"cannot parse document: {exc}"))
            continue

        issues.extend(
            validate_document(
                document,
                schemas[directory],
                path=path,
                forbid_bindings=directory in BINDING_FREE_DIRECTORIES,
            )
        )

    return sorted(
        issues,
        key=lambda item: (str(item.path), item.location, item.message),
    )
