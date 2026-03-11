"""
Bandwidth Calculator

Calculates network bandwidth and throughput metrics.
"""

from typing import List, Optional

from Asgard.Verdandi.Network.models.network_models import BandwidthMetrics


class BandwidthCalculator:
    """
    Calculator for bandwidth and throughput metrics.

    Calculates upload/download speeds and utilization.

    Example:
        calc = BandwidthCalculator()
        result = calc.analyze(
            bytes_sent=100_000_000,
            bytes_received=500_000_000,
            duration_seconds=60
        )
        print(f"Download: {result.download_mbps} Mbps")
    """

    def analyze(
        self,
        bytes_sent: int,
        bytes_received: int,
        duration_seconds: float,
        capacity_mbps: Optional[float] = None,
    ) -> BandwidthMetrics:
        """
        Analyze bandwidth metrics.

        Args:
            bytes_sent: Total bytes sent
            bytes_received: Total bytes received
            duration_seconds: Duration of measurement
            capacity_mbps: Link capacity in Mbps (optional)

        Returns:
            BandwidthMetrics with analysis
        """
        upload_mbps = self.bytes_to_mbps(bytes_sent, duration_seconds)
        download_mbps = self.bytes_to_mbps(bytes_received, duration_seconds)
        total = upload_mbps + download_mbps

        utilization = None
        if capacity_mbps and capacity_mbps > 0:
            utilization = (total / capacity_mbps) * 100

        status = self._determine_status(utilization)
        recommendations = self._generate_recommendations(utilization, total)

        return BandwidthMetrics(
            upload_mbps=round(upload_mbps, 2),
            download_mbps=round(download_mbps, 2),
            total_throughput_mbps=round(total, 2),
            utilization_percent=round(utilization, 2) if utilization else None,
            capacity_mbps=capacity_mbps,
            bytes_sent=bytes_sent,
            bytes_received=bytes_received,
            duration_seconds=duration_seconds,
            status=status,
            recommendations=recommendations,
        )

    def bytes_to_mbps(
        self,
        bytes_value: int,
        duration_seconds: float,
    ) -> float:
        """
        Convert bytes over time to Mbps.

        Args:
            bytes_value: Number of bytes
            duration_seconds: Duration in seconds

        Returns:
            Speed in Megabits per second
        """
        if duration_seconds <= 0:
            return 0.0
        bits = bytes_value * 8
        megabits = bits / 1_000_000
        return megabits / duration_seconds

    def mbps_to_bytes_per_second(self, mbps: float) -> float:
        """
        Convert Mbps to bytes per second.

        Args:
            mbps: Speed in Megabits per second

        Returns:
            Speed in bytes per second
        """
        return (mbps * 1_000_000) / 8

    def _determine_status(self, utilization: Optional[float]) -> str:
        """Determine bandwidth status."""
        if utilization is None:
            return "unknown"
        if utilization >= 90:
            return "saturated"
        if utilization >= 70:
            return "high"
        if utilization >= 30:
            return "normal"
        return "low"

    def _generate_recommendations(
        self,
        utilization: Optional[float],
        throughput: float,
    ) -> List[str]:
        """Generate bandwidth recommendations."""
        recommendations = []

        if utilization and utilization >= 90:
            recommendations.append(
                "Bandwidth is saturated. Consider upgrading network capacity."
            )
        elif utilization and utilization >= 70:
            recommendations.append(
                f"Bandwidth utilization is high ({utilization:.1f}%). "
                "Monitor for potential bottlenecks."
            )

        return recommendations
