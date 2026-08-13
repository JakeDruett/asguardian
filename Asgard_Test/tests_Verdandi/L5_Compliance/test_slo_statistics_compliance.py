"""
L5 Compliance Tests — Verdandi SLO / Statistics Ground Truths.

Known-bad series (SLO breach, obvious spike) MUST be detected; known-good
series (clean traffic, stable metric) MUST NOT raise. References: Google
SRE error-budget model (SRE-ErrorBudget), statistical anomaly detection.
"""

from datetime import datetime, timedelta

from Asgard.Verdandi.Anomaly.services.statistical_detector import StatisticalDetector
from Asgard.Verdandi.SLO.models.slo_models import (
    SLIMetric,
    SLOComplianceStatus,
    SLODefinition,
    SLOType,
)
from Asgard.Verdandi.SLO.services.error_budget_calculator import ErrorBudgetCalculator

_NOW = datetime(2026, 5, 19, 12, 0, 0)


def _slo(target: float = 99.9) -> SLODefinition:
    return SLODefinition(
        name="l5-slo",
        slo_type=SLOType.AVAILABILITY,
        target=target,
        window_days=30,
        service_name="l5-service",
    )


def _metrics(good: int, total: int) -> list:
    return [SLIMetric(
        timestamp=_NOW - timedelta(days=15),
        service_name="l5-service",
        slo_type=SLOType.AVAILABILITY,
        good_events=good,
        total_events=total,
    )]


class TestSLOBreachCompliance:
    """Known-bad: error rate far beyond budget MUST report BREACHED."""

    def setup_method(self) -> None:
        self.calc = ErrorBudgetCalculator()

    def test_gross_breach_detected(self) -> None:
        # 99.9% target, 10% failures: 100x the allowed budget.
        budget = self.calc.calculate(
            _slo(99.9), _metrics(good=9_000, total=10_000), current_time=_NOW
        )
        assert budget.status == SLOComplianceStatus.BREACHED, (
            f"10% failure rate against a 99.9% SLO must breach, got {budget.status}"
        )
        assert budget.budget_consumed_percent >= 100.0

    def test_clean_traffic_compliant(self) -> None:
        budget = self.calc.calculate(
            _slo(99.9), _metrics(good=10_000, total=10_000), current_time=_NOW
        )
        assert budget.status == SLOComplianceStatus.COMPLIANT
        assert budget.budget_consumed_percent == 0.0

    def test_budget_size_matches_sre_formula(self) -> None:
        # Google SRE: allowed failures = (1 - target) * total events.
        budget = self.calc.calculate(
            _slo(99.9), _metrics(good=999_000, total=1_000_000), current_time=_NOW
        )
        assert abs(budget.allowed_failures - 1_000.0) < 1.0


class TestAnomalyDetectionCompliance:
    """Known-bad: a 5x spike in a stable series MUST be detected."""

    def setup_method(self) -> None:
        self.detector = StatisticalDetector()

    @staticmethod
    def _stable_series() -> list:
        # Deterministic small oscillation around 100.
        return [100.0 + (0.5 if i % 2 else -0.5) for i in range(40)]

    def test_spike_detected(self) -> None:
        values = self._stable_series()
        values[20] = 500.0  # unmistakable spike
        anomalies = self.detector.detect(values, metric_name="latency_ms")
        assert anomalies, "5x spike in a stable series must be detected"
        spike_values = [a.actual_value for a in anomalies]
        assert 500.0 in spike_values, (
            f"Spike value must be among anomalies, got {spike_values}"
        )

    def test_stable_series_clean(self) -> None:
        anomalies = self.detector.detect(
            self._stable_series(), metric_name="latency_ms"
        )
        assert anomalies == [], (
            f"Stable series must yield no anomalies, got {len(anomalies)}"
        )

    def test_detection_is_deterministic(self) -> None:
        values = self._stable_series()
        values[10] = 400.0
        first = self.detector.detect(values, metric_name="m")
        second = self.detector.detect(values, metric_name="m")
        assert [a.actual_value for a in first] == [a.actual_value for a in second]
