"""Deterministic runtime Lovelace renderer for NikaS House."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

SUPPORTED_SUFFIXES = {".json", ".yaml", ".yml"}
SUPPORTED_TOGGLE_DOMAINS = frozenset({"light", "switch", "input_boolean"})


class RuntimeRenderError(ValueError):
    """Raised when runtime sources cannot be rendered safely."""


@dataclass(frozen=True, slots=True)
class GeneratedArtifact:
    """One generated Lovelace dashboard and its trace."""

    manifest_id: str
    output_path: Path
    trace_path: Path
    dashboard_sha256: str
    changed: bool


def _load_document(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        if path.suffix.lower() == ".json":
            return json.load(handle)
        if path.suffix.lower() in {".yaml", ".yml"}:
            return yaml.safe_load(handle)
    raise RuntimeRenderError(f"unsupported document type: {path}")


def _documents(base: Path) -> Iterable[Path]:
    if not base.exists():
        return ()
    return (
        path
        for path in sorted(base.rglob("*"))
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def _load_object(path: Path) -> dict[str, Any]:
    document = _load_document(path)
    if not isinstance(document, dict):
        raise RuntimeRenderError(f"document root must be an object: {path}")
    return document


def _index_contracts(source_root: Path) -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for path in _documents(source_root / "contracts"):
        document = _load_object(path)
        if document.get("kind") != "UIContract":
            raise RuntimeRenderError(f"unexpected contract document kind in {path}")
        contract_id = document.get("metadata", {}).get("id")
        if not isinstance(contract_id, str) or not contract_id:
            raise RuntimeRenderError(f"contract id missing in {path}")
        if contract_id in contracts:
            raise RuntimeRenderError(f"duplicate contract id {contract_id!r}")
        contracts[contract_id] = document
    if not contracts:
        raise RuntimeRenderError("no UI contracts found")
    return contracts


def _index_inventory(
    source_root: Path,
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    bindings: dict[str, dict[str, Any]] = {}
    snapshot_ids: set[str] = set()
    for path in _documents(source_root / "inventory"):
        document = _load_object(path)
        if document.get("kind") != "SemanticInventory":
            raise RuntimeRenderError(f"unexpected inventory document kind in {path}")
        metadata = document.get("metadata", {})
        if metadata.get("scrubbed") is not True:
            raise RuntimeRenderError(f"inventory must be marked scrubbed: {path}")
        snapshot_id = metadata.get("snapshot_id")
        if isinstance(snapshot_id, str) and snapshot_id:
            snapshot_ids.add(snapshot_id)
        raw_bindings = document.get("spec", {}).get("bindings")
        if not isinstance(raw_bindings, dict):
            raise RuntimeRenderError(f"inventory bindings missing in {path}")
        for semantic_key, binding in raw_bindings.items():
            if semantic_key in bindings:
                raise RuntimeRenderError(
                    f"duplicate semantic inventory key {semantic_key!r}"
                )
            if not isinstance(binding, dict) or binding.get("verification") != "verified":
                raise RuntimeRenderError(
                    f"semantic binding {semantic_key!r} is not verified"
                )
            bindings[semantic_key] = binding
    if not bindings:
        raise RuntimeRenderError("semantic inventory is empty")
    return bindings, sorted(snapshot_ids)


def _actions_by_role(contract: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    contract_id = contract["metadata"]["id"]
    spec = contract["spec"]
    roles = spec["roles"]
    role_order = spec["presentation"]["role_order"]
    if set(role_order) != set(roles) or len(role_order) != len(roles):
        raise RuntimeRenderError(
            f"contract {contract_id!r} role_order must contain every role exactly once"
        )

    actions: dict[str, Mapping[str, Any]] = {}
    for action in spec["actions"]:
        role = action["role"]
        if role not in roles:
            raise RuntimeRenderError(
                f"contract {contract_id!r} action references unknown role {role!r}"
            )
        if role in actions:
            raise RuntimeRenderError(
                f"contract {contract_id!r} defines multiple actions for role {role!r}"
            )
        kind = action["kind"]
        if kind == "service":
            raise RuntimeRenderError(
                f"contract {contract_id!r} uses unsupported service action"
            )
        if kind == "navigate":
            target = action.get("target")
            if not isinstance(target, str) or not target.startswith("/"):
                raise RuntimeRenderError(
                    f"contract {contract_id!r} navigation target must be absolute"
                )
        actions[role] = action

    if set(actions) != set(roles):
        missing = ", ".join(sorted(set(roles) - set(actions)))
        raise RuntimeRenderError(
            f"contract {contract_id!r} has no explicit action for: {missing}"
        )
    return actions


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
            raise RuntimeRenderError(
                f"contract {contract_id!r} role {role!r} cannot toggle {domain!r}"
            )
        return {"action": "toggle"}
    raise RuntimeRenderError(
        f"contract {contract_id!r} role {role!r} uses unsupported action {kind!r}"
    )


def _semantic_action(action: Mapping[str, Any]) -> dict[str, Any]:
    result = {"kind": action["kind"]}
    if action["kind"] == "navigate":
        result["target"] = action["target"]
    return result


def _render_manifest(
    manifest: Mapping[str, Any],
    contracts: Mapping[str, Mapping[str, Any]],
    inventory: Mapping[str, Mapping[str, Any]],
    *,
    snapshot_ids: Iterable[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest_id = manifest["metadata"]["id"]
    views = manifest["spec"]["views"]
    if len({view["id"] for view in views}) != len(views):
        raise RuntimeRenderError(f"manifest {manifest_id!r} has duplicate view ids")
    if len({view["path"] for view in views}) != len(views):
        raise RuntimeRenderError(f"manifest {manifest_id!r} has duplicate view paths")
    if len({view["order"] for view in views}) != len(views):
        raise RuntimeRenderError(f"manifest {manifest_id!r} has duplicate view order")

    rendered_views: list[dict[str, Any]] = []
    semantic_views: list[dict[str, Any]] = []
    used_contracts: dict[str, str] = {}
    used_bindings: dict[str, dict[str, str]] = {}

    for view in sorted(views, key=lambda item: item["order"]):
        modules = view["modules"]
        if len({module["order"] for module in modules}) != len(modules):
            raise RuntimeRenderError(
                f"view {view['id']!r} has duplicate module order"
            )
        cards: list[dict[str, Any]] = []
        semantic_modules: list[dict[str, Any]] = []

        for module in sorted(modules, key=lambda item: item["order"]):
            contract_id = module["contract"]
            contract = contracts.get(contract_id)
            if contract is None:
                raise RuntimeRenderError(
                    f"view {view['id']!r} references missing contract {contract_id!r}"
                )
            spec = contract["spec"]
            roles = spec["roles"]
            actions = _actions_by_role(contract)
            module_bindings = module["bindings"]
            unknown_roles = set(module_bindings) - set(roles)
            if unknown_roles:
                raise RuntimeRenderError(
                    f"module {contract_id!r} binds unknown roles: "
                    + ", ".join(sorted(unknown_roles))
                )

            tiles: list[dict[str, Any]] = []
            semantic_roles: list[dict[str, Any]] = []
            instance = module.get("instance") or contract_id
            for role in spec["presentation"]["role_order"]:
                role_spec = roles[role]
                semantic_key = module_bindings.get(role)
                if semantic_key is None:
                    if role_spec["required"]:
                        raise RuntimeRenderError(
                            f"module {contract_id!r} missing required binding {role!r}"
                        )
                    continue
                binding = inventory.get(semantic_key)
                if binding is None:
                    raise RuntimeRenderError(
                        f"module {contract_id!r} references unknown semantic key "
                        f"{semantic_key!r}"
                    )
                entity_id = binding.get("entity_id")
                domain = binding.get("domain")
                if not isinstance(entity_id, str) or not isinstance(domain, str):
                    raise RuntimeRenderError(
                        f"semantic binding {semantic_key!r} is incomplete"
                    )
                if entity_id.partition(".")[0] != domain:
                    raise RuntimeRenderError(
                        f"semantic binding {semantic_key!r} domain mismatch"
                    )
                if domain not in role_spec["allowed_domains"]:
                    raise RuntimeRenderError(
                        f"role {role!r} requires {role_spec['allowed_domains']!r}, "
                        f"got {domain!r}"
                    )
                primary = _lovelace_action(
                    actions[role],
                    domain=domain,
                    contract_id=contract_id,
                    role=role,
                )
                tiles.append(
                    {
                        "type": "tile",
                        "entity": entity_id,
                        "name": role_spec["label"],
                        "tap_action": dict(primary),
                        "hold_action": {"action": "more-info"},
                        "double_tap_action": {"action": "none"},
                        "icon_tap_action": dict(primary),
                        "icon_hold_action": {"action": "more-info"},
                        "icon_double_tap_action": {"action": "none"},
                    }
                )
                trace_key = f"{view['id']}.{instance}.{role}"
                if trace_key in used_bindings:
                    raise RuntimeRenderError(f"duplicate trace key {trace_key!r}")
                used_bindings[trace_key] = {
                    "semantic_key": semantic_key,
                    "entity_id": entity_id,
                }
                semantic_roles.append(
                    {
                        "role": role,
                        "label": role_spec["label"],
                        "semantic_key": semantic_key,
                        "entity_id": entity_id,
                        "domain": domain,
                        "action": _semantic_action(actions[role]),
                    }
                )

            if not tiles:
                raise RuntimeRenderError(f"module {contract_id!r} rendered no roles")
            title = module.get("title") or contract["metadata"]["title"]
            cards.extend(
                [
                    {"type": "heading", "heading": title},
                    {
                        "type": "grid",
                        "columns": spec["presentation"]["columns"],
                        "square": False,
                        "cards": tiles,
                    },
                ]
            )
            used_contracts[contract_id] = contract["metadata"]["version"]
            semantic_modules.append(
                {
                    "instance": instance,
                    "contract": contract_id,
                    "order": module["order"],
                    "title": title,
                    "renderer": spec["presentation"]["renderer"],
                    "columns": spec["presentation"]["columns"],
                    "roles": semantic_roles,
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
    canonical = json.dumps(
        dashboard,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    dashboard_sha256 = hashlib.sha256(canonical).hexdigest()
    trace = {
        "api_version": "nikas.home-assistant/render-trace/v1",
        "manifest": {
            "id": manifest_id,
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
        "renderer_engine_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "dashboard_sha256": dashboard_sha256,
    }
    return dashboard, trace


def _atomic_write(path: Path, text: str) -> bool:
    previous = path.read_text(encoding="utf-8") if path.exists() else None
    if previous == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)
    return True


def render_all_manifests(
    source_root: Path,
    generated_root: Path,
) -> list[GeneratedArtifact]:
    """Render every runtime manifest without applying it to Home Assistant."""
    contracts = _index_contracts(source_root)
    inventory, snapshot_ids = _index_inventory(source_root)
    artifacts: list[GeneratedArtifact] = []

    manifests = list(_documents(source_root / "manifests"))
    if not manifests:
        raise RuntimeRenderError("no panel manifests found")
    seen_ids: set[str] = set()
    for manifest_path in manifests:
        manifest = _load_object(manifest_path)
        if manifest.get("kind") != "PanelManifest":
            raise RuntimeRenderError(f"unexpected manifest kind in {manifest_path}")
        manifest_id = manifest.get("metadata", {}).get("id")
        if not isinstance(manifest_id, str) or not manifest_id:
            raise RuntimeRenderError(f"manifest id missing in {manifest_path}")
        if manifest_id in seen_ids:
            raise RuntimeRenderError(f"duplicate manifest id {manifest_id!r}")
        seen_ids.add(manifest_id)

        dashboard, trace = _render_manifest(
            manifest,
            contracts,
            inventory,
            snapshot_ids=snapshot_ids,
        )
        output_path = generated_root / f"{manifest_id}.yaml"
        trace_path = generated_root / f"{manifest_id}.meta.json"
        yaml_text = yaml.safe_dump(dashboard, allow_unicode=True, sort_keys=False)
        trace_text = json.dumps(trace, ensure_ascii=False, indent=2) + "\n"
        output_changed = _atomic_write(output_path, yaml_text)
        trace_changed = _atomic_write(trace_path, trace_text)
        artifacts.append(
            GeneratedArtifact(
                manifest_id=manifest_id,
                output_path=output_path,
                trace_path=trace_path,
                dashboard_sha256=trace["dashboard_sha256"],
                changed=output_changed or trace_changed,
            )
        )
    return artifacts
