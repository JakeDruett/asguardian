"""
Latency Calculator

Calculates network latency metrics.
"""

from typing import List, Optional

from Asgard.Verdandi.Analysis import PercentileCalculator
from Asgard.Verdandi.Network.models.network_models import LatencyMetrics


class LatencyCalculator:
    """
    Calculator for network latency metrics.

    Analyzes latency samples and calculates percentiles, jitter, etc.

    Example:
        calc = LatencyCalculator()
        result = calc.analyze([10, 15, 12, 20, 18, 25, 11])
        print(f"P99: {result.p99_ms}ms")
    """

    GOOD_THRESHOLD = 50
    ACCEPTABLE_THRESHOLD = 100

    def __init__(self):
        """Initialize the calculator."""
        self._percentile_calc = PercentileCalculator()

    def analyze(
        self,
        latencies_ms: List[float],
        packet_loss_percent: Optional[float] = None,
    ) -> LatencyMetrics:
        """
        Analyze latency samples.

        Args:
            latencies_ms: List of latency samples in milliseconds
            packet_loss_percent: Optional packet loss percentage

        Returns:
            LatencyMetrics with analysis
        """
        if not latencies_ms:
            raise ValueError("Cannot analyze empty latency list")

        percentiles = self._percentile_calc.calculate(latencies_ms)
        jitter = self._calculate_jitter(latencies_ms)

        status = self._determine_status(percentiles.p95, packet_loss_percent)
        recommendations = self._generate_recommendations(
            percentiles.p95, jitter, packet_loss_percent
        )

        return LatencyMetrics(
            sample_count=len(latencies_ms),
            min_ms=round(percentiles.min_value, 2),
            max_ms=round(percentiles.max_value, 2),
            mean_ms=round(percentiles.mean, 2),
            median_ms=round(percentiles.median, 2),
            p90_ms=round(percentiles.p90, 2),
            p95_ms=round(percentiles.p95, 2),
            p99_ms=round(percentiles.p99, 2),
            std_dev_ms=round(percentiles.std_dev, 2),
            jitter_ms=round(jitter, 2),
            packet_loss_percent=packet_loss_percent,
            status=status,
            recommendations=recommendations,
        )

    def _calculate_jitter(self, latencies: List[float]) -> float:
        """Calculate jitter (variation between consecutive samples)."""
        if len(latencies) < 2:
            return 0.0

        variations = []
        for i in range(1, len(latencies)):
            variations.append(abs(latencies[i] - latencies[i - 1]))

        return sum(variations) / len(variations)

    def _determine_status(
        self,
        p95: float,
        packet_loss: Optional[float],
    ) -> str:
        """Determine latency status."""
        if packet_loss and packet_loss > 5:
            return "poor"
        if p95 <= self.GOOD_THRESHOLD:
            return "good"
        if p95 <= self.ACCEPTABLE_THRESHOLD:
            return "acceptable"
        return "poor"

    def _generate_recommendations(
        self,
        p95: float,
        jitter: float,
        packet_loss: Optional[float],
    ) -> List[str]:
        """Generate latency recommendations."""
        recommendations = []

        if p95 > self.ACCEPTABLE_THRESHOLD:
            recommendations.append(
                f"P95 latency ({p95:.1f}ms) is high. "
                "Consider using a CDN or optimizing network path."
            )

        if jitter > 20:
            recommendations.append(
                f"High jitter ({jitter:.1f}ms) detected. "
                "Network may be congested or experiencing issues."
            )

        if packet_loss and packet_loss > 1:
            recommendations.append(
                f"Packet loss ({packet_loss:.1f}%) detected. "
                "Check network infrastructure and connections."
            )

        return recommendations
