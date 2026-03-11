"""
Database Throughput Calculator

Calculates database throughput metrics.
"""

from typing import Dict, List, Optional, Sequence

from Asgard.Verdandi.Database.models.database_models import QueryType


class ThroughputCalculator:
    """
    Calculator for database throughput metrics.

    Calculates queries per second, transactions per second, and related metrics.

    Example:
        calc = ThroughputCalculator()
        qps = calc.calculate_qps(query_count=1000, duration_seconds=60)
        print(f"QPS: {qps}")
    """

    def calculate_qps(
        self,
        query_count: int,
        duration_seconds: float,
    ) -> float:
        """
        Calculate queries per second.

        Args:
            query_count: Total queries executed
            duration_seconds: Time period in seconds

        Returns:
            Queries per second
        """
        if duration_seconds <= 0:
            return 0.0
        return round(query_count / duration_seconds, 2)

    def calculate_tps(
        self,
        transaction_count: int,
        duration_seconds: float,
    ) -> float:
        """
        Calculate transactions per second.

        Args:
            transaction_count: Total transactions completed
            duration_seconds: Time period in seconds

        Returns:
            Transactions per second
        """
        if duration_seconds <= 0:
            return 0.0
        return round(transaction_count / duration_seconds, 2)

    def calculate_iops(
        self,
        read_operations: int,
        write_operations: int,
        duration_seconds: float,
    ) -> Dict[str, float]:
        """
        Calculate I/O operations per second.

        Args:
            read_operations: Total read operations
            write_operations: Total write operations
            duration_seconds: Time period in seconds

        Returns:
            Dictionary with read_iops, write_iops, and total_iops
        """
        if duration_seconds <= 0:
            return {"read_iops": 0.0, "write_iops": 0.0, "total_iops": 0.0}

        read_iops = read_operations / duration_seconds
        write_iops = write_operations / duration_seconds

        return {
            "read_iops": round(read_iops, 2),
            "write_iops": round(write_iops, 2),
            "total_iops": round(read_iops + write_iops, 2),
        }

    def calculate_throughput_by_type(
        self,
        query_types: Sequence[QueryType],
        duration_seconds: float,
    ) -> Dict[str, float]:
        """
        Calculate throughput breakdown by query type.

        Args:
            query_types: Sequence of query types executed
            duration_seconds: Time period in seconds

        Returns:
            Dictionary mapping query type to QPS
        """
        if duration_seconds <= 0:
            return {}

        type_counts: Dict[str, int] = {}
        for query_type in query_types:
            type_name = query_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        return {
            query_type: round(count / duration_seconds, 2)
            for query_type, count in type_counts.items()
        }

    def calculate_bytes_throughput(
        self,
        bytes_read: int,
        bytes_written: int,
        duration_seconds: float,
    ) -> Dict[str, float]:
        """
        Calculate data throughput in MB/s.

        Args:
            bytes_read: Total bytes read
            bytes_written: Total bytes written
            duration_seconds: Time period in seconds

        Returns:
            Dictionary with read_mbps, write_mbps, and total_mbps
        """
        if duration_seconds <= 0:
            return {"read_mbps": 0.0, "write_mbps": 0.0, "total_mbps": 0.0}

        mb_factor = 1024 * 1024
        read_mbps = (bytes_read / mb_factor) / duration_seconds
        write_mbps = (bytes_written / mb_factor) / duration_seconds

        return {
            "read_mbps": round(read_mbps, 2),
            "write_mbps": round(write_mbps, 2),
            "total_mbps": round(read_mbps + write_mbps, 2),
        }

    def calculate_capacity(
        self,
        current_qps: float,
        max_qps: float,
    ) -> Dict[str, float]:
        """
        Calculate capacity utilization and headroom.

        Args:
            current_qps: Current queries per second
            max_qps: Maximum sustainable QPS

        Returns:
            Dictionary with utilization_percent and headroom_percent
        """
        if max_qps <= 0:
            return {"utilization_percent": 100.0, "headroom_percent": 0.0}

        utilization = (current_qps / max_qps) * 100
        headroom = 100 - utilization

        return {
            "utilization_percent": round(min(utilization, 100), 2),
            "headroom_percent": round(max(headroom, 0), 2),
        }
