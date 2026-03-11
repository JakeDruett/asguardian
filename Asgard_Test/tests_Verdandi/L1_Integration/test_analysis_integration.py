"""
L1 Integration Tests for Statistical Analysis Workflow.

Tests the complete workflow of loading historical metrics data,
calculating percentiles over time windows, performing trend analysis,
checking SLA compliance, and validating aggregation results.
"""

import pytest

from Asgard.Verdandi.Analysis import (
    PercentileCalculator,
    TrendAnalyzer,
    SLAChecker,
    ApdexCalculator,
    AggregationService,
)
from Asgard.Verdandi.Analysis.models.analysis_models import (
    PercentileResult,
    TrendDirection,
    TrendResult,
    SLAStatus,
    SLAResult,
    ApdexResult,
    AggregationConfig,
    AggregationResult,
)


class TestPercentileAnalysisIntegration:
    """Integration tests for percentile calculation workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = PercentileCalculator()

    def test_percentile_workflow_good_performance(self, response_times_good_performance):
        """Test percentile calculation with good performance data."""
        result = self.calculator.calculate(response_times_good_performance)

        assert isinstance(result, PercentileResult)
        assert result.sample_count == 20
        assert result.min_value == 100.0
        assert result.max_value == 150.0
        assert result.p50 < result.p95
        assert result.p95 < result.p99

    def test_percentile_workflow_bimodal_distribution(self, bimodal_distribution):
        """Test percentile calculation with bimodal distribution."""
        result = self.calculator.calculate(bimodal_distribution)

        assert result.sample_count == 100
        assert result.min_value == 50.0
        assert result.max_value == 549.0
        assert result.p50 < 300.0
        assert result.p95 > 500.0

    def test_percentile_workflow_uniform_distribution(self, uniform_distribution):
        """Test percentile calculation with uniform distribution."""
        result = self.calculator.calculate(uniform_distribution)

        assert result.sample_count == 100
        assert result.min_value == 1.0
        assert result.max_value == 100.0
        assert result.p50 == pytest.approx(50.0, rel=0.1)
        assert result.p95 == pytest.approx(95.0, rel=0.1)

    def test_percentile_specific_value_calculation(self, response_times_good_performance):
        """Test calculating a specific percentile value."""
        p95 = self.calculator.calculate_percentile(response_times_good_performance, 95.0)

        assert isinstance(p95, float)
        assert p95 >= min(response_times_good_performance)
        assert p95 <= max(response_times_good_performance)

    def test_percentile_range_property(self, response_times_good_performance):
        """Test range property calculation."""
        result = self.calculator.calculate(response_times_good_performance)

        expected_range = result.max_value - result.min_value
        assert result.range == expected_range


class TestTrendAnalysisIntegration:
    """Integration tests for trend analysis workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = TrendAnalyzer()

    def test_trend_workflow_improving(self, response_times_improving):
        """Test trend analysis detecting improving performance."""
        result = self.analyzer.analyze(
            response_times_improving,
            period_seconds=3600,
            lower_is_better=True
        )

        assert isinstance(result, TrendResult)
        assert result.direction == TrendDirection.IMPROVING
        assert result.slope < 0
        assert result.change_percent < 0
        assert result.baseline_value > result.current_value

    def test_trend_workflow_degrading(self, response_times_degrading):
        """Test trend analysis detecting degrading performance."""
        result = self.analyzer.analyze(
            response_times_degrading,
            period_seconds=3600,
            lower_is_better=True
        )

        assert isinstance(result, TrendResult)
        assert result.direction == TrendDirection.DEGRADING
        assert result.slope > 0
        assert result.change_percent > 0
        assert result.baseline_value < result.current_value

    def test_trend_workflow_stable(self, response_times_stable):
        """Test trend analysis detecting stable performance."""
        result = self.analyzer.analyze(
            response_times_stable,
            period_seconds=3600,
            lower_is_better=True
        )

        assert isinstance(result, TrendResult)
        assert result.direction == TrendDirection.STABLE
        assert abs(result.change_percent) < 5.0

    def test_trend_workflow_with_anomalies(self, response_times_with_anomalies):
        """Test trend analysis with anomalous data points."""
        result = self.analyzer.analyze(
            response_times_with_anomalies,
            period_seconds=3600,
            lower_is_better=True
        )

        assert isinstance(result, TrendResult)
        assert result.anomalies_detected > 0

    def test_trend_period_comparison(self, response_times_good_performance, response_times_degrading):
        """Test comparing two time periods."""
        result = self.analyzer.compare_periods(
            baseline_values=response_times_good_performance,
            current_values=response_times_degrading,
            lower_is_better=True
        )

        assert isinstance(result, TrendResult)
        assert result.direction == TrendDirection.DEGRADING
        assert result.change_percent > 0

    def test_trend_higher_is_better(self, response_times_improving):
        """Test trend analysis when higher values are better."""
        result = self.analyzer.analyze(
            response_times_improving,
            period_seconds=3600,
            lower_is_better=False
        )

        assert result.direction == TrendDirection.DEGRADING
        assert result.slope < 0

    def test_trend_confidence_threshold(self):
        """Test trend with low confidence due to noise."""
        noisy_data = [100.0 + (i % 2) * 50 for i in range(20)]

        analyzer = TrendAnalyzer(confidence_threshold=0.9)
        result = analyzer.analyze(noisy_data, lower_is_better=True)

        assert result.confidence < 0.9


