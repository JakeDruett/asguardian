"""
Freya L0 Mocked Tests - Viewport Tester Service

Tests for ViewportTester service with mocked Playwright dependencies.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from Asgard.Freya.Responsive.models.responsive_models import ViewportIssueType
from Asgard.Freya.Responsive.services.viewport_tester import ViewportTester


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def tester():
    """Create a ViewportTester instance."""
    return ViewportTester()


@pytest.fixture
def mock_page():
    """Create a mock Playwright page."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.evaluate = AsyncMock()
    return page


# =============================================================================
# Test ViewportTester Initialization
# =============================================================================

class TestViewportTesterInit:
    """Tests for ViewportTester initialization."""

    @pytest.mark.L0
    def test_init(self):
        """Test initialization."""
        tester = ViewportTester()
        assert tester is not None


# =============================================================================
# Test ViewportTester.test Method
# =============================================================================

class TestViewportTesterTest:
    """Tests for ViewportTester.test method."""

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.viewport_tester.async_playwright")
    async def test_test_with_valid_viewport_meta(self, mock_playwright, tester):
        """Test with page that has valid viewport meta tag."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=[
            "width=device-width, initial-scale=1",
            375,
            {"sizes": {"16px": 10, "14px": 5}, "minimum": 14.0},
        ])

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await tester.test(url="https://example.com")

        assert report.url == "https://example.com"
        assert report.viewport_meta == "width=device-width, initial-scale=1"
        assert report.has_horizontal_scroll is False
        assert len(report.issues) == 0

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.viewport_tester.async_playwright")
    async def test_test_with_missing_viewport_meta(self, mock_playwright, tester):
        """Test with page missing viewport meta tag."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=[
            None,
            375,
            {"sizes": {}, "minimum": None},
        ])

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await tester.test(url="https://example.com")

        assert report.viewport_meta is None
        missing_issues = [
            i for i in report.issues
            if i.issue_type == ViewportIssueType.MISSING_VIEWPORT_META
        ]
        assert len(missing_issues) == 1
        assert missing_issues[0].severity == "critical"

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.viewport_tester.async_playwright")
    async def test_test_with_horizontal_scroll(self, mock_playwright, tester):
        """Test with page that has horizontal scroll."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=[
            "width=device-width, initial-scale=1",
            450,
            {"sizes": {}, "minimum": None},
        ])

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await tester.test(url="https://example.com", viewport_width=375)

        assert report.content_width == 450
        assert report.has_horizontal_scroll is True
        scroll_issues = [
            i for i in report.issues
            if i.issue_type == ViewportIssueType.CONTENT_WIDER_THAN_VIEWPORT
        ]
        assert len(scroll_issues) == 1

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.viewport_tester.async_playwright")
    async def test_test_with_small_text(self, mock_playwright, tester):
        """Test with page that has small text."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=[
            "width=device-width, initial-scale=1",
            375,
            {"sizes": {"10px": 5, "12px": 3}, "minimum": 10.0},
        ])

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await tester.test(url="https://example.com")

        assert report.minimum_text_size == 10.0
        text_issues = [
            i for i in report.issues
            if i.issue_type == ViewportIssueType.TEXT_TOO_SMALL
        ]
        assert len(text_issues) == 1

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.viewport_tester.async_playwright")
    async def test_test_with_custom_viewport(self, mock_playwright, tester):
        """Test with custom viewport dimensions."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=[
            "width=device-width, initial-scale=1",
            414,
            {"sizes": {}, "minimum": None},
        ])

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await tester.test(
            url="https://example.com",
            viewport_width=414,
            viewport_height=896,
        )

        assert report.viewport_width == 414

        mock_browser.new_context.assert_called_once()
        call_kwargs = mock_browser.new_context.call_args[1]
        assert call_kwargs["viewport"]["width"] == 414
        assert call_kwargs["viewport"]["height"] == 896


# =============================================================================
# Test Helper Methods
# =============================================================================

class TestGetViewportMeta:
    """Tests for _get_viewport_meta method."""

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_get_viewport_meta_exists(self, tester, mock_page):
        """Test getting viewport meta when it exists."""
        mock_page.evaluate = AsyncMock(
            return_value="width=device-width, initial-scale=1"
        )

        result = await tester._get_viewport_meta(mock_page)

        assert result == "width=device-width, initial-scale=1"

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_get_viewport_meta_missing(self, tester, mock_page):
        """Test getting viewport meta when it's missing."""
        mock_page.evaluate = AsyncMock(return_value=None)

        result = await tester._get_viewport_meta(mock_page)

        assert result is None

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_get_viewport_meta_handles_exception(self, tester, mock_page):
        """Test that method handles exceptions gracefully."""
        mock_page.evaluate = AsyncMock(side_effect=Exception("JavaScript error"))

        result = await tester._get_viewport_meta(mock_page)

        assert result is None


