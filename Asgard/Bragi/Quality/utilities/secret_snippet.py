"""Mask credential literals in quality-rule snippets (CH-0043 / CH-0079)."""

import re
from typing import Optional

from Asgard.Heimdall.Security.utilities.security_utils import mask_secret

_QUOTED_LITERAL = re.compile(r"""(["'])((?:\\.|(?!\1).)*)\1""")


def unwrap_quoted(value: str) -> str:
    """Strip one matching pair of surrounding quotes, if present."""
    if len(value) >= 2 and value[0] in "'\"" and value[-1] == value[0]:
        return value[1:-1]
    return value


def mask_quoted_literals(line: str) -> str:
    """Replace quoted string contents with a last-2 / length-only mask."""
    if not line:
        return line

    def _replace(match: re.Match) -> str:
        quote, value = match.group(1), match.group(2)
        return f"{quote}{mask_secret(value)}{quote}"

    return _QUOTED_LITERAL.sub(_replace, line)


def mask_stored_secret(value: Optional[str]) -> Optional[str]:
    """Mask a stored default/secret, preserving surrounding quotes."""
    if value is None or value == "":
        return value
    if len(value) >= 2 and value[0] in "'\"" and value[-1] == value[0]:
        return f"{value[0]}{mask_secret(value[1:-1])}{value[-1]}"
    return mask_secret(value)


def redact_secret_in_text(text: str, secret: Optional[str]) -> str:
    """Replace occurrences of ``secret`` with a CH-0079 mask."""
    if not text or not secret:
        return text or ""
    raw = unwrap_quoted(secret)
    if not raw:
        return text
    return text.replace(raw, mask_secret(raw))