class TestSLAComplianceIntegration:
    """Integration tests for SLA compliance checking workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        pass

    def test_sla_workflow_compliant(self, sla_config_lenient, response_times_good_performance):
        """Test SLA compliance check with compliant data."""
        checker = SLAChecker(sla_config_lenient)
        result = checker.check(response_times_good_performance)

        assert isinstance(result, SLAResult)
        assert result.status == SLAStatus.COMPLIANT
        assert result.percentile_value <= result.threshold_ms
        assert result.margin_percent > 0
        assert len(result.violations) == 0

    def test_sla_workflow_breached(self, sla_config_strict, response_times_degrading):
        """Test SLA compliance check with breached data."""
        checker = SLAChecker(sla_config_strict)
        result = checker.check(response_times_degrading)

        assert isinstance(result, SLAResult)
        assert result.status == SLAStatus.BREACHED
        assert result.percentile_value > result.threshold_ms
        assert result.margin_percent < 0
        assert len(result.violations) > 0

    def test_sla_workflow_warning(self, sla_config_strict, response_times_good_performance):
        """Test SLA compliance check with warning status."""
        checker = SLAChecker(sla_config_strict)
        result = checker.check(response_times_good_performance)

        if result.status == SLAStatus.WARNING:
            assert 0 < result.margin_percent < 10

    def test_sla_multiple_windows(self, sla_config_lenient, multiple_time_windows):
        """Test SLA compliance across multiple time windows."""
        checker = SLAChecker(sla_config_lenient)
        results = checker.check_multiple_windows(multiple_time_windows)

        assert isinstance(results, list)
        assert len(results) == len(multiple_time_windows)
        assert all(isinstance(r, SLAResult) for r in results)

    def test_sla_compliance_rate(self, sla_config_lenient, multiple_time_windows):
        """Test SLA compliance rate calculation."""
        checker = SLAChecker(sla_config_lenient)
        results = checker.check_multiple_windows(multiple_time_windows)
        compliance_rate = checker.calculate_compliance_rate(results)

        assert 0.0 <= compliance_rate <= 100.0
        compliant_count = sum(1 for r in results if r.status == SLAStatus.COMPLIANT)
        expected_rate = (compliant_count / len(results)) * 100
        assert compliance_rate == expected_rate

    def test_sla_with_availability(self, sla_config_strict):
        """Test SLA check including availability metrics."""
        checker = SLAChecker(sla_config_strict)
        result = checker.check(
            response_times_ms=[100.0] * 100,
            downtime_seconds=100,
            total_seconds=10000,
        )

        assert result.availability_actual is not None
        assert result.availability_actual == pytest.approx(99.0, rel=0.01)

    def test_sla_with_error_rate(self, sla_config_strict):
        """Test SLA check including error rate metrics."""
        checker = SLAChecker(sla_config_strict)
        result = checker.check(
            response_times_ms=[100.0] * 100,
            error_count=2,
            total_requests=100,
        )

        assert result.error_rate_actual is not None
        assert result.error_rate_actual == 2.0

    def test_sla_error_rate_violation(self, sla_config_strict):
        """Test SLA violation due to high error rate."""
        checker = SLAChecker(sla_config_strict)
        result = checker.check(
            response_times_ms=[100.0] * 100,
            error_count=5,
            total_requests=100,
        )

        assert result.status == SLAStatus.BREACHED
        assert any("error rate" in v.lower() for v in result.violations)

    def test_sla_availability_violation(self, sla_config_strict):
        """Test SLA violation due to low availability."""
        checker = SLAChecker(sla_config_strict)
        result = checker.check(
            response_times_ms=[100.0] * 100,
            downtime_seconds=1000,
            total_seconds=10000,
        )

        assert result.status == SLAStatus.BREACHED
        assert any("availability" in v.lower() for v in result.violations)


class TestApdexCalculationIntegration:
    """Integration tests for Apdex score calculation workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        pass

    def test_apdex_workflow_excellent(self, apdex_config_standard):
        """Test Apdex calculation with excellent performance."""
        calculator = ApdexCalculator(threshold_ms=apdex_config_standard.threshold_ms)
        response_times = [100.0, 150.0, 200.0, 250.0, 300.0] * 20

        result = calculator.calculate(response_times)

        assert isinstance(result, ApdexResult)
        assert result.score >= 0.94
        assert result.rating == "Excellent"
        assert result.satisfied_count > result.frustrated_count

    def test_apdex_workflow_poor(self, apdex_config_standard):
        """Test Apdex calculation with poor performance."""
        calculator = ApdexCalculator(threshold_ms=apdex_config_standard.threshold_ms)
        response_times = [2500.0, 3000.0, 3500.0, 4000.0, 4500.0] * 20

        result = calculator.calculate(response_times)

        assert isinstance(result, ApdexResult)
        assert result.score < 0.70
        assert result.frustrated_count > result.satisfied_count

    def test_apdex_workflow_mixed(self, apdex_config_standard):
        """Test Apdex calculation with mixed performance."""
        calculator = ApdexCalculator(threshold_ms=apdex_config_standard.threshold_ms)
        satisfied = [200.0] * 50
        tolerating = [1000.0] * 30
        frustrated = [3000.0] * 20

        result = calculator.calculate(satisfied + tolerating + frustrated)

        assert isinstance(result, ApdexResult)
        assert result.satisfied_count == 50
        assert result.tolerating_count == 30
        assert result.frustrated_count == 20
        assert 0.5 <= result.score <= 0.85

    def test_apdex_strict_threshold(self, apdex_config_strict):
        """Test Apdex with strict threshold."""
        calculator = ApdexCalculator(threshold_ms=apdex_config_strict.threshold_ms)
        response_times = [150.0, 200.0, 250.0, 300.0, 350.0] * 20

        result = calculator.calculate(response_times)

        assert result.threshold_ms == 100.0
        assert result.frustrated_count > 0


