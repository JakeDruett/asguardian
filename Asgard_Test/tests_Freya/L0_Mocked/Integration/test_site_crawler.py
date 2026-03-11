"""
L0 Unit Tests for Freya Site Crawler

Comprehensive tests for site crawling and testing functionality with mocked Playwright dependencies.
Tests crawl discovery, page testing, authentication, and report generation.
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from urllib.parse import urlparse

from Freya.Integration.services.site_crawler import SiteCrawler
from Freya.Integration.models.integration_models import (
    CrawlConfig,
    BrowserConfig,
    CrawledPage,
    PageStatus,
    PageTestResult,
    SiteCrawlReport,
    TestCategory,
)


class TestSiteCrawlerInit:
    """Test SiteCrawler initialization."""

    def test_init_with_basic_config(self):
        """Test initializing crawler with basic configuration."""
        config = CrawlConfig(
            start_url="https://example.com",
            max_depth=3,
            max_pages=100,
            output_directory="./test_output"
        )

        crawler = SiteCrawler(config)

        assert crawler.config == config
        assert crawler.base_domain == "example.com"
        assert len(crawler.discovered_pages) == 0
        assert len(crawler.tested_pages) == 0

    def test_init_creates_output_directory(self, tmp_path):
        """Test initialization creates output directories."""
        output_dir = tmp_path / "crawl_output"
        config = CrawlConfig(
            start_url="https://example.com",
            output_directory=str(output_dir)
        )

        crawler = SiteCrawler(config)

        assert output_dir.exists()
        assert (output_dir / "screenshots").exists()

    def test_init_compiles_regex_patterns(self):
        """Test initialization compiles include/exclude patterns."""
        config = CrawlConfig(
            start_url="https://example.com",
            include_patterns=[r".*\/blog\/.*"],
            exclude_patterns=[r".*\.pdf$", r".*logout.*"],
            output_directory="./test_output"
        )

        crawler = SiteCrawler(config)

        assert len(crawler._compiled_include) == 1
        assert len(crawler._compiled_exclude) == 2


class TestProgressCallback:
    """Test progress callback functionality."""

    def test_set_progress_callback(self):
        """Test setting progress callback."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        callback = Mock()
        crawler.set_progress_callback(callback)

        assert crawler._progress_callback == callback

    def test_report_progress_with_callback(self):
        """Test reporting progress with callback set."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        callback = Mock()
        crawler.set_progress_callback(callback)

        crawler._report_progress("Test message", 5, 10)

        callback.assert_called_once_with("Test message", 5, 10)

    def test_report_progress_without_callback(self):
        """Test reporting progress without callback set."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        crawler._report_progress("Test message")


