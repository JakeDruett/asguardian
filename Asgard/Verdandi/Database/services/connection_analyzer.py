"""
Connection Pool Analyzer

Analyzes database connection pool performance.
"""

from typing import List, Optional

from Asgard.Verdandi.Database.models.database_models import ConnectionPoolMetrics


class ConnectionAnalyzer:
    """
    Analyzer for database connection pool metrics.

    Calculates utilization, wait times, and provides recommendations.

    Example:
        analyzer = ConnectionAnalyzer()
        metrics = analyzer.analyze(
            pool_size=20,
            active=15,
            waiting=3,
            wait_times=[10, 20, 15, 25]
        )
        print(f"Utilization: {metrics.utilization_percent}%")
    """

    def analyze(
        self,
        pool_size: int,
        active_connections: int,
        idle_connections: Optional[int] = None,
        waiting_requests: int = 0,
        wait_times_ms: Optional[List[float]] = None,
        connection_errors: int = 0,
        timeout_count: int = 0,
    ) -> ConnectionPoolMetrics:
        """
        Analyze connection pool metrics.

        Args:
            pool_size: Total pool size
            active_connections: Currently active connections
            idle_connections: Idle connections (calculated if not provided)
            waiting_requests: Requests waiting for connection
            wait_times_ms: List of wait times for connections
            connection_errors: Count of connection errors
            timeout_count: Count of connection timeouts

        Returns:
            ConnectionPoolMetrics with analysis
        """
        if idle_connections is None:
            idle_connections = max(0, pool_size - active_connections)

        utilization = (active_connections / pool_size) * 100 if pool_size > 0 else 0

        avg_wait = 0.0
        max_wait = 0.0
        if wait_times_ms:
            avg_wait = sum(wait_times_ms) / len(wait_times_ms)
            max_wait = max(wait_times_ms)

        return ConnectionPoolMetrics(
            pool_size=pool_size,
            active_connections=active_connections,
            idle_connections=idle_connections,
            waiting_requests=waiting_requests,
            utilization_percent=round(utilization, 2),
            average_wait_time_ms=round(avg_wait, 2),
            max_wait_time_ms=round(max_wait, 2),
            connection_errors=connection_errors,
            timeout_count=timeout_count,
        )

    def calculate_optimal_pool_size(
        self,
        concurrent_requests: int,
        avg_query_time_ms: float,
        target_wait_time_ms: float = 50.0,
    ) -> int:
        """
        Calculate optimal pool size based on workload.

        Uses Little's Law: L = lambda * W
        Where L = connections needed, lambda = arrival rate, W = service time

        Args:
            concurrent_requests: Average concurrent requests
            avg_query_time_ms: Average query execution time
            target_wait_time_ms: Target maximum wait time

        Returns:
            Recommended pool size
        """
        avg_query_seconds = avg_query_time_ms / 1000

        base_connections = concurrent_requests * avg_query_seconds

        buffer_factor = 1.5
        optimal = int(base_connections * buffer_factor)

        return max(optimal, concurrent_requests, 5)

    def get_recommendations(
        self,
        metrics: ConnectionPoolMetrics,
    ) -> List[str]:
        """
        Generate recommendations based on connection metrics.

        Args:
            metrics: Connection pool metrics

        Returns:
            List of recommendations
        """
        recommendations = []

        if metrics.utilization_percent > 90:
            recommendations.append(
                f"Pool utilization is high ({metrics.utilization_percent:.1f}%). "
                "Consider increasing pool size."
            )

        if metrics.utilization_percent < 20 and metrics.pool_size > 10:
            recommendations.append(
                f"Pool utilization is low ({metrics.utilization_percent:.1f}%). "
                "Consider reducing pool size to free resources."
            )

        if metrics.waiting_requests > 0:
            recommendations.append(
                f"{metrics.waiting_requests} requests waiting for connections. "
                "Pool size may be insufficient for current load."
            )

        if metrics.average_wait_time_ms > 100:
            recommendations.append(
                f"Average connection wait time is {metrics.average_wait_time_ms:.1f}ms. "
                "Consider increasing pool size or optimizing queries."
            )

        if metrics.connection_errors > 0:
            recommendations.append(
                f"{metrics.connection_errors} connection errors detected. "
                "Check database server health and network connectivity."
            )

        if metrics.timeout_count > 0:
            recommendations.append(
                f"{metrics.timeout_count} connection timeouts detected. "
                "Review timeout settings and connection pool configuration."
            )

        return recommendations
