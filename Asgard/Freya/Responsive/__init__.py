"""
Freya Responsive Module

Responsive design testing including breakpoint validation,
touch target sizing, viewport behavior, and mobile compatibility.

Components:
- BreakpointTester: Test layouts across different breakpoints
- TouchTargetValidator: Validate touch target sizes
- ViewportTester: Test viewport behavior and meta tags
- MobileCompatibilityTester: Test mobile device compatibility

Usage:
    from Asgard.Freya.Responsive import BreakpointTester, COMMON_BREAKPOINTS

    tester = BreakpointTester()
    result = await tester.test("https://example.com", COMMON_BREAKPOINTS)

    for breakpoint, issues in result.breakpoint_issues.items():
        print(f"{breakpoint}: {len(issues)} issues")
"""

from Asgard.Freya.Responsive.models.responsive_models import (
    Breakpoint,
    BreakpointIssue,
    BreakpointIssueType,
    BreakpointReport,
    BreakpointTestResult,
    TouchTargetIssue,
    TouchTargetReport,
    ViewportIssue,
    ViewportIssueType,
    ViewportReport,
    MobileCompatibilityIssue,
    MobileCompatibilityIssueType,
    MobileCompatibilityReport,
    COMMON_BREAKPOINTS,
    MOBILE_DEVICES,
)

from Asgard.Freya.Responsive.services.breakpoint_tester import BreakpointTester
from Asgard.Freya.Responsive.services.touch_target_validator import TouchTargetValidator
from Asgard.Freya.Responsive.services.viewport_tester import ViewportTester
from Asgard.Freya.Responsive.services.mobile_compatibility import MobileCompatibilityTester

__all__ = [
    # Services
    "BreakpointTester",
    "TouchTargetValidator",
    "ViewportTester",
    "MobileCompatibilityTester",
    # Models
    "Breakpoint",
    "BreakpointIssue",
    "BreakpointIssueType",
    "BreakpointReport",
    "BreakpointTestResult",
    "TouchTargetIssue",
    "TouchTargetReport",
    "ViewportIssue",
    "ViewportIssueType",
    "ViewportReport",
    "MobileCompatibilityIssue",
    "MobileCompatibilityIssueType",
    "MobileCompatibilityReport",
    "COMMON_BREAKPOINTS",
    "MOBILE_DEVICES",
]