class TestURLNormalization:
    """Test URL normalization and validation."""

    def test_normalize_url_absolute(self):
        """Test normalizing absolute URL."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        normalized = crawler._normalize_url(
            "https://example.com/page",
            "https://example.com"
        )

        assert normalized == "https://example.com/page"

    def test_normalize_url_relative(self):
        """Test normalizing relative URL."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        normalized = crawler._normalize_url(
            "/page",
            "https://example.com"
        )

        assert normalized == "https://example.com/page"

    def test_normalize_url_removes_trailing_slash(self):
        """Test normalization removes trailing slash."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        normalized = crawler._normalize_url(
            "https://example.com/page/",
            "https://example.com"
        )

        assert normalized == "https://example.com/page"

    def test_normalize_url_removes_fragment(self):
        """Test normalization removes URL fragment."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        normalized = crawler._normalize_url(
            "https://example.com/page#section",
            "https://example.com"
        )

        assert normalized == "https://example.com/page"

    def test_normalize_url_javascript_link_returns_none(self):
        """Test javascript: links are filtered out."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        normalized = crawler._normalize_url(
            "javascript:void(0)",
            "https://example.com"
        )

        assert normalized is None

    def test_normalize_url_mailto_link_returns_none(self):
        """Test mailto: links are filtered out."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        normalized = crawler._normalize_url(
            "mailto:test@example.com",
            "https://example.com"
        )

        assert normalized is None

    def test_normalize_url_empty_returns_none(self):
        """Test empty URL returns None."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        normalized = crawler._normalize_url("", "https://example.com")

        assert normalized is None


class TestShouldCrawl:
    """Test URL crawl decision logic."""

    def test_should_crawl_same_domain(self):
        """Test crawling URL on same domain."""
        config = CrawlConfig(
            start_url="https://example.com",
            same_domain_only=True
        )
        crawler = SiteCrawler(config)

        should_crawl = crawler._should_crawl("https://example.com/page")

        assert should_crawl is True

    def test_should_not_crawl_different_domain(self):
        """Test not crawling URL on different domain."""
        config = CrawlConfig(
            start_url="https://example.com",
            same_domain_only=True
        )
        crawler = SiteCrawler(config)

        should_crawl = crawler._should_crawl("https://other.com/page")

        assert should_crawl is False

    def test_should_not_crawl_excluded_pattern(self):
        """Test excluded pattern prevents crawling."""
        config = CrawlConfig(
            start_url="https://example.com",
            exclude_patterns=[r".*\.pdf$"]
        )
        crawler = SiteCrawler(config)

        should_crawl = crawler._should_crawl("https://example.com/document.pdf")

        assert should_crawl is False

    def test_should_crawl_included_pattern(self):
        """Test included pattern allows crawling."""
        config = CrawlConfig(
            start_url="https://example.com",
            include_patterns=[r".*\/blog\/.*"]
        )
        crawler = SiteCrawler(config)

        should_crawl = crawler._should_crawl("https://example.com/blog/post")

        assert should_crawl is True

    def test_should_not_crawl_without_included_pattern(self):
        """Test URL without included pattern is rejected."""
        config = CrawlConfig(
            start_url="https://example.com",
            include_patterns=[r".*\/blog\/.*"]
        )
        crawler = SiteCrawler(config)

        should_crawl = crawler._should_crawl("https://example.com/about")

        assert should_crawl is False


class TestAddPage:
    """Test page discovery tracking."""

    def test_add_page_creates_entry(self):
        """Test adding page creates discovery entry."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        crawler._add_page("https://example.com/page", depth=1, parent_url="https://example.com")

        assert "https://example.com/page" in crawler.discovered_pages
        page = crawler.discovered_pages["https://example.com/page"]
        assert page.url == "https://example.com/page"
        assert page.depth == 1
        assert page.parent_url == "https://example.com"
        assert page.status == PageStatus.PENDING

    def test_add_page_does_not_duplicate(self):
        """Test adding same page twice does not create duplicate."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        crawler._add_page("https://example.com/page", depth=1, parent_url="https://example.com")
        crawler._add_page("https://example.com/page", depth=2, parent_url="https://example.com/other")

        assert len(crawler.discovered_pages) == 1
        page = crawler.discovered_pages["https://example.com/page"]
        assert page.depth == 1


class TestExtractLinks:
    """Test link extraction from pages."""

    @pytest.mark.asyncio
    async def test_extract_links_from_page(self):
        """Test extracting links from page."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[
            "https://example.com/page1",
            "https://example.com/page2",
            "/relative/page"
        ])

        links = await crawler._extract_links(mock_page, "https://example.com")

        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links
        assert "https://example.com/relative/page" in links

    @pytest.mark.asyncio
    async def test_extract_links_removes_duplicates(self):
        """Test link extraction removes duplicates."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[
            "https://example.com/page",
            "https://example.com/page",
            "https://example.com/page/"
        ])

        links = await crawler._extract_links(mock_page, "https://example.com")

        assert len(links) == 1
        assert links[0] == "https://example.com/page"


class TestAuthentication:
    """Test authentication functionality."""

    @pytest.mark.asyncio
    async def test_authenticate_with_credentials(self):
        """Test authentication with username and password."""
        config = CrawlConfig(
            start_url="https://example.com",
            auth_config={
                "login_url": "https://example.com/login",
                "username": "testuser",
                "password": "testpass",
                "username_selector": 'input[name="username"]',
                "password_selector": 'input[name="password"]',
                "submit_selector": 'button[type="submit"]'
            }
        )
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.fill = AsyncMock()
        mock_page.click = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        mock_page.close = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        await crawler._authenticate(mock_context)

        mock_page.goto.assert_called_once()
        assert mock_page.fill.call_count == 2
        mock_page.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_authenticate_without_config(self):
        """Test authentication skipped without config."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        mock_context = AsyncMock()

        await crawler._authenticate(mock_context)

        mock_context.new_page.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_handles_exception(self):
        """Test authentication handles exceptions gracefully."""
        config = CrawlConfig(
            start_url="https://example.com",
            auth_config={
                "login_url": "https://example.com/login",
                "username": "testuser",
                "password": "testpass"
            }
        )
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Navigation failed"))
        mock_page.close = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        await crawler._authenticate(mock_context)

        mock_page.close.assert_called_once()


