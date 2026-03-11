"""
Freya L0 Mocked Tests - Touch Target Validator Service

Tests for TouchTargetValidator service with mocked Playwright dependencies.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from Asgard.Freya.Responsive.services.touch_target_validator import TouchTargetValidator


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def validator():
    """Create a TouchTargetValidator instance with default settings."""
    return TouchTargetValidator()


@pytest.fixture
def custom_validator():
    """Create a TouchTargetValidator instance with custom minimum size."""
    return TouchTargetValidator(min_touch_size=48)


@pytest.fixture
def mock_page():
    """Create a mock Playwright page."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.evaluate = AsyncMock()
    page.query_selector = AsyncMock()
    return page


@pytest.fixture
def mock_element():
    """Create a mock Playwright element."""
    element = AsyncMock()
    element.bounding_box = AsyncMock()
    element.evaluate = AsyncMock()
    return element


# =============================================================================
# Test TouchTargetValidator Initialization
# =============================================================================

class TestTouchTargetValidatorInit:
    """Tests for TouchTargetValidator initialization."""

    @pytest.mark.L0
    def test_init_default_min_size(self):
        """Test initialization with default minimum touch size."""
        validator = TouchTargetValidator()
        assert validator.min_touch_size == 44

    @pytest.mark.L0
    def test_init_custom_min_size(self):
        """Test initialization with custom minimum touch size."""
        validator = TouchTargetValidator(min_touch_size=48)
        assert validator.min_touch_size == 48


# =============================================================================
# Test TouchTargetValidator.validate Method
# =============================================================================

