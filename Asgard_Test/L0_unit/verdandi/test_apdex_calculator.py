"""
Comprehensive L0 Unit Tests for ApdexCalculator Service

Tests all functionality of the ApdexCalculator including:
- Basic Apdex score calculations
- Satisfied/Tolerating/Frustrated classifications
- Custom threshold configurations
- Weighted calculations
- Rating classifications
- Edge cases and boundary conditions
"""

import pytest

from Asgard.Verdandi.Analysis.services.apdex_calculator import ApdexCalculator
from Asgard.Verdandi.Analysis.models.analysis_models import ApdexConfig, ApdexResult


class TestApdexCalculatorInitialization:
    """Tests for ApdexCalculator initialization."""

    def test_calculator_default_initialization(self):
        """Test calculator with default threshold."""
        calc = ApdexCalculator()

        assert calc.config.threshold_ms == 500.0
        assert calc.config.frustration_multiplier == 4.0
        assert calc.config.frustration_threshold_ms == 2000.0

    def test_calculator_custom_threshold(self):
        """Test calculator with custom threshold."""
        calc = ApdexCalculator(threshold_ms=300.0)

        assert calc.config.threshold_ms == 300.0
        assert calc.config.frustration_threshold_ms == 1200.0

    def test_calculator_custom_multiplier(self):
        """Test calculator with custom frustration multiplier."""
        calc = ApdexCalculator(threshold_ms=500.0, frustration_multiplier=3.0)

        assert calc.config.frustration_multiplier == 3.0
        assert calc.config.frustration_threshold_ms == 1500.0


class TestApdexCalculationBasic:
    """Tests for basic Apdex calculations."""

    def test_calculate_all_satisfied(self):
        """Test Apdex when all requests are satisfied."""
        calc = ApdexCalculator(threshold_ms=500.0)
        response_times = [100, 200, 300, 400, 500]

        result = calc.calculate(response_times)

        assert result.score == 1.0
        assert result.satisfied_count == 5
        assert result.tolerating_count == 0
        assert result.frustrated_count == 0
        assert result.total_count == 5
        assert result.rating == "Excellent"

    def test_calculate_all_frustrated(self):
        """Test Apdex when all requests are frustrated."""
        calc = ApdexCalculator(threshold_ms=500.0)
        # All > 2000ms (4 * 500)
        response_times = [2100, 2500, 3000, 2200, 2300]

        result = calc.calculate(response_times)

        assert result.score == 0.0
        assert result.satisfied_count == 0
        assert result.tolerating_count == 0
        assert result.frustrated_count == 5
        assert result.rating == "Unacceptable"

    def test_calculate_all_tolerating(self):
        """Test Apdex when all requests are tolerating."""
        calc = ApdexCalculator(threshold_ms=500.0)
        # All between 500ms and 2000ms
        response_times = [600, 800, 1000, 1500, 1800]

        result = calc.calculate(response_times)

        assert result.score == 0.5  # (0 + 5 * 0.5) / 5
        assert result.satisfied_count == 0
        assert result.tolerating_count == 5
        assert result.frustrated_count == 0

    def test_calculate_mixed_distribution(self):
        """Test Apdex with mixed distribution."""
        calc = ApdexCalculator(threshold_ms=500.0)
        # 3 satisfied (<=500), 2 tolerating (501-2000), 1 frustrated (>2000)
        response_times = [100, 300, 500, 600, 1500, 2500]

        result = calc.calculate(response_times)

        # Apdex = (3 + 2 * 0.5) / 6 = 4 / 6 = 0.6667
        assert abs(result.score - 0.6667) < 0.01
        assert result.satisfied_count == 3
        assert result.tolerating_count == 2
        assert result.frustrated_count == 1
        assert result.total_count == 6

    def test_calculate_empty_dataset_raises_error(self):
        """Test that empty dataset raises ValueError."""
        calc = ApdexCalculator()

        with pytest.raises(ValueError, match="Cannot calculate Apdex for empty dataset"):
            calc.calculate([])

    def test_calculate_single_value(self):
        """Test Apdex calculation with single value."""
        calc = ApdexCalculator(threshold_ms=500.0)

        # Satisfied
        result = calc.calculate([300])
        assert result.score == 1.0
        assert result.satisfied_count == 1

        # Tolerating
        result = calc.calculate([1000])
        assert result.score == 0.5
        assert result.tolerating_count == 1

        # Frustrated
        result = calc.calculate([3000])
        assert result.score == 0.0
        assert result.frustrated_count == 1


