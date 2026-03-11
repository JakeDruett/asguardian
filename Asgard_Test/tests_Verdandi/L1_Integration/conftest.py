"""
Fixtures for Verdandi L1 Integration Tests.

Provides sample data for testing web vitals, database metrics, and statistical analysis workflows.
"""

from datetime import datetime, timedelta
from typing import List

import pytest

from Asgard.Verdandi.Web.models.web_models import CoreWebVitalsInput
from Asgard.Verdandi.Database.models.database_models import QueryMetricsInput, QueryType
from Asgard.Verdandi.Analysis.models.analysis_models import SLAConfig, ApdexConfig


@pytest.fixture
def good_web_vitals_data() -> CoreWebVitalsInput:
    """Web vitals data with all good ratings."""
    return CoreWebVitalsInput(
        lcp_ms=2000.0,
        fid_ms=50.0,
        cls=0.05,
        inp_ms=150.0,
        ttfb_ms=600.0,
        fcp_ms=1500.0,
    )


@pytest.fixture
def poor_web_vitals_data() -> CoreWebVitalsInput:
    """Web vitals data with all poor ratings."""
    return CoreWebVitalsInput(
        lcp_ms=5000.0,
        fid_ms=400.0,
        cls=0.4,
        inp_ms=600.0,
        ttfb_ms=2000.0,
        fcp_ms=3500.0,
    )


@pytest.fixture
def mixed_web_vitals_data() -> CoreWebVitalsInput:
    """Web vitals data with mixed good/poor ratings."""
    return CoreWebVitalsInput(
        lcp_ms=2000.0,
        fid_ms=50.0,
        cls=0.5,
        inp_ms=150.0,
        ttfb_ms=700.0,
        fcp_ms=1600.0,
    )


@pytest.fixture
def needs_improvement_web_vitals_data() -> CoreWebVitalsInput:
    """Web vitals data that needs improvement."""
    return CoreWebVitalsInput(
        lcp_ms=3200.0,
        fid_ms=200.0,
        cls=0.18,
        inp_ms=350.0,
        ttfb_ms=1200.0,
        fcp_ms=2200.0,
    )


@pytest.fixture
def partial_web_vitals_data() -> CoreWebVitalsInput:
    """Web vitals data with only some metrics."""
    return CoreWebVitalsInput(
        lcp_ms=2100.0,
        cls=0.08,
        ttfb_ms=650.0,
    )


@pytest.fixture
def fast_query_metrics() -> List[QueryMetricsInput]:
    """Fast database queries with good performance."""
    return [
        QueryMetricsInput(
            query_id=f"query_{i}",
            query_type=QueryType.SELECT,
            execution_time_ms=50.0 + (i * 5),
            rows_examined=100,
            rows_affected=100,
            used_index=True,
            timestamp=datetime.now().isoformat(),
        )
        for i in range(10)
    ]


@pytest.fixture
def slow_query_metrics() -> List[QueryMetricsInput]:
    """Slow database queries with performance issues."""
    queries = []

    for i in range(5):
        queries.append(
            QueryMetricsInput(
                query_id=f"slow_select_{i}",
                query_type=QueryType.SELECT,
                execution_time_ms=500.0 + (i * 100),
                rows_examined=10000,
                rows_affected=100,
                used_index=False,
                timestamp=datetime.now().isoformat(),
            )
        )

    for i in range(3):
        queries.append(
            QueryMetricsInput(
                query_id=f"slow_update_{i}",
                query_type=QueryType.UPDATE,
                execution_time_ms=300.0 + (i * 50),
                rows_examined=5000,
                rows_affected=50,
                used_index=False,
                timestamp=datetime.now().isoformat(),
            )
        )

    queries.append(
        QueryMetricsInput(
            query_id="slow_insert",
            query_type=QueryType.INSERT,
            execution_time_ms=200.0,
            rows_examined=0,
            rows_affected=1,
            used_index=True,
            timestamp=datetime.now().isoformat(),
        )
    )

    return queries


@pytest.fixture
def mixed_query_metrics() -> List[QueryMetricsInput]:
    """Mix of fast and slow queries."""
    queries = []

    for i in range(20):
        queries.append(
            QueryMetricsInput(
                query_id=f"fast_query_{i}",
                query_type=QueryType.SELECT,
                execution_time_ms=30.0 + (i * 2),
                rows_examined=50,
                rows_affected=50,
                used_index=True,
                timestamp=datetime.now().isoformat(),
            )
        )

    for i in range(5):
        queries.append(
            QueryMetricsInput(
                query_id=f"slow_query_{i}",
                query_type=QueryType.SELECT,
                execution_time_ms=400.0 + (i * 50),
                rows_examined=5000,
                rows_affected=100,
                used_index=False,
                timestamp=datetime.now().isoformat(),
            )
        )

    return queries


