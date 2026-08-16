"""CH-0106: pipeline/scaffold writes stay under the output directory."""

from pathlib import Path

import pytest

from Asgard.Volundr.CICD.services.pipeline_generator import (
    confine_pipeline_output,
    safe_pipeline_name,
)
from Asgard.Volundr.Scaffold.services.microservice_scaffold import _confine_scaffold_path


def test_parent_name_is_rejected():
    with pytest.raises(ValueError):
        safe_pipeline_name("../x")


def test_pipeline_save_path_parent_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        confine_pipeline_output(str(tmp_path), "../x.yml")


def test_pipeline_save_path_stays_under_output(tmp_path: Path):
    dest = confine_pipeline_output(str(tmp_path), "ci.yml")
    assert dest.is_relative_to(tmp_path.resolve())


def test_spaces_normalize_to_hyphens():
    assert safe_pipeline_name("CI Pipeline") == "ci-pipeline"


def test_scaffold_parent_path_rejected(tmp_path: Path):
    with pytest.raises(ValueError):
        _confine_scaffold_path(str(tmp_path), "../x")
