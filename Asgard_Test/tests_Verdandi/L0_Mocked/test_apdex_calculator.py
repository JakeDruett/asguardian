"""
Unit tests for ApdexCalculator.
"""

import pytest

from Asgard.Verdandi.Analysis import ApdexCalculator, ApdexConfig


class TestApdexCalculator:
    """Tests for ApdexCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = ApdexCalculator(threshold_ms=500)

    def test_calculate_all_satisfied(self):
        """Test Apdex with all satisfied responses."""
        data = [100, 200, 300, 400, 450]
        result = self.calculator.calculate(data)

        assert result.score == 1.0
        assert result.satisfied_count == 5
        assert result.tolerating_count == 0
        assert result.frustrated_count == 0
        assert result.rating == "Excellent"

    def test_calculate_mixed_responses(self):
        """Test Apdex with mixed responses."""
        data = [100, 200, 600, 800, 2500]
        result = self.calculator.calculate(data)

        assert result.satisfied_count == 2
        assert result.tolerating_count == 2
        assert result.frustrated_count == 1
        assert result.score == pytest.approx(0.6, abs=0.01)

    def test_calculate_all_frustrated(self):
        """Test Apdex with all frustrated responses."""
        data = [2500, 3000, 4000, 5000]
        result = self.calculator.calculate(data)

        assert result.score == 0.0
        assert result.frustrated_count == 4
        assert result.rating == "Unacceptable"

    def test_calculate_empty_raises(self):
        """Test that empty dataset raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            self.calculator.calculate([])

    def test_calculate_with_custom_config(self):
        """Test Apdex with custom threshold config."""
        config = ApdexConfig(threshold_ms=100, frustration_multiplier=4.0)
        data = [50, 150, 450]
        result = self.calculator.calculate(data, config=config)

        assert result.threshold_ms == 100
        assert result.satisfied_count == 1
        assert result.tolerating_count == 1
        assert result.frustrated_count == 1

    def test_rating_thresholds(self):
        """Test Apdex rating thresholds."""
        assert ApdexCalculator._get_rating_for_score(0.95) == "Excellent"
        assert ApdexCalculator._get_rating_for_score(0.90) == "Good"
        assert ApdexCalculator._get_rating_for_score(0.75) == "Fair"
        assert ApdexCalculator._get_rating_for_score(0.55) == "Poor"
        assert ApdexCalculator._get_rating_for_score(0.40) == "Unacceptable"

    @staticmethod
    def _get_rating_for_score(score: float) -> str:
        """Helper to get rating for score."""
        from Asgard.Verdandi.Analysis.models.analysis_models import ApdexResult
        return ApdexResult.get_rating(score)

    def test_frustration_threshold(self):
        """Test frustration threshold calculation."""
        config = ApdexConfig(threshold_ms=500, frustration_multiplier=4.0)
        assert config.frustration_threshold_ms == 2000

    def test_weighted_apdex(self):
        """Test weighted Apdex calculation."""
        data = [100, 600, 2500]
        weights = [10, 5, 1]
        result = self.calculator.calculate_with_weights(data, weights)

        assert result.total_count == 3
        assert result.score > 0.5

    def test_recommended_threshold(self):
        """Test recommended threshold calculation."""
        data = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
        recommended = ApdexCalculator.get_recommended_threshold(data, target_score=0.85)

        assert recommended > 0
        assert recommended <= 1000