class TestApdexBoundaries:
    """Tests for Apdex calculation at boundary values."""

    def test_calculate_at_threshold(self):
        """Test Apdex when value equals threshold."""
        calc = ApdexCalculator(threshold_ms=500.0)

        result = calc.calculate([500.0])

        # Exactly at threshold should be satisfied (<=)
        assert result.satisfied_count == 1
        assert result.score == 1.0

    def test_calculate_at_frustration_threshold(self):
        """Test Apdex when value equals frustration threshold."""
        calc = ApdexCalculator(threshold_ms=500.0)
        # Frustration threshold is 2000ms (4 * 500)

        result = calc.calculate([2000.0])

        # Exactly at frustration threshold should be tolerating (<=)
        assert result.tolerating_count == 1
        assert result.score == 0.5

    def test_calculate_just_above_threshold(self):
        """Test Apdex when value is just above threshold."""
        calc = ApdexCalculator(threshold_ms=500.0)

        result = calc.calculate([500.1])

        # Just above threshold should be tolerating
        assert result.tolerating_count == 1
        assert result.score == 0.5

    def test_calculate_just_above_frustration_threshold(self):
        """Test Apdex when value is just above frustration threshold."""
        calc = ApdexCalculator(threshold_ms=500.0)

        result = calc.calculate([2000.1])

        # Just above frustration threshold should be frustrated
        assert result.frustrated_count == 1
        assert result.score == 0.0


class TestApdexRatingClassification:
    """Tests for Apdex rating classification."""

    def test_rating_excellent(self):
        """Test Excellent rating (>= 0.94)."""
        calc = ApdexCalculator(threshold_ms=500.0)

        # 94 satisfied, 6 tolerating = (94 + 3) / 100 = 0.97
        response_times = [100] * 94 + [600] * 6

        result = calc.calculate(response_times)

        assert result.score >= 0.94
        assert result.rating == "Excellent"

    def test_rating_good(self):
        """Test Good rating (0.85 - 0.93)."""
        calc = ApdexCalculator(threshold_ms=500.0)

        # 85 satisfied, 10 tolerating, 5 frustrated = (85 + 5) / 100 = 0.90
        response_times = [100] * 85 + [600] * 10 + [2500] * 5

        result = calc.calculate(response_times)

        assert 0.85 <= result.score < 0.94
        assert result.rating == "Good"

    def test_rating_fair(self):
        """Test Fair rating (0.70 - 0.84)."""
        calc = ApdexCalculator(threshold_ms=500.0)

        # 70 satisfied, 10 tolerating, 20 frustrated = (70 + 5) / 100 = 0.75
        response_times = [100] * 70 + [600] * 10 + [2500] * 20

        result = calc.calculate(response_times)

        assert 0.70 <= result.score < 0.85
        assert result.rating == "Fair"

    def test_rating_poor(self):
        """Test Poor rating (0.50 - 0.69)."""
        calc = ApdexCalculator(threshold_ms=500.0)

        # 50 satisfied, 20 tolerating, 30 frustrated = (50 + 10) / 100 = 0.60
        response_times = [100] * 50 + [600] * 20 + [2500] * 30

        result = calc.calculate(response_times)

        assert 0.50 <= result.score < 0.70
        assert result.rating == "Poor"

    def test_rating_unacceptable(self):
        """Test Unacceptable rating (< 0.50)."""
        calc = ApdexCalculator(threshold_ms=500.0)

        # 30 satisfied, 10 tolerating, 60 frustrated = (30 + 5) / 100 = 0.35
        response_times = [100] * 30 + [600] * 10 + [2500] * 60

        result = calc.calculate(response_times)

        assert result.score < 0.50
        assert result.rating == "Unacceptable"


class TestApdexConfigOverride:
    """Tests for config override in calculate method."""

    def test_calculate_with_config_override(self):
        """Test calculation with config override."""
        calc = ApdexCalculator(threshold_ms=500.0)

        # Override with stricter threshold
        custom_config = ApdexConfig(threshold_ms=200.0)
        response_times = [150, 250, 350, 450, 550]

        result = calc.calculate(response_times, config=custom_config)

        # With 200ms threshold:
        # 150 = satisfied
        # 250, 350, 450, 550 = tolerating (200 < x <= 800)
        assert result.satisfied_count == 1
        assert result.tolerating_count == 4

    def test_calculate_uses_default_config_when_no_override(self):
        """Test that default config is used when no override."""
        calc = ApdexCalculator(threshold_ms=500.0)
        response_times = [400, 600, 800]

        result = calc.calculate(response_times)

        assert result.threshold_ms == 500.0


