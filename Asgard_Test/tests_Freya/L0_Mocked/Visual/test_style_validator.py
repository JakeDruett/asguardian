"""
Freya Visual L0 Mocked Tests - Style Validator

Comprehensive tests for style validation service with mocked Playwright and theme loading.
"""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, mock_open

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from Asgard.Freya.Visual.models.visual_models import StyleIssueType
from Asgard.Freya.Visual.services.style_validator import StyleValidator, ThemeLoader


# =============================================================================
# Test StyleValidator Initialization
# =============================================================================

class TestStyleValidatorInit:
    """Tests for StyleValidator initialization."""

    @pytest.mark.L0
    def test_init_without_theme(self):
        """Test StyleValidator initialization without theme file."""
        validator = StyleValidator()

        assert validator is not None
        assert len(validator.theme_colors) == 0
        assert len(validator.theme_fonts) == 0

    @pytest.mark.L0
    def test_init_with_theme_file(self, temp_theme_file):
        """Test StyleValidator initialization with theme file."""
        validator = StyleValidator(theme_file=str(temp_theme_file))

        assert validator is not None
        assert len(validator.theme_colors) > 0
        assert len(validator.theme_fonts) > 0


# =============================================================================
# Test _load_theme Method
# =============================================================================

class TestLoadTheme:
    """Tests for _load_theme method."""

    @pytest.mark.L0
    def test_load_theme_valid_json(self, temp_output_dir):
        """Test loading valid JSON theme file."""
        theme_file = temp_output_dir / "test_theme.json"
        theme_data = {
            "colors": {
                "primary": "#007bff",
                "secondary": "#6c757d",
            },
            "fonts": {
                "primary": "Roboto",
                "secondary": "Arial",
            }
        }
        theme_file.write_text(json.dumps(theme_data))

        validator = StyleValidator(theme_file=str(theme_file))

        assert "#007bff" in validator.theme_colors
        assert "#6c757d" in validator.theme_colors
        assert "roboto" in validator.theme_fonts
        assert "arial" in validator.theme_fonts

    @pytest.mark.L0
    def test_load_theme_nested_colors(self, temp_output_dir):
        """Test loading theme with nested color structure."""
        theme_file = temp_output_dir / "nested_theme.json"
        theme_data = {
            "colors": {
                "primary": {
                    "main": "#007bff",
                    "light": "#66b3ff",
                    "dark": "#0056b3",
                },
                "text": "#212529",
            }
        }
        theme_file.write_text(json.dumps(theme_data))

        validator = StyleValidator(theme_file=str(theme_file))

        assert "#007bff" in validator.theme_colors
        assert "#66b3ff" in validator.theme_colors
        assert "#0056b3" in validator.theme_colors
        assert "#212529" in validator.theme_colors

    @pytest.mark.L0
    def test_load_theme_typography_key(self, temp_output_dir):
        """Test loading theme with typography key instead of fonts."""
        theme_file = temp_output_dir / "typography_theme.json"
        theme_data = {
            "colors": {"primary": "#007bff"},
            "typography": {
                "heading": "Montserrat",
                "body": {
                    "family": "Roboto"
                }
            }
        }
        theme_file.write_text(json.dumps(theme_data))

        validator = StyleValidator(theme_file=str(theme_file))

        assert "montserrat" in validator.theme_fonts
        assert "roboto" in validator.theme_fonts

    @pytest.mark.L0
    def test_load_theme_invalid_file(self, temp_output_dir):
        """Test loading theme with invalid file path."""
        validator = StyleValidator(theme_file=str(temp_output_dir / "nonexistent.json"))

        # Should handle gracefully
        assert len(validator.theme_colors) == 0
        assert len(validator.theme_fonts) == 0

    @pytest.mark.L0
    def test_load_theme_malformed_json(self, temp_output_dir):
        """Test loading theme with malformed JSON."""
        theme_file = temp_output_dir / "malformed.json"
        theme_file.write_text("{invalid json")

        validator = StyleValidator(theme_file=str(theme_file))

        # Should handle gracefully
        assert len(validator.theme_colors) == 0
        assert len(validator.theme_fonts) == 0


