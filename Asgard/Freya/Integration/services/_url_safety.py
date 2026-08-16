"""
URL policy for Freya crawler navigation (CWE-918).

Only http/https are allowed. Loopback, RFC1918, link-local, metadata, and
other non-global addresses are blocked unless allow_internal is set.
Hostnames are re-checked after navigation via page.url.
"""

from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Sequence
from typing import Any, Optional
from urllib.parse import urlparse

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
            f"Failed to resolve navigation host {host!r}: {exc}"
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


def validate_navigation_url(
    url: str,
    *,
    allow_internal: bool = False,
    resolver: Optional[Callable[[str], Sequence[str]]] = None,
    resolve_host: bool = True,
) -> None:
    """
    Reject non-http(s) schemes and internal/metadata targets.

    Args:
        url: Candidate navigation or post-redirect page.url.
        allow_internal: Permit loopback, RFC1918, link-local, and metadata.
        resolver: Optional hostname resolver (returns IP strings). Defaults
            to socket.getaddrinfo when resolve_host is True.
        resolve_host: Resolve hostnames and check their addresses. Literal
            IPs and blocked hostnames are always checked.

    Raises:
        ValueError: Scheme, host, or address is not allowed.
        ConnectionError: Hostname could not be resolved.
    """
    candidate = (url or "").strip()
    if not candidate:
        raise ValueError("Navigation URL is required")

    parsed = urlparse(candidate)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        shown = scheme or "missing"
        raise ValueError(
            f"Navigation URL scheme must be http or https, got {shown!r}"
        )

    host = parsed.hostname
    if not host:
        raise ValueError("Navigation URL is missing a host")

    if not allow_internal and _is_blocked_hostname(host):
        raise ValueError(f"Refusing navigation to blocked host: {host}")

    literal = _parse_literal_ip(host)
    if literal is not None:
        if not allow_internal and _is_blocked_ip(literal):
            raise ValueError(
                f"Refusing navigation to internal or metadata address: {literal}"
            )
        return

    if not resolve_host:
        return

    ips = _host_ips(host, resolver or _default_resolver)
    if not ips:
        raise ValueError(f"Could not resolve navigation host: {host}")

    if not allow_internal:
        for ip in ips:
            if _is_blocked_ip(ip):
                raise ValueError(
                    f"Refusing navigation to internal or metadata address: {ip}"
                )


def is_allowed_navigation_url(
    url: str,
    *,
    allow_internal: bool = False,
    resolver: Optional[Callable[[str], Sequence[str]]] = None,
    resolve_host: bool = False,
) -> bool:
    """Return True when url passes the navigation policy."""
    try:
        validate_navigation_url(
            url,
            allow_internal=allow_internal,
            resolver=resolver,
            resolve_host=resolve_host,
        )
    except (ValueError, ConnectionError):
        return False
    return True


async def safe_goto(
    page: Any,
    url: str,
    *,
    allow_internal: bool = False,
    resolver: Optional[Callable[[str], Sequence[str]]] = None,
    resolve_host: bool = False,
    **goto_kwargs: Any,
) -> Any:
    """Validate url, navigate, then re-validate page.url (redirect target)."""
    validate_navigation_url(
        url,
        allow_internal=allow_internal,
        resolver=resolver,
        resolve_host=resolve_host,
    )
    result = await page.goto(url, **goto_kwargs)
    validate_navigation_url(
        page.url,
        allow_internal=allow_internal,
        resolver=resolver,
        resolve_host=resolve_host,
    )
    return result
