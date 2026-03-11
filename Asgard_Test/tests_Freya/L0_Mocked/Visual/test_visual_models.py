"""
Freya Visual L0 Mocked Tests - Visual Models

Comprehensive tests for Visual module Pydantic models.
"""

import sys
from datetime import datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from Asgard.Freya.Visual.models.visual_models import (
    ComparisonMethod,
    DifferenceType,
    LayoutIssueType,
    StyleIssueType,
    DeviceConfig,
    COMMON_DEVICES,
    ScreenshotConfig,
    ScreenshotResult,
    DifferenceRegion,
    ComparisonConfig,
    VisualComparisonResult,
    RegressionTestCase,
    RegressionTestSuite,
    RegressionReport,
    ElementBox,
    LayoutIssue,
    LayoutReport,
    StyleIssue,
    StyleReport,
)


# =============================================================================
# Test Enums
# =============================================================================

class TestComparisonMethod:
    """Tests for ComparisonMethod enum."""

    @pytest.mark.L0
    def test_all_comparison_methods_exist(self):
        """Test all expected comparison methods are defined."""
        expected_methods = {
            "pixel_diff",
            "structural_similarity",
            "perceptual_hash",
            "histogram_comparison",
        }

        actual_methods = {method.value for method in ComparisonMethod}
        assert actual_methods == expected_methods

    @pytest.mark.L0
    def test_comparison_method_values_are_strings(self):
        """Test all comparison method values are strings."""
        for method in ComparisonMethod:
            assert isinstance(method.value, str)


class TestDifferenceType:
    """Tests for DifferenceType enum."""

    @pytest.mark.L0
    def test_all_difference_types_exist(self):
        """Test all expected difference types are defined."""
        expected_types = {
            "addition",
            "removal",
            "modification",
            "position",
            "color",
            "size",
            "text",
        }

        actual_types = {dtype.value for dtype in DifferenceType}
        assert actual_types == expected_types

    @pytest.mark.L0
    def test_difference_type_values_are_strings(self):
        """Test all difference type values are strings."""
        for dtype in DifferenceType:
            assert isinstance(dtype.value, str)


class TestLayoutIssueType:
    """Tests for LayoutIssueType enum."""

    @pytest.mark.L0
    def test_all_layout_issue_types_exist(self):
        """Test all expected layout issue types are defined."""
        expected_types = {
            "overflow",
            "overlap",
            "misalignment",
            "spacing",
            "z_index",
            "visibility",
            "responsive",
        }

        actual_types = {itype.value for itype in LayoutIssueType}
        assert actual_types == expected_types

    @pytest.mark.L0
    def test_layout_issue_type_values_are_strings(self):
        """Test all layout issue type values are strings."""
        for itype in LayoutIssueType:
            assert isinstance(itype.value, str)


class TestStyleIssueType:
    """Tests for StyleIssueType enum."""

    @pytest.mark.L0
    def test_all_style_issue_types_exist(self):
        """Test all expected style issue types are defined."""
        expected_types = {
            "color_mismatch",
            "font_mismatch",
            "spacing_mismatch",
            "border_mismatch",
            "shadow_mismatch",
            "unknown_color",
            "unknown_font",
        }

        actual_types = {itype.value for itype in StyleIssueType}
        assert actual_types == expected_types

    @pytest.mark.L0
    def test_style_issue_type_values_are_strings(self):
        """Test all style issue type values are strings."""
        for itype in StyleIssueType:
            assert isinstance(itype.value, str)


# =============================================================================
# Test DeviceConfig
# =============================================================================

