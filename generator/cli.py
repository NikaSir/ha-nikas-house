from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from .release_gate import (
    ReleaseGateError,
    gate_render_traces,
    load_validated_render_trace,
    render_diff_payload,
)
from .render_dispatch import RenderError, render_repository_manifest, write_render_result
from .semantic_diff import diff_inventories, diff_registry_snapshots, render_text
from .snapshot import (
    SnapshotBindingError,
    build_inventory,
    load_validated_snapshot,
    parse_binding,
    validate_snapshot_document,
)
from .validation import load_document, load_schema, validate_document, validate_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ha-contract-ui")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate",
        help="validate contracts, semantic inventory, manifests and snapshots",
    )
    validate.add_argument("repo_root", nargs="?", default=".", type=Path)

    snapshot = subparsers.add_parser("snapshot", help="work with scrubbed HA snapshots")
    snapshot_sub = snapshot.add_subparsers(dest="snapshot_command", required=True)
    snapshot_validate = snapshot_sub.add_parser("validate", help="validate one snapshot")
    snapshot_validate.add_argument("snapshot", type=Path)
    snapshot_validate.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/registry-snapshot.schema.json"),
    )

    inventory = subparsers.add_parser("inventory", help="build verified semantic inventory")
    inventory_sub = inventory.add_subparsers(dest="inventory_command", required=True)
    inventory_build = inventory_sub.add_parser("build")
    inventory_build.add_argument("snapshot", type=Path)
    inventory_build.add_argument("output", type=Path)
    inventory_build.add_argument("--bind", action="append", required=True, dest="bindings")
    inventory_build.add_argument(
        "--snapshot-schema",
        type=Path,
        default=Path("schemas/registry-snapshot.schema.json"),
    )
    inventory_build.add_argument(
        "--inventory-schema",
        type=Path,
        default=Path("schemas/inventory.schema.json"),
    )

    diff = subparsers.add_parser("diff", help="show meaning-level changes")
    diff_sub = diff.add_subparsers(dest="diff_kind", required=True)

    inventory_diff = diff_sub.add_parser("inventory")
    inventory_diff.add_argument("before", type=Path)
    inventory_diff.add_argument("after", type=Path)
    inventory_diff.add_argument("--json", action="store_true", dest="as_json")
    inventory_diff.add_argument("--check", action="store_true")
    inventory_diff.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/inventory.schema.json"),
    )

    snapshot_diff = diff_sub.add_parser("snapshot")
    snapshot_diff.add_argument("before", type=Path)
    snapshot_diff.add_argument("after", type=Path)
    snapshot_diff.add_argument("--json", action="store_true", dest="as_json")
    snapshot_diff.add_argument("--check", action="store_true")
    snapshot_diff.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/registry-snapshot.schema.json"),
    )

    render_diff = diff_sub.add_parser("render")
    render_diff.add_argument("before", type=Path)
    render_diff.add_argument("after", type=Path)
    render_diff.add_argument("--json", action="store_true", dest="as_json")
    render_diff.add_argument("--check", action="store_true")
    render_diff.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/render-trace.schema.json"),
    )

    render = subparsers.add_parser(
        "render",
        help="render deterministic Lovelace YAML from one panel manifest",
    )
    render.add_argument("manifest", type=Path)
    render.add_argument("output", type=Path)
    render.add_argument("--repo-root", type=Path, default=Path("."))
    render.add_argument("--metadata", type=Path)

    gate = subparsers.add_parser(
        "gate",
        help="apply fail-closed release gates",
    )
    gate_sub = gate.add_subparsers(dest="gate_kind", required=True)
    render_gate = gate_sub.add_parser("render")
    render_gate.add_argument("before", type=Path)
    render_gate.add_argument("after", type=Path)
    render_gate.add_argument("--approval", type=Path)
    render_gate.add_argument(
        "--trace-schema",
        type=Path,
        default=Path("schemas/render-trace.schema.json"),
    )
    render_gate.add_argument(
        "--approval-schema",
        type=Path,
        default=Path("schemas/render-approval.schema.json"),
    )

    return parser


