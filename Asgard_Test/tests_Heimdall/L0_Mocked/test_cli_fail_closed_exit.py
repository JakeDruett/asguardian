"""CH-0088: ratings/gate/compliance CLIs fail closed on exit status."""

import argparse
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from Asgard.Bragi.QualityGate.models.quality_gate_models import GateStatus
from Asgard.Bragi.Ratings.models._scoring_models import MeasurementConfidence
from Asgard.Bragi.Ratings.models.ratings_models import (
    DimensionRating,
    LetterRating,
    ProjectRatings,
    RatingDimension,
)
from Asgard.Heimdall.cli.handlers.ratings import (
    _gate_exit_code,
    _ratings_exit_code,
    _run_differential_gate,
    run_gate_evaluation,
    run_ratings_analysis,
)
from Asgard.Heimdall.cli.handlers.security import (
    _compliance_exit_code,
    run_compliance_analysis,
)


def _dim(letter, dimension, confidence=MeasurementConfidence.MEASURED):
    return DimensionRating(
        dimension=dimension,
        rating=letter,
        score=0.0,
        rationale="test",
        issues_count=0,
        confidence=confidence,
    )


def _project_ratings(overall, maint=LetterRating.A, rel=LetterRating.A, sec=LetterRating.A,
                     maint_conf=MeasurementConfidence.MEASURED,
                     rel_conf=MeasurementConfidence.MEASURED,
                     sec_conf=MeasurementConfidence.MEASURED):
    return ProjectRatings(
        maintainability=_dim(maint, RatingDimension.MAINTAINABILITY, maint_conf),
        reliability=_dim(rel, RatingDimension.RELIABILITY, rel_conf),
        security=_dim(sec, RatingDimension.SECURITY, sec_conf),
        overall_rating=overall,
        scan_path="/tmp/proj",
    )


def _ratings_args(tmp_path, fmt="json", **extra):
    ns = argparse.Namespace(path=str(tmp_path), format=fmt, history=False)
    for key, value in extra.items():
        setattr(ns, key, value)
    return ns


def _patch_ratings_pipeline(monkeypatch, ratings, security_report=None):
    debt = MagicMock()
    debt.analyze.return_value = object()
    monkeypatch.setattr(
        "Asgard.Heimdall.cli.handlers.ratings._TechDebtAnalyzer",
        lambda config: debt,
    )
    sec = MagicMock()
    sec.scan.return_value = security_report if security_report is not None else SimpleNamespace(domain_errors=[])
    monkeypatch.setattr(
        "Asgard.Heimdall.cli.handlers.ratings._StaticSecuritySvc",
        lambda config: sec,
    )
    calc = MagicMock()
    calc.calculate_from_reports.return_value = ratings
    monkeypatch.setattr(
        "Asgard.Heimdall.cli.handlers.ratings.RatingsCalculator",
        lambda config=None: calc,
    )


class TestRatingsExitCode:
    def test_e_rating_returns_1(self):
        ratings = _project_ratings(
            LetterRating.E, maint=LetterRating.A, rel=LetterRating.A, sec=LetterRating.E,
        )
        assert _ratings_exit_code(ratings) == 1

    def test_d_rating_returns_1(self):
        ratings = _project_ratings(LetterRating.D, sec=LetterRating.D)
        assert _ratings_exit_code(ratings) == 1

    def test_a_rating_returns_0(self):
        ratings = _project_ratings(LetterRating.A)
        assert _ratings_exit_code(ratings) == 0

    def test_c_rating_returns_0(self):
        ratings = _project_ratings(LetterRating.C, rel=LetterRating.C)
        assert _ratings_exit_code(ratings) == 0

    def test_unmeasured_na_returns_1(self):
        ratings = _project_ratings(
            LetterRating.NA,
            sec=LetterRating.NA,
            sec_conf=MeasurementConfidence.NOT_MEASURED,
        )
        assert _ratings_exit_code(ratings) == 1

    def test_not_measured_confidence_returns_1(self):
        ratings = _project_ratings(
            LetterRating.A,
            sec_conf=MeasurementConfidence.NOT_MEASURED,
        )
        assert _ratings_exit_code(ratings) == 1

    def test_domain_errors_return_1(self):
        ratings = _project_ratings(LetterRating.A)
        report = SimpleNamespace(domain_errors=[{"domain": "secrets", "message": "boom"}])
        assert _ratings_exit_code(ratings, report) == 1


