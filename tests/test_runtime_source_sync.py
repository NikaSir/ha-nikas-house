from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
PACKAGE_PATH = ROOT / "custom_components" / "nikas_house"
EXPECTED_PUBLIC_SOURCE_FILES = 3


def _module():
    package_name = "nikas_house_sync_test"
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
        f"{package_name}.runtime_source_sync",
        PACKAGE_PATH / "runtime_source_sync.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_bundled_sync_keeps_private_and_unowned_data_untouched(tmp_path: Path) -> None:
    module = _module()
    root = tmp_path / "nikas_house"
    (root / "inventory").mkdir(parents=True)
    (root / "snapshots").mkdir(parents=True)
    (root / "generated").mkdir(parents=True)
    (root / "manifests").mkdir(parents=True)

    private_files = {
        root / "inventory" / "home.yaml": "PRIVATE-INVENTORY\n",
        root / "snapshots" / "current.json": "PRIVATE-SNAPSHOT\n",
        root / "generated" / "legacy-house.yaml": "GENERATED-HISTORY\n",
        root / "manifests" / "private_runtime.yaml": "PRIVATE-RUNTIME-MANIFEST\n",
    }
    for path, content in private_files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    result = module.sync_bundled_public_sources(root)
    assert result.checked_files == EXPECTED_PUBLIC_SOURCE_FILES
    assert result.changed_files == EXPECTED_PUBLIC_SOURCE_FILES

    for path, content in private_files.items():
        assert path.read_text(encoding="utf-8") == content

    assert (root / "contracts" / "house_home.yaml").exists()
    assert (root / "manifests" / "house_v13.yaml").exists()
    assert (root / "navigation" / "main.yaml").exists()
    assert not (root / "contracts" / "actions_home.yaml").exists()
    assert not (root / "manifests" / "infrastructure.yaml").exists()

    second = module.sync_bundled_public_sources(root)
    assert second.checked_files == EXPECTED_PUBLIC_SOURCE_FILES
    assert second.changed_files == 0
