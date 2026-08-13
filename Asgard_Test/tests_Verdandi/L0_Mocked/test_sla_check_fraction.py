"""
Tests for SLAChecker.check_fraction — threshold-fraction SLI mode.

The threshold-fraction (good events / total events) is the sanctioned
shape for SLO use: fractions aggregate across time/hosts and weight by
traffic, unlike percentile point targets (DEEPTHINK_04). Includes the
minimum-traffic validity rule: min_events = 10 / (1 - target_fraction).
"""

import pytest

from Asgard.Verdandi.Analysis import SLAChecker, SLAConfig
from Asgard.Verdandi.Analysis.models.analysis_models import SLAStatus


def _checker(threshold_ms: float = 200.0) -> SLAChecker:
    return SLAChecker(SLAConfig(threshold_ms=threshold_ms))


class TestCheckFraction:
    def test_compliant_fraction(self):
        # 990 good + 10 bad = 0.99 exactly, target 0.99, ample traffic
        data = [100.0] * 990 + [500.0] * 10
        result = _checker().check_fraction(data, target_fraction=0.99)
        assert result.good_events == 990
        assert result.total_events == 1000
        assert result.good_fraction == 0.99
        assert result.status == SLAStatus.COMPLIANT
        assert result.insufficient_traffic is False
        assert result.violations == []

    def test_breached_fraction(self):
        data = [100.0] * 900 + [500.0] * 100
        result = _checker().check_fraction(data, target_fraction=0.99)
        assert result.status == SLAStatus.BREACHED
        assert any("below target" in v for v in result.violations)

    def test_minimum_traffic_rule(self):
        # 10 / (1 - 0.999) = 10_000 events required
        data = [100.0] * 100
        result = _checker().check_fraction(data, target_fraction=0.999)
        assert result.minimum_events_required == 10000
        assert result.insufficient_traffic is True
        # Insufficient traffic is never confidently clean
        assert result.status == SLAStatus.WARNING
        assert any("Insufficient traffic" in v for v in result.violations)

    def test_insufficient_traffic_does_not_mask_breach(self):
        # Breach with too little traffic stays BREACHED, not WARNING
        data = [500.0] * 5 + [100.0] * 5
        result = _checker().check_fraction(data, target_fraction=0.99)
        assert result.status == SLAStatus.BREACHED
        assert result.insufficient_traffic is True

    def test_threshold_override(self):
        data = [100.0, 300.0]
        result = _checker(200.0).check_fraction(
            data, threshold_ms=350.0, target_fraction=0.5
        )
        assert result.good_events == 2
        assert result.threshold_ms == 350.0

    def test_boundary_value_is_good(self):
        result = _checker(200.0).check_fraction([200.0], target_fraction=0.5)
        assert result.good_events == 1

    def test_empty_dataset_raises(self):
        with pytest.raises(ValueError):
            _checker().check_fraction([], target_fraction=0.99)

    @pytest.mark.parametrize("target", [0.0, 1.0, -0.1, 1.5])
    def test_invalid_target_fraction_raises(self, target):
        with pytest.raises(ValueError):
            _checker().check_fraction([100.0], target_fraction=target)

    def test_deterministic(self):
        data = [100.0] * 50 + [900.0] * 3
        a = _checker().check_fraction(data, target_fraction=0.9)
        b = _checker().check_fraction(data, target_fraction=0.9)
        assert a == b
