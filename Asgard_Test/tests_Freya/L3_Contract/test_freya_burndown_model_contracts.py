"""L3 Contract tests for remaining Freya pydantic models (Phase 2.2 burn-down).

Covers Freya-owned models that lacked L3 contract coverage per
_scripts/list_pydantic_models.py: Accessibility, Config, Integration,
Performance budgets/timing, Responsive, SEO, Scoring, Security, and Visual.
"""
import pytest
from pydantic import ValidationError

from Asgard.Freya.Accessibility.models._accessibility_enums import (
    ColorInfo,
)
from Asgard.Freya.Accessibility.models._accessibility_report_models import (
    ARIAReport,
    ARIAViolation,
    ContrastIssue,
    ContrastReport,
    ContrastResult,
    HeadingInfo,
    KeyboardIssue,
    KeyboardNavigationReport,
    ScreenReaderIssue,
    ScreenReaderReport,
)
from Asgard.Freya.Config.models.config_models import (
    FreyaConfig,
    RouteBudgetRef,
    VisualConfig,
)
from Asgard.Freya.Integration.models._integration_base_models import (
    BaselineConfig,
    BaselineEntry,
    BrowserConfig,
    CrawlConfig,
    EnvironmentFingerprint,
    ReportConfig,
    UnifiedTestConfig,
    UnifiedTestReport,
    UnifiedTestResult,
)
from Asgard.Freya.Integration.models._integration_crawl_models import (
    CrawledPage,
    PageTestResult,
    SiteCrawlReport,
)
from Asgard.Freya.Performance.models._budget_models import (
    BudgetEvaluation,
    BudgetThreshold,
    RouteBudget,
)
from Asgard.Freya.Performance.models._performance_timing_models import (
    ResourceTiming,
)
from Asgard.Freya.Responsive.models.responsive_models import (
    MobileCompatibilityIssue,
    TouchTargetIssue,
    TouchTargetReport,
    ViewportIssue,
)
from Asgard.Freya.SEO.models.seo_models import (
    RobotDirective,
    RobotsTxtReport,
    SitemapEntry,
    SitemapReport,
    StructuredDataItem,
    StructuredDataReport,
)
from Asgard.Freya.Scoring.models.scoring_models import (
    Finding,
    GateConfig,
    GateResult,
    GradedScore,
)
from Asgard.Freya.Security.models.security_header_models import (
    MixedContentFinding,
    MixedContentReport,
    SRIFinding,
    SRIReport,
)
from Asgard.Freya.Visual.models.visual_models import (
    DifferenceRegion,
    ElementBox,
    LayoutIssue,
    LayoutReport,
    RegressionTestCase,
    RegressionTestSuite,
    StyleIssue,
    StyleReport,
)

# ---------------------------------------------------------------------------
# Asgard.Freya.Accessibility.models._accessibility_enums
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Asgard.Freya.Accessibility.models._accessibility_report_models
# ---------------------------------------------------------------------------

class TestARIAReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ARIAReport()

    def test_accepts_valid_data(self):
        obj = ARIAReport(url="x")
        assert isinstance(obj, ARIAReport)

    def test_round_trip(self):
        obj = ARIAReport(url="x")
        assert ARIAReport.model_validate(obj.model_dump()) == obj

class TestARIAViolationContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ARIAViolation()

    def test_accepts_valid_data(self):
        obj = ARIAViolation(violation_type='missing_required_attribute', element_selector="x", description="x", severity='critical', wcag_reference="x", suggested_fix="x")
        assert isinstance(obj, ARIAViolation)

    def test_round_trip(self):
        obj = ARIAViolation(violation_type='missing_required_attribute', element_selector="x", description="x", severity='critical', wcag_reference="x", suggested_fix="x")
        assert ARIAViolation.model_validate(obj.model_dump()) == obj

class TestContrastIssueContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ContrastIssue()

    def test_accepts_valid_data(self):
        obj = ContrastIssue(element_selector="x", foreground_color="x", background_color="x", contrast_ratio=1.0, required_ratio=1.0)
        assert isinstance(obj, ContrastIssue)

    def test_round_trip(self):
        obj = ContrastIssue(element_selector="x", foreground_color="x", background_color="x", contrast_ratio=1.0, required_ratio=1.0)
        assert ContrastIssue.model_validate(obj.model_dump()) == obj

class TestContrastReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ContrastReport()

    def test_accepts_valid_data(self):
        obj = ContrastReport(url="x", wcag_level="x")
        assert isinstance(obj, ContrastReport)

    def test_round_trip(self):
        obj = ContrastReport(url="x", wcag_level="x")
        assert ContrastReport.model_validate(obj.model_dump()) == obj

class TestContrastResultContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ContrastResult()

    def test_accepts_valid_data(self):
        obj = ContrastResult(element_selector="x", foreground_color="x", background_color="x", contrast_ratio=1.0, required_ratio=1.0, text_size='normal', font_size_px=1.0, font_weight="x", is_passing=True, wcag_aa_pass=True, wcag_aaa_pass=True)
        assert isinstance(obj, ContrastResult)

    def test_round_trip(self):
        obj = ContrastResult(element_selector="x", foreground_color="x", background_color="x", contrast_ratio=1.0, required_ratio=1.0, text_size='normal', font_size_px=1.0, font_weight="x", is_passing=True, wcag_aa_pass=True, wcag_aaa_pass=True)
        assert ContrastResult.model_validate(obj.model_dump()) == obj

class TestHeadingInfoContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            HeadingInfo()

    def test_accepts_valid_data(self):
        obj = HeadingInfo(level=1, text="x", element_selector="x")
        assert isinstance(obj, HeadingInfo)

    def test_round_trip(self):
        obj = HeadingInfo(level=1, text="x", element_selector="x")
        assert HeadingInfo.model_validate(obj.model_dump()) == obj

class TestKeyboardIssueContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            KeyboardIssue()

    def test_accepts_valid_data(self):
        obj = KeyboardIssue(issue_type='no_focus_indicator', element_selector="x", description="x", severity='critical', wcag_reference="x", suggested_fix="x")
        assert isinstance(obj, KeyboardIssue)

    def test_round_trip(self):
        obj = KeyboardIssue(issue_type='no_focus_indicator', element_selector="x", description="x", severity='critical', wcag_reference="x", suggested_fix="x")
        assert KeyboardIssue.model_validate(obj.model_dump()) == obj

class TestKeyboardNavigationReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            KeyboardNavigationReport()

    def test_accepts_valid_data(self):
        obj = KeyboardNavigationReport(url="x")
        assert isinstance(obj, KeyboardNavigationReport)

    def test_round_trip(self):
        obj = KeyboardNavigationReport(url="x")
        assert KeyboardNavigationReport.model_validate(obj.model_dump()) == obj

class TestScreenReaderIssueContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ScreenReaderIssue()

    def test_accepts_valid_data(self):
        obj = ScreenReaderIssue(issue_type='missing_alt_text', element_selector="x", description="x", severity='critical', wcag_reference="x", suggested_fix="x")
        assert isinstance(obj, ScreenReaderIssue)

    def test_round_trip(self):
        obj = ScreenReaderIssue(issue_type='missing_alt_text', element_selector="x", description="x", severity='critical', wcag_reference="x", suggested_fix="x")
        assert ScreenReaderIssue.model_validate(obj.model_dump()) == obj

class TestScreenReaderReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ScreenReaderReport()

    def test_accepts_valid_data(self):
        obj = ScreenReaderReport(url="x")
        assert isinstance(obj, ScreenReaderReport)

    def test_round_trip(self):
        obj = ScreenReaderReport(url="x")
        assert ScreenReaderReport.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Freya.Config.models.config_models
# ---------------------------------------------------------------------------

class TestFreyaConfigContract:
    def test_instantiates_with_defaults(self):
        obj = FreyaConfig()
        assert obj is not None

    def test_round_trip(self):
        obj = FreyaConfig()
        assert FreyaConfig.model_validate(obj.model_dump()) == obj

class TestRouteBudgetRefContract:
    def test_instantiates_with_defaults(self):
        obj = RouteBudgetRef()
        assert obj is not None

    def test_round_trip(self):
        obj = RouteBudgetRef()
        assert RouteBudgetRef.model_validate(obj.model_dump()) == obj

class TestVisualConfigContract:
    def test_instantiates_with_defaults(self):
        obj = VisualConfig()
        assert obj is not None

    def test_round_trip(self):
        obj = VisualConfig()
        assert VisualConfig.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Freya.Integration.models._integration_base_models
# ---------------------------------------------------------------------------

class TestBaselineConfigContract:
    def test_instantiates_with_defaults(self):
        obj = BaselineConfig()
        assert obj is not None

    def test_round_trip(self):
        obj = BaselineConfig()
        assert BaselineConfig.model_validate(obj.model_dump()) == obj

class TestBaselineEntryContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            BaselineEntry()

    def test_accepts_valid_data(self):
        obj = BaselineEntry(url="x", name="x", created_at="x", updated_at="x", screenshot_path="x", viewport_width=1, viewport_height=1, hash="x")
        assert isinstance(obj, BaselineEntry)

    def test_round_trip(self):
        obj = BaselineEntry(url="x", name="x", created_at="x", updated_at="x", screenshot_path="x", viewport_width=1, viewport_height=1, hash="x")
        assert BaselineEntry.model_validate(obj.model_dump()) == obj

class TestBrowserConfigContract:
    def test_instantiates_with_defaults(self):
        obj = BrowserConfig()
        assert obj is not None

    def test_round_trip(self):
        obj = BrowserConfig()
        assert BrowserConfig.model_validate(obj.model_dump()) == obj

class TestCrawlConfigContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            CrawlConfig()

    def test_accepts_valid_data(self):
        obj = CrawlConfig(start_url="x")
        assert isinstance(obj, CrawlConfig)

    def test_round_trip(self):
        obj = CrawlConfig(start_url="x")
        assert CrawlConfig.model_validate(obj.model_dump()) == obj

class TestEnvironmentFingerprintContract:
    def test_instantiates_with_defaults(self):
        obj = EnvironmentFingerprint()
        assert obj is not None

    def test_round_trip(self):
        obj = EnvironmentFingerprint()
        assert EnvironmentFingerprint.model_validate(obj.model_dump()) == obj

class TestReportConfigContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ReportConfig()

    def test_accepts_valid_data(self):
        obj = ReportConfig(output_path="x")
        assert isinstance(obj, ReportConfig)

    def test_round_trip(self):
        obj = ReportConfig(output_path="x")
        assert ReportConfig.model_validate(obj.model_dump()) == obj

class TestUnifiedTestConfigContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            UnifiedTestConfig()

    def test_accepts_valid_data(self):
        obj = UnifiedTestConfig(url="x")
        assert isinstance(obj, UnifiedTestConfig)

    def test_round_trip(self):
        obj = UnifiedTestConfig(url="x")
        assert UnifiedTestConfig.model_validate(obj.model_dump()) == obj

class TestUnifiedTestReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            UnifiedTestReport()

    def test_accepts_valid_data(self):
        obj = UnifiedTestReport(url="x", tested_at="x", duration_ms=1, total_tests=1, passed=1, failed=1, config=UnifiedTestConfig(url="x"))
        assert isinstance(obj, UnifiedTestReport)

    def test_round_trip(self):
        obj = UnifiedTestReport(url="x", tested_at="x", duration_ms=1, total_tests=1, passed=1, failed=1, config=UnifiedTestConfig(url="x"))
        assert UnifiedTestReport.model_validate(obj.model_dump()) == obj

class TestUnifiedTestResultContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            UnifiedTestResult()

    def test_accepts_valid_data(self):
        obj = UnifiedTestResult(category='accessibility', test_name="x", passed=True, message="x")
        assert isinstance(obj, UnifiedTestResult)

    def test_round_trip(self):
        obj = UnifiedTestResult(category='accessibility', test_name="x", passed=True, message="x")
        assert UnifiedTestResult.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Freya.Integration.models._integration_crawl_models
# ---------------------------------------------------------------------------

class TestCrawledPageContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            CrawledPage()

    def test_accepts_valid_data(self):
        obj = CrawledPage(url="x", depth=1)
        assert isinstance(obj, CrawledPage)

    def test_round_trip(self):
        obj = CrawledPage(url="x", depth=1)
        assert CrawledPage.model_validate(obj.model_dump()) == obj

class TestPageTestResultContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            PageTestResult()

    def test_accepts_valid_data(self):
        obj = PageTestResult(url="x", tested_at="x", duration_ms=1)
        assert isinstance(obj, PageTestResult)

    def test_round_trip(self):
        obj = PageTestResult(url="x", tested_at="x", duration_ms=1)
        assert PageTestResult.model_validate(obj.model_dump()) == obj

class TestSiteCrawlReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SiteCrawlReport()

    def test_accepts_valid_data(self):
        obj = SiteCrawlReport(start_url="x", crawl_started="x", crawl_completed="x", total_duration_ms=1, pages_discovered=1, pages_tested=1, pages_skipped=1, pages_errored=1, config=CrawlConfig(start_url="x"))
        assert isinstance(obj, SiteCrawlReport)

    def test_round_trip(self):
        obj = SiteCrawlReport(start_url="x", crawl_started="x", crawl_completed="x", total_duration_ms=1, pages_discovered=1, pages_tested=1, pages_skipped=1, pages_errored=1, config=CrawlConfig(start_url="x"))
        assert SiteCrawlReport.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Freya.Performance.models._budget_models
# ---------------------------------------------------------------------------

class TestBudgetEvaluationContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            BudgetEvaluation()

    def test_accepts_valid_data(self):
        obj = BudgetEvaluation(metric="x", value=1.0, status='pass')
        assert isinstance(obj, BudgetEvaluation)

    def test_round_trip(self):
        obj = BudgetEvaluation(metric="x", value=1.0, status='pass')
        assert BudgetEvaluation.model_validate(obj.model_dump()) == obj

class TestBudgetThresholdContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            BudgetThreshold()

    def test_accepts_valid_data(self):
        obj = BudgetThreshold(metric="x")
        assert isinstance(obj, BudgetThreshold)

    def test_round_trip(self):
        obj = BudgetThreshold(metric="x")
        assert BudgetThreshold.model_validate(obj.model_dump()) == obj

class TestRouteBudgetContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            RouteBudget()

    def test_accepts_valid_data(self):
        obj = RouteBudget(archetype='document')
        assert isinstance(obj, RouteBudget)

    def test_round_trip(self):
        obj = RouteBudget(archetype='document')
        assert RouteBudget.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Freya.Performance.models._performance_timing_models
# ---------------------------------------------------------------------------

class TestResourceTimingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ResourceTiming()

    def test_accepts_valid_data(self):
        obj = ResourceTiming(url="x", resource_type='document', name="x")
        assert isinstance(obj, ResourceTiming)

    def test_round_trip(self):
        obj = ResourceTiming(url="x", resource_type='document', name="x")
        assert ResourceTiming.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Freya.Responsive.models.responsive_models
# ---------------------------------------------------------------------------

class TestMobileCompatibilityIssueContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            MobileCompatibilityIssue()

    def test_accepts_valid_data(self):
        obj = MobileCompatibilityIssue(issue_type='flash_content', description="x", severity="x", suggested_fix="x")
        assert isinstance(obj, MobileCompatibilityIssue)

    def test_round_trip(self):
        obj = MobileCompatibilityIssue(issue_type='flash_content', description="x", severity="x", suggested_fix="x")
        assert MobileCompatibilityIssue.model_validate(obj.model_dump()) == obj

class TestTouchTargetIssueContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            TouchTargetIssue()

    def test_accepts_valid_data(self):
        obj = TouchTargetIssue(element_selector="x", element_type="x", width=1.0, height=1.0, description="x", severity="x", suggested_fix="x")
        assert isinstance(obj, TouchTargetIssue)

    def test_round_trip(self):
        obj = TouchTargetIssue(element_selector="x", element_type="x", width=1.0, height=1.0, description="x", severity="x", suggested_fix="x")
        assert TouchTargetIssue.model_validate(obj.model_dump()) == obj

class TestTouchTargetReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            TouchTargetReport()

    def test_accepts_valid_data(self):
        obj = TouchTargetReport(url="x", viewport_width=1, viewport_height=1)
        assert isinstance(obj, TouchTargetReport)

    def test_round_trip(self):
        obj = TouchTargetReport(url="x", viewport_width=1, viewport_height=1)
        assert TouchTargetReport.model_validate(obj.model_dump()) == obj

class TestViewportIssueContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ViewportIssue()

    def test_accepts_valid_data(self):
        obj = ViewportIssue(issue_type='missing_viewport_meta', description="x", severity="x", suggested_fix="x")
        assert isinstance(obj, ViewportIssue)

    def test_round_trip(self):
        obj = ViewportIssue(issue_type='missing_viewport_meta', description="x", severity="x", suggested_fix="x")
        assert ViewportIssue.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Freya.SEO.models.seo_models
# ---------------------------------------------------------------------------

class TestRobotDirectiveContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            RobotDirective()

    def test_accepts_valid_data(self):
        obj = RobotDirective(directive="x", value="x")
        assert isinstance(obj, RobotDirective)

    def test_round_trip(self):
        obj = RobotDirective(directive="x", value="x")
        assert RobotDirective.model_validate(obj.model_dump()) == obj

class TestRobotsTxtReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            RobotsTxtReport()

    def test_accepts_valid_data(self):
        obj = RobotsTxtReport(url="x", robots_url="x")
        assert isinstance(obj, RobotsTxtReport)

    def test_round_trip(self):
        obj = RobotsTxtReport(url="x", robots_url="x")
        assert RobotsTxtReport.model_validate(obj.model_dump()) == obj

class TestSitemapEntryContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SitemapEntry()

    def test_accepts_valid_data(self):
        obj = SitemapEntry(loc="x")
        assert isinstance(obj, SitemapEntry)

    def test_round_trip(self):
        obj = SitemapEntry(loc="x")
        assert SitemapEntry.model_validate(obj.model_dump()) == obj

class TestSitemapReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SitemapReport()

    def test_accepts_valid_data(self):
        obj = SitemapReport(url="x", sitemap_url="x")
        assert isinstance(obj, SitemapReport)

    def test_round_trip(self):
        obj = SitemapReport(url="x", sitemap_url="x")
        assert SitemapReport.model_validate(obj.model_dump()) == obj

class TestStructuredDataItemContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            StructuredDataItem()

    def test_accepts_valid_data(self):
        obj = StructuredDataItem(data_type='json-ld', schema_type="x")
        assert isinstance(obj, StructuredDataItem)

    def test_round_trip(self):
        obj = StructuredDataItem(data_type='json-ld', schema_type="x")
        assert StructuredDataItem.model_validate(obj.model_dump()) == obj

class TestStructuredDataReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            StructuredDataReport()

    def test_accepts_valid_data(self):
        obj = StructuredDataReport(url="x")
        assert isinstance(obj, StructuredDataReport)

    def test_round_trip(self):
        obj = StructuredDataReport(url="x")
        assert StructuredDataReport.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Freya.Scoring.models.scoring_models
# ---------------------------------------------------------------------------

class TestFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            Finding()

    def test_accepts_valid_data(self):
        obj = Finding(category="x", severity='blocker', check_id="x", message="x")
        assert isinstance(obj, Finding)

    def test_round_trip(self):
        obj = Finding(category="x", severity='blocker', check_id="x", message="x")
        assert Finding.model_validate(obj.model_dump()) == obj

class TestGateConfigContract:
    def test_instantiates_with_defaults(self):
        obj = GateConfig()
        assert obj is not None

    def test_round_trip(self):
        obj = GateConfig()
        assert GateConfig.model_validate(obj.model_dump()) == obj

class TestGateResultContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            GateResult()

    def test_accepts_valid_data(self):
        obj = GateResult(passed=True)
        assert isinstance(obj, GateResult)

    def test_round_trip(self):
        obj = GateResult(passed=True)
        assert GateResult.model_validate(obj.model_dump()) == obj

class TestGradedScoreContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            GradedScore()

    def test_accepts_valid_data(self):
        obj = GradedScore(base_score=1.0, capped_score=1.0, grade='A')
        assert isinstance(obj, GradedScore)

    def test_round_trip(self):
        obj = GradedScore(base_score=1.0, capped_score=1.0, grade='A')
        assert GradedScore.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Freya.Security.models.security_header_models
# ---------------------------------------------------------------------------

class TestMixedContentFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            MixedContentFinding()

    def test_accepts_valid_data(self):
        obj = MixedContentFinding(url="x", resource_type="x", category="x", severity="x", description="x")
        assert isinstance(obj, MixedContentFinding)

    def test_round_trip(self):
        obj = MixedContentFinding(url="x", resource_type="x", category="x", severity="x", description="x")
        assert MixedContentFinding.model_validate(obj.model_dump()) == obj

class TestMixedContentReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            MixedContentReport()

    def test_accepts_valid_data(self):
        obj = MixedContentReport(url="x")
        assert isinstance(obj, MixedContentReport)

    def test_round_trip(self):
        obj = MixedContentReport(url="x")
        assert MixedContentReport.model_validate(obj.model_dump()) == obj

class TestSRIFindingContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SRIFinding()

    def test_accepts_valid_data(self):
        obj = SRIFinding(element="x", url="x", severity="x", issue_type="x", description="x")
        assert isinstance(obj, SRIFinding)

    def test_round_trip(self):
        obj = SRIFinding(element="x", url="x", severity="x", issue_type="x", description="x")
        assert SRIFinding.model_validate(obj.model_dump()) == obj

class TestSRIReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            SRIReport()

    def test_accepts_valid_data(self):
        obj = SRIReport(url="x")
        assert isinstance(obj, SRIReport)

    def test_round_trip(self):
        obj = SRIReport(url="x")
        assert SRIReport.model_validate(obj.model_dump()) == obj

# ---------------------------------------------------------------------------
# Asgard.Freya.Visual.models.visual_models
# ---------------------------------------------------------------------------

class TestDifferenceRegionContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            DifferenceRegion()

    def test_accepts_valid_data(self):
        obj = DifferenceRegion(x=1, y=1, width=1, height=1, difference_type='addition', confidence=1.0, description="x")
        assert isinstance(obj, DifferenceRegion)

    def test_round_trip(self):
        obj = DifferenceRegion(x=1, y=1, width=1, height=1, difference_type='addition', confidence=1.0, description="x")
        assert DifferenceRegion.model_validate(obj.model_dump()) == obj

class TestElementBoxContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ElementBox()

    def test_accepts_valid_data(self):
        obj = ElementBox(x=1.0, y=1.0, width=1.0, height=1.0, selector="x")
        assert isinstance(obj, ElementBox)

    def test_round_trip(self):
        obj = ElementBox(x=1.0, y=1.0, width=1.0, height=1.0, selector="x")
        assert ElementBox.model_validate(obj.model_dump()) == obj

class TestLayoutIssueContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            LayoutIssue()

    def test_accepts_valid_data(self):
        obj = LayoutIssue(issue_type='overflow', element_selector="x", description="x", severity="x", suggested_fix="x")
        assert isinstance(obj, LayoutIssue)

    def test_round_trip(self):
        obj = LayoutIssue(issue_type='overflow', element_selector="x", description="x", severity="x", suggested_fix="x")
        assert LayoutIssue.model_validate(obj.model_dump()) == obj

class TestLayoutReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            LayoutReport()

    def test_accepts_valid_data(self):
        obj = LayoutReport(url="x", viewport_width=1, viewport_height=1)
        assert isinstance(obj, LayoutReport)

    def test_round_trip(self):
        obj = LayoutReport(url="x", viewport_width=1, viewport_height=1)
        assert LayoutReport.model_validate(obj.model_dump()) == obj

class TestRegressionTestCaseContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            RegressionTestCase()

    def test_accepts_valid_data(self):
        obj = RegressionTestCase(name="x", url="x")
        assert isinstance(obj, RegressionTestCase)

    def test_round_trip(self):
        obj = RegressionTestCase(name="x", url="x")
        assert RegressionTestCase.model_validate(obj.model_dump()) == obj

class TestRegressionTestSuiteContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            RegressionTestSuite()

    def test_accepts_valid_data(self):
        obj = RegressionTestSuite(name="x", baseline_directory="x", output_directory="x")
        assert isinstance(obj, RegressionTestSuite)

    def test_round_trip(self):
        obj = RegressionTestSuite(name="x", baseline_directory="x", output_directory="x")
        assert RegressionTestSuite.model_validate(obj.model_dump()) == obj

class TestStyleIssueContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            StyleIssue()

    def test_accepts_valid_data(self):
        obj = StyleIssue(issue_type='color_mismatch', element_selector="x", property_name="x", actual_value="x", description="x", severity="x")
        assert isinstance(obj, StyleIssue)

    def test_round_trip(self):
        obj = StyleIssue(issue_type='color_mismatch', element_selector="x", property_name="x", actual_value="x", description="x", severity="x")
        assert StyleIssue.model_validate(obj.model_dump()) == obj

class TestStyleReportContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            StyleReport()

    def test_accepts_valid_data(self):
        obj = StyleReport(url="x")
        assert isinstance(obj, StyleReport)

    def test_round_trip(self):
        obj = StyleReport(url="x")
        assert StyleReport.model_validate(obj.model_dump()) == obj



from Asgard.Freya.Accessibility.models._accessibility_enums import (
    ColorInfo,
)


class TestColorInfoContract:
    def test_requires_fields(self):
        with pytest.raises((ValidationError, TypeError)):
            ColorInfo()

    def test_accepts_valid_data(self):
        obj = ColorInfo(hex_value="#000000", rgb=(0, 0, 0), luminance=0.0)
        assert isinstance(obj, ColorInfo)

    def test_round_trip(self):
        obj = ColorInfo(hex_value="#000000", rgb=(0, 0, 0), luminance=0.0)
        assert ColorInfo.model_validate(obj.model_dump()) == obj
