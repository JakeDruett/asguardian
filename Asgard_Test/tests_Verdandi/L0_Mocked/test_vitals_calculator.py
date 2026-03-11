"""
Unit tests for CoreWebVitalsCalculator.
"""

import pytest

from Asgard.Verdandi.Web import CoreWebVitalsCalculator, VitalsRating


class TestCoreWebVitalsCalculator:
    """Tests for CoreWebVitalsCalculator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = CoreWebVitalsCalculator()

    def test_calculate_all_good(self):
        """Test calculation with all good vitals."""
        result = self.calculator.calculate(
            lcp_ms=2000,
            fid_ms=50,
            cls=0.05,
        )

        assert result.lcp_rating == VitalsRating.GOOD
        assert result.fid_rating == VitalsRating.GOOD
        assert result.cls_rating == VitalsRating.GOOD
        assert result.overall_rating == VitalsRating.GOOD
        assert result.score == 100

    def test_calculate_all_poor(self):
        """Test calculation with all poor vitals."""
        result = self.calculator.calculate(
            lcp_ms=5000,
            fid_ms=500,
            cls=0.5,
        )

        assert result.lcp_rating == VitalsRating.POOR
        assert result.fid_rating == VitalsRating.POOR
        assert result.cls_rating == VitalsRating.POOR
        assert result.overall_rating == VitalsRating.POOR
        assert result.score == 20

    def test_calculate_needs_improvement(self):
        """Test calculation with needs improvement vitals."""
        result = self.calculator.calculate(
            lcp_ms=3000,
            fid_ms=200,
            cls=0.15,
        )

        assert result.lcp_rating == VitalsRating.NEEDS_IMPROVEMENT
        assert result.fid_rating == VitalsRating.NEEDS_IMPROVEMENT
        assert result.cls_rating == VitalsRating.NEEDS_IMPROVEMENT
        assert result.overall_rating == VitalsRating.NEEDS_IMPROVEMENT

    def test_calculate_mixed_ratings(self):
        """Test that overall rating is worst of individual ratings."""
        result = self.calculator.calculate(
            lcp_ms=2000,
            fid_ms=50,
            cls=0.5,
        )

        assert result.lcp_rating == VitalsRating.GOOD
        assert result.fid_rating == VitalsRating.GOOD
        assert result.cls_rating == VitalsRating.POOR
        assert result.overall_rating == VitalsRating.POOR

    def test_calculate_partial_metrics(self):
        """Test calculation with only some metrics provided."""
        result = self.calculator.calculate(lcp_ms=2000)

        assert result.lcp_rating == VitalsRating.GOOD
        assert result.fid_rating is None
        assert result.cls_rating is None
        assert result.overall_rating == VitalsRating.GOOD

    def test_calculate_inp(self):
        """Test INP calculation."""
        result = self.calculator.calculate(inp_ms=150)
        assert result.inp_rating == VitalsRating.GOOD

        result = self.calculator.calculate(inp_ms=350)
        assert result.inp_rating == VitalsRating.NEEDS_IMPROVEMENT

        result = self.calculator.calculate(inp_ms=600)
        assert result.inp_rating == VitalsRating.POOR

    def test_calculate_ttfb(self):
        """Test TTFB calculation."""
        result = self.calculator.calculate(ttfb_ms=500)
        assert result.ttfb_rating == VitalsRating.GOOD

        result = self.calculator.calculate(ttfb_ms=1200)
        assert result.ttfb_rating == VitalsRating.NEEDS_IMPROVEMENT

        result = self.calculator.calculate(ttfb_ms=2500)
        assert result.ttfb_rating == VitalsRating.POOR

    def test_recommendations_generated(self):
        """Test that recommendations are generated for poor metrics."""
        result = self.calculator.calculate(
            lcp_ms=5000,
            fid_ms=500,
            cls=0.5,
        )

        assert len(result.recommendations) > 0
        assert any("LCP" in rec or "contentful" in rec.lower() for rec in result.recommendations)

    def test_no_recommendations_for_good(self):
        """Test that no recommendations for good metrics."""
        result = self.calculator.calculate(
            lcp_ms=2000,
            fid_ms=50,
            cls=0.05,
        )

        assert len(result.recommendations) == 0

    def test_thresholds(self):
        """Test threshold constants are correct."""
        assert CoreWebVitalsCalculator.LCP_GOOD == 2500
        assert CoreWebVitalsCalculator.LCP_POOR == 4000
        assert CoreWebVitalsCalculator.FID_GOOD == 100
        assert CoreWebVitalsCalculator.FID_POOR == 300
        assert CoreWebVitalsCalculator.CLS_GOOD == 0.1
        assert CoreWebVitalsCalculator.CLS_POOR == 0.25
