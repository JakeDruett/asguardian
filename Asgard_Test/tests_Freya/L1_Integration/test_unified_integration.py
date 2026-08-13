"""
L1 Integration Tests for Freya Unified Testing

Comprehensive integration tests for unified site testing that combines accessibility,
visual, and responsive testing into a single comprehensive test suite with HTML
report generation and baseline management.

All tests use file:// URLs for local HTML fixtures, making them CI-friendly.
"""

import pytest
from pathlib import Path

from Asgard.Freya.Integration.services.unified_tester import UnifiedTester
from Asgard.Freya.Integration.services.html_reporter import HTMLReporter
from Asgard.Freya.Integration.services.baseline_manager import BaselineManager
from Asgard.Freya.Integration.services.site_crawler import SiteCrawler
from Asgard.Freya.Integration.models.integration_models import (
    BaselineConfig,
    CrawlConfig,
    UnifiedTestConfig,
    TestCategory,
    TestSeverity,
)

from Asgard_Test.tests_Freya.L1_Integration.conftest import file_url


class TestUnifiedIntegrationUnifiedTester:
    """Integration tests for Unified Tester with real HTML pages."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_unified_tester_all_categories(self, sample_accessible_page, output_dir):
        """Test unified tester runs all test categories."""
        config = UnifiedTestConfig(
            url="",
            output_directory=str(output_dir / "unified"),
            categories=[TestCategory.ALL],
            min_severity=TestSeverity.MINOR,
            capture_screenshots=False,
        )
        tester = UnifiedTester(config)

        url = file_url(sample_accessible_page)
        report = await tester.test(url)

        assert report is not None
        assert report.url == url
        assert report.total_tests > 0
        assert report.duration_ms > 0

        assert len(report.accessibility_results) > 0
        assert len(report.visual_results) > 0
        assert len(report.responsive_results) > 0

        assert 0.0 <= report.overall_score <= 100.0
        assert 0.0 <= report.accessibility_score <= 100.0
        assert 0.0 <= report.visual_score <= 100.0
        assert 0.0 <= report.responsive_score <= 100.0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_unified_tester_accessibility_only(self, sample_accessible_page, output_dir):
        """Test unified tester with accessibility category only."""
        config = UnifiedTestConfig(
            url="",
            output_directory=str(output_dir / "unified"),
            categories=[TestCategory.ACCESSIBILITY],
            capture_screenshots=False,
        )
        tester = UnifiedTester(config)

        url = file_url(sample_accessible_page)
        report = await tester.test(url)

        assert report is not None
        assert len(report.accessibility_results) > 0
        assert len(report.visual_results) == 0
        assert len(report.responsive_results) == 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_unified_tester_visual_only(self, sample_visual_page, output_dir):
        """Test unified tester with visual category only."""
        config = UnifiedTestConfig(
            url="",
            output_directory=str(output_dir / "unified"),
            categories=[TestCategory.VISUAL],
            capture_screenshots=False,
        )
        tester = UnifiedTester(config)

        url = file_url(sample_visual_page)
        report = await tester.test(url)

        assert report is not None
        assert len(report.accessibility_results) == 0
        assert len(report.visual_results) > 0
        assert len(report.responsive_results) == 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_unified_tester_responsive_only(self, sample_responsive_page, output_dir):
        """Test unified tester with responsive category only."""
        config = UnifiedTestConfig(
            url="",
            output_directory=str(output_dir / "unified"),
            categories=[TestCategory.RESPONSIVE],
            capture_screenshots=False,
        )
        tester = UnifiedTester(config)

        url = file_url(sample_responsive_page)
        report = await tester.test(url)

        assert report is not None
        assert len(report.accessibility_results) == 0
        assert len(report.visual_results) == 0
        assert len(report.responsive_results) > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_unified_tester_severity_filtering(self, sample_inaccessible_page, output_dir):
        """Test unified tester filters results by severity."""
        config_critical = UnifiedTestConfig(
            url="",
            output_directory=str(output_dir / "unified"),
            categories=[TestCategory.ACCESSIBILITY],
            min_severity=TestSeverity.CRITICAL,
            capture_screenshots=False,
        )
        tester_critical = UnifiedTester(config_critical)

        url = file_url(sample_inaccessible_page)
        report_critical = await tester_critical.test(url, min_severity=TestSeverity.CRITICAL)

        config_all = UnifiedTestConfig(
            url="",
            output_directory=str(output_dir / "unified"),
            categories=[TestCategory.ACCESSIBILITY],
            min_severity=TestSeverity.MINOR,
            capture_screenshots=False,
        )
        tester_all = UnifiedTester(config_all)
        report_all = await tester_all.test(url, min_severity=TestSeverity.MINOR)

        assert report_critical.total_tests <= report_all.total_tests

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_unified_tester_with_screenshots(self, sample_visual_page, output_dir):
        """Test unified tester captures screenshots when enabled."""
        config = UnifiedTestConfig(
            url="",
            output_directory=str(output_dir / "unified_screenshots"),
            categories=[TestCategory.RESPONSIVE],
            capture_screenshots=True,
        )
        tester = UnifiedTester(config)

        url = file_url(sample_visual_page)
        report = await tester.test(url)

        assert report is not None
        if len(report.screenshots) > 0:
            for screenshot_path in report.screenshots.values():
                assert Path(screenshot_path).exists()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_unified_tester_report_structure(self, sample_accessible_page, output_dir):
        """Test unified tester report has correct structure."""
        config = UnifiedTestConfig(
            url="",
            output_directory=str(output_dir / "unified"),
            capture_screenshots=False,
        )
        tester = UnifiedTester(config)

        url = file_url(sample_accessible_page)
        report = await tester.test(url)

        assert report.url is not None
        assert report.tested_at is not None
        assert report.duration_ms >= 0
        assert report.total_tests >= 0
        assert report.passed >= 0
        assert report.failed >= 0
        assert report.passed + report.failed <= report.total_tests

        assert report.critical_count >= 0
        assert report.serious_count >= 0
        assert report.moderate_count >= 0
        assert report.minor_count >= 0

        assert isinstance(report.accessibility_results, list)
        assert isinstance(report.visual_results, list)
        assert isinstance(report.responsive_results, list)
        assert isinstance(report.screenshots, dict)
        assert hasattr(report, 'config')


class TestUnifiedIntegrationHTMLReporter:
    """Integration tests for HTML Reporter with real test results."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_html_reporter_generates_report(self, sample_accessible_page, output_dir):
        """Test HTML reporter generates valid HTML report."""
        config = UnifiedTestConfig(
            url="",
            output_directory=str(output_dir / "unified"),
            capture_screenshots=False,
        )
        tester = UnifiedTester(config)

        url = file_url(sample_accessible_page)
        test_report = await tester.test(url)

        reporter = HTMLReporter()
        html_path = reporter.generate(
            test_report, str(output_dir / "reports" / "unified_report.html")
        )

        assert html_path is not None
        assert Path(html_path).exists()
        assert Path(html_path).suffix == ".html"

        html_content = Path(html_path).read_text()
        assert "<!DOCTYPE html>" in html_content or "<html" in html_content
        assert test_report.url in html_content

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_html_reporter_includes_test_results(self, sample_inaccessible_page, output_dir):
        """Test HTML reporter includes test results in report."""
        config = UnifiedTestConfig(
            url="",
            output_directory=str(output_dir / "unified"),
            categories=[TestCategory.ACCESSIBILITY],
            capture_screenshots=False,
        )
        tester = UnifiedTester(config)

        url = file_url(sample_inaccessible_page)
        test_report = await tester.test(url)

        reporter = HTMLReporter()
        html_path = reporter.generate(
            test_report, str(output_dir / "reports" / "results_report.html")
        )

        html_content = Path(html_path).read_text()
        assert str(test_report.total_tests) in html_content
        assert str(test_report.overall_score) in html_content or "score" in html_content.lower()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_html_reporter_custom_title(self, sample_accessible_page, output_dir):
        """Test HTML reporter with custom report title."""
        config = UnifiedTestConfig(
            url="",
            output_directory=str(output_dir / "unified"),
            capture_screenshots=False,
        )
        tester = UnifiedTester(config)

        url = file_url(sample_accessible_page)
        test_report = await tester.test(url)

        reporter = HTMLReporter()
        html_path = reporter.generate(
            test_report,
            str(output_dir / "reports" / "custom_report.html"),
            title="Custom Test Report",
        )

        assert Path(html_path).exists()

        html_content = Path(html_path).read_text()
        assert "Custom Test Report" in html_content or "Test Report" in html_content