class TestRunRatingsAnalysisExit:
    def test_e_rating_returns_1(self, tmp_path, monkeypatch, capsys):
        ratings = _project_ratings(
            LetterRating.E, maint=LetterRating.A, rel=LetterRating.A, sec=LetterRating.E,
        )
        _patch_ratings_pipeline(monkeypatch, ratings)
        rc = run_ratings_analysis(_ratings_args(tmp_path))
        assert rc == 1
        out = capsys.readouterr().out
        assert '"overall_rating"' in out

    def test_a_rating_returns_0(self, tmp_path, monkeypatch):
        _patch_ratings_pipeline(monkeypatch, _project_ratings(LetterRating.A))
        assert run_ratings_analysis(_ratings_args(tmp_path)) == 0

    def test_unmeasured_returns_1(self, tmp_path, monkeypatch):
        ratings = _project_ratings(
            LetterRating.NA,
            maint=LetterRating.NA,
            rel=LetterRating.NA,
            sec=LetterRating.NA,
            maint_conf=MeasurementConfidence.NOT_MEASURED,
            rel_conf=MeasurementConfidence.NOT_MEASURED,
            sec_conf=MeasurementConfidence.NOT_MEASURED,
        )
        _patch_ratings_pipeline(monkeypatch, ratings)
        assert run_ratings_analysis(_ratings_args(tmp_path)) == 1

    def test_missing_path_returns_1(self, tmp_path):
        args = _ratings_args(tmp_path / "does-not-exist")
        assert run_ratings_analysis(args) == 1


class TestGateExitCode:
    def test_failed_returns_1(self):
        assert _gate_exit_code(GateStatus.FAILED) == 1

    def test_not_evaluated_returns_1(self):
        assert _gate_exit_code("not_evaluated") == 1

    def test_missing_baseline_returns_1(self):
        assert _gate_exit_code(GateStatus.PASSED, baseline_available=False) == 1

    def test_passed_returns_0(self):
        assert _gate_exit_code(GateStatus.PASSED) == 0

    def test_warning_returns_0(self):
        assert _gate_exit_code(GateStatus.WARNING) == 0


class TestDifferentialGateFailClosed:
    def test_missing_baseline_returns_1(self, tmp_path, monkeypatch, capsys):
        result = SimpleNamespace(
            status=GateStatus.NOT_EVALUATED,
            baseline_available=False,
            new_findings=[],
            blocking_findings=[],
            advisory_findings=[],
            suppressed_findings=[],
            preexisting_count=0,
        )
        evaluator = MagicMock()
        evaluator.evaluate_differential.return_value = result
        monkeypatch.setattr(
            "Asgard.Heimdall.cli.handlers.ratings.QualityGateEvaluator",
            lambda: evaluator,
        )
        args = _ratings_args(tmp_path, fmt="json", diff=True, tier="pr", base="main")
        rc = _run_differential_gate(args, tmp_path, SimpleNamespace())
        assert rc == 1

    def test_exception_fails_closed(self, tmp_path, monkeypatch):
        debt = MagicMock()
        debt.analyze.return_value = object()
        monkeypatch.setattr(
            "Asgard.Heimdall.cli.handlers.ratings._TechDebtAnalyzer",
            lambda config: debt,
        )
        sec = MagicMock()
        sec.scan.return_value = SimpleNamespace(domain_errors=[])
        monkeypatch.setattr(
            "Asgard.Heimdall.cli.handlers.ratings._StaticSecuritySvc",
            lambda config: sec,
        )
        calc = MagicMock()
        calc.calculate_from_reports.return_value = _project_ratings(LetterRating.A)
        monkeypatch.setattr(
            "Asgard.Heimdall.cli.handlers.ratings.RatingsCalculator",
            lambda: calc,
        )
        docs = MagicMock()
        docs.scan.return_value = object()
        monkeypatch.setattr(
            "Asgard.Heimdall.cli.handlers.ratings.DocumentationScanner",
            lambda: docs,
        )
        evaluator = MagicMock()
        evaluator.get_default_gate.return_value = object()
        evaluator.evaluate_from_reports.return_value = SimpleNamespace(
            gate_name="t",
            status="passed",
            summary="ok",
            scan_path=str(tmp_path),
            evaluated_at=datetime.now(),
            condition_results=[],
        )
        evaluator.evaluate_differential.side_effect = RuntimeError("baseline missing")
        monkeypatch.setattr(
            "Asgard.Heimdall.cli.handlers.ratings.QualityGateEvaluator",
            lambda: evaluator,
        )
        args = _ratings_args(tmp_path, fmt="json", diff=True, tier="pr", base="main", history=False)
        assert run_gate_evaluation(args) == 1


