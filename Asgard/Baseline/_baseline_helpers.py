"""
Baseline Manager - Helper Functions

Standalone helper functions used by BaselineManager.
"""

import hashlib
import hmac
from pathlib import Path
from typing import Any, Callable, Optional

_MESSAGE_HASH_PREFIX = "sha256:"
_MESSAGE_HASH_HEX_LEN = 64
_SENSITIVE_MESSAGE_ATTRS = ("description", "import_statement", "code_snippet")


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


def is_message_hash(message: str) -> bool:
    """True when *message* is a persistable identity digest."""
    text = (message or "").strip()
    if not text.startswith(_MESSAGE_HASH_PREFIX):
        return False
    digest = text[len(_MESSAGE_HASH_PREFIX):]
    return len(digest) == _MESSAGE_HASH_HEX_LEN and all(
        c in "0123456789abcdef" for c in digest
    )


def hash_violation_message(message: str) -> str:
    """Stable, idempotent digest of a violation identity string."""
    text = (message or "").strip()
    if not text:
        return ""
    if is_message_hash(text):
        return text
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{_MESSAGE_HASH_PREFIX}{digest}"


def messages_match(stored: str, query: str) -> bool:
    """Compare stored and query identities after the same persist hash."""
    left = hash_violation_message(stored)
    right = hash_violation_message(query)
    if not left or not right:
        return False
    return hmac.compare_digest(left, right)


def persistable_violation_message(message: str, violation_id: str) -> str:
    """Non-empty hashed identity so fuzzy match cannot use blanks as wildcards."""
    stripped = (message or "").strip()
    if not stripped:
        stripped = (violation_id or "").strip()
    return hash_violation_message(stripped)


def get_violation_message(
    violation: Any,
    redact: Optional[Callable[[str, str], str]] = None,
) -> str:
    """Extract a stable non-empty identity key from a violation object.

    SecretFinding has no message/description; fall back to pattern_name plus
    masked_value (never the raw secret), then violation_id.

    ``description`` / ``import_statement`` / ``code_snippet`` are not returned
    raw unless *redact* yields a replacement; otherwise they are hashed.
    """
    value = _attr_text(violation, "message")
    if value:
        return value

    for attr in _SENSITIVE_MESSAGE_ATTRS:
        value = _attr_text(violation, attr)
        if not value:
            continue
        if redact is not None:
            redacted = (redact(attr, value) or "").strip()
            if redacted:
                return redacted
            continue
        return hash_violation_message(value)

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
