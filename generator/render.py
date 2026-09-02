from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from .validation import SUPPORTED_SUFFIXES, load_document, load_schema, validate_document

SUPPORTED_TOGGLE_DOMAINS = frozenset({"light", "switch", "input_boolean"})


class RenderError(ValueError):
    """Raised when validated inputs cannot be rendered safely."""


@dataclass(frozen=True, slots=True)
class RenderResult:
    """Deterministic Lovelace output plus its trace metadata."""

    dashboard: dict[str, Any]
    trace: dict[str, Any]


def _renderer_engine_sha256() -> str:
    """Return a deterministic fingerprint of the rendering engine source."""
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _documents(base: Path) -> Iterable[Path]:
    if not base.exists():
        return ()
    return (
        path
        for path in sorted(base.rglob("*"))
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def _load_valid_documents(
    directory: Path,
    schema: Mapping[str, Any],
    *,
    forbid_bindings: bool = False,
) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    issues = []
    for path in _documents(directory):
        document = load_document(path)
        issues.extend(
            validate_document(
                document,
                dict(schema),
                path=path,
                forbid_bindings=forbid_bindings,
            )
        )
        if isinstance(document, dict):
            documents.append(document)
    if issues:
        raise RenderError("\n".join(str(issue) for issue in issues))
    return documents


def _index_contracts(
    documents: Iterable[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    contracts: dict[str, Mapping[str, Any]] = {}
    for document in documents:
        contract_id = document["metadata"]["id"]
        if contract_id in contracts:
            raise RenderError(f"duplicate contract id {contract_id!r}")
        contracts[contract_id] = document
    return contracts


def _index_bindings(
    documents: Iterable[Mapping[str, Any]],
) -> tuple[dict[str, Mapping[str, Any]], list[str]]:
    bindings: dict[str, Mapping[str, Any]] = {}
    snapshot_ids: set[str] = set()
    for document in documents:
        snapshot_id = document.get("metadata", {}).get("snapshot_id")
        if snapshot_id:
            snapshot_ids.add(snapshot_id)
        for semantic_key, binding in document["spec"]["bindings"].items():
            if semantic_key in bindings:
                raise RenderError(f"duplicate semantic inventory key {semantic_key!r}")
            bindings[semantic_key] = binding
    return bindings, sorted(snapshot_ids)


def _assert_unique(
    items: Iterable[Mapping[str, Any]],
    field: str,
    context: str,
) -> None:
    seen: set[Any] = set()
    for item in items:
        value = item[field]
        if value in seen:
            raise RenderError(f"duplicate {field} {value!r} in {context}")
        seen.add(value)


def _validate_contract_semantics(
    contract: Mapping[str, Any],
) -> dict[str, Mapping[str, Any]]:
    contract_id = contract["metadata"]["id"]
    spec = contract["spec"]
    roles = spec["roles"]
    role_names = set(roles)
    role_order = spec["presentation"]["role_order"]

    if set(role_order) != role_names or len(role_order) != len(role_names):
        raise RenderError(
            f"contract {contract_id!r} presentation.role_order must contain "
            "every role exactly once"
        )

    actions_by_role: dict[str, Mapping[str, Any]] = {}
    action_ids: set[str] = set()
    for action in spec["actions"]:
        if action["id"] in action_ids:
            raise RenderError(
                f"contract {contract_id!r} has duplicate action id {action['id']!r}"
            )
        action_ids.add(action["id"])

        role = action["role"]
        if role not in roles:
            raise RenderError(
                f"contract {contract_id!r} action {action['id']!r} "
                f"references unknown role {role!r}"
            )
        if role in actions_by_role:
            raise RenderError(
                f"contract {contract_id!r} defines more than one action "
                f"for role {role!r}"
            )
        if action["kind"] == "service":
            raise RenderError(
                f"contract {contract_id!r} role {role!r} uses unsupported "
                "service action in tiles_v1"
            )
        if action["kind"] == "navigate":
            target = action.get("target")
            if not isinstance(target, str) or not target.startswith("/"):
                raise RenderError(
                    f"contract {contract_id!r} navigate action for {role!r} "
                    "requires absolute target"
                )
        elif "target" in action:
            raise RenderError(
                f"contract {contract_id!r} action {action['id']!r} "
                "has target outside navigate action"
            )
        actions_by_role[role] = action

    if set(actions_by_role) != role_names:
        missing = ", ".join(sorted(role_names - set(actions_by_role)))
        extra = ", ".join(sorted(set(actions_by_role) - role_names))
        detail = f"missing actions: {missing}" if missing else f"extra actions: {extra}"
        raise RenderError(
            f"contract {contract_id!r} must define exactly one explicit "
            f"action per role ({detail})"
        )

    for state_name, state_class in spec["states"].items():
        for rule in state_class["rules"]:
            unknown = set(rule.get("roles", ())) - role_names
            if unknown:
                raise RenderError(
                    f"contract {contract_id!r} state {state_name!r} rule "
                    f"{rule['id']!r} references unknown roles: "
                    f"{', '.join(sorted(unknown))}"
                )

    return actions_by_role


def _lovelace_action(
    action: Mapping[str, Any],
    *,
    domain: str,
    contract_id: str,
    role: str,
) -> dict[str, Any]:
    kind = action["kind"]
    if kind == "none":
        return {"action": "none"}
    if kind == "more_info":
        return {"action": "more-info"}
    if kind == "navigate":
        return {"action": "navigate", "navigation_path": action["target"]}
    if kind == "toggle":
        if domain not in SUPPORTED_TOGGLE_DOMAINS:
            raise RenderError(
                f"contract {contract_id!r} role {role!r} requests toggle "
                f"for unsupported domain {domain!r}"
            )
        return {"action": "toggle"}
    raise RenderError(
        f"contract {contract_id!r} role {role!r} uses unsupported action {kind!r}"
    )


def _semantic_action(action: Mapping[str, Any]) -> dict[str, Any]:
    rendered = {"kind": action["kind"]}
    if action["kind"] == "navigate":
        rendered["target"] = action["target"]
    return rendered


def _render_module(
    module: Mapping[str, Any],
    contract: Mapping[str, Any],
    inventory: Mapping[str, Mapping[str, Any]],
) -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, str]],
    list[dict[str, Any]],
]:
    contract_id = contract["metadata"]["id"]
    spec = contract["spec"]
    roles = spec["roles"]
    actions = _validate_contract_semantics(contract)
    bindings = module["bindings"]

    unknown_roles = set(bindings) - set(roles)
    if unknown_roles:
        raise RenderError(
            f"module {contract_id!r} binds unknown roles: "
            f"{', '.join(sorted(unknown_roles))}"
        )

    used: dict[str, dict[str, str]] = {}
    role_semantics: list[dict[str, Any]] = []
    tiles: list[dict[str, Any]] = []
    for role in spec["presentation"]["role_order"]:
        role_spec = roles[role]
        semantic_key = bindings.get(role)
        if semantic_key is None:
            if role_spec["required"]:
                raise RenderError(
                    f"module {contract_id!r} is missing required role binding {role!r}"
                )
            continue

        binding = inventory.get(semantic_key)
        if binding is None:
            raise RenderError(
                f"module {contract_id!r} role {role!r} references unknown "
                f"semantic key {semantic_key!r}"
            )

        domain = binding["domain"]
        if domain not in role_spec["allowed_domains"]:
            raise RenderError(
                f"module {contract_id!r} role {role!r} requires domains "
                f"{role_spec['allowed_domains']!r}, got {domain!r}"
            )

        primary_action = _lovelace_action(
            actions[role],
            domain=domain,
            contract_id=contract_id,
            role=role,
        )
        tile = {
            "type": "tile",
            "entity": binding["entity_id"],
            "name": role_spec["label"],
            "tap_action": dict(primary_action),
            "hold_action": {"action": "more-info"},
            "double_tap_action": {"action": "none"},
            "icon_tap_action": dict(primary_action),
            "icon_hold_action": {"action": "more-info"},
            "icon_double_tap_action": {"action": "none"},
        }
        tiles.append(tile)
        used[role] = {
            "semantic_key": semantic_key,
            "entity_id": binding["entity_id"],
        }
        role_semantics.append(
            {
                "role": role,
                "label": role_spec["label"],
                "semantic_key": semantic_key,
                "entity_id": binding["entity_id"],
                "domain": domain,
                "action": _semantic_action(actions[role]),
            }
        )

    if not tiles:
        raise RenderError(f"module {contract_id!r} rendered no roles")

    title = module.get("title") or contract["metadata"]["title"]
    cards = [
        {"type": "heading", "heading": title},
        {
            "type": "grid",
            "columns": spec["presentation"]["columns"],
            "square": False,
            "cards": tiles,
        },
    ]
    return cards, used, role_semantics