class TestAnalyzeViewportMeta:
    """Tests for _analyze_viewport_meta method."""

    @pytest.mark.L0
    def test_analyze_valid_meta(self, tester):
        """Test analyzing valid viewport meta tag."""
        content = "width=device-width, initial-scale=1"

        issues = tester._analyze_viewport_meta(content)

        assert len(issues) == 0

    @pytest.mark.L0
    def test_analyze_fixed_width(self, tester):
        """Test analyzing viewport with fixed width."""
        content = "width=600"

        issues = tester._analyze_viewport_meta(content)

        fixed_width_issues = [
            i for i in issues
            if i.issue_type == ViewportIssueType.FIXED_WIDTH_VIEWPORT
        ]
        assert len(fixed_width_issues) == 1
        assert fixed_width_issues[0].severity == "serious"

    @pytest.mark.L0
    def test_analyze_user_scalable_disabled(self, tester):
        """Test analyzing viewport with user scaling disabled."""
        content = "width=device-width, user-scalable=no"

        issues = tester._analyze_viewport_meta(content)

        scalable_issues = [
            i for i in issues
            if i.issue_type == ViewportIssueType.USER_SCALABLE_DISABLED
        ]
        assert len(scalable_issues) == 1
        assert scalable_issues[0].severity == "serious"
        assert scalable_issues[0].wcag_reference == "1.4.4"

    @pytest.mark.L0
    def test_analyze_user_scalable_zero(self, tester):
        """Test analyzing viewport with user-scalable=0."""
        content = "width=device-width, user-scalable=0"

        issues = tester._analyze_viewport_meta(content)

        scalable_issues = [
            i for i in issues
            if i.issue_type == ViewportIssueType.USER_SCALABLE_DISABLED
        ]
        assert len(scalable_issues) == 1

    @pytest.mark.L0
    def test_analyze_maximum_scale_too_low(self, tester):
        """Test analyzing viewport with maximum scale too low."""
        content = "width=device-width, maximum-scale=1.5"

        issues = tester._analyze_viewport_meta(content)

        scale_issues = [
            i for i in issues
            if i.issue_type == ViewportIssueType.MAXIMUM_SCALE_TOO_LOW
        ]
        assert len(scale_issues) == 1
        assert scale_issues[0].severity == "moderate"

    @pytest.mark.L0
    def test_analyze_maximum_scale_acceptable(self, tester):
        """Test analyzing viewport with acceptable maximum scale."""
        content = "width=device-width, maximum-scale=2.0"

        issues = tester._analyze_viewport_meta(content)

        scale_issues = [
            i for i in issues
            if i.issue_type == ViewportIssueType.MAXIMUM_SCALE_TOO_LOW
        ]
        assert len(scale_issues) == 0

    @pytest.mark.L0
    def test_analyze_multiple_issues(self, tester):
        """Test analyzing viewport with multiple issues."""
        content = "width=600, user-scalable=no, maximum-scale=1.0"

        issues = tester._analyze_viewport_meta(content)

        assert len(issues) == 3

    @pytest.mark.L0
    def test_analyze_handles_spaces(self, tester):
        """Test that analysis handles spaces in content."""
        content1 = "width=device-width, user-scalable=no"
        content2 = "width=device-width,user-scalable=no"

        issues1 = tester._analyze_viewport_meta(content1)
        issues2 = tester._analyze_viewport_meta(content2)

        assert len(issues1) == len(issues2)


class TestAnalyzeTextSizes:
    """Tests for _analyze_text_sizes method."""

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_analyze_text_sizes_success(self, tester, mock_page):
        """Test analyzing text sizes successfully."""
        mock_page.evaluate = AsyncMock(return_value={
            "sizes": {"16px": 10, "14px": 5, "12px": 2},
            "minimum": 12.0,
        })

        result = await tester._analyze_text_sizes(mock_page)

        assert "sizes" in result
        assert "minimum" in result
        assert result["minimum"] == 12.0
        assert len(result["sizes"]) == 3

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_analyze_text_sizes_no_text(self, tester, mock_page):
        """Test analyzing page with no text."""
        mock_page.evaluate = AsyncMock(return_value={
            "sizes": {},
            "minimum": None,
        })

        result = await tester._analyze_text_sizes(mock_page)

        assert result["sizes"] == {}
        assert result["minimum"] is None

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_analyze_text_sizes_handles_exception(self, tester, mock_page):
        """Test that method handles exceptions gracefully."""
        mock_page.evaluate = AsyncMock(side_effect=Exception("JavaScript error"))

        result = await tester._analyze_text_sizes(mock_page)

        assert result == {"sizes": {}, "minimum": None}


# =============================================================================
# Integration Tests
# =============================================================================

class TestViewportTesterIntegration:
    """Integration tests for ViewportTester."""

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.viewport_tester.async_playwright")
    async def test_test_produces_complete_report(self, mock_playwright, tester):
        """Test that test method produces a complete report."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=[
            "width=600, user-scalable=no",
            450,
            {"sizes": {"10px": 5}, "minimum": 10.0},
        ])

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await tester.test(url="https://example.com", viewport_width=375)

        assert report.url == "https://example.com"
        assert report.tested_at is not None
        assert report.viewport_meta == "width=600, user-scalable=no"
        assert report.content_width == 450
        assert report.viewport_width == 375
        assert report.has_horizontal_scroll is True
        assert len(report.issues) > 0
        assert report.has_issues is True

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.viewport_tester.async_playwright")
    async def test_test_closes_browser(self, mock_playwright, tester):
        """Test that test closes browser properly."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=[
            "width=device-width, initial-scale=1",
            375,
            {"sizes": {}, "minimum": None},
        ])

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        await tester.test(url="https://example.com")

        mock_browser.close.assert_called_once()

    @pytest.mark.L0
    @pytest.mark.asyncio
    @patch("Asgard.Freya.Responsive.services.viewport_tester.async_playwright")
    async def test_test_perfect_page(self, mock_playwright, tester):
        """Test validation of a perfect page with no issues."""
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=[
            "width=device-width, initial-scale=1",
            375,
            {"sizes": {"16px": 20, "14px": 10}, "minimum": 14.0},
        ])

        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_p = AsyncMock()
        mock_p.chromium.launch = AsyncMock(return_value=mock_browser)

        mock_playwright.return_value.__aenter__ = AsyncMock(return_value=mock_p)
        mock_playwright.return_value.__aexit__ = AsyncMock()

        report = await tester.test(url="https://example.com")

        assert report.has_issues is False
        assert len(report.issues) == 0


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
