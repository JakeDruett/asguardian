"""
Unit tests for CacheMetricsCalculator.
"""

import pytest

from Asgard.Verdandi.Cache import CacheMetricsCalculator


class TestCacheMetricsCalculator:
    """Tests for CacheMetricsCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = CacheMetricsCalculator()

    def test_analyze_basic(self):
        """Test basic cache analysis."""
        result = self.calculator.analyze(hits=950, misses=50)

        assert result.total_requests == 1000
        assert result.hits == 950
        assert result.misses == 50
        assert result.hit_rate_percent == 95.0
        assert result.miss_rate_percent == 5.0
        assert result.status == "excellent"

    def test_analyze_with_latency(self):
        """Test cache analysis with latency metrics."""
        result = self.calculator.analyze(
            hits=950,
            misses=50,
            avg_hit_latency_ms=5.0,
            avg_miss_latency_ms=100.0,
        )

        assert result.avg_hit_latency_ms == 5.0
        assert result.avg_miss_latency_ms == 100.0
        assert result.latency_savings_ms == pytest.approx((100.0 - 5.0) * 950, abs=0.1)

    def test_analyze_with_size(self):
        """Test cache analysis with size metrics."""
        result = self.calculator.analyze(
            hits=950,
            misses=50,
            size_bytes=800_000_000,
            max_size_bytes=1_000_000_000,
        )

        assert result.size_bytes == 800_000_000
        assert result.max_size_bytes == 1_000_000_000
        assert result.fill_percent == 80.0

    def test_calculate_hit_rate(self):
        """Test hit rate calculation."""
        hit_rate = self.calculator.calculate_hit_rate(hits=850, total=1000)

        assert hit_rate == 85.0

    def test_calculate_hit_rate_zero_total(self):
        """Test hit rate with zero total requests."""
        hit_rate = self.calculator.calculate_hit_rate(hits=100, total=0)

        assert hit_rate == 0.0

    def test_status_excellent(self):
        """Test excellent status determination."""
        result = self.calculator.analyze(hits=970, misses=30)

        assert result.status == "excellent"
        assert result.hit_rate_percent >= 95.0

    def test_status_good(self):
        """Test good status determination."""
        result = self.calculator.analyze(hits=900, misses=100)

        assert result.status == "good"
        assert 85.0 <= result.hit_rate_percent < 95.0

    def test_status_fair(self):
        """Test fair status determination."""
        result = self.calculator.analyze(hits=750, misses=250)

        assert result.status == "fair"
        assert 70.0 <= result.hit_rate_percent < 85.0

    def test_status_poor(self):
        """Test poor status determination."""
        result = self.calculator.analyze(hits=600, misses=400)

        assert result.status == "poor"
        assert result.hit_rate_percent < 70.0

    def test_calculate_efficiency_basic(self):
        """Test efficiency calculation."""
        metrics = self.calculator.analyze(
            hits=950,
            misses=50,
            size_bytes=500_000_000,
            max_size_bytes=1_000_000_000,
            avg_hit_latency_ms=5.0,
            avg_miss_latency_ms=100.0,
        )

        efficiency = self.calculator.calculate_efficiency(metrics)

        assert efficiency.efficiency_score > 80
        assert efficiency.hit_rate_percent == 95.0
        assert efficiency.latency_improvement_factor == 20.0

    def test_calculate_efficiency_low_fill(self):
        """Test efficiency with low cache fill."""
        metrics = self.calculator.analyze(
            hits=850,
            misses=150,
            size_bytes=300_000_000,
            max_size_bytes=1_000_000_000,
        )

        efficiency = self.calculator.calculate_efficiency(metrics)

        assert efficiency.memory_efficiency_percent < 100

    def test_calculate_efficiency_high_fill(self):
        """Test efficiency with high cache fill."""
        metrics = self.calculator.analyze(
            hits=900,
            misses=100,
            size_bytes=980_000_000,
            max_size_bytes=1_000_000_000,
        )

        efficiency = self.calculator.calculate_efficiency(metrics)

        assert efficiency.memory_efficiency_percent > 85

    def test_recommendations_low_hit_rate(self):
        """Test recommendations for low hit rate."""
        result = self.calculator.analyze(hits=650, misses=350)

        assert any("hit rate" in rec.lower() or "cache size" in rec.lower() for rec in result.recommendations)

    def test_recommendations_cache_full(self):
        """Test recommendations when cache is nearly full."""
        result = self.calculator.analyze(
            hits=900,
            misses=100,
            size_bytes=980_000_000,
            max_size_bytes=1_000_000_000,
        )

        assert any("full" in rec.lower() or "size" in rec.lower() for rec in result.recommendations)

    def test_recommendations_low_utilization(self):
        """Test recommendations for low cache utilization."""
        result = self.calculator.analyze(
            hits=900,
            misses=100,
            size_bytes=200_000_000,
            max_size_bytes=1_000_000_000,
        )

        assert any("utilization" in rec.lower() or "low" in rec.lower() for rec in result.recommendations)

    def test_recommendations_slow_hit_latency(self):
        """Test recommendations when hit latency is relatively high."""
        result = self.calculator.analyze(
            hits=900,
            misses=100,
            avg_hit_latency_ms=60.0,
            avg_miss_latency_ms=100.0,
        )

        assert any("latency" in rec.lower() for rec in result.recommendations)

    def test_no_recommendations_excellent(self):
        """Test no recommendations for excellent cache."""
        result = self.calculator.analyze(
            hits=970,
            misses=30,
            size_bytes=600_000_000,
            max_size_bytes=1_000_000_000,
            avg_hit_latency_ms=5.0,
            avg_miss_latency_ms=100.0,
        )

        assert len(result.recommendations) == 0

    def test_zero_requests(self):
        """Test analysis with zero requests."""
        result = self.calculator.analyze(hits=0, misses=0)

        assert result.total_requests == 0
        assert result.hit_rate_percent == 0.0

    def test_all_hits(self):
        """Test analysis with all hits."""
        result = self.calculator.analyze(hits=1000, misses=0)

        assert result.hit_rate_percent == 100.0
        assert result.miss_rate_percent == 0.0

    def test_all_misses(self):
        """Test analysis with all misses."""
        result = self.calculator.analyze(hits=0, misses=1000)

        assert result.hit_rate_percent == 0.0
        assert result.miss_rate_percent == 100.0

    def test_rounding_precision(self):
        """Test that values are rounded to 2 decimal places."""
        result = self.calculator.analyze(
            hits=667,
            misses=333,
            avg_hit_latency_ms=5.123,
            avg_miss_latency_ms=100.456,
        )

        assert isinstance(result.hit_rate_percent, float)
        assert isinstance(result.miss_rate_percent, float)

    def test_constant_thresholds(self):
        """Test that threshold constants are correct."""
        assert CacheMetricsCalculator.EXCELLENT_THRESHOLD == 95.0
        assert CacheMetricsCalculator.GOOD_THRESHOLD == 85.0
        assert CacheMetricsCalculator.FAIR_THRESHOLD == 70.0
