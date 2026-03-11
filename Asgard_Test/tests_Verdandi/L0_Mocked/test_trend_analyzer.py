"""
Unit tests for TrendAnalyzer.
"""

import pytest
import numpy as np

from Asgard.Verdandi.Analysis import TrendAnalyzer
from Asgard.Verdandi.Analysis.models.analysis_models import TrendDirection


class TestTrendAnalyzer:
    """Tests for TrendAnalyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = TrendAnalyzer()

    def test_analyze_too_few_points_raises(self):
        """Test that less than 2 data points raises ValueError."""
        with pytest.raises(ValueError, match="at least 2"):
            self.analyzer.analyze([100])

    def test_analyze_improving_trend(self):
        """Test detection of improving trend (lower is better)."""
        values = [100, 95, 90, 85, 80, 75, 70, 65, 60, 55]

        result = self.analyzer.analyze(values, lower_is_better=True)

        assert result.direction == TrendDirection.IMPROVING
        assert result.slope < 0
        assert result.change_percent < 0

    def test_analyze_degrading_trend(self):
        """Test detection of degrading trend (lower is better)."""
        values = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95]

        result = self.analyzer.analyze(values, lower_is_better=True)

        assert result.direction == TrendDirection.DEGRADING
        assert result.slope > 0
        assert result.change_percent > 0

    def test_analyze_stable_trend(self):
        """Test detection of stable trend."""
        values = [100, 101, 99, 100, 101, 100, 99, 101, 100, 100]

        result = self.analyzer.analyze(values, lower_is_better=True)

        assert result.direction == TrendDirection.STABLE

    def test_analyze_higher_is_better(self):
        """Test trend analysis when higher values are better."""
        values = [50, 55, 60, 65, 70, 75, 80, 85, 90, 95]

        result = self.analyzer.analyze(values, lower_is_better=False)

        assert result.direction == TrendDirection.IMPROVING
        assert result.slope > 0

    def test_analyze_low_confidence(self):
        """Test trend with low confidence (noisy data)."""
        values = [50, 80, 45, 90, 55, 85, 60, 75, 65, 95]

        result = self.analyzer.analyze(values, lower_is_better=True)

        assert result.direction == TrendDirection.STABLE
        assert result.confidence < 0.7

    def test_linear_regression_accuracy(self):
        """Test linear regression calculation accuracy."""
        values = [10, 20, 30, 40, 50]

        result = self.analyzer.analyze(values)

        assert result.slope == 10.0
        assert result.confidence > 0.99

    def test_change_percent_calculation(self):
        """Test change percentage calculation."""
        values = [100, 110, 120, 130, 140, 150]

        result = self.analyzer.analyze(values)

        assert result.baseline_value == 100
        assert result.current_value == 150
        assert result.change_percent == 50.0

    def test_anomaly_detection(self):
        """Test anomaly detection in data."""
        values = [50, 52, 51, 53, 200, 52, 51, 53, 52, 51]

        result = self.analyzer.analyze(values)

        assert result.anomalies_detected > 0

    def test_no_anomalies_stable_data(self):
        """Test no anomalies in stable data."""
        values = [50, 51, 52, 51, 50, 52, 51, 50, 52, 51]

        result = self.analyzer.analyze(values)

        assert result.anomalies_detected == 0

    def test_compare_periods_improving(self):
        """Test period comparison showing improvement."""
        baseline = [100, 105, 95, 110, 90]
        current = [60, 65, 55, 70, 50]

        result = self.analyzer.compare_periods(baseline, current, lower_is_better=True)

        assert result.direction == TrendDirection.IMPROVING
        assert result.change_percent < 0

    def test_compare_periods_degrading(self):
        """Test period comparison showing degradation."""
        baseline = [50, 55, 45, 60, 40]
        current = [100, 105, 95, 110, 90]

        result = self.analyzer.compare_periods(baseline, current, lower_is_better=True)

        assert result.direction == TrendDirection.DEGRADING
        assert result.change_percent > 0

    def test_compare_periods_stable(self):
        """Test period comparison showing stable performance."""
        baseline = [100, 105, 95, 110, 90]
        current = [98, 103, 97, 102, 100]

        result = self.analyzer.compare_periods(baseline, current, lower_is_better=True)

        assert result.direction == TrendDirection.STABLE

    def test_custom_stability_threshold(self):
        """Test with custom stability threshold."""
        analyzer = TrendAnalyzer(stability_threshold=0.10)
        values = [100, 102, 104, 106, 108]

        result = analyzer.analyze(values)

        assert result.direction == TrendDirection.STABLE

    def test_custom_confidence_threshold(self):
        """Test with custom confidence threshold."""
        analyzer = TrendAnalyzer(confidence_threshold=0.9)
        values = [50, 80, 45, 90, 55, 85, 60, 75, 65, 95]

        result = analyzer.analyze(values)

        assert result.direction == TrendDirection.STABLE

    def test_zero_baseline(self):
        """Test change percentage when baseline is zero."""
        values = [0, 10, 20, 30, 40]

        result = self.analyzer.analyze(values)

        assert result.change_percent == 0.0

    def test_perfect_linear_trend(self):
        """Test with perfectly linear data."""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        result = self.analyzer.analyze(values, lower_is_better=False)

        assert result.confidence > 0.99
        assert result.direction == TrendDirection.IMPROVING

    def test_data_points_count(self):
        """Test that data points count is correct."""
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        result = self.analyzer.analyze(values)

        assert result.data_points == 10

    def test_period_seconds(self):
        """Test that period seconds is recorded."""
        values = [100, 95, 90, 85, 80]

        result = self.analyzer.analyze(values, period_seconds=300)

        assert result.period_seconds == 300

    def test_rounding_precision(self):
        """Test that slope and confidence are rounded appropriately."""
        values = [10.123, 20.456, 30.789, 40.234, 50.567]

        result = self.analyzer.analyze(values)

        assert isinstance(result.slope, float)
        assert isinstance(result.confidence, float)
        assert isinstance(result.change_percent, float)

    def test_regression_with_identical_values(self):
        """Test regression with all identical values."""
        values = [50, 50, 50, 50, 50]

        result = self.analyzer.analyze(values)

        assert result.slope == 0.0
        assert result.change_percent == 0.0
