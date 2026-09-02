from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
PACKAGE_PATH = ROOT / "custom_components" / "nikas_house"
REGISTRATION_PATH = PACKAGE_PATH / "runtime_registration.py"


def _registration_module():
    package_name = "nikas_house_runtime_registration_test"
    package_spec = importlib.util.spec_from_file_location(
        package_name,
        PACKAGE_PATH / "__init__.py",
        submodule_search_locations=[str(PACKAGE_PATH)],
    )
    assert package_spec is not None and package_spec.loader is not None
    package = importlib.util.module_from_spec(package_spec)
    sys.modules[package_name] = package
    package_spec.loader.exec_module(package)

    spec = importlib.util.spec_from_file_location(
        f"{package_name}.runtime_registration",
        REGISTRATION_PATH,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _manifest(dashboard_path: str = "/dashboard-infrastructure") -> dict:
    return {
        "api_version": "nikas.home-assistant/panel-manifest/v1",
        "kind": "PanelManifest",
        "metadata": {
            "id": "infrastructure",
            "title": "Infrastructure",
            "version": "1.0",
        },
        "spec": {
            "dashboard_path": dashboard_path,
            "views": [
                {
                    "id": "overview",
                    "title": "Infrastructure",
                    "path": "overview",
                    "order": 0,
                    "modules": [
                        {
                            "contract": "infra",
                            "order": 0,
                            "bindings": {
                                "status": "infrastructure.router.status"
                            },
                        }
                    ],
                }
            ],
        },
    }


def _write_manifest(source_root: Path, document: dict) -> None:
    manifest_root = source_root / "manifests"
    manifest_root.mkdir(parents=True, exist_ok=True)
    (manifest_root / "infrastructure.yaml").write_text(
        yaml.safe_dump(document, sort_keys=False),
        encoding="utf-8",
    )


def test_registration_export_is_official_yaml_shape_and_deterministic(
    tmp_path: Path,
) -> None:
    registration = _registration_module()
    source_root = tmp_path / "nikas_house"
    generated_root = source_root / "generated"
    _write_manifest(source_root, _manifest())

    first = registration.write_lovelace_registration_snippet(
        source_root,
        generated_root,
    )
    assert first.changed is True
    assert first.dashboard_count == 1
    text = first.path.read_text(encoding="utf-8")
    assert "registration snippet only" in text
    document = yaml.safe_load(text)
    dashboard = document["lovelace"]["dashboards"]["dashboard-infrastructure"]
    assert dashboard == {
        "mode": "yaml",
        "filename": "nikas_house/generated/infrastructure.yaml",
        "title": "Infrastructure",
        "show_in_sidebar": True,
        "require_admin": False,
    }

    before = first.path.read_bytes()
    second = registration.write_lovelace_registration_snippet(
        source_root,
        generated_root,
    )
    assert second.changed is False
    assert second.path.read_bytes() == before


def test_registration_rejects_single_word_yaml_dashboard_url(tmp_path: Path) -> None:
    registration = _registration_module()
    source_root = tmp_path / "nikas_house"
    _write_manifest(source_root, _manifest("/infrastructure"))

    try:
        registration.write_lovelace_registration_snippet(
            source_root,
            source_root / "generated",
        )
    except registration.RuntimeRegistrationError as exc:
        assert "must contain a hyphen" in str(exc)
    else:
        raise AssertionError("Home Assistant YAML dashboard slug rule must be enforced")
