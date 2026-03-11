"""
Heimdall Security Headers CSP Parser Utilities

Helper functions for parsing and analyzing Content-Security-Policy headers.
"""

import re
from typing import Dict, List, Optional, Set, Tuple


class CSPDirective:
    """Represents a parsed CSP directive with its values."""

    def __init__(self, name: str, values: List[str]):
        self.name = name
        self.values = values

    @property
    def has_unsafe_inline(self) -> bool:
        """Check if directive allows unsafe-inline."""
        return "'unsafe-inline'" in self.values

    @property
    def has_unsafe_eval(self) -> bool:
        """Check if directive allows unsafe-eval."""
        return "'unsafe-eval'" in self.values

    @property
    def has_wildcard(self) -> bool:
        """Check if directive has wildcard source."""
        return "*" in self.values or any(v.startswith("*") for v in self.values)

    @property
    def has_data_uri(self) -> bool:
        """Check if directive allows data: URIs."""
        return "data:" in self.values

    @property
    def has_blob_uri(self) -> bool:
        """Check if directive allows blob: URIs."""
        return "blob:" in self.values

    @property
    def is_none(self) -> bool:
        """Check if directive is set to 'none'."""
        return "'none'" in self.values

    @property
    def is_self_only(self) -> bool:
        """Check if directive only allows 'self'."""
        return self.values == ["'self'"]


class ParsedCSP:
    """Represents a fully parsed Content-Security-Policy."""

    def __init__(self, raw_policy: str):
        self.raw_policy = raw_policy
        self.directives: Dict[str, CSPDirective] = {}
        self._parse()

    def _parse(self) -> None:
        """Parse the CSP string into directives."""
        directive_parts = self.raw_policy.split(";")

        for part in directive_parts:
            part = part.strip()
            if not part:
                continue

            tokens = part.split()
            if not tokens:
                continue

            directive_name = tokens[0].lower()
            directive_values = tokens[1:] if len(tokens) > 1 else []

            self.directives[directive_name] = CSPDirective(directive_name, directive_values)

    def has_directive(self, name: str) -> bool:
        """Check if a directive exists in the policy."""
        return name.lower() in self.directives

    def get_directive(self, name: str) -> Optional[CSPDirective]:
        """Get a specific directive by name."""
        return self.directives.get(name.lower())

    def get_effective_directive(self, name: str) -> Optional[CSPDirective]:
        """Get the effective directive, falling back to default-src if needed."""
        directive = self.get_directive(name)
        if directive is not None:
            return directive

        fallback_map = {
            "script-src": "default-src",
            "style-src": "default-src",
            "img-src": "default-src",
            "font-src": "default-src",
            "connect-src": "default-src",
            "media-src": "default-src",
            "object-src": "default-src",
            "frame-src": "child-src",
            "child-src": "default-src",
            "worker-src": "child-src",
            "manifest-src": "default-src",
        }

        fallback = fallback_map.get(name.lower())
        if fallback:
            return self.get_effective_directive(fallback)

        return None

    @property
    def missing_recommended_directives(self) -> List[str]:
        """Get list of missing recommended directives."""
        recommended = [
            "default-src",
            "script-src",
            "style-src",
            "img-src",
            "object-src",
            "base-uri",
            "form-action",
        ]

        missing = []
        for directive in recommended:
            if not self.has_directive(directive):
                missing.append(directive)

        return missing

    @property
    def unsafe_directives(self) -> List[Tuple[str, str]]:
        """Get list of directives with unsafe values."""
        unsafe = []

        for name, directive in self.directives.items():
            if directive.has_unsafe_inline:
                unsafe.append((name, "'unsafe-inline'"))
            if directive.has_unsafe_eval:
                unsafe.append((name, "'unsafe-eval'"))
            if directive.has_wildcard:
                unsafe.append((name, "* (wildcard)"))
            if directive.has_data_uri and name in ["script-src", "default-src"]:
                unsafe.append((name, "data:"))

        return unsafe


def parse_csp(csp_string: str) -> ParsedCSP:
    """
    Parse a Content-Security-Policy string.

    Args:
        csp_string: The CSP header value

    Returns:
        ParsedCSP object with parsed directives
    """
    return ParsedCSP(csp_string)


