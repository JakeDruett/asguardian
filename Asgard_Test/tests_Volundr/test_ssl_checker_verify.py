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


def test_protocol_probe_verifies_by_default():
    captured = {}

    class _Ctx:
        def __init__(self):
            self.verify_mode = ssl.CERT_NONE
            self.check_hostname = False
            captured["ctx"] = self

        def load_default_certs(self):
            captured["loaded"] = True

        def wrap_socket(self, sock, server_hostname=None):
            raise ssl.SSLCertVerificationError("bad chain")

    with mock.patch("ssl.SSLContext", return_value=_Ctx()) as ctx_ctor, mock.patch(
        "socket.create_connection", return_value=mock.MagicMock()
    ):
        result = SSLChecker().check_protocol_support("example.invalid", 443)

    assert ctx_ctor.called
    assert captured.get("loaded") is True
    assert captured["ctx"].verify_mode == ssl.CERT_REQUIRED
    assert captured["ctx"].check_hostname is True
    assert result["unauthenticated_peek"] is False
    proto_values = [v for k, v in result.items() if k != "unauthenticated_peek"]
    assert proto_values
    assert all(v is False or v == "Not available" or v == "Error" for v in proto_values)


def test_protocol_probe_insecure_is_labeled():
    class _Ctx:
        def __init__(self):
            self.verify_mode = ssl.CERT_REQUIRED
            self.check_hostname = True

        def wrap_socket(self, sock, server_hostname=None):
            raise OSError("no connect")

    with mock.patch("ssl.SSLContext", return_value=_Ctx()), mock.patch(
        "socket.create_connection", return_value=mock.MagicMock()
    ):
        result = SSLChecker().check_protocol_support(
            "example.invalid", 443, verify=False
        )

    assert result["unauthenticated_peek"] is True
