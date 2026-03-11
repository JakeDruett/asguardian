"""
Statistical Validation Tests for Verdandi Calculators.

Validates Verdandi statistical calculations against numpy/scipy implementations
to ensure accuracy and correctness of custom algorithms.
"""

import math
import random

import numpy as np
import pytest

from Asgard.Verdandi.Analysis.services.apdex_calculator import ApdexCalculator
from Asgard.Verdandi.Analysis.services.percentile_calculator import PercentileCalculator
from Asgard.Verdandi.Analysis.services.trend_analyzer import TrendAnalyzer
from Asgard.Verdandi.Analysis.models.analysis_models import ApdexConfig


class TestPercentileValidation:
    """Validate percentile calculations against numpy.percentile."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = PercentileCalculator()
        self.tolerance = 0.001

    @pytest.mark.parametrize("percentile", [50, 75, 90, 95, 99])
    def test_percentile_small_dataset(self, percentile):
        """Test percentile accuracy with small datasets (5-10 items)."""
        random.seed(42)
        data = [random.uniform(1, 1000) for _ in range(8)]

        verdandi_result = self.calculator.calculate_percentile(data, percentile)
        numpy_result = np.percentile(data, percentile)

        assert abs(verdandi_result - numpy_result) < self.tolerance, (
            f"P{percentile} mismatch: Verdandi={verdandi_result}, NumPy={numpy_result}"
        )

    @pytest.mark.parametrize("percentile", [50, 75, 90, 95, 99])
    def test_percentile_large_dataset(self, percentile):
        """Test percentile accuracy with large datasets (10000+ items)."""
        random.seed(123)
        data = [random.uniform(1, 10000) for _ in range(15000)]

        verdandi_result = self.calculator.calculate_percentile(data, percentile)
        numpy_result = np.percentile(data, percentile)

        relative_error = abs(verdandi_result - numpy_result) / numpy_result
        assert relative_error < 0.001, (
            f"P{percentile} relative error too large: {relative_error:.6f}"
        )

    @pytest.mark.parametrize("percentile", [25, 50, 75, 90, 95, 99, 99.9])
    def test_percentile_uniform_distribution(self, percentile):
        """Test percentiles with uniformly distributed data."""
        random.seed(456)
        data = [random.uniform(0, 100) for _ in range(1000)]

        verdandi_result = self.calculator.calculate_percentile(data, percentile)
        numpy_result = np.percentile(data, percentile)

        assert abs(verdandi_result - numpy_result) < self.tolerance

    @pytest.mark.parametrize("percentile", [50, 75, 90, 95, 99])
    def test_percentile_normal_distribution(self, percentile):
        """Test percentiles with normally distributed data."""
        random.seed(789)
        np.random.seed(789)
        data = np.random.normal(100, 20, 5000).tolist()

        verdandi_result = self.calculator.calculate_percentile(data, percentile)
        numpy_result = np.percentile(data, percentile)

        relative_error = abs(verdandi_result - numpy_result) / abs(numpy_result)
        assert relative_error < 0.001

    def test_percentile_result_all_percentiles(self):
        """Test all standard percentiles in PercentileResult against numpy."""
        random.seed(999)
        data = [random.uniform(10, 1000) for _ in range(5000)]

        result = self.calculator.calculate(data)

        assert abs(result.p50 - np.percentile(data, 50)) < self.tolerance
        assert abs(result.p75 - np.percentile(data, 75)) < self.tolerance
        assert abs(result.p90 - np.percentile(data, 90)) < self.tolerance
        assert abs(result.p95 - np.percentile(data, 95)) < self.tolerance
        assert abs(result.p99 - np.percentile(data, 99)) < self.tolerance
        assert abs(result.p999 - np.percentile(data, 99.9)) < self.tolerance

    @pytest.mark.parametrize("size", [5, 10, 50, 100, 1000, 10000])
    def test_percentile_various_sizes(self, size):
        """Test percentile calculation with various dataset sizes."""
        random.seed(111)
        data = [random.uniform(1, 100) for _ in range(size)]

        for percentile in [50, 90, 95, 99]:
            verdandi_result = self.calculator.calculate_percentile(data, percentile)
            numpy_result = np.percentile(data, percentile)

            assert abs(verdandi_result - numpy_result) < self.tolerance

    def test_percentile_edge_values(self):
        """Test percentile calculation at extreme values."""
        data = list(range(1, 101))

        verdandi_p0 = self.calculator.calculate_percentile(data, 0)
        verdandi_p100 = self.calculator.calculate_percentile(data, 100)

        assert verdandi_p0 == min(data)
        assert verdandi_p100 == max(data)

    def test_percentile_duplicates(self):
        """Test percentile calculation with duplicate values."""
        data = [10, 10, 10, 20, 20, 20, 30, 30, 30, 40, 40, 40]

        for percentile in [25, 50, 75, 90]:
            verdandi_result = self.calculator.calculate_percentile(data, percentile)
            numpy_result = np.percentile(data, percentile)

            assert abs(verdandi_result - numpy_result) < self.tolerance

    def test_custom_percentiles_against_numpy(self):
        """Test custom percentile calculations against numpy."""
        random.seed(222)
        data = [random.uniform(1, 1000) for _ in range(2000)]
        percentiles = [10, 20, 30, 40, 50, 60, 70, 80, 90]

        verdandi_results = self.calculator.calculate_custom_percentiles(data, percentiles)

        for p in percentiles:
            numpy_result = np.percentile(data, p)
            assert abs(verdandi_results[p] - numpy_result) < self.tolerance


class TestStandardDeviationValidation:
    """Validate standard deviation calculations against numpy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = PercentileCalculator()
        self.tolerance = 0.001

    @pytest.mark.parametrize("seed", [42, 123, 456, 789, 999])
    def test_std_dev_uniform_distribution(self, seed):
        """Test standard deviation with uniform distribution."""
        random.seed(seed)
        data = [random.uniform(0, 100) for _ in range(1000)]

        result = self.calculator.calculate(data)
        numpy_std = np.std(data, ddof=0)

        relative_error = abs(result.std_dev - numpy_std) / numpy_std
        assert relative_error < 0.001

    @pytest.mark.parametrize("mean,std", [(100, 15), (500, 50), (1000, 200)])
    def test_std_dev_normal_distribution(self, mean, std):
        """Test standard deviation with normal distribution."""
        np.random.seed(42)
        data = np.random.normal(mean, std, 5000).tolist()

        result = self.calculator.calculate(data)
        numpy_std = np.std(data, ddof=0)

        relative_error = abs(result.std_dev - numpy_std) / numpy_std
        assert relative_error < 0.001

    def test_std_dev_identical_values(self):
        """Test standard deviation with identical values."""
        data = [50.0] * 100

        result = self.calculator.calculate(data)
        numpy_std = np.std(data, ddof=0)

        assert result.std_dev == pytest.approx(numpy_std, abs=self.tolerance)
        assert result.std_dev == 0.0

    def test_std_dev_small_variance(self):
        """Test standard deviation with small variance."""
        data = [100.0 + i * 0.1 for i in range(100)]

        result = self.calculator.calculate(data)
        numpy_std = np.std(data, ddof=0)

        assert result.std_dev == pytest.approx(numpy_std, abs=self.tolerance)

    @pytest.mark.parametrize("size", [10, 100, 1000, 10000])
    def test_std_dev_various_sizes(self, size):
        """Test standard deviation with various dataset sizes."""
        random.seed(333)
        data = [random.uniform(1, 1000) for _ in range(size)]

        result = self.calculator.calculate(data)
        numpy_std = np.std(data, ddof=0)

        relative_error = abs(result.std_dev - numpy_std) / numpy_std
        assert relative_error < 0.001


