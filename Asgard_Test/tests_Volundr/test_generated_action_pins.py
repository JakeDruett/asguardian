"""CH-0001 residual: generated workflows must not emit mutable @vN tags."""

import re

from Asgard.Volundr.CICD.services.action_pins import pinned
from Asgard.Volundr.Docker.services.dockerfile_generator import _scan_workflow
from Asgard.Volundr.Scaffold.models.scaffold_models import ProjectConfig
from Asgard.Volundr.Scaffold.services._monorepo_infra_templates import github_actions_ci
from Asgard.Volundr.Scaffold.services._monorepo_infra_templates_part2 import github_actions_cd

_MUTABLE = re.compile(r"uses:\s+\S+@v\d")


def test_scaffold_ci_pins_checkout():
    yaml_text = github_actions_ci(ProjectConfig(name="demo", version="0.1.0", description="d"))
    assert _MUTABLE.search(yaml_text) is None
    assert pinned("actions/checkout@v4") in yaml_text


def test_scaffold_cd_pins_checkout():
    yaml_text = github_actions_cd(ProjectConfig(name="demo", version="0.1.0", description="d"))
    assert _MUTABLE.search(yaml_text) is None


def test_scan_workflow_pins_checkout():
    text = _scan_workflow(privileged_scan=False)
    assert "actions/checkout@v4" not in text
    assert pinned("actions/checkout@v4") in text
