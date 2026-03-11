"""
L1 Integration Tests for Database Metrics Workflow.

Tests the complete workflow of processing query timing data,
calculating comprehensive database metrics, identifying performance
bottlenecks, and validating recommendations.
"""

import pytest

from Asgard.Verdandi.Database.services.query_metrics import QueryMetricsCalculator
from Asgard.Verdandi.Database.models.database_models import (
    QueryMetricsInput,
    QueryMetricsResult,
    QueryType,
)


class TestDatabaseMetricsIntegration:
    """Integration tests for database query metrics workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = QueryMetricsCalculator(slow_query_threshold_ms=100.0)

    def test_database_workflow_fast_queries(self, fast_query_metrics):
        """Test complete workflow with fast queries."""
        result = self.calculator.analyze(fast_query_metrics)

        assert isinstance(result, QueryMetricsResult)
        assert result.total_queries == 10
        assert result.average_execution_ms < 100.0
        assert result.median_execution_ms < 100.0
        assert result.p95_execution_ms < 100.0
        assert result.slow_query_count == 0
        assert result.index_usage_rate == 100.0
        assert len(result.recommendations) == 0

    def test_database_workflow_slow_queries(self, slow_query_metrics):
        """Test complete workflow with slow queries."""
        result = self.calculator.analyze(slow_query_metrics)

        assert isinstance(result, QueryMetricsResult)
        assert result.total_queries == 9
        assert result.average_execution_ms > 100.0
        assert result.p95_execution_ms > 500.0
        assert result.slow_query_count > 0
        assert result.index_usage_rate < 50.0
        assert len(result.recommendations) > 0

    def test_database_workflow_mixed_queries(self, mixed_query_metrics):
        """Test workflow with mix of fast and slow queries."""
        result = self.calculator.analyze(mixed_query_metrics)

        assert isinstance(result, QueryMetricsResult)
        assert result.total_queries == 25
        assert result.slow_query_count == 5
        assert result.slow_query_count / result.total_queries == 0.2
        assert 20.0 < result.average_execution_ms < 200.0
        assert len(result.recommendations) > 0

    def test_database_workflow_by_query_type(self, query_metrics_by_type):
        """Test workflow analyzing different query types."""
        result = self.calculator.analyze(query_metrics_by_type)

        assert isinstance(result, QueryMetricsResult)
        assert "select" in result.by_type
        assert "insert" in result.by_type
        assert "update" in result.by_type
        assert "delete" in result.by_type

        assert result.by_type["select"]["count"] == 10
        assert result.by_type["insert"]["count"] == 5
        assert result.by_type["update"]["count"] == 3
        assert result.by_type["delete"]["count"] == 1

    def test_database_percentile_calculations(self, mixed_query_metrics):
        """Test that percentiles are calculated correctly."""
        result = self.calculator.analyze(mixed_query_metrics)

        assert result.min_execution_ms <= result.median_execution_ms
        assert result.median_execution_ms <= result.p95_execution_ms
        assert result.p95_execution_ms <= result.p99_execution_ms
        assert result.p99_execution_ms <= result.max_execution_ms

    def test_database_index_usage_rate(self, slow_query_metrics):
        """Test index usage rate calculation."""
        result = self.calculator.analyze(slow_query_metrics)

        queries_with_index = sum(1 for q in slow_query_metrics if q.used_index)
        expected_rate = (queries_with_index / len(slow_query_metrics)) * 100

        assert result.index_usage_rate == pytest.approx(expected_rate, rel=0.01)

    def test_database_scan_rate_calculation(self, slow_query_metrics):
        """Test scan rate calculation for query efficiency."""
        result = self.calculator.analyze(slow_query_metrics)

        total_examined = sum(q.rows_examined for q in slow_query_metrics)
        total_affected = sum(q.rows_affected for q in slow_query_metrics if q.rows_affected > 0)
        expected_scan_rate = total_examined / total_affected if total_affected > 0 else 0

        assert result.scan_rate == pytest.approx(expected_scan_rate, rel=0.01)

    def test_database_high_scan_rate_recommendation(self):
        """Test that high scan rate generates recommendations."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=200.0,
                rows_examined=10000,
                rows_affected=10,
                used_index=False,
            )
            for _ in range(5)
        ]

        result = self.calculator.analyze(queries)

        assert result.scan_rate > 100
        assert any("scan" in rec.lower() for rec in result.recommendations)

    def test_database_low_index_usage_recommendation(self):
        """Test that low index usage generates recommendations."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=150.0,
                rows_examined=1000,
                rows_affected=100,
                used_index=False,
            )
            for _ in range(10)
        ]

        result = self.calculator.analyze(queries)

        assert result.index_usage_rate == 0.0
        assert any("index" in rec.lower() for rec in result.recommendations)

    def test_database_slow_query_percentage_recommendation(self):
        """Test that high percentage of slow queries generates recommendations."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=500.0,
                rows_examined=100,
                rows_affected=100,
                used_index=True,
            )
            for _ in range(10)
        ]

        result = self.calculator.analyze(queries)

        slow_pct = (result.slow_query_count / result.total_queries) * 100
        assert slow_pct > 10
        assert any("slow" in rec.lower() for rec in result.recommendations)

    def test_database_p95_threshold_recommendation(self):
        """Test that high P95 generates recommendations."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=600.0 + i,
                rows_examined=100,
                rows_affected=100,
                used_index=True,
            )
            for i in range(20)
        ]

        result = self.calculator.analyze(queries)

        assert result.p95_execution_ms > 500
        assert any("P95" in rec or "p95" in rec.lower() for rec in result.recommendations)

    def test_database_query_type_statistics(self, query_metrics_by_type):
        """Test query type statistics are accurate."""
        result = self.calculator.analyze(query_metrics_by_type)

        select_stats = result.by_type["select"]
        assert select_stats["count"] == 10
        assert select_stats["avg_ms"] == 50.0
        assert select_stats["max_ms"] == 50.0
        assert select_stats["min_ms"] == 50.0

        insert_stats = result.by_type["insert"]
        assert insert_stats["count"] == 5
        assert insert_stats["avg_ms"] == 30.0

        update_stats = result.by_type["update"]
        assert update_stats["count"] == 3
        assert update_stats["avg_ms"] == 80.0

    def test_database_custom_slow_threshold(self):
        """Test custom slow query threshold."""
        calculator = QueryMetricsCalculator(slow_query_threshold_ms=50.0)

        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=60.0,
                rows_examined=100,
                rows_affected=100,
                used_index=True,
            )
            for _ in range(5)
        ]

        result = calculator.analyze(queries)

        assert result.slow_query_threshold_ms == 50.0
        assert result.slow_query_count == 5

    def test_database_zero_affected_rows_scan_rate(self):
        """Test scan rate when no rows are affected."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=50.0,
                rows_examined=1000,
                rows_affected=0,
                used_index=True,
            )
            for _ in range(5)
        ]

        result = self.calculator.analyze(queries)

        assert result.scan_rate == 0.0

    def test_database_mixed_index_usage(self):
        """Test mixed index usage patterns."""
        queries = []

        for i in range(5):
            queries.append(
                QueryMetricsInput(
                    query_type=QueryType.SELECT,
                    execution_time_ms=50.0,
                    rows_examined=100,
                    rows_affected=100,
                    used_index=True,
                )
            )

        for i in range(5):
            queries.append(
                QueryMetricsInput(
                    query_type=QueryType.SELECT,
                    execution_time_ms=200.0,
                    rows_examined=5000,
                    rows_affected=100,
                    used_index=False,
                )
            )

        result = self.calculator.analyze(queries)

        assert result.index_usage_rate == 50.0

    def test_database_single_query_analysis(self):
        """Test analysis with a single query."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=75.0,
                rows_examined=100,
                rows_affected=100,
                used_index=True,
            )
        ]

        result = self.calculator.analyze(queries)

        assert result.total_queries == 1
        assert result.average_execution_ms == 75.0
        assert result.median_execution_ms == 75.0
        assert result.min_execution_ms == 75.0
        assert result.max_execution_ms == 75.0

    def test_database_empty_query_list_error(self):
        """Test that empty query list raises error."""
        with pytest.raises(ValueError, match="Cannot analyze empty query list"):
            self.calculator.analyze([])

    def test_database_all_metrics_present(self, mixed_query_metrics):
        """Test that all expected metrics are present in result."""
        result = self.calculator.analyze(mixed_query_metrics)

        assert hasattr(result, "total_queries")
        assert hasattr(result, "average_execution_ms")
        assert hasattr(result, "median_execution_ms")
        assert hasattr(result, "p95_execution_ms")
        assert hasattr(result, "p99_execution_ms")
        assert hasattr(result, "max_execution_ms")
        assert hasattr(result, "min_execution_ms")
        assert hasattr(result, "by_type")
        assert hasattr(result, "slow_query_count")
        assert hasattr(result, "slow_query_threshold_ms")
        assert hasattr(result, "index_usage_rate")
        assert hasattr(result, "scan_rate")
        assert hasattr(result, "recommendations")

    def test_database_recommendations_for_optimal_queries(self):
        """Test that no recommendations for optimal queries."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=30.0,
                rows_examined=100,
                rows_affected=100,
                used_index=True,
            )
            for _ in range(10)
        ]

        result = self.calculator.analyze(queries)

        assert len(result.recommendations) == 0

    def test_database_large_dataset_analysis(self):
        """Test analysis with large number of queries."""
        queries = [
            QueryMetricsInput(
                query_type=QueryType.SELECT,
                execution_time_ms=50.0 + (i % 100),
                rows_examined=100,
                rows_affected=100,
                used_index=True,
            )
            for i in range(1000)
        ]

        result = self.calculator.analyze(queries)

        assert result.total_queries == 1000
        assert result.average_execution_ms > 0
        assert result.p95_execution_ms > result.median_execution_ms
