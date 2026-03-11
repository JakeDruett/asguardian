"""
DNS Metrics Calculator

Calculates DNS resolution performance metrics.
"""

from typing import Dict, List, Optional

from Asgard.Verdandi.Analysis import PercentileCalculator
from Asgard.Verdandi.Network.models.network_models import DnsMetrics


class DnsCalculator:
    """
    Calculator for DNS resolution metrics.

    Analyzes DNS query performance and cache effectiveness.

    Example:
        calc = DnsCalculator()
        result = calc.analyze(
            resolution_times=[5, 10, 8, 150, 7],
            cache_hits=45,
            total_queries=50
        )
        print(f"Cache Hit Rate: {result.cache_hit_rate}%")
    """

    def __init__(self):
        """Initialize the calculator."""
        self._percentile_calc = PercentileCalculator()

    def analyze(
        self,
        resolution_times_ms: List[float],
        cache_hits: int = 0,
        total_queries: Optional[int] = None,
        failures: int = 0,
        by_record_type: Optional[Dict[str, List[float]]] = None,
    ) -> DnsMetrics:
        """
        Analyze DNS metrics.

        Args:
            resolution_times_ms: List of DNS resolution times in ms
            cache_hits: Number of cache hits
            total_queries: Total queries (defaults to len(resolution_times_ms))
            failures: Number of failed queries
            by_record_type: Breakdown of times by record type

        Returns:
            DnsMetrics with analysis
        """
        if not resolution_times_ms:
            raise ValueError("Cannot analyze empty resolution times list")

        total = total_queries or len(resolution_times_ms)
        percentiles = self._percentile_calc.calculate(resolution_times_ms)

        cache_hit_rate = (cache_hits / total) * 100 if total > 0 else 0
        failure_rate = (failures / total) * 100 if total > 0 else 0

        type_breakdown = {}
        if by_record_type:
            for record_type, times in by_record_type.items():
                if times:
                    type_percentiles = self._percentile_calc.calculate(times)
                    type_breakdown[record_type] = {
                        "count": len(times),
                        "avg_ms": round(type_percentiles.mean, 2),
                        "p95_ms": round(type_percentiles.p95, 2),
                    }

        status = self._determine_status(percentiles.p95, failure_rate)
        recommendations = self._generate_recommendations(
            percentiles.p95, cache_hit_rate, failure_rate
        )

        return DnsMetrics(
            query_count=total,
            avg_resolution_ms=round(percentiles.mean, 2),
            p95_resolution_ms=round(percentiles.p95, 2),
            max_resolution_ms=round(percentiles.max_value, 2),
            cache_hit_rate=round(cache_hit_rate, 2),
            failure_rate=round(failure_rate, 2),
            by_record_type=type_breakdown,
            status=status,
            recommendations=recommendations,
        )

    def _determine_status(
        self,
        p95: float,
        failure_rate: float,
    ) -> str:
        """Determine DNS status."""
        if failure_rate > 5:
            return "critical"
        if p95 > 100:
            return "slow"
        if p95 > 50:
            return "acceptable"
        return "good"

    def _generate_recommendations(
        self,
        p95: float,
        cache_hit_rate: float,
        failure_rate: float,
    ) -> List[str]:
        """Generate DNS recommendations."""
        recommendations = []

        if p95 > 100:
            recommendations.append(
                f"DNS resolution is slow (P95: {p95:.1f}ms). "
                "Consider using faster DNS servers or local caching."
            )

        if cache_hit_rate < 50:
            recommendations.append(
                f"DNS cache hit rate is low ({cache_hit_rate:.1f}%). "
                "Consider increasing cache TTL or size."
            )

        if failure_rate > 1:
            recommendations.append(
                f"DNS failure rate ({failure_rate:.1f}%) is elevated. "
                "Check DNS server health and network connectivity."
            )

        return recommendations