# =============================================================================
# Test _normalize_color Method
# =============================================================================

class TestNormalizeColor:
    """Tests for _normalize_color method."""

    @pytest.mark.L0
    def test_normalize_hex_6_digit(self):
        """Test normalizing 6-digit hex color."""
        validator = StyleValidator()

        normalized = validator._normalize_color("#007BFF")

        assert normalized == "#007bff"

    @pytest.mark.L0
    def test_normalize_hex_3_digit(self):
        """Test normalizing 3-digit hex color."""
        validator = StyleValidator()

        normalized = validator._normalize_color("#F0F")

        assert normalized == "#ff00ff"

    @pytest.mark.L0
    def test_normalize_rgb(self):
        """Test normalizing RGB color."""
        validator = StyleValidator()

        normalized = validator._normalize_color("rgb(255, 0, 0)")

        assert normalized == "#ff0000"

    @pytest.mark.L0
    def test_normalize_rgba(self):
        """Test normalizing RGBA color."""
        validator = StyleValidator()

        normalized = validator._normalize_color("rgba(0, 123, 255, 0.5)")

        assert normalized == "#007bff"

    @pytest.mark.L0
    def test_normalize_invalid_color(self):
        """Test normalizing invalid color returns None."""
        validator = StyleValidator()

        normalized = validator._normalize_color("not-a-color")

        assert normalized is None

    @pytest.mark.L0
    def test_normalize_whitespace(self):
        """Test normalizing color with whitespace."""
        validator = StyleValidator()

        normalized = validator._normalize_color("  #007BFF  ")

        assert normalized == "#007bff"


# =============================================================================
# Test validate Method
# =============================================================================

