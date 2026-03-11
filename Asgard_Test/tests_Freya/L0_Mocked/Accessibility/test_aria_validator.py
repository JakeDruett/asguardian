"""
L0 Unit Tests for Freya ARIA Validator

Comprehensive tests for ARIA validation with mocked Playwright dependencies.
Tests role validation, attribute validation, parent role requirements, and ID references.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from Asgard.Freya.Accessibility.services.aria_validator import ARIAValidator, VALID_ROLES
from Asgard.Freya.Accessibility.models.accessibility_models import (
    AccessibilityConfig,
    ARIAViolationType,
    ViolationSeverity,
)


class TestARIAValidatorInit:
    """Test ARIAValidator initialization."""

    def test_init_with_config(self, accessibility_config):
        """Test initializing validator with configuration."""
        validator = ARIAValidator(accessibility_config)

        assert validator.config == accessibility_config


class TestValidRoles:
    """Test VALID_ROLES constant."""

    def test_valid_roles_contains_common_roles(self):
        """Test VALID_ROLES includes common ARIA roles."""
        assert "button" in VALID_ROLES
        assert "navigation" in VALID_ROLES
        assert "main" in VALID_ROLES
        assert "banner" in VALID_ROLES
        assert "dialog" in VALID_ROLES
        assert "alert" in VALID_ROLES

    def test_valid_roles_contains_form_roles(self):
        """Test VALID_ROLES includes form-related roles."""
        assert "checkbox" in VALID_ROLES
        assert "radio" in VALID_ROLES
        assert "textbox" in VALID_ROLES
        assert "combobox" in VALID_ROLES

    def test_valid_roles_contains_structural_roles(self):
        """Test VALID_ROLES includes structural roles."""
        assert "article" in VALID_ROLES
        assert "list" in VALID_ROLES
        assert "listitem" in VALID_ROLES
        assert "table" in VALID_ROLES


class TestValidateRoles:
    """Test role validation."""

    @pytest.mark.asyncio
    async def test_validate_roles_with_valid_role(self, accessibility_config, mock_page, mock_element):
        """Test validating element with valid ARIA role."""
        validator = ARIAValidator(accessibility_config)

        mock_element.get_attribute = AsyncMock(return_value="button")
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])
        mock_page.evaluate = AsyncMock(side_effect=["#test", None])

        violations, roles = await validator._validate_roles(mock_page)

        assert len(violations) == 0
        assert roles["button"] == 1

    @pytest.mark.asyncio
    async def test_validate_roles_with_invalid_role(self, accessibility_config, mock_page, mock_element):
        """Test validating element with invalid ARIA role."""
        validator = ARIAValidator(accessibility_config)

        mock_element.get_attribute = AsyncMock(return_value="invalid-role")
        mock_element.evaluate = AsyncMock(return_value="<div role='invalid-role'></div>")
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])
        mock_page.evaluate = AsyncMock(return_value="#test")

        violations, roles = await validator._validate_roles(mock_page)

        assert len(violations) == 1
        assert violations[0].violation_type == ARIAViolationType.UNSUPPORTED_ROLE
        assert violations[0].severity == ViolationSeverity.SERIOUS

    @pytest.mark.asyncio
    async def test_validate_roles_with_multiple_roles(self, accessibility_config, mock_page, mock_element):
        """Test validating element with multiple roles."""
        validator = ARIAValidator(accessibility_config)

        mock_element.get_attribute = AsyncMock(return_value="button navigation")
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])
        mock_page.evaluate = AsyncMock(side_effect=["#test", None])

        violations, roles = await validator._validate_roles(mock_page)

        assert len(violations) == 0
        assert roles["button"] == 1
        assert roles["navigation"] == 1

    @pytest.mark.asyncio
    async def test_validate_roles_handles_exceptions(self, accessibility_config, mock_page):
        """Test role validation handles exceptions gracefully."""
        validator = ARIAValidator(accessibility_config)

        mock_page.query_selector_all = AsyncMock(side_effect=Exception("Test error"))

        violations, roles = await validator._validate_roles(mock_page)

        assert len(violations) == 0
        assert len(roles) == 0


class TestValidateAriaAttributes:
    """Test ARIA attribute validation."""

    @pytest.mark.asyncio
    async def test_validate_valid_aria_attributes(self, accessibility_config, mock_page):
        """Test validating elements with valid ARIA attributes."""
        validator = ARIAValidator(accessibility_config)

        mock_page.evaluate = AsyncMock(return_value=[
            {
                "tag": "div",
                "id": "test",
                "className": "",
                "attrs": {"aria-label": "Test label", "aria-hidden": "false"}
            }
        ])

        violations, attrs = await validator._validate_aria_attributes(mock_page)

        assert len(violations) == 0
        assert attrs["aria-label"] == 1
        assert attrs["aria-hidden"] == 1

    @pytest.mark.asyncio
    async def test_validate_invalid_aria_attribute(self, accessibility_config, mock_page):
        """Test validating element with invalid ARIA attribute."""
        validator = ARIAValidator(accessibility_config)

        mock_page.evaluate = AsyncMock(return_value=[
            {
                "tag": "div",
                "id": "test",
                "className": "",
                "attrs": {"aria-invalid-attr": "value"}
            }
        ])

        violations, attrs = await validator._validate_aria_attributes(mock_page)

        assert len(violations) == 1
        assert violations[0].violation_type == ARIAViolationType.INVALID_ATTRIBUTE_VALUE

    @pytest.mark.asyncio
    async def test_validate_aria_checked_invalid_value(self, accessibility_config, mock_page):
        """Test aria-checked with invalid value."""
        validator = ARIAValidator(accessibility_config)

        mock_page.evaluate = AsyncMock(return_value=[
            {
                "tag": "div",
                "id": "test",
                "className": "",
                "attrs": {"aria-checked": "invalid"}
            }
        ])

        violations, attrs = await validator._validate_aria_attributes(mock_page)

        assert len(violations) == 1
        assert violations[0].violation_type == ARIAViolationType.INVALID_ATTRIBUTE_VALUE
        assert violations[0].severity == ViolationSeverity.SERIOUS

    @pytest.mark.asyncio
    async def test_validate_aria_expanded_valid_values(self, accessibility_config, mock_page):
        """Test aria-expanded with valid values."""
        validator = ARIAValidator(accessibility_config)

        for value in ["true", "false", "mixed"]:
            mock_page.evaluate = AsyncMock(return_value=[
                {
                    "tag": "button",
                    "id": "test",
                    "className": "",
                    "attrs": {"aria-expanded": value}
                }
            ])

            violations, attrs = await validator._validate_aria_attributes(mock_page)

            assert len(violations) == 0

    @pytest.mark.asyncio
    async def test_validate_aria_attributes_handles_exceptions(self, accessibility_config, mock_page):
        """Test attribute validation handles exceptions gracefully."""
        validator = ARIAValidator(accessibility_config)

        mock_page.evaluate = AsyncMock(side_effect=Exception("Test error"))

        violations, attrs = await validator._validate_aria_attributes(mock_page)

        assert len(violations) == 0
        assert len(attrs) == 0


class TestValidateParentRoles:
    """Test parent role validation."""

    @pytest.mark.asyncio
    async def test_validate_option_with_valid_parent(self, accessibility_config, mock_page, mock_element):
        """Test option element with listbox parent."""
        validator = ARIAValidator(accessibility_config)

        mock_element.get_attribute = AsyncMock(return_value="option")
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])
        mock_page.evaluate = AsyncMock(side_effect=[True, "#option"])

        violations = await validator._validate_parent_roles(mock_page)

        assert len(violations) == 0

    @pytest.mark.asyncio
    async def test_validate_option_without_valid_parent(self, accessibility_config, mock_page, mock_element):
        """Test option element without required parent."""
        validator = ARIAValidator(accessibility_config)

        mock_element.get_attribute = AsyncMock(return_value="option")
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])
        mock_page.evaluate = AsyncMock(side_effect=[False, "#option"])

        violations = await validator._validate_parent_roles(mock_page)

        assert len(violations) == 1
        assert violations[0].violation_type == ARIAViolationType.MISSING_PARENT_ROLE
        assert violations[0].severity == ViolationSeverity.SERIOUS

    @pytest.mark.asyncio
    async def test_validate_tab_with_tablist_parent(self, accessibility_config, mock_page, mock_element):
        """Test tab element with tablist parent."""
        validator = ARIAValidator(accessibility_config)

        mock_element.get_attribute = AsyncMock(return_value="tab")
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])
        mock_page.evaluate = AsyncMock(side_effect=[True, "#tab"])

        violations = await validator._validate_parent_roles(mock_page)

        assert len(violations) == 0

    @pytest.mark.asyncio
    async def test_validate_parent_roles_handles_exceptions(self, accessibility_config, mock_page):
        """Test parent role validation handles exceptions gracefully."""
        validator = ARIAValidator(accessibility_config)

        mock_page.query_selector_all = AsyncMock(side_effect=Exception("Test error"))

        violations = await validator._validate_parent_roles(mock_page)

        assert len(violations) == 0


class TestValidateRequiredAttributes:
    """Test required attribute validation."""

    @pytest.mark.asyncio
    async def test_validate_checkbox_with_aria_checked(self, accessibility_config, mock_page, mock_element):
        """Test checkbox with required aria-checked attribute."""
        validator = ARIAValidator(accessibility_config)

        mock_element.get_attribute = AsyncMock(side_effect=["checkbox", "true"])
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])

        violations = await validator._validate_required_attributes(mock_page)

        assert len(violations) == 0

    @pytest.mark.asyncio
    async def test_validate_checkbox_missing_aria_checked(self, accessibility_config, mock_page, mock_element):
        """Test checkbox missing required aria-checked attribute."""
        validator = ARIAValidator(accessibility_config)

        mock_element.get_attribute = AsyncMock(side_effect=["checkbox", None])
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])
        mock_page.evaluate = AsyncMock(return_value="#checkbox")

        violations = await validator._validate_required_attributes(mock_page)

        assert len(violations) >= 1
        assert violations[0].violation_type == ARIAViolationType.MISSING_REQUIRED_ATTRIBUTE
        assert violations[0].aria_attribute in ["aria-checked", "aria-expanded"]

    @pytest.mark.asyncio
    async def test_validate_slider_with_required_attributes(self, accessibility_config, mock_page, mock_element):
        """Test slider with all required attributes."""
        validator = ARIAValidator(accessibility_config)

        mock_element.get_attribute = AsyncMock(side_effect=[
            "slider",
            "50",
            "0",
            "100",
        ])
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])

        violations = await validator._validate_required_attributes(mock_page)

        assert len(violations) == 0

    @pytest.mark.asyncio
    async def test_validate_required_attributes_handles_exceptions(self, accessibility_config, mock_page):
        """Test required attribute validation handles exceptions gracefully."""
        validator = ARIAValidator(accessibility_config)

        mock_page.query_selector_all = AsyncMock(side_effect=Exception("Test error"))

        violations = await validator._validate_required_attributes(mock_page)

        assert len(violations) == 0


class TestValidateHiddenFocusable:
    """Test hidden focusable element validation."""

    @pytest.mark.asyncio
    async def test_validate_aria_hidden_with_focusable_content(self, accessibility_config, mock_page, mock_element):
        """Test aria-hidden element containing focusable content."""
        validator = ARIAValidator(accessibility_config)

        mock_focusable = AsyncMock()
        mock_element.query_selector = AsyncMock(return_value=mock_focusable)
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])
        mock_page.evaluate = AsyncMock(return_value="#hidden")

        violations = await validator._validate_hidden_focusable(mock_page)

        assert len(violations) == 1
        assert violations[0].violation_type == ARIAViolationType.HIDDEN_FOCUSABLE
        assert violations[0].severity == ViolationSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_validate_aria_hidden_without_focusable_content(self, accessibility_config, mock_page, mock_element):
        """Test aria-hidden element without focusable content."""
        validator = ARIAValidator(accessibility_config)

        mock_element.query_selector = AsyncMock(return_value=None)
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])

        violations = await validator._validate_hidden_focusable(mock_page)

        assert len(violations) == 0

    @pytest.mark.asyncio
    async def test_validate_hidden_focusable_handles_exceptions(self, accessibility_config, mock_page):
        """Test hidden focusable validation handles exceptions gracefully."""
        validator = ARIAValidator(accessibility_config)

        mock_page.query_selector_all = AsyncMock(side_effect=Exception("Test error"))

        violations = await validator._validate_hidden_focusable(mock_page)

        assert len(violations) == 0


class TestValidateAriaIds:
    """Test ARIA ID reference validation."""

    @pytest.mark.asyncio
    async def test_validate_aria_labelledby_existing_id(self, accessibility_config, mock_page, mock_element):
        """Test aria-labelledby referencing existing ID."""
        validator = ARIAValidator(accessibility_config)

        mock_element.get_attribute = AsyncMock(side_effect=["label1", None, None, None])
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])
        mock_page.evaluate = AsyncMock(return_value=True)

        violations = await validator._validate_aria_ids(mock_page)

        assert len(violations) == 0

    @pytest.mark.asyncio
    async def test_validate_aria_labelledby_nonexistent_id(self, accessibility_config, mock_page, mock_element):
        """Test aria-labelledby referencing non-existent ID."""
        validator = ARIAValidator(accessibility_config)

        mock_element.get_attribute = AsyncMock(side_effect=["nonexistent", None, None, None])
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])
        mock_page.evaluate = AsyncMock(side_effect=[False, "#element"])

        violations = await validator._validate_aria_ids(mock_page)

        assert len(violations) == 1
        assert violations[0].violation_type == ARIAViolationType.INVALID_ATTRIBUTE_VALUE
        assert "nonexistent" in violations[0].description

    @pytest.mark.asyncio
    async def test_validate_multiple_id_references(self, accessibility_config, mock_page, mock_element):
        """Test aria-labelledby with multiple ID references."""
        validator = ARIAValidator(accessibility_config)

        mock_element.get_attribute = AsyncMock(side_effect=["id1 id2 id3", None, None, None])
        mock_page.query_selector_all = AsyncMock(return_value=[mock_element])
        mock_page.evaluate = AsyncMock(return_value=True)

        violations = await validator._validate_aria_ids(mock_page)

        assert len(violations) == 0

    @pytest.mark.asyncio
    async def test_validate_aria_ids_handles_exceptions(self, accessibility_config, mock_page):
        """Test ARIA ID validation handles exceptions gracefully."""
        validator = ARIAValidator(accessibility_config)

        mock_page.query_selector_all = AsyncMock(side_effect=Exception("Test error"))

        violations = await validator._validate_aria_ids(mock_page)

        assert len(violations) == 0


class TestGetSelector:
    """Test selector generation."""

    @pytest.mark.asyncio
    async def test_get_selector_with_id(self, accessibility_config, mock_page, mock_element):
        """Test generating selector for element with ID."""
        validator = ARIAValidator(accessibility_config)

        mock_page.evaluate = AsyncMock(return_value="#test-id")

        selector = await validator._get_selector(mock_page, mock_element)

        assert selector == "#test-id"

    @pytest.mark.asyncio
    async def test_get_selector_with_role(self, accessibility_config, mock_page, mock_element):
        """Test generating selector for element with role."""
        validator = ARIAValidator(accessibility_config)

        mock_page.evaluate = AsyncMock(return_value='[role="button"]')

        selector = await validator._get_selector(mock_page, mock_element)

        assert selector == '[role="button"]'

    @pytest.mark.asyncio
    async def test_get_selector_handles_exception(self, accessibility_config, mock_page, mock_element):
        """Test selector generation handles exceptions."""
        validator = ARIAValidator(accessibility_config)

        mock_page.evaluate = AsyncMock(side_effect=Exception("Test error"))

        selector = await validator._get_selector(mock_page, mock_element)

        assert selector == "unknown"


class TestBuildSelector:
    """Test selector building from element data."""

    def test_build_selector_with_id(self, accessibility_config):
        """Test building selector with ID."""
        validator = ARIAValidator(accessibility_config)

        selector = validator._build_selector({"id": "test-id", "tag": "div"})

        assert selector == "#test-id"

    def test_build_selector_with_classes(self, accessibility_config):
        """Test building selector with classes."""
        validator = ARIAValidator(accessibility_config)

        selector = validator._build_selector({"tag": "div", "className": "class1 class2 class3"})

        assert selector == "div.class1.class2"

    def test_build_selector_tag_only(self, accessibility_config):
        """Test building selector with tag only."""
        validator = ARIAValidator(accessibility_config)

        selector = validator._build_selector({"tag": "span", "className": ""})

        assert selector == "span"


class TestFullValidation:
    """Test complete ARIA validation."""

    @pytest.mark.asyncio
    async def test_validate_complete_flow(self, accessibility_config, test_url):
        """Test complete validation flow."""
        validator = ARIAValidator(accessibility_config)

        with patch('Asgard.Freya.Accessibility.services.aria_validator.async_playwright') as mock_pw:
            mock_context = AsyncMock()
            mock_browser = AsyncMock()
            mock_page = AsyncMock()

            mock_page.goto = AsyncMock()
            mock_page.query_selector_all = AsyncMock(return_value=[])
            mock_page.evaluate = AsyncMock(side_effect=[[], 0])
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()
            mock_browser.is_connected = MagicMock(return_value=False)
            mock_context.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_context)
            mock_pw.return_value.__aexit__ = AsyncMock()

            report = await validator.validate(test_url)

            assert report.url == test_url
            assert isinstance(report.tested_at, str)
            assert report.total_aria_elements >= 0
            assert report.valid_count >= 0

    @pytest.mark.asyncio
    async def test_validate_report_has_violations_property(self, accessibility_config, test_url):
        """Test report has_violations property."""
        validator = ARIAValidator(accessibility_config)

        with patch('Asgard.Freya.Accessibility.services.aria_validator.async_playwright') as mock_pw:
            mock_context = AsyncMock()
            mock_browser = AsyncMock()
            mock_page = AsyncMock()

            mock_page.goto = AsyncMock()
            mock_page.query_selector_all = AsyncMock(return_value=[])
            mock_page.evaluate = AsyncMock(side_effect=[[], 0])
            mock_browser.new_page = AsyncMock(return_value=mock_page)
            mock_browser.close = AsyncMock()
            mock_browser.is_connected = MagicMock(return_value=False)
            mock_context.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_pw.return_value.__aenter__ = AsyncMock(return_value=mock_context)
            mock_pw.return_value.__aexit__ = AsyncMock()

            report = await validator.validate(test_url)

            assert report.has_violations is False