class TestAccessibilityChecks:
    """Test accessibility checking functionality."""

    @pytest.mark.asyncio
    async def test_run_accessibility_checks_missing_alt(self):
        """Test detecting images without alt text."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[
            {
                "type": "missing-alt",
                "severity": "serious",
                "element": "<img src='logo.png'>",
                "message": "Image missing alt text",
                "wcag": "1.1.1"
            }
        ])

        issues = await crawler._run_accessibility_checks(mock_page)

        assert len(issues) == 1
        assert issues[0]["category"] == "accessibility"
        assert issues[0]["type"] == "missing-alt"
        assert issues[0]["severity"] == "serious"

    @pytest.mark.asyncio
    async def test_run_accessibility_checks_missing_label(self):
        """Test detecting form inputs without labels."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[
            {
                "type": "missing-label",
                "severity": "serious",
                "element": "<input type='text'>",
                "message": "Form input missing label",
                "wcag": "1.3.1"
            }
        ])

        issues = await crawler._run_accessibility_checks(mock_page)

        assert len(issues) == 1
        assert issues[0]["type"] == "missing-label"

    @pytest.mark.asyncio
    async def test_run_accessibility_checks_no_issues(self):
        """Test page with no accessibility issues."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[])

        issues = await crawler._run_accessibility_checks(mock_page)

        assert len(issues) == 0


class TestVisualChecks:
    """Test visual checking functionality."""

    @pytest.mark.asyncio
    async def test_run_visual_checks_broken_image(self):
        """Test detecting broken images."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[
            {
                "type": "broken-image",
                "severity": "moderate",
                "element": "logo.png",
                "message": "Image failed to load"
            }
        ])

        issues = await crawler._run_visual_checks(mock_page)

        assert len(issues) == 1
        assert issues[0]["category"] == "visual"
        assert issues[0]["type"] == "broken-image"

    @pytest.mark.asyncio
    async def test_run_visual_checks_horizontal_overflow(self):
        """Test detecting horizontal overflow."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[
            {
                "type": "horizontal-overflow",
                "severity": "moderate",
                "element": "body",
                "message": "Page has horizontal scroll"
            }
        ])

        issues = await crawler._run_visual_checks(mock_page)

        assert len(issues) == 1
        assert issues[0]["type"] == "horizontal-overflow"


class TestResponsiveChecks:
    """Test responsive checking functionality."""

    @pytest.mark.asyncio
    async def test_run_responsive_checks_missing_viewport(self):
        """Test detecting missing viewport meta tag."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[
            {
                "type": "missing-viewport",
                "severity": "serious",
                "element": "head",
                "message": "Missing viewport meta tag"
            }
        ])

        issues = await crawler._run_responsive_checks(mock_page)

        assert len(issues) == 1
        assert issues[0]["category"] == "responsive"
        assert issues[0]["type"] == "missing-viewport"

    @pytest.mark.asyncio
    async def test_run_responsive_checks_small_touch_target(self):
        """Test detecting small touch targets."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[
            {
                "type": "small-touch-target",
                "severity": "moderate",
                "element": "<button>Click</button>",
                "message": "Touch target 30x30px is below 44x44px minimum"
            }
        ])

        issues = await crawler._run_responsive_checks(mock_page)

        assert len(issues) == 1
        assert issues[0]["type"] == "small-touch-target"


class TestTestPage:
    """Test individual page testing."""

    @pytest.mark.asyncio
    async def test_test_page_success(self):
        """Test successfully testing a page."""
        config = CrawlConfig(
            start_url="https://example.com",
            test_categories=[TestCategory.ACCESSIBILITY]
        )
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.title = AsyncMock(return_value="Test Page")
        mock_page.evaluate = AsyncMock(return_value=[])
        mock_page.close = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        page_info = CrawledPage(
            url="https://example.com/page",
            depth=1,
            parent_url="https://example.com",
            status=PageStatus.TESTED
        )

        result = await crawler._test_page(mock_context, page_info)

        assert result.url == "https://example.com/page"
        assert result.title == "Test Page"
        assert result.passed is True
        assert result.overall_score == 100.0

    @pytest.mark.asyncio
    async def test_test_page_with_issues(self):
        """Test testing page with issues found."""
        config = CrawlConfig(
            start_url="https://example.com",
            test_categories=[TestCategory.ACCESSIBILITY]
        )
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.title = AsyncMock(return_value="Test Page")
        mock_page.evaluate = AsyncMock(return_value=[
            {
                "type": "missing-alt",
                "severity": "critical",
                "element": "<img>",
                "message": "Missing alt text",
                "wcag": "1.1.1"
            }
        ])
        mock_page.close = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        page_info = CrawledPage(
            url="https://example.com/page",
            depth=1,
            status=PageStatus.TESTED
        )

        result = await crawler._test_page(mock_context, page_info)

        assert result.passed is False
        assert result.critical_issues == 1
        assert result.accessibility_score < 100

    @pytest.mark.asyncio
    async def test_test_page_with_screenshot(self, tmp_path):
        """Test testing page with screenshot capture."""
        config = CrawlConfig(
            start_url="https://example.com",
            capture_screenshots=True,
            output_directory=str(tmp_path)
        )
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.title = AsyncMock(return_value="Test Page")
        mock_page.screenshot = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[])
        mock_page.close = AsyncMock()

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        page_info = CrawledPage(
            url="https://example.com/page",
            depth=1,
            status=PageStatus.TESTED
        )

        result = await crawler._test_page(mock_context, page_info)

        assert result.screenshot_path is not None
        mock_page.screenshot.assert_called_once()

    @pytest.mark.asyncio
    async def test_test_page_handles_exception(self):
        """Test page testing handles exceptions."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(side_effect=Exception("Navigation failed"))

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        page_info = CrawledPage(
            url="https://example.com/page",
            depth=1,
            status=PageStatus.TESTED
        )

        result = await crawler._test_page(mock_context, page_info)

        assert result.passed is False
        assert result.error == "Navigation failed"


