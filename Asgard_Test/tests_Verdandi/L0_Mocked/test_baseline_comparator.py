"""Fail-closed baseline comparison (CH-0100)."""

from Asgard.Verdandi.Anomaly.models.anomaly_models import BaselineMetrics
from Asgard.Verdandi.Anomaly.services.baseline_comparator import BaselineComparator


def _invalid_baseline() -> BaselineMetrics:
    return BaselineMetrics(metric_name="latency", sample_count=0, std_dev=0.0)


def test_invalid_baseline_is_not_within():
    cmp = BaselineComparator()
    assert cmp.is_within_baseline(10.0, _invalid_baseline()) is False


def test_invalid_baseline_deviation_is_not_zero():
    cmp = BaselineComparator()
    assert cmp.calculate_deviation_score(10.0, _invalid_baseline()) == 1.0


def test_invalid_baseline_compare_is_unknown():
    cmp = BaselineComparator()
    result = cmp.compare([10.0, 11.0, 12.0], _invalid_baseline())
    assert result.overall_status == "unknown"
    assert result.is_significant is True


def test_empty_current_is_unknown_not_normal():
    valid = BaselineMetrics(
        metric_name="latency",
        sample_count=20,
        std_dev=2.0,
        mean=10.0,
    )
    result = BaselineComparator().compare([], valid)
    assert result.overall_status == "unknown"
    assert result.is_significant is True
