"""
Freya CSP Analyzer

Deep analysis of Content-Security-Policy headers.
Parses directives and identifies security issues.
"""

import re
from typing import Dict, List, Optional

from Asgard.Freya.Security.models.security_header_models import (
    CSPDirective,
    CSPReport,
    SecurityConfig,
)


class CSPAnalyzer:
    """
    Analyzes Content-Security-Policy headers in depth.

    Parses all directives and identifies security issues
    with specific recommendations.
    """

    # CSP directive categories
    FETCH_DIRECTIVES = [
        "default-src",
        "script-src",
        "script-src-elem",
        "script-src-attr",
        "style-src",
        "style-src-elem",
        "style-src-attr",
        "img-src",
        "font-src",
        "connect-src",
        "media-src",
        "object-src",
        "prefetch-src",
        "child-src",
        "frame-src",
        "worker-src",
        "manifest-src",
    ]

    DOCUMENT_DIRECTIVES = [
        "base-uri",
        "plugin-types",
        "sandbox",
    ]

    NAVIGATION_DIRECTIVES = [
        "form-action",
        "frame-ancestors",
        "navigate-to",
    ]

    REPORTING_DIRECTIVES = [
        "report-uri",
        "report-to",
    ]

    # Unsafe source keywords
    UNSAFE_KEYWORDS = ["'unsafe-inline'", "'unsafe-eval'", "'unsafe-hashes'"]

    def __init__(self, config: Optional[SecurityConfig] = None):
        """
        Initialize the CSP analyzer.

        Args:
            config: Security configuration
        """
        self.config = config or SecurityConfig()

    def analyze(self, csp_value: str) -> CSPReport:
        """
        Analyze a CSP header value.

        Args:
            csp_value: The CSP header value

        Returns:
            CSPReport with analysis results
        """
        report = CSPReport(raw_value=csp_value, is_present=True)

        # Parse all directives
        directives = self._parse_directives(csp_value)
        report.directives = directives

        # Map key directives
        directive_map = {d.name: d for d in directives}

        report.default_src = directive_map.get("default-src")
        report.script_src = directive_map.get("script-src")
        report.style_src = directive_map.get("style-src")
        report.img_src = directive_map.get("img-src")
        report.connect_src = directive_map.get("connect-src")
        report.frame_src = directive_map.get("frame-src")
        report.font_src = directive_map.get("font-src")
        report.object_src = directive_map.get("object-src")
        report.base_uri = directive_map.get("base-uri")
        report.form_action = directive_map.get("form-action")
        report.frame_ancestors = directive_map.get("frame-ancestors")

        # Check for nonces/hashes
        report.uses_nonces = self._uses_nonces(csp_value)
        report.uses_hashes = self._uses_hashes(csp_value)
        report.uses_strict_dynamic = "'strict-dynamic'" in csp_value

        # Analyze for issues
        self._analyze_issues(report)

        # Calculate score
        report.security_score = self._calculate_score(report)

        return report

    def _parse_directives(self, csp_value: str) -> List[CSPDirective]:
        """Parse CSP value into directives."""
        directives = []

        # Split on semicolons
        parts = csp_value.split(";")

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Split directive name from values
            tokens = part.split()
            if not tokens:
                continue

            directive_name = tokens[0].lower()
            values = tokens[1:] if len(tokens) > 1 else []

            directive = CSPDirective(name=directive_name, values=values)

            # Check for unsafe keywords
            for val in values:
                val_lower = val.lower()
                if val_lower == "'unsafe-inline'":
                    directive.has_unsafe_inline = True
                elif val_lower == "'unsafe-eval'":
                    directive.has_unsafe_eval = True
                elif val == "*":
                    directive.allows_any = True

            directives.append(directive)

        return directives

    def _uses_nonces(self, csp_value: str) -> bool:
        """Check if CSP uses nonces."""
        return bool(re.search(r"'nonce-[^']+?'", csp_value))

    def _uses_hashes(self, csp_value: str) -> bool:
        """Check if CSP uses hashes."""
        return bool(
            re.search(r"'sha(256|384|512)-[^']+?'", csp_value)
        )

    def _analyze_issues(self, report: CSPReport) -> None:
        """Analyze CSP for security issues."""
        # Check for missing default-src
        if not report.default_src:
            report.warnings.append(
                "No default-src directive - consider adding one as a fallback"
            )

        # Check for unsafe-inline in scripts
        script_src = report.script_src or report.default_src
        if script_src and script_src.has_unsafe_inline:
            if not report.uses_nonces and not report.uses_hashes:
                report.critical_issues.append(
                    "script-src allows 'unsafe-inline' without nonces or hashes - "
                    "vulnerable to XSS"
                )
                report.recommendations.append(
                    "Use nonces or hashes instead of 'unsafe-inline' for scripts"
                )
            elif not report.uses_strict_dynamic:
                report.warnings.append(
                    "script-src allows 'unsafe-inline' - "
                    "consider using 'strict-dynamic' with nonces"
                )

        # Check for unsafe-eval in scripts
        if script_src and script_src.has_unsafe_eval:
            if not self.config.allow_unsafe_eval:
                report.critical_issues.append(
                    "script-src allows 'unsafe-eval' - "
                    "allows dynamic code execution"
                )
                report.recommendations.append(
                    "Remove 'unsafe-eval' and refactor code to avoid eval()"
                )

        # Check for unsafe-inline in styles
        style_src = report.style_src or report.default_src
        if style_src and style_src.has_unsafe_inline:
            report.warnings.append(
                "style-src allows 'unsafe-inline' - "
                "consider using hashes for inline styles"
            )

        # Check for wildcard sources
        for directive in report.directives:
            if directive.allows_any:
                if directive.name in ["script-src", "default-src"]:
                    report.critical_issues.append(
                        f"{directive.name} allows any source (*) - "
                        "allows loading scripts from anywhere"
                    )
                else:
                    report.warnings.append(
                        f"{directive.name} allows any source (*)"
                    )

        # Check for missing object-src
        if not report.object_src and report.default_src:
            if "'none'" not in [v.lower() for v in report.default_src.values]:
                report.warnings.append(
                    "object-src is not explicitly set to 'none' - "
                    "consider blocking plugins"
                )
        elif report.object_src:
            if "'none'" not in [v.lower() for v in report.object_src.values]:
                report.warnings.append(
                    "object-src should be 'none' to prevent plugin content"
                )

        # Check for base-uri
        if not report.base_uri:
            report.warnings.append(
                "base-uri not set - vulnerable to base tag injection"
            )
            report.recommendations.append(
                "Add base-uri 'self' or 'none' to prevent base tag attacks"
            )

        # Check for form-action
        if not report.form_action:
            report.warnings.append(
                "form-action not set - forms can submit to any URL"
            )
            report.recommendations.append(
                "Add form-action to restrict where forms can be submitted"
            )

        # Check for frame-ancestors
        if not report.frame_ancestors:
            report.warnings.append(
                "frame-ancestors not set - use this instead of X-Frame-Options"
            )
            report.recommendations.append(
                "Add frame-ancestors to control embedding"
            )

        # Check for data: and blob: URLs
        for directive in report.directives:
            for value in directive.values:
                if value.lower() == "data:" and directive.name in [
                    "script-src",
                    "default-src",
                ]:
                    report.critical_issues.append(
                        f"{directive.name} allows data: URLs - "
                        "can be used for XSS"
                    )
                elif value.lower() == "blob:" and directive.name in [
                    "script-src",
                    "default-src",
                ]:
                    report.warnings.append(
                        f"{directive.name} allows blob: URLs"
                    )

        # Check for http: sources (mixed content)
        for directive in report.directives:
            for value in directive.values:
                if value.lower().startswith("http:"):
                    report.warnings.append(
                        f"{directive.name} allows insecure HTTP source: {value}"
                    )

    def _calculate_score(self, report: CSPReport) -> float:
        """Calculate CSP security score (0-100)."""
        score = 100.0

        # Critical issues: -20 each
        score -= len(report.critical_issues) * 20

        # Warnings: -5 each
        score -= len(report.warnings) * 5

        # Bonus for good practices
        if report.uses_nonces or report.uses_hashes:
            score += 10

        if report.uses_strict_dynamic:
            score += 5

        if report.object_src:
            if "'none'" in [v.lower() for v in report.object_src.values]:
                score += 5

        if report.base_uri:
            score += 5

        if report.form_action:
            score += 5

        if report.frame_ancestors:
            score += 5

        return max(0, min(100, score))

    def get_sample_policy(self, strict: bool = True) -> str:
        """
        Generate a sample CSP policy.

        Args:
            strict: Whether to generate a strict policy

        Returns:
            Sample CSP header value
        """
        if strict:
            return (
                "default-src 'self'; "
                "script-src 'self' 'strict-dynamic' 'nonce-{RANDOM}'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "object-src 'none'; "
                "base-uri 'self'; "
                "form-action 'self'; "
                "frame-ancestors 'self'; "
                "upgrade-insecure-requests"
            )
        else:
            return (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' https:; "
                "connect-src 'self' https:; "
                "object-src 'none'; "
                "frame-ancestors 'self'"
            )
