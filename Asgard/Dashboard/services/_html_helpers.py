"""
Asgard Dashboard HTML Helpers

Utility functions for generating HTML fragments in the web dashboard.
"""

import html
from pathlib import Path

_ALLOWED_SEVERITY = frozenset({"critical", "high", "medium", "low", "info"})
_ALLOWED_STATUS = frozenset(
    {"open", "confirmed", "resolved", "false_positive", "wont_fix", "unknown"}
)
_ALLOWED_GATE = frozenset({"passed", "failed", "warning", "unknown", "error", "not_evaluated"})


def esc(value: object) -> str:
    """HTML-escape text and attribute values (quote=True)."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


def truncate_path(file_path: str, components: int = 3) -> str:
    """Return the last N path components of a file path."""
    parts = Path(file_path).parts
    if len(parts) <= components:
        return file_path
    return "/".join(parts[-components:])


def rating_badge(letter: str) -> str:
    """Return an HTML rating badge for a letter grade."""
    raw = (letter or "").upper()
    safe = raw if raw in ("A", "B", "C", "D", "E") else "unknown"
    return f'<span class="rating-badge rating-{safe}">{esc(letter or "?")}</span>'


def severity_badge(severity: str) -> str:
    """Return an HTML severity badge."""
    low = (severity or "").lower()
    css = low if low in _ALLOWED_SEVERITY else "info"
    return f'<span class="sev-badge sev-{css}">{esc((severity or "").upper())}</span>'


def status_badge(status: str) -> str:
    """Return an HTML status badge."""
    low = (status or "").lower()
    css = low if low in _ALLOWED_STATUS else "unknown"
    label = (status or "").replace("_", " ").title()
    return f'<span class="status-badge status-{css}">{esc(label)}</span>'


def gate_badge(status: str) -> str:
    """Return an HTML quality gate badge."""
    low = (status or "unknown").lower()
    css = low if low in _ALLOWED_GATE else "unknown"
    label = (status or "Unknown").upper()
    return f'<span class="gate-badge gate-{css}">{esc(label)}</span>'


def rating_to_score(letter: str) -> int:
    """Convert a letter rating to a numeric score for charting."""
    mapping = {"A": 100, "B": 80, "C": 60, "D": 40, "E": 20}
    return mapping.get((letter or "").upper(), 0)
