"""CH-0111: SSL checker verifies certificates by default."""

import ssl
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

SSLChecker = SourceFileLoader(
    "ssl_checker_ch0111",
    str(Path(__file__).resolve().parents[2] / "_FutureItems-Security" / "Tools_Security" / "ssl_checker.py"),
).load_module().SSLChecker


def test_default_verify_uses_cert_required():
    captured = {}
    real = ssl.create_default_context

    def _capture():
        ctx = real()
        captured["ctx"] = ctx
        return ctx

    with mock.patch("ssl.create_default_context", _capture), mock.patch(
        "socket.create_connection", side_effect=ssl.SSLCertVerificationError("bad chain")
    ):
        result = SSLChecker().check_certificate("example.invalid", 443)

    assert captured["ctx"].verify_mode == ssl.CERT_REQUIRED
    assert result["unauthenticated_peek"] is False
    assert result["score"] < 100
    assert any("SSL" in issue or "Error" in issue or "verify" in issue.lower() for issue in result["issues"])


def test_insecure_peek_disables_verify():
    captured = {}
    real = ssl.create_default_context

    def _capture():
        ctx = real()
        captured["ctx"] = ctx
        return ctx

    with mock.patch("ssl.create_default_context", _capture), mock.patch(
        "socket.create_connection", side_effect=OSError("no connect")
    ):
        result = SSLChecker().check_certificate("example.invalid", 443, verify=False)

    assert captured["ctx"].verify_mode == ssl.CERT_NONE
    assert result["unauthenticated_peek"] is True
    assert any("unauthenticated peek" in issue for issue in result["issues"])
