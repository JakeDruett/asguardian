"""
Unit tests for PercentileCalculator.
"""

import pytest

from Asgard.Verdandi.Analysis import PercentileCalculator


class TestPercentileCalculator:
    """Tests for PercentileCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = PercentileCalculator()

    def test_calculate_basic_dataset(self):
        """Test percentile calculation with basic dataset."""
        data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        result = self.calculator.calculate(data)

        assert result.sample_count == 10
        assert result.min_value == 1
        assert result.max_value == 10
        assert result.mean == 5.5
        assert result.median == 5.5

    def test_calculate_single_value(self):
        """Test percentile calculation with single value."""
        data = [100]
        result = self.calculator.calculate(data)

        assert result.sample_count == 1
        assert result.min_value == 100
        assert result.max_value == 100
        assert result.p50 == 100
        assert result.p99 == 100

    def test_calculate_empty_raises(self):
        """Test that empty dataset raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            self.calculator.calculate([])

    def test_calculate_percentile_specific(self):
        """Test specific percentile calculation."""
        data = list(range(1, 101))
        p95 = self.calculator.calculate_percentile(data, 95)

        assert 94 <= p95 <= 96

    def test_calculate_percentile_invalid_range(self):
        """Test that invalid percentile range raises ValueError."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            self.calculator.calculate_percentile([1, 2, 3], 150)

    def test_calculate_custom_percentiles(self):
        """Test custom percentile calculation."""
        data = list(range(1, 101))
        percentiles = self.calculator.calculate_custom_percentiles(
            data, [10, 25, 50, 75, 90]
        )

        assert 10 in percentiles
        assert 50 in percentiles
        assert percentiles[50] == 50.5

    def test_calculate_histogram(self):
        """Test histogram bucket calculation."""
        data = [5, 15, 25, 55, 110, 260, 600, 1100, 3000, 15000]
        histogram = self.calculator.calculate_histogram(data)

        assert "<=10" in histogram
        assert ">10000" in histogram
        assert histogram["<=10"] == 1
        assert histogram[">10000"] == 1

    def test_std_dev_calculation(self):
        """Test standard deviation calculation."""
        data = [2, 4, 4, 4, 5, 5, 7, 9]
        result = self.calculator.calculate(data)

        assert result.std_dev == pytest.approx(2.0, abs=0.1)
