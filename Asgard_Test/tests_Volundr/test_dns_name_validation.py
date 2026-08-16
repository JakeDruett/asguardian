"""CH-0113: DNS checker hostname validation."""

import pytest

from importlib.machinery import SourceFileLoader
from pathlib import Path

_MOD = SourceFileLoader(
    "dns_security_checker",
    str(Path(__file__).resolve().parents[2] / "_FutureItems-Security" / "Tools_Security" / "dns_security_checker.py"),
).load_module()


def test_rejects_option_and_server_injection():
    with pytest.raises(ValueError):
        _MOD.validate_dns_name("-f")
    with pytest.raises(ValueError):
        _MOD.validate_dns_name("@/etc/passwd")


def test_accepts_hostname():
    assert _MOD.validate_dns_name("example.com") == "example.com"
