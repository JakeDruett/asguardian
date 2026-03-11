"""
L0 Unit Tests for Freya Accessibility Models

Tests all Pydantic models, enums, and model properties.
"""

import pytest
from datetime import datetime

from Asgard.Freya.Accessibility.models.accessibility_models import (
    WCAGLevel,
    ViolationSeverity,
    AccessibilityCategory,
    TextSize,
    ColorBlindnessType,
    AccessibilityViolation,
    AccessibilityReport,
    AccessibilityConfig,
    ColorInfo,
    ContrastResult,
    ContrastIssue,
    ContrastReport,
    KeyboardIssueType,
    KeyboardIssue,
    KeyboardNavigationReport,
    ARIAViolationType,
    ARIAViolation,
    ARIAReport,
    ScreenReaderIssueType,
    ScreenReaderIssue,
    HeadingInfo,
    ScreenReaderReport,
)


class TestEnums:
    """Test all enum definitions."""

    def test_wcag_level_enum_values(self):
        """Test WCAG level enum has correct values."""
        assert WCAGLevel.A == "A"
        assert WCAGLevel.AA == "AA"
        assert WCAGLevel.AAA == "AAA"

    def test_violation_severity_enum_values(self):
        """Test violation severity enum has correct values."""
        assert ViolationSeverity.CRITICAL == "critical"
        assert ViolationSeverity.SERIOUS == "serious"
        assert ViolationSeverity.MODERATE == "moderate"
        assert ViolationSeverity.MINOR == "minor"
        assert ViolationSeverity.INFO == "info"

    def test_accessibility_category_enum_values(self):
        """Test accessibility category enum has all WCAG principles."""
        assert AccessibilityCategory.PERCEIVABLE == "perceivable"
        assert AccessibilityCategory.OPERABLE == "operable"
        assert AccessibilityCategory.UNDERSTANDABLE == "understandable"
        assert AccessibilityCategory.ROBUST == "robust"
        assert AccessibilityCategory.CONTRAST == "contrast"
        assert AccessibilityCategory.KEYBOARD == "keyboard"
        assert AccessibilityCategory.ARIA == "aria"

    def test_text_size_enum_values(self):
        """Test text size enum for contrast checking."""
        assert TextSize.NORMAL == "normal"
        assert TextSize.LARGE == "large"

    def test_color_blindness_type_enum_values(self):
        """Test color blindness type enum has all types."""
        assert ColorBlindnessType.PROTANOPIA == "protanopia"
        assert ColorBlindnessType.DEUTERANOPIA == "deuteranopia"
        assert ColorBlindnessType.TRITANOPIA == "tritanopia"
        assert ColorBlindnessType.MONOCHROMACY == "monochromacy"

    def test_keyboard_issue_type_enum_values(self):
        """Test keyboard issue type enum."""
        assert KeyboardIssueType.NO_FOCUS_INDICATOR == "no_focus_indicator"
        assert KeyboardIssueType.NOT_FOCUSABLE == "not_focusable"
        assert KeyboardIssueType.FOCUS_TRAP == "focus_trap"
        assert KeyboardIssueType.SKIP_LINK_MISSING == "skip_link_missing"

    def test_aria_violation_type_enum_values(self):
        """Test ARIA violation type enum."""
        assert ARIAViolationType.MISSING_REQUIRED_ATTRIBUTE == "missing_required_attribute"
        assert ARIAViolationType.INVALID_ATTRIBUTE_VALUE == "invalid_attribute_value"
        assert ARIAViolationType.UNSUPPORTED_ROLE == "unsupported_role"
        assert ARIAViolationType.HIDDEN_FOCUSABLE == "hidden_focusable"

    def test_screen_reader_issue_type_enum_values(self):
        """Test screen reader issue type enum."""
        assert ScreenReaderIssueType.MISSING_ALT_TEXT == "missing_alt_text"
        assert ScreenReaderIssueType.MISSING_LABEL == "missing_label"
        assert ScreenReaderIssueType.EMPTY_BUTTON == "empty_button"
        assert ScreenReaderIssueType.MISSING_LANG_ATTRIBUTE == "missing_lang_attribute"


