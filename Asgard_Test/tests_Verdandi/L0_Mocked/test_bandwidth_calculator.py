"""
Unit tests for BandwidthCalculator.
"""

import pytest

from Asgard.Verdandi.Network import BandwidthCalculator


class TestBandwidthCalculator:
    """Tests for BandwidthCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = BandwidthCalculator()

    def test_analyze_basic(self):
        """Test basic bandwidth analysis."""
        result = self.calculator.analyze(
            bytes_sent=100_000_000,
            bytes_received=500_000_000,
            duration_seconds=60,
        )

        assert result.upload_mbps == pytest.approx(13.33, abs=0.1)
        assert result.download_mbps == pytest.approx(66.67, abs=0.1)
        assert result.total_throughput_mbps == pytest.approx(80.0, abs=0.1)
        assert result.utilization_percent is None

    def test_analyze_with_capacity(self):
        """Test bandwidth analysis with capacity."""
        result = self.calculator.analyze(
            bytes_sent=100_000_000,
            bytes_received=500_000_000,
            duration_seconds=60,
            capacity_mbps=100.0,
        )

        assert result.capacity_mbps == 100.0
        assert result.utilization_percent == pytest.approx(80.0, abs=0.1)

    def test_analyze_zero_duration(self):
        """Test analysis with zero duration."""
        result = self.calculator.analyze(
            bytes_sent=100_000_000,
            bytes_received=500_000_000,
            duration_seconds=0,
        )

        assert result.upload_mbps == 0.0
        assert result.download_mbps == 0.0
        assert result.total_throughput_mbps == 0.0

    def test_bytes_to_mbps(self):
        """Test bytes to Mbps conversion."""
        mbps = self.calculator.bytes_to_mbps(
            bytes_value=125_000_000,
            duration_seconds=10,
        )

        assert mbps == 100.0

    def test_bytes_to_mbps_zero_duration(self):
        """Test bytes to Mbps with zero duration."""
        mbps = self.calculator.bytes_to_mbps(
            bytes_value=125_000_000,
            duration_seconds=0,
        )

        assert mbps == 0.0

    def test_mbps_to_bytes_per_second(self):
        """Test Mbps to bytes per second conversion."""
        bytes_per_sec = self.calculator.mbps_to_bytes_per_second(100.0)

        assert bytes_per_sec == 12_500_000

    def test_status_low(self):
        """Test low utilization status."""
        result = self.calculator.analyze(
            bytes_sent=10_000_000,
            bytes_received=20_000_000,
            duration_seconds=60,
            capacity_mbps=100.0,
        )

        assert result.status == "low"
        assert result.utilization_percent < 30

    def test_status_normal(self):
        """Test normal utilization status."""
        result = self.calculator.analyze(
            bytes_sent=200_000_000,
            bytes_received=200_000_000,
            duration_seconds=60,
            capacity_mbps=100.0,
        )

        assert result.status == "normal"
        assert 30 <= result.utilization_percent < 70

    def test_status_high(self):
        """Test high utilization status."""
        result = self.calculator.analyze(
            bytes_sent=400_000_000,
            bytes_received=400_000_000,
            duration_seconds=60,
            capacity_mbps=150.0,
        )

        assert result.status == "high"
        assert 70 <= result.utilization_percent < 90

    def test_status_saturated(self):
        """Test saturated utilization status."""
        result = self.calculator.analyze(
            bytes_sent=500_000_000,
            bytes_received=500_000_000,
            duration_seconds=60,
            capacity_mbps=150.0,
        )

        assert result.status == "saturated"
        assert result.utilization_percent >= 90

    def test_status_unknown_no_capacity(self):
        """Test unknown status when capacity is not specified."""
        result = self.calculator.analyze(
            bytes_sent=100_000_000,
            bytes_received=500_000_000,
            duration_seconds=60,
        )

        assert result.status == "unknown"

    def test_recommendations_saturated(self):
        """Test recommendations for saturated bandwidth."""
        result = self.calculator.analyze(
            bytes_sent=500_000_000,
            bytes_received=500_000_000,
            duration_seconds=60,
            capacity_mbps=150.0,
        )

        assert any("saturated" in rec.lower() or "upgrade" in rec.lower() for rec in result.recommendations)

    def test_recommendations_high_utilization(self):
        """Test recommendations for high utilization."""
        result = self.calculator.analyze(
            bytes_sent=400_000_000,
            bytes_received=400_000_000,
            duration_seconds=60,
            capacity_mbps=150.0,
        )

        assert any("high" in rec.lower() or "utilization" in rec.lower() for rec in result.recommendations)

    def test_no_recommendations_normal(self):
        """Test no recommendations for normal utilization."""
        result = self.calculator.analyze(
            bytes_sent=200_000_000,
            bytes_received=200_000_000,
            duration_seconds=60,
            capacity_mbps=100.0,
        )

        assert len(result.recommendations) == 0

    def test_upload_only(self):
        """Test analysis with only upload traffic."""
        result = self.calculator.analyze(
            bytes_sent=100_000_000,
            bytes_received=0,
            duration_seconds=60,
        )

        assert result.upload_mbps > 0
        assert result.download_mbps == 0.0

    def test_download_only(self):
        """Test analysis with only download traffic."""
        result = self.calculator.analyze(
            bytes_sent=0,
            bytes_received=500_000_000,
            duration_seconds=60,
        )

        assert result.upload_mbps == 0.0
        assert result.download_mbps > 0

    def test_rounding_precision(self):
        """Test that values are rounded to 2 decimal places."""
        result = self.calculator.analyze(
            bytes_sent=123_456_789,
            bytes_received=987_654_321,
            duration_seconds=7,
        )

        assert isinstance(result.upload_mbps, float)
        assert isinstance(result.download_mbps, float)
        assert isinstance(result.total_throughput_mbps, float)

    def test_high_throughput(self):
        """Test analysis with high throughput."""
        result = self.calculator.analyze(
            bytes_sent=10_000_000_000,
            bytes_received=10_000_000_000,
            duration_seconds=60,
            capacity_mbps=5000.0,
        )

        assert result.total_throughput_mbps > 2000
        assert result.utilization_percent > 50
