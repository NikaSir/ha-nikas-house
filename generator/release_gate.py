from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping

from .validation import load_document, load_schema, validate_document


class ReleaseGateError(ValueError):
    """Raised when release-gate inputs or approvals are invalid."""


@dataclass(frozen=True, slots=True)
class ReleaseChange:
    """One meaning-level change between two render traces."""

    category: str
    kind: str
    key: str
    severity: str
    before: Any
    after: Any

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GateResult:
    """Outcome of applying the semantic release gate."""

    allowed: bool
    changes: tuple[ReleaseChange, ...]
    semantic_diff_sha256: str
    reason: str


def load_validated_render_trace(path: Path, schema_path: Path) -> dict[str, Any]:
    """Load one render trace after JSON-Schema validation."""
    document = load_document(path)
    schema = load_schema(schema_path)
    issues = validate_document(document, schema, path=path)
    if issues:
        raise ReleaseGateError("\n".join(str(issue) for issue in issues))
    if not isinstance(document, dict):
        raise ReleaseGateError(f"render trace root must be an object: {path}")
    return document


def _change(
    category: str,
    kind: str,
    key: str,
    severity: str,
    before: Any,
    after: Any,
) -> ReleaseChange:
    return ReleaseChange(category, kind, key, severity, before, after)


def _index(
    items: list[Mapping[str, Any]],
    field: str,
    context: str,
) -> dict[Any, Mapping[str, Any]]:
    indexed: dict[Any, Mapping[str, Any]] = {}
    for item in items:
        key = item[field]
        if key in indexed:
            raise ReleaseGateError(f"duplicate {field} {key!r} in {context}")
        indexed[key] = item
    return indexed


def _compare_scalar_fields(
    changes: list[ReleaseChange],
    *,
    category: str,
    key: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    fields: Mapping[str, tuple[str, str]],
) -> None:
    for field, (kind, severity) in fields.items():
        old = before.get(field)
        new = after.get(field)
        if old != new:
            changes.append(_change(category, kind, key, severity, old, new))


