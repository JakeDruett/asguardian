"""
Freya Visual Module

Visual testing capabilities including screenshot capture,
visual regression testing, layout validation, and style checking.

Components:
- ScreenshotCapture: Full-page and element screenshots with device emulation
- VisualRegressionTester: Compare screenshots and detect visual differences
- LayoutValidator: Validate element positioning and alignment
- StyleValidator: Check style consistency against design tokens

Usage:
    from Asgard.Freya.Visual import ScreenshotCapture, VisualRegressionTester

    capture = ScreenshotCapture()
    await capture.capture_full_page("https://example.com", "homepage.png")

    regression = VisualRegressionTester()
    result = await regression.compare("baseline.png", "current.png")
"""

from Asgard.Freya.Visual.models.visual_models import (
    ScreenshotConfig,
    DeviceConfig,
    ScreenshotResult,
    ComparisonMethod,
    DifferenceType,
    DifferenceRegion,
    VisualComparisonResult,
    RegressionTestSuite,
    RegressionReport,
    LayoutIssue,
    LayoutIssueType,
    LayoutReport,
    StyleIssue,
    StyleIssueType,
    StyleReport,
)

from Asgard.Freya.Visual.services.screenshot_capture import ScreenshotCapture
from Asgard.Freya.Visual.services.visual_regression import VisualRegressionTester
from Asgard.Freya.Visual.services.layout_validator import LayoutValidator
from Asgard.Freya.Visual.services.style_validator import StyleValidator

__all__ = [
    # Services
    "ScreenshotCapture",
    "VisualRegressionTester",
    "LayoutValidator",
    "StyleValidator",
    # Models
    "ScreenshotConfig",
    "DeviceConfig",
    "ScreenshotResult",
    "ComparisonMethod",
    "DifferenceType",
    "DifferenceRegion",
    "VisualComparisonResult",
    "RegressionTestSuite",
    "RegressionReport",
    "LayoutIssue",
    "LayoutIssueType",
    "LayoutReport",
    "StyleIssue",
    "StyleIssueType",
    "StyleReport",
]
