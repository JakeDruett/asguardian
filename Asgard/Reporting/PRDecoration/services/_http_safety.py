"""HTTPS-only API base + same-host redirects for PR decoration."""

from __future__ import annotations

from urllib.parse import quote, urlsplit
from urllib.request import HTTPRedirectHandler

_DEFAULT_GITHUB = "https://api.github.com"


def normalize_https_api_base(url: str) -> str:
    parsed = urlsplit((url or "").strip())
    if parsed.scheme.lower() != "https" or not parsed.netloc:
        raise ValueError("API base must be an https URL with a host")
    if parsed.username or parsed.password:
        raise ValueError("API base must not include userinfo")
    path = parsed.path.rstrip("/")
    return f"https://{parsed.netloc}{path}"


def github_api_base(configured: str | None, default: str = _DEFAULT_GITHUB) -> str:
    base = normalize_https_api_base(configured or default)
    if configured is None and base != _DEFAULT_GITHUB:
        raise ValueError("default GitHub API base must be https://api.github.com")
    return base


def quote_owner_repo(repository: str) -> str:
    parts = (repository or "").split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("repository must be owner/repo")
    return f"{quote(parts[0], safe='')}/{quote(parts[1], safe='')}"


def url_on_allowed_origin(url: str, allowed_base: str) -> bool:
    dest = urlsplit(url)
    allowed = urlsplit(allowed_base)
    return (
        dest.scheme.lower() == "https"
        and dest.netloc.lower() == allowed.netloc.lower()
    )


class SameOriginHTTPSRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        origin = urlsplit(req.full_url)
        dest = urlsplit(newurl)
        if dest.scheme.lower() != "https":
            return None
        if (dest.hostname or "").lower() != (origin.hostname or "").lower():
            return None
        return super().redirect_request(req, fp, code, msg, headers, newurl)
