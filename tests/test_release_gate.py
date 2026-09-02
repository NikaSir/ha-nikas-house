from __future__ import annotations

import copy
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from generator.release_gate import (
    diff_render_traces,
    gate_render_traces,
    render_diff_payload,
)
from generator.render import render_dashboard

ROOT = Path(__file__).parents[1]


def _contract() -> dict:
    return {
        "api_version": "nikas.home-assistant/ui-contract/v1",
        "kind": "UIContract",
        "metadata": {"id": "access", "title": "Access", "version": "1.0"},
        "spec": {
            "roles": {
                "contact": {
                    "label": "Door",
                    "description": "Door contact",
                    "required": True,
                    "allowed_domains": ["binary_sensor"],
                },
                "light": {
                    "label": "Light",
                    "description": "Local light",
                    "required": False,
                    "allowed_domains": ["light"],
                },
            },
            "states": {
                "normal": {"description": "Normal", "rules": []},
                "event": {"description": "Event", "rules": []},
                "unreliable": {"description": "Unreliable", "rules": []},
            },
            "actions": [
                {
                    "id": "contact_info",
                    "kind": "more_info",
                    "description": "Open details",
                    "role": "contact",
                },
                {
                    "id": "light_toggle",
                    "kind": "toggle",
                    "description": "Toggle light",
                    "role": "light",
                },
            ],
            "presentation": {
                "renderer": "tiles_v1",
                "columns": 2,
                "role_order": ["contact", "light"],
            },
            "safety": {
                "unknown_is_unreliable": True,
                "unavailable_is_unreliable": True,
                "invent_entity_ids": False,
            },
        },
    }


def _manifest() -> dict:
    return {
        "api_version": "nikas.home-assistant/panel-manifest/v1",
        "kind": "PanelManifest",
        "metadata": {"id": "house", "title": "House", "version": "1.0"},
        "spec": {
            "dashboard_path": "/dashboard-house",
            "views": [
                {
                    "id": "home",
                    "title": "Home",
                    "path": "home",
                    "order": 0,
                    "modules": [
                        {
                            "contract": "access",
                            "instance": "garden",
                            "order": 0,
                            "bindings": {
                                "contact": "access.garden.contact",
                                "light": "access.garden.light",
                            },
                        }
                    ],
                }
            ],
        },
    }


def _inventory() -> dict:
    return {
        "access.garden.contact": {
            "entity_id": "binary_sensor.garden_door",
            "domain": "binary_sensor",
            "verification": "verified",
        },
        "access.garden.light": {
            "entity_id": "light.garden",
            "domain": "light",
            "verification": "verified",
        },
    }


def _trace() -> dict:
    return render_dashboard(
        _manifest(),
        {"access": _contract()},
        _inventory(),
        snapshot_ids=["sha256:synthetic"],
    ).trace


def test_render_trace_contains_reviewable_semantics() -> None:
    trace = _trace()
    module = trace["semantics"]["views"][0]["modules"][0]
    light = module["roles"][1]

    assert module["renderer"] == "tiles_v1"
    assert module["columns"] == 2
    assert light["semantic_key"] == "access.garden.light"
    assert light["action"] == {"kind": "toggle"}
    assert len(trace["renderer_engine_sha256"]) == 64


def test_render_diff_classifies_rebinding_and_action_change() -> None:
    before = _trace()
    inventory = _inventory()
    inventory["access.garden.light"] = {
        "entity_id": "light.garden_new",
        "domain": "light",
        "verification": "verified",
    }
    contract = _contract()
    contract["spec"]["actions"][1] = {
        "id": "light_none",
        "kind": "none",
        "description": "Disable primary action",
        "role": "light",
    }
    after = render_dashboard(
        _manifest(),
        {"access": contract},
        inventory,
        snapshot_ids=["sha256:synthetic"],
    ).trace

    changes = diff_render_traces(before, after)
    summary = {(change.category, change.kind, change.key) for change in changes}
    assert ("binding", "rebound", "home.garden.light") in summary
    assert ("action", "action_changed", "home.garden.light") in summary


def test_view_path_and_module_layout_changes_are_classified() -> None:
    before = _trace()
    manifest = _manifest()
    manifest["spec"]["views"][0]["path"] = "overview"
    contract = _contract()
    contract["spec"]["presentation"]["columns"] = 1
    after = render_dashboard(
        manifest,
        {"access": contract},
        _inventory(),
        snapshot_ids=["sha256:synthetic"],
    ).trace

    summary = {(change.category, change.kind) for change in diff_render_traces(before, after)}
    assert ("view", "path_changed") in summary
    assert ("module", "columns_changed") in summary


def test_unclassified_dashboard_drift_is_critical() -> None:
    before = _trace()
    after = copy.deepcopy(before)
    after["dashboard_sha256"] = "0" * 64

    changes = diff_render_traces(before, after)
    assert len(changes) == 1
    assert changes[0].kind == "unclassified_render_drift"
    assert changes[0].severity == "critical"


def test_renderer_engine_change_is_explicit_release_event() -> None:
    before = _trace()
    after = copy.deepcopy(before)
    after["renderer_engine_sha256"] = "f" * 64

    changes = diff_render_traces(before, after)
    assert any(
        change.category == "renderer" and change.kind == "engine_changed"
        for change in changes
    )


def test_gate_blocks_without_approval_and_accepts_exact_approval() -> None:
    before = _trace()
    after = copy.deepcopy(before)
    after["manifest"]["version"] = "1.1"

    blocked = gate_render_traces(before, after)
    assert blocked.allowed is False

    approval = {
        "api_version": "nikas.home-assistant/render-approval/v1",
        "baseline_dashboard_sha256": before["dashboard_sha256"],
        "candidate_dashboard_sha256": after["dashboard_sha256"],
        "semantic_diff_sha256": blocked.semantic_diff_sha256,
        "reviewed_by": "synthetic-reviewer",
        "rationale": "Reviewed the intended manifest version change.",
    }
    approval_schema = json.loads(
        (ROOT / "schemas" / "render-approval.schema.json").read_text(encoding="utf-8")
    )

    allowed = gate_render_traces(
        before,
        after,
        approval=approval,
        approval_schema=approval_schema,
        approval_path=Path("approval.json"),
    )
    assert allowed.allowed is True
    assert "synthetic-reviewer" in allowed.reason

    approval["semantic_diff_sha256"] = "0" * 64
    stale = gate_render_traces(
        before,
        after,
        approval=approval,
        approval_schema=approval_schema,
        approval_path=Path("approval.json"),
    )
    assert stale.allowed is False
    assert "does not match" in stale.reason


def test_render_diff_and_approval_schemas_cover_machine_outputs() -> None:
    before = _trace()
    after = copy.deepcopy(before)
    after["manifest"]["version"] = "1.1"
    payload = render_diff_payload(before, after)

    diff_schema = json.loads(
        (ROOT / "schemas" / "render-diff.schema.json").read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(diff_schema).iter_errors(payload)) == []

    trace_schema = json.loads(
        (ROOT / "schemas" / "render-trace.schema.json").read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(trace_schema).iter_errors(before)) == []
