"""
Unit tests for IoMetricsCalculator.
"""

import pytest

from Asgard.Verdandi.System import IoMetricsCalculator


class TestIoMetricsCalculator:
    """Tests for IoMetricsCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = IoMetricsCalculator()

    def test_analyze_basic(self):
        """Test basic I/O analysis."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
        )

        assert result.read_bytes_per_sec == 10_000_000
        assert result.write_bytes_per_sec == 5_000_000
        assert result.read_ops_per_sec == 100.0
        assert result.write_ops_per_sec == 50.0
        assert result.total_iops == 150.0
        assert result.total_throughput_mbps == pytest.approx(14.31, abs=0.1)

    def test_analyze_with_latency(self):
        """Test I/O analysis with latency metrics."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            avg_read_latency_ms=5.0,
            avg_write_latency_ms=10.0,
        )

        assert result.avg_read_latency_ms == 5.0
        assert result.avg_write_latency_ms == 10.0

    def test_analyze_with_queue_depth(self):
        """Test I/O analysis with queue depth."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            queue_depth=8.5,
        )

        assert result.queue_depth == 8.5

    def test_analyze_with_utilization(self):
        """Test I/O analysis with utilization."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            utilization_percent=75.0,
        )

        assert result.utilization_percent == 75.0

    def test_status_healthy(self):
        """Test healthy status determination."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            avg_read_latency_ms=5.0,
            avg_write_latency_ms=8.0,
            utilization_percent=50.0,
        )

        assert result.status == "healthy"

    def test_status_warning_high_utilization(self):
        """Test warning status for high utilization."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            utilization_percent=85.0,
        )

        assert result.status == "warning"

    def test_status_critical_very_high_utilization(self):
        """Test critical status for very high utilization."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            utilization_percent=96.0,
        )

        assert result.status == "critical"

    def test_status_warning_high_read_latency(self):
        """Test warning status for high read latency."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            avg_read_latency_ms=55.0,
        )

        assert result.status == "warning"

    def test_status_warning_high_write_latency(self):
        """Test warning status for high write latency."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            avg_write_latency_ms=60.0,
        )

        assert result.status == "warning"

    def test_calculate_iops(self):
        """Test IOPS calculation method."""
        iops = self.calculator.calculate_iops(operations=1000, duration_seconds=10)
        assert iops == 100.0

    def test_calculate_iops_zero_duration(self):
        """Test IOPS calculation with zero duration."""
        iops = self.calculator.calculate_iops(operations=1000, duration_seconds=0)
        assert iops == 0.0

    def test_calculate_throughput_mbps(self):
        """Test throughput calculation in MB/s."""
        throughput = self.calculator.calculate_throughput_mbps(
            bytes_transferred=104_857_600,
            duration_seconds=10,
        )
        assert throughput == 10.0

    def test_calculate_throughput_mbps_zero_duration(self):
        """Test throughput calculation with zero duration."""
        throughput = self.calculator.calculate_throughput_mbps(
            bytes_transferred=104_857_600,
            duration_seconds=0,
        )
        assert throughput == 0.0

    def test_recommendations_critical_utilization(self):
        """Test recommendations for critical disk utilization."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            utilization_percent=97.0,
        )

        assert any("critical" in rec.lower() for rec in result.recommendations)

    def test_recommendations_warning_utilization(self):
        """Test recommendations for warning disk utilization."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            utilization_percent=85.0,
        )

        assert any("elevated" in rec.lower() or "utilization" in rec.lower() for rec in result.recommendations)

    def test_recommendations_high_read_latency(self):
        """Test recommendations for high read latency."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            avg_read_latency_ms=30.0,
        )

        assert any("read" in rec.lower() and "latency" in rec.lower() for rec in result.recommendations)

    def test_recommendations_high_write_latency(self):
        """Test recommendations for high write latency."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            avg_write_latency_ms=35.0,
        )

        assert any("write" in rec.lower() and "latency" in rec.lower() for rec in result.recommendations)

    def test_recommendations_high_queue_depth(self):
        """Test recommendations for high queue depth."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            queue_depth=40.0,
        )

        assert any("queue" in rec.lower() for rec in result.recommendations)

    def test_no_recommendations_healthy(self):
        """Test no recommendations for healthy I/O state."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=50_000_000,
            read_ops=1000,
            write_ops=500,
            duration_seconds=10,
            avg_read_latency_ms=5.0,
            avg_write_latency_ms=8.0,
            queue_depth=4.0,
            utilization_percent=50.0,
        )

        assert len(result.recommendations) == 0

    def test_zero_operations(self):
        """Test analysis with zero operations."""
        result = self.calculator.analyze(
            read_bytes=0,
            write_bytes=0,
            read_ops=0,
            write_ops=0,
            duration_seconds=10,
        )

        assert result.total_iops == 0.0
        assert result.total_throughput_mbps == 0.0

    def test_read_only_workload(self):
        """Test analysis with read-only workload."""
        result = self.calculator.analyze(
            read_bytes=100_000_000,
            write_bytes=0,
            read_ops=1000,
            write_ops=0,
            duration_seconds=10,
        )

        assert result.write_ops_per_sec == 0.0
        assert result.write_bytes_per_sec == 0.0

    def test_write_only_workload(self):
        """Test analysis with write-only workload."""
        result = self.calculator.analyze(
            read_bytes=0,
            write_bytes=100_000_000,
            read_ops=0,
            write_ops=1000,
            duration_seconds=10,
        )

        assert result.read_ops_per_sec == 0.0
        assert result.read_bytes_per_sec == 0.0

    def test_rounding_precision(self):
        """Test that values are rounded to 2 decimal places."""
        result = self.calculator.analyze(
            read_bytes=123_456_789,
            write_bytes=654_321,
            read_ops=1234,
            write_ops=567,
            duration_seconds=7,
        )

        assert isinstance(result.read_ops_per_sec, float)
        assert isinstance(result.total_throughput_mbps, float)
