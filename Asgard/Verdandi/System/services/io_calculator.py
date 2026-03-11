"""
I/O Metrics Calculator

Calculates I/O throughput and performance metrics.
"""

from typing import List, Optional

from Asgard.Verdandi.System.models.system_models import IoMetrics


class IoMetricsCalculator:
    """
    Calculator for I/O performance metrics.

    Analyzes disk I/O throughput, IOPS, and latency.

    Example:
        calc = IoMetricsCalculator()
        result = calc.analyze(
            read_bytes=1_000_000_000,
            write_bytes=500_000_000,
            duration_seconds=60
        )
        print(f"Total IOPS: {result.total_iops}")
    """

    def analyze(
        self,
        read_bytes: int,
        write_bytes: int,
        read_ops: int,
        write_ops: int,
        duration_seconds: float,
        avg_read_latency_ms: Optional[float] = None,
        avg_write_latency_ms: Optional[float] = None,
        queue_depth: Optional[float] = None,
        utilization_percent: Optional[float] = None,
    ) -> IoMetrics:
        """
        Analyze I/O metrics.

        Args:
            read_bytes: Total bytes read
            write_bytes: Total bytes written
            read_ops: Total read operations
            write_ops: Total write operations
            duration_seconds: Duration of measurement
            avg_read_latency_ms: Average read latency
            avg_write_latency_ms: Average write latency
            queue_depth: Average queue depth
            utilization_percent: Disk utilization percentage

        Returns:
            IoMetrics with analysis
        """
        read_bytes_per_sec = read_bytes / duration_seconds if duration_seconds > 0 else 0
        write_bytes_per_sec = write_bytes / duration_seconds if duration_seconds > 0 else 0
        read_ops_per_sec = read_ops / duration_seconds if duration_seconds > 0 else 0
        write_ops_per_sec = write_ops / duration_seconds if duration_seconds > 0 else 0

        total_iops = read_ops_per_sec + write_ops_per_sec
        total_throughput_mbps = (read_bytes_per_sec + write_bytes_per_sec) / (1024 * 1024)

        status = self._determine_status(
            total_iops, avg_read_latency_ms, avg_write_latency_ms, utilization_percent
        )
        recommendations = self._generate_recommendations(
            total_iops, avg_read_latency_ms, avg_write_latency_ms,
            utilization_percent, queue_depth
        )

        return IoMetrics(
            read_bytes_per_sec=round(read_bytes_per_sec, 2),
            write_bytes_per_sec=round(write_bytes_per_sec, 2),
            read_ops_per_sec=round(read_ops_per_sec, 2),
            write_ops_per_sec=round(write_ops_per_sec, 2),
            total_iops=round(total_iops, 2),
            total_throughput_mbps=round(total_throughput_mbps, 2),
            avg_read_latency_ms=avg_read_latency_ms,
            avg_write_latency_ms=avg_write_latency_ms,
            queue_depth=queue_depth,
            utilization_percent=utilization_percent,
            status=status,
            recommendations=recommendations,
        )

    def calculate_iops(
        self,
        operations: int,
        duration_seconds: float,
    ) -> float:
        """
        Calculate operations per second.

        Args:
            operations: Total operations
            duration_seconds: Duration in seconds

        Returns:
            Operations per second
        """
        if duration_seconds <= 0:
            return 0.0
        return round(operations / duration_seconds, 2)

    def calculate_throughput_mbps(
        self,
        bytes_transferred: int,
        duration_seconds: float,
    ) -> float:
        """
        Calculate throughput in MB/s.

        Args:
            bytes_transferred: Total bytes transferred
            duration_seconds: Duration in seconds

        Returns:
            Throughput in MB/s
        """
        if duration_seconds <= 0:
            return 0.0
        return round((bytes_transferred / (1024 * 1024)) / duration_seconds, 2)

    def _determine_status(
        self,
        iops: float,
        read_latency: Optional[float],
        write_latency: Optional[float],
        utilization: Optional[float],
    ) -> str:
        """Determine I/O status."""
        if utilization and utilization >= 95:
            return "critical"
        if utilization and utilization >= 80:
            return "warning"

        if read_latency and read_latency > 50:
            return "warning"
        if write_latency and write_latency > 50:
            return "warning"

        return "healthy"

    def _generate_recommendations(
        self,
        iops: float,
        read_latency: Optional[float],
        write_latency: Optional[float],
        utilization: Optional[float],
        queue_depth: Optional[float],
    ) -> List[str]:
        """Generate I/O recommendations."""
        recommendations = []

        if utilization and utilization >= 95:
            recommendations.append(
                "Critical: Disk utilization is very high. "
                "Consider adding storage capacity or faster disks."
            )
        elif utilization and utilization >= 80:
            recommendations.append(
                f"Disk utilization is elevated ({utilization:.1f}%). "
                "Monitor for potential bottlenecks."
            )

        if read_latency and read_latency > 20:
            recommendations.append(
                f"Read latency is high ({read_latency:.1f}ms). "
                "Consider SSD storage or caching."
            )

        if write_latency and write_latency > 20:
            recommendations.append(
                f"Write latency is high ({write_latency:.1f}ms). "
                "Consider write-back caching or faster storage."
            )

        if queue_depth and queue_depth > 32:
            recommendations.append(
                f"High I/O queue depth ({queue_depth:.1f}). "
                "Storage may be a bottleneck."
            )

        return recommendations
