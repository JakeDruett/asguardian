"""
Query Metrics Calculator

Calculates database query performance metrics.
"""

from typing import Dict, List

from Asgard.Verdandi.Analysis import PercentileCalculator
from Asgard.Verdandi.Database.models.database_models import (
    QueryMetricsInput,
    QueryMetricsResult,
    QueryType,
)


class QueryMetricsCalculator:
    """
    Calculator for database query performance metrics.

    Analyzes query execution times, index usage, and identifies slow queries.

    Example:
        calc = QueryMetricsCalculator()
        result = calc.analyze([query1, query2, ...])
        print(f"P95: {result.p95_execution_ms}ms")
    """

    def __init__(self, slow_query_threshold_ms: float = 100.0):
        """
        Initialize the calculator.

        Args:
            slow_query_threshold_ms: Threshold for classifying slow queries
        """
        self.slow_query_threshold_ms = slow_query_threshold_ms
        self._percentile_calc = PercentileCalculator()

    def analyze(
        self,
        queries: List[QueryMetricsInput],
    ) -> QueryMetricsResult:
        """
        Analyze query metrics.

        Args:
            queries: List of query metrics to analyze

        Returns:
            QueryMetricsResult with analysis
        """
        if not queries:
            raise ValueError("Cannot analyze empty query list")

        execution_times = [q.execution_time_ms for q in queries]
        percentiles = self._percentile_calc.calculate(execution_times)

        by_type = self._group_by_type(queries)
        slow_count = sum(1 for q in queries if q.execution_time_ms > self.slow_query_threshold_ms)
        index_usage = sum(1 for q in queries if q.used_index) / len(queries) * 100

        total_examined = sum(q.rows_examined for q in queries)
        total_affected = sum(q.rows_affected for q in queries if q.rows_affected > 0)
        scan_rate = total_examined / total_affected if total_affected > 0 else 0

        recommendations = self._generate_recommendations(
            percentiles.p95, slow_count, index_usage, scan_rate, len(queries)
        )

        return QueryMetricsResult(
            total_queries=len(queries),
            average_execution_ms=round(percentiles.mean, 2),
            median_execution_ms=round(percentiles.median, 2),
            p95_execution_ms=round(percentiles.p95, 2),
            p99_execution_ms=round(percentiles.p99, 2),
            max_execution_ms=round(percentiles.max_value, 2),
            min_execution_ms=round(percentiles.min_value, 2),
            by_type=by_type,
            slow_query_count=slow_count,
            slow_query_threshold_ms=self.slow_query_threshold_ms,
            index_usage_rate=round(index_usage, 2),
            scan_rate=round(scan_rate, 2),
            recommendations=recommendations,
        )

    def _group_by_type(
        self,
        queries: List[QueryMetricsInput],
    ) -> Dict[str, Dict[str, float]]:
        """Group queries by type and calculate stats."""
        groups: Dict[str, List[float]] = {}

        for query in queries:
            query_type = query.query_type.value
            if query_type not in groups:
                groups[query_type] = []
            groups[query_type].append(query.execution_time_ms)

        result = {}
        for query_type, times in groups.items():
            result[query_type] = {
                "count": len(times),
                "avg_ms": round(sum(times) / len(times), 2),
                "max_ms": round(max(times), 2),
                "min_ms": round(min(times), 2),
            }

        return result

    def _generate_recommendations(
        self,
        p95: float,
        slow_count: int,
        index_usage: float,
        scan_rate: float,
        total: int,
    ) -> List[str]:
        """Generate performance recommendations."""
        recommendations = []

        if p95 > 500:
            recommendations.append(
                f"P95 query time ({p95:.0f}ms) is high. Review slow queries for optimization."
            )

        slow_pct = (slow_count / total) * 100 if total > 0 else 0
        if slow_pct > 10:
            recommendations.append(
                f"{slow_pct:.1f}% of queries are slow (>{self.slow_query_threshold_ms}ms). "
                "Consider adding indexes or query optimization."
            )

        if index_usage < 80:
            recommendations.append(
                f"Index usage is {index_usage:.1f}%. "
                "Review queries not using indexes and add appropriate indexes."
            )

        if scan_rate > 100:
            recommendations.append(
                f"Scan rate is {scan_rate:.0f} rows examined per row affected. "
                "Queries may be doing full table scans."
            )

        return recommendations
