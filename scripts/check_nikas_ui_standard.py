#!/usr/bin/env python3
"""Fail CI when a repository drifts from the mandatory NikaS UI contract."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / ".nikas-ui-standard.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def read_relative(path: str) -> str:
    target = ROOT / path
    require(target.is_file(), f"missing required file: {path}")
    return target.read_text(encoding="utf-8")


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    require(config.get("version") == "1.9", "NikaS UI standard version must be 1.9")
    require(
        config.get("navigation_contract_version") == "1.1",
        "NikaS navigation contract version must be 1.1",
    )

    standard_path = config.get("standard_path", "docs/NIKAS_SPECIALIZED_PANEL_UI_STANDARD.md")
    standard = read_relative(standard_path)
    digest = hashlib.sha256(standard.encode("utf-8")).hexdigest()
    require(digest == config.get("standard_sha256"), "local NikaS UI standard is not the canonical v1.9 copy")
    navigation_contract = read_relative(config["navigation_contract_path"])
    navigation_digest = hashlib.sha256(navigation_contract.encode("utf-8")).hexdigest()
    require(
        navigation_digest == config.get("navigation_contract_sha256"),
        "local NikaS navigation contract is not the canonical copy",
    )
    for clause in (
        "Center title plaque — return to the source NikaS base panel",
        'sessionStorage["nikas.specialized.source_route.v1"]',
        "return_to",
        "history.pushState()",
        "history.back()",
        "Capture precedence is:",
        "exact form `UI vX.Y.Z`",
        "focus state and pressed response",
        "same click/keyboard handler",
        "Ambient shell synchronization",
        "Data truth and command safety",
        "Production bundle and version coherence",
    ):
        require(clause in standard, f"canonical Header-return clause missing: {clause}")
    for clause in (
        "/dashboard-house-v13/home",
        "/dashboard-actions/home",
        "/dashboard-infrastructure/overview",
        "/starline",
        "nikas.specialized.source_route_at.v1",
        "same click/keyboard handler",
        "Both hand-off values are required",
        "timestamp from the future",
        "partial storage write is rolled back",
        "A missing, orphaned or mismatched public route is a blocking defect.",
    ):
        require(clause in navigation_contract, f"canonical navigation clause missing: {clause}")

    role = config.get("role")
    require(role in {"base", "specialized", "readiness"}, f"unsupported NikaS UI role: {role}")
    runtime_files = config.get("runtime_files", [])
    require(isinstance(runtime_files, list), "runtime_files must be a list")
    require(len(runtime_files) == len(set(runtime_files)), "runtime_files must not contain duplicates")
    sources = "\n".join(read_relative(path) for path in runtime_files)

    production_entrypoint = config.get("production_entrypoint")
    if production_entrypoint:
        require(
            production_entrypoint in runtime_files,
            "production_entrypoint must be one of the checked runtime_files",
        )

    if role == "readiness":
        require(not runtime_files, "readiness-only repository must not claim a panel runtime")
        compliance = read_relative(config["compliance_path"])
        require("GAP" in compliance, "readiness-only repository must record the absent runtime as GAP")
        require("data truth" in compliance.lower(), "readiness record must cover the data-truth GAP")
        require("autonomous" in compliance.lower(), "readiness record must cover the autonomous-bundle GAP")
        return

    require(runtime_files, f"{role} repository must declare checked runtime_files")

    for token in (
        "nikas.specialized.source_route.v1",
        "nikas.specialized.source_route_at.v1",
        "/dashboard-house-v13/home",
        "/dashboard-actions/home",
        "/dashboard-infrastructure/overview",
    ):
        require(token in sources, f"runtime route contract missing token: {token}")
    require('"/dashboard-house"' not in sources, "legacy /dashboard-house route is forbidden in runtime")
    require("'/dashboard-house'" not in sources, "legacy /dashboard-house route is forbidden in runtime")
    require("/dashboard-starline" not in sources, "invalid /dashboard-starline route is forbidden in runtime")

    if role == "base":
        require("sessionStorage" in sources, "base shell must persist the source-route hand-off")
        markers = config.get("source_handoff", {})
        require(isinstance(markers, dict) and markers, "base shell must declare source_handoff markers")
        for name in (
            "storage_write_marker",
            "timestamp_write_marker",
            "rollback_marker",
            "route_normalizer_marker",
            "specialized_route_marker",
            "capture_marker",
            "navigation_marker",
            "delegation_marker",
            "contract_version_marker",
        ):
            marker = markers.get(name)
            require(isinstance(marker, str) and marker, f"source_handoff.{name} must be configured")
            require(marker in sources, f"base source-route hand-off marker missing: {marker}")
        require(
            "rememberSpecializedSourceRoute(window.location.pathname);" not in sources,
            "ambient shell synchronization must not refresh the source hand-off",
        )
        delegated_files = config.get("delegated_navigation_files", [])
        require(delegated_files, "base shell must list every delegated navigation source")
        delegation_marker = markers["delegation_marker"]
        for path in delegated_files:
            require(
                delegation_marker in read_relative(path),
                f"base outbound navigation does not delegate to click-time hand-off: {path}",
            )
        for token in (
            "/dashboard-zont",
            "/starline",
            "/dashboard-s8-omni",
            "/dashboard-irrigation",
            "/dashboard-ups",
            "/dashboard-keenetic",
            "/dashboard-lider",
            "/dashboard-access-v1",
        ):
            require(token in sources, f"canonical specialized-panel route missing from base registry: {token}")
        return

    header_return_runtime_path = config.get("header_return_runtime_path", production_entrypoint)
    header_return_runtime = (
        read_relative(header_return_runtime_path) if header_return_runtime_path else sources
    )

    for token in (
        "return_to",
        "from",
        "history.pushState",
        "location-changed",
        "UI v",
        "sessionStorage",
        "removeItem(",
        "window.location.origin",
        "url.origin",
        "url.pathname",
        "document.referrer",
        "parent_route",
    ):
        require(token in header_return_runtime, f"specialized Header-return runtime missing token: {token}")
    require("history.back(" not in sources, "history.back() is forbidden by the NikaS routing contract")
    require(
        re.search(r"/dashboard-starline(?:[/'\"?#]|$)", sources) is None,
        "retired /dashboard-starline route is forbidden",
    )
    require(
        re.search(r"/dashboard-house(?:[/'\"?#]|$)", sources) is None,
        "legacy /dashboard-house route is forbidden as a specialized-panel return",
    )
    require(
        "<button" in header_return_runtime or 'createElement("button")' in header_return_runtime,
        "center title must be a semantic button",
    )

    markers = config.get("header_return", {})
    require(isinstance(markers, dict) and markers, "specialized panel must declare header_return markers")
    for name in (
        "button_marker",
        "version_marker",
        "focus_marker",
        "pressed_marker",
        "explicit_precedence_marker",
        "capture_once_marker",
        "timestamp_required_marker",
        "future_timestamp_rejection_marker",
    ):
        marker = markers.get(name)
        require(isinstance(marker, str) and marker, f"header_return.{name} must be configured")
        require(marker in header_return_runtime, f"specialized Header-return marker missing: {marker}")

    version_marker = markers["version_marker"]
    require("UI v" in version_marker, "header_return.version_marker must identify the exact UI version line")
    require("·" not in version_marker, "header_return.version_marker must be version-only")

    for marker in config.get("forbidden_runtime_markers", []):
        require(marker not in sources, f"forbidden specialized-panel runtime marker present: {marker}")

    artifact_kind = config.get("artifact_kind", "production")
    require(artifact_kind in {"production", "reference"}, "unsupported specialized artifact_kind")
    if artifact_kind == "reference":
        return

    require(production_entrypoint, "production specialized panel must declare production_entrypoint")
    require(
        runtime_files == [production_entrypoint],
        "runtime_files must contain only the shipped production_entrypoint",
    )
    bundle_contract = config.get("bundle_contract", {})
    require(bundle_contract.get("autonomous") is True, "production bundle must be autonomous")
    require(bundle_contract.get("runtime_imports") is False, "production bundle must forbid runtime imports")
    require(bundle_contract.get("deterministic") is True, "production bundle must be deterministic")
    require(
        bundle_contract.get("cache_busting") == "ui_version",
        "production bundle cache busting must follow ui_version",
    )

    entrypoint_source = read_relative(production_entrypoint)
    executable_lines = "\n".join(
        line for line in entrypoint_source.splitlines() if not line.lstrip().startswith("//")
    )
    require(
        re.search(r"^\s*(?:import|export)\b", executable_lines, re.MULTILINE) is None,
        "production entrypoint contains an ES module import/export",
    )
    require(
        re.search(r"\bimport\s*\(", executable_lines) is None,
        "production entrypoint contains a dynamic runtime import",
    )

    build_source_files = config.get("build_source_files", [])
    require(isinstance(build_source_files, list), "build_source_files must be a list")
    require(
        len(build_source_files) == len(set(build_source_files)),
        "build_source_files must not contain duplicates",
    )
    for path in build_source_files:
        read_relative(path)
    bundled_inputs = set(
        re.findall(r"^// BEGIN ([^\n]+)$", entrypoint_source, re.MULTILINE)
    )
    undeclared_inputs = bundled_inputs.difference(build_source_files)
    require(
        not undeclared_inputs,
        "production bundle contains undeclared build inputs: "
        + ", ".join(sorted(undeclared_inputs)),
    )

    ui_version = config.get("ui_version")
    require(
        isinstance(ui_version, str) and re.fullmatch(r"\d+\.\d+\.\d+", ui_version),
        "production specialized panel must declare numeric ui_version",
    )
    require(ui_version in entrypoint_source, "production entrypoint does not contain configured ui_version")
    require(
        isinstance(config.get("web_component"), str) and config["web_component"],
        "production specialized panel must declare web_component",
    )
    require(
        config["web_component"] in entrypoint_source,
        "production entrypoint does not register the configured web_component",
    )

    data_truth = config.get("data_truth", {})
    require(
        data_truth.get("entity_source") == "integration_or_ha_registry",
        "data truth entity_source must be integration_or_ha_registry",
    )
    require(data_truth.get("unknown_unavailable") == "explicit", "unknown/unavailable policy must be explicit")
    require(data_truth.get("invented_entity_ids") is False, "invented entity IDs are forbidden")
    require(
        data_truth.get("fixed_entity_ids") in {"none", "tested_public_contract_only"},
        "fixed entity IDs must be absent or an explicit tested public contract",
    )
    command_policy = data_truth.get("command_policy")
    require(
        command_policy in {"read_only", "refresh_only", "integration_services", "entity_services"},
        "unsupported command policy",
    )
    lowered_source = entrypoint_source.lower()
    require("unknown" in lowered_source, "production runtime must render unknown data explicitly")
    require("unavailable" in lowered_source, "production runtime must render unavailable data explicitly")

    if command_policy == "read_only":
        forbidden_commands = data_truth.get("forbidden_command_markers", [])
        require(forbidden_commands, "read-only panel must declare forbidden command markers")
        for marker in forbidden_commands:
            require(marker not in entrypoint_source, f"read-only panel contains command marker: {marker}")
    else:
        command_markers = data_truth.get("command_markers", [])
        require(command_markers, "command-capable panel must declare runtime command markers")
        for marker in command_markers:
            require(marker in entrypoint_source, f"declared command marker missing: {marker}")


if __name__ == "__main__":
    main()
