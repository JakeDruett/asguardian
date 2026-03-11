"""
Freya Images Package

Image optimization scanning module.
Detects image issues including accessibility, performance, and best practices.
"""

from Asgard.Freya.Images.models import (
    ImageConfig,
    ImageFormat,
    ImageInfo,
    ImageIssue,
    ImageIssueSeverity,
    ImageIssueType,
    ImageReport,
)
from Asgard.Freya.Images.services import (
    ImageOptimizationScanner,
)

__all__ = [
    # Models
    "ImageConfig",
    "ImageFormat",
    "ImageInfo",
    "ImageIssue",
    "ImageIssueSeverity",
    "ImageIssueType",
    "ImageReport",
    # Services
    "ImageOptimizationScanner",
]
