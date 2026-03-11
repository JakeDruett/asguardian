"""
Unit tests for ConnectionAnalyzer.
"""

import pytest

from Asgard.Verdandi.Database import ConnectionAnalyzer


class TestConnectionAnalyzer:
    """Tests for ConnectionAnalyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = ConnectionAnalyzer()

    def test_analyze_basic(self):
        """Test basic connection analysis."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=10,
            idle_connections=10,
            waiting_requests=0,
        )

        assert metrics.pool_size == 20
        assert metrics.active_connections == 10
        assert metrics.idle_connections == 10
        assert metrics.utilization_percent == 50.0

    def test_analyze_calculate_idle(self):
        """Test automatic idle connection calculation."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=15,
        )

        assert metrics.idle_connections == 5
        assert metrics.utilization_percent == 75.0

    def test_analyze_full_utilization(self):
        """Test analysis with full pool utilization."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=20,
        )

        assert metrics.utilization_percent == 100.0
        assert metrics.idle_connections == 0

    def test_analyze_over_utilization(self):
        """Test analysis when active exceeds pool size."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=25,
        )

        assert metrics.idle_connections == 0
        assert metrics.utilization_percent > 100

    def test_analyze_with_wait_times(self):
        """Test analysis with connection wait times."""
        wait_times = [10.0, 20.0, 15.0, 25.0, 12.0]

        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=18,
            waiting_requests=5,
            wait_times_ms=wait_times,
        )

        assert metrics.average_wait_time_ms == pytest.approx(16.4, abs=0.1)
        assert metrics.max_wait_time_ms == 25.0
        assert metrics.waiting_requests == 5

    def test_analyze_no_wait_times(self):
        """Test analysis without wait time data."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=10,
        )

        assert metrics.average_wait_time_ms == 0.0
        assert metrics.max_wait_time_ms == 0.0

    def test_analyze_with_errors(self):
        """Test analysis with connection errors."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=10,
            connection_errors=5,
            timeout_count=3,
        )

        assert metrics.connection_errors == 5
        assert metrics.timeout_count == 3

    def test_analyze_zero_pool_size(self):
        """Test analysis with zero pool size."""
        metrics = self.analyzer.analyze(
            pool_size=0,
            active_connections=0,
        )

        assert metrics.utilization_percent == 0.0

    def test_calculate_optimal_pool_size_basic(self):
        """Test optimal pool size calculation."""
        optimal = self.analyzer.calculate_optimal_pool_size(
            concurrent_requests=10,
            avg_query_time_ms=100,
        )

        assert optimal >= 10
        assert optimal >= 5

    def test_calculate_optimal_pool_size_high_concurrency(self):
        """Test optimal pool size with high concurrency."""
        optimal = self.analyzer.calculate_optimal_pool_size(
            concurrent_requests=100,
            avg_query_time_ms=50,
        )

        assert optimal >= 100

    def test_calculate_optimal_pool_size_slow_queries(self):
        """Test optimal pool size with slow queries."""
        optimal = self.analyzer.calculate_optimal_pool_size(
            concurrent_requests=10,
            avg_query_time_ms=1000,
        )

        assert optimal >= 10

    def test_calculate_optimal_pool_size_minimum(self):
        """Test optimal pool size has minimum value."""
        optimal = self.analyzer.calculate_optimal_pool_size(
            concurrent_requests=1,
            avg_query_time_ms=10,
        )

        assert optimal >= 5

    def test_get_recommendations_high_utilization(self):
        """Test recommendations for high pool utilization."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=19,
        )

        recommendations = self.analyzer.get_recommendations(metrics)

        assert len(recommendations) > 0
        assert any("utilization" in rec.lower() for rec in recommendations)

    def test_get_recommendations_low_utilization(self):
        """Test recommendations for low pool utilization."""
        metrics = self.analyzer.analyze(
            pool_size=100,
            active_connections=5,
        )

        recommendations = self.analyzer.get_recommendations(metrics)

        assert len(recommendations) > 0
        assert any("low" in rec.lower() or "reducing" in rec.lower() for rec in recommendations)

    def test_get_recommendations_waiting_requests(self):
        """Test recommendations when requests are waiting."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=18,
            waiting_requests=10,
        )

        recommendations = self.analyzer.get_recommendations(metrics)

        assert any("waiting" in rec.lower() for rec in recommendations)

    def test_get_recommendations_high_wait_time(self):
        """Test recommendations for high wait times."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=15,
            wait_times_ms=[100, 150, 200, 180, 120],
        )

        recommendations = self.analyzer.get_recommendations(metrics)

        assert any("wait" in rec.lower() for rec in recommendations)

    def test_get_recommendations_connection_errors(self):
        """Test recommendations for connection errors."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=10,
            connection_errors=15,
        )

        recommendations = self.analyzer.get_recommendations(metrics)

        assert any("error" in rec.lower() for rec in recommendations)

    def test_get_recommendations_timeouts(self):
        """Test recommendations for connection timeouts."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=10,
            timeout_count=5,
        )

        recommendations = self.analyzer.get_recommendations(metrics)

        assert any("timeout" in rec.lower() for rec in recommendations)

    def test_get_recommendations_healthy_pool(self):
        """Test no recommendations for healthy pool."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=10,
            waiting_requests=0,
            wait_times_ms=[5, 8, 6, 7, 5],
            connection_errors=0,
            timeout_count=0,
        )

        recommendations = self.analyzer.get_recommendations(metrics)

        assert len(recommendations) == 0

    def test_utilization_rounding(self):
        """Test that utilization is rounded to 2 decimal places."""
        metrics = self.analyzer.analyze(
            pool_size=7,
            active_connections=3,
        )

        assert metrics.utilization_percent == pytest.approx(42.86, abs=0.01)

    def test_wait_time_rounding(self):
        """Test that wait times are rounded to 2 decimal places."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=10,
            wait_times_ms=[10.123, 20.456, 15.789],
        )

        assert abs(metrics.average_wait_time_ms - round(metrics.average_wait_time_ms, 2)) < 0.01
        assert abs(metrics.max_wait_time_ms - round(metrics.max_wait_time_ms, 2)) < 0.01

    def test_multiple_recommendation_triggers(self):
        """Test multiple recommendations triggered simultaneously."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=19,
            waiting_requests=10,
            wait_times_ms=[150, 200, 180, 220],
            connection_errors=5,
            timeout_count=3,
        )

        recommendations = self.analyzer.get_recommendations(metrics)

        assert len(recommendations) >= 4

    def test_edge_case_empty_wait_times(self):
        """Test analysis with empty wait times list."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=10,
            wait_times_ms=[],
        )

        assert metrics.average_wait_time_ms == 0.0
        assert metrics.max_wait_time_ms == 0.0

    def test_edge_case_single_wait_time(self):
        """Test analysis with single wait time."""
        metrics = self.analyzer.analyze(
            pool_size=20,
            active_connections=10,
            wait_times_ms=[50.0],
        )

        assert metrics.average_wait_time_ms == 50.0
        assert metrics.max_wait_time_ms == 50.0
