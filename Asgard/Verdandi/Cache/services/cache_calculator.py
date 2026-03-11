"""
Cache Metrics Calculator

Calculates cache performance metrics.
"""

from typing import List, Optional

from Asgard.Verdandi.Cache.models.cache_models import CacheMetrics, CacheEfficiency


class CacheMetricsCalculator:
    """
    Calculator for cache performance metrics.

    Analyzes cache hit rates, latency savings, and efficiency.

    Example:
        calc = CacheMetricsCalculator()
        result = calc.analyze(hits=950, misses=50)
        print(f"Hit Rate: {result.hit_rate_percent}%")
    """

    EXCELLENT_THRESHOLD = 95.0
    GOOD_THRESHOLD = 85.0
    FAIR_THRESHOLD = 70.0

    def analyze(
        self,
        hits: int,
        misses: int,
        avg_hit_latency_ms: Optional[float] = None,
        avg_miss_latency_ms: Optional[float] = None,
        size_bytes: Optional[int] = None,
        max_size_bytes: Optional[int] = None,
    ) -> CacheMetrics:
        """
        Analyze cache metrics.

        Args:
            hits: Number of cache hits
            misses: Number of cache misses
            avg_hit_latency_ms: Average latency for cache hits
            avg_miss_latency_ms: Average latency for cache misses
            size_bytes: Current cache size in bytes
            max_size_bytes: Maximum cache size in bytes

        Returns:
            CacheMetrics with analysis
        """
        total = hits + misses
        hit_rate = (hits / total) * 100 if total > 0 else 0
        miss_rate = (misses / total) * 100 if total > 0 else 0

        latency_savings = None
        if avg_hit_latency_ms is not None and avg_miss_latency_ms is not None:
            savings_per_hit = avg_miss_latency_ms - avg_hit_latency_ms
            latency_savings = savings_per_hit * hits

        fill_percent = None
        if size_bytes is not None and max_size_bytes and max_size_bytes > 0:
            fill_percent = (size_bytes / max_size_bytes) * 100

        status = self._determine_status(hit_rate)
        recommendations = self._generate_recommendations(
            hit_rate, fill_percent, avg_hit_latency_ms, avg_miss_latency_ms
        )

        return CacheMetrics(
            total_requests=total,
            hits=hits,
            misses=misses,
            hit_rate_percent=round(hit_rate, 2),
            miss_rate_percent=round(miss_rate, 2),
            avg_hit_latency_ms=avg_hit_latency_ms,
            avg_miss_latency_ms=avg_miss_latency_ms,
            latency_savings_ms=round(latency_savings, 2) if latency_savings else None,
            size_bytes=size_bytes,
            max_size_bytes=max_size_bytes,
            fill_percent=round(fill_percent, 2) if fill_percent else None,
            status=status,
            recommendations=recommendations,
        )

    def calculate_hit_rate(self, hits: int, total: int) -> float:
        """
        Calculate cache hit rate.

        Args:
            hits: Number of hits
            total: Total requests

        Returns:
            Hit rate as percentage
        """
        if total <= 0:
            return 0.0
        return round((hits / total) * 100, 2)

    def calculate_efficiency(
        self,
        metrics: CacheMetrics,
        memory_overhead_percent: float = 10.0,
    ) -> CacheEfficiency:
        """
        Calculate overall cache efficiency.

        Args:
            metrics: Cache metrics to analyze
            memory_overhead_percent: Estimated memory overhead

        Returns:
            CacheEfficiency assessment
        """
        hit_rate = metrics.hit_rate_percent

        memory_efficiency = 100.0
        if metrics.fill_percent:
            if metrics.fill_percent < 50:
                memory_efficiency = metrics.fill_percent * 2
            elif metrics.fill_percent > 95:
                memory_efficiency = 90 + (100 - metrics.fill_percent)
            else:
                memory_efficiency = 90 + (metrics.fill_percent - 50) * 0.2

        latency_factor = None
        if metrics.avg_hit_latency_ms and metrics.avg_miss_latency_ms:
            if metrics.avg_hit_latency_ms > 0:
                latency_factor = metrics.avg_miss_latency_ms / metrics.avg_hit_latency_ms

        efficiency_score = (hit_rate * 0.7) + (memory_efficiency * 0.3)

        status = self._determine_status(efficiency_score)
        recommendations = self._generate_efficiency_recommendations(
            hit_rate, memory_efficiency, latency_factor, metrics.fill_percent
        )

        return CacheEfficiency(
            efficiency_score=round(efficiency_score, 2),
            hit_rate_percent=hit_rate,
            memory_efficiency_percent=round(memory_efficiency, 2),
            latency_improvement_factor=round(latency_factor, 2) if latency_factor else None,
            cost_savings_percent=round(hit_rate * 0.8, 2),
            optimal_size_bytes=None,
            status=status,
            recommendations=recommendations,
        )

    def _determine_status(self, rate: float) -> str:
        """Determine cache status based on hit rate."""
        if rate >= self.EXCELLENT_THRESHOLD:
            return "excellent"
        if rate >= self.GOOD_THRESHOLD:
            return "good"
        if rate >= self.FAIR_THRESHOLD:
            return "fair"
        return "poor"

    def _generate_recommendations(
        self,
        hit_rate: float,
        fill_percent: Optional[float],
        hit_latency: Optional[float],
        miss_latency: Optional[float],
    ) -> List[str]:
        """Generate cache recommendations."""
        recommendations = []

        if hit_rate < self.FAIR_THRESHOLD:
            recommendations.append(
                f"Cache hit rate ({hit_rate:.1f}%) is low. "
                "Consider increasing cache size or adjusting TTL."
            )

        if fill_percent and fill_percent > 95:
            recommendations.append(
                "Cache is nearly full. Consider increasing size to reduce evictions."
            )

        if fill_percent and fill_percent < 30:
            recommendations.append(
                f"Cache utilization is low ({fill_percent:.1f}%). "
                "Consider caching more data types."
            )

        if hit_latency and miss_latency:
            if hit_latency > miss_latency * 0.5:
                recommendations.append(
                    "Cache hit latency is relatively high. "
                    "Consider optimizing cache access patterns."
                )

        return recommendations

    def _generate_efficiency_recommendations(
        self,
        hit_rate: float,
        memory_efficiency: float,
        latency_factor: Optional[float],
        fill_percent: Optional[float],
    ) -> List[str]:
        """Generate efficiency recommendations."""
        recommendations = []

        if hit_rate < 80:
            recommendations.append(
                "Improve hit rate by increasing cache size or optimizing eviction policy."
            )

        if memory_efficiency < 70:
            recommendations.append(
                "Memory efficiency is suboptimal. Review cache sizing strategy."
            )

        if latency_factor and latency_factor < 5:
            recommendations.append(
                "Latency improvement from caching is modest. "
                "Ensure high-latency operations are being cached."
            )

        return recommendations
