from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_house_layout_source_is_identical_in_cli_and_runtime() -> None:
    generator = (ROOT / "generator" / "render_house.py").read_bytes()
    runtime = (
        ROOT
        / "custom_components"
        / "nikas_house"
        / "runtime_house.py"
    ).read_bytes()
    assert generator == runtime


def test_house_base_source_is_identical_in_cli_and_runtime() -> None:
    generator = (ROOT / "generator" / "house_base.py").read_bytes()
    runtime = (
        ROOT
        / "custom_components"
        / "nikas_house"
        / "house_base.py"
    ).read_bytes()
    assert generator == runtime