class TestMeanValidation:
    """Validate mean calculations against numpy."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = PercentileCalculator()
        self.tolerance = 0.000001

    @pytest.mark.parametrize("seed", [42, 123, 456])
    def test_mean_accuracy(self, seed):
        """Test mean calculation accuracy."""
        random.seed(seed)
        data = [random.uniform(1, 10000) for _ in range(5000)]

        result = self.calculator.calculate(data)
        numpy_mean = np.mean(data)

        assert abs(result.mean - numpy_mean) < self.tolerance

    def test_mean_with_negative_values(self):
        """Test mean calculation with negative values."""
        data = [-100, -50, 0, 50, 100, 150, 200]

        result = self.calculator.calculate(data)
        numpy_mean = np.mean(data)

        assert result.mean == pytest.approx(numpy_mean, abs=self.tolerance)

    def test_mean_large_values(self):
        """Test mean calculation with large values."""
        data = [1e6, 2e6, 3e6, 4e6, 5e6]

        result = self.calculator.calculate(data)
        numpy_mean = np.mean(data)

        relative_error = abs(result.mean - numpy_mean) / numpy_mean
        assert relative_error < 1e-10


class TestApdexFormulaValidation:
    """Validate Apdex formula against manual calculations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = ApdexCalculator(threshold_ms=500)

    def test_apdex_formula_all_satisfied(self):
        """Verify Apdex formula with all satisfied responses."""
        data = [100, 200, 300, 400, 450]

        result = self.calculator.calculate(data)

        satisfied = 5
        tolerating = 0
        frustrated = 0
        total = 5
        expected_score = (satisfied + tolerating * 0.5) / total

        assert result.score == expected_score
        assert result.score == 1.0

    def test_apdex_formula_all_tolerating(self):
        """Verify Apdex formula with all tolerating responses."""
        data = [600, 800, 1000, 1200, 1500]

        result = self.calculator.calculate(data)

        satisfied = 0
        tolerating = 5
        frustrated = 0
        total = 5
        expected_score = (satisfied + tolerating * 0.5) / total

        assert result.score == expected_score
        assert result.score == 0.5

    def test_apdex_formula_all_frustrated(self):
        """Verify Apdex formula with all frustrated responses."""
        data = [2100, 2500, 3000, 3500, 4000]

        result = self.calculator.calculate(data)

        satisfied = 0
        tolerating = 0
        frustrated = 5
        total = 5
        expected_score = (satisfied + tolerating * 0.5) / total

        assert result.score == expected_score
        assert result.score == 0.0

    def test_apdex_formula_mixed_responses(self):
        """Verify Apdex formula with mixed response types."""
        data = [100, 200, 600, 800, 2500, 3000]

        result = self.calculator.calculate(data)

        satisfied = 2
        tolerating = 2
        frustrated = 2
        total = 6
        expected_score = (satisfied + tolerating * 0.5) / total

        assert result.satisfied_count == satisfied
        assert result.tolerating_count == tolerating
        assert result.frustrated_count == frustrated
        assert result.score == pytest.approx(expected_score, abs=0.0001)
        assert result.score == pytest.approx(0.5, abs=0.0001)

    @pytest.mark.parametrize(
        "satisfied,tolerating,frustrated",
        [
            (10, 0, 0),
            (0, 10, 0),
            (0, 0, 10),
            (5, 5, 0),
            (5, 0, 5),
            (0, 5, 5),
            (3, 4, 3),
            (8, 1, 1),
            (1, 8, 1),
            (1, 1, 8),
        ],
    )
    def test_apdex_formula_various_distributions(self, satisfied, tolerating, frustrated):
        """Test Apdex formula with various response distributions."""
        data = (
            [100] * satisfied
            + [600] * tolerating
            + [2500] * frustrated
        )

        result = self.calculator.calculate(data)

        total = satisfied + tolerating + frustrated
        expected_score = (satisfied + tolerating * 0.5) / total

        assert result.satisfied_count == satisfied
        assert result.tolerating_count == tolerating
        assert result.frustrated_count == frustrated
        assert result.total_count == total
        assert result.score == pytest.approx(expected_score, abs=0.0001)

    def test_apdex_custom_threshold(self):
        """Verify Apdex formula with custom threshold."""
        config = ApdexConfig(threshold_ms=200, frustration_multiplier=4.0)
        data = [100, 300, 500, 900]

        result = self.calculator.calculate(data, config=config)

        satisfied = 1
        tolerating = 2
        frustrated = 1
        total = 4
        expected_score = (satisfied + tolerating * 0.5) / total

        assert result.satisfied_count == satisfied
        assert result.tolerating_count == tolerating
        assert result.frustrated_count == frustrated
        assert result.score == pytest.approx(expected_score, abs=0.0001)
        assert result.score == pytest.approx(0.5, abs=0.0001)

    def test_apdex_weighted_formula(self):
        """Verify weighted Apdex formula."""
        data = [100, 600, 2500]
        weights = [10, 5, 2]

        result = self.calculator.calculate_with_weights(data, weights)

        satisfied_weight = 10
        tolerating_weight = 5
        frustrated_weight = 2
        total_weight = 17
        expected_score = (satisfied_weight + tolerating_weight * 0.5) / total_weight

        assert result.score == pytest.approx(expected_score, abs=0.0001)

    def test_apdex_threshold_boundaries(self):
        """Test Apdex classification at threshold boundaries."""
        data = [500, 501, 2000, 2001]

        result = self.calculator.calculate(data)

        assert result.satisfied_count == 1
        assert result.tolerating_count == 2
        assert result.frustrated_count == 1

    @pytest.mark.parametrize("threshold", [100, 500, 1000, 2000])
    def test_apdex_various_thresholds(self, threshold):
        """Test Apdex formula with various thresholds."""
        calculator = ApdexCalculator(threshold_ms=threshold)
        frustration_threshold = threshold * 4

        data = [
            threshold - 10,
            threshold + 10,
            frustration_threshold - 10,
            frustration_threshold + 10,
        ]

        result = calculator.calculate(data)

        assert result.satisfied_count == 1
        assert result.tolerating_count == 2
        assert result.frustrated_count == 1

        expected_score = (1 + 2 * 0.5) / 4
        assert result.score == pytest.approx(expected_score, abs=0.0001)


