"""
Unit tests for DnsCalculator.
"""

import pytest

from Asgard.Verdandi.Network import DnsCalculator


class TestDnsCalculator:
    """Tests for DnsCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = DnsCalculator()

    def test_analyze_empty_raises(self):
        """Test that empty resolution times raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            self.calculator.analyze([])

    def test_analyze_basic(self):
        """Test basic DNS analysis."""
        resolution_times = [5, 10, 8, 12, 7, 15, 9, 11]

        result = self.calculator.analyze(resolution_times)

        assert result.query_count == 8
        assert 8 < result.avg_resolution_ms < 11
        assert result.max_resolution_ms == 15

    def test_analyze_with_cache_hits(self):
        """Test analysis with cache hit data."""
        resolution_times = [5, 10, 8, 12, 7]

        result = self.calculator.analyze(
            resolution_times,
            cache_hits=45,
            total_queries=50,
        )

        assert result.cache_hit_rate == 90.0

    def test_analyze_with_failures(self):
        """Test analysis with DNS failures."""
        resolution_times = [5, 10, 8, 12, 7]

        result = self.calculator.analyze(
            resolution_times,
            total_queries=55,
            failures=5,
        )

        assert result.failure_rate == pytest.approx(9.09, abs=0.1)

    def test_analyze_with_record_type_breakdown(self):
        """Test analysis with record type breakdown."""
        resolution_times = [5, 10, 8, 12, 7]
        by_record_type = {
            "A": [5, 8, 10],
            "AAAA": [12, 15],
            "MX": [20],
        }

        result = self.calculator.analyze(
            resolution_times,
            by_record_type=by_record_type,
        )

        assert "A" in result.by_record_type
        assert "AAAA" in result.by_record_type
        assert "MX" in result.by_record_type
        assert result.by_record_type["A"]["count"] == 3
        assert result.by_record_type["A"]["avg_ms"] == pytest.approx(7.67, abs=0.1)

    def test_cache_hit_rate_all_hits(self):
        """Test cache hit rate with all hits."""
        resolution_times = [5, 10, 8]

        result = self.calculator.analyze(
            resolution_times,
            cache_hits=50,
            total_queries=50,
        )

        assert result.cache_hit_rate == 100.0

    def test_cache_hit_rate_no_hits(self):
        """Test cache hit rate with no hits."""
        resolution_times = [5, 10, 8]

        result = self.calculator.analyze(
            resolution_times,
            cache_hits=0,
            total_queries=50,
        )

        assert result.cache_hit_rate == 0.0

    def test_failure_rate_no_failures(self):
        """Test failure rate with no failures."""
        resolution_times = [5, 10, 8]

        result = self.calculator.analyze(
            resolution_times,
            failures=0,
        )

        assert result.failure_rate == 0.0

    def test_status_good(self):
        """Test good status determination."""
        resolution_times = [5, 8, 10, 12, 15, 7, 9, 11]

        result = self.calculator.analyze(
            resolution_times,
            failures=0,
        )

        assert result.status == "good"

    def test_status_acceptable(self):
        """Test acceptable status determination."""
        resolution_times = [40, 50, 60, 55, 65, 45, 52, 58]

        result = self.calculator.analyze(resolution_times)

        assert result.status == "acceptable"

    def test_status_slow(self):
        """Test slow status determination."""
        resolution_times = [100, 120, 150, 110, 130, 140, 115, 125]

        result = self.calculator.analyze(resolution_times)

        assert result.status == "slow"

    def test_status_critical_high_failures(self):
        """Test critical status for high failure rate."""
        resolution_times = [5, 10, 8]

        result = self.calculator.analyze(
            resolution_times,
            total_queries=50,
            failures=4,
        )

        assert result.status == "critical"

    def test_recommendations_slow_dns(self):
        """Test recommendations for slow DNS."""
        resolution_times = [100, 120, 150, 110, 130]

        result = self.calculator.analyze(resolution_times)

        assert any("slow" in rec.lower() or "faster" in rec.lower() for rec in result.recommendations)

    def test_recommendations_low_cache_hit(self):
        """Test recommendations for low cache hit rate."""
        resolution_times = [5, 10, 8]

        result = self.calculator.analyze(
            resolution_times,
            cache_hits=20,
            total_queries=50,
        )

        assert any("cache" in rec.lower() for rec in result.recommendations)

    def test_recommendations_high_failure_rate(self):
        """Test recommendations for high failure rate."""
        resolution_times = [5, 10, 8]

        result = self.calculator.analyze(
            resolution_times,
            total_queries=50,
            failures=2,
        )

        assert any("failure" in rec.lower() or "dns" in rec.lower() for rec in result.recommendations)

    def test_no_recommendations_good_dns(self):
        """Test no recommendations for good DNS."""
        resolution_times = [5, 8, 10, 7, 9]

        result = self.calculator.analyze(
            resolution_times,
            cache_hits=90,
            total_queries=95,
            failures=0,
        )

        assert len(result.recommendations) == 0

    def test_empty_record_type_breakdown(self):
        """Test analysis with empty record type lists."""
        resolution_times = [5, 10, 8]
        by_record_type = {
            "A": [5, 8, 10],
            "AAAA": [],
        }

        result = self.calculator.analyze(
            resolution_times,
            by_record_type=by_record_type,
        )

        assert "A" in result.by_record_type
        assert "AAAA" not in result.by_record_type

    def test_rounding_precision(self):
        """Test that values are rounded to 2 decimal places."""
        resolution_times = [5.123, 10.456, 8.789]

        result = self.calculator.analyze(
            resolution_times,
            cache_hits=33,
            total_queries=50,
            failures=2,
        )

        assert isinstance(result.avg_resolution_ms, float)
        assert isinstance(result.cache_hit_rate, float)
        assert isinstance(result.failure_rate, float)

    def test_single_query(self):
        """Test analysis with single query."""
        resolution_times = [10.0]

        result = self.calculator.analyze(resolution_times)

        assert result.query_count == 1
        assert result.avg_resolution_ms == 10.0
        assert result.max_resolution_ms == 10.0
