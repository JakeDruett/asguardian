"""
L1 Integration Tests for Freya Visual Testing

Comprehensive integration tests for visual regression testing with real screenshots.
Tests screenshot capture, visual comparison, difference detection, and layout validation
using actual Playwright browser instances in headless mode.

All tests use file:// URLs for local HTML fixtures, making them CI-friendly.
"""

import pytest
from pathlib import Path
import shutil

from Asgard.Freya.Visual.services.screenshot_capture import ScreenshotCapture
from Asgard.Freya.Visual.services.visual_regression import VisualRegressionTester
from Asgard.Freya.Visual.services.layout_validator import LayoutValidator
from Asgard.Freya.Visual.services.style_validator import StyleValidator
from Asgard.Freya.Visual.models.visual_models import (
    ScreenshotConfig,
    ComparisonConfig,
    ComparisonMethod,
    DeviceConfig,
    RegressionTestSuite,
    RegressionTestCase,
)

from Asgard_Test.tests_Freya.L1_Integration.conftest import file_url


class TestVisualIntegrationScreenshotCapture:
    """Integration tests for Screenshot Capture with real HTML pages."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_screenshot_capture_basic(self, sample_visual_page, output_dir):
        """Test basic screenshot capture of HTML page."""
        capture = ScreenshotCapture(output_directory=str(output_dir / "screenshots"))

        url = file_url(sample_visual_page)
        result = await capture.capture_full_page(url, "visual_page.png")

        assert result is not None
        assert result.file_path is not None
        assert Path(result.file_path).exists()
        assert Path(result.file_path).stat().st_size > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_screenshot_capture_viewport_sizes(self, sample_responsive_page, output_dir):
        """Test screenshot capture at different viewport sizes."""
        capture = ScreenshotCapture(output_directory=str(output_dir / "screenshots"))
        url = file_url(sample_responsive_page)

        desktop_config = ScreenshotConfig(
            full_page=False,
            custom_device=DeviceConfig(name="Desktop", width=1920, height=1080),
        )
        result_desktop = await capture.capture_viewport(
            url, "responsive_desktop.png", desktop_config
        )

        assert Path(result_desktop.file_path).exists()

        mobile_config = ScreenshotConfig(
            full_page=False,
            custom_device=DeviceConfig(name="Mobile", width=375, height=667),
        )
        result_mobile = await capture.capture_viewport(
            url, "responsive_mobile.png", mobile_config
        )

        assert Path(result_mobile.file_path).exists()

        desktop_size = Path(result_desktop.file_path).stat().st_size
        mobile_size = Path(result_mobile.file_path).stat().st_size
        assert desktop_size != mobile_size

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_screenshot_capture_full_page(self, sample_accessible_page, output_dir):
        """Test full page screenshot capture."""
        capture = ScreenshotCapture(output_directory=str(output_dir / "screenshots"))

        url = file_url(sample_accessible_page)
        result = await capture.capture_full_page(url, "accessible_full.png")

        assert result.width > 0
        assert result.height > 0
        assert result.metadata is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_screenshot_capture_with_selector(self, sample_visual_page, output_dir):
        """Test screenshot capture of specific element."""
        capture = ScreenshotCapture(output_directory=str(output_dir / "screenshots"))

        url = file_url(sample_visual_page)
        result = await capture.capture_element(url, ".box", "visual_box.png")

        assert Path(result.file_path).exists()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_screenshot_capture_result_structure(self, sample_visual_page, output_dir):
        """Test screenshot capture result structure."""
        capture = ScreenshotCapture(output_directory=str(output_dir / "screenshots"))

        url = file_url(sample_visual_page)
        result = await capture.capture_full_page(url, "structure_test.png")

        assert hasattr(result, 'file_path')
        assert hasattr(result, 'url')
        assert hasattr(result, 'width')
        assert hasattr(result, 'height')
        assert hasattr(result, 'captured_at')
        assert hasattr(result, 'metadata')
        assert result.url == url


class TestVisualIntegrationVisualRegression:
    """Integration tests for Visual Regression Testing with real images."""

    @pytest.fixture
    async def baseline_screenshot(self, sample_visual_page, baseline_fixtures_dir):
        """Create a baseline screenshot for comparison."""
        capture = ScreenshotCapture(output_directory=str(baseline_fixtures_dir))

        url = file_url(sample_visual_page)
        result = await capture.capture_full_page(url, "baseline.png")

        return Path(result.file_path)

    @pytest.fixture
    async def comparison_screenshot(self, sample_visual_page, output_dir):
        """Create a comparison screenshot (should be identical to baseline)."""
        capture = ScreenshotCapture(output_directory=str(output_dir / "comparisons"))

        url = file_url(sample_visual_page)
        result = await capture.capture_full_page(url, "comparison.png")

        return Path(result.file_path)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_visual_regression_identical_images(
        self, baseline_screenshot, comparison_screenshot, output_dir
    ):
        """Test visual regression with identical images."""
        tester = VisualRegressionTester(output_directory=str(output_dir / "regression"))

        config = ComparisonConfig(
            threshold=0.95,
            method=ComparisonMethod.PIXEL_DIFF,
        )

        result = tester.compare(
            str(baseline_screenshot),
            str(comparison_screenshot),
            config
        )

        assert result is not None
        assert result.similarity_score >= 0.95
        assert result.is_similar is True
        assert len(result.difference_regions) == 0 or result.similarity_score >= 0.99

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_visual_regression_comparison_methods(
        self, baseline_screenshot, comparison_screenshot, output_dir
    ):
        """Test different visual comparison methods."""
        tester = VisualRegressionTester(output_directory=str(output_dir / "regression"))

        methods = [
            ComparisonMethod.PIXEL_DIFF,
            ComparisonMethod.PERCEPTUAL_HASH,
            ComparisonMethod.HISTOGRAM_COMPARISON,
        ]

        results = []
        for method in methods:
            config = ComparisonConfig(
                threshold=0.90,
                method=method,
            )
            result = tester.compare(
                str(baseline_screenshot),
                str(comparison_screenshot),
                config
            )
            results.append(result)

        assert all(r.similarity_score >= 0.90 for r in results)
        assert all(r.comparison_method in methods for r in results)

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_visual_regression_difference_detection(
        self, sample_visual_page, sample_accessible_page, output_dir
    ):
        """Test visual regression detects differences between different pages."""
        capture = ScreenshotCapture(output_directory=str(output_dir / "diff_test"))

        url1 = file_url(sample_visual_page)
        result1 = await capture.capture_full_page(url1, "page1.png")

        url2 = file_url(sample_accessible_page)
        result2 = await capture.capture_full_page(url2, "page2.png")

        tester = VisualRegressionTester(output_directory=str(output_dir / "regression"))
        config = ComparisonConfig(
            threshold=0.95,
            method=ComparisonMethod.PIXEL_DIFF,
        )

        result = tester.compare(
            str(result1.file_path),
            str(result2.file_path),
            config
        )

        assert result.similarity_score < 0.95
        assert result.is_similar is False

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_visual_regression_generates_diff_images(
        self, sample_visual_page, sample_accessible_page, output_dir
    ):
        """Test visual regression generates diff and annotated images."""
        capture = ScreenshotCapture(output_directory=str(output_dir / "diff_images"))

        url1 = file_url(sample_visual_page)
        result1 = await capture.capture_full_page(url1, "diff_base.png")

        url2 = file_url(sample_accessible_page)
        result2 = await capture.capture_full_page(url2, "diff_comp.png")

        tester = VisualRegressionTester(output_directory=str(output_dir / "regression"))
        config = ComparisonConfig(
            threshold=0.95,
            method=ComparisonMethod.PIXEL_DIFF,
        )

        result = tester.compare(
            str(result1.file_path),
            str(result2.file_path),
            config
        )

        if result.diff_image_path:
            assert Path(result.diff_image_path).exists()

        if result.annotated_image_path:
            assert Path(result.annotated_image_path).exists()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_visual_regression_result_structure(
        self, baseline_screenshot, comparison_screenshot, output_dir
    ):
        """Test visual regression result structure."""
        tester = VisualRegressionTester(output_directory=str(output_dir / "regression"))

        config = ComparisonConfig(
            threshold=0.95,
        )

        result = tester.compare(
            str(baseline_screenshot),
            str(comparison_screenshot),
            config
        )

        assert hasattr(result, 'baseline_path')
        assert hasattr(result, 'comparison_path')
        assert hasattr(result, 'similarity_score')
        assert hasattr(result, 'is_similar')
        assert hasattr(result, 'difference_regions')
        assert hasattr(result, 'comparison_method')
        assert 0.0 <= result.similarity_score <= 1.0


class TestVisualIntegrationLayoutValidator:
    """Integration tests for Layout Validator with real HTML pages."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_layout_validator_accessible_page(self, sample_accessible_page):
        """Test layout validation on well-structured page."""
        validator = LayoutValidator()

        url = file_url(sample_accessible_page)
        report = await validator.validate(url)

        assert report is not None
        assert report.url == url
        assert report.total_elements > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_layout_validator_responsive_page(self, sample_responsive_page):
        """Test layout validation on responsive page."""
        validator = LayoutValidator()

        url = file_url(sample_responsive_page)
        report = await validator.validate(url)

        assert report is not None
        assert report.total_elements > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_layout_validator_report_structure(self, sample_visual_page):
        """Test layout validator report structure."""
        validator = LayoutValidator()

        url = file_url(sample_visual_page)
        report = await validator.validate(url)

        assert report.url is not None
        assert report.tested_at is not None
        assert report.total_elements >= 0
        assert report.viewport_width > 0
        assert report.viewport_height > 0
        assert isinstance(report.issues, list)


