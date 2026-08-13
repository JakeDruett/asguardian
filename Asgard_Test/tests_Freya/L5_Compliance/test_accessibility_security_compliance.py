"""
L5 Compliance Tests — Freya Accessibility / Security Ground Truths.

Known-bad inputs (failing contrast, disordered focus flow, mixed content,
missing security headers) MUST be flagged; known-good equivalents MUST be
clean. References: WCAG 2.1 SC 1.4.3 / 1.4.6 / 1.3.2, CWE-319, CWE-693.
"""

import httpx

from Asgard.Freya.Accessibility.services._color_contrast_math import (
    calculate_contrast_ratio,
)
from Asgard.Freya.Accessibility.services._focus_order_spatial import (
    analyze_focus_order_spatial,
)
from Asgard.Freya.Security.models.security_header_models import SecurityConfig
from Asgard.Freya.Security.services._security_header_analyzers import (
    analyze_csp,
    analyze_frame_options,
    analyze_hsts,
)
from Asgard.Freya.Security.services.mixed_content_checker import scan_static_dom

from Asgard_Test.L5_Meta.l5_fixtures import fixture_path

PAGE = "https://example.com/"

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
MID_GREY = (119, 119, 119)  # #777 on white: ~4.48:1, below the AA 4.5:1 bar
DARK_GREY = (89, 89, 89)    # #595959 on white: ~7.0:1, at the AAA bar


class TestContrastRatioCompliance:
    """WCAG 1.4.3 (AA, 4.5:1) and 1.4.6 (AAA, 7:1) ground truths."""

    def test_known_bad_grey_fails_aa(self) -> None:
        ratio = calculate_contrast_ratio(MID_GREY, WHITE)
        assert ratio < 4.5, f"#777 on white must fail AA, got {ratio:.2f}:1"

    def test_black_on_white_passes_aaa(self) -> None:
        ratio = calculate_contrast_ratio(BLACK, WHITE)
        assert abs(ratio - 21.0) < 0.01, f"Expected 21:1, got {ratio:.2f}:1"
        assert ratio >= 7.0

    def test_aaa_boundary_colour(self) -> None:
        ratio = calculate_contrast_ratio(DARK_GREY, WHITE)
        assert 6.9 <= ratio <= 7.1, f"#595959 on white must sit at ~7:1, got {ratio:.2f}"

    def test_ratio_is_symmetric(self) -> None:
        assert calculate_contrast_ratio(BLACK, WHITE) == \
            calculate_contrast_ratio(WHITE, BLACK)


class TestFocusOrderCompliance:
    """WCAG 1.3.2: keyboard focus order must follow reading flow."""

    def test_reversed_focus_order_flagged(self) -> None:
        # Every tab step jumps UP the page — 100% regression ratio.
        centers = [{"x": 100.0, "y": 500.0 - i * 100.0} for i in range(5)]
        issue = analyze_focus_order_spatial(centers)
        assert issue is not None, "Reversed focus order must be flagged"
        assert issue.wcag_reference == "1.3.2"

    def test_natural_reading_order_clean(self) -> None:
        centers = [{"x": 100.0, "y": 100.0 + i * 100.0} for i in range(5)]
        assert analyze_focus_order_spatial(centers) is None


class TestMixedContentCompliance:
    """CWE-319: https page loading http:// subresources."""

    def test_library_fixture_flagged(self) -> None:
        html = fixture_path(
            "CWE-319_cleartext_transmission/mixed_content_page.html"
        ).read_text(encoding="utf-8")
        findings = scan_static_dom(html, PAGE)
        assert findings, "Mixed-content fixture must produce findings"

    def test_all_https_page_clean(self) -> None:
        html = '<script src="https://cdn.example.com/a.js"></script>'
        assert scan_static_dom(html, PAGE) == []


class TestSecurityHeaderCompliance:
    """CWE-693 / OWASP secure headers: missing headers must be insecure."""

    def test_missing_headers_insecure(self) -> None:
        empty = httpx.Headers({})
        config = SecurityConfig()
        for analyzer in (analyze_frame_options,):
            header = analyzer(empty)
            assert header.is_secure is False, f"{header.name} missing but secure"
        assert analyze_csp(empty, config).is_secure is False
        assert analyze_hsts(empty, config).is_secure is False

    def test_unsafe_inline_csp_insecure(self) -> None:
        headers = httpx.Headers(
            {"Content-Security-Policy": "default-src 'self' 'unsafe-inline'"}
        )
        assert analyze_csp(headers, SecurityConfig()).is_secure is False

    def test_strong_headers_secure(self) -> None:
        config = SecurityConfig()
        headers = httpx.Headers({
            "Content-Security-Policy": "default-src 'self'",
            "Strict-Transport-Security":
                "max-age=63072000; includeSubDomains; preload",
            "X-Frame-Options": "DENY",
        })
        assert analyze_csp(headers, config).is_secure is True
        assert analyze_hsts(headers, config).is_secure is True
        assert analyze_frame_options(headers).is_secure is True