class TestUnifiedIntegrationBaselineManager:
    """Integration tests for Baseline Manager with real screenshots."""

    def _manager(self, baseline_fixtures_dir) -> BaselineManager:
        return BaselineManager(BaselineConfig(
            storage_directory=str(baseline_fixtures_dir / "managed"),
        ))

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_baseline_manager_save_baseline(self, sample_visual_page, baseline_fixtures_dir):
        """Test baseline manager creates baselines."""
        manager = self._manager(baseline_fixtures_dir)

        url = file_url(sample_visual_page)
        entry = await manager.create_baseline(url, "baseline_test")

        assert entry is not None
        assert Path(entry.screenshot_path).exists()
        assert entry.url == url
        assert entry.hash

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_baseline_manager_load_baseline(self, sample_visual_page, baseline_fixtures_dir):
        """Test baseline manager retrieves stored baselines."""
        manager = self._manager(baseline_fixtures_dir)

        url = file_url(sample_visual_page)
        created = await manager.create_baseline(url, "load_test")

        loaded = manager.get_baseline(url, "load_test")

        assert loaded is not None
        assert Path(loaded.screenshot_path).exists()
        assert loaded.screenshot_path == created.screenshot_path

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_baseline_manager_update_baseline(self, sample_visual_page, baseline_fixtures_dir):
        """Test baseline manager updates existing baselines."""
        manager = self._manager(baseline_fixtures_dir)

        url = file_url(sample_visual_page)
        entry1 = await manager.create_baseline(url, "update_test")
        entry2 = await manager.update_baseline(url, "update_test")

        assert entry1 is not None
        assert entry2 is not None
        assert Path(entry2.screenshot_path).exists()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_baseline_manager_list_baselines(self, sample_visual_page, baseline_fixtures_dir):
        """Test baseline manager lists all baselines."""
        manager = self._manager(baseline_fixtures_dir)

        url = file_url(sample_visual_page)
        for i in range(3):
            await manager.create_baseline(url, f"baseline_{i}")

        baselines = manager.list_baselines()

        assert baselines is not None
        assert len(baselines) >= 3

        names = [b.name for b in baselines]
        for i in range(3):
            assert f"baseline_{i}" in names

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_baseline_manager_delete_baseline(self, sample_visual_page, baseline_fixtures_dir):
        """Test baseline manager deletes baselines."""
        manager = self._manager(baseline_fixtures_dir)

        url = file_url(sample_visual_page)
        entry = await manager.create_baseline(url, "delete_test")

        assert Path(entry.screenshot_path).exists()

        success = manager.delete_baseline(url, "delete_test")

        assert success is True
        assert manager.get_baseline(url, "delete_test") is None