def _diff_roles(
    changes: list[ReleaseChange],
    *,
    view_id: str,
    instance: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> None:
    old_roles = _index(before["roles"], "role", f"{view_id}.{instance} roles")
    new_roles = _index(after["roles"], "role", f"{view_id}.{instance} roles")
    for role in sorted(old_roles.keys() | new_roles.keys()):
        key = f"{view_id}.{instance}.{role}"
        old = old_roles.get(role)
        new = new_roles.get(role)
        if old is None:
            changes.append(_change("binding", "added", key, "high", None, new))
            continue
        if new is None:
            changes.append(_change("binding", "removed", key, "critical", old, None))
            continue

        _compare_scalar_fields(
            changes,
            category="binding",
            key=key,
            before=old,
            after=new,
            fields={
                "semantic_key": ("semantic_key_changed", "critical"),
                "entity_id": ("rebound", "critical"),
                "domain": ("domain_changed", "critical"),
                "label": ("label_changed", "medium"),
            },
        )
        if old["action"] != new["action"]:
            changes.append(
                _change(
                    "action",
                    "action_changed",
                    key,
                    "critical",
                    old["action"],
                    new["action"],
                )
            )


def _diff_modules(
    changes: list[ReleaseChange],
    *,
    view_id: str,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> None:
    old_modules = _index(before["modules"], "instance", f"{view_id} modules")
    new_modules = _index(after["modules"], "instance", f"{view_id} modules")
    for instance in sorted(old_modules.keys() | new_modules.keys()):
        key = f"{view_id}.{instance}"
        old = old_modules.get(instance)
        new = new_modules.get(instance)
        if old is None:
            changes.append(_change("module", "added", key, "high", None, new))
            continue
        if new is None:
            changes.append(_change("module", "removed", key, "critical", old, None))
            continue

        _compare_scalar_fields(
            changes,
            category="module",
            key=key,
            before=old,
            after=new,
            fields={
                "contract": ("contract_changed", "critical"),
                "order": ("order_changed", "medium"),
                "title": ("title_changed", "medium"),
                "renderer": ("renderer_changed", "critical"),
                "columns": ("columns_changed", "medium"),
            },
        )
        _diff_roles(
            changes,
            view_id=view_id,
            instance=instance,
            before=old,
            after=new,
        )


def _diff_views(
    changes: list[ReleaseChange],
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> None:
    old_views = _index(before["semantics"]["views"], "id", "render trace views")
    new_views = _index(after["semantics"]["views"], "id", "render trace views")
    for view_id in sorted(old_views.keys() | new_views.keys()):
        old = old_views.get(view_id)
        new = new_views.get(view_id)
        if old is None:
            changes.append(_change("view", "added", view_id, "high", None, new))
            continue
        if new is None:
            changes.append(_change("view", "removed", view_id, "critical", old, None))
            continue

        _compare_scalar_fields(
            changes,
            category="view",
            key=view_id,
            before=old,
            after=new,
            fields={
                "title": ("title_changed", "medium"),
                "path": ("path_changed", "critical"),
                "order": ("order_changed", "medium"),
            },
        )
        _diff_modules(changes, view_id=view_id, before=old, after=new)


def _diff_contract_versions(
    changes: list[ReleaseChange],
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> None:
    old_contracts = _index(before["contracts"], "id", "render trace contracts")
    new_contracts = _index(after["contracts"], "id", "render trace contracts")
    for contract_id in sorted(old_contracts.keys() | new_contracts.keys()):
        old = old_contracts.get(contract_id)
        new = new_contracts.get(contract_id)
        if old is None:
            changes.append(_change("contract", "added", contract_id, "high", None, new))
        elif new is None:
            changes.append(_change("contract", "removed", contract_id, "critical", old, None))
        elif old["version"] != new["version"]:
            changes.append(
                _change(
                    "contract",
                    "version_changed",
                    contract_id,
                    "low",
                    old["version"],
                    new["version"],
                )
            )


def diff_render_traces(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> list[ReleaseChange]:
    """Return deterministic meaning-level differences between render traces."""
    changes: list[ReleaseChange] = []

    _compare_scalar_fields(
        changes,
        category="manifest",
        key="manifest",
        before=before["manifest"],
        after=after["manifest"],
        fields={
            "id": ("id_changed", "critical"),
            "version": ("version_changed", "low"),
            "dashboard_path": ("dashboard_path_changed", "critical"),
        },
    )
    _diff_contract_versions(changes, before, after)

    old_snapshots = before["inventory_snapshot_ids"]
    new_snapshots = after["inventory_snapshot_ids"]
    if old_snapshots != new_snapshots:
        changes.append(
            _change(
                "source",
                "inventory_snapshot_changed",
                "inventory_snapshot_ids",
                "medium",
                old_snapshots,
                new_snapshots,
            )
        )

    _diff_views(changes, before, after)

    if before["renderer_engine_sha256"] != after["renderer_engine_sha256"]:
        changes.append(
            _change(
                "renderer",
                "engine_changed",
                "renderer_engine_sha256",
                "high",
                before["renderer_engine_sha256"],
                after["renderer_engine_sha256"],
            )
        )

    render_affecting = any(
        change.category in {"view", "module", "binding", "action"}
        for change in changes
    ) or any(
        change.category == "renderer" and change.kind == "engine_changed"
        for change in changes
    )
    if (
        not render_affecting
        and before["dashboard_sha256"] != after["dashboard_sha256"]
    ):
        changes.append(
            _change(
                "renderer",
                "unclassified_render_drift",
                "dashboard_sha256",
                "critical",
                before["dashboard_sha256"],
                after["dashboard_sha256"],
            )
        )

    return sorted(
        changes,
        key=lambda item: (
            item.category,
            item.key,
            item.kind,
            item.severity,
        ),
    )


def render_diff_payload(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a deterministic machine-readable semantic render diff."""
    changes = diff_render_traces(before, after)
    core = {
        "baseline_dashboard_sha256": before["dashboard_sha256"],
        "candidate_dashboard_sha256": after["dashboard_sha256"],
        "changes": [change.as_dict() for change in changes],
    }
    canonical = json.dumps(
        core,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "api_version": "nikas.home-assistant/render-diff/v1",
        **core,
        "semantic_diff_sha256": hashlib.sha256(canonical).hexdigest(),
    }


def validate_approval(
    approval: Mapping[str, Any],
    *,
    approval_schema: Mapping[str, Any],
    path: Path,
) -> None:
    """Validate a manually reviewed render approval document."""
    issues = validate_document(
        approval,
        dict(approval_schema),
        path=path,
    )
    if issues:
        raise ReleaseGateError("\n".join(str(issue) for issue in issues))


def gate_render_traces(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    *,
    approval: Mapping[str, Any] | None = None,
    approval_schema: Mapping[str, Any] | None = None,
    approval_path: Path | None = None,
) -> GateResult:
    """Block semantic render changes unless an exact approval matches them."""
    payload = render_diff_payload(before, after)
    changes = tuple(diff_render_traces(before, after))
    diff_sha = payload["semantic_diff_sha256"]

    if not changes:
        return GateResult(True, changes, diff_sha, "no semantic changes")

    if approval is None:
        return GateResult(
            False,
            changes,
            diff_sha,
            "semantic changes require an exact review approval",
        )

    if approval_schema is None or approval_path is None:
        raise ReleaseGateError("approval schema and path are required with approval")
    validate_approval(
        approval,
        approval_schema=approval_schema,
        path=approval_path,
    )

    expected = {
        "baseline_dashboard_sha256": before["dashboard_sha256"],
        "candidate_dashboard_sha256": after["dashboard_sha256"],
        "semantic_diff_sha256": diff_sha,
    }
    for field, value in expected.items():
        if approval[field] != value:
            return GateResult(
                False,
                changes,
                diff_sha,
                f"approval {field} does not match current semantic diff",
            )

    return GateResult(
        True,
        changes,
        diff_sha,
        f"approved by {approval['reviewed_by']}",
    )
