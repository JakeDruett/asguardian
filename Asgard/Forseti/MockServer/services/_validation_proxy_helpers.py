"""
Validation Proxy Helpers - path-template matching for `forseti mock proxy` (plan 06-B.2).

Pure, stdlib-only helpers so the proxy's routing logic is testable without
binding a real socket.
"""

import re
from typing import Optional
from urllib.parse import unquote, urlsplit

from Asgard.Forseti.LiveContract.models.live_contract_models import ProbeOperation

_PARAM_RE = re.compile(r"\{([^/{}]+)\}")
_ALLOWED_UPSTREAM_SCHEMES = frozenset({"http", "https"})
_HOP_BY_HOP = frozenset({
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-length",
})


def validate_upstream_url(upstream: str) -> str:
    """Require an http(s) upstream with a host. Returns stripped form."""
    raw = (upstream or "").strip()
    parsed = urlsplit(raw)
    if parsed.scheme.lower() not in _ALLOWED_UPSTREAM_SCHEMES:
        raise ValueError("upstream must be an http or https URL")
    if not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("upstream must include a host and no userinfo")
    return raw.rstrip("/")


def sanitize_proxy_path(path: str) -> str:
    """Return a request path that cannot rewrite the upstream authority."""
    raw = path or "/"
    if raw.startswith("//") or "://" in raw:
        raise ValueError("absolute or scheme-relative paths are refused")
    if not raw.startswith("/"):
        raw = "/" + raw
    parsed = urlsplit(raw)
    if parsed.scheme or parsed.netloc:
        raise ValueError("path must not include a scheme or host")
    decoded = unquote(parsed.path)
    parts = [part for part in decoded.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        raise ValueError("path traversal is refused")
    return raw


def strip_hop_by_hop_headers(headers: dict[str, str]) -> dict[str, str]:
    """Drop hop-by-hop headers before forwarding."""
    extra: set[str] = set()
    for key, value in headers.items():
        if key.lower() == "connection":
            extra.update(token.strip().lower() for token in value.split(",") if token.strip())
    blocked = _HOP_BY_HOP | extra
    return {k: v for k, v in headers.items() if k.lower() not in blocked}


def path_template_to_regex(template: str) -> re.Pattern:
    """Convert an OpenAPI path template (`/users/{id}`) into a matching regex."""
    escaped = re.escape(template)
    # re.escape turns `{` and `}` into `\{`/`\}`; undo that before substituting.
    escaped = escaped.replace(r"\{", "{").replace(r"\}", "}")
    pattern = _PARAM_RE.sub(lambda m: f"(?P<{re.sub(r'[^A-Za-z0-9_]', '_', m.group(1))}>[^/]+)", escaped)
    return re.compile(f"^{pattern}$")


def match_operation(
    operations: list[ProbeOperation], method: str, raw_path: str
) -> Optional[ProbeOperation]:
    """Find the ProbeOperation matching an incoming request's method + path.

    Exact (non-templated) paths are preferred over templated ones when both
    would match, so `/users/active` beats `/users/{id}`.
    """
    path = urlsplit(raw_path).path
    method_upper = method.upper()
    candidates = [op for op in operations if op.method.upper() == method_upper]

    literal_matches = [op for op in candidates if "{" not in op.path and op.path == path]
    if literal_matches:
        return literal_matches[0]

    templated = [op for op in candidates if "{" in op.path]
    for op in templated:
        if path_template_to_regex(op.path).match(path):
            return op
    return None
