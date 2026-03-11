"""
Comprehensive L0 Unit Tests for PercentileCalculator Service

Tests all functionality of the PercentileCalculator including:
- Standard percentile calculations (P50, P75, P90, P95, P99, P99.9)
- Custom percentile calculations
- Histogram generation
- Edge cases and error handling
"""

import pytest
import math

from Asgard.Verdandi.Analysis.services.percentile_calculator import PercentileCalculator
from Asgard.Verdandi.Analysis.models.analysis_models import PercentileResult


class TestPercentileCalculatorBasics:
    """Tests for basic PercentileCalculator functionality."""

    def test_calculator_initialization(self):
        """Test that calculator can be instantiated."""
        calc = PercentileCalculator()
        assert calc is not None

    def test_calculate_simple_dataset(self):
        """Test calculate with a simple dataset."""
        calc = PercentileCalculator()
        values = [100, 150, 200, 250, 300]

        result = calc.calculate(values)

        assert isinstance(result, PercentileResult)
        assert result.sample_count == 5
        assert result.min_value == 100.0
        assert result.max_value == 300.0
        assert result.mean == 200.0

    def test_calculate_empty_dataset_raises_error(self):
        """Test that empty dataset raises ValueError."""
        calc = PercentileCalculator()

        with pytest.raises(ValueError, match="Cannot calculate percentiles for empty dataset"):
            calc.calculate([])

    def test_calculate_single_value(self):
        """Test calculate with single value."""
        calc = PercentileCalculator()
        values = [150.0]

        result = calc.calculate(values)

        assert result.sample_count == 1
        assert result.min_value == 150.0
        assert result.max_value == 150.0
        assert result.mean == 150.0
        assert result.p50 == 150.0
        assert result.p99 == 150.0
        assert result.std_dev == 0.0

    def test_calculate_two_values(self):
        """Test calculate with two values."""
        calc = PercentileCalculator()
        values = [100.0, 200.0]

        result = calc.calculate(values)

        assert result.sample_count == 2
        assert result.min_value == 100.0
        assert result.max_value == 200.0
        assert result.mean == 150.0
        assert result.p50 == 150.0  # Median of 100 and 200


class TestPercentileCalculations:
    """Tests for specific percentile calculations."""

    def test_percentile_calculation_p50_median(self):
        """Test P50 (median) calculation."""
        calc = PercentileCalculator()

        # Odd number of values
        values = [1, 2, 3, 4, 5]
        result = calc.calculate(values)
        assert result.p50 == 3.0
        assert result.median == 3.0

        # Even number of values
        values = [1, 2, 3, 4]
        result = calc.calculate(values)
        assert result.p50 == 2.5

    def test_percentile_calculation_p95(self):
        """Test P95 calculation."""
        calc = PercentileCalculator()
        values = list(range(1, 101))  # 1 to 100

        result = calc.calculate(values)

        # P95 of 1-100 should be close to 95
        assert 94.0 <= result.p95 <= 96.0

    def test_percentile_calculation_p99(self):
        """Test P99 calculation."""
        calc = PercentileCalculator()
        values = list(range(1, 1001))  # 1 to 1000

        result = calc.calculate(values)

        # P99 of 1-1000 should be close to 990
        assert 989.0 <= result.p99 <= 991.0

    def test_percentile_calculation_p999(self):
        """Test P99.9 calculation."""
        calc = PercentileCalculator()
        values = list(range(1, 10001))  # 1 to 10000

        result = calc.calculate(values)

        # P99.9 of 1-10000 should be close to 9990
        assert 9989.0 <= result.p999 <= 9991.0

    def test_percentile_all_same_values(self):
        """Test percentiles when all values are the same."""
        calc = PercentileCalculator()
        values = [42.0] * 100

        result = calc.calculate(values)

        assert result.p50 == 42.0
        assert result.p75 == 42.0
        assert result.p90 == 42.0
        assert result.p95 == 42.0
        assert result.p99 == 42.0
        assert result.p999 == 42.0
        assert result.std_dev == 0.0


class TestStatisticalMeasures:
    """Tests for statistical measures (mean, std_dev, etc.)."""

    def test_mean_calculation(self):
        """Test mean calculation."""
        calc = PercentileCalculator()
        values = [10, 20, 30, 40, 50]

        result = calc.calculate(values)

        assert result.mean == 30.0

    def test_standard_deviation_calculation(self):
        """Test standard deviation calculation."""
        calc = PercentileCalculator()
        values = [2, 4, 4, 4, 5, 5, 7, 9]

        result = calc.calculate(values)

        # Expected std dev is 2.0
        assert abs(result.std_dev - 2.0) < 0.01

    def test_min_max_calculation(self):
        """Test min and max calculations."""
        calc = PercentileCalculator()
        values = [15, 3, 42, 7, 99, 1, 28]

        result = calc.calculate(values)

        assert result.min_value == 1.0
        assert result.max_value == 99.0

    def test_range_property(self):
        """Test the range property."""
        calc = PercentileCalculator()
        values = [10, 20, 30, 40, 50]

        result = calc.calculate(values)

        assert result.range == 40.0  # 50 - 10


