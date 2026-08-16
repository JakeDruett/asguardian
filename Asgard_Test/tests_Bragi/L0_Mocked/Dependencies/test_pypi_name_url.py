"""CH-0034: PyPI package names must be PEP 503 normalized and quoted."""

import json
from urllib.request import Request

import pytest

from Asgard.Bragi.Dependencies.models.license_models import LicenseConfig
from Asgard.Bragi.Dependencies.services import license_checker as lc
from Asgard.Bragi.Dependencies.services.license_checker import (
    LicenseChecker,
    PyPIHostRedirectHandler,
    normalize_pypi_name,
)


def _boom(*_a, **_k):
    raise AssertionError("urlopen must not be called")


class TestNormalizePypiName:
    def test_pep503_collapses_underscores_and_case(self):
        assert normalize_pypi_name("Some_Package") == "some-package"

    def test_pep503_collapses_dots_and_runs(self):
        assert normalize_pypi_name("Foo.Bar__Baz") == "foo-bar-baz"

    def test_rejects_empty(self):
        with pytest.raises(ValueError):
            normalize_pypi_name("")
        with pytest.raises(ValueError):
            normalize_pypi_name("   ")

    @pytest.mark.parametrize("name", ["foo/bar", "../evil", "foo bar", "foo?x", "foo#x", "foo@bar"])
    def test_rejects_path_query_and_foreign_chars(self, name):
        with pytest.raises(ValueError):
            normalize_pypi_name(name)


class TestGetLicenseFromPypiNameGuard:
    def test_slash_dotdot_space_never_open(self, monkeypatch):
        monkeypatch.setattr(lc.urllib.request, "urlopen", _boom)
        monkeypatch.setattr(lc, "_open_pypi_url", _boom)
        checker = LicenseChecker(LicenseConfig())
        for name in ("foo/bar", "..", "foo bar"):
            assert checker._get_license_from_pypi(name) is None

    def test_normalized_name_used_in_url(self, monkeypatch):
        captured = []

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *_a):
                return False

            def read(self):
                return json.dumps({
                    "info": {
                        "version": "1.0",
                        "license": "MIT",
                        "classifiers": [],
                    }
                }).encode()

        def fake_open(url, timeout=10):
            captured.append(url)
            return _Resp()

        monkeypatch.setattr(lc, "_open_pypi_url", fake_open)
        monkeypatch.setattr(lc.urllib.request, "urlopen", _boom)
        checker = LicenseChecker(LicenseConfig())
        result = checker._get_license_from_pypi("Some_Package")
        assert result is not None
        assert captured == ["https://pypi.org/pypi/some-package/json"]
        assert result.source == "pypi"
        assert result.package_name == "Some_Package"


class TestPypiRedirectGuard:
    def test_http_evil_redirect_refused(self):
        handler = PyPIHostRedirectHandler()
        req = Request("https://pypi.org/pypi/foo/json")
        assert handler.redirect_request(
            req, None, 302, "Found", {}, "http://evil/x"
        ) is None

    def test_off_host_https_redirect_refused(self):
        handler = PyPIHostRedirectHandler()
        req = Request("https://pypi.org/pypi/foo/json")
        assert handler.redirect_request(
            req, None, 302, "Found", {}, "https://evil.example/x"
        ) is None

    def test_same_host_https_redirect_allowed(self):
        handler = PyPIHostRedirectHandler()
        req = Request("https://pypi.org/pypi/foo/json")
        followed = handler.redirect_request(
            req, None, 302, "Found", {}, "https://pypi.org/pypi/foo/json"
        )
        assert followed is not None
        assert followed.full_url.startswith("https://pypi.org/")