class TestAccessibilityViolation:
    """Test AccessibilityViolation model."""

    def test_violation_creation_with_required_fields(self):
        """Test creating violation with all required fields."""
        violation = AccessibilityViolation(
            id="test-001",
            wcag_reference="1.4.3",
            category=AccessibilityCategory.CONTRAST,
            severity=ViolationSeverity.SERIOUS,
            description="Insufficient color contrast",
            element_selector="div.content",
            suggested_fix="Increase contrast ratio to 4.5:1",
        )

        assert violation.id == "test-001"
        assert violation.wcag_reference == "1.4.3"
        assert violation.category == AccessibilityCategory.CONTRAST
        assert violation.severity == ViolationSeverity.SERIOUS
        assert violation.element_html is None
        assert violation.impact is None

    def test_violation_creation_with_optional_fields(self):
        """Test creating violation with optional fields."""
        violation = AccessibilityViolation(
            id="test-002",
            wcag_reference="4.1.2",
            category=AccessibilityCategory.ARIA,
            severity=ViolationSeverity.CRITICAL,
            description="Invalid ARIA role",
            element_selector='[role="invalid"]',
            suggested_fix="Use valid ARIA role",
            element_html='<div role="invalid">Content</div>',
            impact="Screen readers cannot interpret element",
            help_url="https://example.com/help",
        )

        assert violation.element_html == '<div role="invalid">Content</div>'
        assert violation.impact == "Screen readers cannot interpret element"
        assert violation.help_url == "https://example.com/help"


class TestAccessibilityReport:
    """Test AccessibilityReport model."""

    def test_report_creation_with_defaults(self):
        """Test creating report with default values."""
        report = AccessibilityReport(
            url="https://example.com",
            wcag_level="AA",
        )

        assert report.url == "https://example.com"
        assert report.wcag_level == "AA"
        assert report.score == 100.0
        assert len(report.violations) == 0
        assert len(report.warnings) == 0
        assert report.passed_checks == 0
        assert report.total_checks == 0
        assert isinstance(report.tested_at, str)

    def test_report_has_violations_property(self):
        """Test has_violations property with violations."""
        violation = AccessibilityViolation(
            id="v1",
            wcag_reference="1.1.1",
            category=AccessibilityCategory.IMAGES,
            severity=ViolationSeverity.CRITICAL,
            description="Missing alt text",
            element_selector="img",
            suggested_fix="Add alt attribute",
        )

        report = AccessibilityReport(
            url="https://example.com",
            wcag_level="AA",
            violations=[violation],
        )

        assert report.has_violations is True

    def test_report_has_no_violations(self):
        """Test has_violations property without violations."""
        report = AccessibilityReport(
            url="https://example.com",
            wcag_level="AA",
        )

        assert report.has_violations is False

    def test_report_total_violations_count(self):
        """Test total_violations property."""
        violations = [
            AccessibilityViolation(
                id=f"v{i}",
                wcag_reference="1.1.1",
                category=AccessibilityCategory.IMAGES,
                severity=ViolationSeverity.CRITICAL,
                description="Test",
                element_selector="test",
                suggested_fix="Fix",
            )
            for i in range(5)
        ]

        report = AccessibilityReport(
            url="https://example.com",
            wcag_level="AA",
            violations=violations,
        )

        assert report.total_violations == 5

    def test_report_critical_count(self):
        """Test critical_count property."""
        violations = [
            AccessibilityViolation(
                id="v1",
                wcag_reference="1.1.1",
                category=AccessibilityCategory.IMAGES,
                severity=ViolationSeverity.CRITICAL,
                description="Test",
                element_selector="test",
                suggested_fix="Fix",
            ),
            AccessibilityViolation(
                id="v2",
                wcag_reference="1.1.1",
                category=AccessibilityCategory.IMAGES,
                severity=ViolationSeverity.SERIOUS,
                description="Test",
                element_selector="test",
                suggested_fix="Fix",
            ),
        ]

        report = AccessibilityReport(
            url="https://example.com",
            wcag_level="AA",
            violations=violations,
        )

        assert report.critical_count == 1

    def test_report_severity_counts(self):
        """Test all severity count properties."""
        violations = [
            AccessibilityViolation(
                id="v1",
                wcag_reference="1.1.1",
                category=AccessibilityCategory.IMAGES,
                severity=ViolationSeverity.CRITICAL,
                description="Test",
                element_selector="test",
                suggested_fix="Fix",
            ),
            AccessibilityViolation(
                id="v2",
                wcag_reference="1.1.1",
                category=AccessibilityCategory.IMAGES,
                severity=ViolationSeverity.SERIOUS,
                description="Test",
                element_selector="test",
                suggested_fix="Fix",
            ),
            AccessibilityViolation(
                id="v3",
                wcag_reference="1.1.1",
                category=AccessibilityCategory.IMAGES,
                severity=ViolationSeverity.MODERATE,
                description="Test",
                element_selector="test",
                suggested_fix="Fix",
            ),
            AccessibilityViolation(
                id="v4",
                wcag_reference="1.1.1",
                category=AccessibilityCategory.IMAGES,
                severity=ViolationSeverity.MINOR,
                description="Test",
                element_selector="test",
                suggested_fix="Fix",
            ),
        ]

        report = AccessibilityReport(
            url="https://example.com",
            wcag_level="AA",
            violations=violations,
        )

        assert report.critical_count == 1
        assert report.serious_count == 1
        assert report.moderate_count == 1
        assert report.minor_count == 1


