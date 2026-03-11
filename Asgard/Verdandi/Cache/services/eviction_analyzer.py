"""
Eviction Analyzer

Analyzes cache eviction patterns and metrics.
"""

from typing import Dict, List, Optional

from Asgard.Verdandi.Cache.models.cache_models import EvictionMetrics


class EvictionAnalyzer:
    """
    Analyzer for cache eviction metrics.

    Tracks eviction rates, reasons, and patterns.

    Example:
        analyzer = EvictionAnalyzer()
        result = analyzer.analyze(
            evictions=100,
            duration_seconds=3600,
            total_operations=10000
        )
        print(f"Eviction Rate: {result.eviction_rate_per_sec}/sec")
    """

    def analyze(
        self,
        evictions: int,
        duration_seconds: float,
        total_operations: int,
        by_reason: Optional[Dict[str, int]] = None,
        avg_entry_age_seconds: Optional[float] = None,
        premature_evictions: int = 0,
    ) -> EvictionMetrics:
        """
        Analyze eviction metrics.

        Args:
            evictions: Total evictions
            duration_seconds: Duration of measurement
            total_operations: Total cache operations
            by_reason: Breakdown by eviction reason
            avg_entry_age_seconds: Average age of evicted entries
            premature_evictions: Entries evicted before natural expiry

        Returns:
            EvictionMetrics with analysis
        """
        eviction_rate = evictions / duration_seconds if duration_seconds > 0 else 0
        eviction_percent = (evictions / total_operations) * 100 if total_operations > 0 else 0

        if by_reason is None:
            by_reason = {}

        status = self._determine_status(eviction_percent, premature_evictions, evictions)
        recommendations = self._generate_recommendations(
            eviction_percent, premature_evictions, avg_entry_age_seconds, by_reason
        )

        return EvictionMetrics(
            total_evictions=evictions,
            eviction_rate_per_sec=round(eviction_rate, 2),
            eviction_percent=round(eviction_percent, 2),
            by_reason=by_reason,
            avg_entry_age_seconds=avg_entry_age_seconds,
            premature_evictions=premature_evictions,
            status=status,
            recommendations=recommendations,
        )

    def calculate_eviction_rate(
        self,
        evictions: int,
        duration_seconds: float,
    ) -> float:
        """
        Calculate evictions per second.

        Args:
            evictions: Number of evictions
            duration_seconds: Duration in seconds

        Returns:
            Evictions per second
        """
        if duration_seconds <= 0:
            return 0.0
        return round(evictions / duration_seconds, 2)

    def _determine_status(
        self,
        eviction_percent: float,
        premature: int,
        total: int,
    ) -> str:
        """Determine eviction status."""
        premature_rate = (premature / total) * 100 if total > 0 else 0

        if premature_rate > 30:
            return "critical"
        if eviction_percent > 20:
            return "high"
        if eviction_percent > 10:
            return "moderate"
        return "normal"

    def _generate_recommendations(
        self,
        eviction_percent: float,
        premature: int,
        avg_age: Optional[float],
        by_reason: Dict[str, int],
    ) -> List[str]:
        """Generate eviction recommendations."""
        recommendations = []

        if eviction_percent > 20:
            recommendations.append(
                f"High eviction rate ({eviction_percent:.1f}%). "
                "Consider increasing cache size."
            )

        if premature > 0:
            recommendations.append(
                f"{premature} premature evictions detected. "
                "Cache may be undersized for workload."
            )

        if avg_age and avg_age < 60:
            recommendations.append(
                f"Average entry age is low ({avg_age:.1f}s). "
                "Entries are being evicted quickly."
            )

        if by_reason:
            total_evictions = sum(by_reason.values())
            if "lru" in by_reason and total_evictions > 0:
                lru_percent = (by_reason["lru"] / total_evictions) * 100
                if lru_percent > 70:
                    recommendations.append(
                        f"Most evictions ({lru_percent:.0f}%) are LRU-based. "
                        "Cache is at capacity frequently."
                    )

        return recommendations
