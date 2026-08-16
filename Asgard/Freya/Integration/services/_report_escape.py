"""
HTML/XML escaping for Freya reports (CWE-79).

Page-controlled strings (WCAG messages, selectors, URLs, screenshot
paths) must never be interpolated raw into HTML or JUnit XML.
"""

from __future__ import annotations

import html
import json
import re
from urllib.parse import urlparse

_ALLOWED_URL_SCHEMES = frozenset({"http", "https"})
_CSS_TOKEN_RE = re.compile(r"^[a-z0-9_-]+$")
_ALLOWED_CSS_TOKENS = frozenset({
    "blocker",
    "critical",
    "serious",
    "major",
    "moderate",
    "minor",
    "info",
    "passed",
    "pass",
    "failed",
    "present",
    "missing",
    "invalid",
    "weak",
    "present_needs_verification",
    "misconfigured",
})


def esc(value: object) -> str:
    """HTML/XML-escape text and quoted attribute values."""
    if value is None:
        return ""
    text = "".join(ch for ch in str(value) if ord(ch) >= 32 or ch in "\t\n\r")
    return html.escape(text, quote=True)


def json_for_script(value: object) -> str:
    """JSON that cannot break out of a <script> element."""
    return (
        json.dumps(value)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )


def safe_css_token(value: object, default: str = "") -> str:
    """Allowlist a CSS class token. Reject anything that is not [a-z0-9_-]."""
    raw = str(value or "").strip().lower()
    if raw in _ALLOWED_CSS_TOKENS or _CSS_TOKEN_RE.fullmatch(raw):
        return raw
    return default


def _has_forbidden_chars(raw: str) -> bool:
    return any(ord(c) < 32 for c in raw)


def safe_href(url: object) -> str:
    """Escaped http(s) URL, or empty string if the scheme is not allowlisted."""
    raw = str(url or "").strip()
    if not raw or _has_forbidden_chars(raw):
        return ""
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_URL_SCHEMES or not parsed.netloc:
        return ""
    return esc(raw)


def safe_src(path: object) -> str:
    """
    Escaped http(s) URL or scheme-less local path for img src.

    Rejects javascript:/data:/file:/protocol-relative URLs and '..' segments.
    """
    raw = str(path or "").strip()
    if not raw or _has_forbidden_chars(raw):
        return ""
    if "\\" in raw:
        raw = raw.replace("\\", "/")
    if raw.startswith("//"):
        return ""
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "").lower()
    if scheme in _ALLOWED_URL_SCHEMES:
        if not parsed.netloc:
            return ""
        return esc(raw)
    if scheme and not (len(scheme) == 1 and scheme.isalpha()):
        return ""
    parts = [p for p in raw.split("/") if p not in ("", ".")]
    if ".." in parts:
        return ""
    return esc(raw)


def html_link(url: object) -> str:
    """Escaped URL text; href only when the URL is http(s)."""
    text = esc(url)
    href = safe_href(url)
    if not href:
        return text
    return f'<a href="{href}" target="_blank" rel="noopener noreferrer">{text}</a>'