class TestDeviceConfig:
    """Tests for DeviceConfig model."""

    @pytest.mark.L0
    def test_device_config_creation_minimal(self):
        """Test creating DeviceConfig with minimal required fields."""
        config = DeviceConfig(name="Test Device", width=1920, height=1080)

        assert config.name == "Test Device"
        assert config.width == 1920
        assert config.height == 1080
        assert config.device_scale_factor == 1.0
        assert config.is_mobile is False
        assert config.has_touch is False
        assert config.user_agent is None

    @pytest.mark.L0
    def test_device_config_creation_full(self):
        """Test creating DeviceConfig with all fields."""
        config = DeviceConfig(
            name="iPhone 14",
            width=390,
            height=844,
            device_scale_factor=3.0,
            is_mobile=True,
            has_touch=True,
            user_agent="Mozilla/5.0 iPhone",
        )

        assert config.name == "iPhone 14"
        assert config.width == 390
        assert config.height == 844
        assert config.device_scale_factor == 3.0
        assert config.is_mobile is True
        assert config.has_touch is True
        assert config.user_agent == "Mozilla/5.0 iPhone"

    @pytest.mark.L0
    def test_device_config_validation_missing_name(self):
        """Test DeviceConfig validation fails without name."""
        with pytest.raises(ValidationError):
            DeviceConfig(width=1920, height=1080)

    @pytest.mark.L0
    def test_device_config_validation_missing_dimensions(self):
        """Test DeviceConfig validation fails without dimensions."""
        with pytest.raises(ValidationError):
            DeviceConfig(name="Test Device")

    @pytest.mark.L0
    def test_common_devices_exist(self):
        """Test that COMMON_DEVICES dictionary is populated."""
        assert len(COMMON_DEVICES) > 0

        expected_devices = {
            "desktop-1080p",
            "desktop-720p",
            "laptop",
            "ipad",
            "ipad-pro",
            "iphone-14",
            "iphone-14-pro-max",
            "pixel-7",
            "galaxy-s21",
        }

        assert set(COMMON_DEVICES.keys()) == expected_devices

    @pytest.mark.L0
    def test_common_devices_are_device_configs(self):
        """Test all common devices are DeviceConfig instances."""
        for device_name, device in COMMON_DEVICES.items():
            assert isinstance(device, DeviceConfig)
            assert device.name is not None
            assert device.width > 0
            assert device.height > 0


# =============================================================================
# Test ScreenshotConfig
# =============================================================================

class TestScreenshotConfig:
    """Tests for ScreenshotConfig model."""

    @pytest.mark.L0
    def test_screenshot_config_defaults(self):
        """Test ScreenshotConfig default values."""
        config = ScreenshotConfig()

        assert config.full_page is True
        assert config.device is None
        assert config.custom_device is None
        assert config.wait_for_selector is None
        assert config.wait_for_timeout == 1000
        assert config.hide_selectors == []
        assert config.clip is None
        assert config.quality == 100
        assert config.format == "png"

    @pytest.mark.L0
    def test_screenshot_config_custom_values(self):
        """Test ScreenshotConfig with custom values."""
        config = ScreenshotConfig(
            full_page=False,
            device="iphone-14",
            wait_for_selector="#content",
            wait_for_timeout=2000,
            hide_selectors=[".ad", ".cookie-banner"],
            clip={"x": 0, "y": 0, "width": 800, "height": 600},
            quality=80,
            format="jpeg",
        )

        assert config.full_page is False
        assert config.device == "iphone-14"
        assert config.wait_for_selector == "#content"
        assert config.wait_for_timeout == 2000
        assert config.hide_selectors == [".ad", ".cookie-banner"]
        assert config.clip == {"x": 0, "y": 0, "width": 800, "height": 600}
        assert config.quality == 80
        assert config.format == "jpeg"

    @pytest.mark.L0
    def test_screenshot_config_model_copy(self):
        """Test ScreenshotConfig model_copy functionality."""
        config = ScreenshotConfig(full_page=True, format="png")
        updated = config.model_copy(update={"full_page": False, "format": "jpeg"})

        assert updated.full_page is False
        assert updated.format == "jpeg"


# =============================================================================
# Test ScreenshotResult
# =============================================================================

class TestScreenshotResult:
    """Tests for ScreenshotResult model."""

    @pytest.mark.L0
    def test_screenshot_result_creation(self):
        """Test creating ScreenshotResult."""
        result = ScreenshotResult(
            url="https://example.com",
            file_path="/tmp/screenshot.png",
            width=1920,
            height=1080,
        )

        assert result.url == "https://example.com"
        assert result.file_path == "/tmp/screenshot.png"
        assert result.width == 1920
        assert result.height == 1080
        assert result.device is None
        assert result.file_size_bytes == 0
        assert result.metadata == {}
        assert result.captured_at is not None

    @pytest.mark.L0
    def test_screenshot_result_with_metadata(self):
        """Test ScreenshotResult with metadata."""
        result = ScreenshotResult(
            url="https://example.com",
            file_path="/tmp/screenshot.png",
            width=390,
            height=844,
            device="iphone-14",
            file_size_bytes=12345,
            metadata={"full_page": True, "format": "png"},
        )

        assert result.device == "iphone-14"
        assert result.file_size_bytes == 12345
        assert result.metadata["full_page"] is True
        assert result.metadata["format"] == "png"

    @pytest.mark.L0
    def test_screenshot_result_captured_at_auto_generated(self):
        """Test captured_at is auto-generated."""
        result = ScreenshotResult(
            url="https://example.com",
            file_path="/tmp/screenshot.png",
            width=1920,
            height=1080,
        )

        # Should be ISO format datetime
        datetime.fromisoformat(result.captured_at)