class TestTrendAnalysisValidation:
    """Validate trend analysis against numpy linear regression."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = TrendAnalyzer()
        self.tolerance = 0.000001

    def test_linear_regression_slope(self):
        """Test linear regression slope against numpy.polyfit."""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        result = self.analyzer.analyze(values)

        x = np.arange(len(values))
        y = np.array(values)
        numpy_slope, numpy_intercept = np.polyfit(x, y, 1)

        assert abs(result.slope - numpy_slope) < self.tolerance

    def test_linear_regression_negative_slope(self):
        """Test linear regression with negative slope."""
        values = [100, 90, 80, 70, 60, 50, 40, 30, 20, 10]

        result = self.analyzer.analyze(values)

        x = np.arange(len(values))
        y = np.array(values)
        numpy_slope, numpy_intercept = np.polyfit(x, y, 1)

        assert abs(result.slope - numpy_slope) < self.tolerance

    @pytest.mark.parametrize("seed", [42, 123, 456, 789])
    def test_linear_regression_noisy_data(self, seed):
        """Test linear regression with noisy data."""
        random.seed(seed)
        np.random.seed(seed)

        base_values = [i * 10 for i in range(50)]
        noise = [random.uniform(-5, 5) for _ in range(50)]
        values = [base + n for base, n in zip(base_values, noise)]

        result = self.analyzer.analyze(values)

        x = np.arange(len(values))
        y = np.array(values)
        numpy_slope, numpy_intercept = np.polyfit(x, y, 1)

        relative_error = abs(result.slope - numpy_slope) / abs(numpy_slope)
        assert relative_error < 0.001

    def test_r_squared_perfect_fit(self):
        """Test R-squared with perfect linear fit."""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

        result = self.analyzer.analyze(values)

        x = np.arange(len(values))
        y = np.array(values)
        numpy_slope, numpy_intercept = np.polyfit(x, y, 1)

        y_pred = numpy_slope * x + numpy_intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        numpy_r_squared = 1 - (ss_res / ss_tot)

        assert abs(result.confidence - numpy_r_squared) < self.tolerance
        assert result.confidence > 0.999

    def test_r_squared_noisy_data(self):
        """Test R-squared with noisy data."""
        random.seed(42)
        np.random.seed(42)

        base_values = [i * 5 for i in range(100)]
        noise = [random.uniform(-20, 20) for _ in range(100)]
        values = [base + n for base, n in zip(base_values, noise)]

        result = self.analyzer.analyze(values)

        x = np.arange(len(values))
        y = np.array(values)
        numpy_slope, numpy_intercept = np.polyfit(x, y, 1)

        y_pred = numpy_slope * x + numpy_intercept
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        numpy_r_squared = 1 - (ss_res / ss_tot)

        assert abs(result.confidence - numpy_r_squared) < 0.001

    def test_linear_regression_horizontal_line(self):
        """Test linear regression with horizontal line (slope = 0)."""
        values = [50.0] * 20

        result = self.analyzer.analyze(values)

        assert result.slope == 0.0
        assert result.change_percent == 0.0

    def test_linear_regression_intercept_calculation(self):
        """Test that intercept is calculated correctly."""
        values = [15, 25, 35, 45, 55]

        result = self.analyzer.analyze(values)

        x = np.arange(len(values))
        y = np.array(values)
        numpy_slope, numpy_intercept = np.polyfit(x, y, 1)

        x_mean = np.mean(x)
        y_mean = np.mean(y)
        verdandi_intercept = y_mean - result.slope * x_mean

        assert abs(verdandi_intercept - numpy_intercept) < self.tolerance

    @pytest.mark.parametrize("size", [10, 50, 100, 500, 1000])
    def test_linear_regression_various_sizes(self, size):
        """Test linear regression with various dataset sizes."""
        random.seed(111)
        np.random.seed(111)

        values = [i * 2 + random.uniform(-1, 1) for i in range(size)]

        result = self.analyzer.analyze(values)

        x = np.arange(len(values))
        y = np.array(values)
        numpy_slope, numpy_intercept = np.polyfit(x, y, 1)

        relative_error = abs(result.slope - numpy_slope) / abs(numpy_slope)
        assert relative_error < 0.001

    def test_trend_direction_accuracy(self):
        """Test trend direction detection accuracy."""
        improving_values = [100, 95, 90, 85, 80, 75, 70]
        degrading_values = [70, 75, 80, 85, 90, 95, 100]
        stable_values = [100, 101, 99, 100, 101, 100, 99]

        improving_result = self.analyzer.analyze(improving_values, lower_is_better=True)
        degrading_result = self.analyzer.analyze(degrading_values, lower_is_better=True)
        stable_result = self.analyzer.analyze(stable_values, lower_is_better=True)

        assert improving_result.slope < 0
        assert degrading_result.slope > 0
        assert abs(stable_result.change_percent) < 5

    def test_anomaly_detection_z_score(self):
        """Test anomaly detection using z-score method."""
        values = [50, 52, 51, 53, 200, 52, 51, 53, 52, 51]

        result = self.analyzer.analyze(values)

        mean = np.mean(values)
        std = np.std(values, ddof=0)

        anomaly_indices = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std)
            if z_score > 2.0:
                anomaly_indices.append(i)

        assert result.anomalies_detected == len(anomaly_indices)
        assert result.anomalies_detected > 0


class TestEdgeCasesValidation:
    """Test edge cases and boundary conditions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.percentile_calc = PercentileCalculator()
        self.apdex_calc = ApdexCalculator(threshold_ms=500)
        self.trend_analyzer = TrendAnalyzer()

    def test_single_value_percentiles(self):
        """Test percentile calculations with single value."""
        data = [42.0]

        result = self.percentile_calc.calculate(data)

        assert result.p50 == 42.0
        assert result.p95 == 42.0
        assert result.p99 == 42.0
        assert result.std_dev == 0.0

    def test_two_values_percentiles(self):
        """Test percentile calculations with two values."""
        data = [10.0, 20.0]

        result = self.percentile_calc.calculate(data)

        assert result.p50 == 15.0
        assert result.min_value == 10.0
        assert result.max_value == 20.0

    def test_large_number_precision(self):
        """Test calculations with very large numbers."""
        data = [1e9, 2e9, 3e9, 4e9, 5e9]

        result = self.percentile_calc.calculate(data)
        numpy_mean = np.mean(data)

        relative_error = abs(result.mean - numpy_mean) / numpy_mean
        assert relative_error < 1e-10

    def test_small_number_precision(self):
        """Test calculations with very small numbers."""
        data = [1e-6, 2e-6, 3e-6, 4e-6, 5e-6]

        result = self.percentile_calc.calculate(data)
        numpy_mean = np.mean(data)

        relative_error = abs(result.mean - numpy_mean) / numpy_mean
        assert relative_error < 1e-10

    def test_mixed_magnitude_values(self):
        """Test calculations with mixed magnitude values."""
        data = [0.001, 1, 1000, 1000000]

        result = self.percentile_calc.calculate(data)

        for percentile in [25, 50, 75, 95]:
            verdandi_result = self.percentile_calc.calculate_percentile(data, percentile)
            numpy_result = np.percentile(data, percentile)
            assert abs(verdandi_result - numpy_result) < 0.001