class TestValidate:
    """Tests for validate method."""

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_basic(self, mock_async_playwright, mock_page):
        """Test basic style validation."""
        validator = StyleValidator()

        mock_page.evaluate.side_effect = [
            {
                "colors": {"rgb(0, 123, 255)": 10},
                "fonts": {"roboto": 50},
                "elements": []
            },
            100,  # total elements
        ]

        with patch("Asgard.Freya.Visual.services.style_validator.async_playwright", mock_async_playwright):
            report = await validator.validate(url="https://example.com")

        assert report.url == "https://example.com"
        assert report.tested_at is not None
        assert report.total_elements == 100
        assert isinstance(report.issues, list)
        assert isinstance(report.colors_found, dict)
        assert isinstance(report.fonts_found, dict)

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_collects_colors(self, mock_async_playwright, mock_page):
        """Test validation collects colors from page."""
        validator = StyleValidator()

        mock_page.evaluate.side_effect = [
            {
                "colors": {
                    "rgb(0, 123, 255)": 25,
                    "rgb(255, 0, 0)": 5,
                },
                "fonts": {},
                "elements": []
            },
            100,
        ]

        with patch("Asgard.Freya.Visual.services.style_validator.async_playwright", mock_async_playwright):
            report = await validator.validate(url="https://example.com")

        assert "#007bff" in report.colors_found
        assert "#ff0000" in report.colors_found
        assert report.colors_found["#007bff"] == 25
        assert report.colors_found["#ff0000"] == 5

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_collects_fonts(self, mock_async_playwright, mock_page):
        """Test validation collects fonts from page."""
        validator = StyleValidator()

        mock_page.evaluate.side_effect = [
            {
                "colors": {},
                "fonts": {
                    "roboto": 80,
                    "arial": 20,
                },
                "elements": []
            },
            100,
        ]

        with patch("Asgard.Freya.Visual.services.style_validator.async_playwright", mock_async_playwright):
            report = await validator.validate(url="https://example.com")

        assert "roboto" in report.fonts_found
        assert "arial" in report.fonts_found
        assert report.fonts_found["roboto"] == 80
        assert report.fonts_found["arial"] == 20

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_detects_unknown_colors(self, mock_async_playwright, mock_page, temp_theme_file):
        """Test validation detects colors not in theme."""
        validator = StyleValidator(theme_file=str(temp_theme_file))

        mock_page.evaluate.side_effect = [
            {
                "colors": {
                    "rgb(255, 0, 0)": 5,  # Not in theme
                },
                "fonts": {},
                "elements": [
                    {
                        "selector": ".text",
                        "color": "rgb(255, 0, 0)",
                        "backgroundColor": "rgb(255, 255, 255)",
                        "fontFamily": "roboto",
                        "fontSize": "16px",
                        "fontWeight": "400",
                        "lineHeight": "24px",
                        "padding": "10px",
                        "margin": "0px",
                        "borderRadius": "4px",
                    }
                ]
            },
            100,
        ]

        with patch("Asgard.Freya.Visual.services.style_validator.async_playwright", mock_async_playwright):
            report = await validator.validate(url="https://example.com")

        assert "#ff0000" in report.unknown_colors
        assert len(report.issues) > 0
        color_issues = [i for i in report.issues if i.issue_type == StyleIssueType.UNKNOWN_COLOR]
        assert len(color_issues) > 0

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_detects_unknown_fonts(self, mock_async_playwright, mock_page, temp_theme_file):
        """Test validation detects fonts not in theme."""
        validator = StyleValidator(theme_file=str(temp_theme_file))

        mock_page.evaluate.side_effect = [
            {
                "colors": {},
                "fonts": {"comic sans": 10},  # Not in theme
                "elements": [
                    {
                        "selector": ".text",
                        "color": "rgb(33, 37, 41)",
                        "backgroundColor": "rgb(255, 255, 255)",
                        "fontFamily": "comic sans",
                        "fontSize": "16px",
                        "fontWeight": "400",
                        "lineHeight": "24px",
                        "padding": "10px",
                        "margin": "0px",
                        "borderRadius": "4px",
                    }
                ]
            },
            100,
        ]

        with patch("Asgard.Freya.Visual.services.style_validator.async_playwright", mock_async_playwright):
            report = await validator.validate(url="https://example.com")

        assert "comic sans" in report.unknown_fonts
        assert len(report.issues) > 0
        font_issues = [i for i in report.issues if i.issue_type == StyleIssueType.UNKNOWN_FONT]
        assert len(font_issues) > 0

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_ignores_system_fonts(self, mock_async_playwright, mock_page, temp_theme_file):
        """Test validation ignores system fonts."""
        validator = StyleValidator(theme_file=str(temp_theme_file))

        mock_page.evaluate.side_effect = [
            {
                "colors": {},
                "fonts": {
                    "system-ui": 10,
                    "serif": 5,
                    "sans-serif": 3,
                },
                "elements": []
            },
            100,
        ]

        with patch("Asgard.Freya.Visual.services.style_validator.async_playwright", mock_async_playwright):
            report = await validator.validate(url="https://example.com")

        # System fonts should not be in unknown_fonts
        assert "system-ui" not in report.unknown_fonts
        assert "serif" not in report.unknown_fonts
        assert "sans-serif" not in report.unknown_fonts

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_ignores_black_white(self, mock_async_playwright, mock_page, temp_theme_file):
        """Test validation ignores pure black and white backgrounds."""
        validator = StyleValidator(theme_file=str(temp_theme_file))

        mock_page.evaluate.side_effect = [
            {
                "colors": {},
                "fonts": {},
                "elements": [
                    {
                        "selector": ".element1",
                        "color": "rgb(0, 0, 0)",
                        "backgroundColor": "rgb(255, 255, 255)",
                        "fontFamily": "roboto",
                        "fontSize": "16px",
                        "fontWeight": "400",
                        "lineHeight": "24px",
                        "padding": "10px",
                        "margin": "0px",
                        "borderRadius": "4px",
                    },
                    {
                        "selector": ".element2",
                        "color": "rgb(255, 255, 255)",
                        "backgroundColor": "rgb(0, 0, 0)",
                        "fontFamily": "roboto",
                        "fontSize": "16px",
                        "fontWeight": "400",
                        "lineHeight": "24px",
                        "padding": "10px",
                        "margin": "0px",
                        "borderRadius": "4px",
                    }
                ]
            },
            100,
        ]

        with patch("Asgard.Freya.Visual.services.style_validator.async_playwright", mock_async_playwright):
            report = await validator.validate(url="https://example.com")

        # Black/white backgrounds should not trigger issues
        bg_issues = [i for i in report.issues
                     if i.property_name == "backgroundColor"
                     and i.actual_value in ["#ffffff", "#000000"]]
        assert len(bg_issues) == 0

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_validate_limits_issues(self, mock_async_playwright, mock_page, temp_theme_file):
        """Test validation limits number of issues returned."""
        validator = StyleValidator(theme_file=str(temp_theme_file))

        # Generate 100 elements with unknown colors
        elements = []
        for i in range(100):
            elements.append({
                "selector": f".element{i}",
                "color": "rgb(255, 0, 0)",  # Not in theme
                "backgroundColor": "rgb(255, 255, 255)",
                "fontFamily": "roboto",
                "fontSize": "16px",
                "fontWeight": "400",
                "lineHeight": "24px",
                "padding": "10px",
                "margin": "0px",
                "borderRadius": "4px",
            })

        mock_page.evaluate.side_effect = [
            {
                "colors": {"rgb(255, 0, 0)": 100},
                "fonts": {},
                "elements": elements
            },
            100,
        ]

        with patch("Asgard.Freya.Visual.services.style_validator.async_playwright", mock_async_playwright):
            report = await validator.validate(url="https://example.com")

        # Should limit to 50 issues
        assert len(report.issues) <= 50


