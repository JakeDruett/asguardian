"""
Freya Visual L0 Mocked Tests - Visual Regression Tester

Comprehensive tests for visual regression testing service with mocked image_ops.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from Asgard.Freya.Visual.models.visual_models import (
    ComparisonConfig,
    ComparisonMethod,
    DifferenceType,
    RegressionTestSuite,
    RegressionTestCase,
)
from Asgard.Freya.Visual.services.visual_regression import VisualRegressionTester

# Module path prefix for patching
_VR = "Asgard.Freya.Visual.services.visual_regression"


# =============================================================================
# Helper: build a mock image_ops.Image
# =============================================================================

def _make_mock_image(width=1920, height=1080):
    """Create a mock Image compatible with image_ops.Image interface."""
    img = MagicMock()
    img.width = width
    img.height = height
    img.size = (width, height)
    img.pixels = [(0, 0, 0)] * (width * height)
    img.copy.return_value = img
    img.to_grayscale_array.return_value = [128] * (width * height)
    img.histogram.return_value = [0] * 768
    return img


# =============================================================================
# Test VisualRegressionTester Initialization
# =============================================================================

class TestVisualRegressionTesterInit:
    """Tests for VisualRegressionTester initialization."""

    @pytest.mark.L0
    def test_init_default_directory(self):
        """Test initialization with default output directory."""
        tester = VisualRegressionTester()
        assert tester.output_directory == Path("./regression_output")

    @pytest.mark.L0
    def test_init_custom_directory(self, temp_output_dir):
        """Test initialization with custom output directory."""
        tester = VisualRegressionTester(output_directory=str(temp_output_dir))
        assert tester.output_directory == temp_output_dir

    @pytest.mark.L0
    def test_init_creates_subdirectories(self, tmp_path):
        """Test initialization creates subdirectories."""
        output_dir = tmp_path / "regression"
        tester = VisualRegressionTester(output_directory=str(output_dir))

        assert (output_dir / "diffs").exists()
        assert (output_dir / "reports").exists()


# =============================================================================
# Test compare Method - Basic Functionality
# =============================================================================

class TestCompareBasic:
    """Tests for basic compare method functionality."""

    @pytest.mark.L0
    def test_compare_identical_images(self, temp_baseline_file, temp_comparison_file):
        """Test comparing identical images."""
        mock_img = _make_mock_image()

        with patch(f"{_VR}.load_image", return_value=mock_img), \
             patch(f"{_VR}.grayscale_difference_array", return_value=[0] * (1920 * 1080)), \
             patch(f"{_VR}.count_above_threshold", return_value=0):

            tester = VisualRegressionTester()
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
            )

        assert result.baseline_path == str(temp_baseline_file)
        assert result.comparison_path == str(temp_comparison_file)
        assert result.similarity_score == 1.0
        assert result.is_similar is True
        assert len(result.difference_regions) == 0

    @pytest.mark.L0
    def test_compare_different_images(self, temp_baseline_file, temp_comparison_file):
        """Test comparing different images."""
        mock_img = _make_mock_image()
        total = 1920 * 1080
        different = int(total * 0.1)

        with patch(f"{_VR}.load_image", return_value=mock_img), \
             patch(f"{_VR}.grayscale_difference_array", return_value=[50] * total), \
             patch(f"{_VR}.count_above_threshold", return_value=different), \
             patch(f"{_VR}.threshold_to_binary", return_value=[0] * total), \
             patch(f"{_VR}.connected_components", return_value=(0, [0] * total)), \
             patch(f"{_VR}.component_bounding_boxes", return_value={}), \
             patch(f"{_VR}.difference", return_value=mock_img), \
             patch(f"{_VR}.enhance_contrast", return_value=mock_img), \
             patch(f"{_VR}.save_image"), \
             patch(f"{_VR}.draw_rectangle"), \
             patch(f"{_VR}.draw_label"), \
             patch(f"{_VR}.fill_rectangle"):

            tester = VisualRegressionTester()
            config = ComparisonConfig(threshold=0.95, method=ComparisonMethod.PIXEL_DIFF)
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
                config=config,
            )

        assert result.similarity_score == 0.9
        assert result.is_similar is False

    @pytest.mark.L0
    def test_compare_handles_image_load_error(self, temp_baseline_file, temp_comparison_file):
        """Test compare handles image loading errors."""
        with patch(f"{_VR}.load_image", side_effect=Exception("Failed to load image")):

            tester = VisualRegressionTester()
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
            )

        assert result.similarity_score == 0.0
        assert result.is_similar is False
        assert "error" in result.metadata

    @pytest.mark.L0
    def test_compare_resizes_mismatched_sizes(self, temp_baseline_file, temp_comparison_file):
        """Test compare resizes images of different sizes."""
        baseline_img = _make_mock_image(1920, 1080)
        comparison_img = _make_mock_image(1280, 720)
        resized_img = _make_mock_image(1280, 720)

        load_returns = [baseline_img, comparison_img]

        with patch(f"{_VR}.load_image", side_effect=load_returns), \
             patch(f"{_VR}.resize", return_value=resized_img) as mock_resize, \
             patch(f"{_VR}.grayscale_difference_array", return_value=[0] * (1280 * 720)), \
             patch(f"{_VR}.count_above_threshold", return_value=0):

            tester = VisualRegressionTester()
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
            )

        # Should have called resize for both images
        assert mock_resize.call_count == 2


# =============================================================================
# Test compare Method - Comparison Methods
# =============================================================================

class TestComparisonMethods:
    """Tests for different comparison methods."""

    @pytest.mark.L0
    def test_pixel_diff_comparison(self, temp_baseline_file, temp_comparison_file):
        """Test pixel diff comparison method."""
        mock_img = _make_mock_image(100, 100)

        with patch(f"{_VR}.load_image", return_value=mock_img), \
             patch(f"{_VR}.grayscale_difference_array", return_value=[0] * 10000), \
             patch(f"{_VR}.count_above_threshold", return_value=50), \
             patch(f"{_VR}.threshold_to_binary", return_value=[0] * 10000), \
             patch(f"{_VR}.connected_components", return_value=(0, [0] * 10000)), \
             patch(f"{_VR}.component_bounding_boxes", return_value={}):

            tester = VisualRegressionTester()
            config = ComparisonConfig(method=ComparisonMethod.PIXEL_DIFF)
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
                config=config,
            )

        assert result.comparison_method == ComparisonMethod.PIXEL_DIFF
        assert 0.99 <= result.similarity_score <= 1.0

    @pytest.mark.L0
    def test_ssim_comparison(self, temp_baseline_file, temp_comparison_file):
        """Test SSIM comparison method."""
        mock_img = _make_mock_image(100, 100)

        with patch(f"{_VR}.load_image", return_value=mock_img), \
             patch(f"{_VR}.structural_similarity", return_value=(0.95, [1.0] * 10000)):

            tester = VisualRegressionTester()
            config = ComparisonConfig(method=ComparisonMethod.STRUCTURAL_SIMILARITY)
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
                config=config,
            )

        assert result.comparison_method == ComparisonMethod.STRUCTURAL_SIMILARITY
        assert result.similarity_score == 0.95

    @pytest.mark.L0
    def test_perceptual_hash_comparison(self, temp_baseline_file, temp_comparison_file):
        """Test perceptual hash comparison method."""
        mock_img = _make_mock_image(100, 100)
        small_img = _make_mock_image(8, 8)
        small_img.to_grayscale_array.return_value = [128] * 64

        with patch(f"{_VR}.load_image", return_value=mock_img), \
             patch(f"{_VR}.resize", return_value=small_img):

            tester = VisualRegressionTester()
            config = ComparisonConfig(method=ComparisonMethod.PERCEPTUAL_HASH)
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
                config=config,
            )

        assert result.comparison_method == ComparisonMethod.PERCEPTUAL_HASH
        # Identical mock images should produce identical hashes
        assert result.similarity_score == 1.0

    @pytest.mark.L0
    def test_histogram_comparison(self, temp_baseline_file, temp_comparison_file):
        """Test histogram comparison method."""
        mock_img = _make_mock_image(100, 100)
        mock_img.histogram.return_value = [100] * 768

        with patch(f"{_VR}.load_image", return_value=mock_img):

            tester = VisualRegressionTester()
            config = ComparisonConfig(method=ComparisonMethod.HISTOGRAM_COMPARISON)
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
                config=config,
            )

        assert result.comparison_method == ComparisonMethod.HISTOGRAM_COMPARISON


# =============================================================================
# Test compare Method - Configuration Options
# =============================================================================

class TestComparisonConfiguration:
    """Tests for comparison configuration options."""

    @pytest.mark.L0
    def test_compare_with_blur(self, temp_baseline_file, temp_comparison_file):
        """Test comparison with blur preprocessing."""
        mock_img = _make_mock_image(100, 100)

        with patch(f"{_VR}.load_image", return_value=mock_img), \
             patch(f"{_VR}.gaussian_blur", return_value=mock_img) as mock_blur, \
             patch(f"{_VR}.grayscale_difference_array", return_value=[0] * 10000), \
             patch(f"{_VR}.count_above_threshold", return_value=0):

            tester = VisualRegressionTester()
            config = ComparisonConfig(blur_radius=5)
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
                config=config,
            )

        # Should have called gaussian_blur for both images
        assert mock_blur.call_count == 2

    @pytest.mark.L0
    def test_compare_with_ignore_regions(self, temp_baseline_file, temp_comparison_file):
        """Test comparison with ignore regions."""
        mock_img = _make_mock_image(100, 100)

        with patch(f"{_VR}.load_image", return_value=mock_img), \
             patch(f"{_VR}.fill_rectangle") as mock_fill, \
             patch(f"{_VR}.grayscale_difference_array", return_value=[0] * 10000), \
             patch(f"{_VR}.count_above_threshold", return_value=0):

            tester = VisualRegressionTester()
            config = ComparisonConfig(
                ignore_regions=[{"x": 0, "y": 0, "width": 100, "height": 50}]
            )
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
                config=config,
            )

        # Should have called fill_rectangle for masking (once per image per region)
        assert mock_fill.call_count == 2
        mock_img.copy.assert_called()

    @pytest.mark.L0
    def test_compare_respects_threshold(self, temp_baseline_file, temp_comparison_file):
        """Test comparison respects similarity threshold."""
        mock_img = _make_mock_image(100, 100)

        with patch(f"{_VR}.load_image", return_value=mock_img), \
             patch(f"{_VR}.grayscale_difference_array", return_value=[50] * 10000), \
             patch(f"{_VR}.count_above_threshold", return_value=400), \
             patch(f"{_VR}.threshold_to_binary", return_value=[0] * 10000), \
             patch(f"{_VR}.connected_components", return_value=(0, [0] * 10000)), \
             patch(f"{_VR}.component_bounding_boxes", return_value={}):

            tester = VisualRegressionTester()

            # Use PIXEL_DIFF explicitly so the pixel comparison path is used
            # Test with high threshold (0.96 > similarity of 0.96 -> fail)
            config_high = ComparisonConfig(threshold=0.97, method=ComparisonMethod.PIXEL_DIFF)
            result_high = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
                config=config_high,
            )

            # Test with low threshold (0.90 < similarity of 0.96 -> pass)
            config_low = ComparisonConfig(threshold=0.90, method=ComparisonMethod.PIXEL_DIFF)
            result_low = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
                config=config_low,
            )

        assert result_high.similarity_score == result_low.similarity_score
        assert result_high.is_similar != result_low.is_similar


# =============================================================================
# Test run_suite Method
# =============================================================================

class TestRunSuite:
    """Tests for run_suite method."""

    @pytest.mark.L0
    def test_run_suite_basic(self, sample_regression_test_suite):
        """Test running a basic regression test suite."""
        baseline_dir = Path(sample_regression_test_suite.baseline_directory)
        (baseline_dir / "test1.png").write_text("baseline1")
        (baseline_dir / "test2.png").write_text("baseline2")

        output_dir = Path(sample_regression_test_suite.output_directory)
        (output_dir / "test1_current.png").write_text("comparison1")
        (output_dir / "test2_current.png").write_text("comparison2")

        mock_img = _make_mock_image(100, 100)

        with patch(f"{_VR}.load_image", return_value=mock_img), \
             patch(f"{_VR}.grayscale_difference_array", return_value=[0] * 10000), \
             patch(f"{_VR}.count_above_threshold", return_value=0):

            tester = VisualRegressionTester()
            report = tester.run_suite(sample_regression_test_suite)

        assert report.suite_name == sample_regression_test_suite.name
        assert report.total_comparisons == 2
        assert report.report_path is not None

    @pytest.mark.L0
    def test_run_suite_skips_missing_baselines(self, temp_output_dir):
        """Test suite skips tests with missing baseline images."""
        baseline_dir = temp_output_dir / "baselines"
        baseline_dir.mkdir()
        output_dir = temp_output_dir / "output"
        output_dir.mkdir()

        # Only create baseline for test1
        (baseline_dir / "test1.png").write_text("baseline1")

        suite = RegressionTestSuite(
            name="Test Suite",
            baseline_directory=str(baseline_dir),
            output_directory=str(output_dir),
            test_cases=[
                RegressionTestCase(name="test1", url="https://example.com/1"),
                RegressionTestCase(name="test2", url="https://example.com/2"),
            ],
        )

        tester = VisualRegressionTester()
        report = tester.run_suite(suite)

        # Should skip test2 since baseline doesn't exist
        assert report.total_comparisons == 0

    @pytest.mark.L0
    def test_run_suite_calculates_statistics(self, temp_output_dir):
        """Test suite calculates correct statistics."""
        baseline_dir = temp_output_dir / "baselines"
        baseline_dir.mkdir(exist_ok=True)
        output_dir = temp_output_dir / "output"
        output_dir.mkdir(exist_ok=True)

        (baseline_dir / "test1.png").write_text("baseline1")
        (baseline_dir / "test2.png").write_text("baseline2")
        (output_dir / "test1_current.png").write_text("comparison1")
        (output_dir / "test2_current.png").write_text("comparison2")

        suite = RegressionTestSuite(
            name="Stats Suite",
            baseline_directory=str(baseline_dir),
            output_directory=str(output_dir),
            test_cases=[
                RegressionTestCase(name="test1", url="https://example.com/1", threshold=0.95),
                RegressionTestCase(name="test2", url="https://example.com/2", threshold=0.95),
            ],
            comparison_method=ComparisonMethod.PIXEL_DIFF,
        )

        call_count = [0]
        total = 100 * 100

        def mock_count_above(*args, **kwargs):
            call_count[0] += 1
            # First comparison passes (0 different), second fails (5000 different)
            return 0 if call_count[0] <= 1 else 5000

        mock_img = _make_mock_image(100, 100)

        with patch(f"{_VR}.load_image", return_value=mock_img), \
             patch(f"{_VR}.grayscale_difference_array", return_value=[50] * total), \
             patch(f"{_VR}.count_above_threshold", side_effect=mock_count_above), \
             patch(f"{_VR}.threshold_to_binary", return_value=[0] * total), \
             patch(f"{_VR}.connected_components", return_value=(0, [0] * total)), \
             patch(f"{_VR}.component_bounding_boxes", return_value={}), \
             patch(f"{_VR}.difference", return_value=mock_img), \
             patch(f"{_VR}.enhance_contrast", return_value=mock_img), \
             patch(f"{_VR}.save_image"), \
             patch(f"{_VR}.draw_rectangle"), \
             patch(f"{_VR}.draw_label"), \
             patch(f"{_VR}.fill_rectangle"):

            tester = VisualRegressionTester()
            report = tester.run_suite(suite)

        assert report.total_comparisons == 2
        assert report.passed_comparisons == 1
        assert report.failed_comparisons == 1


# =============================================================================
# Test Helper Methods
# =============================================================================

class TestHelperMethods:
    """Tests for helper methods."""

    @pytest.mark.L0
    def test_mask_regions(self):
        """Test _mask_regions helper method."""
        mock_img = _make_mock_image(200, 200)

        with patch(f"{_VR}.fill_rectangle") as mock_fill:
            tester = VisualRegressionTester()
            regions = [
                {"x": 0, "y": 0, "width": 100, "height": 50},
                {"x": 200, "y": 100, "width": 150, "height": 75},
            ]

            masked = tester._mask_regions(mock_img, regions)

        mock_img.copy.assert_called_once()
        assert mock_fill.call_count == 2

    @pytest.mark.L0
    def test_generate_diff_image(self):
        """Test _generate_diff_image helper method."""
        mock_img = _make_mock_image(100, 100)
        mock_diff = _make_mock_image(100, 100)
        mock_enhanced = _make_mock_image(100, 100)

        with patch(f"{_VR}.difference", return_value=mock_diff), \
             patch(f"{_VR}.enhance_contrast", return_value=mock_enhanced), \
             patch(f"{_VR}.save_image") as mock_save:

            tester = VisualRegressionTester()
            diff_path = tester._generate_diff_image(mock_img, mock_img)

        assert "diff_" in diff_path
        assert ".png" in diff_path
        mock_save.assert_called_once()

    @pytest.mark.L0
    def test_generate_annotated_image(self):
        """Test _generate_annotated_image helper method."""
        mock_img = _make_mock_image(200, 200)

        from Asgard.Freya.Visual.models.visual_models import DifferenceRegion, DifferenceType

        regions = [
            DifferenceRegion(
                x=10, y=20, width=100, height=50,
                difference_type=DifferenceType.MODIFICATION,
                confidence=0.85,
                description="Change detected"
            )
        ]

        with patch(f"{_VR}.draw_rectangle") as mock_rect, \
             patch(f"{_VR}.draw_label") as mock_label, \
             patch(f"{_VR}.save_image") as mock_save:

            tester = VisualRegressionTester()
            ann_path = tester._generate_annotated_image(mock_img, regions)

        assert "annotated_" in ann_path
        assert ".png" in ann_path
        mock_img.copy.assert_called_once()
        mock_rect.assert_called_once()
        mock_label.assert_called_once()
        mock_save.assert_called_once()

    @pytest.mark.L0
    def test_generate_html_report(self, sample_regression_test_suite):
        """Test _generate_html_report helper method."""
        from Asgard.Freya.Visual.models.visual_models import RegressionReport, VisualComparisonResult

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
        )

        tester = VisualRegressionTester()
        report_path = tester._generate_html_report(report)

        assert report_path.exists()
        assert report_path.suffix == ".html"

        html_content = report_path.read_text()
        assert "Test Suite" in html_content
        assert "98" in html_content


# =============================================================================
# Test Error Handling
# =============================================================================

class TestErrorHandling:
    """Tests for error handling in VisualRegressionTester."""

    @pytest.mark.L0
    def test_compare_handles_load_errors(self, temp_baseline_file, temp_comparison_file):
        """Test compare handles image loading errors gracefully."""
        with patch(f"{_VR}.load_image", side_effect=Exception("Conversion failed")):

            tester = VisualRegressionTester()
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
            )

        assert result.similarity_score == 0.0
        assert result.is_similar is False

    @pytest.mark.L0
    def test_ssim_always_available(self, temp_baseline_file, temp_comparison_file):
        """Test SSIM comparison is always available (no external dependency fallback)."""
        mock_img = _make_mock_image(100, 100)

        with patch(f"{_VR}.load_image", return_value=mock_img), \
             patch(f"{_VR}.structural_similarity", return_value=(0.92, [1.0] * 10000)):

            tester = VisualRegressionTester()
            config = ComparisonConfig(method=ComparisonMethod.STRUCTURAL_SIMILARITY)
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
                config=config,
            )

        assert result.comparison_method == ComparisonMethod.STRUCTURAL_SIMILARITY
        assert result.similarity_score == 0.92


# =============================================================================
# Test Integration
# =============================================================================

class TestVisualRegressionIntegration:
    """Integration tests for VisualRegressionTester."""

    @pytest.mark.L0
    def test_full_comparison_workflow(self, temp_baseline_file, temp_comparison_file):
        """Test complete comparison workflow with difference detection."""
        mock_img = _make_mock_image(100, 100)
        ssim_map = [1.0] * 10000
        # Mark a region with low SSIM
        for y in range(10, 30):
            for x in range(10, 30):
                ssim_map[y * 100 + x] = 0.5

        with patch(f"{_VR}.load_image", return_value=mock_img), \
             patch(f"{_VR}.structural_similarity", return_value=(0.92, ssim_map)), \
             patch(f"{_VR}.connected_components", return_value=(1, [0] * 10000)), \
             patch(f"{_VR}.component_bounding_boxes", return_value={
                 1: (10, 10, 30, 30, 400)
             }), \
             patch(f"{_VR}.mean_of_indices", return_value=0.5), \
             patch(f"{_VR}.difference", return_value=mock_img), \
             patch(f"{_VR}.enhance_contrast", return_value=mock_img), \
             patch(f"{_VR}.save_image"), \
             patch(f"{_VR}.draw_rectangle"), \
             patch(f"{_VR}.draw_label"):

            tester = VisualRegressionTester()
            config = ComparisonConfig(
                threshold=0.95,
                method=ComparisonMethod.STRUCTURAL_SIMILARITY,
            )
            result = tester.compare(
                str(temp_baseline_file),
                str(temp_comparison_file),
                config=config,
            )

        assert result.similarity_score == 0.92
        assert result.is_similar is False
        assert result.diff_image_path is not None
        assert result.annotated_image_path is not None
        assert len(result.difference_regions) == 1
        assert result.difference_regions[0].pixel_count == 400