class TestCalculatePercentile:
    """Tests for the calculate_percentile method."""

    def test_calculate_percentile_50(self):
        """Test calculating 50th percentile."""
        calc = PercentileCalculator()
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        p50 = calc.calculate_percentile(values, 50)

        assert p50 == 5.5

    def test_calculate_percentile_with_presorted(self):
        """Test calculate_percentile with presorted=True."""
        calc = PercentileCalculator()
        sorted_values = [1, 2, 3, 4, 5]

        # Should work with presorted flag
        p50 = calc.calculate_percentile(sorted_values, 50, presorted=True)
        assert p50 == 3.0

    def test_calculate_percentile_unsorted_input(self):
        """Test that calculate_percentile handles unsorted input."""
        calc = PercentileCalculator()
        unsorted_values = [5, 2, 8, 1, 9, 3]

        p50 = calc.calculate_percentile(unsorted_values, 50)

        # Should automatically sort
        assert p50 == 4.0  # Median of [1, 2, 3, 5, 8, 9]

    def test_calculate_percentile_0(self):
        """Test calculating 0th percentile (minimum)."""
        calc = PercentileCalculator()
        values = [10, 20, 30, 40, 50]

        p0 = calc.calculate_percentile(values, 0)

        assert p0 == 10.0

    def test_calculate_percentile_100(self):
        """Test calculating 100th percentile (maximum)."""
        calc = PercentileCalculator()
        values = [10, 20, 30, 40, 50]

        p100 = calc.calculate_percentile(values, 100)

        assert p100 == 50.0

    def test_calculate_percentile_empty_raises_error(self):
        """Test that empty dataset raises ValueError."""
        calc = PercentileCalculator()

        with pytest.raises(ValueError, match="Cannot calculate percentile for empty dataset"):
            calc.calculate_percentile([], 50)

    def test_calculate_percentile_invalid_percentile_high(self):
        """Test that percentile > 100 raises ValueError."""
        calc = PercentileCalculator()
        values = [1, 2, 3, 4, 5]

        with pytest.raises(ValueError, match="Percentile must be between 0 and 100"):
            calc.calculate_percentile(values, 101)

    def test_calculate_percentile_invalid_percentile_low(self):
        """Test that percentile < 0 raises ValueError."""
        calc = PercentileCalculator()
        values = [1, 2, 3, 4, 5]

        with pytest.raises(ValueError, match="Percentile must be between 0 and 100"):
            calc.calculate_percentile(values, -1)

    def test_calculate_percentile_single_value(self):
        """Test percentile calculation with single value."""
        calc = PercentileCalculator()
        values = [42.0]

        # Any percentile of a single value should be that value
        assert calc.calculate_percentile(values, 0) == 42.0
        assert calc.calculate_percentile(values, 50) == 42.0
        assert calc.calculate_percentile(values, 100) == 42.0


class TestCustomPercentiles:
    """Tests for calculate_custom_percentiles method."""

    def test_calculate_custom_percentiles(self):
        """Test calculating multiple custom percentiles."""
        calc = PercentileCalculator()
        values = list(range(1, 101))  # 1 to 100
        percentiles = [10, 25, 50, 75, 90]

        result = calc.calculate_custom_percentiles(values, percentiles)

        assert isinstance(result, dict)
        assert len(result) == 5
        assert 10 in result
        assert 25 in result
        assert 50 in result
        assert 75 in result
        assert 90 in result

    def test_calculate_custom_percentiles_values(self):
        """Test that custom percentile values are correct."""
        calc = PercentileCalculator()
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        percentiles = [25, 50, 75]

        result = calc.calculate_custom_percentiles(values, percentiles)

        # Verify approximate values
        assert 20 <= result[25] <= 35
        assert 50 <= result[50] <= 60
        assert 75 <= result[75] <= 85

    def test_calculate_custom_percentiles_empty_list(self):
        """Test custom percentiles with empty percentile list."""
        calc = PercentileCalculator()
        values = [1, 2, 3, 4, 5]
        percentiles = []

        result = calc.calculate_custom_percentiles(values, percentiles)

        assert result == {}

    def test_calculate_custom_percentiles_empty_values_raises_error(self):
        """Test that empty values raises ValueError."""
        calc = PercentileCalculator()

        with pytest.raises(ValueError, match="Cannot calculate percentiles for empty dataset"):
            calc.calculate_custom_percentiles([], [50, 90])


