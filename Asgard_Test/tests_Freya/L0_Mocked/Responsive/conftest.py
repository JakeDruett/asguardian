"""
Freya Responsive L0 Tests - Module-Specific Fixtures

Contains fixtures specific to responsive testing.
Shared Playwright mocks are in the parent L0_Mocked/conftest.py.
"""

import pytest


# =============================================================================
# Responsive-Specific Model Fixtures
# =============================================================================

@pytest.fixture
def sample_breakpoint():
    """Sample mobile Breakpoint for testing."""
    from Asgard.Freya.Responsive.models.responsive_models import Breakpoint

    return Breakpoint(
        name="mobile-test",
        width=375,
        height=667,
        is_mobile=True,
        device_scale_factor=2,
    )


@pytest.fixture
def sample_desktop_breakpoint():
    """Sample desktop Breakpoint for testing."""
    from Asgard.Freya.Responsive.models.responsive_models import Breakpoint

    return Breakpoint(
        name="desktop-test",
        width=1920,
        height=1080,
        is_mobile=False,
        device_scale_factor=1,
    )


@pytest.fixture
def sample_tablet_breakpoint():
    """Sample tablet Breakpoint for testing."""
    from Asgard.Freya.Responsive.models.responsive_models import Breakpoint

    return Breakpoint(
        name="tablet-test",
        width=768,
        height=1024,
        is_mobile=True,
        device_scale_factor=2,
    )


@pytest.fixture
def sample_breakpoint_issue():
    """Sample BreakpointIssue for testing."""
    from Asgard.Freya.Responsive.models.responsive_models import (
        BreakpointIssue,
        BreakpointIssueType,
    )

    return BreakpointIssue(
        issue_type=BreakpointIssueType.HORIZONTAL_SCROLL,
        breakpoint="mobile-test",
        viewport_width=375,
        element_selector="div.container",
        description="Element extends beyond viewport",
        severity="serious",
        suggested_fix="Use max-width: 100%",
    )


@pytest.fixture
def sample_touch_target_issue():
    """Sample TouchTargetIssue for testing."""
    from Asgard.Freya.Responsive.models.responsive_models import TouchTargetIssue

    return TouchTargetIssue(
        element_selector="button.small",
        element_type="button",
        width=30.0,
        height=30.0,
        min_required=44,
        description="Button too small (30x30px)",
        severity="serious",
        suggested_fix="Increase to at least 44x44px",
    )


@pytest.fixture
def sample_viewport_issue():
    """Sample ViewportIssue for testing."""
    from Asgard.Freya.Responsive.models.responsive_models import (
        ViewportIssue,
        ViewportIssueType,
    )

    return ViewportIssue(
        issue_type=ViewportIssueType.MISSING_VIEWPORT_META,
        description="Page is missing viewport meta tag",
        severity="critical",
        suggested_fix='Add <meta name="viewport" content="width=device-width, initial-scale=1">',
        wcag_reference="1.4.4",
    )


@pytest.fixture
def sample_mobile_compatibility_issue():
    """Sample MobileCompatibilityIssue for testing."""
    from Asgard.Freya.Responsive.models.responsive_models import (
        MobileCompatibilityIssue,
        MobileCompatibilityIssueType,
    )

    return MobileCompatibilityIssue(
        issue_type=MobileCompatibilityIssueType.FLASH_CONTENT,
        description="Page contains 2 Flash element(s)",
        severity="critical",
        suggested_fix="Replace Flash content with HTML5 alternatives",
        affected_devices=["iphone-14", "pixel-7"],
    )


# =============================================================================
# Responsive-Specific Service Fixtures
# =============================================================================

@pytest.fixture
def breakpoint_tester(temp_output_dir):
    """BreakpointTester service instance for testing."""
    from Asgard.Freya.Responsive.services.breakpoint_tester import BreakpointTester

    return BreakpointTester(output_directory=str(temp_output_dir / "breakpoints"))


@pytest.fixture
def mobile_compatibility_tester():
    """MobileCompatibilityTester service instance for testing."""
    from Asgard.Freya.Responsive.services.mobile_compatibility import MobileCompatibilityTester

    return MobileCompatibilityTester()


@pytest.fixture
def touch_target_validator():
    """TouchTargetValidator service instance for testing."""
    from Asgard.Freya.Responsive.services.touch_target_validator import TouchTargetValidator

    return TouchTargetValidator()


@pytest.fixture
def viewport_tester():
    """ViewportTester service instance for testing."""
    from Asgard.Freya.Responsive.services.viewport_tester import ViewportTester

    return ViewportTester()