class TestUnifiedIntegrationSiteCrawler:
    """Integration tests for Site Crawler with real HTML pages."""

    @staticmethod
    def _crawl_config(start_url: str, output_dir: Path, **kwargs) -> CrawlConfig:
        return CrawlConfig(
            start_url=start_url,
            output_directory=str(output_dir),
            discover_items=False,
            delay_between_requests=0.0,
            **kwargs,
        )

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_site_crawler_single_page(self, sample_accessible_page, output_dir):
        """Test site crawler on single page."""
        config = self._crawl_config(
            file_url(sample_accessible_page),
            output_dir / "crawl_single",
            max_depth=0,
            max_pages=1,
        )
        crawler = SiteCrawler(config)

        report = await crawler.crawl_and_test()

        assert report is not None
        assert report.pages_discovered >= 1
        assert report.pages_tested >= 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_site_crawler_with_links(self, html_fixtures_dir, output_dir):
        """Test site crawler follows links."""
        page1_html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Page 1</title></head>
<body>
    <h1>Page 1</h1>
    <a href="page2.html">Go to Page 2</a>
</body>
</html>"""

        page2_html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Page 2</title></head>
<body>
    <h1>Page 2</h1>
    <a href="page1.html">Back to Page 1</a>
</body>
</html>"""

        page1 = html_fixtures_dir / "page1.html"
        page2 = html_fixtures_dir / "page2.html"
        page1.write_text(page1_html, encoding="utf-8")
        page2.write_text(page2_html, encoding="utf-8")

        config = self._crawl_config(
            file_url(page1),
            output_dir / "crawl_links",
            max_depth=1,
            max_pages=5,
        )
        crawler = SiteCrawler(config)

        report = await crawler.crawl_and_test()

        assert report is not None
        assert report.pages_discovered >= 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_site_crawler_respects_max_pages(self, sample_accessible_page, output_dir):
        """Test site crawler respects max pages limit."""
        config = self._crawl_config(
            file_url(sample_accessible_page),
            output_dir / "crawl_max_pages",
            max_depth=2,
            max_pages=1,
        )
        crawler = SiteCrawler(config)

        report = await crawler.crawl_and_test()

        assert report is not None
        assert report.pages_tested <= 1

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_site_crawler_respects_max_depth(self, html_fixtures_dir, output_dir):
        """Test site crawler respects max depth limit."""
        page_html = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><title>Depth Test</title></head>
