"""
Resource Timing Calculator

Analyzes resource loading performance from Resource Timing API data.
"""

from typing import Dict, List

from Asgard.Verdandi.Web.models.web_models import (
    ResourceTimingInput,
    ResourceTimingResult,
)


class ResourceTimingCalculator:
    """
    Calculator for Resource Timing analysis.

    Analyzes resource loading patterns, identifies bottlenecks,
    and provides optimization recommendations.

    Example:
        calc = ResourceTimingCalculator()
        result = calc.analyze([resource1, resource2, ...])
        print(f"Total transfer: {result.total_transfer_bytes} bytes")
    """

    RENDER_BLOCKING_TYPES = {"script", "link", "stylesheet"}

    def analyze(
        self,
        resources: List[ResourceTimingInput],
    ) -> ResourceTimingResult:
        """
        Analyze resource timing data.

        Args:
            resources: List of resource timing entries

        Returns:
            ResourceTimingResult with analysis
        """
        if not resources:
            return ResourceTimingResult(
                total_resources=0,
                total_transfer_bytes=0,
                total_duration_ms=0,
                by_type={},
                largest_resources=[],
                slowest_resources=[],
                blocking_resources=[],
                cache_hit_rate=0,
                recommendations=[],
            )

        total_bytes = sum(r.transfer_size_bytes for r in resources)
        total_duration = max(r.start_time_ms + r.duration_ms for r in resources)

        by_type = self._group_by_type(resources)
        largest = self._find_largest(resources)
        slowest = self._find_slowest(resources)
        blocking = self._find_blocking(resources)
        cache_hit = self._calculate_cache_hit_rate(resources)
        recommendations = self._generate_recommendations(
            resources, by_type, largest, slowest, blocking, cache_hit
        )

        return ResourceTimingResult(
            total_resources=len(resources),
            total_transfer_bytes=total_bytes,
            total_duration_ms=round(total_duration, 2),
            by_type=by_type,
            largest_resources=largest,
            slowest_resources=slowest,
            blocking_resources=blocking,
            cache_hit_rate=round(cache_hit, 2),
            recommendations=recommendations,
        )

    def _group_by_type(
        self,
        resources: List[ResourceTimingInput],
    ) -> Dict[str, Dict[str, float]]:
        """Group resources by initiator type."""
        groups: Dict[str, Dict[str, float]] = {}

        for resource in resources:
            res_type = resource.initiator_type
            if res_type not in groups:
                groups[res_type] = {
                    "count": 0,
                    "total_bytes": 0,
                    "total_duration_ms": 0,
                }

            groups[res_type]["count"] += 1
            groups[res_type]["total_bytes"] += resource.transfer_size_bytes
            groups[res_type]["total_duration_ms"] += resource.duration_ms

        for group in groups.values():
            group["avg_duration_ms"] = group["total_duration_ms"] / group["count"]

        return groups

    def _find_largest(
        self,
        resources: List[ResourceTimingInput],
        top_n: int = 5,
    ) -> List[Dict[str, float]]:
        """Find the largest resources by transfer size."""
        sorted_resources = sorted(
            resources,
            key=lambda r: r.transfer_size_bytes,
            reverse=True,
        )

        return [
            {
                "name": r.name,
                "size_bytes": r.transfer_size_bytes,
                "type": r.initiator_type,
            }
            for r in sorted_resources[:top_n]
        ]

    def _find_slowest(
        self,
        resources: List[ResourceTimingInput],
        top_n: int = 5,
    ) -> List[Dict[str, float]]:
        """Find the slowest resources by duration."""
        sorted_resources = sorted(
            resources,
            key=lambda r: r.duration_ms,
            reverse=True,
        )

        return [
            {
                "name": r.name,
                "duration_ms": r.duration_ms,
                "type": r.initiator_type,
            }
            for r in sorted_resources[:top_n]
        ]

    def _find_blocking(
        self,
        resources: List[ResourceTimingInput],
    ) -> List[str]:
        """Find render-blocking resources."""
        blocking = []

        for resource in resources:
            if resource.initiator_type in self.RENDER_BLOCKING_TYPES:
                if resource.start_time_ms < 500:
                    blocking.append(resource.name)

        return blocking

    def _calculate_cache_hit_rate(
        self,
        resources: List[ResourceTimingInput],
    ) -> float:
        """Estimate cache hit rate based on transfer size."""
        if not resources:
            return 0.0

        cache_hits = 0
        for resource in resources:
            if resource.transfer_size_bytes == 0:
                cache_hits += 1
            elif resource.transfer_size_bytes < resource.encoded_body_size_bytes * 0.1:
                cache_hits += 1

        return (cache_hits / len(resources)) * 100

    def _generate_recommendations(
        self,
        resources: List[ResourceTimingInput],
        by_type: Dict[str, Dict[str, float]],
        largest: List[Dict],
        slowest: List[Dict],
        blocking: List[str],
        cache_hit_rate: float,
    ) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        if len(blocking) > 3:
            recommendations.append(
                f"Found {len(blocking)} render-blocking resources. "
                "Consider deferring non-critical scripts and inlining critical CSS."
            )

        if largest and largest[0]["size_bytes"] > 500000:
            recommendations.append(
                f"Large resource detected: {largest[0]['name']} ({largest[0]['size_bytes']/1024:.0f}KB). "
                "Consider compression or lazy loading."
            )

        if slowest and slowest[0]["duration_ms"] > 1000:
            recommendations.append(
                f"Slow resource: {slowest[0]['name']} ({slowest[0]['duration_ms']:.0f}ms). "
                "Check network conditions or optimize resource."
            )

        if cache_hit_rate < 50:
            recommendations.append(
                f"Cache hit rate is low ({cache_hit_rate:.0f}%). "
                "Implement proper caching headers."
            )

        if "img" in by_type:
            img_stats = by_type["img"]
            if img_stats["total_bytes"] > 1000000:
                recommendations.append(
                    f"Images total {img_stats['total_bytes']/1024:.0f}KB. "
                    "Consider using modern formats (WebP, AVIF) and responsive images."
                )

        if len(resources) > 100:
            recommendations.append(
                f"Page loads {len(resources)} resources. "
                "Consider bundling, lazy loading, or reducing dependencies."
            )

        return recommendations