class TestTouchTargetValidatorValidate:
    """Tests for TouchTargetValidator.validate method."""

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.touch_target_validator.async_playwright")
    async def test_validate_all_elements_pass(self, mock_playwright, validator):
        """Test validation when all elements meet size requirements."""
        elements_data = [
            {
                "selector": "button.submit",
                "type": "button",
                "role": None,
                "width": 50,
                "height": 50,
                "text": "Submit",
            },
            {
                "selector": "a.link",
                "type": "a",
                "role": None,
                "width": 60,
                "height": 44,
                "text": "Click here",
            },
        ]

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=elements_data)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await validator.validate(url="https://example.com")

        assert report.url == "https://example.com"
        assert report.total_interactive_elements == 2
        assert report.passing_count == 2
        assert report.failing_count == 0
        assert len(report.issues) == 0

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.touch_target_validator.async_playwright")
    async def test_validate_some_elements_fail(self, mock_playwright, validator):
        """Test validation when some elements are too small."""
        elements_data = [
            {
                "selector": "button.submit",
                "type": "button",
                "role": None,
                "width": 50,
                "height": 50,
                "text": "Submit",
            },
            {
                "selector": "a.small-link",
                "type": "a",
                "role": None,
                "width": 30,
                "height": 30,
                "text": "Small",
            },
        ]

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=elements_data)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await validator.validate(url="https://example.com")

        assert report.total_interactive_elements == 2
        assert report.passing_count == 1
        assert report.failing_count == 1
        assert len(report.issues) == 1
        assert report.issues[0].element_selector == "a.small-link"

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.touch_target_validator.async_playwright")
    async def test_validate_custom_viewport(self, mock_playwright, validator):
        """Test validation with custom viewport dimensions."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[])

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await validator.validate(
            url="https://example.com",
            viewport_width=414,
            viewport_height=896,
        )

        assert report.viewport_width == 414
        assert report.viewport_height == 896

        mock_browser.new_context.assert_called_once()
        call_kwargs = mock_browser.new_context.call_args[1]
        assert call_kwargs["viewport"]["width"] == 414
        assert call_kwargs["viewport"]["height"] == 896

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.touch_target_validator.async_playwright")
    async def test_validate_severity_levels(self, mock_playwright, validator):
        """Test that severity levels are assigned correctly based on size."""
        elements_data = [
            {
                "selector": "button.critical",
                "type": "button",
                "role": None,
                "width": 20,
                "height": 20,
                "text": "Critical",
            },
            {
                "selector": "button.serious",
                "type": "button",
                "role": None,
                "width": 28,
                "height": 28,
                "text": "Serious",
            },
            {
                "selector": "button.moderate",
                "type": "button",
                "role": None,
                "width": 40,
                "height": 40,
                "text": "Moderate",
            },
        ]

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=elements_data)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await validator.validate(url="https://example.com")

        assert len(report.issues) == 3
        severities = {issue.element_selector: issue.severity for issue in report.issues}
        assert severities["button.critical"] == "critical"
        assert severities["button.serious"] == "serious"
        assert severities["button.moderate"] == "moderate"

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.touch_target_validator.async_playwright")
    async def test_validate_uses_role_when_present(self, mock_playwright, validator):
        """Test that element role is used as type when available."""
        elements_data = [
            {
                "selector": "div.button",
                "type": "div",
                "role": "button",
                "width": 30,
                "height": 30,
                "text": "Click",
            },
        ]

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=elements_data)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await validator.validate(url="https://example.com")

        assert len(report.issues) == 1
        assert report.issues[0].element_type == "button"

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.touch_target_validator.async_playwright")
    async def test_validate_skips_hidden_elements(self, mock_playwright, validator):
        """Test that hidden elements are not included in validation."""
        elements_data = []

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=elements_data)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await validator.validate(url="https://example.com")

        assert report.total_interactive_elements == 0


# =============================================================================
# Test TouchTargetValidator.validate_element Method
# =============================================================================

class TestTouchTargetValidatorValidateElement:
    """Tests for TouchTargetValidator.validate_element method."""

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_element_passes(self, validator, mock_page, mock_element):
        """Test validating an element that meets size requirements."""
        mock_element.bounding_box = AsyncMock(return_value={
            "x": 0,
            "y": 0,
            "width": 50,
            "height": 50,
        })
        mock_element.evaluate = AsyncMock(return_value="button")
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        result = await validator.validate_element(mock_page, "button.submit")

        assert result is None

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_element_fails(self, validator, mock_page, mock_element):
        """Test validating an element that is too small."""
        mock_element.bounding_box = AsyncMock(return_value={
            "x": 0,
            "y": 0,
            "width": 30,
            "height": 30,
        })
        mock_element.evaluate = AsyncMock(return_value="button")
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        result = await validator.validate_element(mock_page, "button.small")

        assert result is not None
        assert result.element_selector == "button.small"
        assert result.element_type == "button"
        assert result.width == 30
        assert result.height == 30

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_element_not_found(self, validator, mock_page):
        """Test validating a non-existent element."""
        mock_page.query_selector = AsyncMock(return_value=None)

        result = await validator.validate_element(mock_page, "button.missing")

        assert result is None

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_element_no_bounding_box(self, validator, mock_page, mock_element):
        """Test validating an element with no bounding box."""
        mock_element.bounding_box = AsyncMock(return_value=None)
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        result = await validator.validate_element(mock_page, "button.invisible")

        assert result is None

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_element_with_custom_validator(
        self, custom_validator, mock_page, mock_element
    ):
        """Test validating element with custom minimum size."""
        mock_element.bounding_box = AsyncMock(return_value={
            "x": 0,
            "y": 0,
            "width": 46,
            "height": 46,
        })
        mock_element.evaluate = AsyncMock(return_value="button")
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        result = await custom_validator.validate_element(mock_page, "button.medium")

        assert result is not None
        assert result.min_required == 48


# =============================================================================
# Integration Tests
# =============================================================================

class TestTouchTargetValidatorIntegration:
    """Integration tests for TouchTargetValidator."""

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.touch_target_validator.async_playwright")
    async def test_validate_produces_complete_report(self, mock_playwright, validator):
        """Test that validate produces a complete report."""
        elements_data = [
            {
                "selector": "button.good",
                "type": "button",
                "role": None,
                "width": 50,
                "height": 50,
                "text": "Good",
            },
            {
                "selector": "button.bad",
                "type": "button",
                "role": None,
                "width": 30,
                "height": 30,
                "text": "Bad",
            },
            {
                "selector": "a.good",
                "type": "a",
                "role": None,
                "width": 44,
                "height": 44,
                "text": "Link",
            },
        ]

        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=elements_data)

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await validator.validate(url="https://example.com")

        assert report.url == "https://example.com"
        assert report.tested_at is not None
        assert report.total_interactive_elements == 3
        assert report.passing_count == 2
        assert report.failing_count == 1
        assert len(report.issues) == 1
        assert report.min_touch_size == 44
        assert report.has_issues is True

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.touch_target_validator.async_playwright")
    async def test_validate_closes_browser(self, mock_playwright, validator):
        """Test that validate closes the browser properly."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[])

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        await validator.validate(url="https://example.com")

        mock_browser.close.assert_called_once()

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.touch_target_validator.async_playwright")
    async def test_validate_with_no_interactive_elements(self, mock_playwright, validator):
        """Test validation of page with no interactive elements."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=[])

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await validator.validate(url="https://example.com")

        assert report.total_interactive_elements == 0
        assert report.passing_count == 0
        assert report.failing_count == 0
        assert report.has_issues is False


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
