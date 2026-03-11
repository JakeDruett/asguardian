"""
Unit tests for EvictionAnalyzer.
"""

import pytest

from Asgard.Verdandi.Cache import EvictionAnalyzer


class TestEvictionAnalyzer:
    """Tests for EvictionAnalyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = EvictionAnalyzer()

    def test_analyze_basic(self):
        """Test basic eviction analysis."""
        result = self.analyzer.analyze(
            evictions=100,
            duration_seconds=3600,
            total_operations=10000,
        )

        assert result.total_evictions == 100
        assert result.eviction_rate_per_sec == pytest.approx(0.03, abs=0.01)
        assert result.eviction_percent == 1.0

    def test_analyze_with_reason_breakdown(self):
        """Test analysis with eviction reason breakdown."""
        result = self.analyzer.analyze(
            evictions=100,
            duration_seconds=3600,
            total_operations=10000,
            by_reason={"lru": 60, "ttl": 30, "size": 10},
        )

        assert result.by_reason == {"lru": 60, "ttl": 30, "size": 10}

    def test_analyze_with_entry_age(self):
        """Test analysis with average entry age."""
        result = self.analyzer.analyze(
            evictions=100,
            duration_seconds=3600,
            total_operations=10000,
            avg_entry_age_seconds=120.0,
        )

        assert result.avg_entry_age_seconds == 120.0

    def test_analyze_with_premature_evictions(self):
        """Test analysis with premature evictions."""
        result = self.analyzer.analyze(
            evictions=100,
            duration_seconds=3600,
            total_operations=10000,
            premature_evictions=40,
        )

        assert result.premature_evictions == 40

    def test_calculate_eviction_rate(self):
        """Test eviction rate calculation."""
        rate = self.analyzer.calculate_eviction_rate(
            evictions=100,
            duration_seconds=3600,
        )

        assert rate == pytest.approx(0.03, abs=0.01)

    def test_calculate_eviction_rate_zero_duration(self):
        """Test eviction rate with zero duration."""
        rate = self.analyzer.calculate_eviction_rate(
            evictions=100,
            duration_seconds=0,
        )

        assert rate == 0.0

    def test_status_normal(self):
        """Test normal status determination."""
        result = self.analyzer.analyze(
            evictions=50,
            duration_seconds=3600,
            total_operations=10000,
            premature_evictions=5,
        )

        assert result.status == "normal"

    def test_status_moderate(self):
        """Test moderate status determination."""
        result = self.analyzer.analyze(
            evictions=1200,
            duration_seconds=3600,
            total_operations=10000,
            premature_evictions=100,
        )

        assert result.status == "moderate"

    def test_status_high(self):
        """Test high status determination."""
        result = self.analyzer.analyze(
            evictions=2500,
            duration_seconds=3600,
            total_operations=10000,
            premature_evictions=300,
        )

        assert result.status == "high"

    def test_status_critical(self):
        """Test critical status for high premature evictions."""
        result = self.analyzer.analyze(
            evictions=1000,
            duration_seconds=3600,
            total_operations=10000,
            premature_evictions=350,
        )

        assert result.status == "critical"

    def test_recommendations_high_eviction_rate(self):
        """Test recommendations for high eviction rate."""
        result = self.analyzer.analyze(
            evictions=2500,
            duration_seconds=3600,
            total_operations=10000,
        )

        assert any("eviction rate" in rec.lower() or "cache size" in rec.lower() for rec in result.recommendations)

    def test_recommendations_premature_evictions(self):
        """Test recommendations for premature evictions."""
        result = self.analyzer.analyze(
            evictions=1000,
            duration_seconds=3600,
            total_operations=10000,
            premature_evictions=200,
        )

        assert any("premature" in rec.lower() for rec in result.recommendations)

    def test_recommendations_low_entry_age(self):
        """Test recommendations for low average entry age."""
        result = self.analyzer.analyze(
            evictions=1000,
            duration_seconds=3600,
            total_operations=10000,
            avg_entry_age_seconds=30.0,
        )

        assert any("age" in rec.lower() or "quickly" in rec.lower() for rec in result.recommendations)

    def test_recommendations_high_lru_evictions(self):
        """Test recommendations for high LRU-based evictions."""
        result = self.analyzer.analyze(
            evictions=1000,
            duration_seconds=3600,
            total_operations=10000,
            by_reason={"lru": 800, "ttl": 150, "size": 50},
        )

        assert any("lru" in rec.lower() or "capacity" in rec.lower() for rec in result.recommendations)

    def test_no_recommendations_healthy(self):
        """Test no recommendations for healthy eviction pattern."""
        result = self.analyzer.analyze(
            evictions=50,
            duration_seconds=3600,
            total_operations=10000,
            premature_evictions=5,
            avg_entry_age_seconds=300.0,
            by_reason={"ttl": 40, "manual": 10},
        )

        assert len(result.recommendations) == 0

    def test_zero_evictions(self):
        """Test analysis with zero evictions."""
        result = self.analyzer.analyze(
            evictions=0,
            duration_seconds=3600,
            total_operations=10000,
        )

        assert result.total_evictions == 0
        assert result.eviction_rate_per_sec == 0.0
        assert result.eviction_percent == 0.0

    def test_all_premature_evictions(self):
        """Test analysis when all evictions are premature."""
        result = self.analyzer.analyze(
            evictions=100,
            duration_seconds=3600,
            total_operations=10000,
            premature_evictions=100,
        )

        assert result.status == "critical"

    def test_rounding_precision(self):
        """Test that values are rounded to 2 decimal places."""
        result = self.analyzer.analyze(
            evictions=123,
            duration_seconds=7,
            total_operations=10000,
        )

        assert isinstance(result.eviction_rate_per_sec, float)
        assert isinstance(result.eviction_percent, float)

    def test_empty_reason_breakdown(self):
        """Test analysis with empty reason breakdown."""
        result = self.analyzer.analyze(
            evictions=100,
            duration_seconds=3600,
            total_operations=10000,
            by_reason={},
        )

        assert result.by_reason == {}
