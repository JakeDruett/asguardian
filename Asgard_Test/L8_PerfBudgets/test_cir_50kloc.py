"""
Heimdall Plan-02 perf bar: synthetic ~50k LOC CIR build under budget.

Plan (_Docs/Planning/Heimdall/02_SOLID_Detection.md): 50k LOC in <5s on
4 cores. The enforced budget (heimdall.cir_build_50kloc_ms) carries >= 5x
headroom over that target so the test stays deterministic-ish across
varied hardware — it exists to catch order-of-magnitude regressions in the
tree-sitter capture/assembly path, not to certify the plan's target.

The synthetic tree is generated deterministically in-memory: 100 modules of
~500 LOC each (classes with methods, fields, and self-attribute accesses so
the CIR builder does real assembly work).
"""

import time

import pytest

from Asgard.Bragi.Architecture.cir.builder import build_file_cir
from Asgard.Heimdall.treesitter._language_loader import is_available

N_MODULES = 100
CLASSES_PER_MODULE = 5
METHODS_PER_CLASS = 10


def _make_module_source(module_idx: int) -> str:
    """~500 LOC of deterministic Python with CIR-relevant structure."""
    parts = ["import os\nimport json\n\n"]
    for c in range(CLASSES_PER_MODULE):
        parts.append(f"class Service_{module_idx}_{c}:\n")
        parts.append("    def __init__(self):\n")
        parts.append(f"        self.state_{c} = {{}}\n")
        parts.append(f"        self.counter_{c} = 0\n\n")
        for m in range(METHODS_PER_CLASS):
            parts.append(f"    def method_{m}(self, arg_a, arg_b):\n")
            parts.append(f"        self.counter_{c} += arg_a\n")
            parts.append(f"        self.state_{c}[arg_b] = arg_a + {m}\n")
            parts.append(f"        local = arg_a * {m + 1}\n")
            parts.append(f"        if local > {m * 10}:\n")
            parts.append(f"            return self.counter_{c}\n")
            parts.append(f"        return local + self.counter_{c}\n\n")
    return "".join(parts)


@pytest.mark.skipif(
    not is_available("python"), reason="tree-sitter python grammar unavailable"
)
class TestCIR50kLocBuild:
    def test_synthetic_tree_is_about_50k_loc(self):
        loc = sum(
            _make_module_source(i).count("\n") for i in range(N_MODULES)
        )
        assert 40_000 <= loc <= 70_000, f"synthetic tree is {loc} LOC"

    def test_cir_build_50kloc_within_budget(self, l8_budget):
        sources = [
            (f"module_{i}.py", _make_module_source(i)) for i in range(N_MODULES)
        ]
        start = time.perf_counter()
        file_infos = [
            build_file_cir(path, source, "python") for path, source in sources
        ]
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        assert all(fi is not None for fi in file_infos)
        total_classes = sum(len(fi.classes) for fi in file_infos)
        assert total_classes == N_MODULES * CLASSES_PER_MODULE
        assert elapsed_ms <= l8_budget("heimdall.cir_build_50kloc_ms")