def extract_csp_from_code(content: str) -> List[Tuple[int, str]]:
    """
    Extract CSP definitions from source code.

    Args:
        content: Source code content

    Returns:
        List of (line_number, csp_value) tuples
    """
    results = []
    lines = content.split("\n")

    csp_patterns = [
        r'["\']Content-Security-Policy["\']\s*[,:]\s*["\']([^"\']+)["\']',
        r'add_header\s+Content-Security-Policy\s+["\']([^"\']+)["\']',
        r'Header\s+set\s+Content-Security-Policy\s+["\']([^"\']+)["\']',
        r'content_security_policy\s*=\s*["\']([^"\']+)["\']',
        r'CSP\s*=\s*["\']([^"\']+)["\']',
        r'csp_policy\s*=\s*["\']([^"\']+)["\']',
        r'\.set\s*\(\s*["\']Content-Security-Policy["\']\s*,\s*["\']([^"\']+)["\']',
        r'response\.headers\[["\']Content-Security-Policy["\']\]\s*=\s*["\']([^"\']+)["\']',
    ]

    combined_pattern = "|".join(f"(?:{p})" for p in csp_patterns)
    regex = re.compile(combined_pattern, re.IGNORECASE)

    for i, line in enumerate(lines, start=1):
        for match in regex.finditer(line):
            for group in match.groups():
                if group:
                    results.append((i, group))
                    break

    return results


def validate_csp_directive_value(directive: str, value: str) -> List[str]:
    """
    Validate a CSP directive value and return any issues.

    Args:
        directive: The directive name
        value: The directive value

    Returns:
        List of issue descriptions
    """
    issues = []
    value_lower = value.lower()

    if value == "*":
        issues.append(f"Wildcard (*) source in {directive} allows loading from any origin")

    if "'unsafe-inline'" in value_lower:
        issues.append(f"'unsafe-inline' in {directive} allows inline scripts/styles, defeating CSP protection")

    if "'unsafe-eval'" in value_lower:
        issues.append(f"'unsafe-eval' in {directive} allows eval() and similar methods")

    if directive in ["script-src", "default-src"]:
        if "data:" in value_lower:
            issues.append(f"data: URI in {directive} can be used to inject scripts")

    if value.startswith("http:"):
        issues.append(f"HTTP source in {directive} allows loading over insecure connection")

    return issues


def get_csp_security_level(csp: ParsedCSP) -> str:
    """
    Assess the overall security level of a CSP.

    Args:
        csp: Parsed CSP object

    Returns:
        Security level: "strict", "moderate", "weak", or "none"
    """
    if not csp.directives:
        return "none"

    has_default = csp.has_directive("default-src")
    unsafe_count = len(csp.unsafe_directives)
    missing_count = len(csp.missing_recommended_directives)

    if not has_default:
        return "weak"

    if unsafe_count == 0 and missing_count <= 2:
        return "strict"

    if unsafe_count <= 2 and missing_count <= 4:
        return "moderate"

    return "weak"


def suggest_csp_improvements(csp: ParsedCSP) -> List[str]:
    """
    Suggest improvements for a CSP.

    Args:
        csp: Parsed CSP object

    Returns:
        List of improvement suggestions
    """
    suggestions = []

    if not csp.has_directive("default-src"):
        suggestions.append("Add default-src directive to establish a fallback policy")

    script_src = csp.get_directive("script-src")
    if script_src and script_src.has_unsafe_inline:
        suggestions.append("Replace 'unsafe-inline' with nonce or hash-based CSP for scripts")

    if script_src and script_src.has_unsafe_eval:
        suggestions.append("Remove 'unsafe-eval' and refactor code to avoid eval()")

    if not csp.has_directive("object-src"):
        suggestions.append("Add object-src 'none' to prevent plugin-based attacks")

    if not csp.has_directive("base-uri"):
        suggestions.append("Add base-uri 'self' to prevent base tag hijacking")

    if not csp.has_directive("form-action"):
        suggestions.append("Add form-action directive to restrict form submission targets")

    if not csp.has_directive("frame-ancestors"):
        suggestions.append("Add frame-ancestors directive as a modern replacement for X-Frame-Options")

    if not csp.has_directive("upgrade-insecure-requests"):
        suggestions.append("Consider adding upgrade-insecure-requests to automatically upgrade HTTP to HTTPS")

    for directive_name, unsafe_value in csp.unsafe_directives:
        if "wildcard" in unsafe_value:
            suggestions.append(f"Replace wildcard in {directive_name} with specific allowed origins")

    return suggestions
