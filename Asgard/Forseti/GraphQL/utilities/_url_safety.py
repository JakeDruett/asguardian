"""
URL policy for GraphQL introspection (CWE-918).

Only http/https are allowed. Loopback, RFC1918, link-local, metadata, and
other non-global addresses are blocked unless allow_internal is set.
Redirects are re-validated against the same policy. File/FTP/data handlers
are omitted from the opener.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Sequence
from typing import Optional
from urllib.parse import urlparse
from urllib.request import (
    HTTPDefaultErrorHandler,
    HTTPErrorProcessor,
    HTTPHandler,
    HTTPRedirectHandler,
    HTTPSHandler,
    OpenerDirector,
    ProxyHandler,
    UnknownHandler,
)

_ALLOWED_SCHEMES = frozenset({"http", "https"})

_BLOCKED_HOSTNAMES = frozenset({
    "localhost",
    "localhost.localdomain",
    "ip6-localhost",
    "ip6-loopback",
    "metadata",
    "metadata.google.internal",
    "metadata.goog",
})


def _is_blocked_hostname(host: str) -> bool:
    name = host.lower().rstrip(".")
    if name in _BLOCKED_HOSTNAMES:
        return True
    return name.endswith(".localhost") or name.endswith(".local")


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    if isinstance(ip, ipaddress.IPv6Address):
        if ip.ipv4_mapped is not None:
            return _is_blocked_ip(ip.ipv4_mapped)
        if ip.sixtofour is not None:
            return _is_blocked_ip(ip.sixtofour)
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or not ip.is_global
    )


def _parse_literal_ip(host: str) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        pass
    if host.isdigit():
        value = int(host)
        if 0 <= value <= 0xFFFFFFFF:
            return ipaddress.IPv4Address(value)
    if host.lower().startswith("0x"):
        try:
            value = int(host, 16)
        except ValueError:
            return None
        if 0 <= value <= 0xFFFFFFFF:
            return ipaddress.IPv4Address(value)
    return None


def _default_resolver(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError as exc:
        raise ConnectionError(
            f"Failed to resolve introspection host {host!r}: {exc}"
        ) from exc
    addresses: list[str] = []
    seen: set[str] = set()
    for info in infos:
        addr = info[4][0]
        if addr not in seen:
            seen.add(addr)
            addresses.append(addr)
    return addresses


def _host_ips(
    host: str,
    resolver: Callable[[str], Sequence[str]],
) -> list[ipaddress.IPv4Address | ipaddress.IPv6Address]:
    literal = _parse_literal_ip(host)
    if literal is not None:
        return [literal]
    ips: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for addr in resolver(host):
        try:
            ips.append(ipaddress.ip_address(addr))
        except ValueError:
            continue
    return ips


def validate_introspection_url(
    url: str,
    *,
    allow_internal: bool = False,
    resolver: Optional[Callable[[str], Sequence[str]]] = None,
) -> None:
    """
    Reject non-http(s) schemes and internal/metadata targets.

    Args:
        url: Candidate endpoint or redirect Location.
        allow_internal: Permit loopback, RFC1918, link-local, and metadata.
        resolver: Optional hostname resolver (returns IP strings). Defaults
            to socket.getaddrinfo.

    Raises:
        ValueError: Scheme, host, or address is not allowed.
        ConnectionError: Hostname could not be resolved.
    """
    candidate = (url or "").strip()
    if not candidate:
        raise ValueError("Introspection URL is required")

    parsed = urlparse(candidate)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        shown = scheme or "missing"
        raise ValueError(
            f"Introspection URL scheme must be http or https, got {shown!r}"
        )

    host = parsed.hostname
    if not host:
        raise ValueError("Introspection URL is missing a host")

    if not allow_internal and _is_blocked_hostname(host):
        raise ValueError(f"Refusing introspection of blocked host: {host}")

    ips = _host_ips(host, resolver or _default_resolver)
    if not ips:
        raise ValueError(f"Could not resolve introspection host: {host}")

    if not allow_internal:
        for ip in ips:
            if _is_blocked_ip(ip):
                raise ValueError(
                    f"Refusing introspection of internal or metadata address: {ip}"
                )


class SafeRedirectHandler(HTTPRedirectHandler):
    """Re-validate each redirect Location against the introspection URL policy."""

    def __init__(self, allow_internal: bool = False) -> None:
        self.allow_internal = allow_internal

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_introspection_url(newurl, allow_internal=self.allow_internal)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_introspection_opener(*, allow_internal: bool = False) -> OpenerDirector:
    """Build an opener without file/ftp/data handlers; redirects are re-checked."""
    opener = OpenerDirector()
    opener.add_handler(ProxyHandler())
    opener.add_handler(UnknownHandler())
    opener.add_handler(HTTPDefaultErrorHandler())
    opener.add_handler(HTTPHandler())
    opener.add_handler(HTTPSHandler())
    opener.add_handler(HTTPErrorProcessor())
    opener.add_handler(SafeRedirectHandler(allow_internal=allow_internal))
    return opener
