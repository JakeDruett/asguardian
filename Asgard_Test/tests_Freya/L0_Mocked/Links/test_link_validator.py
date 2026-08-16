"""L0 tests: LinkValidator HEAD policy (CH-0071). Mocked httpx, no live network."""

from unittest.mock import AsyncMock

import httpx
import pytest

from Asgard.Freya.Links.models.link_models import LinkConfig, LinkStatus, LinkType
from Asgard.Freya.Links.services.link_validator import LinkValidator

PUBLIC = "https://93.184.216.34/start"
SOURCE = "https://93.184.216.34/"


def _link(url: str, link_type=LinkType.EXTERNAL) -> dict:
    return {"url": url, "href": url, "link_type": link_type, "text": "t", "html": "<a>"}


def _response(status_code: int, location: str | None = None) -> httpx.Response:
    headers = {"location": location} if location is not None else {}
    return httpx.Response(
        status_code,
        headers=headers,
        request=httpx.Request("HEAD", "https://93.184.216.34/"),
    )


def _validator(config: LinkConfig | None = None, client: AsyncMock | None = None) -> LinkValidator:
    validator = LinkValidator(config)
    validator._http_client = client if client is not None else AsyncMock()
    return validator


class TestCheckSingleLinkSchemeAndHost:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://files.example.com/a"])
    async def test_file_and_ftp_skipped_without_head(self, url):
        client = AsyncMock()
        validator = _validator(client=client)
        result = await validator._check_single_link(_link(url, LinkType.OTHER), SOURCE)
        assert result.status == LinkStatus.SKIPPED
        assert "http or https" in (result.error_message or "")
        client.head.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("url", ["http://127.0.0.1/admin", "http://10.1.2.3/secret"])
    async def test_loopback_and_rfc1918_skipped_without_head(self, url):
        client = AsyncMock()
        validator = _validator(client=client)
        result = await validator._check_single_link(_link(url), SOURCE)
        assert result.status == LinkStatus.SKIPPED
        assert "internal or metadata" in (result.error_message or "")
        client.head.assert_not_called()

    @pytest.mark.asyncio
    async def test_loopback_headed_when_allow_internal(self):
        client = AsyncMock()
        client.head = AsyncMock(return_value=_response(200))
        validator = _validator(LinkConfig(allow_internal=True), client=client)
        result = await validator._check_single_link(
            _link("http://127.0.0.1/admin"), SOURCE
        )
        assert result.status == LinkStatus.OK
        client.head.assert_awaited_once_with("http://127.0.0.1/admin")

    @pytest.mark.asyncio
    async def test_rfc1918_headed_when_allow_internal(self):
        client = AsyncMock()
        client.head = AsyncMock(return_value=_response(200))
        validator = _validator(LinkConfig(allow_internal=True), client=client)
        result = await validator._check_single_link(
            _link("http://10.0.0.1/internal"), SOURCE
        )
        assert result.status == LinkStatus.OK
        client.head.assert_awaited_once_with("http://10.0.0.1/internal")

    @pytest.mark.asyncio
    async def test_file_still_skipped_when_allow_internal(self):
        client = AsyncMock()
        validator = _validator(LinkConfig(allow_internal=True), client=client)
        result = await validator._check_single_link(
            _link("file:///etc/passwd", LinkType.OTHER), SOURCE
        )
        assert result.status == LinkStatus.SKIPPED
        client.head.assert_not_called()

    @pytest.mark.asyncio
    async def test_public_http_is_headed(self):
        client = AsyncMock()
        client.head = AsyncMock(return_value=_response(200))
        validator = _validator(client=client)
        result = await validator._check_single_link(_link(PUBLIC), SOURCE)
        assert result.status == LinkStatus.OK
        assert result.status_code == 200
        client.head.assert_awaited_once_with(PUBLIC)


class TestRedirectLocationPolicy:
    @pytest.mark.asyncio
    async def test_redirect_to_file_not_followed(self):
        client = AsyncMock()
        client.head = AsyncMock(return_value=_response(302, "file:///etc/passwd"))
        validator = _validator(client=client)
        result = await validator._check_single_link(_link(PUBLIC), SOURCE)
        assert result.status == LinkStatus.REDIRECT
        assert result.status_code == 302
        assert "file" in (result.error_message or "").lower()
        assert result.final_url is None
        client.head.assert_awaited_once_with(PUBLIC)

    @pytest.mark.asyncio
    async def test_redirect_to_rfc1918_not_followed(self):
        client = AsyncMock()
        client.head = AsyncMock(return_value=_response(302, "http://10.0.0.1/loot"))
        validator = _validator(client=client)
        result = await validator._check_single_link(_link(PUBLIC), SOURCE)
        assert result.status == LinkStatus.REDIRECT
        assert "internal or metadata" in (result.error_message or "")
        client.head.assert_awaited_once_with(PUBLIC)
        headed = [call.args[0] for call in client.head.await_args_list]
        assert "http://10.0.0.1/loot" not in headed

    @pytest.mark.asyncio
    async def test_redirect_to_loopback_not_followed(self):
        client = AsyncMock()
        client.head = AsyncMock(return_value=_response(302, "http://127.0.0.1/"))
        validator = _validator(client=client)
        result = await validator._check_single_link(_link(PUBLIC), SOURCE)
        assert result.status == LinkStatus.REDIRECT
        client.head.assert_awaited_once_with(PUBLIC)

    @pytest.mark.asyncio
    async def test_protocol_relative_rfc1918_location_not_followed(self):
        client = AsyncMock()
        client.head = AsyncMock(return_value=_response(302, "//10.0.0.1/x"))
        validator = _validator(client=client)
        result = await validator._check_single_link(_link(PUBLIC), SOURCE)
        assert result.status == LinkStatus.REDIRECT
        headed = [call.args[0] for call in client.head.await_args_list]
        assert headed == [PUBLIC]

    @pytest.mark.asyncio
    async def test_safe_redirect_is_followed(self):
        dest = "https://93.184.216.34/next"

        async def _head(url: str) -> httpx.Response:
            if url == PUBLIC:
                return _response(302, dest)
            if url == dest:
                return _response(200)
            raise AssertionError(f"unexpected HEAD {url}")

        client = AsyncMock()
        client.head = AsyncMock(side_effect=_head)
        validator = _validator(client=client)
        result = await validator._check_single_link(_link(PUBLIC), SOURCE)
        assert result.status == LinkStatus.REDIRECT
        assert result.final_url == dest
        assert result.redirect_count == 1
        assert [call.args[0] for call in client.head.await_args_list] == [PUBLIC, dest]

    @pytest.mark.asyncio
    async def test_hostname_resolving_to_rfc1918_not_headed(self):
        client = AsyncMock()
        validator = LinkValidator(resolver=lambda _host: ["10.0.0.8"])
        validator._http_client = client
        result = await validator._check_single_link(
            _link("https://evil.example.com/ssrf"), SOURCE
        )
        assert result.status == LinkStatus.SKIPPED
        client.head.assert_not_called()