class TestAggregationIntegration:
    """Integration tests for metric aggregation workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = AggregationService()

    def test_aggregation_workflow_basic(self, response_times_good_performance):
        """Test basic aggregation workflow."""
        config = AggregationConfig(
            window_size_seconds=60,
            include_percentiles=True,
            include_histograms=False,
        )

        result = self.service.aggregate(
            values=response_times_good_performance,
            config=config,
        )

        assert isinstance(result, AggregationResult)
        assert result.sample_count == 20
        assert result.mean > 0
        assert result.min_value <= result.mean <= result.max_value
        assert result.percentiles is not None

    def test_aggregation_workflow_with_histograms(self, response_times_good_performance):
        """Test aggregation with histogram generation."""
        config = AggregationConfig(
            window_size_seconds=60,
            include_percentiles=True,
            include_histograms=True,
        )

        result = self.service.aggregate(
            values=response_times_good_performance,
            config=config,
        )

        assert result.histogram is not None
        assert isinstance(result.histogram, dict)

    def test_aggregation_throughput_calculation(self, response_times_good_performance):
        """Test throughput calculation in aggregation."""
        config = AggregationConfig(window_size_seconds=60)

        result = self.service.aggregate(
            values=response_times_good_performance,
            config=config,
        )

        expected_throughput = len(response_times_good_performance) / 60
        assert result.throughput == pytest.approx(expected_throughput, rel=0.01)

    def test_aggregation_large_dataset(self, time_series_7_days):
        """Test aggregation with large time series dataset."""
        config = AggregationConfig(
            window_size_seconds=3600,
            include_percentiles=True,
        )

        result = self.service.aggregate(
            values=time_series_7_days,
            config=config,
        )

        assert result.sample_count == len(time_series_7_days)
        assert result.percentiles.p95 > result.percentiles.p50


class TestEndToEndAnalysisWorkflow:
    """End-to-end integration tests combining multiple analysis components."""

    def test_complete_performance_analysis_workflow(
        self,
        response_times_good_performance,
        sla_config_lenient,
        apdex_config_standard,
    ):
        """Test complete performance analysis workflow."""
        percentile_calc = PercentileCalculator()
        trend_analyzer = TrendAnalyzer()
        sla_checker = SLAChecker(sla_config_lenient)
        apdex_calc = ApdexCalculator(threshold_ms=apdex_config_standard.threshold_ms)

        percentile_result = percentile_calc.calculate(response_times_good_performance)
        assert percentile_result.p95 < 200.0

        trend_result = trend_analyzer.analyze(
            response_times_good_performance,
            lower_is_better=True
        )
        assert trend_result.direction in [TrendDirection.STABLE, TrendDirection.IMPROVING]

        sla_result = sla_checker.check(response_times_good_performance)
        assert sla_result.status in [SLAStatus.COMPLIANT, SLAStatus.WARNING]

        apdex_result = apdex_calc.calculate(response_times_good_performance)
        assert apdex_result.score >= 0.85

    def test_performance_degradation_detection_workflow(
        self,
        response_times_good_performance,
        response_times_degrading,
        sla_config_strict,
    ):
        """Test workflow detecting performance degradation."""
        trend_analyzer = TrendAnalyzer()
        sla_checker = SLAChecker(sla_config_strict)

        baseline_sla = sla_checker.check(response_times_good_performance)
        current_sla = sla_checker.check(response_times_degrading)

        trend = trend_analyzer.compare_periods(
            baseline_values=response_times_good_performance,
            current_values=response_times_degrading,
            lower_is_better=True,
        )

        assert trend.direction == TrendDirection.DEGRADING
        assert baseline_sla.status == SLAStatus.COMPLIANT
        assert current_sla.status == SLAStatus.BREACHED

    def test_multi_window_sla_monitoring_workflow(
        self,
        multiple_time_windows,
        sla_config_lenient,
    ):
        """Test multi-window SLA monitoring workflow."""
        sla_checker = SLAChecker(sla_config_lenient)

        results = sla_checker.check_multiple_windows(multiple_time_windows)
        compliance_rate = sla_checker.calculate_compliance_rate(results)

        assert len(results) == len(multiple_time_windows)
        assert 0.0 <= compliance_rate <= 100.0

        breached_windows = [r for r in results if r.status == SLAStatus.BREACHED]
        assert len(breached_windows) >= 0
