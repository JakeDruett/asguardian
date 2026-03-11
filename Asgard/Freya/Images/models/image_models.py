"""
Freya Image Models

Pydantic models for image optimization scanning including
image issues, reports, and configuration.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ImageIssueType(str, Enum):
    """Type of image issue."""
    MISSING_ALT = "missing_alt"
    EMPTY_ALT = "empty_alt"
    MISSING_LAZY_LOADING = "missing_lazy_loading"
    NON_OPTIMIZED_FORMAT = "non_optimized_format"
    MISSING_DIMENSIONS = "missing_dimensions"
    OVERSIZED_IMAGE = "oversized_image"
    MISSING_SRCSET = "missing_srcset"
    DECORATIVE_WITHOUT_EMPTY_ALT = "decorative_without_empty_alt"
    LARGE_FILE_SIZE = "large_file_size"


class ImageIssueSeverity(str, Enum):
    """Severity of image issues."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class ImageFormat(str, Enum):
    """Image format types."""
    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
    AVIF = "avif"
    SVG = "svg"
    ICO = "ico"
    BMP = "bmp"
    TIFF = "tiff"
    UNKNOWN = "unknown"


class ImageInfo(BaseModel):
    """Information about a single image."""
    src: str = Field(..., description="Image source URL")
    alt: Optional[str] = Field(None, description="Alt text if present")
    has_alt: bool = Field(False, description="Whether alt attribute exists")
    width: Optional[int] = Field(None, description="Width attribute value")
    height: Optional[int] = Field(None, description="Height attribute value")
    has_dimensions: bool = Field(False, description="Has both width and height")
    loading: Optional[str] = Field(None, description="Loading attribute value")
    has_lazy_loading: bool = Field(False, description="Has lazy loading")
    srcset: Optional[str] = Field(None, description="Srcset attribute if present")
    has_srcset: bool = Field(False, description="Has srcset for responsive images")
    sizes: Optional[str] = Field(None, description="Sizes attribute if present")
    format: ImageFormat = Field(ImageFormat.UNKNOWN, description="Image format")
    natural_width: Optional[int] = Field(None, description="Natural width in pixels")
    natural_height: Optional[int] = Field(None, description="Natural height in pixels")
    display_width: Optional[int] = Field(None, description="Rendered width in pixels")
    display_height: Optional[int] = Field(None, description="Rendered height in pixels")
    file_size_bytes: Optional[int] = Field(None, description="File size in bytes")
    is_above_fold: bool = Field(False, description="Visible in initial viewport")
    element_html: Optional[str] = Field(None, description="HTML of image element")
    css_selector: Optional[str] = Field(None, description="CSS selector for element")
    is_decorative: bool = Field(False, description="Appears to be decorative")
    is_background_image: bool = Field(
        False, description="Is a CSS background image"
    )


class ImageIssue(BaseModel):
    """An issue found with an image."""
    issue_type: ImageIssueType = Field(..., description="Type of issue")
    severity: ImageIssueSeverity = Field(..., description="Issue severity")
    image_src: str = Field(..., description="Source URL of the image")
    description: str = Field(..., description="Human-readable description")
    suggested_fix: str = Field(..., description="How to fix the issue")
    wcag_reference: Optional[str] = Field(
        None, description="Related WCAG criterion"
    )
    impact: str = Field(..., description="Impact on users/performance")
    element_html: Optional[str] = Field(None, description="HTML snippet")
    css_selector: Optional[str] = Field(None, description="CSS selector")


class ImageReport(BaseModel):
    """Complete image optimization report."""
    url: str = Field(..., description="URL analyzed")
    analyzed_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    analysis_duration_ms: float = Field(0, description="Analysis duration")

    # All images found
    images: List[ImageInfo] = Field(default_factory=list)
    total_images: int = Field(0, description="Total images found")

    # Issues
    issues: List[ImageIssue] = Field(default_factory=list)
    total_issues: int = Field(0, description="Total issues found")

    # Counts by issue type
    missing_alt_count: int = Field(0, description="Images missing alt text")
    empty_alt_count: int = Field(0, description="Images with empty alt")
    missing_lazy_loading_count: int = Field(
        0, description="Below-fold images without lazy loading"
    )
    non_optimized_format_count: int = Field(
        0, description="Images using non-optimized formats"
    )
    missing_dimensions_count: int = Field(
        0, description="Images without width/height"
    )
    oversized_count: int = Field(
        0, description="Images larger than display size"
    )
    missing_srcset_count: int = Field(
        0, description="Images without srcset"
    )

    # Severity counts
    critical_count: int = Field(0, description="Critical issues")
    warning_count: int = Field(0, description="Warning issues")
    info_count: int = Field(0, description="Info issues")

    # Statistics
    total_image_bytes: int = Field(0, description="Total bytes for all images")
    potential_savings_bytes: int = Field(
        0, description="Estimated bytes that could be saved"
    )
    images_above_fold: int = Field(0, description="Images in initial viewport")
    images_with_lazy_loading: int = Field(0, description="Images with lazy loading")
    images_with_srcset: int = Field(0, description="Images with srcset")
    optimized_format_count: int = Field(
        0, description="Images using WebP/AVIF"
    )

    # Format breakdown
    format_breakdown: dict = Field(
        default_factory=dict, description="Count by format"
    )

    # Score and summary
    optimization_score: float = Field(0, description="Score 0-100")
    suggestions: List[str] = Field(
        default_factory=list, description="Optimization suggestions"
    )

    @property
    def has_issues(self) -> bool:
        """Check if there are any issues."""
        return self.total_issues > 0

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical issues."""
        return self.critical_count > 0

    @property
    def has_accessibility_issues(self) -> bool:
        """Check if there are accessibility-related issues."""
        return self.missing_alt_count > 0


class ImageConfig(BaseModel):
    """Configuration for image optimization scanning."""
    # What to check
    check_alt_text: bool = Field(True, description="Check for alt text")
    check_lazy_loading: bool = Field(True, description="Check lazy loading")
    check_formats: bool = Field(True, description="Check image formats")
    check_dimensions: bool = Field(True, description="Check width/height")
    check_oversized: bool = Field(True, description="Check for oversized images")
    check_srcset: bool = Field(True, description="Check for srcset")

    # Thresholds
    oversized_threshold: float = Field(
        1.5, description="Ratio threshold for oversized detection"
    )
    large_file_threshold_kb: int = Field(
        200, description="Large file threshold in KB"
    )
    min_srcset_width: int = Field(
        768, description="Min display width to require srcset"
    )

    # Recommended formats
    recommended_formats: List[str] = Field(
        default_factory=lambda: ["webp", "avif"],
        description="Recommended modern formats"
    )

    # Skip patterns
    skip_data_urls: bool = Field(True, description="Skip data: URLs")
    skip_svg: bool = Field(True, description="Skip SVG images for format checks")
    skip_external_images: bool = Field(
        False, description="Skip external domain images"
    )

    # Above fold detection
    above_fold_height: int = Field(
        800, description="Viewport height for above-fold detection"
    )

    # Output
    output_format: str = Field("text", description="Output format")
    include_all_images: bool = Field(
        False, description="Include images without issues"
    )
