from __future__ import annotations

import json
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

from generator.render import RenderError, render_dashboard, write_render_result


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


def _bindings() -> dict:
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


def _render():
    return render_dashboard(
        _manifest(),
        {"access": _contract()},
        _bindings(),
        snapshot_ids=["sha256:test"],
    )


def test_tiles_have_no_implicit_interactive_actions() -> None:
    result = _render()
    contact, light = result.dashboard["views"][0]["cards"][1]["cards"]

    assert contact["tap_action"] == {"action": "more-info"}
    assert contact["icon_tap_action"] == {"action": "more-info"}
    assert light["tap_action"] == {"action": "toggle"}
    assert light["icon_tap_action"] == {"action": "toggle"}

    for tile in (contact, light):
        assert tile["hold_action"] == {"action": "more-info"}
        assert tile["icon_hold_action"] == {"action": "more-info"}
        assert tile["double_tap_action"] == {"action": "none"}
        assert tile["icon_double_tap_action"] == {"action": "none"}


def test_required_role_binding_cannot_be_omitted() -> None:
    document = _manifest()
    del document["spec"]["views"][0]["modules"][0]["bindings"]["contact"]
    try:
        render_dashboard(document, {"access": _contract()}, _bindings())
    except RenderError as exc:
        assert "missing required role binding" in str(exc)
    else:
        raise AssertionError("required role must be enforced")


def test_binding_domain_must_match_contract_role() -> None:
    inventory = _bindings()
    inventory["access.garden.contact"] = {
        "entity_id": "sensor.garden_door",
        "domain": "sensor",
        "verification": "verified",
    }
    try:
        render_dashboard(_manifest(), {"access": _contract()}, inventory)
    except RenderError as exc:
        assert "requires domains" in str(exc)
    else:
        raise AssertionError("domain mismatch must fail")


def test_toggle_is_restricted_to_explicit_safe_v1_domains() -> None:
    contract = _contract()
    contract["spec"]["roles"]["light"]["allowed_domains"] = ["lock"]
    inventory = _bindings()
    inventory["access.garden.light"] = {
        "entity_id": "lock.garden",
        "domain": "lock",
        "verification": "verified",
    }
    try:
        render_dashboard(_manifest(), {"access": contract}, inventory)
    except RenderError as exc:
        assert "requests toggle for unsupported domain" in str(exc)
    else:
        raise AssertionError("unsafe toggle domain must fail")


def test_role_order_and_action_coverage_are_explicit() -> None:
    contract = _contract()
    contract["spec"]["presentation"]["role_order"] = ["contact"]
    try:
        render_dashboard(_manifest(), {"access": contract}, _bindings())
    except RenderError as exc:
        assert "role_order must contain every role" in str(exc)
    else:
        raise AssertionError("partial role order must fail")

    contract = _contract()
    contract["spec"]["actions"].pop()
    try:
        render_dashboard(_manifest(), {"access": contract}, _bindings())
    except RenderError as exc:
        assert "exactly one explicit action per role" in str(exc)
    else:
        raise AssertionError("action coverage must fail")


def test_service_action_is_not_rendered_by_v1() -> None:
    contract = _contract()
    contract["spec"]["actions"][0]["kind"] = "service"
    contract["spec"]["actions"][0]["target"] = "homeassistant.update_entity"
    try:
        render_dashboard(_manifest(), {"access": contract}, _bindings())
    except RenderError as exc:
        assert "unsupported service action" in str(exc)
    else:
        raise AssertionError("service action must fail closed")


def test_navigate_requires_absolute_path() -> None:
    contract = _contract()
    contract["spec"]["actions"][0]["kind"] = "navigate"
    contract["spec"]["actions"][0]["target"] = "dashboard-house/access"
    try:
        render_dashboard(_manifest(), {"access": contract}, _bindings())
    except RenderError as exc:
        assert "requires absolute target" in str(exc)
    else:
        raise AssertionError("relative navigation must fail")


def test_render_is_deterministic_and_trace_matches_schema(tmp_path: Path) -> None:
    first = _render()
    second = _render()
    assert first == second

    output = tmp_path / "house.yaml"
    yaml_path, meta_path = write_render_result(output, first)
    first_yaml = yaml_path.read_bytes()
    first_meta = meta_path.read_bytes()

    write_render_result(output, second)
    assert yaml_path.read_bytes() == first_yaml
    assert meta_path.read_bytes() == first_meta

    trace_schema = json.loads(
        (Path(__file__).parents[1] / "schemas" / "render-trace.schema.json").read_text(
            encoding="utf-8"
        )
    )
    trace = json.loads(meta_path.read_text(encoding="utf-8"))
    assert list(Draft202012Validator(trace_schema).iter_errors(trace)) == []
    assert yaml.safe_load(yaml_path.read_text(encoding="utf-8")) == first.dashboard