def _write_document(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    elif path.suffix.lower() in {".yaml", ".yml"}:
        text = yaml.safe_dump(document, allow_unicode=True, sort_keys=False)
    else:
        raise SnapshotBindingError("inventory output must end in .json, .yaml or .yml")
    path.write_text(text, encoding="utf-8")


def _render_release_changes(changes: list[dict]) -> str:
    if not changes:
        return "No semantic render changes."
    lines = [f"{len(changes)} semantic render change(s):"]
    for change in changes:
        lines.append(
            f"- [{change['severity']}] {change['category']}:"
            f"{change['kind']} {change['key']}"
        )
    return "\n".join(lines)


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "validate":
        issues = validate_repository(args.repo_root)
        if issues:
            for issue in issues:
                print(issue)
            print(f"Validation failed: {len(issues)} issue(s).")
            return 1
        print("NikaS House inputs are valid.")
        return 0

    if args.command == "snapshot" and args.snapshot_command == "validate":
        document = load_document(args.snapshot)
        schema = load_schema(args.schema)
        issues = validate_snapshot_document(document, schema, path=args.snapshot)
        if issues:
            for issue in issues:
                print(issue)
            return 1
        print("Registry snapshot is valid.")
        return 0

    if args.command == "inventory" and args.inventory_command == "build":
        try:
            snapshot = load_validated_snapshot(args.snapshot, args.snapshot_schema)
            inventory = build_inventory(
                snapshot,
                [parse_binding(value) for value in args.bindings],
            )
            inventory_schema = load_schema(args.inventory_schema)
            issues = validate_document(inventory, inventory_schema, path=args.output)
            if issues:
                for issue in issues:
                    print(issue)
                return 1
            _write_document(args.output, inventory)
        except (OSError, SnapshotBindingError, ValueError) as exc:
            print(exc)
            return 1
        print(f"Verified semantic inventory written to {args.output}.")
        return 0

    if args.command == "diff":
        if args.diff_kind == "render":
            try:
                before = load_validated_render_trace(args.before, args.schema)
                after = load_validated_render_trace(args.after, args.schema)
                payload = render_diff_payload(before, after)
            except (OSError, ReleaseGateError, ValueError) as exc:
                print(exc)
                return 1
            if args.as_json:
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                print(_render_release_changes(payload["changes"]))
                print(f"Semantic diff SHA-256: {payload['semantic_diff_sha256']}")
            return 2 if args.check and payload["changes"] else 0

        before = load_document(args.before)
        after = load_document(args.after)
        schema = load_schema(args.schema)
        if args.diff_kind == "inventory":
            issues = validate_document(before, schema, path=args.before) + validate_document(
                after, schema, path=args.after
            )
            changes = diff_inventories(before, after) if not issues else []
        else:
            issues = validate_snapshot_document(
                before, schema, path=args.before
            ) + validate_snapshot_document(after, schema, path=args.after)
            changes = diff_registry_snapshots(before, after) if not issues else []
        if issues:
            for issue in issues:
                print(issue)
            return 1
        if args.as_json:
            print(
                json.dumps(
                    [change.as_dict() for change in changes],
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            print(render_text(changes))
        return 2 if args.check and changes else 0

    if args.command == "render":
        repo_root = args.repo_root.resolve()
        manifest_path = args.manifest
        if not manifest_path.is_absolute():
            manifest_path = repo_root / manifest_path
        try:
            result = render_repository_manifest(repo_root, manifest_path)
            output_path, metadata_path = write_render_result(
                args.output,
                result,
                metadata_path=args.metadata,
            )
        except (
            OSError,
            RenderError,
            ValueError,
            json.JSONDecodeError,
            yaml.YAMLError,
        ) as exc:
            print(exc)
            return 1
        print(f"Lovelace YAML written to {output_path}.")
        print(f"Render trace written to {metadata_path}.")
        return 0

    if args.command == "gate" and args.gate_kind == "render":
        try:
            before = load_validated_render_trace(args.before, args.trace_schema)
            after = load_validated_render_trace(args.after, args.trace_schema)
            approval = load_document(args.approval) if args.approval else None
            approval_schema = (
                load_schema(args.approval_schema) if args.approval else None
            )
            result = gate_render_traces(
                before,
                after,
                approval=approval,
                approval_schema=approval_schema,
                approval_path=args.approval,
            )
        except (
            OSError,
            ReleaseGateError,
            ValueError,
            json.JSONDecodeError,
            yaml.YAMLError,
        ) as exc:
            print(exc)
            return 1

        print(_render_release_changes([change.as_dict() for change in result.changes]))
        print(f"Semantic diff SHA-256: {result.semantic_diff_sha256}")
        print(f"Gate: {'ALLOW' if result.allowed else 'BLOCK'} — {result.reason}")
        return 0 if result.allowed else 3

    raise AssertionError("unhandled command")
