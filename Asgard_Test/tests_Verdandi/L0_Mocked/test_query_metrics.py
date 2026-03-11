"""
Unit tests for QueryMetricsCalculator.
"""

import pytest

from Asgard.Verdandi.Database import QueryMetricsCalculator
from Asgard.Verdandi.Database.models.database_models import QueryMetricsInput, QueryType


class TestQueryMetricsCalculator:
    """Tests for QueryMetricsCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = QueryMetricsCalculator(slow_query_threshold_ms=100.0)

    def test_analyze_empty_queries_raises(self):
        """Test that empty query list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            self.calculator.analyze([])

    def test_analyze_single_query(self):
        """Test analysis with single query."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=50.0,
                rows_examined=100,
                rows_affected=10,
                used_index=True,
            )
        ]

        result = self.calculator.analyze(queries)

        assert result.total_queries == 1
        assert result.average_execution_ms == 50.0
        assert result.median_execution_ms == 50.0
        assert result.min_execution_ms == 50.0
        assert result.max_execution_ms == 50.0

    def test_analyze_multiple_queries(self):
        """Test analysis with multiple queries."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=10.0,
                rows_examined=50,
                rows_affected=0,
                used_index=True,
            ),
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=50.0,
                rows_examined=100,
                rows_affected=0,
                used_index=True,
            ),
            QueryMetricsInput(
                query_type=QueryType.INSERT,
                execution_time_ms=100.0,
                rows_examined=0,
                rows_affected=1,
                used_index=False,
            ),
            QueryMetricsInput(
                query_type=QueryType.UPDATE,
                execution_time_ms=150.0,
                rows_examined=200,
                rows_affected=5,
                used_index=True,
            ),
        ]

        result = self.calculator.analyze(queries)

        assert result.total_queries == 4
        assert result.min_execution_ms == 10.0
        assert result.max_execution_ms == 150.0
        assert 50 < result.median_execution_ms < 100

    def test_group_by_type(self):
        """Test grouping queries by type."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=10.0,
                rows_examined=50,
                rows_affected=0,
                used_index=True,
            ),
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=20.0,
                rows_examined=100,
                rows_affected=0,
                used_index=True,
            ),
            QueryMetricsInput(
                query_type=QueryType.INSERT,
                execution_time_ms=30.0,
                rows_examined=0,
                rows_affected=1,
                used_index=False,
            ),
            QueryMetricsInput(
                query_type=QueryType.UPDATE,
                execution_time_ms=40.0,
                rows_examined=200,
                rows_affected=5,
                used_index=True,
            ),
        ]

        result = self.calculator.analyze(queries)

        assert "select" in result.by_type
        assert "insert" in result.by_type
        assert "update" in result.by_type
        assert result.by_type["select"]["count"] == 2
        assert result.by_type["select"]["avg_ms"] == 15.0
        assert result.by_type["select"]["max_ms"] == 20.0
        assert result.by_type["select"]["min_ms"] == 10.0

    def test_slow_query_detection(self):
        """Test detection of slow queries."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=50.0,
                rows_examined=50,
                rows_affected=0,
                used_index=True,
            ),
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=150.0,
                rows_examined=100,
                rows_affected=0,
                used_index=False,
            ),
            QueryMetricsInput(
                query_type=QueryType.UPDATE,
                execution_time_ms=250.0,
                rows_examined=500,
                rows_affected=10,
                used_index=False,
            ),
        ]

        result = self.calculator.analyze(queries)

        assert result.slow_query_count == 2
        assert result.slow_query_threshold_ms == 100.0

    def test_index_usage_rate(self):
        """Test calculation of index usage rate."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=10.0,
                rows_examined=50,
                rows_affected=0,
                used_index=True,
            ),
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=20.0,
                rows_examined=100,
                rows_affected=0,
                used_index=True,
            ),
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=30.0,
                rows_examined=200,
                rows_affected=0,
                used_index=False,
            ),
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=40.0,
                rows_examined=300,
                rows_affected=0,
                used_index=True,
            ),
        ]

        result = self.calculator.analyze(queries)

        assert result.index_usage_rate == 75.0

    def test_scan_rate_calculation(self):
        """Test calculation of scan rate (rows examined per row affected)."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=10.0,
                rows_examined=1000,
                rows_affected=10,
                used_index=True,
            ),
            QueryMetricsInput(
                query_type=QueryType.UPDATE,
                execution_time_ms=20.0,
                rows_examined=500,
                rows_affected=5,
                used_index=True,
            ),
        ]

        result = self.calculator.analyze(queries)

        assert result.scan_rate == 100.0

    def test_scan_rate_no_affected_rows(self):
        """Test scan rate when no rows are affected (SELECT only)."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=10.0,
                rows_examined=1000,
                rows_affected=0,
                used_index=True,
            ),
        ]

        result = self.calculator.analyze(queries)

        assert result.scan_rate == 0.0

    def test_percentile_calculations(self):
        """Test that percentile calculations are accurate."""
        execution_times = [float(i) for i in range(1, 101)]
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=time,
                rows_examined=100,
                rows_affected=0,
                used_index=True,
            )
            for time in execution_times
        ]

        result = self.calculator.analyze(queries)

        assert 94 <= result.p95_execution_ms <= 96
        assert 98 <= result.p99_execution_ms <= 100

    def test_recommendations_high_p95(self):
        """Test recommendations when P95 is high."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=float(i),
                rows_examined=100,
                rows_affected=0,
                used_index=True,
            )
            for i in range(100, 700, 10)
        ]

        result = self.calculator.analyze(queries)

        assert any("P95" in rec for rec in result.recommendations)

    def test_recommendations_many_slow_queries(self):
        """Test recommendations when many queries are slow."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=200.0 if i < 15 else 50.0,
                rows_examined=100,
                rows_affected=0,
                used_index=True,
            )
            for i in range(100)
        ]

        result = self.calculator.analyze(queries)

        assert any("slow" in rec.lower() for rec in result.recommendations)

    def test_recommendations_low_index_usage(self):
        """Test recommendations when index usage is low."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=50.0,
                rows_examined=100,
                rows_affected=0,
                used_index=(i % 5 == 0),
            )
            for i in range(100)
        ]

        result = self.calculator.analyze(queries)

        assert any("index" in rec.lower() for rec in result.recommendations)

    def test_recommendations_high_scan_rate(self):
        """Test recommendations when scan rate is high."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.UPDATE,
                execution_time_ms=50.0,
                rows_examined=10000,
                rows_affected=1,
                used_index=False,
            )
            for i in range(10)
        ]

        result = self.calculator.analyze(queries)

        assert any("scan" in rec.lower() for rec in result.recommendations)

    def test_no_recommendations_good_performance(self):
        """Test no recommendations when performance is good."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=10.0,
                rows_examined=10,
                rows_affected=10,
                used_index=True,
            )
            for i in range(100)
        ]

        result = self.calculator.analyze(queries)

        assert len(result.recommendations) == 0

    def test_custom_slow_query_threshold(self):
        """Test custom slow query threshold."""
        calculator = QueryMetricsCalculator(slow_query_threshold_ms=50.0)

        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=60.0,
                rows_examined=100,
                rows_affected=0,
                used_index=True,
            ),
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=40.0,
                rows_examined=100,
                rows_affected=0,
                used_index=True,
            ),
        ]

        result = calculator.analyze(queries)

        assert result.slow_query_count == 1
        assert result.slow_query_threshold_ms == 50.0

    def test_mixed_query_types(self):
        """Test analysis with all query types."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=10.0,
                rows_examined=100,
                rows_affected=0,
                used_index=True,
            ),
            QueryMetricsInput(
                query_type=QueryType.INSERT,
                execution_time_ms=20.0,
                rows_examined=0,
                rows_affected=1,
                used_index=False,
            ),
            QueryMetricsInput(
                query_type=QueryType.UPDATE,
                execution_time_ms=30.0,
                rows_examined=50,
                rows_affected=5,
                used_index=True,
            ),
            QueryMetricsInput(
                query_type=QueryType.DELETE,
                execution_time_ms=40.0,
                rows_examined=100,
                rows_affected=10,
                used_index=True,
            ),
            QueryMetricsInput(
                query_type=QueryType.OTHER,
                execution_time_ms=50.0,
                rows_examined=0,
                rows_affected=0,
                used_index=False,
            ),
        ]

        result = self.calculator.analyze(queries)

        assert result.total_queries == 5
        assert len(result.by_type) == 5
        assert "select" in result.by_type
        assert "insert" in result.by_type
        assert "update" in result.by_type
        assert "delete" in result.by_type
        assert "other" in result.by_type
