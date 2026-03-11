"""
Freya Accessibility Models

Pydantic models for accessibility testing results and configurations.
Based on WCAG 2.1 guidelines.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


class WCAGLevel(str, Enum):
    """WCAG conformance levels."""
    A = "A"
    AA = "AA"
    AAA = "AAA"


class ViolationSeverity(str, Enum):
    """Severity levels for accessibility violations."""
    CRITICAL = "critical"
    SERIOUS = "serious"
    MODERATE = "moderate"
    MINOR = "minor"
    INFO = "info"


class AccessibilityCategory(str, Enum):
    """Categories of accessibility requirements."""
    PERCEIVABLE = "perceivable"
    OPERABLE = "operable"
    UNDERSTANDABLE = "understandable"
    ROBUST = "robust"
    CONTRAST = "contrast"
    KEYBOARD = "keyboard"
    ARIA = "aria"
    FORMS = "forms"
    IMAGES = "images"
    LINKS = "links"
    STRUCTURE = "structure"
    LANGUAGE = "language"
    NAVIGATION = "navigation"


class TextSize(str, Enum):
    """Text size categories for contrast requirements."""
    NORMAL = "normal"
    LARGE = "large"


class ColorBlindnessType(str, Enum):
    """Types of color vision deficiency."""
    PROTANOPIA = "protanopia"
    DEUTERANOPIA = "deuteranopia"
    TRITANOPIA = "tritanopia"
    PROTANOMALY = "protanomaly"
    DEUTERANOMALY = "deuteranomaly"
    TRITANOMALY = "tritanomaly"
    MONOCHROMACY = "monochromacy"


class AccessibilityViolation(BaseModel):
    """A single accessibility violation."""
    id: str = Field(..., description="Unique violation ID")
    wcag_reference: str = Field(..., description="WCAG success criterion (e.g., '1.4.3')")
    category: AccessibilityCategory = Field(..., description="Violation category")
    severity: ViolationSeverity = Field(..., description="Severity level")
    description: str = Field(..., description="Description of the violation")
    element_selector: str = Field(..., description="CSS selector for the element")
    element_html: Optional[str] = Field(None, description="HTML snippet of the element")
    suggested_fix: str = Field(..., description="Suggested remediation")
    impact: Optional[str] = Field(None, description="Impact on users")
    help_url: Optional[str] = Field(None, description="URL to documentation")


class AccessibilityReport(BaseModel):
    """Complete accessibility report for a page."""
    url: str = Field(..., description="URL that was tested")
    wcag_level: str = Field(..., description="WCAG conformance level tested")
    tested_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    score: float = Field(100.0, description="Accessibility score (0-100)")
    violations: List[AccessibilityViolation] = Field(default_factory=list)
    warnings: List[AccessibilityViolation] = Field(default_factory=list)
    notices: List[AccessibilityViolation] = Field(default_factory=list)
    passed_checks: int = Field(0, description="Number of passed checks")
    total_checks: int = Field(0, description="Total number of checks")

    @property
    def has_violations(self) -> bool:
        """Check if there are any violations."""
        return len(self.violations) > 0

    @property
    def total_violations(self) -> int:
        """Total number of violations."""
        return len(self.violations)

    @property
    def critical_count(self) -> int:
        """Count of critical violations."""
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.CRITICAL)

    @property
    def serious_count(self) -> int:
        """Count of serious violations."""
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.SERIOUS)

    @property
    def moderate_count(self) -> int:
        """Count of moderate violations."""
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.MODERATE)

    @property
    def minor_count(self) -> int:
        """Count of minor violations."""
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.MINOR)


class AccessibilityConfig(BaseModel):
    """Configuration for accessibility testing."""
    wcag_level: WCAGLevel = Field(WCAGLevel.AA, description="WCAG conformance level")
    check_contrast: bool = Field(True, description="Check color contrast")
    check_keyboard: bool = Field(True, description="Check keyboard accessibility")
    check_aria: bool = Field(True, description="Check ARIA implementation")
    check_forms: bool = Field(True, description="Check form accessibility")
    check_images: bool = Field(True, description="Check image accessibility")
    check_links: bool = Field(True, description="Check link accessibility")
    check_structure: bool = Field(True, description="Check document structure")
    check_language: bool = Field(True, description="Check language attributes")
    min_severity: ViolationSeverity = Field(
        ViolationSeverity.MINOR,
        description="Minimum severity to report"
    )
    output_format: str = Field("text", description="Output format (text/json/html/markdown)")
    screenshot_on_failure: bool = Field(False, description="Take screenshots on failures")
    include_element_html: bool = Field(True, description="Include element HTML in reports")


class ColorInfo(BaseModel):
    """Color information."""
    hex_value: str = Field(..., description="Hex color value (e.g., '#ffffff')")
    rgb: Tuple[int, int, int] = Field(..., description="RGB values (0-255)")
    luminance: float = Field(..., description="Relative luminance (0-1)")


class ContrastResult(BaseModel):
    """Result of a single contrast check."""
    element_selector: str = Field(..., description="CSS selector for the element")
    foreground_color: str = Field(..., description="Foreground (text) color")
    background_color: str = Field(..., description="Background color")
    contrast_ratio: float = Field(..., description="Calculated contrast ratio")
    required_ratio: float = Field(..., description="Required ratio for compliance")
    text_size: TextSize = Field(..., description="Text size category")
    font_size_px: float = Field(..., description="Font size in pixels")
    font_weight: str = Field(..., description="Font weight")
    is_passing: bool = Field(..., description="Whether contrast passes")
    wcag_aa_pass: bool = Field(..., description="Passes WCAG AA")
    wcag_aaa_pass: bool = Field(..., description="Passes WCAG AAA")


class ContrastIssue(BaseModel):
    """A contrast issue found during analysis."""
    element_selector: str = Field(..., description="CSS selector")
    foreground_color: str = Field(..., description="Foreground color")
    background_color: str = Field(..., description="Background color")
    contrast_ratio: float = Field(..., description="Current ratio")
    required_ratio: float = Field(..., description="Required ratio")
    text_content: Optional[str] = Field(None, description="Text content")
    suggested_foreground: Optional[str] = Field(None, description="Suggested foreground color")
    suggested_background: Optional[str] = Field(None, description="Suggested background color")


class ContrastReport(BaseModel):
    """Color contrast analysis report."""
    url: str = Field(..., description="URL tested")
    wcag_level: str = Field(..., description="WCAG level tested against")
    tested_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_elements: int = Field(0, description="Total elements analyzed")
    passing_count: int = Field(0, description="Elements passing contrast")
    failing_count: int = Field(0, description="Elements failing contrast")
    results: List[ContrastResult] = Field(default_factory=list)
    issues: List[ContrastIssue] = Field(default_factory=list)
    average_contrast: float = Field(0.0, description="Average contrast ratio")

    @property
    def has_violations(self) -> bool:
        """Check if there are contrast violations."""
        return self.failing_count > 0


class KeyboardIssueType(str, Enum):
    """Types of keyboard accessibility issues."""
    NO_FOCUS_INDICATOR = "no_focus_indicator"
    NOT_FOCUSABLE = "not_focusable"
    FOCUS_TRAP = "focus_trap"
    SKIP_LINK_MISSING = "skip_link_missing"
    TAB_ORDER_ISSUE = "tab_order_issue"
    NO_KEYBOARD_ACCESS = "no_keyboard_access"
    MISSING_FOCUS_MANAGEMENT = "missing_focus_management"


class KeyboardIssue(BaseModel):
    """A keyboard accessibility issue."""
    issue_type: KeyboardIssueType = Field(..., description="Type of issue")
    element_selector: str = Field(..., description="CSS selector")
    description: str = Field(..., description="Issue description")
    severity: ViolationSeverity = Field(..., description="Severity level")
    wcag_reference: str = Field(..., description="WCAG criterion")
    suggested_fix: str = Field(..., description="How to fix")


class KeyboardNavigationReport(BaseModel):
    """Keyboard navigation test report."""
    url: str = Field(..., description="URL tested")
    tested_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_focusable: int = Field(0, description="Total focusable elements")
    accessible_count: int = Field(0, description="Keyboard accessible elements")
    tab_order: List[str] = Field(default_factory=list, description="Tab order of elements")
    focus_indicators: Dict[str, bool] = Field(
        default_factory=dict,
        description="Focus indicator visibility per element"
    )
    issues: List[KeyboardIssue] = Field(default_factory=list)
    has_skip_link: bool = Field(False, description="Has skip to content link")
    focus_traps: List[str] = Field(default_factory=list, description="Elements with focus traps")

    @property
    def has_issues(self) -> bool:
        """Check if there are keyboard issues."""
        return len(self.issues) > 0

    @property
    def issue_count(self) -> int:
        """Count of keyboard issues."""
        return len(self.issues)


class ARIAViolationType(str, Enum):
    """Types of ARIA violations."""
    MISSING_REQUIRED_ATTRIBUTE = "missing_required_attribute"
    INVALID_ATTRIBUTE_VALUE = "invalid_attribute_value"
    UNSUPPORTED_ROLE = "unsupported_role"
    CONFLICTING_ROLES = "conflicting_roles"
    MISSING_ACCESSIBLE_NAME = "missing_accessible_name"
    HIDDEN_FOCUSABLE = "hidden_focusable"
    IMPROPER_ROLE_USAGE = "improper_role_usage"
    MISSING_PARENT_ROLE = "missing_parent_role"
    DUPLICATE_ID = "duplicate_id"


class ARIAViolation(BaseModel):
    """An ARIA implementation violation."""
    violation_type: ARIAViolationType = Field(..., description="Type of violation")
    element_selector: str = Field(..., description="CSS selector")
    element_html: Optional[str] = Field(None, description="Element HTML")
    description: str = Field(..., description="Violation description")
    severity: ViolationSeverity = Field(..., description="Severity level")
    wcag_reference: str = Field(..., description="WCAG criterion")
    suggested_fix: str = Field(..., description="How to fix")
    aria_attribute: Optional[str] = Field(None, description="Related ARIA attribute")
    role: Optional[str] = Field(None, description="Element role")


class ARIAReport(BaseModel):
    """ARIA validation report."""
    url: str = Field(..., description="URL tested")
    tested_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_aria_elements: int = Field(0, description="Elements with ARIA attributes")
    valid_count: int = Field(0, description="Valid ARIA implementations")
    invalid_count: int = Field(0, description="Invalid ARIA implementations")
    violations: List[ARIAViolation] = Field(default_factory=list)
    roles_found: Dict[str, int] = Field(default_factory=dict, description="Count of roles")
    aria_attributes_used: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of ARIA attributes"
    )

    @property
    def has_violations(self) -> bool:
        """Check if there are ARIA violations."""
        return len(self.violations) > 0


class ScreenReaderIssueType(str, Enum):
    """Types of screen reader compatibility issues."""
    MISSING_ALT_TEXT = "missing_alt_text"
    EMPTY_ALT_TEXT = "empty_alt_text"
    MISSING_LABEL = "missing_label"
    EMPTY_BUTTON = "empty_button"
    EMPTY_LINK = "empty_link"
    MISSING_HEADING_STRUCTURE = "missing_heading_structure"
    SKIPPED_HEADING_LEVEL = "skipped_heading_level"
    MISSING_LANDMARK = "missing_landmark"
    MISSING_LANG_ATTRIBUTE = "missing_lang_attribute"
    INACCESSIBLE_CONTENT = "inaccessible_content"


class ScreenReaderIssue(BaseModel):
    """A screen reader compatibility issue."""
    issue_type: ScreenReaderIssueType = Field(..., description="Type of issue")
    element_selector: str = Field(..., description="CSS selector")
    element_html: Optional[str] = Field(None, description="Element HTML")
    description: str = Field(..., description="Issue description")
    severity: ViolationSeverity = Field(..., description="Severity level")
    wcag_reference: str = Field(..., description="WCAG criterion")
    suggested_fix: str = Field(..., description="How to fix")
    accessible_name: Optional[str] = Field(None, description="Computed accessible name")


class HeadingInfo(BaseModel):
    """Information about a heading element."""
    level: int = Field(..., description="Heading level (1-6)")
    text: str = Field(..., description="Heading text")
    element_selector: str = Field(..., description="CSS selector")


class ScreenReaderReport(BaseModel):
    """Screen reader compatibility report."""
    url: str = Field(..., description="URL tested")
    tested_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    total_elements: int = Field(0, description="Total elements analyzed")
    labeled_count: int = Field(0, description="Elements with accessible names")
    missing_labels: int = Field(0, description="Elements missing accessible names")
    issues: List[ScreenReaderIssue] = Field(default_factory=list)
    landmark_structure: Dict[str, int] = Field(
        default_factory=dict,
        description="Landmark structure (role: count)"
    )
    heading_structure: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Document heading structure"
    )
    language: Optional[str] = Field(None, description="Page language")

    @property
    def has_issues(self) -> bool:
        """Check if there are screen reader issues."""
        return len(self.issues) > 0
