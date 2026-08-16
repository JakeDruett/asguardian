"""CH-0112: FutureItems URL/host allowlist (CWE-918)."""

import sys

import pytest

from importlib.machinery import SourceFileLoader
from pathlib import Path

_TOOLS = Path(__file__).resolve().parents[2] / "_FutureItems-Security" / "Tools_Security"
if str(_TOOLS) not in sys.path:
    sys.path.insert(0, str(_TOOLS))

_URL = SourceFileLoader("_url_safety", str(_TOOLS / "_url_safety.py")).load_module()
_CORS = SourceFileLoader("cors_checker", str(_TOOLS / "cors_checker.py")).load_module()
_PORT = SourceFileLoader("port_scanner", str(_TOOLS / "port_scanner.py")).load_module()
_HEADERS = SourceFileLoader(
    "http_security_headers", str(_TOOLS / "http_security_headers.py")
).load_module()


def test_metadata_link_local_rejected():
    with pytest.raises(ValueError):
        _URL.validate_target_url("http://169.254.169.254/")


def test_loopback_rejected_unless_allow_internal():
    with pytest.raises(ValueError):
        _URL.validate_target_url("http://127.0.0.1/")
    _URL.validate_target_url("http://127.0.0.1/", allow_internal=True)


def test_file_scheme_rejected():
    with pytest.raises(ValueError):
        _URL.validate_target_url("file:///etc/passwd")


def test_https_example_accepted_without_resolve():
    normalized = _URL.validate_target_url("https://example.com", resolve_host=False)
    assert normalized == "https://example.com"


def test_cors_rejects_metadata_before_urlopen(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("urlopen must not be called")

    monkeypatch.setattr(_CORS.urllib.request, "urlopen", _boom)
    with pytest.raises(ValueError):
        _CORS.CORSChecker().check_cors("http://169.254.169.254/")


def test_headers_rejects_metadata_before_urlopen(monkeypatch):
    def _boom(*_a, **_k):
        raise AssertionError("urlopen must not be called")

    monkeypatch.setattr(_HEADERS.urllib.request, "urlopen", _boom)
    with pytest.raises(ValueError):
        _HEADERS.HTTPSecurityHeadersChecker().check_url("http://169.254.169.254/")


def test_port_scanner_rejects_metadata():
    scanner = _PORT.PortScanner()
    with pytest.raises(ValueError):
        scanner.scan_host("169.254.169.254", [80])
    with pytest.raises(ValueError):
        scanner.scan_port("169.254.169.254", 80)
    with pytest.raises(ValueError):
        scanner.get_banner("169.254.169.254", 80)


def test_redirect_to_metadata_is_rejected():
    handler = _URL.SafeRedirectHandler(allow_internal=False)
    with pytest.raises(ValueError):
        handler.redirect_request(
            None, None, 302, "Found", {}, "http://169.254.169.254/latest/meta-data/"
        )


def test_workers_capped_at_32():
    assert _PORT.MAX_WORKERS == 32
    assert _PORT.DEFAULT_WORKERS == 16
    assert _PORT.clamp_workers(100) == 32
    assert _PORT.clamp_workers(33) == 32
    assert _PORT.clamp_workers(16) == 16
