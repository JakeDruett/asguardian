"""
Tests for Heimdall Plan 03 item 6 — Reflexion-model summary
(convergences / divergences / absences of declared allowed layer edges
vs the observed import graph, per RESEARCH_05).
"""
import json

import pytest

from Asgard.Bragi.Architecture.graph.reflexion import (
    ReflexionSummary,
    compute_reflexion,
    declared_allowed_edges,
    layer_name_for_module,
    observed_layer_edges,
)
from Asgard.Bragi.Architecture.graph.service import ArchGraphService
from Asgard.Bragi.Architecture.services._architecture_config import (
    default_architecture_config,
)
from Asgard.Bragi.Dependencies.models.dependency_models import DependencyConfig


@pytest.fixture(autouse=True)
def _no_disk_cache(monkeypatch):
    monkeypatch.setenv("ASGARD_NO_CACHE", "1")


def _write_project(root, files: dict):
    for rel, content in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)


CLEAN_PROJECT = {
    "domain/__init__.py": "",
    "domain/order.py": "class Order:\n    pass\n",
    "services/__init__.py": "",
    "services/order_service.py": "from domain.order import Order\n\nclass OrderService:\n    pass\n",
    "infrastructure/__init__.py": "",
    "infrastructure/order_repo.py": (
        "from services.order_service import OrderService\n"
        "from domain.order import Order\n\n"
        "class OrderRepository:\n    pass\n"
    ),
}

DIVERGENT_PROJECT = {
    **CLEAN_PROJECT,
    "domain/naughty.py": (
        "from infrastructure.order_repo import OrderRepository\n\n"
        "class Naughty:\n    pass\n"
    ),
}


def _arch_service(scan_path):
    return ArchGraphService(
        config=default_architecture_config(),
        dep_config=DependencyConfig(scan_path=scan_path),
    )


class TestUnits:
    def test_declared_edges_skip_unknown_and_self(self):
        cfg = default_architecture_config()
        declared = declared_allowed_edges(cfg)
        assert ("application", "domain") in declared
        assert ("infrastructure", "application") in declared
        # No self edges, no edges from names outside the layer set.
        assert all(src != dst for src, dst in declared)

    def test_layer_name_for_module_glob_and_unmatched(self):
        cfg = default_architecture_config()
        assert layer_name_for_module("domain.order", set(), cfg) == "domain"
        assert layer_name_for_module("services.order_service", set(), cfg) == "application"
        assert layer_name_for_module("utils.helper", set(), cfg) is None

    def test_observed_edges_exclude_same_layer_and_unclassified(self):
        deps = {
            "domain.a": ["domain.b", "utils.x"],
            "services.s": ["domain.a"],
        }
        layers = {
            "domain.a": "domain", "domain.b": "domain",
            "services.s": "application", "utils.x": None,
        }
        assert observed_layer_edges(deps, layers) == {("application", "domain")}

    def test_compute_reflexion_buckets_and_determinism(self):
        cfg = default_architecture_config()
        deps = {
            "services.s": ["domain.a"],          # convergence
            "domain.a": ["infrastructure.r"],    # divergence (never allowed)
        }
        layers = {
            "domain.a": "domain",
            "services.s": "application",
            "infrastructure.r": "infrastructure",
        }
        summary = compute_reflexion(deps, layers, cfg)
        assert ("application", "domain") in summary.convergences
        assert ("domain", "infrastructure") in summary.divergences
        # Declared-but-unobserved edges are absences, never silently dropped.
        assert ("infrastructure", "application") in summary.absences
        # Deterministic: identical inputs give identical (sorted) output.
        again = compute_reflexion(deps, layers, cfg)
        assert summary.to_dict() == again.to_dict()
        assert summary.divergences == sorted(summary.divergences)


class TestServiceIntegration:
    def test_clean_project_has_no_divergences(self, tmp_path):
        _write_project(tmp_path, CLEAN_PROJECT)
        summary = _arch_service(tmp_path).reflexion_summary(tmp_path)
        assert summary.divergence_count == 0
        assert ("application", "domain") in summary.convergences
        assert ("infrastructure", "domain") in summary.convergences
        # 'ports' layer never appears in the fixture -> its declared
        # edges are honestly reported absent.
        assert ("ports", "domain") in summary.absences

    def test_divergent_project_reports_domain_to_infrastructure(self, tmp_path):
        _write_project(tmp_path, DIVERGENT_PROJECT)
        summary = _arch_service(tmp_path).reflexion_summary(tmp_path)
        assert ("domain", "infrastructure") in summary.divergences

    def test_hexagonal_report_carries_reflexion_and_reporters_render_it(self, tmp_path):
        from Asgard.Bragi.Architecture.models.architecture_models import (
            ArchitectureConfig,
        )
        from Asgard.Bragi.Architecture.services.hexagonal_analyzer import (
            HexagonalAnalyzer,
        )

        _write_project(tmp_path, DIVERGENT_PROJECT)
        analyzer = HexagonalAnalyzer(ArchitectureConfig(scan_path=tmp_path))
        report = analyzer.analyze(tmp_path)

        assert isinstance(report.reflexion, ReflexionSummary)
        assert ("domain", "infrastructure") in report.reflexion.divergences

        text = analyzer.generate_report(report, "text")
        assert "REFLEXION MODEL" in text
        assert "domain -> infrastructure" in text

        data = json.loads(analyzer.generate_report(report, "json"))
        assert data["reflexion"]["divergence_count"] >= 1
        assert ["domain", "infrastructure"] in data["reflexion"]["divergences"]

        md = analyzer.generate_report(report, "markdown")
        assert "## Reflexion Model" in md
