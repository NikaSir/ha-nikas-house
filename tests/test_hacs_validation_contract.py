"""Keep full HACS publication validation in the required CI chain."""

from pathlib import Path

import yaml


def test_required_hacs_action_has_no_publication_exemptions():
    root = Path(__file__).resolve().parents[1]
    workflow = yaml.safe_load((root / ".github/workflows/repository-checks.yml").read_text())
    jobs = workflow["jobs"]
    assert "hacs" in jobs["validate"]["needs"]
    actions = [step for step in jobs["hacs"]["steps"]
               if step.get("uses", "").startswith("hacs/action@")]
    assert len(actions) == 1
    assert actions[0]["with"]["category"] == "integration"
    assert "ignore" not in actions[0]["with"], "HACS must validate topics and all publication checks"
