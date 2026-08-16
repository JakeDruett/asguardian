"""HCL identifier allowlists and string escaping for generated Terraform."""

from __future__ import annotations

import re

_MODULE_NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")
_HCL_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")


def escape_hcl_string(value: str) -> str:
    """Escape a value for interpolation inside an HCL double-quoted string."""
    text = str(value)
    return (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("${", "$${")
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )


def hcl_quoted(value: str) -> str:
    """Return an HCL double-quoted literal."""
    return f'"{escape_hcl_string(value)}"'


def require_module_name(name: str) -> str:
    text = (name or "").strip()
    if not _MODULE_NAME_RE.fullmatch(text):
        raise ValueError("module name must match ^[a-z][a-z0-9_-]{0,63}$")
    return text


def require_hcl_identifier(name: str, *, kind: str = "identifier") -> str:
    text = (name or "").strip()
    if not _HCL_IDENT_RE.fullmatch(text):
        raise ValueError(f"{kind} must be a Terraform identifier")
    return text