# =============================================================================
# Test _check_consistency Method
# =============================================================================

class TestCheckConsistency:
    """Tests for _check_consistency method."""

    @pytest.mark.L0
    def test_check_consistency_too_many_font_sizes(self):
        """Test consistency check detects too many font sizes."""
        validator = StyleValidator()

        elements = []
        for i in range(15):
            elements.append({"fontSize": f"{i + 10}px"})

        issues = validator._check_consistency(elements)

        font_issues = [i for i in issues if i.issue_type == StyleIssueType.FONT_MISMATCH]
        assert len(font_issues) > 0
        assert "type scale" in font_issues[0].description

    @pytest.mark.L0
    def test_check_consistency_too_many_spacing_values(self):
        """Test consistency check detects too many spacing values."""
        validator = StyleValidator()

        elements = []
        for i in range(25):
            elements.append({"padding": f"{i}px", "margin": f"{i}px"})

        issues = validator._check_consistency(elements)

        spacing_issues = [i for i in issues if i.issue_type == StyleIssueType.SPACING_MISMATCH]
        assert len(spacing_issues) > 0
        assert "spacing scale" in spacing_issues[0].description

    @pytest.mark.L0
    def test_check_consistency_acceptable_variety(self):
        """Test consistency check accepts reasonable variety."""
        validator = StyleValidator()

        elements = [
            {"fontSize": "14px", "padding": "10px", "margin": "10px"},
            {"fontSize": "16px", "padding": "15px", "margin": "15px"},
            {"fontSize": "18px", "padding": "20px", "margin": "20px"},
        ]

        issues = validator._check_consistency(elements)

        assert len(issues) == 0


# =============================================================================
# Test ThemeLoader
# =============================================================================

