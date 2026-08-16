"""CH-0096: init-linter project_name must be a safe identifier."""

from pathlib import Path

import pytest

from Asgard.Shared.Init.linter_initializer import LinterInitializer


def test_rejects_toml_breakout_name(tmp_path: Path):
    with pytest.raises(ValueError, match="project_name"):
        LinterInitializer(tmp_path, project_name='foo"]\n')


def test_rejects_hook_injection_name(tmp_path: Path):
    with pytest.raises(ValueError, match="project_name"):
        LinterInitializer(tmp_path, project_name="foo; id")


def test_accepts_identifier(tmp_path: Path):
    init = LinterInitializer(tmp_path, project_name="my_proj-1")
    assert init.project_name == "my_proj-1"