class TestURLToFilename:
    """Test URL to filename conversion."""

    def test_url_to_filename_removes_protocol(self):
        """Test filename removes protocol."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        filename = crawler._url_to_filename("https://example.com/page")

        assert not filename.startswith("https://")
        assert not filename.startswith("http://")

    def test_url_to_filename_replaces_slashes(self):
        """Test filename replaces slashes with underscores."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        filename = crawler._url_to_filename("https://example.com/path/to/page")

        assert "/" not in filename
        assert "_" in filename

    def test_url_to_filename_replaces_special_chars(self):
        """Test filename replaces special characters."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        filename = crawler._url_to_filename("https://example.com/page?id=1&ref=2#section")

        assert "?" not in filename
        assert "&" not in filename
        assert "=" not in filename
        assert "#" not in filename

    def test_url_to_filename_truncates_long_urls(self):
        """Test filename truncates very long URLs."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        long_url = "https://example.com/" + "x" * 200
        filename = crawler._url_to_filename(long_url)

        assert len(filename) <= 100


class TestGenerateReport:
    """Test report generation."""

    def test_generate_report_with_results(self):
        """Test generating report with test results."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        crawler.discovered_pages = {
            "https://example.com": CrawledPage(
                url="https://example.com",
                depth=0,
                status=PageStatus.TESTED
            ),
            "https://example.com/page": CrawledPage(
                url="https://example.com/page",
                depth=1,
                status=PageStatus.TESTED
            )
        }

        crawler.tested_pages = {
            "https://example.com": PageTestResult(
                url="https://example.com",
                title="Home",
                tested_at=datetime.now().isoformat(),
                duration_ms=100,
                accessibility_score=90.0,
                visual_score=95.0,
                responsive_score=85.0,
                overall_score=90.0,
                critical_issues=0,
                serious_issues=1,
                moderate_issues=2,
                minor_issues=3,
                issues=[],
                passed=True
            ),
            "https://example.com/page": PageTestResult(
                url="https://example.com/page",
                title="Page",
                tested_at=datetime.now().isoformat(),
                duration_ms=150,
                accessibility_score=80.0,
                visual_score=90.0,
                responsive_score=75.0,
                overall_score=81.67,
                critical_issues=1,
                serious_issues=0,
                moderate_issues=1,
                minor_issues=1,
                issues=[],
                passed=False
            )
        }

        report = crawler._generate_report(
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            1000
        )

        assert report.pages_discovered == 2
        assert report.pages_tested == 2
        assert report.total_critical == 1
        assert report.total_serious == 1
        assert report.average_overall_score > 0

    def test_generate_report_empty_results(self):
        """Test generating report with no results."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        report = crawler._generate_report(
            datetime.now().isoformat(),
            datetime.now().isoformat(),
            500
        )

        assert report.pages_discovered == 0
        assert report.pages_tested == 0
        assert report.average_overall_score == 0.0