@pytest.fixture
def query_metrics_by_type() -> List[QueryMetricsInput]:
    """Queries demonstrating different query types."""
    queries = []

    for i in range(10):
        queries.append(
            QueryMetricsInput(
                query_id=f"select_{i}",
                query_type=QueryType.SELECT,
                execution_time_ms=50.0,
                rows_examined=100,
                rows_affected=100,
                used_index=True,
            )
        )

    for i in range(5):
        queries.append(
            QueryMetricsInput(
                query_id=f"insert_{i}",
                query_type=QueryType.INSERT,
                execution_time_ms=30.0,
                rows_examined=0,
                rows_affected=1,
                used_index=True,
            )
        )

    for i in range(3):
        queries.append(
            QueryMetricsInput(
                query_id=f"update_{i}",
                query_type=QueryType.UPDATE,
                execution_time_ms=80.0,
                rows_examined=1000,
                rows_affected=10,
                used_index=True,
            )
        )

    queries.append(
        QueryMetricsInput(
            query_id="delete_1",
            query_type=QueryType.DELETE,
            execution_time_ms=60.0,
            rows_examined=100,
            rows_affected=5,
            used_index=True,
        )
    )

    return queries


@pytest.fixture
def response_times_good_performance() -> List[float]:
    """Response times with good performance for SLA/trend analysis."""
    return [
        100.0, 105.0, 110.0, 108.0, 112.0,
        115.0, 118.0, 120.0, 122.0, 125.0,
        128.0, 130.0, 132.0, 135.0, 138.0,
        140.0, 142.0, 145.0, 148.0, 150.0,
    ]


@pytest.fixture
def response_times_degrading() -> List[float]:
    """Response times showing degrading performance trend."""
    return [
        100.0, 120.0, 140.0, 160.0, 180.0,
        200.0, 220.0, 240.0, 260.0, 280.0,
        300.0, 320.0, 340.0, 360.0, 380.0,
        400.0, 420.0, 440.0, 460.0, 480.0,
    ]


@pytest.fixture
def response_times_improving() -> List[float]:
    """Response times showing improving performance trend."""
    return [
        500.0, 480.0, 460.0, 440.0, 420.0,
        400.0, 380.0, 360.0, 340.0, 320.0,
        300.0, 280.0, 260.0, 240.0, 220.0,
        200.0, 180.0, 160.0, 140.0, 120.0,
    ]


@pytest.fixture
def response_times_stable() -> List[float]:
    """Response times showing stable performance."""
    base = 150.0
    return [base + i % 3 for i in range(20)]


@pytest.fixture
def response_times_with_anomalies() -> List[float]:
    """Response times with anomalous spikes."""
    normal = [100.0] * 15
    anomalies = [100.0, 100.0, 1000.0, 100.0, 100.0, 2000.0, 100.0, 100.0]
    return normal + anomalies


@pytest.fixture
def time_series_7_days() -> List[float]:
    """Time series data spanning 7 days (hourly samples)."""
    hours = 24 * 7
    base = 200.0
    trend = 2.0
    return [base + (i * trend) + ((i % 24) * 10) for i in range(hours)]


@pytest.fixture
def bimodal_distribution() -> List[float]:
    """Bimodal distribution for testing percentile calculations."""
    fast_responses = [50.0 + i for i in range(50)]
    slow_responses = [500.0 + i for i in range(50)]
    return fast_responses + slow_responses


@pytest.fixture
def uniform_distribution() -> List[float]:
    """Uniform distribution for testing."""
    return [float(i) for i in range(1, 101)]


@pytest.fixture
def normal_like_distribution() -> List[float]:
    """Approximation of normal distribution."""
    mean = 200.0
    data = []
    for i in range(100):
        offset = (i - 50) ** 2 / 50
        value = mean - offset if i < 50 else mean - (100 - i - 50) ** 2 / 50
        data.append(max(50.0, value))
    return sorted(data)


@pytest.fixture
def sla_config_strict() -> SLAConfig:
    """Strict SLA configuration."""
    return SLAConfig(
        target_percentile=95.0,
        threshold_ms=200.0,
        warning_threshold_percent=90.0,
        availability_target=99.9,
        error_rate_threshold=0.5,
    )


@pytest.fixture
def sla_config_lenient() -> SLAConfig:
    """Lenient SLA configuration."""
    return SLAConfig(
        target_percentile=95.0,
        threshold_ms=1000.0,
        warning_threshold_percent=80.0,
        availability_target=99.0,
        error_rate_threshold=2.0,
    )


@pytest.fixture
def apdex_config_standard() -> ApdexConfig:
    """Standard Apdex configuration."""
    return ApdexConfig(
        threshold_ms=500.0,
        frustration_multiplier=4.0,
    )


@pytest.fixture
def apdex_config_strict() -> ApdexConfig:
    """Strict Apdex configuration."""
    return ApdexConfig(
        threshold_ms=100.0,
        frustration_multiplier=4.0,
    )


@pytest.fixture
def multiple_time_windows() -> List[List[float]]:
    """Multiple time windows for testing SLA compliance over time."""
    return [
        [100.0 + i for i in range(20)],
        [120.0 + i for i in range(20)],
        [140.0 + i for i in range(20)],
        [300.0 + i for i in range(20)],
        [150.0 + i for i in range(20)],
    ]