class TestVisualIntegrationStyleValidator:
    """Integration tests for Style Validator with real HTML pages."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_style_validator_accessible_page(self, sample_accessible_page):
        """Test style validation on page with consistent styles."""
        validator = StyleValidator()

        url = file_url(sample_accessible_page)
        report = await validator.validate(url)

        assert report is not None
        assert report.url == url
        assert report.total_elements > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_style_validator_visual_page(self, sample_visual_page):
        """Test style validation on visual test page."""
        validator = StyleValidator()

        url = file_url(sample_visual_page)
        report = await validator.validate(url)

        assert report is not None
        assert report.total_elements > 0

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_style_validator_report_structure(self, sample_responsive_page):
        """Test style validator report structure."""
        validator = StyleValidator()

        url = file_url(sample_responsive_page)
        report = await validator.validate(url)

        assert report.url is not None
        assert report.tested_at is not None
        assert report.total_elements >= 0
        assert isinstance(report.issues, list)
        assert isinstance(report.colors_found, dict)
        assert isinstance(report.fonts_found, dict)


class TestVisualIntegrationRegressionSuite:
    """Integration tests for Regression Test Suite."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_regression_suite_execution(
        self, sample_visual_page, baseline_fixtures_dir, output_dir
    ):
        """Test running a complete regression test suite."""
        capture = ScreenshotCapture(output_directory=str(baseline_fixtures_dir))

        url = file_url(sample_visual_page)
        baseline_result = await capture.capture_full_page(url, "suite_test.png")

        current_dir = output_dir / "suite_current"
        current_dir.mkdir(exist_ok=True)
        shutil.copy(baseline_result.file_path, current_dir / "suite_test_current.png")

        suite = RegressionTestSuite(
            name="Integration Test Suite",
            baseline_directory=str(baseline_fixtures_dir),
            output_directory=str(current_dir),
            test_cases=[
                RegressionTestCase(
                    name="suite_test",
                    url=url,
                ),
            ],
            comparison_method=ComparisonMethod.PIXEL_DIFF,
            default_threshold=0.95,
        )

        tester = VisualRegressionTester(output_directory=str(output_dir / "suite_regression"))
        report = tester.run_suite(suite)

        assert report is not None
        assert report.suite_name == "Integration Test Suite"
        assert report.total_comparisons >= 1
        assert report.passed_comparisons + report.failed_comparisons == report.total_comparisons

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_regression_suite_report_generation(
        self, sample_visual_page, baseline_fixtures_dir, output_dir
    ):
        """Test regression suite generates HTML report."""
        capture = ScreenshotCapture(output_directory=str(baseline_fixtures_dir))

        url = file_url(sample_visual_page)
        baseline_result = await capture.capture_full_page(url, "report_test.png")

        current_dir = output_dir / "report_current"
        current_dir.mkdir(exist_ok=True)
        shutil.copy(baseline_result.file_path, current_dir / "report_test_current.png")

        suite = RegressionTestSuite(
            name="Report Generation Test",
            baseline_directory=str(baseline_fixtures_dir),
            output_directory=str(current_dir),
            test_cases=[
                RegressionTestCase(
                    name="report_test",
                    url=url,
                ),
            ],
        )

        tester = VisualRegressionTester(output_directory=str(output_dir / "report_regression"))
        report = tester.run_suite(suite)

        if report.report_path:
            assert Path(report.report_path).exists()
            assert Path(report.report_path).suffix == ".html"
