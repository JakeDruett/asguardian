"""
Unit tests for ThroughputCalculator.
"""

import pytest

from Asgard.Verdandi.Database import ThroughputCalculator
from Asgard.Verdandi.Database.models.database_models import QueryType


class TestThroughputCalculator:
    """Tests for ThroughputCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = ThroughputCalculator()

    def test_calculate_qps_basic(self):
        """Test basic QPS calculation."""
        qps = self.calculator.calculate_qps(query_count=1000, duration_seconds=60)
        assert qps == pytest.approx(16.67, abs=0.01)

    def test_calculate_qps_zero_duration(self):
        """Test QPS with zero duration returns zero."""
        qps = self.calculator.calculate_qps(query_count=1000, duration_seconds=0)
        assert qps == 0.0

    def test_calculate_qps_negative_duration(self):
        """Test QPS with negative duration returns zero."""
        qps = self.calculator.calculate_qps(query_count=1000, duration_seconds=-10)
        assert qps == 0.0

    def test_calculate_qps_high_throughput(self):
        """Test QPS with high throughput."""
        qps = self.calculator.calculate_qps(query_count=100000, duration_seconds=60)
        assert qps == pytest.approx(1666.67, abs=0.01)

    def test_calculate_tps_basic(self):
        """Test basic TPS calculation."""
        tps = self.calculator.calculate_tps(transaction_count=500, duration_seconds=60)
        assert tps == pytest.approx(8.33, abs=0.01)

    def test_calculate_tps_zero_duration(self):
        """Test TPS with zero duration returns zero."""
        tps = self.calculator.calculate_tps(transaction_count=500, duration_seconds=0)
        assert tps == 0.0

    def test_calculate_iops_basic(self):
        """Test basic IOPS calculation."""
        result = self.calculator.calculate_iops(
            read_operations=6000,
            write_operations=3000,
            duration_seconds=60,
        )

        assert result["read_iops"] == 100.0
        assert result["write_iops"] == 50.0
        assert result["total_iops"] == 150.0

    def test_calculate_iops_zero_duration(self):
        """Test IOPS with zero duration returns zeros."""
        result = self.calculator.calculate_iops(
            read_operations=6000,
            write_operations=3000,
            duration_seconds=0,
        )

        assert result["read_iops"] == 0.0
        assert result["write_iops"] == 0.0
        assert result["total_iops"] == 0.0

    def test_calculate_iops_read_only(self):
        """Test IOPS with only read operations."""
        result = self.calculator.calculate_iops(
            read_operations=6000,
            write_operations=0,
            duration_seconds=60,
        )

        assert result["read_iops"] == 100.0
        assert result["write_iops"] == 0.0
        assert result["total_iops"] == 100.0

    def test_calculate_iops_write_only(self):
        """Test IOPS with only write operations."""
        result = self.calculator.calculate_iops(
            read_operations=0,
            write_operations=3000,
            duration_seconds=60,
        )

        assert result["read_iops"] == 0.0
        assert result["write_iops"] == 50.0
        assert result["total_iops"] == 50.0

    def test_calculate_throughput_by_type(self):
        """Test throughput breakdown by query type."""
        query_types = [
            QueryType.SELECT, QueryType.SELECT, QueryType.SELECT,
            QueryType.INSERT, QueryType.INSERT,
            QueryType.UPDATE,
        ]

        result = self.calculator.calculate_throughput_by_type(
            query_types=query_types,
            duration_seconds=2.0,
        )

        assert result["select"] == 1.5
        assert result["insert"] == 1.0
        assert result["update"] == 0.5

    def test_calculate_throughput_by_type_zero_duration(self):
        """Test throughput by type with zero duration returns empty."""
        query_types = [QueryType.SELECT, QueryType.INSERT]

        result = self.calculator.calculate_throughput_by_type(
            query_types=query_types,
            duration_seconds=0,
        )

        assert result == {}

    def test_calculate_throughput_by_type_empty(self):
        """Test throughput by type with empty query list."""
        result = self.calculator.calculate_throughput_by_type(
            query_types=[],
            duration_seconds=60,
        )

        assert result == {}

    def test_calculate_bytes_throughput_basic(self):
        """Test bytes throughput calculation."""
        result = self.calculator.calculate_bytes_throughput(
            bytes_read=100 * 1024 * 1024,
            bytes_written=50 * 1024 * 1024,
            duration_seconds=10,
        )

        assert result["read_mbps"] == 10.0
        assert result["write_mbps"] == 5.0
        assert result["total_mbps"] == 15.0

    def test_calculate_bytes_throughput_zero_duration(self):
        """Test bytes throughput with zero duration returns zeros."""
        result = self.calculator.calculate_bytes_throughput(
            bytes_read=100 * 1024 * 1024,
            bytes_written=50 * 1024 * 1024,
            duration_seconds=0,
        )

        assert result["read_mbps"] == 0.0
        assert result["write_mbps"] == 0.0
        assert result["total_mbps"] == 0.0

    def test_calculate_bytes_throughput_high_volume(self):
        """Test bytes throughput with high data volume."""
        result = self.calculator.calculate_bytes_throughput(
            bytes_read=10 * 1024 * 1024 * 1024,
            bytes_written=5 * 1024 * 1024 * 1024,
            duration_seconds=60,
        )

        assert result["read_mbps"] == pytest.approx(170.67, abs=0.1)
        assert result["write_mbps"] == pytest.approx(85.33, abs=0.1)
        assert result["total_mbps"] == pytest.approx(256.0, abs=0.1)

    def test_calculate_capacity_basic(self):
        """Test capacity calculation."""
        result = self.calculator.calculate_capacity(
            current_qps=800.0,
            max_qps=1000.0,
        )

        assert result["utilization_percent"] == 80.0
        assert result["headroom_percent"] == 20.0

    def test_calculate_capacity_full(self):
        """Test capacity when at maximum."""
        result = self.calculator.calculate_capacity(
            current_qps=1000.0,
            max_qps=1000.0,
        )

        assert result["utilization_percent"] == 100.0
        assert result["headroom_percent"] == 0.0

    def test_calculate_capacity_over(self):
        """Test capacity when over maximum."""
        result = self.calculator.calculate_capacity(
            current_qps=1200.0,
            max_qps=1000.0,
        )

        assert result["utilization_percent"] == 100.0
        assert result["headroom_percent"] == 0.0

    def test_calculate_capacity_low_utilization(self):
        """Test capacity with low utilization."""
        result = self.calculator.calculate_capacity(
            current_qps=100.0,
            max_qps=1000.0,
        )

        assert result["utilization_percent"] == 10.0
        assert result["headroom_percent"] == 90.0

    def test_calculate_capacity_zero_max(self):
        """Test capacity with zero maximum QPS."""
        result = self.calculator.calculate_capacity(
            current_qps=100.0,
            max_qps=0.0,
        )

        assert result["utilization_percent"] == 100.0
        assert result["headroom_percent"] == 0.0

    def test_calculate_capacity_negative_max(self):
        """Test capacity with negative maximum QPS."""
        result = self.calculator.calculate_capacity(
            current_qps=100.0,
            max_qps=-1000.0,
        )

        assert result["utilization_percent"] == 100.0
        assert result["headroom_percent"] == 0.0

    def test_rounding_precision(self):
        """Test that all calculations are rounded to 2 decimal places."""
        qps = self.calculator.calculate_qps(query_count=1000, duration_seconds=7)
        assert isinstance(qps, float)
        assert len(str(qps).split('.')[-1]) <= 2

        tps = self.calculator.calculate_tps(transaction_count=500, duration_seconds=7)
        assert isinstance(tps, float)
        assert len(str(tps).split('.')[-1]) <= 2

    def test_calculate_throughput_by_type_all_types(self):
        """Test throughput calculation with all query types."""
        query_types = [
            QueryType.SELECT, QueryType.SELECT, QueryType.SELECT,
            QueryType.INSERT, QueryType.INSERT,
            QueryType.UPDATE,
            QueryType.DELETE,
            QueryType.OTHER,
        ]

        result = self.calculator.calculate_throughput_by_type(
            query_types=query_types,
            duration_seconds=1.0,
        )

        assert "select" in result
        assert "insert" in result
        assert "update" in result
        assert "delete" in result
        assert "other" in result
        assert result["select"] == 3.0
        assert result["insert"] == 2.0
        assert result["update"] == 1.0
        assert result["delete"] == 1.0
        assert result["other"] == 1.0

    def test_bytes_throughput_fractional_mb(self):
        """Test bytes throughput with fractional megabytes."""
        result = self.calculator.calculate_bytes_throughput(
            bytes_read=512 * 1024,
            bytes_written=256 * 1024,
            duration_seconds=1,
        )

        assert result["read_mbps"] == 0.5
        assert result["write_mbps"] == pytest.approx(0.25, abs=0.01)
        assert result["total_mbps"] == 0.75
