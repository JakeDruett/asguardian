"""
Freya Accessibility L0 Tests - Module-Specific Fixtures

Contains fixtures specific to accessibility testing.
Shared Playwright mocks are in the parent L0_Mocked/conftest.py.
"""

import pytest
from unittest.mock import AsyncMock


# =============================================================================
# Accessibility-Specific Fixtures
# =============================================================================

@pytest.fixture
def accessibility_config():
    """Create a default AccessibilityConfig for testing."""
    from Asgard.Freya.Accessibility.models.accessibility_models import (
        AccessibilityConfig,
        WCAGLevel,
        ViolationSeverity,
    )

    return AccessibilityConfig(
        wcag_level=WCAGLevel.AA,
        check_contrast=True,
        check_keyboard=True,
        check_aria=True,
        check_forms=True,
        check_images=True,
        check_links=True,
        check_structure=True,
        check_language=True,
        min_severity=ViolationSeverity.MINOR,
        output_format="text",
        screenshot_on_failure=False,
        include_element_html=True,
    )


@pytest.fixture
def accessibility_config_strict():
    """Create a strict AccessibilityConfig for AAA compliance testing."""
    from Asgard.Freya.Accessibility.models.accessibility_models import (
        AccessibilityConfig,
        WCAGLevel,
        ViolationSeverity,
    )

    return AccessibilityConfig(
        wcag_level=WCAGLevel.AAA,
        check_contrast=True,
        check_keyboard=True,
        check_aria=True,
        check_forms=True,
        check_images=True,
        check_links=True,
        check_structure=True,
        check_language=True,
        min_severity=ViolationSeverity.MINOR,
        output_format="text",
        screenshot_on_failure=True,
        include_element_html=True,
    )


@pytest.fixture
def sample_violation():
    """Create a sample accessibility violation for testing."""
    from Asgard.Freya.Accessibility.models.accessibility_models import (
        AccessibilityViolation,
        ViolationSeverity,
    )

    return AccessibilityViolation(
        rule_id="color-contrast",
        severity=ViolationSeverity.SERIOUS,
        description="Element has insufficient color contrast",
        element_selector="p.low-contrast",
        element_html='<p class="low-contrast">Sample text</p>',
        wcag_criteria=["1.4.3"],
        help_url="https://www.w3.org/WAI/WCAG21/Understanding/contrast-minimum.html",
        suggested_fix="Increase contrast ratio to at least 4.5:1",
    )


@pytest.fixture
def mock_focusable_elements():
    """Create mock focusable elements for keyboard testing."""
    elements = []
    for i, tag in enumerate(["button", "a", "input", "select"]):
        element = AsyncMock()
        element.get_attribute = AsyncMock(side_effect=lambda attr, t=tag: t if attr == "tagName" else None)
        element.evaluate = AsyncMock(return_value=True)
        element.bounding_box = AsyncMock(return_value={"x": i * 50, "y": 10, "width": 40, "height": 30})
        element.focus = AsyncMock()
        elements.append(element)
    return elements


@pytest.fixture
def mock_image_elements():
    """Create mock image elements for image accessibility testing."""
    elements = []
    for i, alt in enumerate(["Image description", "", None]):
        element = AsyncMock()
        element.get_attribute = AsyncMock(side_effect=lambda attr, a=alt: a if attr == "alt" else None)
        element.evaluate = AsyncMock(return_value={"src": f"image{i}.jpg", "alt": alt})
        elements.append(element)
    return elements