class TestAccessibilityConfig:
    """Test AccessibilityConfig model."""

    def test_config_creation_with_defaults(self):
        """Test config with default values."""
        config = AccessibilityConfig()

        assert config.wcag_level == WCAGLevel.AA
        assert config.check_contrast is True
        assert config.check_keyboard is True
        assert config.check_aria is True
        assert config.min_severity == ViolationSeverity.MINOR
        assert config.output_format == "text"
        assert config.screenshot_on_failure is False

    def test_config_creation_with_custom_values(self):
        """Test config with custom values."""
        config = AccessibilityConfig(
            wcag_level=WCAGLevel.AAA,
            check_contrast=False,
            min_severity=ViolationSeverity.CRITICAL,
            output_format="json",
            screenshot_on_failure=True,
        )

        assert config.wcag_level == WCAGLevel.AAA
        assert config.check_contrast is False
        assert config.min_severity == ViolationSeverity.CRITICAL
        assert config.output_format == "json"
        assert config.screenshot_on_failure is True


class TestContrastModels:
    """Test contrast-related models."""

    def test_color_info_creation(self):
        """Test ColorInfo model creation."""
        color = ColorInfo(
            hex_value="#ffffff",
            rgb=(255, 255, 255),
            luminance=1.0,
        )

        assert color.hex_value == "#ffffff"
        assert color.rgb == (255, 255, 255)
        assert color.luminance == 1.0

    def test_contrast_result_creation(self):
        """Test ContrastResult model creation."""
        result = ContrastResult(
            element_selector="div.text",
            foreground_color="rgb(0, 0, 0)",
            background_color="rgb(255, 255, 255)",
            contrast_ratio=21.0,
            required_ratio=4.5,
            text_size=TextSize.NORMAL,
            font_size_px=16.0,
            font_weight="400",
            is_passing=True,
            wcag_aa_pass=True,
            wcag_aaa_pass=True,
        )

        assert result.contrast_ratio == 21.0
        assert result.is_passing is True
        assert result.wcag_aa_pass is True
        assert result.wcag_aaa_pass is True

    def test_contrast_issue_creation(self):
        """Test ContrastIssue model creation."""
        issue = ContrastIssue(
            element_selector="p.low-contrast",
            foreground_color="rgb(150, 150, 150)",
            background_color="rgb(255, 255, 255)",
            contrast_ratio=2.5,
            required_ratio=4.5,
            text_content="Low contrast text",
            suggested_foreground="#000000",
            suggested_background=None,
        )

        assert issue.contrast_ratio == 2.5
        assert issue.required_ratio == 4.5
        assert issue.suggested_foreground == "#000000"

    def test_contrast_report_creation(self):
        """Test ContrastReport model creation."""
        report = ContrastReport(
            url="https://example.com",
            wcag_level="AA",
            total_elements=10,
            passing_count=8,
            failing_count=2,
            average_contrast=6.5,
        )

        assert report.total_elements == 10
        assert report.passing_count == 8
        assert report.failing_count == 2
        assert report.has_violations is True

    def test_contrast_report_no_violations(self):
        """Test ContrastReport has_violations when passing."""
        report = ContrastReport(
            url="https://example.com",
            wcag_level="AA",
            total_elements=10,
            passing_count=10,
            failing_count=0,
        )

        assert report.has_violations is False


class TestKeyboardModels:
    """Test keyboard navigation models."""

    def test_keyboard_issue_creation(self):
        """Test KeyboardIssue model creation."""
        issue = KeyboardIssue(
            issue_type=KeyboardIssueType.NO_FOCUS_INDICATOR,
            element_selector="button.no-focus",
            description="Button has no visible focus indicator",
            severity=ViolationSeverity.SERIOUS,
            wcag_reference="2.4.7",
            suggested_fix="Add :focus styles to button",
        )

        assert issue.issue_type == KeyboardIssueType.NO_FOCUS_INDICATOR
        assert issue.severity == ViolationSeverity.SERIOUS
        assert issue.wcag_reference == "2.4.7"

    def test_keyboard_navigation_report_creation(self):
        """Test KeyboardNavigationReport model creation."""
        report = KeyboardNavigationReport(
            url="https://example.com",
            total_focusable=20,
            accessible_count=18,
            tab_order=["#link1", "button.submit"],
            has_skip_link=True,
            focus_traps=[],
        )

        assert report.total_focusable == 20
        assert report.accessible_count == 18
        assert report.has_skip_link is True
        assert report.has_issues is False

    def test_keyboard_navigation_report_with_issues(self):
        """Test KeyboardNavigationReport with issues."""
        issue = KeyboardIssue(
            issue_type=KeyboardIssueType.FOCUS_TRAP,
            element_selector=".modal",
            description="Modal traps focus",
            severity=ViolationSeverity.CRITICAL,
            wcag_reference="2.1.2",
            suggested_fix="Add escape mechanism",
        )

        report = KeyboardNavigationReport(
            url="https://example.com",
            total_focusable=10,
            accessible_count=10,
            issues=[issue],
        )

        assert report.has_issues is True
        assert report.issue_count == 1