class TestApdexScoreRounding:
    """Tests for Apdex score rounding."""

    def test_score_rounded_to_four_decimals(self):
        """Test that score is rounded to 4 decimal places."""
        calc = ApdexCalculator(threshold_ms=500.0)

        # Create specific distribution to test rounding
        # 2 satisfied, 1 tolerating = (2 + 0.5) / 3 = 0.83333...
        response_times = [100, 200, 600]

        result = calc.calculate(response_times)

        # Should be rounded to 4 decimals
        assert result.score == 0.8333


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_calculate_with_zero_threshold(self):
        """Test Apdex with zero threshold."""
        calc = ApdexCalculator(threshold_ms=0.0)

        # Any non-zero response time should be tolerating or frustrated
        response_times = [1, 2, 3, 4, 5]

        result = calc.calculate(response_times)

        assert result.satisfied_count == 0
        assert result.total_count == 5

    def test_calculate_with_very_high_threshold(self):
        """Test Apdex with very high threshold."""
        calc = ApdexCalculator(threshold_ms=10000.0)

        response_times = [100, 500, 1000, 2000, 5000]

        result = calc.calculate(response_times)

        # All should be satisfied (< 10000ms)
        assert result.satisfied_count == 5
        assert result.score == 1.0

    def test_calculate_with_very_small_values(self):
        """Test Apdex with very small response times."""
        calc = ApdexCalculator(threshold_ms=100.0)

        response_times = [0.1, 0.5, 1.0, 5.0, 10.0]

        result = calc.calculate(response_times)

        # All should be satisfied (< 100ms)
        assert result.satisfied_count == 5

    def test_calculate_with_very_large_values(self):
        """Test Apdex with very large response times."""
        calc = ApdexCalculator(threshold_ms=1000.0)

        response_times = [100000, 200000, 300000, 400000, 500000]

        result = calc.calculate(response_times)

        # All should be frustrated (> 4000ms)
        assert result.frustrated_count == 5
        assert result.score == 0.0

    def test_calculate_with_negative_values(self):
        """Test Apdex behavior with negative values (invalid but handled)."""
        calc = ApdexCalculator(threshold_ms=500.0)

        # Negative values should be treated as satisfied
        response_times = [-10, 0, 100, 200]

        result = calc.calculate(response_times)

        assert result.satisfied_count == 4

    def test_calculate_large_dataset(self):
        """Test Apdex calculation with large dataset."""
        calc = ApdexCalculator(threshold_ms=500.0)

        # 10,000 requests with varying response times
        response_times = (
            [100] * 5000 +  # Satisfied
            [1000] * 3000 +  # Tolerating
            [3000] * 2000    # Frustrated
        )

        result = calc.calculate(response_times)

        assert result.total_count == 10000
        assert result.satisfied_count == 5000
        assert result.tolerating_count == 3000
        assert result.frustrated_count == 2000
        # Score = (5000 + 3000 * 0.5) / 10000 = 6500 / 10000 = 0.65
        assert abs(result.score - 0.65) < 0.01


class TestRealWorldScenarios:
    """Tests simulating real-world scenarios."""

    def test_typical_fast_api(self):
        """Test Apdex for a typical fast API."""
        calc = ApdexCalculator(threshold_ms=100.0)

        # Most requests fast, few slow ones
        response_times = (
            [50] * 85 +      # Fast
            [120] * 10 +     # Acceptable
            [500] * 5        # Slow
        )

        result = calc.calculate(response_times)

        # Should have good Apdex score
        assert result.score >= 0.85
        assert result.rating in ["Excellent", "Good"]

    def test_degraded_service(self):
        """Test Apdex for degraded service."""
        calc = ApdexCalculator(threshold_ms=500.0)

        # Many slow requests
        response_times = (
            [200] * 30 +     # Fast
            [1000] * 40 +    # Slow but tolerable
            [3000] * 30      # Very slow
        )

        result = calc.calculate(response_times)

        # Should have poor Apdex score
        assert result.score < 0.70
        assert result.rating in ["Fair", "Poor", "Unacceptable"]

    def test_bimodal_distribution(self):
        """Test Apdex with bimodal distribution (cache hits/misses)."""
        calc = ApdexCalculator(threshold_ms=50.0)

        # Cache hits (fast) and cache misses (slow)
        response_times = (
            [10] * 70 +      # Cache hits
            [200] * 30       # Cache misses
        )

        result = calc.calculate(response_times)

        # 70 satisfied + 30 tolerating (assuming 200 < 4*50)
        # Actually 200 > 200 so frustrated
        # Score should reflect this distribution


class TestCustomFrustrationMultiplier:
    """Tests for custom frustration multiplier."""

    def test_frustration_multiplier_3x(self):
        """Test with 3x frustration multiplier instead of 4x."""
        calc = ApdexCalculator(threshold_ms=500.0, frustration_multiplier=3.0)

        # 1500ms would be frustrated with 3x, tolerating with 4x
        result = calc.calculate([1500])

        assert calc.config.frustration_threshold_ms == 1500.0
        # Exactly at threshold - should be tolerating
        assert result.tolerating_count == 1

    def test_frustration_multiplier_5x(self):
        """Test with 5x frustration multiplier."""
        calc = ApdexCalculator(threshold_ms=500.0, frustration_multiplier=5.0)

        # 2000ms would be tolerating with 5x (< 2500), frustrated with 4x
        result = calc.calculate([2000])

        assert calc.config.frustration_threshold_ms == 2500.0
        assert result.tolerating_count == 1
