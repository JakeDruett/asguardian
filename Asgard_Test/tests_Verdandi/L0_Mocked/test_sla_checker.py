"""
Unit tests for SLAChecker.
"""

import pytest

from Asgard.Verdandi.Analysis import SLAChecker
from Asgard.Verdandi.Analysis.models.analysis_models import SLAConfig, SLAStatus


class TestSLAChecker:
    """Tests for SLAChecker."""

    def setup_method(self):
        """Set up test fixtures."""
        config = SLAConfig(threshold_ms=200.0)
        self.checker = SLAChecker(config)

    def test_check_empty_raises(self):
        """Test that empty dataset raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            self.checker.check([])

    def test_check_compliant(self):
        """Test SLA check with compliant performance."""
        response_times = [50, 75, 100, 125, 150, 80, 90, 110, 120, 130]

        result = self.checker.check(response_times)

        assert result.status == SLAStatus.COMPLIANT
        assert result.percentile_value < result.threshold_ms
        assert len(result.violations) == 0

    def test_check_warning(self):
        """Test SLA check with warning threshold."""
        response_times = [150, 160, 170, 180, 185, 190, 175, 165, 155, 195]

        result = self.checker.check(response_times)

        assert result.status == SLAStatus.WARNING
        assert result.margin_percent < 10

    def test_check_breached(self):
        """Test SLA check with breached threshold."""
        response_times = [200, 210, 220, 230, 240, 205, 215, 225, 235, 250]

        result = self.checker.check(response_times)

        assert result.status == SLAStatus.BREACHED
        assert result.percentile_value > result.threshold_ms
        assert len(result.violations) > 0

    def test_check_with_errors(self):
        """Test SLA check with error rate."""
        config = SLAConfig(threshold_ms=200.0, error_rate_threshold=1.0)
        checker = SLAChecker(config)

        response_times = [50, 75, 100, 125, 150]

        result = checker.check(
            response_times,
            error_count=10,
            total_requests=100,
        )

        assert result.error_rate_actual == 10.0
        assert result.status == SLAStatus.BREACHED

    def test_check_with_availability(self):
        """Test SLA check with availability metric."""
        config = SLAConfig(threshold_ms=200.0, availability_target=99.9)
        checker = SLAChecker(config)

        response_times = [50, 75, 100, 125, 150]

        result = checker.check(
            response_times,
            downtime_seconds=100,
            total_seconds=10000,
        )

        assert result.availability_actual == 99.0
        assert result.status == SLAStatus.BREACHED

    def test_custom_percentile(self):
        """Test SLA check with custom percentile."""
        config = SLAConfig(target_percentile=99.0, threshold_ms=250.0)
        checker = SLAChecker(config)

        response_times = list(range(1, 101))

        result = checker.check(response_times)

        assert result.percentile_target == 99.0
        assert 98 <= result.percentile_value <= 100

    def test_margin_calculation(self):
        """Test margin percentage calculation."""
        response_times = [50, 75, 100, 125, 150]

        result = self.checker.check(response_times)

        expected_margin = ((200.0 - result.percentile_value) / 200.0) * 100
        assert result.margin_percent == pytest.approx(expected_margin, abs=0.1)

    def test_check_multiple_windows(self):
        """Test checking SLA across multiple windows."""
        windows = [
            [50, 75, 100, 125, 150],
            [200, 210, 220, 230, 240],
            [80, 90, 100, 110, 120],
        ]

        results = self.checker.check_multiple_windows(windows)

        assert len(results) == 3
        assert results[0].status == SLAStatus.COMPLIANT
        assert results[1].status == SLAStatus.BREACHED
        assert results[2].status == SLAStatus.COMPLIANT

    def test_calculate_compliance_rate(self):
        """Test compliance rate calculation."""
        windows = [
            [50, 75, 100, 125, 150],
            [80, 90, 100, 110, 120],
            [70, 85, 95, 105, 115],
        ]

        results = self.checker.check_multiple_windows(windows)
        compliance_rate = self.checker.calculate_compliance_rate(results)

        assert compliance_rate == 100.0

    def test_calculate_compliance_rate_mixed(self):
        """Test compliance rate with mixed results."""
        windows = [
            [50, 75, 100, 125, 150],
            [200, 210, 220, 230, 240],
            [80, 90, 100, 110, 120],
        ]

        results = self.checker.check_multiple_windows(windows)
        compliance_rate = self.checker.calculate_compliance_rate(results)

        assert compliance_rate == pytest.approx(66.67, abs=0.1)

    def test_calculate_compliance_rate_empty(self):
        """Test compliance rate with no results."""
        compliance_rate = self.checker.calculate_compliance_rate([])

        assert compliance_rate == 100.0

    def test_violations_list(self):
        """Test that violations are properly listed."""
        config = SLAConfig(
            threshold_ms=200.0,
            availability_target=99.9,
            error_rate_threshold=1.0,
        )
        checker = SLAChecker(config)

        response_times = [200, 210, 220, 230, 240]

        result = checker.check(
            response_times,
            error_count=5,
            total_requests=100,
            downtime_seconds=100,
            total_seconds=10000,
        )

        assert len(result.violations) == 3
        assert any("response time" in v.lower() for v in result.violations)
        assert any("availability" in v.lower() for v in result.violations)
        assert any("error rate" in v.lower() for v in result.violations)

    def test_single_value(self):
        """Test SLA check with single value."""
        response_times = [100.0]

        result = self.checker.check(response_times)

        assert result.percentile_value == 100.0
        assert result.status == SLAStatus.COMPLIANT

    def test_config_frustration_multiplier(self):
        """Test SLA config with custom frustration multiplier."""
        config = SLAConfig(threshold_ms=100.0, warning_threshold_percent=85.0)
        checker = SLAChecker(config)

        response_times = [80, 85, 90, 92, 88]

        result = checker.check(response_times)

        assert result.status == SLAStatus.WARNING