class TestThemeLoader:
    """Tests for ThemeLoader utility class."""

    @pytest.mark.L0
    def test_load_from_json_file(self, temp_output_dir):
        """Test loading theme from JSON file."""
        theme_file = temp_output_dir / "theme.json"
        theme_data = {"colors": {"primary": "#007bff"}}
        theme_file.write_text(json.dumps(theme_data))

        theme = ThemeLoader.load_from_file(str(theme_file))

        assert "colors" in theme
        assert theme["colors"]["primary"] == "#007bff"

    @pytest.mark.L0
    def test_parse_js_theme(self, temp_output_dir):
        """Test parsing JavaScript theme file."""
        theme_file = temp_output_dir / "theme.js"
        content = """
        export const colors = {
            primary: '#007bff',
            secondary: '#6c757d',
            success: 'rgb(40, 167, 69)',
        };
        """
        theme_file.write_text(content)

        theme = ThemeLoader.load_from_file(str(theme_file))

        assert "colors" in theme
        assert "#007bff" in theme["colors"].values()

    @pytest.mark.L0
    def test_parse_css_variables(self, temp_output_dir):
        """Test parsing CSS custom properties."""
        theme_file = temp_output_dir / "theme.css"
        content = """
        :root {
            --primary-color: #007bff;
            --secondary-color: #6c757d;
            --text-color: rgb(33, 37, 41);
        }
        """
        theme_file.write_text(content)

        theme = ThemeLoader.load_from_file(str(theme_file))

        assert "colors" in theme
        assert "#007bff" in theme["colors"].values()
        assert "#6c757d" in theme["colors"].values()

    @pytest.mark.L0
    def test_load_unsupported_format(self, temp_output_dir):
        """Test loading unsupported file format returns empty dict."""
        theme_file = temp_output_dir / "theme.xml"
        theme_file.write_text("<theme></theme>")

        theme = ThemeLoader.load_from_file(str(theme_file))

        assert theme == {}


# =============================================================================
# Test Integration
# =============================================================================

class TestStyleValidatorIntegration:
    """Integration tests for StyleValidator."""

    @pytest.mark.L0
    @pytest.mark.asyncio
    async def test_full_validation_workflow(self, mock_async_playwright, mock_page, temp_theme_file):
        """Test complete validation workflow."""
        validator = StyleValidator(theme_file=str(temp_theme_file))

        mock_page.evaluate.side_effect = [
            {
                "colors": {
                    "rgb(0, 123, 255)": 25,  # In theme
                    "rgb(255, 0, 0)": 5,     # Not in theme
                },
                "fonts": {
                    "roboto": 80,      # In theme
                    "comic sans": 20,  # Not in theme
                },
                "elements": [
                    {
                        "selector": ".valid",
                        "color": "rgb(33, 37, 41)",
                        "backgroundColor": "rgb(255, 255, 255)",
                        "fontFamily": "roboto",
                        "fontSize": "16px",
                        "fontWeight": "400",
                        "lineHeight": "24px",
                        "padding": "10px",
                        "margin": "10px",
                        "borderRadius": "4px",
                    },
                    {
                        "selector": ".invalid-color",
                        "color": "rgb(255, 0, 0)",
                        "backgroundColor": "rgb(255, 255, 255)",
                        "fontFamily": "roboto",
                        "fontSize": "16px",
                        "fontWeight": "400",
                        "lineHeight": "24px",
                        "padding": "10px",
                        "margin": "10px",
                        "borderRadius": "4px",
                    },
                    {
                        "selector": ".invalid-font",
                        "color": "rgb(33, 37, 41)",
                        "backgroundColor": "rgb(255, 255, 255)",
                        "fontFamily": "comic sans",
                        "fontSize": "16px",
                        "fontWeight": "400",
                        "lineHeight": "24px",
                        "padding": "10px",
                        "margin": "10px",
                        "borderRadius": "4px",
                    },
                ]
            },
            100,
        ]

        with patch("Asgard.Freya.Visual.services.style_validator.async_playwright", mock_async_playwright):
            report = await validator.validate(url="https://example.com")

        # Should detect unknown color and font
        assert "#ff0000" in report.unknown_colors
        assert "comic sans" in report.unknown_fonts

        # Should have issues for unknown color and font
        assert len(report.issues) >= 2

        unknown_color_issues = [i for i in report.issues
                                if i.issue_type == StyleIssueType.UNKNOWN_COLOR]
        unknown_font_issues = [i for i in report.issues
                               if i.issue_type == StyleIssueType.UNKNOWN_FONT]

        assert len(unknown_color_issues) >= 1
        assert len(unknown_font_issues) >= 1