class TestHTMLReportGeneration:
    """Test HTML report generation."""

    def test_generate_html_report(self):
        """Test generating HTML report."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        report = SiteCrawlReport(
            start_url="https://example.com",
            crawl_started=datetime.now().isoformat(),
            crawl_completed=datetime.now().isoformat(),
            total_duration_ms=1000,
            pages_discovered=5,
            pages_tested=5,
            pages_skipped=0,
            pages_errored=0,
            average_accessibility_score=85.0,
            average_visual_score=90.0,
            average_responsive_score=80.0,
            average_overall_score=85.0,
            total_critical=1,
            total_serious=2,
            total_moderate=3,
            total_minor=4,
            page_results=[],
            worst_pages=[],
            common_issues=[],
            config=config
        )

        html = crawler._generate_html_report(report)

        assert "<!DOCTYPE html>" in html
        assert "Freya Site Crawl Report" in html
        assert "https://example.com" in html
        assert "85" in html

    def test_generate_html_report_with_page_results(self):
        """Test HTML report includes page results."""
        config = CrawlConfig(start_url="https://example.com")
        crawler = SiteCrawler(config)

        page_result = PageTestResult(
            url="https://example.com/page",
            title="Test Page",
            tested_at=datetime.now().isoformat(),
            duration_ms=100,
            accessibility_score=90.0,
            visual_score=95.0,
            responsive_score=85.0,
            overall_score=90.0,
            critical_issues=0,
            serious_issues=0,
            moderate_issues=0,
            minor_issues=0,
            issues=[],
            passed=True
        )

        report = SiteCrawlReport(
            start_url="https://example.com",
            crawl_started=datetime.now().isoformat(),
            crawl_completed=datetime.now().isoformat(),
            total_duration_ms=1000,
            pages_discovered=1,
            pages_tested=1,
            pages_skipped=0,
            pages_errored=0,
            average_accessibility_score=90.0,
            average_visual_score=95.0,
            average_responsive_score=85.0,
            average_overall_score=90.0,
            total_critical=0,
            total_serious=0,
            total_moderate=0,
            total_minor=0,
            page_results=[page_result],
            worst_pages=[],
            common_issues=[],
            config=config
        )

        html = crawler._generate_html_report(report)

        assert "https://example.com/page" in html
        assert "PASS" in html


class TestSaveReport:
    """Test report saving functionality."""

    @pytest.mark.asyncio
    async def test_save_report_creates_files(self, tmp_path):
        """Test report saving creates JSON and HTML files."""
        config = CrawlConfig(
            start_url="https://example.com",
            output_directory=str(tmp_path)
        )
        crawler = SiteCrawler(config)

        report = SiteCrawlReport(
            start_url="https://example.com",
            crawl_started=datetime.now().isoformat(),
            crawl_completed=datetime.now().isoformat(),
            total_duration_ms=1000,
            pages_discovered=0,
            pages_tested=0,
            pages_skipped=0,
            pages_errored=0,
            average_accessibility_score=0.0,
            average_visual_score=0.0,
            average_responsive_score=0.0,
            average_overall_score=0.0,
            total_critical=0,
            total_serious=0,
            total_moderate=0,
            total_minor=0,
            page_results=[],
            worst_pages=[],
            common_issues=[],
            config=config
        )

        await crawler._save_report(report)

        json_path = tmp_path / "crawl_report.json"
        html_path = tmp_path / "crawl_report.html"

        assert json_path.exists()
        assert html_path.exists()

        json_content = json_path.read_text()
        assert "https://example.com" in json_content

        html_content = html_path.read_text()
        assert "<!DOCTYPE html>" in html_content
