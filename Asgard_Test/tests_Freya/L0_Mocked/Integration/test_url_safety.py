"""
URL policy tests for Freya crawler navigation (CH-0066 / CWE-918).

No live network. Hostname checks use an injected resolver.
"""

import pytest

from Asgard.Freya.Integration.services._url_safety import (
    is_allowed_navigation_url,
    safe_goto,
    validate_navigation_url,
)
from Asgard.Freya.cli._parser import create_parser

PUBLIC_IP = "93.184.216.34"


def _public_resolver(_host: str) -> list[str]:
    return [PUBLIC_IP]


def _private_resolver(_host: str) -> list[str]:
    return ["10.0.0.1"]


class TestValidateNavigationUrl:
    def test_file_scheme_rejected(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_navigation_url("file:///tmp/rejected")

    def test_javascript_and_mailto_rejected(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_navigation_url("javascript:void(0)")
        with pytest.raises(ValueError, match="http or https"):
            validate_navigation_url("mailto:test@example.com")

    def test_data_scheme_rejected(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_navigation_url("data:text/html,hi")

    def test_loopback_rejected_by_default(self):
        with pytest.raises(ValueError, match="internal or metadata"):
            validate_navigation_url("http://127.0.0.1/")

    def test_rfc1918_rejected_by_default(self):
        with pytest.raises(ValueError, match="internal or metadata"):
            validate_navigation_url("http://10.0.0.1/")

    def test_link_local_metadata_rejected(self):
        with pytest.raises(ValueError, match="internal or metadata"):
            validate_navigation_url("http://169.254.169.254/")

    def test_localhost_hostname_rejected(self):
        with pytest.raises(ValueError, match="blocked host"):
            validate_navigation_url("http://localhost:3000/")

    def test_loopback_allowed_when_internal_opted_in(self):
        validate_navigation_url("http://127.0.0.1/", allow_internal=True)

    def test_rfc1918_allowed_when_internal_opted_in(self):
        validate_navigation_url("http://10.0.0.1/", allow_internal=True)

    def test_file_still_rejected_when_internal_opted_in(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_navigation_url("file:///tmp/rejected", allow_internal=True)

    def test_https_public_ip_allowed(self):
        validate_navigation_url(f"https://{PUBLIC_IP}/")

    def test_https_public_host_allowed_with_resolver(self):
        validate_navigation_url(
            "https://example.com/",
            resolver=_public_resolver,
        )

    def test_hostname_resolving_to_rfc1918_rejected(self):
        with pytest.raises(ValueError, match="internal or metadata"):
            validate_navigation_url(
                "https://internal.example.com/",
                resolver=_private_resolver,
            )

    def test_ipv6_loopback_rejected(self):
        with pytest.raises(ValueError, match="internal or metadata"):
            validate_navigation_url("http://[::1]/")

    def test_decimal_loopback_rejected(self):
        with pytest.raises(ValueError, match="internal or metadata"):
            validate_navigation_url("http://2130706433/")


class TestIsAllowedNavigationUrl:
    def test_file_rejected(self):
        assert is_allowed_navigation_url("file:///tmp/rejected") is False

    def test_loopback_rejected_unless_allow_internal(self):
        assert is_allowed_navigation_url("http://127.0.0.1/") is False
        assert is_allowed_navigation_url(
            "http://127.0.0.1/",
            allow_internal=True,
        ) is True

    def test_javascript_mailto_rejected(self):
        assert is_allowed_navigation_url("javascript:void(0)") is False
        assert is_allowed_navigation_url("mailto:test@example.com") is False


class TestSafeGoto:
    @pytest.mark.asyncio
    async def test_rejects_file_before_goto(self):
        page = type("Page", (), {"goto": None, "url": "https://example.com"})()
        called = False

        async def _goto(*_a, **_k):
            nonlocal called
            called = True

        page.goto = _goto
        with pytest.raises(ValueError, match="http or https"):
            await safe_goto(page, "file:///tmp/rejected")
        assert called is False

    @pytest.mark.asyncio
    async def test_revalidates_redirect_target(self):
        page = type("Page", (), {})()

        async def _goto(url, **_k):
            page.url = "http://127.0.0.1/redirected"
            return None

        page.goto = _goto
        page.url = "https://93.184.216.34/"
        with pytest.raises(ValueError, match="internal or metadata"):
            await safe_goto(page, f"https://{PUBLIC_IP}/")


class TestCrawlAllowInternalFlag:
    def test_allow_internal_flag_parsed(self):
        parser = create_parser()
        args = parser.parse_args(
            ["crawl", "https://example.com", "--allow-internal"]
        )
        assert args.allow_internal is True

    def test_allow_internal_flag_defaults_false(self):
        parser = create_parser()
        args = parser.parse_args(["crawl", "https://example.com"])
        assert args.allow_internal is False
