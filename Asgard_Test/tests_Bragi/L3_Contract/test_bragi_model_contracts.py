"""L3 Contract tests for core Bragi (code quality) models.

Covers QualityGate, Ratings (+ scoring), Calibration, CodeFix,
Dependencies/SBOM, Performance, BugDetection, and Quality analysis models.
"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

# Pre-load Heimdall so Bragi.common.context_classifier's import of
# Heimdall.Security does not re-enter a partially initialized
# Bragi.common module via the Heimdall -> Bragi.Dependencies chain.
import Asgard.Heimdall  # noqa: F401

from Asgard.Bragi.QualityGate.models.quality_gate_models import (
    MetricType,
    GateOperator,
    GateStatus,
    OnMissing,
    GateCondition,
    ConditionResult,
    QualityGate,
    QualityGateResult,
    GateFinding,
    NewCodeDefinition,
    BreakGlassRecord,
    DifferentialGateResult,
    QualityGateConfig,
)
from Asgard.Bragi.Ratings.models.ratings_models import (
    LetterRating,
    RatingDimension,
    DimensionRating,
    DebtThresholds,
    SuppressionStats,
    ProjectRatings,
    RatingsConfig,
)
from Asgard.Bragi.Ratings.models._scoring_models import (
    ScoreCategory,
    MetricUtility,
    CategoryScore,
    ScoreCap,
    ScoreConfidence,
    ROIAction,
    FileQualityScore,
    RiskProfile,
    FileMetricBundle,
)
from Asgard.Bragi.Calibration.models.calibration_models import (
    ThresholdSpec,
    LanguageProfile,
    ValidityReport,
    BugFixCommit,
    SZZResult,
    NBModelFit,
    FeatureAttribution,
    Stage2ValidityReport,
    CalibrationRun,
)
from Asgard.Bragi.CodeFix.models.codefix_models import (
    FixConfidence,
    FixType,
    CodeFix,
    FixSuggestion,
    CodeFixReport,
)
from Asgard.Bragi.Dependencies.models.sbom_models import (
    SBOMFormat,
    ComponentType,
    SBOMComponent,
    SBOMDocument,
    SBOMConfig,
)
from Asgard.Bragi.Performance.models._performance_findings import (
    PerformanceSeverity,
    MemoryIssueType,
    CpuIssueType,
    DatabaseIssueType,
    CacheIssueType,
    MemoryFinding,
    CpuFinding,
    DatabaseFinding,
    CacheFinding,
)
from Asgard.Bragi.Performance.models._performance_reports import (
    PerformanceScanConfig,
    MemoryReport,
    CpuReport,
    DatabaseReport,
    CacheReport,
    PerformanceReport,
)
from Asgard.Bragi.Quality.BugDetection.models.bug_models import (
    BugCategory,
    BugSeverity,
    BugFinding,
    BugReport,
    BugDetectionConfig,
)
from Asgard.Bragi.Quality.models.analysis_models import (
    SeverityLevel,
    FileAnalysis,
    AnalysisResult,
    AnalysisConfig,
)


_NOW = datetime(2026, 5, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# QualityGate
# ---------------------------------------------------------------------------
class TestGateConditionContract:
    def test_requires_metric_operator_threshold(self):
        with pytest.raises((ValidationError, TypeError)):
            GateCondition()

    def test_instantiates_with_required_fields(self):
        cond = GateCondition(
            metric=list(MetricType)[0],
            operator=list(GateOperator)[0],
            threshold=80.0,
        )
        assert cond.threshold == 80.0

    def test_has_model_fields(self):
        fields = set(GateCondition.model_fields.keys())
        assert "metric" in fields
        assert "operator" in fields
        assert "threshold" in fields


class TestConditionResultContract:
    def test_requires_condition(self):
        with pytest.raises((ValidationError, TypeError)):
            ConditionResult()

    def test_instantiates_with_required_fields(self):
        cond = GateCondition(
            metric=list(MetricType)[0],
            operator=list(GateOperator)[0],
            threshold=80.0,
        )
        result = ConditionResult(condition=cond)
        assert result.condition is cond


class TestQualityGateContract:
    def test_requires_name(self):
        with pytest.raises((ValidationError, TypeError)):
            QualityGate()

    def test_instantiates_with_required_fields(self):
        gate = QualityGate(name="default")
        assert gate.name == "default"


class TestQualityGateResultContract:
    def test_requires_gate_name(self):
        with pytest.raises((ValidationError, TypeError)):
            QualityGateResult()

    def test_instantiates_with_required_fields(self):
        result = QualityGateResult(gate_name="default")
        assert result.gate_name == "default"

    def test_has_status_field(self):
        assert "status" in QualityGateResult.model_fields
        assert GateStatus is not None


class TestGateFindingContract:
    def test_requires_rule_id_and_file_path(self):
        with pytest.raises((ValidationError, TypeError)):
            GateFinding()

    def test_instantiates_with_required_fields(self):
        finding = GateFinding(rule_id="BR-001", file_path="src/app.py")
        assert finding.rule_id == "BR-001"


class TestNewCodeDefinitionContract:
    def test_instantiates_with_defaults(self):
        ncd = NewCodeDefinition()
        assert ncd is not None


class TestBreakGlassRecordContract:
    def test_requires_actor_and_reason(self):
        with pytest.raises((ValidationError, TypeError)):
            BreakGlassRecord()

    def test_instantiates_with_required_fields(self):
        record = BreakGlassRecord(actor="release-bot", reason="hotfix")
        assert record.actor == "release-bot"


class TestDifferentialGateResultContract:
    def test_instantiates_with_defaults(self):
        result = DifferentialGateResult()
        assert result is not None


class TestQualityGateConfigContract:
    def test_requires_gate(self):
        with pytest.raises((ValidationError, TypeError)):
            QualityGateConfig()

    def test_instantiates_with_required_fields(self):
        config = QualityGateConfig(gate=QualityGate(name="default"))
        assert config.gate.name == "default"


class TestOnMissingContract:
    def test_enum_nonempty(self):
        assert len(list(OnMissing)) >= 1


# ---------------------------------------------------------------------------
# Ratings
# ---------------------------------------------------------------------------
class TestLetterRatingContract:
    def test_members(self):
        values = {r.value for r in LetterRating}
        assert "A" in values
        assert "E" in values or "F" in values


class TestDimensionRatingContract:
    def test_requires_dimension_and_rating(self):
        with pytest.raises((ValidationError, TypeError)):
            DimensionRating()

    def test_instantiates_with_required_fields(self):
        rating = DimensionRating(
            dimension=list(RatingDimension)[0], rating=LetterRating.A
        )
        assert rating.rating == LetterRating.A


class TestDebtThresholdsContract:
    def test_instantiates_with_defaults(self):
        assert DebtThresholds() is not None


class TestSuppressionStatsContract:
    def test_instantiates_with_defaults(self):
        assert SuppressionStats() is not None


class TestProjectRatingsContract:
    def test_requires_dimensions_and_overall(self):
        with pytest.raises((ValidationError, TypeError)):
            ProjectRatings()

    def test_instantiates_with_required_fields(self):
        def dim(d):
            return DimensionRating(dimension=d, rating=LetterRating.B)

        ratings = ProjectRatings(
            maintainability=dim(RatingDimension.MAINTAINABILITY),
            reliability=dim(RatingDimension.RELIABILITY),
            security=dim(RatingDimension.SECURITY),
            overall_rating=LetterRating.B,
        )
        assert ratings.overall_rating == LetterRating.B


class TestRatingsConfigContract:
    def test_instantiates_with_defaults(self):
        assert RatingsConfig() is not None


# ---------------------------------------------------------------------------
# Ratings scoring models
# ---------------------------------------------------------------------------
class TestMetricUtilityContract:
    def test_requires_core_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            MetricUtility()

    def test_instantiates_with_required_fields(self):
        util = MetricUtility(
            metric_id="complexity", category=list(ScoreCategory)[0], utility=0.5
        )
        assert util.metric_id == "complexity"


class TestCategoryScoreContract:
    def test_requires_category_and_weight(self):
        with pytest.raises((ValidationError, TypeError)):
            CategoryScore()

    def test_instantiates_with_required_fields(self):
        score = CategoryScore(category=list(ScoreCategory)[0], weight=0.25)
        assert score.weight == 0.25


class TestScoreCapAndConfidenceContract:
    def test_instantiate_with_defaults(self):
        assert ScoreCap() is not None
        assert ScoreConfidence() is not None


class TestROIActionContract:
    def test_requires_core_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ROIAction()

    def test_instantiates_with_required_fields(self):
        action = ROIAction(
            metric_id="complexity", description="refactor", score_delta=2.5
        )
        assert action.score_delta == 2.5


class TestFileQualityScoreContract:
    def test_requires_file_path(self):
        with pytest.raises((ValidationError, TypeError)):
            FileQualityScore()

    def test_instantiates_with_required_fields(self):
        score = FileQualityScore(file_path="src/app.py")
        assert score.file_path == "src/app.py"


class TestRiskProfileAndBundleContract:
    def test_instantiate_with_defaults(self):
        assert RiskProfile() is not None
        assert FileMetricBundle() is not None


# ---------------------------------------------------------------------------
# Calibration
# ---------------------------------------------------------------------------
class TestThresholdSpecContract:
    def test_requires_warn_and_fail(self):
        with pytest.raises((ValidationError, TypeError)):
            ThresholdSpec()

    def test_instantiates_with_required_fields(self):
        spec = ThresholdSpec(warn=10.0, fail=20.0)
        assert spec.warn == 10.0


class TestLanguageProfileContract:
    def test_requires_language(self):
        with pytest.raises((ValidationError, TypeError)):
            LanguageProfile()

    def test_instantiates_with_required_fields(self):
        profile = LanguageProfile(language="python")
        assert profile.language == "python"


class TestValidityReportContract:
    def test_requires_rule_id(self):
        with pytest.raises((ValidationError, TypeError)):
            ValidityReport()

    def test_instantiates_with_required_fields(self):
        report = ValidityReport(rule_id="BR-001")
        assert report.rule_id == "BR-001"


class TestBugFixCommitContract:
    def test_requires_core_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            BugFixCommit()

    def test_instantiates_with_required_fields(self):
        commit = BugFixCommit(
            sha="a" * 40, parent_sha="b" * 40, timestamp=1700000000, subject="fix: bug"
        )
        assert commit.subject == "fix: bug"


class TestCalibrationDefaultModelsContract:
    def test_instantiate_with_defaults(self):
        assert SZZResult() is not None
        assert NBModelFit() is not None
        assert CalibrationRun() is not None

    def test_attribution_and_stage2_require_rule_id(self):
        with pytest.raises((ValidationError, TypeError)):
            FeatureAttribution()
        with pytest.raises((ValidationError, TypeError)):
            Stage2ValidityReport()
        assert FeatureAttribution(rule_id="BR-001").rule_id == "BR-001"
        assert Stage2ValidityReport(rule_id="BR-001").rule_id == "BR-001"


# ---------------------------------------------------------------------------
# CodeFix
# ---------------------------------------------------------------------------
class TestCodeFixContract:
    def test_requires_core_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            CodeFix()

    def test_instantiates_with_required_fields(self):
        fix = CodeFix(
            rule_id="BR-001",
            title="Remove unused import",
            description="delete line",
            fix_type=list(FixType)[0],
            confidence=list(FixConfidence)[0],
        )
        assert fix.rule_id == "BR-001"


class TestFixSuggestionContract:
    def test_requires_core_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            FixSuggestion()

    def test_instantiates_with_required_fields(self):
        fix = CodeFix(
            rule_id="BR-001",
            title="t",
            description="d",
            fix_type=list(FixType)[0],
            confidence=list(FixConfidence)[0],
        )
        suggestion = FixSuggestion(
            file_path="src/app.py",
            line_number=10,
            rule_id="BR-001",
            finding_title="unused import",
            fix=fix,
        )
        assert suggestion.line_number == 10


class TestCodeFixReportContract:
    def test_instantiates_with_defaults(self):
        assert CodeFixReport() is not None


# ---------------------------------------------------------------------------
# Dependencies / SBOM
# ---------------------------------------------------------------------------
class TestSBOMComponentContract:
    def test_requires_name_and_version(self):
        with pytest.raises((ValidationError, TypeError)):
            SBOMComponent()

    def test_instantiates_with_required_fields(self):
        component = SBOMComponent(name="requests", version="2.32.0")
        assert component.name == "requests"

    def test_component_type_enum_nonempty(self):
        assert len(list(ComponentType)) >= 1


class TestSBOMDocumentContract:
    def test_requires_core_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SBOMDocument()

    def test_instantiates_with_required_fields(self):
        doc = SBOMDocument(
            format=list(SBOMFormat)[0],
            spec_version="1.5",
            document_id="doc-1",
            document_name="sbom",
            project_name="asgard",
            created_at=_NOW,
        )
        assert doc.project_name == "asgard"


class TestSBOMConfigContract:
    def test_instantiates_with_defaults(self):
        assert SBOMConfig() is not None


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------
class TestPerformanceFindingContracts:
    @pytest.mark.parametrize(
        "model_cls,issue_enum",
        [
            (MemoryFinding, MemoryIssueType),
            (CpuFinding, CpuIssueType),
            (DatabaseFinding, DatabaseIssueType),
            (CacheFinding, CacheIssueType),
        ],
    )
    def test_requires_core_fields(self, model_cls, issue_enum):
        with pytest.raises((ValidationError, TypeError)):
            model_cls()

    @pytest.mark.parametrize(
        "model_cls,issue_enum",
        [
            (MemoryFinding, MemoryIssueType),
            (CpuFinding, CpuIssueType),
            (DatabaseFinding, DatabaseIssueType),
            (CacheFinding, CacheIssueType),
        ],
    )
    def test_instantiates_with_required_fields(self, model_cls, issue_enum):
        finding = model_cls(
            file_path="src/app.py",
            line_number=5,
            issue_type=list(issue_enum)[0],
            severity=list(PerformanceSeverity)[0],
            description="issue",
            recommendation="fix it",
        )
        assert finding.file_path == "src/app.py"
        assert finding.line_number == 5


class TestPerformanceReportContracts:
    def test_scan_config_instantiates_with_defaults(self):
        assert PerformanceScanConfig() is not None

    @pytest.mark.parametrize(
        "model_cls", [MemoryReport, CpuReport, DatabaseReport, CacheReport]
    )
    def test_reports_require_scan_path(self, model_cls):
        with pytest.raises((ValidationError, TypeError)):
            model_cls()
        report = model_cls(scan_path="/repo")
        assert report.scan_path == "/repo"

    def test_performance_report_requires_scan_path_and_config(self):
        with pytest.raises((ValidationError, TypeError)):
            PerformanceReport()
        report = PerformanceReport(
            scan_path="/repo", scan_config=PerformanceScanConfig()
        )
        assert report.scan_path == "/repo"


# ---------------------------------------------------------------------------
# BugDetection
# ---------------------------------------------------------------------------
class TestBugFindingContract:
    def test_requires_core_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            BugFinding()

    def test_instantiates_with_required_fields(self):
        finding = BugFinding(
            file_path="src/app.py",
            line_number=12,
            category=list(BugCategory)[0],
            severity=list(BugSeverity)[0],
            title="off-by-one",
            description="loop bound",
        )
        assert finding.title == "off-by-one"


class TestBugReportAndConfigContract:
    def test_instantiate_with_defaults(self):
        assert BugReport() is not None
        assert BugDetectionConfig() is not None


# ---------------------------------------------------------------------------
# Quality analysis models
# ---------------------------------------------------------------------------
class TestFileAnalysisContract:
    def test_requires_core_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            FileAnalysis()

    def test_instantiates_with_required_fields(self):
        analysis = FileAnalysis(
            file_path="/repo/src/app.py",
            line_count=1200,
            threshold=1000,
            lines_over=200,
            severity=list(SeverityLevel)[0],
            file_extension=".py",
            relative_path="src/app.py",
        )
        assert analysis.lines_over == 200


class TestAnalysisResultContract:
    def test_requires_threshold_and_scan_path(self):
        with pytest.raises((ValidationError, TypeError)):
            AnalysisResult()

    def test_instantiates_with_required_fields(self):
        result = AnalysisResult(default_threshold=1000, scan_path="/repo")
        assert result.scan_path == "/repo"


class TestAnalysisConfigContract:
    def test_instantiates_with_defaults(self):
        assert AnalysisConfig() is not None
