"""
Tests for Plan Heimdall-06 — optional `SECURITY_SCORE >= threshold`
quality-gate condition (multiplicative-decay score feeding the gate).
"""
from types import SimpleNamespace

from Asgard.Bragi.QualityGate.models.quality_gate_models import (
    METRIC_DETERMINISM,
    GateStatus,
    MetricDeterminism,
    MetricType,
)
from Asgard.Bragi.QualityGate.services._quality_gate_helpers import (
    build_asgard_way_gate,
    extract_metrics_from_reports,
)
from Asgard.Bragi.QualityGate.services.quality_gate_evaluator import (
    QualityGateEvaluator,
)


class TestSecurityScoreMetric:
    def test_metric_exists_and_is_heuristic(self):
        # Heuristic inputs -> the score may never hard-block a pipeline.
        assert METRIC_DETERMINISM[MetricType.SECURITY_SCORE] is MetricDeterminism.HEURISTIC

    def test_default_gate_has_warn_only_skip_on_missing_condition(self):
        gate = build_asgard_way_gate()
        conditions = [
            c for c in gate.conditions
            if c.metric == MetricType.SECURITY_SCORE.value or c.metric == MetricType.SECURITY_SCORE
        ]
        assert len(conditions) == 1
        cond = conditions[0]
        assert cond.error_on_fail is False
        assert str(cond.on_missing) in ("skip", "OnMissing.SKIP")

    def test_extracted_from_security_report_when_present(self):
        report = SimpleNamespace(security_score=73.0)
        metrics = extract_metrics_from_reports(security_report=report)
        assert metrics[MetricType.SECURITY_SCORE] == 73.0

    def test_not_fabricated_when_absent(self):
        # A report without the field must not be assumed clean.
        report = SimpleNamespace()
        metrics = extract_metrics_from_reports(security_report=report)
        assert MetricType.SECURITY_SCORE not in metrics

    def test_unmeasured_letter_ratings_are_omitted(self):
        """N/A / NOT_MEASURED dimensions must not extract as A."""
        from Asgard.Bragi.Ratings.models.ratings_models import (
            DimensionRating,
            LetterRating,
            ProjectRatings,
            RatingDimension,
        )
        from Asgard.Bragi.Ratings.models._scoring_models import MeasurementConfidence

        na = DimensionRating(
            dimension=RatingDimension.SECURITY,
            rating=LetterRating.NA,
            confidence=MeasurementConfidence.NOT_MEASURED,
        )
        measured = DimensionRating(
            dimension=RatingDimension.MAINTAINABILITY,
            rating=LetterRating.B,
        )
        ratings = ProjectRatings(
            maintainability=measured,
            reliability=na,
            security=na,
            overall_rating=LetterRating.NA,
        )
        metrics = extract_metrics_from_reports(ratings=ratings)
        assert MetricType.SECURITY_RATING not in metrics
        assert MetricType.RELIABILITY_RATING not in metrics
        assert metrics[MetricType.MAINTAINABILITY_RATING] == "B"

    def test_blocker_finding_counts_as_critical(self):
        report = SimpleNamespace(findings=[SimpleNamespace(severity="blocker")])
        metrics = extract_metrics_from_reports(security_report=report)
        assert metrics[MetricType.CRITICAL_VULNERABILITIES] == 1.0


class TestSecurityScoreEvaluation:
    def _evaluate(self, metrics):
        evaluator = QualityGateEvaluator()
        return evaluator.evaluate(build_asgard_way_gate(), metrics)

    def _score_result(self, result):
        for r in result.condition_results:
            if str(r.condition.metric) in ("security_score", "MetricType.SECURITY_SCORE"):
                return r
        return None

    def _base_metrics(self):
        return {
            MetricType.SECURITY_RATING: "A",
            MetricType.RELIABILITY_RATING: "A",
            MetricType.MAINTAINABILITY_RATING: "A",
            MetricType.CRITICAL_VULNERABILITIES: 0.0,
        }

    def test_low_score_fails_condition_as_warning_only(self):
        metrics = self._base_metrics()
        metrics[MetricType.SECURITY_SCORE] = 15.0
        result = self._evaluate(metrics)
        score_result = self._score_result(result)
        assert score_result is not None
        assert score_result.passed is False
        # Warn-only condition never fails the whole gate by itself.
        assert result.status != GateStatus.FAILED

    def test_good_score_passes(self):
        metrics = self._base_metrics()
        metrics[MetricType.SECURITY_SCORE] = 95.0
        score_result = self._score_result(self._evaluate(metrics))
        assert score_result is not None
        assert score_result.passed is True