class TestPerformanceBenchmark:
    """Benchmark performance of Verdandi calculations."""

    def test_percentile_performance_large_dataset(self):
        """Test percentile calculation performance with large datasets."""
        import time

        random.seed(999)
        data = [random.uniform(1, 10000) for _ in range(100000)]

        calculator = PercentileCalculator()

        start_time = time.time()
        result = calculator.calculate(data)
        end_time = time.time()

        execution_time = end_time - start_time

        assert execution_time < 1.0

    def test_apdex_performance_large_dataset(self):
        """Test Apdex calculation performance with large datasets."""
        import time

        random.seed(888)
        data = [random.uniform(1, 5000) for _ in range(100000)]

        calculator = ApdexCalculator(threshold_ms=500)

        start_time = time.time()
        result = calculator.calculate(data)
        end_time = time.time()

        execution_time = end_time - start_time

        assert execution_time < 0.5

    def test_trend_analysis_performance(self):
        """Test trend analysis performance with large datasets."""
        import time

        random.seed(777)
        data = [i * 2 + random.uniform(-10, 10) for i in range(10000)]

        analyzer = TrendAnalyzer()

        start_time = time.time()
        result = analyzer.analyze(data)
        end_time = time.time()

        execution_time = end_time - start_time

        assert execution_time < 1.0