class TestComplianceExit:
    def test_findings_return_1(self):
        owasp = SimpleNamespace(total_findings_mapped=2, categories={})
        assert _compliance_exit_code(owasp=owasp) == 1

    def test_cwe_findings_return_1(self):
        cwe = SimpleNamespace(top_25_coverage={
            "CWE-89": SimpleNamespace(findings_count=1),
        })
        assert _compliance_exit_code(cwe=cwe) == 1

    def test_clean_returns_0(self):
        owasp = SimpleNamespace(total_findings_mapped=0, categories={})
        cwe = SimpleNamespace(top_25_coverage={})
        assert _compliance_exit_code(owasp=owasp, cwe=cwe) == 0

    def test_domain_errors_return_1(self):
        owasp = SimpleNamespace(total_findings_mapped=0, categories={})
        report = SimpleNamespace(domain_errors=[{"domain": "injection"}])
        assert _compliance_exit_code(owasp=owasp, security_report=report) == 1

    def test_run_compliance_findings_return_1(self, tmp_path, monkeypatch, capsys):
        sec = MagicMock()
        sec.scan.return_value = SimpleNamespace(domain_errors=[])
        monkeypatch.setattr(
            "Asgard.Heimdall.cli.handlers.security._StaticSecuritySvc",
            lambda config: sec,
        )
        hot = MagicMock()
        hot.scan.return_value = SimpleNamespace(hotspots=[])
        monkeypatch.setattr(
            "Asgard.Heimdall.cli.handlers.security.HotspotDetector",
            lambda: hot,
        )
        reporter = MagicMock()
        reporter.generate_owasp_report.return_value = SimpleNamespace(
            owasp_version="2021",
            overall_grade="C",
            total_findings_mapped=3,
            categories={},
        )
        reporter.generate_cwe_report.return_value = SimpleNamespace(
            cwe_version="2024",
            overall_grade="A",
            top_25_coverage={},
        )
        monkeypatch.setattr(
            "Asgard.Heimdall.cli.handlers.security.ComplianceReporter",
            lambda config: reporter,
        )
        args = argparse.Namespace(
            path=str(tmp_path), format="json", no_owasp=False, no_cwe=False,
        )
        assert run_compliance_analysis(args) == 1

    def test_run_compliance_clean_returns_0(self, tmp_path, monkeypatch):
        sec = MagicMock()
        sec.scan.return_value = SimpleNamespace(domain_errors=[])
        monkeypatch.setattr(
            "Asgard.Heimdall.cli.handlers.security._StaticSecuritySvc",
            lambda config: sec,
        )
        hot = MagicMock()
        hot.scan.return_value = SimpleNamespace(hotspots=[])
        monkeypatch.setattr(
            "Asgard.Heimdall.cli.handlers.security.HotspotDetector",
            lambda: hot,
        )
        reporter = MagicMock()
        reporter.generate_owasp_report.return_value = SimpleNamespace(
            owasp_version="2021",
            overall_grade="A",
            total_findings_mapped=0,
            categories={},
        )
        reporter.generate_cwe_report.return_value = SimpleNamespace(
            cwe_version="2024",
            overall_grade="A",
            top_25_coverage={},
        )
        monkeypatch.setattr(
            "Asgard.Heimdall.cli.handlers.security.ComplianceReporter",
            lambda config: reporter,
        )
        args = argparse.Namespace(
            path=str(tmp_path), format="json", no_owasp=False, no_cwe=False,
        )
        assert run_compliance_analysis(args) == 0
