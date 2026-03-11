"""
Freya Integration Models Tests

Comprehensive L0 unit tests for Integration models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from Asgard.Freya.Integration.models.integration_models import (
    TestCategory,
    TestSeverity,
    ReportFormat,
    BrowserConfig,
    DeviceConfig,
    UnifiedTestConfig,
    UnifiedTestResult,
    UnifiedTestReport,
    ReportConfig,
    BaselineEntry,
    BaselineConfig,
    CrawlConfig,
    PageStatus,
    CrawledPage,
    PageTestResult,
    SiteCrawlReport,
)


class TestEnums:
    """Tests for enum types."""

    def test_test_category_values(self):
        """Test TestCategory enum values."""
        assert TestCategory.ACCESSIBILITY.value == "accessibility"
        assert TestCategory.VISUAL.value == "visual"
        assert TestCategory.RESPONSIVE.value == "responsive"
        assert TestCategory.ALL.value == "all"

    def test_test_severity_values(self):
        """Test TestSeverity enum values."""
        assert TestSeverity.CRITICAL.value == "critical"
        assert TestSeverity.SERIOUS.value == "serious"
        assert TestSeverity.MODERATE.value == "moderate"
        assert TestSeverity.MINOR.value == "minor"

    def test_report_format_values(self):
        """Test ReportFormat enum values."""
        assert ReportFormat.JSON.value == "json"
        assert ReportFormat.HTML.value == "html"
        assert ReportFormat.JUNIT.value == "junit"
        assert ReportFormat.MARKDOWN.value == "markdown"

    def test_page_status_values(self):
        """Test PageStatus enum values."""
        assert PageStatus.PENDING.value == "pending"
        assert PageStatus.CRAWLING.value == "crawling"
        assert PageStatus.TESTED.value == "tested"
        assert PageStatus.SKIPPED.value == "skipped"
        assert PageStatus.ERROR.value == "error"


class TestBrowserConfig:
    """Tests for BrowserConfig model."""

    def test_browser_config_defaults(self):
        """Test BrowserConfig with default values."""
        config = BrowserConfig()
        assert config.browser_type == "chromium"
        assert config.headless is True
        assert config.slow_mo == 0
        assert config.timeout == 30000
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080
        assert config.device_scale_factor == 1.0
        assert config.user_agent is None
        assert config.locale == "en-US"

    def test_browser_config_custom_values(self):
        """Test BrowserConfig with custom values."""
        config = BrowserConfig(
            browser_type="firefox",
            headless=False,
            slow_mo=100,
            timeout=60000,
            viewport_width=1280,
            viewport_height=720,
            device_scale_factor=2.0,
            user_agent="Custom Agent",
            locale="en-GB"
        )
        assert config.browser_type == "firefox"
        assert config.headless is False
        assert config.slow_mo == 100
        assert config.timeout == 60000
        assert config.viewport_width == 1280
        assert config.viewport_height == 720
        assert config.device_scale_factor == 2.0
        assert config.user_agent == "Custom Agent"
        assert config.locale == "en-GB"

    def test_browser_config_serialization(self):
        """Test BrowserConfig serialization."""
        config = BrowserConfig(browser_type="webkit", headless=False)
        data = config.model_dump()
        assert data["browser_type"] == "webkit"
        assert data["headless"] is False
        assert isinstance(data, dict)


class TestDeviceConfig:
    """Tests for DeviceConfig model."""

    def test_device_config_required_fields(self):
        """Test DeviceConfig requires name, width, and height."""
        config = DeviceConfig(
            name="Test Device",
            width=375,
            height=667
        )
        assert config.name == "Test Device"
        assert config.width == 375
        assert config.height == 667
        assert config.device_scale_factor == 2.0
        assert config.is_mobile is True
        assert config.has_touch is True
        assert config.user_agent is None

    def test_device_config_all_fields(self):
        """Test DeviceConfig with all fields."""
        config = DeviceConfig(
            name="Desktop",
            width=1920,
            height=1080,
            device_scale_factor=1.0,
            is_mobile=False,
            has_touch=False,
            user_agent="Mozilla/5.0"
        )
        assert config.name == "Desktop"
        assert config.is_mobile is False
        assert config.has_touch is False
        assert config.user_agent == "Mozilla/5.0"

    def test_device_config_validation_missing_fields(self):
        """Test DeviceConfig validation with missing required fields."""
        with pytest.raises(ValidationError):
            DeviceConfig(name="Test")  # Missing width and height


class TestUnifiedTestConfig:
    """Tests for UnifiedTestConfig model."""

    def test_unified_test_config_required_fields(self):
        """Test UnifiedTestConfig with required fields."""
        config = UnifiedTestConfig(url="https://example.com")
        assert config.url == "https://example.com"
        assert config.categories == [TestCategory.ALL]
        assert config.min_severity == TestSeverity.MINOR
        assert config.devices == ["desktop", "tablet", "mobile"]
        assert config.capture_screenshots is True
        assert config.output_directory == "./freya_output"
        assert isinstance(config.browser_config, BrowserConfig)
        assert config.parallel is False

    def test_unified_test_config_custom_values(self):
        """Test UnifiedTestConfig with custom values."""
        browser_config = BrowserConfig(browser_type="firefox")
        config = UnifiedTestConfig(
            url="https://test.com",
            categories=[TestCategory.ACCESSIBILITY, TestCategory.VISUAL],
            min_severity=TestSeverity.SERIOUS,
            devices=["mobile"],
            capture_screenshots=False,
            output_directory="/tmp/output",
            browser_config=browser_config,
            parallel=True
        )
        assert config.url == "https://test.com"
        assert TestCategory.ACCESSIBILITY in config.categories
        assert TestCategory.VISUAL in config.categories
        assert config.min_severity == TestSeverity.SERIOUS
        assert config.devices == ["mobile"]
        assert config.capture_screenshots is False
        assert config.parallel is True


class TestUnifiedTestResult:
    """Tests for UnifiedTestResult model."""

    def test_unified_test_result_passed(self):
        """Test UnifiedTestResult for passing test."""
        result = UnifiedTestResult(
            category=TestCategory.ACCESSIBILITY,
            test_name="WCAG Validation",
            passed=True,
            message="All checks passed"
        )
        assert result.category == TestCategory.ACCESSIBILITY
        assert result.test_name == "WCAG Validation"
        assert result.passed is True
        assert result.message == "All checks passed"
        assert result.severity is None
        assert result.element_selector is None
        assert result.suggested_fix is None

    def test_unified_test_result_failed(self):
        """Test UnifiedTestResult for failing test."""
        result = UnifiedTestResult(
            category=TestCategory.VISUAL,
            test_name="Layout Check",
            passed=False,
            severity=TestSeverity.SERIOUS,
            message="Layout overflow detected",
            element_selector=".main-content",
            suggested_fix="Add overflow: hidden",
            wcag_reference="1.4.10",
            screenshot_path="/path/to/screenshot.png",
            details={"overflow": "200px"}
        )
        assert result.passed is False
        assert result.severity == TestSeverity.SERIOUS
        assert result.element_selector == ".main-content"
        assert result.suggested_fix == "Add overflow: hidden"
        assert result.wcag_reference == "1.4.10"
        assert result.screenshot_path == "/path/to/screenshot.png"
        assert result.details["overflow"] == "200px"

    def test_unified_test_result_serialization(self):
        """Test UnifiedTestResult serialization."""
        result = UnifiedTestResult(
            category=TestCategory.RESPONSIVE,
            test_name="Touch Targets",
            passed=False,
            severity=TestSeverity.MODERATE,
            message="Touch target too small"
        )
        data = result.model_dump()
        assert data["category"] == "responsive"
        assert data["test_name"] == "Touch Targets"
        assert data["passed"] is False


class TestUnifiedTestReport:
    """Tests for UnifiedTestReport model."""

    def test_unified_test_report_minimal(self):
        """Test UnifiedTestReport with minimal fields."""
        config = UnifiedTestConfig(url="https://example.com")
        report = UnifiedTestReport(
            url="https://example.com",
            tested_at="2025-01-01T00:00:00",
            duration_ms=5000,
            total_tests=10,
            passed=8,
            failed=2,
            config=config
        )
        assert report.url == "https://example.com"
        assert report.total_tests == 10
        assert report.passed == 8
        assert report.failed == 2
        assert report.duration_ms == 5000
        assert len(report.accessibility_results) == 0
        assert report.critical_count == 0
        assert report.overall_score == 0.0

    def test_unified_test_report_with_results(self):
        """Test UnifiedTestReport with results."""
        config = UnifiedTestConfig(url="https://example.com")
        results = [
            UnifiedTestResult(
                category=TestCategory.ACCESSIBILITY,
                test_name="Test 1",
                passed=True,
                message="Passed"
            ),
            UnifiedTestResult(
                category=TestCategory.VISUAL,
                test_name="Test 2",
                passed=False,
                severity=TestSeverity.CRITICAL,
                message="Failed"
            )
        ]

        report = UnifiedTestReport(
            url="https://example.com",
            tested_at="2025-01-01T00:00:00",
            duration_ms=5000,
            total_tests=2,
            passed=1,
            failed=1,
            accessibility_results=[results[0]],
            visual_results=[results[1]],
            critical_count=1,
            accessibility_score=100.0,
            visual_score=50.0,
            overall_score=75.0,
            config=config
        )

        assert len(report.accessibility_results) == 1
        assert len(report.visual_results) == 1
        assert report.critical_count == 1
        assert report.accessibility_score == 100.0
        assert report.overall_score == 75.0

    def test_unified_test_report_with_screenshots(self):
        """Test UnifiedTestReport with screenshots."""
        config = UnifiedTestConfig(url="https://example.com")
        screenshots = {
            "desktop": "/path/to/desktop.png",
            "mobile": "/path/to/mobile.png"
        }

        report = UnifiedTestReport(
            url="https://example.com",
            tested_at="2025-01-01T00:00:00",
            duration_ms=5000,
            total_tests=5,
            passed=5,
            failed=0,
            config=config,
            screenshots=screenshots
        )

        assert len(report.screenshots) == 2
        assert report.screenshots["desktop"] == "/path/to/desktop.png"


class TestReportConfig:
    """Tests for ReportConfig model."""

    def test_report_config_required_fields(self):
        """Test ReportConfig with required fields."""
        config = ReportConfig(output_path="/tmp/report.html")
        assert config.format == ReportFormat.HTML
        assert config.output_path == "/tmp/report.html"
        assert config.include_screenshots is True
        assert config.include_details is True
        assert config.theme == "default"
        assert config.title == "Freya Test Report"

    def test_report_config_custom_values(self):
        """Test ReportConfig with custom values."""
        config = ReportConfig(
            format=ReportFormat.JSON,
            output_path="/custom/path.json",
            include_screenshots=False,
            include_details=False,
            theme="custom",
            title="Custom Report"
        )
        assert config.format == ReportFormat.JSON
        assert config.output_path == "/custom/path.json"
        assert config.include_screenshots is False
        assert config.theme == "custom"
        assert config.title == "Custom Report"


class TestBaselineEntry:
    """Tests for BaselineEntry model."""

    def test_baseline_entry_required_fields(self):
        """Test BaselineEntry with required fields."""
        entry = BaselineEntry(
            url="https://example.com",
            name="homepage",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            screenshot_path="/path/to/screenshot.png",
            viewport_width=1920,
            viewport_height=1080,
            hash="abc123"
        )
        assert entry.url == "https://example.com"
        assert entry.name == "homepage"
        assert entry.viewport_width == 1920
        assert entry.hash == "abc123"
        assert entry.device is None

    def test_baseline_entry_with_device(self):
        """Test BaselineEntry with device."""
        entry = BaselineEntry(
            url="https://example.com",
            name="homepage",
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00",
            screenshot_path="/path/to/screenshot.png",
            viewport_width=375,
            viewport_height=667,
            device="iphone-14",
            hash="abc123",
            metadata={"format": "png", "file_size": 12345}
        )
        assert entry.device == "iphone-14"
        assert entry.metadata["format"] == "png"
        assert entry.metadata["file_size"] == 12345


class TestBaselineConfig:
    """Tests for BaselineConfig model."""

    def test_baseline_config_defaults(self):
        """Test BaselineConfig with default values."""
        config = BaselineConfig()
        assert config.storage_directory == "./freya_baselines"
        assert config.auto_update is False
        assert config.version_baselines is True
        assert config.max_versions == 10
        assert config.diff_threshold == 0.1

    def test_baseline_config_custom_values(self):
        """Test BaselineConfig with custom values."""
        config = BaselineConfig(
            storage_directory="/custom/baselines",
            auto_update=True,
            version_baselines=False,
            max_versions=5,
            diff_threshold=0.05
        )
        assert config.storage_directory == "/custom/baselines"
        assert config.auto_update is True
        assert config.version_baselines is False
        assert config.max_versions == 5
        assert config.diff_threshold == 0.05


class TestCrawlConfig:
    """Tests for CrawlConfig model."""

    def test_crawl_config_required_fields(self):
        """Test CrawlConfig with required fields."""
        config = CrawlConfig(start_url="https://example.com")
        assert config.start_url == "https://example.com"
        assert config.max_depth == 3
        assert config.max_pages == 100
        assert config.same_domain_only is True
        assert config.respect_robots_txt is False
        assert config.delay_between_requests == 0.5
        assert config.test_categories == [TestCategory.ALL]
        assert config.capture_screenshots is True
        assert isinstance(config.browser_config, BrowserConfig)

    def test_crawl_config_custom_values(self):
        """Test CrawlConfig with custom values."""
        config = CrawlConfig(
            start_url="https://test.com",
            max_depth=2,
            max_pages=50,
            include_patterns=[r".*\/blog\/.*"],
            exclude_patterns=[r".*\.pdf$"],
            same_domain_only=False,
            respect_robots_txt=True,
            delay_between_requests=1.0,
            auth_config={"username": "test", "password": "pass"},
            test_categories=[TestCategory.ACCESSIBILITY],
            capture_screenshots=False,
            output_directory="/custom/crawl"
        )
        assert config.max_depth == 2
        assert config.max_pages == 50
        assert len(config.include_patterns) == 1
        assert config.auth_config["username"] == "test"
        assert config.output_directory == "/custom/crawl"

    def test_crawl_config_exclude_patterns_default(self):
        """Test CrawlConfig default exclude patterns."""
        config = CrawlConfig(start_url="https://example.com")
        assert len(config.exclude_patterns) > 0
        assert any("jpg" in pattern for pattern in config.exclude_patterns)


class TestCrawledPage:
    """Tests for CrawledPage model."""

    def test_crawled_page_minimal(self):
        """Test CrawledPage with minimal fields."""
        page = CrawledPage(
            url="https://example.com/page1",
            depth=1
        )
        assert page.url == "https://example.com/page1"
        assert page.depth == 1
        assert page.title is None
        assert page.status == PageStatus.PENDING
        assert page.parent_url is None
        assert len(page.links_found) == 0

    def test_crawled_page_full(self):
        """Test CrawledPage with all fields."""
        page = CrawledPage(
            url="https://example.com/page1",
            title="Page 1",
            depth=2,
            parent_url="https://example.com",
            status=PageStatus.TESTED,
            discovered_at="2025-01-01T00:00:00",
            links_found=["https://example.com/page2", "https://example.com/page3"],
            error_message=None
        )
        assert page.title == "Page 1"
        assert page.depth == 2
        assert page.status == PageStatus.TESTED
        assert len(page.links_found) == 2

    def test_crawled_page_with_error(self):
        """Test CrawledPage with error."""
        page = CrawledPage(
            url="https://example.com/error",
            depth=1,
            status=PageStatus.ERROR,
            error_message="404 Not Found"
        )
        assert page.status == PageStatus.ERROR
        assert page.error_message == "404 Not Found"


class TestPageTestResult:
    """Tests for PageTestResult model."""

    def test_page_test_result_passed(self):
        """Test PageTestResult for passing page."""
        result = PageTestResult(
            url="https://example.com",
            title="Home Page",
            tested_at="2025-01-01T00:00:00",
            duration_ms=3000,
            accessibility_score=100.0,
            visual_score=95.0,
            responsive_score=98.0,
            overall_score=97.7,
            passed=True
        )
        assert result.url == "https://example.com"
        assert result.accessibility_score == 100.0
        assert result.passed is True
        assert result.critical_issues == 0

    def test_page_test_result_with_issues(self):
        """Test PageTestResult with issues."""
        issues = [
            {"type": "contrast", "severity": "serious"},
            {"type": "layout", "severity": "moderate"}
        ]

        result = PageTestResult(
            url="https://example.com",
            tested_at="2025-01-01T00:00:00",
            duration_ms=3000,
            accessibility_score=60.0,
            overall_score=70.0,
            critical_issues=1,
            serious_issues=2,
            moderate_issues=3,
            minor_issues=1,
            issues=issues,
            passed=False,
            screenshot_path="/path/to/screenshot.png"
        )
        assert result.passed is False
        assert result.critical_issues == 1
        assert result.serious_issues == 2
        assert len(result.issues) == 2
        assert result.screenshot_path == "/path/to/screenshot.png"


class TestSiteCrawlReport:
    """Tests for SiteCrawlReport model."""

    def test_site_crawl_report_minimal(self):
        """Test SiteCrawlReport with minimal fields."""
        config = CrawlConfig(start_url="https://example.com")
        report = SiteCrawlReport(
            start_url="https://example.com",
            crawl_started="2025-01-01T00:00:00",
            crawl_completed="2025-01-01T00:05:00",
            total_duration_ms=300000,
            pages_discovered=50,
            pages_tested=45,
            pages_skipped=3,
            pages_errored=2,
            config=config
        )
        assert report.start_url == "https://example.com"
        assert report.pages_discovered == 50
        assert report.pages_tested == 45
        assert report.total_duration_ms == 300000
        assert len(report.page_results) == 0

    def test_site_crawl_report_with_results(self):
        """Test SiteCrawlReport with page results."""
        config = CrawlConfig(start_url="https://example.com")
        page_results = [
            PageTestResult(
                url="https://example.com/page1",
                tested_at="2025-01-01T00:00:00",
                duration_ms=1000,
                overall_score=95.0,
                passed=True
            ),
            PageTestResult(
                url="https://example.com/page2",
                tested_at="2025-01-01T00:01:00",
                duration_ms=1200,
                overall_score=70.0,
                critical_issues=1,
                passed=False
            )
        ]

        report = SiteCrawlReport(
            start_url="https://example.com",
            crawl_started="2025-01-01T00:00:00",
            crawl_completed="2025-01-01T00:05:00",
            total_duration_ms=300000,
            pages_discovered=2,
            pages_tested=2,
            pages_skipped=0,
            pages_errored=0,
            average_overall_score=82.5,
            total_critical=1,
            page_results=page_results,
            worst_pages=["https://example.com/page2"],
            common_issues=[{"issue": "contrast", "count": 5}],
            config=config
        )

        assert len(report.page_results) == 2
        assert report.average_overall_score == 82.5
        assert report.total_critical == 1
        assert len(report.worst_pages) == 1
        assert len(report.common_issues) == 1