class TestHistogram:
    """Tests for calculate_histogram method."""

    def test_calculate_histogram_default_buckets(self):
        """Test histogram with default buckets."""
        calc = PercentileCalculator()
        values = [5, 15, 35, 75, 150, 300, 600, 1500, 3000, 6000, 15000]

        histogram = calc.calculate_histogram(values)

        assert isinstance(histogram, dict)
        assert len(histogram) > 0
        assert sum(histogram.values()) == len(values)

    def test_calculate_histogram_custom_buckets(self):
        """Test histogram with custom buckets."""
        calc = PercentileCalculator()
        values = [10, 20, 30, 50, 75, 150, 300]
        buckets = [25, 50, 100, 200]

        histogram = calc.calculate_histogram(values, buckets)

        assert isinstance(histogram, dict)
        assert sum(histogram.values()) == len(values)

    def test_calculate_histogram_bucket_distribution(self):
        """Test that values are correctly distributed into buckets."""
        calc = PercentileCalculator()
        values = [5, 15, 25, 35, 45]
        buckets = [10, 20, 30, 40, 50]

        histogram = calc.calculate_histogram(values, buckets)

        # 5 should be in <=10
        # 15 should be in 10-20
        # 25 should be in 20-30
        # 35 should be in 30-40
        # 45 should be in 40-50
        assert histogram["<=10"] == 1
        assert histogram["10-20"] == 1
        assert histogram["20-30"] == 1
        assert histogram["30-40"] == 1
        assert histogram["40-50"] == 1

    def test_calculate_histogram_overflow_bucket(self):
        """Test that values exceeding max bucket go to overflow."""
        calc = PercentileCalculator()
        values = [10, 20, 500, 1000, 5000]
        buckets = [50, 100, 200]

        histogram = calc.calculate_histogram(values, buckets)

        # Values 500, 1000, 5000 should be in >200
        assert histogram[">200"] == 3

    def test_calculate_histogram_empty_buckets(self):
        """Test histogram with some empty buckets."""
        calc = PercentileCalculator()
        values = [5, 95]
        buckets = [10, 50, 100]

        histogram = calc.calculate_histogram(values, buckets)

        # Middle bucket should be empty
        assert histogram["10-50"] == 0
        assert histogram["<=10"] == 1
        assert histogram["50-100"] == 1

    def test_calculate_histogram_unsorted_buckets(self):
        """Test that histogram handles unsorted buckets."""
        calc = PercentileCalculator()
        values = [15, 35, 75]
        buckets = [100, 50, 20]  # Unsorted

        histogram = calc.calculate_histogram(values, buckets)

        # Should still work correctly
        assert sum(histogram.values()) == 3


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_very_large_dataset(self):
        """Test with a very large dataset."""
        calc = PercentileCalculator()
        values = list(range(1, 100001))  # 100,000 values

        result = calc.calculate(values)

        assert result.sample_count == 100000
        assert result.min_value == 1.0
        assert result.max_value == 100000.0
        assert abs(result.mean - 50000.5) < 1.0

    def test_negative_values(self):
        """Test with negative values."""
        calc = PercentileCalculator()
        values = [-100, -50, 0, 50, 100]

        result = calc.calculate(values)

        assert result.min_value == -100.0
        assert result.max_value == 100.0
        assert result.mean == 0.0
        assert result.p50 == 0.0

    def test_floating_point_values(self):
        """Test with floating point values."""
        calc = PercentileCalculator()
        values = [1.5, 2.3, 3.7, 4.2, 5.9]

        result = calc.calculate(values)

        assert result.sample_count == 5
        assert abs(result.mean - 3.52) < 0.01

    def test_very_small_values(self):
        """Test with very small values."""
        calc = PercentileCalculator()
        values = [0.001, 0.002, 0.003, 0.004, 0.005]

        result = calc.calculate(values)

        assert result.min_value == 0.001
        assert result.max_value == 0.005
        assert abs(result.mean - 0.003) < 0.0001

    def test_outliers_effect_on_percentiles(self):
        """Test that outliers don't affect lower percentiles much."""
        calc = PercentileCalculator()
        # 99 values around 100, 1 extreme outlier
        values = [100] * 99 + [10000]

        result = calc.calculate(values)

        # P50, P75, P90 should be close to 100
        assert result.p50 == 100.0
        assert result.p75 == 100.0
        assert result.p90 == 100.0

        # But P99 and P99.9 should reflect the outlier
        assert result.p99 > 100.0

    def test_integer_and_float_mixed(self):
        """Test with mixed integer and float values."""
        calc = PercentileCalculator()
        values = [1, 2.5, 3, 4.7, 5]

        result = calc.calculate(values)

        assert result.sample_count == 5
        assert result.min_value == 1.0
        assert result.max_value == 5.0


class TestPerformance:
    """Tests for performance characteristics."""

    def test_sorted_vs_unsorted_presorted_flag(self):
        """Test that presorted flag improves performance (functional test)."""
        calc = PercentileCalculator()
        values = list(range(1, 10001))

        # Both should give same result
        p50_sorted = calc.calculate_percentile(values, 50, presorted=True)
        p50_unsorted = calc.calculate_percentile(values, 50, presorted=False)

        assert p50_sorted == p50_unsorted
