from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

_MAX_ARCH_YAML_BYTES = 256 * 1024


@dataclass
class RulesConfig:
    """Optional top-level `rules:` block (Plan 03 schema)."""

    max_module_fan_out: Optional[int] = None
    detect_module_cycles: bool = True


@dataclass
class LayerConfig:
    name: str
    path_patterns: list[str]
    allowed_imports: list[str]
    forbidden_imports: list[str]
    # --- Plan 03 extensions (all optional, backward compatible) ---
    level: Optional[int] = None
    suffixes: list[str] = field(default_factory=list)
    external_imports: list[str] = field(default_factory=list)


@dataclass
class ArchitectureConfig:
    layers: list[LayerConfig] = field(default_factory=list)
    language: str = "python"
    rules: RulesConfig = field(default_factory=RulesConfig)

    @property
    def has_level_inference(self) -> bool:
        """True when at least one layer declares a `level:` — enables the
        CSP layer-inference engine. False keeps the original glob-only
        classification path (old schema)."""
        return any(layer.level is not None for layer in self.layers)


_MAX_FNMATCH_PATTERN_LEN = 200
_MAX_FNMATCH_STARS = 8
_MAX_FNMATCH_PATTERNS = 64


def sanitize_path_patterns(patterns) -> list[str]:
    """Bound attacker-controlled fnmatch patterns (CWE-1333)."""
    if not isinstance(patterns, list):
        return []
    cleaned: list[str] = []
    for item in patterns[:_MAX_FNMATCH_PATTERNS]:
        if not isinstance(item, str):
            continue
        if len(item) > _MAX_FNMATCH_PATTERN_LEN or item.count("*") > _MAX_FNMATCH_STARS:
            continue
        cleaned.append(item)
    return cleaned


def _str_list(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _optional_int(value) -> Optional[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _parse_layer(layer: dict) -> LayerConfig:
    heuristics = layer.get("heuristics") or {}
    # New schema nests path patterns/suffixes/external anchors under
    # `heuristics:`; old schema keeps `path_patterns` at the layer's top
    # level. Support both — heuristics.paths wins if both are present.
    path_patterns = sanitize_path_patterns(
        heuristics.get("paths") or layer.get("path_patterns", [])
    )
    raw_suffixes = heuristics.get("suffixes") or []
    raw_external = heuristics.get("external_imports") or []
    suffixes = [s for s in raw_suffixes if isinstance(s, str)] if isinstance(raw_suffixes, list) else []
    external_imports = (
        [s for s in raw_external if isinstance(s, str)] if isinstance(raw_external, list) else []
    )

    return LayerConfig(
        name=layer["name"],
        path_patterns=path_patterns,
        allowed_imports=_str_list(layer.get("allowed_imports", [])),
        forbidden_imports=_str_list(layer.get("forbidden_imports", [])),
        level=_optional_int(layer.get("level")),
        suffixes=suffixes,
        external_imports=external_imports,
    )


def load_architecture_config(config_path: str) -> ArchitectureConfig:
    path = Path(config_path)
    if not path.is_file():
        return default_architecture_config()
    try:
        if path.stat().st_size > _MAX_ARCH_YAML_BYTES:
            return default_architecture_config()
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return default_architecture_config()

    if not isinstance(data, dict) or not data:
        return default_architecture_config()

    # New schema nests metadata under `architecture:` with a sibling
    # top-level `layers:`/`rules:`; old schema puts `layers:` at the root
    # with no `architecture:` key. Both are accepted.
    layers_data = data.get("layers", [])
    if not isinstance(layers_data, list):
        layers_data = []
    rules_data = data.get("rules") or {}
    if not isinstance(rules_data, dict):
        rules_data = {}
    language = data.get("language") or (data.get("architecture") or {}).get("language", "python")
    if not isinstance(language, str) or not language:
        language = "python"

    layers = []
    for layer in layers_data:
        if not isinstance(layer, dict):
            continue
        try:
            layers.append(_parse_layer(layer))
        except (KeyError, TypeError, ValueError):
            continue

    detect_cycles = rules_data.get("detect_module_cycles", True)
    if not isinstance(detect_cycles, bool):
        detect_cycles = True
    rules = RulesConfig(
        max_module_fan_out=_optional_int(rules_data.get("max_module_fan_out")),
        detect_module_cycles=detect_cycles,
    )

    return ArchitectureConfig(
        layers=layers,
        language=language,
        rules=rules,
    )


def default_architecture_config() -> ArchitectureConfig:
    """Zero-config default: sensible layer inference with no
    architecture.yml present. Levels are set so CSP inference is active
    by default (Plan 03's "no architecture.yml" requirement)."""
    return ArchitectureConfig(
        language="python",
        layers=[
            LayerConfig(
                name="domain",
                path_patterns=["*/domain/*", "*/models/*"],
                allowed_imports=[],
                forbidden_imports=["infrastructure", "adapters"],
                level=0,
                suffixes=["Entity", "ValueObject", "Model"],
            ),
            LayerConfig(
                name="ports",
                path_patterns=["*/ports/*"],
                allowed_imports=["domain"],
                forbidden_imports=["infrastructure"],
                level=0,
            ),
            LayerConfig(
                name="application",
                path_patterns=["*/services/*", "*/use_cases/*"],
                allowed_imports=["domain", "ports"],
                forbidden_imports=["infrastructure"],
                level=1,
                suffixes=["UseCase", "Service", "Handler"],
            ),
            LayerConfig(
                name="infrastructure",
                path_patterns=["*/infrastructure/*", "*/adapters/*", "*/repositories/*"],
                allowed_imports=["domain", "ports", "application"],
                forbidden_imports=[],
                level=2,
                external_imports=[
                    "sqlalchemy", "psycopg2", "requests", "boto3", "django.db",
                ],
            ),
        ],
        rules=RulesConfig(max_module_fan_out=12, detect_module_cycles=True),
    )