def render_dashboard(
    manifest: Mapping[str, Any],
    contracts: Mapping[str, Mapping[str, Any]],
    inventory: Mapping[str, Mapping[str, Any]],
    *,
    snapshot_ids: Iterable[str] = (),
) -> RenderResult:
    """Render one validated panel manifest into deterministic Lovelace data."""
    views = manifest["spec"]["views"]
    _assert_unique(views, "id", "manifest views")
    _assert_unique(views, "path", "manifest views")
    _assert_unique(views, "order", "manifest views")

    rendered_views: list[dict[str, Any]] = []
    semantic_views: list[dict[str, Any]] = []
    used_contracts: dict[str, str] = {}
    used_bindings: dict[str, dict[str, str]] = {}

    for view in sorted(views, key=lambda item: item["order"]):
        modules = view["modules"]
        _assert_unique(modules, "order", f"view {view['id']!r} modules")
        cards: list[dict[str, Any]] = []
        semantic_modules: list[dict[str, Any]] = []

        for module in sorted(modules, key=lambda item: item["order"]):
            contract_id = module["contract"]
            contract = contracts.get(contract_id)
            if contract is None:
                raise RenderError(
                    f"view {view['id']!r} references missing contract {contract_id!r}"
                )

            module_cards, module_used, role_semantics = _render_module(
                module,
                contract,
                inventory,
            )
            cards.extend(module_cards)
            used_contracts[contract_id] = contract["metadata"]["version"]

            instance = module.get("instance") or contract_id
            for role, used in module_used.items():
                trace_key = f"{view['id']}.{instance}.{role}"
                if trace_key in used_bindings:
                    raise RenderError(
                        f"duplicate rendered binding trace key {trace_key!r}"
                    )
                used_bindings[trace_key] = used

            presentation = contract["spec"]["presentation"]
            semantic_modules.append(
                {
                    "instance": instance,
                    "contract": contract_id,
                    "order": module["order"],
                    "title": module.get("title") or contract["metadata"]["title"],
                    "renderer": presentation["renderer"],
                    "columns": presentation["columns"],
                    "roles": role_semantics,
                }
            )

        rendered_views.append(
            {
                "title": view["title"],
                "path": view["path"],
                "type": "masonry",
                "cards": cards,
            }
        )
        semantic_views.append(
            {
                "id": view["id"],
                "title": view["title"],
                "path": view["path"],
                "order": view["order"],
                "modules": semantic_modules,
            }
        )

    dashboard = {"views": rendered_views}
    dashboard_bytes = json.dumps(
        dashboard,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    trace = {
        "api_version": "nikas.home-assistant/render-trace/v1",
        "manifest": {
            "id": manifest["metadata"]["id"],
            "version": manifest["metadata"]["version"],
            "dashboard_path": manifest["spec"]["dashboard_path"],
        },
        "contracts": [
            {"id": contract_id, "version": version}
            for contract_id, version in sorted(used_contracts.items())
        ],
        "inventory_snapshot_ids": sorted(set(snapshot_ids)),
        "bindings": dict(sorted(used_bindings.items())),
        "semantics": {"views": semantic_views},
        "renderer_engine_sha256": _renderer_engine_sha256(),
        "dashboard_sha256": hashlib.sha256(dashboard_bytes).hexdigest(),
    }
    return RenderResult(dashboard=dashboard, trace=trace)


def render_repository_manifest(repo_root: Path, manifest_path: Path) -> RenderResult:
    """Load, validate, bind and render one manifest from a repository tree."""
    repo_root = repo_root.resolve()
    manifest_path = manifest_path.resolve()
    schema_root = repo_root / "schemas"

    contract_schema = load_schema(schema_root / "contract.schema.json")
    inventory_schema = load_schema(schema_root / "inventory.schema.json")
    manifest_schema = load_schema(schema_root / "manifest.schema.json")

    manifest = load_document(manifest_path)
    manifest_issues = validate_document(
        manifest,
        manifest_schema,
        path=manifest_path,
        forbid_bindings=True,
    )
    if manifest_issues:
        raise RenderError("\n".join(str(issue) for issue in manifest_issues))

    contracts = _index_contracts(
        _load_valid_documents(
            repo_root / "contracts",
            contract_schema,
            forbid_bindings=True,
        )
    )
    inventory_documents = _load_valid_documents(
        repo_root / "inventory",
        inventory_schema,
    )
    inventory, snapshot_ids = _index_bindings(inventory_documents)
    if not inventory:
        raise RenderError("semantic inventory is empty")

    return render_dashboard(
        manifest,
        contracts,
        inventory,
        snapshot_ids=snapshot_ids,
    )


def write_render_result(
    output_path: Path,
    result: RenderResult,
    *,
    metadata_path: Path | None = None,
) -> tuple[Path, Path]:
    """Atomically write deterministic YAML plus render-trace metadata."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix.lower() not in {".yaml", ".yml"}:
        raise RenderError("Lovelace output must end in .yaml or .yml")

    metadata_path = metadata_path or output_path.with_suffix(".meta.json")
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    yaml_text = yaml.safe_dump(
        result.dashboard,
        allow_unicode=True,
        sort_keys=False,
    )
    meta_text = json.dumps(
        result.trace,
        ensure_ascii=False,
        indent=2,
        sort_keys=False,
    ) + "\n"

    yaml_temp = output_path.with_name(f".{output_path.name}.tmp")
    meta_temp = metadata_path.with_name(f".{metadata_path.name}.tmp")
    yaml_temp.write_text(yaml_text, encoding="utf-8")
    meta_temp.write_text(meta_text, encoding="utf-8")
    os.replace(yaml_temp, output_path)
    os.replace(meta_temp, metadata_path)
    return output_path, metadata_path