# =============================================================================
# Test DifferenceRegion
# =============================================================================

class TestDifferenceRegion:
    """Tests for DifferenceRegion model."""

    @pytest.mark.L0
    def test_difference_region_creation(self):
        """Test creating DifferenceRegion."""
        region = DifferenceRegion(
            x=10,
            y=20,
            width=100,
            height=50,
            difference_type=DifferenceType.MODIFICATION,
            confidence=0.85,
            description="Pixel differences detected",
        )

        assert region.x == 10
        assert region.y == 20
        assert region.width == 100
        assert region.height == 50
        assert region.difference_type == DifferenceType.MODIFICATION
        assert region.confidence == 0.85
        assert region.description == "Pixel differences detected"
        assert region.pixel_count == 0
        assert region.average_difference == 0.0

    @pytest.mark.L0
    def test_difference_region_with_optional_fields(self):
        """Test DifferenceRegion with optional fields."""
        region = DifferenceRegion(
            x=10,
            y=20,
            width=100,
            height=50,
            difference_type=DifferenceType.COLOR,
            confidence=0.90,
            description="Color change detected",
            pixel_count=500,
            average_difference=0.25,
        )

        assert region.pixel_count == 500
        assert region.average_difference == 0.25


# =============================================================================
# Test ComparisonConfig
# =============================================================================

class TestComparisonConfig:
    """Tests for ComparisonConfig model."""

    @pytest.mark.L0
    def test_comparison_config_defaults(self):
        """Test ComparisonConfig default values."""
        config = ComparisonConfig()

        assert config.threshold == 0.95
        assert config.method == ComparisonMethod.STRUCTURAL_SIMILARITY
        assert config.ignore_regions == []
        assert config.blur_radius == 0
        assert config.color_tolerance == 10
        assert config.anti_aliasing_detection is True

    @pytest.mark.L0
    def test_comparison_config_custom_values(self):
        """Test ComparisonConfig with custom values."""
        config = ComparisonConfig(
            threshold=0.90,
            method=ComparisonMethod.PIXEL_DIFF,
            ignore_regions=[{"x": 0, "y": 0, "width": 100, "height": 50}],
            blur_radius=5,
            color_tolerance=20,
            anti_aliasing_detection=False,
        )

        assert config.threshold == 0.90
        assert config.method == ComparisonMethod.PIXEL_DIFF
        assert len(config.ignore_regions) == 1
        assert config.blur_radius == 5
        assert config.color_tolerance == 20
        assert config.anti_aliasing_detection is False


# =============================================================================
# Test VisualComparisonResult
# =============================================================================

