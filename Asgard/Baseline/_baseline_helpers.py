"""
Baseline Manager - Helper Functions

Standalone helper functions used by BaselineManager.
"""

import hashlib
from pathlib import Path
from typing import Any


def relative_path(project_path: Path, path: str) -> str:
    """Convert absolute path to relative path."""
    try:
        return str(Path(path).relative_to(project_path))
    except ValueError:
        return path


def _attr_text(obj: Any, name: str) -> str:
    if not hasattr(obj, name):
        return ""
    return str(getattr(obj, name, "") or "").strip()


def is_usable_fuzzy_message(message: str) -> bool:
    """Empty or whitespace keys are not identities for fuzzy match."""
    return bool((message or "").strip())


def persistable_violation_message(message: str, violation_id: str) -> str:
    """Replace empty/whitespace messages so fuzzy match cannot use them as wildcards."""
    stripped = (message or "").strip()
    if stripped:
        return stripped
    return (violation_id or "").strip()


def get_violation_message(violation: Any) -> str:
    """Extract a stable non-empty identity key from a violation object.

    SecretFinding has no message/description; fall back to pattern_name plus
    masked_value (never the raw secret), then violation_id.
    """
    for attr in ("message", "description", "import_statement", "code_snippet"):
        value = _attr_text(violation, attr)
        if value:
            return value

    pattern = _attr_text(violation, "pattern_name")
    masked = _attr_text(violation, "masked_value")
    if pattern and masked:
        return f"{pattern}:{masked}"
    if pattern:
        return pattern
    if masked:
        return masked

    return _attr_text(violation, "violation_id")


def generate_violation_id(
    file_path: str,
    line_number: int,
    violation_type: str,
    message: str,
) -> str:
    """Generate a unique ID for a violation."""
    content = f"{file_path}:{line_number}:{violation_type}:{message}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]
