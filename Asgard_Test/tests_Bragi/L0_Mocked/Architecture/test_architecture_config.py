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


def test_load_rejects_non_mapping_layers():
    yaml_content = "layers: not-a-list\nlanguage: python\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(yaml_content)
        tmp_path = f.name
    try:
        config = load_architecture_config(tmp_path)
        assert config.layers == []
    finally:
        os.unlink(tmp_path)


def test_load_directory_returns_defaults(tmp_path):
    config = load_architecture_config(str(tmp_path))
    assert len(config.layers) > 0
    assert any(layer.name == "domain" for layer in config.layers)


def test_untyped_level_imports_and_fan_out_are_coerced(tmp_path):
    yaml_content = """
language: python
layers:
  - name: core
    path_patterns:
      - "*/core/*"
    allowed_imports: core
    forbidden_imports: [12, infra]
    level: high
  - name: infra
    path_patterns:
      - "*/infra/*"
    allowed_imports: [core, 9]
    level: 2
rules:
  max_module_fan_out: lots
  detect_module_cycles: "yes"
"""
    path = tmp_path / "architecture.yml"
    path.write_text(yaml_content, encoding="utf-8")
    config = load_architecture_config(str(path))
    core = next(layer for layer in config.layers if layer.name == "core")
    infra = next(layer for layer in config.layers if layer.name == "infra")
    assert core.allowed_imports == []
    assert core.forbidden_imports == ["infra"]
    assert core.level is None
    assert infra.allowed_imports == ["core"]
    assert infra.level == 2
    assert config.rules.max_module_fan_out is None
    assert config.rules.detect_module_cycles is True
