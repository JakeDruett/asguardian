"""CHC-0004: generated artifact writes stay under output_dir."""

from pathlib import Path

import pytest

from Asgard.Volundr._output_jail import confine_output_file
from Asgard.Volundr.Docker.models.docker_models import GeneratedDockerConfig
from Asgard.Volundr.Docker.services.dockerfile_generator import DockerfileGenerator


def test_confine_rejects_parent_path(tmp_path: Path):
    with pytest.raises(ValueError):
        confine_output_file(tmp_path, "../evil")


def test_dockerfile_save_rejects_parent(tmp_path: Path):
    gen = DockerfileGenerator()
    cfg = GeneratedDockerConfig(
        id="x",
        config_hash="h",
        dockerfile_content="FROM scratch\n",
        best_practice_score=0,
    )
    with pytest.raises(ValueError):
        gen.save_to_file(cfg, output_dir=str(tmp_path), filename="../evil")
    assert not (tmp_path.parent / "evil").exists()
