"""L0 tests for live-contract URL join / redirect guards (CH-0063)."""

import pytest

from Asgard.Forseti.LiveContract.services._dependency_helpers import extract_operations
from Asgard.Forseti.LiveContract.services._url_safety import (
    SameHostRedirectHandler,
    encode_path_param,
    join_probe_url,
)


class TestJoinProbeUrl:
    def test_joins_root_relative_path(self):
        assert join_probe_url("http://api.example/v1", "/users") == "http://api.example/users"

    def test_rejects_userinfo_rewrite(self):
        with pytest.raises(ValueError):
            join_probe_url("http://intended.example", "@attacker.example/")

    def test_rejects_absolute_url_path(self):
        with pytest.raises(ValueError):
            join_probe_url("http://intended.example", "http://attacker.example/")

    def test_rejects_scheme_relative_path(self):
        with pytest.raises(ValueError):
            join_probe_url("http://intended.example", "//attacker.example/x")

    def test_rejects_file_base(self):
        with pytest.raises(ValueError):
            join_probe_url("file:///tmp", "/x")

    def test_encoded_at_cannot_rewrite_host(self):
        encoded = encode_path_param("@attacker.example")
        url = join_probe_url("http://intended.example", f"/{encoded}")
        assert url.startswith("http://intended.example/")
        assert "attacker.example" not in url.split("/")[2]


class TestExtractOperationsPathJail:
    def test_skips_paths_that_do_not_start_with_slash(self):
        ops = extract_operations({
            "paths": {
                "@evil/x": {"get": {"operationId": "bad", "responses": {"200": {}}}},
                "/ok": {"get": {"operationId": "good", "responses": {"200": {}}}},
            }
        })
        assert [op.operation_id for op in ops] == ["good"]


class TestSameHostRedirects:
    def test_off_host_redirect_dropped(self):
        handler = SameHostRedirectHandler()
        req = type("Req", (), {"full_url": "http://api.example/a"})()
        assert handler.redirect_request(req, None, 302, "Found", {}, "http://evil.example/x") is None
        assert handler.redirect_request(req, None, 302, "Found", {}, "file:///etc/passwd") is None