class TestVisualComparisonResult:
    """Tests for VisualComparisonResult model."""

    @pytest.mark.L0
    def test_visual_comparison_result_creation(self):
        """Test creating VisualComparisonResult."""
        result = VisualComparisonResult(
            baseline_path="/tmp/baseline.png",
            comparison_path="/tmp/comparison.png",
            similarity_score=0.98,
            is_similar=True,
        )

        assert result.baseline_path == "/tmp/baseline.png"
        assert result.comparison_path == "/tmp/comparison.png"
        assert result.similarity_score == 0.98
        assert result.is_similar is True
        assert result.difference_regions == []
        assert result.diff_image_path is None
        assert result.annotated_image_path is None
        assert result.comparison_method == ComparisonMethod.STRUCTURAL_SIMILARITY
        assert result.analysis_time == 0.0
        assert result.metadata == {}

    @pytest.mark.L0
    def test_visual_comparison_result_with_differences(self):
        """Test VisualComparisonResult with difference regions."""
        regions = [
            DifferenceRegion(
                x=10,
                y=20,
                width=100,
                height=50,
                difference_type=DifferenceType.MODIFICATION,
                confidence=0.85,
                description="Change detected",
            )
        ]

        result = VisualComparisonResult(
            baseline_path="/tmp/baseline.png",
            comparison_path="/tmp/comparison.png",
            similarity_score=0.85,
            is_similar=False,
            difference_regions=regions,
            diff_image_path="/tmp/diff.png",
            annotated_image_path="/tmp/annotated.png",
            comparison_method=ComparisonMethod.PIXEL_DIFF,
            analysis_time=1.234,
            metadata={"threshold": 0.95},
        )

        assert result.is_similar is False
        assert len(result.difference_regions) == 1
        assert result.diff_image_path == "/tmp/diff.png"
        assert result.annotated_image_path == "/tmp/annotated.png"
        assert result.comparison_method == ComparisonMethod.PIXEL_DIFF
        assert result.analysis_time == 1.234
        assert result.metadata["threshold"] == 0.95


# =============================================================================
# Test RegressionTestCase
# =============================================================================

class TestRegressionTestCase:
    """Tests for RegressionTestCase model."""

    @pytest.mark.L0
    def test_regression_test_case_minimal(self):
        """Test creating RegressionTestCase with minimal fields."""
        test_case = RegressionTestCase(
            name="homepage_test",
            url="https://example.com",
        )

        assert test_case.name == "homepage_test"
        assert test_case.url == "https://example.com"
        assert test_case.selector is None
        assert test_case.device is None
        assert test_case.wait_for is None
        assert test_case.threshold == 0.95

    @pytest.mark.L0
    def test_regression_test_case_full(self):
        """Test creating RegressionTestCase with all fields."""
        test_case = RegressionTestCase(
            name="mobile_homepage",
            url="https://example.com",
            selector="#main-content",
            device="iphone-14",
            wait_for=".loaded",
            threshold=0.90,
        )

        assert test_case.name == "mobile_homepage"
        assert test_case.url == "https://example.com"
        assert test_case.selector == "#main-content"
        assert test_case.device == "iphone-14"
        assert test_case.wait_for == ".loaded"
        assert test_case.threshold == 0.90


# =============================================================================
# Test RegressionTestSuite
# =============================================================================

class TestRegressionTestSuite:
    """Tests for RegressionTestSuite model."""

    @pytest.mark.L0
    def test_regression_test_suite_creation(self):
        """Test creating RegressionTestSuite."""
        suite = RegressionTestSuite(
            name="Homepage Tests",
            baseline_directory="/tmp/baselines",
            output_directory="/tmp/output",
        )

        assert suite.name == "Homepage Tests"
        assert suite.baseline_directory == "/tmp/baselines"
        assert suite.output_directory == "/tmp/output"
        assert suite.test_cases == []
        assert suite.default_threshold == 0.95
        assert suite.comparison_method == ComparisonMethod.STRUCTURAL_SIMILARITY

    @pytest.mark.L0
    def test_regression_test_suite_with_test_cases(self):
        """Test RegressionTestSuite with test cases."""
        test_cases = [
            RegressionTestCase(name="test1", url="https://example.com/1"),
            RegressionTestCase(name="test2", url="https://example.com/2"),
        ]

        suite = RegressionTestSuite(
            name="Full Suite",
            baseline_directory="/tmp/baselines",
            output_directory="/tmp/output",
            test_cases=test_cases,
            default_threshold=0.90,
            comparison_method=ComparisonMethod.PIXEL_DIFF,
        )

        assert len(suite.test_cases) == 2
        assert suite.default_threshold == 0.90
        assert suite.comparison_method == ComparisonMethod.PIXEL_DIFF


# =============================================================================
# Test RegressionReport
# =============================================================================

