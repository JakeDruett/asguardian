"""
Verdandi-Volundr Integration Tests

Tests for cross-package integration between Verdandi (SLO / error budgets)
and Volundr (deployment manifest generation). The SLO error-budget status
acts as a deployment gate: a breached budget blocks or constrains rollout;
a healthy budget allows a normal rollout.
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from Asgard.Verdandi.SLO import (
    ErrorBudgetCalculator,
    SLIMetric,
    SLODefinition,
    SLOComplianceStatus,
)
from Asgard.Volundr import ManifestConfig, ManifestGenerator


def _slo() -> SLODefinition:
    return SLODefinition(
        name="checkout-availability",
        slo_type="availability",
        target=99.9,
        window_days=30,
        service_name="checkout",
    )


def _metrics(good: int, total: int) -> list:
    return [
        SLIMetric(
            timestamp=datetime.now() - timedelta(hours=1),
            service_name="checkout",
            slo_type="availability",
            good_events=good,
            total_events=total,
        )
    ]


def _status_value(status) -> str:
    return status.value if isinstance(status, SLOComplianceStatus) else str(status)


def _gate_allows_deploy(budget) -> bool:
    return _status_value(budget.status) == "compliant"


@pytest.mark.cross_package
class TestErrorBudgetGatesDeployment:
    def test_healthy_budget_allows_full_rollout(self, output_dir: Path):
        budget = ErrorBudgetCalculator().calculate(_slo(), _metrics(100_000, 100_000))
        assert _gate_allows_deploy(budget), (
            f"perfect SLI must be compliant, got {budget.status}"
        )

        manifest = ManifestGenerator(output_dir=str(output_dir)).generate(
            ManifestConfig(name="checkout", image="checkout:2.0.0", replicas=3)
        )
        assert manifest is not None
        assert "replicas: 3" in manifest.yaml_content

    def test_breached_budget_blocks_rollout(self, output_dir: Path):
        # 5% failure rate against a 99.9% target → budget obliterated.
        budget = ErrorBudgetCalculator().calculate(_slo(), _metrics(95_000, 100_000))
        assert _status_value(budget.status) == "breached", (
            f"5% error rate vs 99.9% target must breach, got {budget.status}"
        )
        assert budget.remaining_budget <= 0

        deployed = False
        if _gate_allows_deploy(budget):
            ManifestGenerator(output_dir=str(output_dir)).generate(
                ManifestConfig(name="checkout", image="checkout:2.0.0")
            )
            deployed = True

        assert not deployed, "breached error budget must block deployment"
        assert list(output_dir.glob("*.yaml")) == []

    def test_at_risk_budget_constrains_rollout_to_canary(self, output_dir: Path):
        # Consume most (but not all) of the 0.1% budget: 99.912% SLI.
        budget = ErrorBudgetCalculator().calculate(_slo(), _metrics(99_912, 100_000))
        status = _status_value(budget.status)
        assert status in ("at_risk", "compliant")

        replicas = 3 if status == "compliant" else 1
        manifest = ManifestGenerator(output_dir=str(output_dir)).generate(
            ManifestConfig(name="checkout", image="checkout:2.0.0", replicas=replicas)
        )
        assert f"replicas: {replicas}" in manifest.yaml_content
        if status == "at_risk":
            assert replicas == 1, "at-risk budget must constrain rollout size"
