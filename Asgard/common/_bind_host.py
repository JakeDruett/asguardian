"""Normalize bind hosts and refuse non-canonical wildcards without --expose."""

from __future__ import annotations

_WILDCARD_BIND_HOSTS = frozenset({
    "0.0.0.0",
    "0",
    "*",
    "::",
    "::0",
})


def normalize_bind_host(host: str | None) -> str:
    """Strip and default empty to localhost. Does not rewrite wildcards."""
    text = "" if host is None else str(host).strip()
    return text or "localhost"


def is_wildcard_bind_host(host: str) -> bool:
    """True for 0.0.0.0 / :: / 0 / ::0 / * (bracketed IPv6 included)."""
    key = (host or "").strip().lower()
    if key.startswith("[") and key.endswith("]"):
        key = key[1:-1]
    return key in _WILDCARD_BIND_HOSTS