class TestARIAModels:
    """Test ARIA validation models."""

    def test_aria_violation_creation(self):
        """Test ARIAViolation model creation."""
        violation = ARIAViolation(
            violation_type=ARIAViolationType.MISSING_REQUIRED_ATTRIBUTE,
            element_selector='[role="checkbox"]',
            description="Checkbox missing aria-checked",
            severity=ViolationSeverity.SERIOUS,
            wcag_reference="4.1.2",
            suggested_fix="Add aria-checked attribute",
            aria_attribute="aria-checked",
            role="checkbox",
        )

        assert violation.violation_type == ARIAViolationType.MISSING_REQUIRED_ATTRIBUTE
        assert violation.aria_attribute == "aria-checked"
        assert violation.role == "checkbox"

    def test_aria_report_creation(self):
        """Test ARIAReport model creation."""
        report = ARIAReport(
            url="https://example.com",
            total_aria_elements=15,
            valid_count=13,
            invalid_count=2,
            roles_found={"button": 5, "navigation": 2},
            aria_attributes_used={"aria-label": 10, "aria-hidden": 3},
        )

        assert report.total_aria_elements == 15
        assert report.valid_count == 13
        assert report.invalid_count == 2
        assert report.has_violations is False

    def test_aria_report_with_violations(self):
        """Test ARIAReport with violations."""
        violation = ARIAViolation(
            violation_type=ARIAViolationType.UNSUPPORTED_ROLE,
            element_selector='[role="invalid"]',
            description="Invalid role",
            severity=ViolationSeverity.SERIOUS,
            wcag_reference="4.1.2",
            suggested_fix="Use valid role",
        )

        report = ARIAReport(
            url="https://example.com",
            total_aria_elements=10,
            valid_count=9,
            invalid_count=1,
            violations=[violation],
        )

        assert report.has_violations is True


class TestScreenReaderModels:
    """Test screen reader compatibility models."""

    def test_screen_reader_issue_creation(self):
        """Test ScreenReaderIssue model creation."""
        issue = ScreenReaderIssue(
            issue_type=ScreenReaderIssueType.MISSING_ALT_TEXT,
            element_selector="img.hero",
            description="Image missing alt text",
            severity=ViolationSeverity.CRITICAL,
            wcag_reference="1.1.1",
            suggested_fix="Add descriptive alt text",
            element_html='<img src="hero.jpg" class="hero">',
            accessible_name=None,
        )

        assert issue.issue_type == ScreenReaderIssueType.MISSING_ALT_TEXT
        assert issue.severity == ViolationSeverity.CRITICAL
        assert issue.accessible_name is None

    def test_heading_info_creation(self):
        """Test HeadingInfo model creation."""
        heading = HeadingInfo(
            level=1,
            text="Main Heading",
            element_selector="h1",
        )

        assert heading.level == 1
        assert heading.text == "Main Heading"

    def test_screen_reader_report_creation(self):
        """Test ScreenReaderReport model creation."""
        report = ScreenReaderReport(
            url="https://example.com",
            total_elements=50,
            labeled_count=45,
            missing_labels=5,
            landmark_structure={"main": 1, "navigation": 2, "banner": 1},
            heading_structure=[{"level": 1, "text": "Title", "selector": "h1"}],
            language="en",
        )

        assert report.total_elements == 50
        assert report.labeled_count == 45
        assert report.missing_labels == 5
        assert report.language == "en"
        assert report.has_issues is False

    def test_screen_reader_report_with_issues(self):
        """Test ScreenReaderReport with issues."""
        issue = ScreenReaderIssue(
            issue_type=ScreenReaderIssueType.EMPTY_BUTTON,
            element_selector="button",
            description="Button has no accessible name",
            severity=ViolationSeverity.CRITICAL,
            wcag_reference="4.1.2",
            suggested_fix="Add text or aria-label",
        )

        report = ScreenReaderReport(
            url="https://example.com",
            total_elements=10,
            labeled_count=9,
            missing_labels=1,
            issues=[issue],
        )

        assert report.has_issues is True
