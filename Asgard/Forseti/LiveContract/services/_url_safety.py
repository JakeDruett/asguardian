"""URL join and redirect guards for live contract probes."""

from __future__ import annotations

import urllib.error
import urllib.request
from typing import Optional
from urllib.parse import quote, urljoin, urlsplit

_ALLOWED_SCHEMES = frozenset({"http", "https"})


def join_probe_url(base_url: str, path: str) -> str:
    """Join a probe path onto base_url without rewriting authority.

    Paths must be root-relative (start with a single ``/``). ``urljoin``
    plus a same-host check blocks ``@host`` and absolute-URL path tricks.
    """
    parsed = urlsplit((base_url or "").strip())
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES or not parsed.netloc:
        raise ValueError("base_url must be an http or https URL with a host")
    if parsed.username or parsed.password:
        raise ValueError("base_url must not include userinfo")
    if not path.startswith("/") or path.startswith("//"):
        raise ValueError("probe path must be a root-relative HTTP path")
    if "://" in path:
        raise ValueError("probe path must not include a scheme")
    base = base_url if base_url.endswith("/") else base_url + "/"
    joined = urljoin(base, path)
    dest = urlsplit(joined)
    if dest.scheme.lower() not in _ALLOWED_SCHEMES:
        raise ValueError("joined URL must be http or https")
    if dest.netloc.lower() != parsed.netloc.lower():
        raise ValueError("probe path must not rewrite the base host")
    return joined


def encode_path_param(value: object) -> str:
    """Percent-encode a path parameter so it cannot rewrite authority."""
    return quote(str(value), safe="")


class SameHostRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Follow redirects only when scheme+host+port stay on the original base."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        origin = urlsplit(req.full_url)
        dest = urlsplit(newurl)
        if dest.scheme.lower() not in _ALLOWED_SCHEMES:
            return None
        if (dest.hostname or "").lower() != (origin.hostname or "").lower():
            return None
        origin_port = origin.port or (443 if origin.scheme == "https" else 80)
        dest_port = dest.port or (443 if dest.scheme == "https" else 80)
        if dest_port != origin_port:
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_probe_url(
    request: urllib.request.Request,
    timeout: float,
    context: Optional[object] = None,
):
    """urlopen that refuses off-host redirects."""
    handlers: list[urllib.request.BaseHandler] = [SameHostRedirectHandler()]
    if context is not None:
        handlers.append(urllib.request.HTTPSHandler(context=context))
    opener = urllib.request.build_opener(*handlers)
    return opener.open(request, timeout=timeout)
