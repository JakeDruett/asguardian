"""
L1 Integration Tests for Web Vitals Workflow.

Tests the complete workflow of loading performance timing data,
calculating Core Web Vitals, validating threshold classifications,
and generating performance reports.
"""

import pytest

from Asgard.Verdandi.Web import CoreWebVitalsCalculator
from Asgard.Verdandi.Web.models.web_models import (
    CoreWebVitalsInput,
    VitalsRating,
    WebVitalsResult,
)


class TestWebVitalsIntegration:
    """Integration tests for Core Web Vitals calculation workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = CoreWebVitalsCalculator()

    def test_vitals_workflow_all_good_performance(self, good_web_vitals_data):
        """Test complete workflow with all good performance metrics."""
        result = self.calculator.calculate_from_input(good_web_vitals_data)

        assert isinstance(result, WebVitalsResult)
        assert result.lcp_rating == VitalsRating.GOOD
        assert result.fid_rating == VitalsRating.GOOD
        assert result.cls_rating == VitalsRating.GOOD
        assert result.inp_rating == VitalsRating.GOOD
        assert result.ttfb_rating == VitalsRating.GOOD
        assert result.fcp_rating == VitalsRating.GOOD
        assert result.overall_rating == VitalsRating.GOOD
        assert result.score == 100.0
        assert len(result.recommendations) == 0

    def test_vitals_workflow_all_poor_performance(self, poor_web_vitals_data):
        """Test complete workflow with all poor performance metrics."""
        result = self.calculator.calculate_from_input(poor_web_vitals_data)

        assert isinstance(result, WebVitalsResult)
        assert result.lcp_rating == VitalsRating.POOR
        assert result.fid_rating == VitalsRating.POOR
        assert result.cls_rating == VitalsRating.POOR
        assert result.inp_rating == VitalsRating.POOR
        assert result.ttfb_rating == VitalsRating.POOR
        assert result.fcp_rating == VitalsRating.POOR
        assert result.overall_rating == VitalsRating.POOR
        assert result.score == 20.0
        assert len(result.recommendations) > 0

    def test_vitals_workflow_mixed_performance(self, mixed_web_vitals_data):
        """Test workflow with mixed good and poor metrics."""
        result = self.calculator.calculate_from_input(mixed_web_vitals_data)

        assert isinstance(result, WebVitalsResult)
        assert result.overall_rating == VitalsRating.POOR
        assert result.cls_rating == VitalsRating.POOR
        assert result.lcp_rating == VitalsRating.GOOD
        assert result.fid_rating == VitalsRating.GOOD
        assert len(result.recommendations) > 0

    def test_vitals_workflow_needs_improvement(self, needs_improvement_web_vitals_data):
        """Test workflow with metrics that need improvement."""
        result = self.calculator.calculate_from_input(needs_improvement_web_vitals_data)

        assert isinstance(result, WebVitalsResult)
        assert result.lcp_rating == VitalsRating.NEEDS_IMPROVEMENT
        assert result.fid_rating == VitalsRating.NEEDS_IMPROVEMENT
        assert result.cls_rating == VitalsRating.NEEDS_IMPROVEMENT
        assert result.inp_rating == VitalsRating.NEEDS_IMPROVEMENT
        assert result.ttfb_rating == VitalsRating.NEEDS_IMPROVEMENT
        assert result.fcp_rating == VitalsRating.NEEDS_IMPROVEMENT
        assert result.overall_rating == VitalsRating.NEEDS_IMPROVEMENT
        assert 20.0 < result.score < 100.0
        assert len(result.recommendations) > 0

    def test_vitals_workflow_partial_metrics(self, partial_web_vitals_data):
        """Test workflow with only some metrics available."""
        result = self.calculator.calculate_from_input(partial_web_vitals_data)

        assert isinstance(result, WebVitalsResult)
        assert result.lcp_rating == VitalsRating.GOOD
        assert result.cls_rating == VitalsRating.GOOD
        assert result.ttfb_rating == VitalsRating.GOOD
        assert result.fid_rating is None
        assert result.inp_rating is None
        assert result.fcp_rating is None
        assert result.overall_rating == VitalsRating.GOOD

    def test_vitals_threshold_boundaries_lcp(self):
        """Test LCP threshold boundary conditions."""
        just_good = CoreWebVitalsInput(lcp_ms=2500.0)
        result = self.calculator.calculate_from_input(just_good)
        assert result.lcp_rating == VitalsRating.GOOD

        just_needs_improvement = CoreWebVitalsInput(lcp_ms=2501.0)
        result = self.calculator.calculate_from_input(just_needs_improvement)
        assert result.lcp_rating == VitalsRating.NEEDS_IMPROVEMENT

        just_poor = CoreWebVitalsInput(lcp_ms=4001.0)
        result = self.calculator.calculate_from_input(just_poor)
        assert result.lcp_rating == VitalsRating.POOR

    def test_vitals_threshold_boundaries_fid(self):
        """Test FID threshold boundary conditions."""
        just_good = CoreWebVitalsInput(fid_ms=100.0)
        result = self.calculator.calculate_from_input(just_good)
        assert result.fid_rating == VitalsRating.GOOD

        just_needs_improvement = CoreWebVitalsInput(fid_ms=101.0)
        result = self.calculator.calculate_from_input(just_needs_improvement)
        assert result.fid_rating == VitalsRating.NEEDS_IMPROVEMENT

        just_poor = CoreWebVitalsInput(fid_ms=301.0)
        result = self.calculator.calculate_from_input(just_poor)
        assert result.fid_rating == VitalsRating.POOR

    def test_vitals_threshold_boundaries_cls(self):
        """Test CLS threshold boundary conditions."""
        just_good = CoreWebVitalsInput(cls=0.1)
        result = self.calculator.calculate_from_input(just_good)
        assert result.cls_rating == VitalsRating.GOOD

        just_needs_improvement = CoreWebVitalsInput(cls=0.11)
        result = self.calculator.calculate_from_input(just_needs_improvement)
        assert result.cls_rating == VitalsRating.NEEDS_IMPROVEMENT

        just_poor = CoreWebVitalsInput(cls=0.26)
        result = self.calculator.calculate_from_input(just_poor)
        assert result.cls_rating == VitalsRating.POOR

    def test_vitals_threshold_boundaries_inp(self):
        """Test INP threshold boundary conditions."""
        just_good = CoreWebVitalsInput(inp_ms=200.0)
        result = self.calculator.calculate_from_input(just_good)
        assert result.inp_rating == VitalsRating.GOOD

        just_needs_improvement = CoreWebVitalsInput(inp_ms=201.0)
        result = self.calculator.calculate_from_input(just_needs_improvement)
        assert result.inp_rating == VitalsRating.NEEDS_IMPROVEMENT

        just_poor = CoreWebVitalsInput(inp_ms=501.0)
        result = self.calculator.calculate_from_input(just_poor)
        assert result.inp_rating == VitalsRating.POOR

    def test_vitals_threshold_boundaries_ttfb(self):
        """Test TTFB threshold boundary conditions."""
        just_good = CoreWebVitalsInput(ttfb_ms=800.0)
        result = self.calculator.calculate_from_input(just_good)
        assert result.ttfb_rating == VitalsRating.GOOD

        just_needs_improvement = CoreWebVitalsInput(ttfb_ms=801.0)
        result = self.calculator.calculate_from_input(just_needs_improvement)
        assert result.ttfb_rating == VitalsRating.NEEDS_IMPROVEMENT

        just_poor = CoreWebVitalsInput(ttfb_ms=1801.0)
        result = self.calculator.calculate_from_input(just_poor)
        assert result.ttfb_rating == VitalsRating.POOR

    def test_vitals_threshold_boundaries_fcp(self):
        """Test FCP threshold boundary conditions."""
        just_good = CoreWebVitalsInput(fcp_ms=1800.0)
        result = self.calculator.calculate_from_input(just_good)
        assert result.fcp_rating == VitalsRating.GOOD

        just_needs_improvement = CoreWebVitalsInput(fcp_ms=1801.0)
        result = self.calculator.calculate_from_input(just_needs_improvement)
        assert result.fcp_rating == VitalsRating.NEEDS_IMPROVEMENT

        just_poor = CoreWebVitalsInput(fcp_ms=3001.0)
        result = self.calculator.calculate_from_input(just_poor)
        assert result.fcp_rating == VitalsRating.POOR

    def test_vitals_recommendations_lcp_poor(self):
        """Test that LCP recommendations are generated for poor performance."""
        data = CoreWebVitalsInput(lcp_ms=5000.0)
        result = self.calculator.calculate_from_input(data)

        assert any(
            "LCP" in rec or "contentful" in rec.lower()
            for rec in result.recommendations
        )
        assert any(
            "CDN" in rec or "optimize" in rec.lower()
            for rec in result.recommendations
        )

    def test_vitals_recommendations_fid_poor(self):
        """Test that FID recommendations are generated for poor performance."""
        data = CoreWebVitalsInput(fid_ms=400.0)
        result = self.calculator.calculate_from_input(data)

        assert any(
            "JavaScript" in rec or "worker" in rec.lower()
            for rec in result.recommendations
        )

    def test_vitals_recommendations_cls_poor(self):
        """Test that CLS recommendations are generated for poor performance."""
        data = CoreWebVitalsInput(cls=0.5)
        result = self.calculator.calculate_from_input(data)

        assert any(
            "size" in rec.lower() or "layout" in rec.lower()
            for rec in result.recommendations
        )

    def test_vitals_score_calculation_all_good(self):
        """Test score calculation with all good metrics."""
        data = CoreWebVitalsInput(
            lcp_ms=2000.0,
            fid_ms=50.0,
            cls=0.05,
        )
        result = self.calculator.calculate_from_input(data)
        assert result.score == 100.0

    def test_vitals_score_calculation_all_poor(self):
        """Test score calculation with all poor metrics."""
        data = CoreWebVitalsInput(
            lcp_ms=5000.0,
            fid_ms=400.0,
            cls=0.5,
        )
        result = self.calculator.calculate_from_input(data)
        assert result.score == 20.0

    def test_vitals_score_calculation_mixed(self):
        """Test score calculation with mixed ratings."""
        data = CoreWebVitalsInput(
            lcp_ms=2000.0,
            fid_ms=200.0,
            cls=0.5,
        )
        result = self.calculator.calculate_from_input(data)
        assert 20.0 < result.score < 100.0
        assert result.score == pytest.approx((100 + 60 + 20) / 3, rel=0.1)

    def test_vitals_overall_rating_worst_case(self):
        """Test that overall rating is worst of all individual ratings."""
        data = CoreWebVitalsInput(
            lcp_ms=2000.0,
            fid_ms=50.0,
            cls=0.5,
            inp_ms=150.0,
        )
        result = self.calculator.calculate_from_input(data)
        assert result.overall_rating == VitalsRating.POOR

        data = CoreWebVitalsInput(
            lcp_ms=2000.0,
            fid_ms=200.0,
            cls=0.05,
        )
        result = self.calculator.calculate_from_input(data)
        assert result.overall_rating == VitalsRating.NEEDS_IMPROVEMENT

    def test_vitals_empty_input(self):
        """Test workflow with no metrics provided."""
        data = CoreWebVitalsInput()
        result = self.calculator.calculate_from_input(data)

        assert result.overall_rating == VitalsRating.GOOD
        assert result.score == 100.0
        assert len(result.recommendations) == 0

    def test_vitals_direct_calculation_method(self):
        """Test direct calculate method (not from input model)."""
        result = self.calculator.calculate(
            lcp_ms=2000.0,
            fid_ms=50.0,
            cls=0.05,
        )

        assert isinstance(result, WebVitalsResult)
        assert result.lcp_rating == VitalsRating.GOOD
        assert result.fid_rating == VitalsRating.GOOD
        assert result.cls_rating == VitalsRating.GOOD
        assert result.overall_rating == VitalsRating.GOOD

    def test_vitals_extreme_values(self):
        """Test workflow with extreme performance values."""
        data = CoreWebVitalsInput(
            lcp_ms=10000.0,
            fid_ms=1000.0,
            cls=2.0,
            inp_ms=2000.0,
            ttfb_ms=5000.0,
            fcp_ms=8000.0,
        )
        result = self.calculator.calculate_from_input(data)

        assert result.lcp_rating == VitalsRating.POOR
        assert result.fid_rating == VitalsRating.POOR
        assert result.cls_rating == VitalsRating.POOR
        assert result.inp_rating == VitalsRating.POOR
        assert result.ttfb_rating == VitalsRating.POOR
        assert result.fcp_rating == VitalsRating.POOR
        assert result.overall_rating == VitalsRating.POOR

    def test_vitals_minimal_values(self):
        """Test workflow with minimal performance values."""
        data = CoreWebVitalsInput(
            lcp_ms=100.0,
            fid_ms=10.0,
            cls=0.001,
            inp_ms=50.0,
            ttfb_ms=100.0,
            fcp_ms=500.0,
        )
        result = self.calculator.calculate_from_input(data)

        assert result.lcp_rating == VitalsRating.GOOD
        assert result.fid_rating == VitalsRating.GOOD
        assert result.cls_rating == VitalsRating.GOOD
        assert result.inp_rating == VitalsRating.GOOD
        assert result.ttfb_rating == VitalsRating.GOOD
        assert result.fcp_rating == VitalsRating.GOOD
        assert result.overall_rating == VitalsRating.GOOD
        assert result.score == 100.0
