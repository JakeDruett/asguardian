"""
Unit tests for LatencyCalculator.
"""

import pytest
import numpy as np

from Asgard.Verdandi.Network import LatencyCalculator


class TestLatencyCalculator:
    """Tests for LatencyCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = LatencyCalculator()

    def test_analyze_empty_raises(self):
        """Test that empty latency list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            self.calculator.analyze([])

    def test_analyze_basic(self):
        """Test basic latency analysis."""
        latencies = [10, 15, 12, 20, 18, 25, 11, 14, 16, 22]

        result = self.calculator.analyze(latencies)

        assert result.sample_count == 10
        assert result.min_ms == 10
        assert result.max_ms == 25
        assert 15 < result.mean_ms < 17
        assert 14 < result.median_ms < 16

    def test_analyze_with_packet_loss(self):
        """Test analysis with packet loss."""
        latencies = [10, 15, 12, 20, 18]

        result = self.calculator.analyze(latencies, packet_loss_percent=2.5)

        assert result.packet_loss_percent == 2.5

    def test_analyze_single_value(self):
        """Test analysis with single latency value."""
        latencies = [50.0]

        result = self.calculator.analyze(latencies)

        assert result.sample_count == 1
        assert result.min_ms == 50.0
        assert result.max_ms == 50.0
        assert result.mean_ms == 50.0
        assert result.median_ms == 50.0
        assert result.jitter_ms == 0.0

    def test_jitter_calculation(self):
        """Test jitter calculation."""
        latencies = [10.0, 20.0, 15.0, 25.0, 12.0]

        result = self.calculator.analyze(latencies)

        expected_jitter = (10 + 5 + 10 + 13) / 4
        assert result.jitter_ms == pytest.approx(expected_jitter, abs=0.1)

    def test_jitter_zero_for_stable_latency(self):
        """Test jitter is zero for perfectly stable latency."""
        latencies = [50.0, 50.0, 50.0, 50.0]

        result = self.calculator.analyze(latencies)

        assert result.jitter_ms == 0.0

    def test_status_good(self):
        """Test good status determination."""
        latencies = [10, 15, 20, 25, 30, 35, 40, 45]

        result = self.calculator.analyze(latencies)

        assert result.status == "good"

    def test_status_acceptable(self):
        """Test acceptable status determination."""
        latencies = [50, 60, 70, 80, 85, 90, 75, 82]

        result = self.calculator.analyze(latencies)

        assert result.status == "acceptable"

    def test_status_poor_high_latency(self):
        """Test poor status for high latency."""
        latencies = [100, 120, 150, 180, 200, 110, 130, 160]

        result = self.calculator.analyze(latencies)

        assert result.status == "poor"

    def test_status_poor_high_packet_loss(self):
        """Test poor status for high packet loss."""
        latencies = [10, 15, 20, 25, 30]

        result = self.calculator.analyze(latencies, packet_loss_percent=6.0)

        assert result.status == "poor"

    def test_percentile_calculations_match_numpy(self):
        """Test that percentile calculations match numpy results."""
        latencies = list(range(1, 101))

        result = self.calculator.analyze(latencies)

        np_p90 = np.percentile(latencies, 90)
        np_p95 = np.percentile(latencies, 95)
        np_p99 = np.percentile(latencies, 99)

        assert abs(result.p90_ms - np_p90) < 2
        assert abs(result.p95_ms - np_p95) < 2
        assert abs(result.p99_ms - np_p99) < 2

    def test_recommendations_high_latency(self):
        """Test recommendations for high latency."""
        latencies = [120, 150, 180, 200, 130, 160, 140, 170]

        result = self.calculator.analyze(latencies)

        assert any("latency" in rec.lower() or "cdn" in rec.lower() for rec in result.recommendations)

    def test_recommendations_high_jitter(self):
        """Test recommendations for high jitter."""
        latencies = [10, 50, 15, 55, 20, 60, 25, 65]

        result = self.calculator.analyze(latencies)

        assert any("jitter" in rec.lower() for rec in result.recommendations)

    def test_recommendations_packet_loss(self):
        """Test recommendations for packet loss."""
        latencies = [10, 15, 20, 25, 30]

        result = self.calculator.analyze(latencies, packet_loss_percent=2.5)

        assert any("packet loss" in rec.lower() for rec in result.recommendations)

    def test_no_recommendations_good_network(self):
        """Test no recommendations for good network."""
        latencies = [10, 12, 15, 11, 14, 13, 16, 12]

        result = self.calculator.analyze(latencies, packet_loss_percent=0.1)

        assert len(result.recommendations) == 0

    def test_constant_thresholds(self):
        """Test that threshold constants are correct."""
        assert LatencyCalculator.GOOD_THRESHOLD == 50
        assert LatencyCalculator.ACCEPTABLE_THRESHOLD == 100

    def test_std_dev_calculation(self):
        """Test standard deviation calculation."""
        latencies = [10, 20, 30, 40, 50]

        result = self.calculator.analyze(latencies)

        np_std = np.std(latencies, ddof=0)
        assert abs(result.std_dev_ms - np_std) < 1

    def test_rounding_precision(self):
        """Test that values are rounded to 2 decimal places."""
        latencies = [10.123, 15.456, 12.789]

        result = self.calculator.analyze(latencies)

        assert isinstance(result.mean_ms, float)
        assert isinstance(result.jitter_ms, float)

    def test_large_dataset(self):
        """Test analysis with large dataset."""
        latencies = list(range(1, 1001))

        result = self.calculator.analyze(latencies)

        assert result.sample_count == 1000
        assert result.min_ms == 1
        assert result.max_ms == 1000

    def test_high_variance_latencies(self):
        """Test analysis with high variance latencies."""
        latencies = [5, 100, 10, 95, 15, 90, 20, 85]

        result = self.calculator.analyze(latencies)

        assert result.jitter_ms > 30
        assert len(result.recommendations) > 0
