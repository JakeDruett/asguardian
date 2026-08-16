"""CH-0075: Heimdall DNS checker domain allowlist."""

import pytest

from Asgard.Heimdall.Security.DNS.services.dns_checker import validate_dns_domain


def test_rejects_at_server_injection():
    with pytest.raises(ValueError):
        validate_dns_domain("@evil")


def test_rejects_leading_dash():
    with pytest.raises(ValueError):
        validate_dns_domain("-f")


def test_accepts_hostname():
    assert validate_dns_domain("example.com") == "example.com"
