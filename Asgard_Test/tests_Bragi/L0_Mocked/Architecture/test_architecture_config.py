import tempfile
import os

import pytest

from Asgard.Bragi.Architecture.services._architecture_config import (
    ArchitectureConfig,
    LayerConfig,
    default_architecture_config,
    load_architecture_config,
)
from Asgard.Bragi.Architecture.services.hexagonal_analyzer import HexagonalAnalyzer


def test_load_default_config():
    config = default_architecture_config()
    assert isinstance(config, ArchitectureConfig)
    domain = next(l for l in config.layers if l.name == "domain")
    assert domain.allowed_imports == []


def test_load_from_yaml():
    yaml_content = """
language: python
layers:
  - name: core
    path_patterns:
      - "*/core/*"
    allowed_imports: []
    forbidden_imports: [infra]
  - name: infra
    path_patterns:
      - "*/infra/*"
    allowed_imports: [core]
    forbidden_imports: []
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name

    try:
        config = load_architecture_config(tmp_path)
        assert config.language == "python"
        names = [l.name for l in config.layers]
        assert "core" in names
        assert "infra" in names
        core = next(l for l in config.layers if l.name == "core")
        assert "*/core/*" in core.path_patterns
    finally:
        os.unlink(tmp_path)


def test_missing_yaml_returns_defaults():
    config = load_architecture_config("nonexistent.yml")
    assert isinstance(config, ArchitectureConfig)
    assert len(config.layers) > 0


def test_hexagonal_analyzer_accepts_config():
    layer_config = default_architecture_config()
    analyzer = HexagonalAnalyzer(layer_config=layer_config)
    assert analyzer.layer_config is layer_config


def test_hostile_fnmatch_patterns_are_dropped():
    from Asgard.Bragi.Architecture.services._architecture_config import sanitize_path_patterns

    assert sanitize_path_patterns(["*/core/*"]) == ["*/core/*"]
    assert sanitize_path_patterns(["*" * 20]) == []
    assert sanitize_path_patterns(["x" * 201]) == []
    assert sanitize_path_patterns([123, None]) == []

    yaml_content = """
language: python
layers:
  - name: core
    path_patterns:
      - "*/core/*"
      - "********************"
      - 12
    allowed_imports: []
    forbidden_imports: []
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name
    try:
        config = load_architecture_config(tmp_path)
        core = next(l for l in config.layers if l.name == "core")
        assert core.path_patterns == ["*/core/*"]
    finally:
        os.unlink(tmp_path)
