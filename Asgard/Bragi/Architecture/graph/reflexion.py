"""
Reflexion-model summary (Plan 03 §Concrete Changes item 6, RESEARCH_05).

Compares the *declared* architecture (layer `allowed_imports` edges from
`architecture.yml`) against the *observed* import graph, classifying each
cross-layer relationship the way Murphy/Notkin Reflexion Models do:

- **convergence**: a declared allowed edge that is actually observed.
- **divergence**: an observed cross-layer edge that was never declared
  allowed (over-approximated: anything not explicitly allowed diverges —
  an unresolved edge is never assumed clean).
- **absence**: a declared allowed edge that is never observed in code
  (dead architecture documentation).

Same-layer edges are always architecturally legal and carry no signal in
any of the three buckets, so they are excluded from the universe.
Output ordering is fully sorted — deterministic across runs.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from Asgard.Bragi.Architecture.services._architecture_config import ArchitectureConfig

LayerEdge = Tuple[str, str]


@dataclass
class ReflexionSummary:
    """Counts + sorted edge lists for the reflexion comparison."""

    convergences: List[LayerEdge] = field(default_factory=list)
    divergences: List[LayerEdge] = field(default_factory=list)
    absences: List[LayerEdge] = field(default_factory=list)

    @property
    def convergence_count(self) -> int:
        return len(self.convergences)

    @property
    def divergence_count(self) -> int:
        return len(self.divergences)

    @property
    def absence_count(self) -> int:
        return len(self.absences)

    def to_dict(self) -> dict:
        return {
            "convergences": [list(e) for e in self.convergences],
            "divergences": [list(e) for e in self.divergences],
            "absences": [list(e) for e in self.absences],
            "convergence_count": self.convergence_count,
            "divergence_count": self.divergence_count,
            "absence_count": self.absence_count,
        }


def layer_name_for_module(
    module: str,
    class_names: Set[str],
    config: ArchitectureConfig,
) -> Optional[str]:
    """Glob/suffix classification of a module into a declared layer.

    Unlike `propagation._match_layer` this considers every layer, not only
    level-annotated ones, so reflexion also works for old glob-only
    configurations. Returns None when unmatched (unclassified modules are
    excluded from the reflexion universe rather than guessed)."""
    path_str = "/" + module.replace(".", "/")
    for layer in config.layers:
        for pattern in layer.path_patterns:
            if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(module, pattern):
                return layer.name
        for suffix in layer.suffixes:
            if module.split(".")[-1].endswith(suffix):
                return layer.name
            if any(name.endswith(suffix) for name in class_names):
                return layer.name
    return None


def declared_allowed_edges(config: ArchitectureConfig) -> Set[LayerEdge]:
    """Cross-layer edges the configuration explicitly allows."""
    known = {layer.name for layer in config.layers}
    declared: Set[LayerEdge] = set()
    for layer in config.layers:
        for target in layer.allowed_imports:
            if target in known and target != layer.name:
                declared.add((layer.name, target))
    return declared


def observed_layer_edges(
    module_deps: Dict[str, List[str]],
    layer_by_module: Dict[str, Optional[str]],
) -> Set[LayerEdge]:
    """Cross-layer edges actually present in the import graph."""
    observed: Set[LayerEdge] = set()
    for src, deps in module_deps.items():
        src_layer = layer_by_module.get(src)
        if src_layer is None:
            continue
        for dst in deps:
            dst_layer = layer_by_module.get(dst)
            if dst_layer is None or dst_layer == src_layer:
                continue
            observed.add((src_layer, dst_layer))
    return observed


def compute_reflexion(
    module_deps: Dict[str, List[str]],
    layer_by_module: Dict[str, Optional[str]],
    config: ArchitectureConfig,
) -> ReflexionSummary:
    """Full reflexion comparison: declared vs observed cross-layer edges."""
    declared = declared_allowed_edges(config)
    observed = observed_layer_edges(module_deps, layer_by_module)
    return ReflexionSummary(
        convergences=sorted(observed & declared),
        divergences=sorted(observed - declared),
        absences=sorted(declared - observed),
    )
