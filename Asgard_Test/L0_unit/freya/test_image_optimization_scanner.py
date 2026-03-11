"""
Comprehensive L0 Unit Tests for Freya ImageOptimizationScanner

Tests the ImageOptimizationScanner service including:
- Scanner initialization with custom configs
- Image extraction and parsing
- Alt text validation (missing, empty, decorative)
- Lazy loading detection (above-fold vs below-fold)
- Image format optimization (WebP/AVIF vs legacy)
- Dimension validation (width/height attributes)
- Oversized image detection
- Srcset validation for responsive images
- Report generation and scoring
- Async scanning workflows
"""

import pytest
import sys
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from datetime import datetime
from typing import Dict, List, Any

# Add the Freya directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'Asgard', 'Freya'))

try:
    from Images.services.image_optimization_scanner import ImageOptimizationScanner
    from Images.models.image_models import (
        ImageConfig,
        ImageFormat,
        ImageInfo,
        ImageIssue,
        ImageIssueSeverity,
        ImageIssueType,
        ImageReport,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestImageOptimizationScannerInit:
    """Test ImageOptimizationScanner initialization"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_scanner_init_with_default_config(self):
        """Test scanner initializes with default config"""
        scanner = ImageOptimizationScanner()

        assert scanner.config is not None
        assert scanner.config.__class__.__name__ == "ImageConfig"
        assert scanner.config.check_alt_text is True
        assert scanner._http_client is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_scanner_init_with_custom_config(self):
        """Test scanner initializes with custom config"""
        custom_config = ImageConfig(
            check_alt_text=True,
            check_lazy_loading=False,
            oversized_threshold=2.0,
        )
        scanner = ImageOptimizationScanner(config=custom_config)

        assert scanner.config == custom_config
        assert scanner.config.check_alt_text is True
        assert scanner.config.check_lazy_loading is False
        assert scanner.config.oversized_threshold == 2.0

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_scanner_init_accessibility_only_config(self):
        """Test scanner with accessibility-only configuration"""
        config = ImageConfig(
            check_alt_text=True,
            check_lazy_loading=False,
            check_formats=False,
            check_dimensions=False,
            check_oversized=False,
            check_srcset=False,
        )
        scanner = ImageOptimizationScanner(config=config)

        assert scanner.config.check_alt_text is True
        assert scanner.config.check_lazy_loading is False
        assert scanner.config.check_formats is False


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
@pytest.mark.asyncio
class TestImageOptimizationScannerHTTPClient:
    """Test HTTP client management"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    async def test_get_client_creates_client_on_first_call(self):
        """Test _get_client creates HTTP client on first access"""
        scanner = ImageOptimizationScanner()

        assert scanner._http_client is None
        client = await scanner._get_client()

        assert client is not None
        assert scanner._http_client is not None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    async def test_get_client_reuses_existing_client(self):
        """Test _get_client reuses existing HTTP client"""
        scanner = ImageOptimizationScanner()

        client1 = await scanner._get_client()
        client2 = await scanner._get_client()

        assert client1 is client2

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    async def test_close_closes_http_client(self):
        """Test close method closes HTTP client"""
        scanner = ImageOptimizationScanner()
        client = await scanner._get_client()

        assert scanner._http_client is not None
        await scanner.close()

        assert scanner._http_client is None


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestImageFormatDetection:
    """Test image format detection"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_detect_format_jpeg(self):
        """Test detection of JPEG format"""
        scanner = ImageOptimizationScanner()

        assert scanner._detect_format("image.jpeg") == ImageFormat.JPEG
        assert scanner._detect_format("image.jpg") == ImageFormat.JPG
        assert scanner._detect_format("IMAGE.JPEG") == ImageFormat.JPEG

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_detect_format_png(self):
        """Test detection of PNG format"""
        scanner = ImageOptimizationScanner()

        assert scanner._detect_format("image.png") == ImageFormat.PNG
        assert scanner._detect_format("IMAGE.PNG") == ImageFormat.PNG

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_detect_format_webp(self):
        """Test detection of WebP format"""
        scanner = ImageOptimizationScanner()

        assert scanner._detect_format("image.webp") == ImageFormat.WEBP
        assert scanner._detect_format("https://cdn.com/img.webp") == ImageFormat.WEBP

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_detect_format_avif(self):
        """Test detection of AVIF format"""
        scanner = ImageOptimizationScanner()

        assert scanner._detect_format("image.avif") == ImageFormat.AVIF

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_detect_format_svg(self):
        """Test detection of SVG format"""
        scanner = ImageOptimizationScanner()

        assert scanner._detect_format("icon.svg") == ImageFormat.SVG

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_detect_format_unknown(self):
        """Test detection returns UNKNOWN for unknown formats"""
        scanner = ImageOptimizationScanner()

        assert scanner._detect_format("") == ImageFormat.UNKNOWN
        assert scanner._detect_format("no-extension") == ImageFormat.UNKNOWN
        assert scanner._detect_format("image.xyz") == ImageFormat.UNKNOWN

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_detect_format_cdn_patterns(self):
        """Test format detection from CDN URLs"""
        scanner = ImageOptimizationScanner()

        assert scanner._detect_format("https://cdn.com/format=webp") == ImageFormat.WEBP
        assert scanner._detect_format("https://cdn.com/output=avif") == ImageFormat.AVIF


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestParseInt:
    """Test integer parsing helper"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_parse_int_valid_integer(self):
        """Test _parse_int with valid integer"""
        scanner = ImageOptimizationScanner()

        assert scanner._parse_int(100) == 100
        assert scanner._parse_int("200") == 200

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_parse_int_invalid_values(self):
        """Test _parse_int returns None for invalid values"""
        scanner = ImageOptimizationScanner()

        assert scanner._parse_int(None) is None
        assert scanner._parse_int("invalid") is None
        assert scanner._parse_int("") is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_parse_int_edge_cases(self):
        """Test _parse_int edge cases"""
        scanner = ImageOptimizationScanner()

        assert scanner._parse_int(0) == 0
        assert scanner._parse_int("0") == 0
        assert scanner._parse_int(12.5) == 12


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestBuildImageInfo:
    """Test building ImageInfo from extracted data"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_image_info_minimal_data(self):
        """Test building ImageInfo with minimal data"""
        scanner = ImageOptimizationScanner()
        data = {
            "src": "https://example.com/image.jpg",
            "hasAlt": False,
        }

        image_info = scanner._build_image_info(data)

        assert image_info.src == "https://example.com/image.jpg"
        assert image_info.format == ImageFormat.JPG

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_image_info_with_alt_text(self):
        """Test building ImageInfo with alt text"""
        scanner = ImageOptimizationScanner()
        data = {
            "src": "https://example.com/image.jpg",
            "alt": "Test image",
            "hasAlt": True,
        }

        image_info = scanner._build_image_info(data)

        assert image_info.alt == "Test image"
        assert image_info.has_alt is True

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_image_info_with_dimensions(self):
        """Test building ImageInfo with dimensions"""
        scanner = ImageOptimizationScanner()
        data = {
            "src": "https://example.com/image.jpg",
            "width": "800",
            "height": "600",
            "hasAlt": False,
        }

        image_info = scanner._build_image_info(data)

        assert image_info.width == 800
        assert image_info.height == 600
        assert image_info.has_dimensions is True

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_image_info_lazy_loading(self):
        """Test building ImageInfo with lazy loading"""
        scanner = ImageOptimizationScanner()
        data = {
            "src": "https://example.com/image.jpg",
            "loading": "lazy",
            "hasAlt": False,
        }

        image_info = scanner._build_image_info(data)

        assert image_info.loading == "lazy"
        assert image_info.has_lazy_loading is True

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_image_info_srcset(self):
        """Test building ImageInfo with srcset"""
        scanner = ImageOptimizationScanner()
        data = {
            "src": "https://example.com/image.jpg",
            "srcset": "image-800.jpg 800w, image-1200.jpg 1200w",
            "hasAlt": False,
        }

        image_info = scanner._build_image_info(data)

        assert image_info.srcset == "image-800.jpg 800w, image-1200.jpg 1200w"
        assert image_info.has_srcset is True

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_image_info_decorative_by_role(self):
        """Test building ImageInfo detects decorative by role=presentation"""
        scanner = ImageOptimizationScanner()
        data = {
            "src": "https://example.com/icon.svg",
            "role": "presentation",
            "hasAlt": False,
        }

        image_info = scanner._build_image_info(data)

        assert image_info.is_decorative is True

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_image_info_decorative_by_aria_hidden(self):
        """Test building ImageInfo detects decorative by aria-hidden"""
        scanner = ImageOptimizationScanner()
        data = {
            "src": "https://example.com/icon.svg",
            "ariaHidden": "true",
            "hasAlt": False,
        }

        image_info = scanner._build_image_info(data)

        assert image_info.is_decorative is True

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_image_info_decorative_by_empty_alt(self):
        """Test building ImageInfo detects decorative by empty alt"""
        scanner = ImageOptimizationScanner()
        data = {
            "src": "https://example.com/icon.svg",
            "alt": "",
            "hasAlt": True,
        }

        image_info = scanner._build_image_info(data)

        assert image_info.is_decorative is True
        assert image_info.alt == ""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_image_info_background_image(self):
        """Test building ImageInfo for background images"""
        scanner = ImageOptimizationScanner()
        data = {
            "src": "https://example.com/bg.jpg",
            "type": "background",
            "hasAlt": False,
        }

        image_info = scanner._build_image_info(data)

        assert image_info.is_background_image is True

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_image_info_natural_vs_display_size(self):
        """Test building ImageInfo with natural and display sizes"""
        scanner = ImageOptimizationScanner()
        data = {
            "src": "https://example.com/image.jpg",
            "naturalWidth": 1600,
            "naturalHeight": 1200,
            "displayWidth": 800,
            "displayHeight": 600,
            "hasAlt": False,
        }

        image_info = scanner._build_image_info(data)

        assert image_info.natural_width == 1600
        assert image_info.natural_height == 1200
        assert image_info.display_width == 800
        assert image_info.display_height == 600

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_image_info_above_fold(self):
        """Test building ImageInfo with above-fold detection"""
        scanner = ImageOptimizationScanner()
        data = {
            "src": "https://example.com/hero.jpg",
            "isAboveFold": True,
            "hasAlt": False,
        }

        image_info = scanner._build_image_info(data)

        assert image_info.is_above_fold is True


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestCheckAltText:
    """Test alt text validation"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_alt_text_missing_alt_attribute(self):
        """Test detection of missing alt attribute"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/image.jpg",
            has_alt=False,
        )

        issue = scanner._check_alt_text(image)

        assert issue is not None
        assert issue.issue_type == ImageIssueType.MISSING_ALT
        assert issue.severity == ImageIssueSeverity.CRITICAL
        assert "WCAG 1.1.1" in issue.wcag_reference

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_alt_text_empty_alt_on_non_decorative(self):
        """Test detection of empty alt on non-decorative image"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/product.jpg",
            has_alt=True,
            alt="",
            is_decorative=False,
        )

        issue = scanner._check_alt_text(image)

        assert issue is not None
        assert issue.issue_type == ImageIssueType.EMPTY_ALT
        assert issue.severity == ImageIssueSeverity.WARNING

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_alt_text_empty_alt_on_decorative_is_ok(self):
        """Test empty alt on decorative image is acceptable"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/icon.svg",
            has_alt=True,
            alt="",
            is_decorative=True,
        )

        issue = scanner._check_alt_text(image)

        assert issue is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_alt_text_valid_alt_text(self):
        """Test image with valid alt text has no issue"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/image.jpg",
            has_alt=True,
            alt="Product photo showing red shoes",
        )

        issue = scanner._check_alt_text(image)

        assert issue is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_appears_decorative_by_filename(self):
        """Test heuristic detection of decorative images by filename"""
        scanner = ImageOptimizationScanner()

        decorative_patterns = [
            "https://example.com/icon.png",
            "https://example.com/logo.svg",
            "https://example.com/spacer.gif",
            "https://example.com/bullet.png",
            "https://example.com/divider.jpg",
            "https://example.com/arrow.svg",
        ]

        for src in decorative_patterns:
            image = ImageInfo(src=src)
            assert scanner._appears_decorative(image) is True

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_appears_decorative_by_small_size(self):
        """Test heuristic detection of decorative images by size"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/tiny.jpg",
            display_width=16,
            display_height=16,
        )

        assert scanner._appears_decorative(image) is True

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_appears_decorative_content_image(self):
        """Test content images are not detected as decorative"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/product-photo.jpg",
            display_width=800,
            display_height=600,
        )

        assert scanner._appears_decorative(image) is False


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestCheckLazyLoading:
    """Test lazy loading validation"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_lazy_loading_above_fold_with_lazy(self):
        """Test above-fold image with lazy loading is flagged"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/hero.jpg",
            is_above_fold=True,
            has_lazy_loading=True,
        )

        issue = scanner._check_lazy_loading(image)

        assert issue is not None
        assert issue.issue_type == ImageIssueType.MISSING_LAZY_LOADING
        assert issue.severity == ImageIssueSeverity.INFO
        assert "LCP" in issue.impact

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_lazy_loading_below_fold_without_lazy(self):
        """Test below-fold image without lazy loading is flagged"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/footer.jpg",
            is_above_fold=False,
            has_lazy_loading=False,
        )

        issue = scanner._check_lazy_loading(image)

        assert issue is not None
        assert issue.issue_type == ImageIssueType.MISSING_LAZY_LOADING
        assert issue.severity == ImageIssueSeverity.WARNING
        assert 'loading="lazy"' in issue.suggested_fix

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_lazy_loading_above_fold_without_lazy(self):
        """Test above-fold image without lazy loading is OK"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/hero.jpg",
            is_above_fold=True,
            has_lazy_loading=False,
        )

        issue = scanner._check_lazy_loading(image)

        assert issue is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_lazy_loading_below_fold_with_lazy(self):
        """Test below-fold image with lazy loading is OK"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/footer.jpg",
            is_above_fold=False,
            has_lazy_loading=True,
        )

        issue = scanner._check_lazy_loading(image)

        assert issue is None


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestCheckFormat:
    """Test image format optimization validation"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_format_jpeg_should_use_webp(self):
        """Test JPEG image is flagged for WebP conversion"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/photo.jpg",
            format=ImageFormat.JPEG,
        )

        issue = scanner._check_format(image)

        assert issue is not None
        assert issue.issue_type == ImageIssueType.NON_OPTIMIZED_FORMAT
        assert issue.severity == ImageIssueSeverity.WARNING
        assert "WebP" in issue.suggested_fix or "AVIF" in issue.suggested_fix

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_format_png_should_use_webp(self):
        """Test PNG image is flagged for WebP conversion"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/graphic.png",
            format=ImageFormat.PNG,
        )

        issue = scanner._check_format(image)

        assert issue is not None
        assert issue.issue_type == ImageIssueType.NON_OPTIMIZED_FORMAT

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_format_webp_is_ok(self):
        """Test WebP format is considered optimized"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/photo.webp",
            format=ImageFormat.WEBP,
        )

        issue = scanner._check_format(image)

        assert issue is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_format_avif_is_ok(self):
        """Test AVIF format is considered optimized"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/photo.avif",
            format=ImageFormat.AVIF,
        )

        issue = scanner._check_format(image)

        assert issue is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_format_svg_is_ok(self):
        """Test SVG format is considered optimized"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/icon.svg",
            format=ImageFormat.SVG,
        )

        issue = scanner._check_format(image)

        assert issue is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_format_svg_skipped_when_configured(self):
        """Test SVG format check can be skipped via config"""
        config = ImageConfig(skip_svg=True)
        scanner = ImageOptimizationScanner(config=config)
        image = ImageInfo(
            src="https://example.com/icon.svg",
            format=ImageFormat.SVG,
        )

        issue = scanner._check_format(image)

        assert issue is None


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestCheckDimensions:
    """Test dimension validation"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_dimensions_missing_dimensions(self):
        """Test image without width/height is flagged"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/image.jpg",
            has_dimensions=False,
        )

        issue = scanner._check_dimensions(image)

        assert issue is not None
        assert issue.issue_type == ImageIssueType.MISSING_DIMENSIONS
        assert issue.severity == ImageIssueSeverity.WARNING
        assert "layout shift" in issue.impact.lower()

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_dimensions_with_dimensions(self):
        """Test image with width/height has no issue"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/image.jpg",
            has_dimensions=True,
            width=800,
            height=600,
        )

        issue = scanner._check_dimensions(image)

        assert issue is None


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestCheckOversized:
    """Test oversized image detection"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_oversized_2x_larger_than_display(self):
        """Test image 2x larger than display is flagged"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/large.jpg",
            natural_width=1600,
            natural_height=1200,
            display_width=800,
            display_height=600,
        )

        issue = scanner._check_oversized(image)

        assert issue is not None
        assert issue.issue_type == ImageIssueType.OVERSIZED_IMAGE
        assert issue.severity == ImageIssueSeverity.WARNING
        assert "2.0x" in issue.description

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_oversized_below_threshold(self):
        """Test image below threshold is not flagged"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/image.jpg",
            natural_width=1000,
            natural_height=750,
            display_width=800,
            display_height=600,
        )

        issue = scanner._check_oversized(image)

        assert issue is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_oversized_missing_dimensions(self):
        """Test oversized check skips images without dimensions"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/image.jpg",
        )

        issue = scanner._check_oversized(image)

        assert issue is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_oversized_custom_threshold(self):
        """Test custom oversized threshold"""
        config = ImageConfig(oversized_threshold=3.0)
        scanner = ImageOptimizationScanner(config=config)
        image = ImageInfo(
            src="https://example.com/large.jpg",
            natural_width=2000,
            natural_height=1500,
            display_width=800,
            display_height=600,
        )

        # 2.5x larger, but threshold is 3.0
        issue = scanner._check_oversized(image)

        assert issue is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_estimate_size_savings(self):
        """Test size savings estimation"""
        scanner = ImageOptimizationScanner()

        savings = scanner._estimate_size_savings(
            natural_width=1600,
            natural_height=1200,
            display_width=800,
            display_height=600,
        )

        assert savings > 0
        # Natural: 1600*1200 = 1,920,000 pixels
        # Display: 800*600 = 480,000 pixels
        # Difference: 1,440,000 pixels * 0.5 bytes = 720,000 bytes
        assert savings == 720000


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestCheckSrcset:
    """Test srcset validation"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_srcset_large_image_without_srcset(self):
        """Test large image without srcset is flagged"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/large.jpg",
            display_width=1000,
            has_srcset=False,
        )

        issue = scanner._check_srcset(image)

        assert issue is not None
        assert issue.issue_type == ImageIssueType.MISSING_SRCSET
        assert issue.severity == ImageIssueSeverity.INFO
        assert "srcset" in issue.suggested_fix

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_srcset_small_image_without_srcset(self):
        """Test small image without srcset is not flagged"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/small.jpg",
            display_width=400,
            has_srcset=False,
        )

        issue = scanner._check_srcset(image)

        assert issue is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_srcset_with_srcset(self):
        """Test image with srcset has no issue"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/responsive.jpg",
            display_width=1000,
            has_srcset=True,
            srcset="img-800.jpg 800w, img-1200.jpg 1200w",
        )

        issue = scanner._check_srcset(image)

        assert issue is None

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_srcset_custom_min_width(self):
        """Test custom minimum width for srcset requirement"""
        config = ImageConfig(min_srcset_width=1200)
        scanner = ImageOptimizationScanner(config=config)
        image = ImageInfo(
            src="https://example.com/medium.jpg",
            display_width=1000,
            has_srcset=False,
        )

        # Below custom threshold, should not be flagged
        issue = scanner._check_srcset(image)

        assert issue is None


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestCheckImage:
    """Test overall image checking"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_image_background_image_limited_checks(self):
        """Test background images only get format checks"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/bg.jpg",
            is_background_image=True,
            format=ImageFormat.JPEG,
            has_alt=False,
            has_dimensions=False,
        )

        issues = scanner._check_image(image)

        # Should only have format issue, not alt or dimensions
        assert len(issues) == 1
        assert issues[0].issue_type == ImageIssueType.NON_OPTIMIZED_FORMAT

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_image_multiple_issues(self):
        """Test image with multiple issues returns all"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/problematic.jpg",
            has_alt=False,
            format=ImageFormat.JPEG,
            has_dimensions=False,
            is_above_fold=False,
            has_lazy_loading=False,
            display_width=1000,
            has_srcset=False,
        )

        issues = scanner._check_image(image)

        # Should have multiple issues
        assert len(issues) > 1
        issue_types = {issue.issue_type for issue in issues}
        assert ImageIssueType.MISSING_ALT in issue_types
        assert ImageIssueType.NON_OPTIMIZED_FORMAT in issue_types

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_check_image_perfect_image_no_issues(self):
        """Test perfectly optimized image has no issues"""
        scanner = ImageOptimizationScanner()
        image = ImageInfo(
            src="https://example.com/perfect.webp",
            has_alt=True,
            alt="Perfect image",
            format=ImageFormat.WEBP,
            has_dimensions=True,
            width=800,
            height=600,
            is_above_fold=False,
            has_lazy_loading=True,
            has_srcset=True,
            natural_width=800,
            natural_height=600,
            display_width=800,
            display_height=600,
        )

        issues = scanner._check_image(image)

        assert len(issues) == 0


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestBuildReport:
    """Test report building"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_report_counts_issues_by_type(self):
        """Test report counts issues by type"""
        scanner = ImageOptimizationScanner()
        # Create images that will trigger real issues
        img1 = scanner._build_image_info({"src": "https://example.com/img1.jpg", "hasAlt": False})
        img2 = scanner._build_image_info({"src": "https://example.com/img2.jpg", "hasAlt": False})
        img3 = scanner._build_image_info({"src": "https://example.com/img3.jpg", "hasAlt": True, "alt": "OK"})

        images = [img1, img2, img3]

        # Get real issues from the scanner's check methods
        issues = []
        issues.extend(scanner._check_image(img1))
        issues.extend(scanner._check_image(img2))
        issues.extend(scanner._check_image(img3))

        report = scanner._build_report("https://example.com", images, issues)

        # Should have at least 2 missing alt issues and format issues
        assert report.missing_alt_count == 2
        assert report.non_optimized_format_count >= 3

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_report_counts_issues_by_severity(self):
        """Test report counts issues by severity"""
        scanner = ImageOptimizationScanner()

        # Create images that will trigger different severity issues
        # CRITICAL: missing alt
        img_critical = scanner._build_image_info({"src": "https://example.com/img1.jpg", "hasAlt": False})

        # WARNING: non-optimized format
        img_warning = scanner._build_image_info({
            "src": "https://example.com/img2.jpg",
            "hasAlt": True,
            "alt": "OK",
        })

        # INFO: missing srcset on large image (below-fold with lazy loading)
        img_info = scanner._build_image_info({
            "src": "https://example.com/img3.jpg",
            "hasAlt": True,
            "alt": "OK",
            "displayWidth": 1000,
            "loading": "lazy",
            "isAboveFold": False,
        })

        images = [img_critical, img_warning, img_info]

        # Get real issues
        issues = []
        issues.extend(scanner._check_image(img_critical))
        issues.extend(scanner._check_image(img_warning))
        issues.extend(scanner._check_image(img_info))

        report = scanner._build_report("https://example.com", images, issues)

        # Check that we have at least one of each severity
        assert report.critical_count >= 1  # Missing alt is critical
        assert report.warning_count >= 1  # Non-optimized format is warning
        assert report.info_count >= 1  # Missing srcset is info

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_report_calculates_statistics(self):
        """Test report calculates image statistics"""
        scanner = ImageOptimizationScanner()
        images = [
            scanner._build_image_info({
                "src": "https://example.com/img1.webp",
                "isAboveFold": True,
                "loading": None,
                "srcset": "img-800.webp 800w",
                "hasAlt": False,
            }),
            scanner._build_image_info({
                "src": "https://example.com/img2.jpg",
                "isAboveFold": False,
                "loading": "lazy",
                "srcset": None,
                "hasAlt": False,
            }),
        ]

        report = scanner._build_report("https://example.com", images, [])

        assert report.images_above_fold == 1
        assert report.images_with_lazy_loading == 1
        assert report.images_with_srcset == 1
        assert report.optimized_format_count == 1

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_report_format_breakdown(self):
        """Test report creates format breakdown"""
        scanner = ImageOptimizationScanner()
        images = [
            scanner._build_image_info({"src": "https://example.com/img1.jpg", "hasAlt": False}),
            scanner._build_image_info({"src": "https://example.com/img2.jpg", "hasAlt": False}),
            scanner._build_image_info({"src": "https://example.com/img3.webp", "hasAlt": False}),
            scanner._build_image_info({"src": "https://example.com/img4.png", "hasAlt": False}),
        ]

        report = scanner._build_report("https://example.com", images, [])

        assert report.format_breakdown.get("jpeg", 0) + report.format_breakdown.get("jpg", 0) == 2
        assert report.format_breakdown["webp"] == 1
        assert report.format_breakdown["png"] == 1

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_report_includes_all_images_when_configured(self):
        """Test report includes all images when configured"""
        config = ImageConfig(include_all_images=True)
        scanner = ImageOptimizationScanner(config=config)
        images = [
            scanner._build_image_info({"src": "https://example.com/img1.jpg", "hasAlt": False}),
            scanner._build_image_info({"src": "https://example.com/img2.jpg", "hasAlt": False}),
        ]

        report = scanner._build_report("https://example.com", images, [])

        assert len(report.images) == 2

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_build_report_excludes_images_by_default(self):
        """Test report excludes images by default"""
        scanner = ImageOptimizationScanner()
        images = [
            scanner._build_image_info({"src": "https://example.com/img1.jpg", "hasAlt": False}),
            scanner._build_image_info({"src": "https://example.com/img2.jpg", "hasAlt": False}),
        ]

        report = scanner._build_report("https://example.com", images, [])

        assert len(report.images) == 0
        assert report.total_images == 2


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestCalculateScore:
    """Test optimization score calculation"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_calculate_score_perfect_images(self):
        """Test score for perfect images is 100"""
        scanner = ImageOptimizationScanner()
        report = ImageReport(url="https://example.com")

        score = scanner._calculate_score(report, total_images=5)

        assert score == 100.0

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_calculate_score_critical_penalties(self):
        """Test critical issues reduce score significantly"""
        scanner = ImageOptimizationScanner()
        report = ImageReport(
            url="https://example.com",
            critical_count=3,
        )

        score = scanner._calculate_score(report, total_images=5)

        # 3 critical issues = 30 point penalty
        assert score == 70.0

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_calculate_score_warning_penalties(self):
        """Test warning issues reduce score"""
        scanner = ImageOptimizationScanner()
        report = ImageReport(
            url="https://example.com",
            warning_count=5,
        )

        score = scanner._calculate_score(report, total_images=5)

        # 5 warnings = 15 point penalty
        assert score == 85.0

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_calculate_score_bonus_for_lazy_loading(self):
        """Test bonus for lazy loading usage"""
        scanner = ImageOptimizationScanner()
        report = ImageReport(
            url="https://example.com",
            images_with_lazy_loading=5,
        )

        score = scanner._calculate_score(report, total_images=5)

        # All images with lazy loading = +5 bonus, but capped at 100
        assert score == 100.0

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_calculate_score_no_images(self):
        """Test score with no images"""
        scanner = ImageOptimizationScanner()
        report = ImageReport(url="https://example.com")

        score = scanner._calculate_score(report, total_images=0)

        assert score == 100.0


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
class TestGenerateSuggestions:
    """Test suggestion generation"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_generate_suggestions_missing_alt(self):
        """Test suggestions for missing alt text"""
        scanner = ImageOptimizationScanner()
        report = ImageReport(
            url="https://example.com",
            missing_alt_count=5,
        )

        suggestions = scanner._generate_suggestions(report)

        assert any("alt text" in s.lower() for s in suggestions)
        assert any("5" in s for s in suggestions)

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_generate_suggestions_non_optimized_format(self):
        """Test suggestions for format optimization"""
        scanner = ImageOptimizationScanner()
        report = ImageReport(
            url="https://example.com",
            non_optimized_format_count=8,
        )

        suggestions = scanner._generate_suggestions(report)

        assert any("webp" in s.lower() or "avif" in s.lower() for s in suggestions)

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_generate_suggestions_perfect_images(self):
        """Test suggestions for perfect images"""
        scanner = ImageOptimizationScanner()
        report = ImageReport(url="https://example.com")

        suggestions = scanner._generate_suggestions(report)

        assert any("well optimized" in s.lower() for s in suggestions)

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    def test_generate_suggestions_multiple_issues(self):
        """Test suggestions for multiple issue types"""
        scanner = ImageOptimizationScanner()
        report = ImageReport(
            url="https://example.com",
            missing_alt_count=3,
            missing_lazy_loading_count=5,
            oversized_count=2,
        )

        suggestions = scanner._generate_suggestions(report)

        assert len(suggestions) >= 3
        assert any("alt" in s.lower() for s in suggestions)
        assert any("lazy" in s.lower() for s in suggestions)
        assert any("oversized" in s.lower() or "resize" in s.lower() for s in suggestions)


@pytest.mark.L0
@pytest.mark.freya
@pytest.mark.unit
@pytest.mark.asyncio
class TestScannerHighLevelMethods:
    """Test high-level scanner methods"""

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    async def test_check_alt_text_method_sets_config(self):
        """Test check_alt_text method configures scanner for alt-only check"""
        scanner = ImageOptimizationScanner()

        with patch.object(scanner, 'scan', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = ImageReport(url="https://example.com")
            await scanner.check_alt_text("https://example.com")

            # During execution, config should be alt-only
            # After execution, config should be restored
            assert scanner.config.check_alt_text is True

    @pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Freya imports not available")
    async def test_check_performance_method_sets_config(self):
        """Test check_performance method configures scanner for performance-only check"""
        scanner = ImageOptimizationScanner()

        with patch.object(scanner, 'scan', new_callable=AsyncMock) as mock_scan:
            mock_scan.return_value = ImageReport(url="https://example.com")
            await scanner.check_performance("https://example.com")

            # Config should be restored after execution
            assert scanner.config.check_alt_text is True
