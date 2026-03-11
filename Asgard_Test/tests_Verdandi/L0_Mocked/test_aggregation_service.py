"""
Unit tests for AggregationService.
"""

import pytest
from datetime import datetime, timedelta

from Asgard.Verdandi.Analysis import AggregationService
from Asgard.Verdandi.Analysis.models.analysis_models import AggregationConfig


class TestAggregationService:
    """Tests for AggregationService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = AggregationService()

    def test_aggregate_empty_raises(self):
        """Test that empty dataset raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            self.service.aggregate([])

    def test_aggregate_basic(self):
        """Test basic aggregation."""
        values = [10, 20, 30, 40, 50]

        result = self.service.aggregate(values)

        assert result.sample_count == 5
        assert result.sum_value == 150
        assert result.mean == 30.0
        assert result.min_value == 10
        assert result.max_value == 50

    def test_aggregate_with_time_window(self):
        """Test aggregation with specific time window."""
        values = [10, 20, 30, 40, 50]
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 10, 1, 0)

        result = self.service.aggregate(values, window_start=start, window_end=end)

        assert result.window_start == start.isoformat()
        assert result.window_end == end.isoformat()
        assert result.throughput == pytest.approx(5.0 / 60, abs=0.01)

    def test_aggregate_with_percentiles(self):
        """Test aggregation including percentiles."""
        config = AggregationConfig(include_percentiles=True)
        service = AggregationService(config)
        values = list(range(1, 101))

        result = service.aggregate(values)

        assert result.percentiles is not None
        assert result.percentiles.p50 == pytest.approx(50.5, abs=1)
        assert result.percentiles.p95 == pytest.approx(95, abs=2)

    def test_aggregate_with_histogram(self):
        """Test aggregation including histogram."""
        config = AggregationConfig(
            include_histograms=True,
            histogram_buckets=[10, 25, 50, 100],
        )
        service = AggregationService(config)
        values = [5, 15, 35, 75, 150]

        result = service.aggregate(values)

        assert result.histogram is not None
        assert isinstance(result.histogram, dict)

    def test_aggregate_without_percentiles(self):
        """Test aggregation without percentiles."""
        config = AggregationConfig(include_percentiles=False)
        service = AggregationService(config)
        values = [10, 20, 30, 40, 50]

        result = service.aggregate(values)

        assert result.percentiles is None

    def test_aggregate_by_windows(self):
        """Test aggregation into multiple time windows."""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        timestamps = [
            datetime(2024, 1, 1, 10, 0, i)
            for i in range(10)
        ]

        results = self.service.aggregate_by_windows(
            values,
            timestamps,
            window_seconds=3,
        )

        assert len(results) > 0
        assert all(r.sample_count > 0 for r in results)

    def test_aggregate_by_windows_mismatched_lengths(self):
        """Test that mismatched lengths raise ValueError."""
        values = [10, 20, 30]
        timestamps = [datetime(2024, 1, 1, 10, 0, 0)]

        with pytest.raises(ValueError, match="same length"):
            self.service.aggregate_by_windows(values, timestamps)

    def test_aggregate_by_windows_empty(self):
        """Test aggregation by windows with empty data."""
        results = self.service.aggregate_by_windows([], [])

        assert results == []

    def test_calculate_throughput(self):
        """Test throughput calculation."""
        throughput = self.service.calculate_throughput(
            request_count=1000,
            duration_seconds=60,
        )

        assert throughput == pytest.approx(16.67, abs=0.01)

    def test_calculate_throughput_zero_duration(self):
        """Test throughput with zero duration."""
        throughput = self.service.calculate_throughput(
            request_count=1000,
            duration_seconds=0,
        )

        assert throughput == 0.0

    def test_calculate_rate(self):
        """Test rate calculation."""
        rate = self.service.calculate_rate(count=25, total=100)

        assert rate == 25.0

    def test_calculate_rate_zero_total(self):
        """Test rate with zero total."""
        rate = self.service.calculate_rate(count=25, total=0)

        assert rate == 0.0

    def test_custom_window_size(self):
        """Test aggregation with custom window size."""
        config = AggregationConfig(window_size_seconds=300)
        service = AggregationService(config)
        values = [10, 20, 30]

        result = service.aggregate(values)

        start = datetime.fromisoformat(result.window_start)
        end = datetime.fromisoformat(result.window_end)
        duration = (end - start).total_seconds()

        assert duration == 300

    def test_single_value_aggregation(self):
        """Test aggregation with single value."""
        values = [50.0]

        result = self.service.aggregate(values)

        assert result.sample_count == 1
        assert result.mean == 50.0
        assert result.min_value == 50.0
        assert result.max_value == 50.0

    def test_large_dataset_aggregation(self):
        """Test aggregation with large dataset."""
        values = list(range(1, 10001))

        result = self.service.aggregate(values)

        assert result.sample_count == 10000
        assert result.sum_value == sum(values)
        assert result.mean == pytest.approx(5000.5, abs=0.1)

    def test_aggregate_by_windows_sorting(self):
        """Test that aggregate_by_windows sorts data correctly."""
        values = [50, 20, 80, 10, 90]
        timestamps = [
            datetime(2024, 1, 1, 10, 0, 4),
            datetime(2024, 1, 1, 10, 0, 1),
            datetime(2024, 1, 1, 10, 0, 8),
            datetime(2024, 1, 1, 10, 0, 0),
            datetime(2024, 1, 1, 10, 0, 9),
        ]

        results = self.service.aggregate_by_windows(
            values,
            timestamps,
            window_seconds=3,
        )

        assert len(results) > 0

    def test_throughput_calculation_in_aggregate(self):
        """Test that throughput is calculated correctly in aggregate."""
        values = [10, 20, 30, 40, 50]
        start = datetime(2024, 1, 1, 10, 0, 0)
        end = datetime(2024, 1, 1, 10, 0, 10)

        result = self.service.aggregate(values, window_start=start, window_end=end)

        expected_throughput = 5 / 10
        assert result.throughput == pytest.approx(expected_throughput, abs=0.01)

    def test_negative_values(self):
        """Test aggregation with negative values."""
        values = [-10, -5, 0, 5, 10]

        result = self.service.aggregate(values)

        assert result.mean == 0.0
        assert result.min_value == -10
        assert result.max_value == 10

    def test_floating_point_values(self):
        """Test aggregation with floating point values."""
        values = [10.5, 20.7, 30.3, 40.1, 50.9]

        result = self.service.aggregate(values)

        assert result.sum_value == pytest.approx(152.5, abs=0.1)
        assert result.mean == pytest.approx(30.5, abs=0.1)

    def test_histogram_bucket_configuration(self):
        """Test that custom histogram buckets work correctly."""
        config = AggregationConfig(
            include_histograms=True,
            histogram_buckets=[10, 50, 100, 500, 1000],
        )
        service = AggregationService(config)
        values = [5, 25, 75, 250, 750, 1500]

        result = service.aggregate(values)

        assert result.histogram is not None
