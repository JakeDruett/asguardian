"""
URL/host policy for FutureItems network tools (CWE-918).

Standalone: do not import Asgard. Only http/https. Loopback, RFC1918,
link-local, metadata, and other non-global addresses are blocked unless
allow_internal is set. Hostnames are resolved and every A/AAAA is checked.
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
        raise ConnectionError(f"Failed to resolve target host {host!r}: {exc}") from exc
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


def _normalize_url(url: str) -> str:
    candidate = (url or "").strip()
    if not candidate:
        raise ValueError("Target URL is required")
    parsed = urlparse(candidate)
    if parsed.scheme:
        return candidate
    if candidate.startswith("//"):
        return "https:" + candidate
    return "https://" + candidate


def _check_resolved_ips(
    host: str,
    *,
    allow_internal: bool,
    resolver: Optional[Callable[[str], Sequence[str]]],
    resolve_host: bool,
) -> None:
    if not allow_internal and _is_blocked_hostname(host):
        raise ValueError(f"Refusing target blocked host: {host}")

    literal = _parse_literal_ip(host)
    if literal is not None:
        if not allow_internal and _is_blocked_ip(literal):
            raise ValueError(
                f"Refusing target internal or metadata address: {literal}"
            )
        return

    if not resolve_host:
        return

    try:
        ips = _host_ips(host, resolver or _default_resolver)
    except ConnectionError:
        if not allow_internal:
            raise ValueError(f"Could not resolve target host: {host}") from None
        raise

    if not ips:
        raise ValueError(f"Could not resolve target host: {host}")

    if not allow_internal:
        for ip in ips:
            if _is_blocked_ip(ip):
                raise ValueError(
                    f"Refusing target internal or metadata address: {ip}"
                )


def validate_target_url(
    url: str,
    *,
    allow_internal: bool = False,
    require_https: bool = False,
    resolver: Optional[Callable[[str], Sequence[str]]] = None,
    resolve_host: bool = True,
) -> str:
    """
    Reject non-http(s) schemes and internal/metadata targets.

    Bare hosts (no scheme) are treated as https. DNS failures fail closed
    unless allow_internal is set.

    Returns the scheme-normalized URL.
    """
    candidate = _normalize_url(url)
    parsed = urlparse(candidate)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        shown = scheme or "missing"
        raise ValueError(f"Target URL scheme must be http or https, got {shown!r}")
    if require_https and scheme != "https":
        raise ValueError("Target URL scheme must be https")

    host = parsed.hostname
    if not host:
        raise ValueError("Target URL is missing a host")

    _check_resolved_ips(
        host,
        allow_internal=allow_internal,
        resolver=resolver,
        resolve_host=resolve_host,
    )
    return candidate


def validate_target_host(
    host: str,
    *,
    allow_internal: bool = False,
    resolver: Optional[Callable[[str], Sequence[str]]] = None,
    resolve_host: bool = True,
) -> str:
    """Reject internal/metadata hosts. Returns the parsed hostname."""
    raw = (host or "").strip()
    if not raw:
        raise ValueError("Target host is required")
    if "://" in raw:
        raise ValueError("Target host must not include a URL scheme")

    parsed = urlparse("https://" + raw)
    name = parsed.hostname
    if not name:
        raise ValueError("Target host is missing")

    _check_resolved_ips(
        name,
        allow_internal=allow_internal,
        resolver=resolver,
        resolve_host=resolve_host,
    )
    return name


class SafeRedirectHandler(HTTPRedirectHandler):
    """Re-validate each redirect Location against the same target policy."""

    def __init__(self, allow_internal: bool = False) -> None:
        self.allow_internal = allow_internal

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_target_url(newurl, allow_internal=self.allow_internal)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def build_safe_opener(*, allow_internal: bool = False) -> OpenerDirector:
    """HTTP(S) opener without file/ftp/data handlers; redirects are re-checked."""
    opener = OpenerDirector()
    opener.add_handler(ProxyHandler())
    opener.add_handler(UnknownHandler())
    opener.add_handler(HTTPDefaultErrorHandler())
    opener.add_handler(HTTPHandler())
    opener.add_handler(HTTPSHandler())
    opener.add_handler(HTTPErrorProcessor())
    opener.add_handler(SafeRedirectHandler(allow_internal=allow_internal))
    return opener