<body>
    <h1>Depth Test</h1>
</body>
</html>"""

        page = html_fixtures_dir / "depth_test.html"
        page.write_text(page_html, encoding="utf-8")

        config = self._crawl_config(
            file_url(page),
            output_dir / "crawl_max_depth",
            max_depth=0,
            max_pages=10,
        )
        crawler = SiteCrawler(config)

        report = await crawler.crawl_and_test()

        assert report is not None
        assert report.pages_discovered == 1


class TestUnifiedIntegrationEndToEnd:
    """End-to-end integration tests for complete workflows."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_complete_site_testing_workflow(self, sample_accessible_page, output_dir):
        """Test complete workflow: test, report, and baseline management."""
        config = UnifiedTestConfig(
            url="",
            output_directory=str(output_dir / "e2e"),
            categories=[TestCategory.ALL],
            capture_screenshots=False,
        )
        tester = UnifiedTester(config)

        url = file_url(sample_accessible_page)
        test_report = await tester.test(url)

        assert test_report is not None
        assert test_report.total_tests > 0

        reporter = HTMLReporter()
        html_path = reporter.generate(
            test_report, str(output_dir / "e2e_reports" / "e2e_report.html")
        )

        assert Path(html_path).exists()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_regression_testing_workflow(self, sample_visual_page, baseline_fixtures_dir, output_dir):
        """Test complete visual regression workflow."""
        from Asgard.Freya.Visual.services.screenshot_capture import ScreenshotCapture
        from Asgard.Freya.Visual.services.visual_regression import VisualRegressionTester
        from Asgard.Freya.Visual.models.visual_models import ComparisonConfig

        url = file_url(sample_visual_page)

        manager = BaselineManager(BaselineConfig(
            storage_directory=str(baseline_fixtures_dir / "regression_managed"),
        ))
        baseline_entry = await manager.create_baseline(url, "regression_test")

        assert Path(baseline_entry.screenshot_path).exists()

        capture = ScreenshotCapture(
            output_directory=str(baseline_fixtures_dir / "regression")
        )
        current_result = await capture.capture_full_page(url, "regression_current.png")

        tester = VisualRegressionTester(output_directory=str(output_dir / "regression"))
        comparison_config = ComparisonConfig(threshold=0.95)
        comparison_result = tester.compare(
            baseline_entry.screenshot_path,
            current_result.file_path,
            comparison_config
        )

        assert comparison_result.similarity_score >= 0.90