class TestRegressionReport:
    """Tests for RegressionReport model."""

    @pytest.mark.L0
    def test_regression_report_creation(self):
        """Test creating RegressionReport."""
        report = RegressionReport(
            suite_name="Test Suite",
            total_comparisons=10,
            passed_comparisons=8,
            failed_comparisons=2,
        )

        assert report.suite_name == "Test Suite"
        assert report.total_comparisons == 10
        assert report.passed_comparisons == 8
        assert report.failed_comparisons == 2
        assert report.skipped_comparisons == 0
        assert report.results == []
        assert report.overall_similarity == 0.0
        assert report.critical_failures == 0
        assert report.report_path is None
        assert report.report_timestamp is not None

    @pytest.mark.L0
    def test_regression_report_with_results(self):
        """Test RegressionReport with results."""
        results = [
            VisualComparisonResult(
                baseline_path="/tmp/baseline.png",
                comparison_path="/tmp/comparison.png",
                similarity_score=0.98,
                is_similar=True,
            )
        ]

        report = RegressionReport(
            suite_name="Test Suite",
            total_comparisons=1,
            passed_comparisons=1,
            failed_comparisons=0,
            results=results,
            overall_similarity=0.98,
            report_path="/tmp/report.html",
        )

        assert len(report.results) == 1
        assert report.overall_similarity == 0.98
        assert report.report_path == "/tmp/report.html"


# =============================================================================
# Test ElementBox
# =============================================================================

class TestElementBox:
    """Tests for ElementBox model."""

    @pytest.mark.L0
    def test_element_box_creation(self):
        """Test creating ElementBox."""
        box = ElementBox(
            x=10.5,
            y=20.3,
            width=100.0,
            height=50.7,
            selector=".test-element",
        )

        assert box.x == 10.5
        assert box.y == 20.3
        assert box.width == 100.0
        assert box.height == 50.7
        assert box.selector == ".test-element"

    @pytest.mark.L0
    def test_element_box_validation(self):
        """Test ElementBox requires all fields."""
        with pytest.raises(ValidationError):
            ElementBox(x=10, y=20, width=100)


# =============================================================================
# Test LayoutIssue
# =============================================================================

class TestLayoutIssue:
    """Tests for LayoutIssue model."""

    @pytest.mark.L0
    def test_layout_issue_creation(self):
        """Test creating LayoutIssue."""
        issue = LayoutIssue(
            issue_type=LayoutIssueType.OVERFLOW,
            element_selector=".container",
            description="Element overflows viewport",
            severity="moderate",
            suggested_fix="Add overflow: hidden",
        )

        assert issue.issue_type == LayoutIssueType.OVERFLOW
        assert issue.element_selector == ".container"
        assert issue.description == "Element overflows viewport"
        assert issue.severity == "moderate"
        assert issue.affected_area is None
        assert issue.related_elements == []
        assert issue.suggested_fix == "Add overflow: hidden"

    @pytest.mark.L0
    def test_layout_issue_with_affected_area(self):
        """Test LayoutIssue with affected area."""
        box = ElementBox(x=10, y=20, width=100, height=50, selector=".container")

        issue = LayoutIssue(
            issue_type=LayoutIssueType.OVERLAP,
            element_selector=".button",
            description="Button overlaps with link",
            severity="serious",
            affected_area=box,
            related_elements=[".link"],
            suggested_fix="Adjust positioning",
        )

        assert issue.affected_area == box
        assert issue.related_elements == [".link"]


# =============================================================================
# Test LayoutReport
# =============================================================================

class TestLayoutReport:
    """Tests for LayoutReport model."""

    @pytest.mark.L0
    def test_layout_report_creation(self):
        """Test creating LayoutReport."""
        report = LayoutReport(
            url="https://example.com",
            viewport_width=1920,
            viewport_height=1080,
        )

        assert report.url == "https://example.com"
        assert report.viewport_width == 1920
        assert report.viewport_height == 1080
        assert report.total_elements == 0
        assert report.issues == []
        assert report.overflow_elements == []
        assert report.overlapping_elements == []
        assert report.tested_at is not None

    @pytest.mark.L0
    def test_layout_report_has_issues_property(self):
        """Test LayoutReport has_issues property."""
        report_no_issues = LayoutReport(
            url="https://example.com",
            viewport_width=1920,
            viewport_height=1080,
        )

        assert report_no_issues.has_issues is False

        issue = LayoutIssue(
            issue_type=LayoutIssueType.OVERFLOW,
            element_selector=".test",
            description="Test issue",
            severity="minor",
            suggested_fix="Fix it",
        )

        report_with_issues = LayoutReport(
            url="https://example.com",
            viewport_width=1920,
            viewport_height=1080,
            issues=[issue],
        )

        assert report_with_issues.has_issues is True

    @pytest.mark.L0
    def test_layout_report_with_data(self):
        """Test LayoutReport with issues and elements."""
        issue = LayoutIssue(
            issue_type=LayoutIssueType.OVERFLOW,
            element_selector=".container",
            description="Overflow detected",
            severity="moderate",
            suggested_fix="Fix overflow",
        )

        report = LayoutReport(
            url="https://example.com",
            viewport_width=1920,
            viewport_height=1080,
            total_elements=150,
            issues=[issue],
            overflow_elements=[".container", ".header"],
            overlapping_elements=[(".button1", ".button2")],
        )

        assert report.total_elements == 150
        assert len(report.issues) == 1
        assert len(report.overflow_elements) == 2
        assert len(report.overlapping_elements) == 1


