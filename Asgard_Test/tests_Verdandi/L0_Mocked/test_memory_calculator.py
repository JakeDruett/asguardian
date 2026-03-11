"""
Unit tests for MemoryMetricsCalculator.
"""

import pytest

from Asgard.Verdandi.System import MemoryMetricsCalculator


class TestMemoryMetricsCalculator:
    """Tests for MemoryMetricsCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = MemoryMetricsCalculator()

    def test_analyze_basic(self):
        """Test basic memory analysis."""
        result = self.calculator.analyze(
            used_bytes=8_000_000_000,
            total_bytes=16_000_000_000,
        )

        assert result.total_bytes == 16_000_000_000
        assert result.used_bytes == 8_000_000_000
        assert result.available_bytes == 8_000_000_000
        assert result.usage_percent == 50.0
        assert result.status == "healthy"

    def test_analyze_with_swap(self):
        """Test memory analysis with swap space."""
        result = self.calculator.analyze(
            used_bytes=8_000_000_000,
            total_bytes=16_000_000_000,
            swap_used_bytes=1_000_000_000,
            swap_total_bytes=4_000_000_000,
        )

        assert result.swap_total_bytes == 4_000_000_000
        assert result.swap_used_bytes == 1_000_000_000
        assert result.swap_percent == 25.0

    def test_analyze_no_swap(self):
        """Test memory analysis without swap space."""
        result = self.calculator.analyze(
            used_bytes=8_000_000_000,
            total_bytes=16_000_000_000,
        )

        assert result.swap_total_bytes is None
        assert result.swap_used_bytes is None
        assert result.swap_percent is None

    def test_status_healthy(self):
        """Test healthy status determination."""
        result = self.calculator.analyze(
            used_bytes=10_000_000_000,
            total_bytes=16_000_000_000,
        )

        assert result.status == "healthy"
        assert result.usage_percent < 80.0

    def test_status_warning(self):
        """Test warning status determination."""
        result = self.calculator.analyze(
            used_bytes=13_000_000_000,
            total_bytes=16_000_000_000,
        )

        assert result.status == "warning"
        assert 80.0 <= result.usage_percent < 95.0

    def test_status_critical(self):
        """Test critical status determination."""
        result = self.calculator.analyze(
            used_bytes=15_500_000_000,
            total_bytes=16_000_000_000,
        )

        assert result.status == "critical"
        assert result.usage_percent >= 95.0

    def test_status_warning_high_swap(self):
        """Test warning status when swap usage is high."""
        result = self.calculator.analyze(
            used_bytes=10_000_000_000,
            total_bytes=16_000_000_000,
            swap_used_bytes=2_200_000_000,
            swap_total_bytes=4_000_000_000,
        )

        assert result.status == "warning"
        assert result.swap_percent > 50

    def test_calculate_usage_percent(self):
        """Test usage percentage calculation."""
        usage = self.calculator.calculate_usage_percent(
            used_bytes=6_000_000_000,
            total_bytes=16_000_000_000,
        )

        assert usage == 37.5

    def test_calculate_usage_percent_zero_total(self):
        """Test usage percentage with zero total bytes."""
        usage = self.calculator.calculate_usage_percent(
            used_bytes=1_000_000_000,
            total_bytes=0,
        )

        assert usage == 0.0

    def test_bytes_to_human_readable_bytes(self):
        """Test conversion to human-readable format (bytes)."""
        result = self.calculator.bytes_to_human_readable(512)
        assert "512" in result and "B" in result

    def test_bytes_to_human_readable_kb(self):
        """Test conversion to human-readable format (KB)."""
        result = self.calculator.bytes_to_human_readable(5120)
        assert "5.00 KB" == result

    def test_bytes_to_human_readable_mb(self):
        """Test conversion to human-readable format (MB)."""
        result = self.calculator.bytes_to_human_readable(5_242_880)
        assert "5.00 MB" == result

    def test_bytes_to_human_readable_gb(self):
        """Test conversion to human-readable format (GB)."""
        result = self.calculator.bytes_to_human_readable(5_368_709_120)
        assert "5.00 GB" == result

    def test_bytes_to_human_readable_tb(self):
        """Test conversion to human-readable format (TB)."""
        result = self.calculator.bytes_to_human_readable(5_497_558_138_880)
        assert "5.00 TB" == result

    def test_recommendations_critical(self):
        """Test recommendations for critical memory usage."""
        result = self.calculator.analyze(
            used_bytes=15_500_000_000,
            total_bytes=16_000_000_000,
        )

        assert len(result.recommendations) > 0
        assert any("critical" in rec.lower() for rec in result.recommendations)

    def test_recommendations_warning(self):
        """Test recommendations for warning memory usage."""
        result = self.calculator.analyze(
            used_bytes=13_000_000_000,
            total_bytes=16_000_000_000,
        )

        assert len(result.recommendations) > 0
        assert any("elevated" in rec.lower() for rec in result.recommendations)

    def test_recommendations_high_swap(self):
        """Test recommendations for high swap usage."""
        result = self.calculator.analyze(
            used_bytes=10_000_000_000,
            total_bytes=16_000_000_000,
            swap_used_bytes=2_500_000_000,
            swap_total_bytes=4_000_000_000,
        )

        assert any("swap" in rec.lower() for rec in result.recommendations)

    def test_recommendations_very_high_swap(self):
        """Test recommendations for very high swap usage."""
        result = self.calculator.analyze(
            used_bytes=10_000_000_000,
            total_bytes=16_000_000_000,
            swap_used_bytes=3_500_000_000,
            swap_total_bytes=4_000_000_000,
        )

        recommendations_text = " ".join(result.recommendations).lower()
        assert "swap" in recommendations_text
        assert len(result.recommendations) >= 2

    def test_no_recommendations_healthy(self):
        """Test no recommendations for healthy memory state."""
        result = self.calculator.analyze(
            used_bytes=8_000_000_000,
            total_bytes=16_000_000_000,
            swap_used_bytes=500_000_000,
            swap_total_bytes=4_000_000_000,
        )

        assert len(result.recommendations) == 0

    def test_rounding_precision(self):
        """Test that percentages are rounded to 2 decimal places."""
        result = self.calculator.analyze(
            used_bytes=7_123_456_789,
            total_bytes=16_000_000_000,
        )

        assert result.usage_percent == pytest.approx(44.52, abs=0.01)

    def test_swap_rounding_precision(self):
        """Test that swap percentage is rounded to 2 decimal places."""
        result = self.calculator.analyze(
            used_bytes=8_000_000_000,
            total_bytes=16_000_000_000,
            swap_used_bytes=1_234_567_890,
            swap_total_bytes=4_000_000_000,
        )

        assert result.swap_percent == pytest.approx(30.86, abs=0.01)

    def test_zero_used_memory(self):
        """Test analysis with zero used memory."""
        result = self.calculator.analyze(
            used_bytes=0,
            total_bytes=16_000_000_000,
        )

        assert result.usage_percent == 0.0
        assert result.available_bytes == 16_000_000_000
        assert result.status == "healthy"

    def test_full_memory_usage(self):
        """Test analysis with full memory usage."""
        result = self.calculator.analyze(
            used_bytes=16_000_000_000,
            total_bytes=16_000_000_000,
        )

        assert result.usage_percent == 100.0
        assert result.available_bytes == 0
        assert result.status == "critical"

    def test_zero_swap_total(self):
        """Test analysis with zero swap total."""
        result = self.calculator.analyze(
            used_bytes=8_000_000_000,
            total_bytes=16_000_000_000,
            swap_used_bytes=0,
            swap_total_bytes=0,
        )

        assert result.swap_percent == 0.0

    def test_constant_thresholds(self):
        """Test that threshold constants are correct."""
        assert MemoryMetricsCalculator.WARNING_THRESHOLD == 80.0
        assert MemoryMetricsCalculator.CRITICAL_THRESHOLD == 95.0

    def test_edge_case_at_warning_threshold(self):
        """Test status exactly at warning threshold."""
        result = self.calculator.analyze(
            used_bytes=12_800_000_000,
            total_bytes=16_000_000_000,
        )

        assert result.usage_percent == 80.0
        assert result.status == "warning"

    def test_edge_case_at_critical_threshold(self):
        """Test status exactly at critical threshold."""
        result = self.calculator.analyze(
            used_bytes=15_200_000_000,
            total_bytes=16_000_000_000,
        )

        assert result.usage_percent == 95.0
        assert result.status == "critical"

    def test_edge_case_at_swap_threshold(self):
        """Test status exactly at swap warning threshold."""
        result = self.calculator.analyze(
            used_bytes=10_000_000_000,
            total_bytes=16_000_000_000,
            swap_used_bytes=2_000_000_000,
            swap_total_bytes=4_000_000_000,
        )

        assert result.swap_percent == 50.0