# =============================================================================
# Test StyleIssue
# =============================================================================

class TestStyleIssue:
    """Tests for StyleIssue model."""

    @pytest.mark.L0
    def test_style_issue_creation(self):
        """Test creating StyleIssue."""
        issue = StyleIssue(
            issue_type=StyleIssueType.UNKNOWN_COLOR,
            element_selector=".text",
            property_name="color",
            actual_value="#ff0000",
            description="Color not in theme",
            severity="minor",
        )

        assert issue.issue_type == StyleIssueType.UNKNOWN_COLOR
        assert issue.element_selector == ".text"
        assert issue.property_name == "color"
        assert issue.actual_value == "#ff0000"
        assert issue.expected_value is None
        assert issue.description == "Color not in theme"
        assert issue.severity == "minor"

    @pytest.mark.L0
    def test_style_issue_with_expected_value(self):
        """Test StyleIssue with expected value."""
        issue = StyleIssue(
            issue_type=StyleIssueType.COLOR_MISMATCH,
            element_selector=".button",
            property_name="backgroundColor",
            actual_value="#ff0000",
            expected_value="#007bff",
            description="Background color mismatch",
            severity="moderate",
        )

        assert issue.expected_value == "#007bff"


# =============================================================================
# Test StyleReport
# =============================================================================

class TestStyleReport:
    """Tests for StyleReport model."""

    @pytest.mark.L0
    def test_style_report_creation(self):
        """Test creating StyleReport."""
        report = StyleReport(
            url="https://example.com",
        )

        assert report.url == "https://example.com"
        assert report.theme_file is None
        assert report.total_elements == 0
        assert report.issues == []
        assert report.colors_found == {}
        assert report.fonts_found == {}
        assert report.unknown_colors == []
        assert report.unknown_fonts == []
        assert report.tested_at is not None

    @pytest.mark.L0
    def test_style_report_has_issues_property(self):
        """Test StyleReport has_issues property."""
        report_no_issues = StyleReport(url="https://example.com")
        assert report_no_issues.has_issues is False

        issue = StyleIssue(
            issue_type=StyleIssueType.UNKNOWN_COLOR,
            element_selector=".test",
            property_name="color",
            actual_value="#ff0000",
            description="Test issue",
            severity="minor",
        )

        report_with_issues = StyleReport(
            url="https://example.com",
            issues=[issue],
        )

        assert report_with_issues.has_issues is True

    @pytest.mark.L0
    def test_style_report_with_data(self):
        """Test StyleReport with complete data."""
        issue = StyleIssue(
            issue_type=StyleIssueType.UNKNOWN_COLOR,
            element_selector=".text",
            property_name="color",
            actual_value="#ff0000",
            description="Unknown color",
            severity="minor",
        )

        report = StyleReport(
            url="https://example.com",
            theme_file="/tmp/theme.json",
            total_elements=100,
            issues=[issue],
            colors_found={"#007bff": 25, "#ff0000": 5},
            fonts_found={"roboto": 80, "arial": 20},
            unknown_colors=["#ff0000"],
            unknown_fonts=["comic sans"],
        )

        assert report.theme_file == "/tmp/theme.json"
        assert report.total_elements == 100
        assert len(report.issues) == 1
        assert report.colors_found["#007bff"] == 25
        assert report.fonts_found["roboto"] == 80
        assert "#ff0000" in report.unknown_colors
        assert "comic sans" in report.unknown_fonts
