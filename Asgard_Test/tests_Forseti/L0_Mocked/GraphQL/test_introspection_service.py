"""
Tests for GraphQL introspection URL policy (CH-0060 / CWE-918).

All HTTP and DNS are mocked — no network I/O.
"""

import json
import socket
from unittest.mock import MagicMock
from urllib.request import FileHandler, Request

import pytest

from Asgard.Forseti.GraphQL.models.graphql_models import GraphQLConfig
from Asgard.Forseti.GraphQL.services.introspection_service import IntrospectionService
from Asgard.Forseti.GraphQL.utilities._url_safety import (
    SafeRedirectHandler,
    build_introspection_opener,
    validate_introspection_url,
)

PUBLIC_IP = "93.184.216.34"

MINIMAL_INTROSPECTION = {
    "data": {
        "__schema": {
            "queryType": {"name": "Query"},
            "mutationType": None,
            "subscriptionType": None,
            "types": [
                {
                    "kind": "OBJECT",
                    "name": "Query",
                    "fields": [
                        {
                            "name": "hello",
                            "args": [],
                            "type": {
                                "kind": "SCALAR",
                                "name": "String",
                                "ofType": None,
                            },
                            "isDeprecated": False,
                            "deprecationReason": None,
                        }
                    ],
                    "inputFields": None,
                    "interfaces": [],
                    "enumValues": None,
                    "possibleTypes": None,
                }
            ],
            "directives": [],
        }
    }
}


def _public_resolver(_host: str) -> list[str]:
    return [PUBLIC_IP]


def _private_resolver(_host: str) -> list[str]:
    return ["10.0.0.1"]


def _fake_opener(payload: dict) -> MagicMock:
    response = MagicMock()
    response.read.return_value = json.dumps(payload).encode("utf-8")
    response.__enter__.return_value = response
    response.__exit__.return_value = False
    opener = MagicMock()
    opener.open.return_value = response
    return opener


class TestValidateIntrospectionUrl:
    """Scheme and destination policy."""

    def test_file_scheme_rejected(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_introspection_url("file:///etc/passwd")

    def test_ftp_and_data_schemes_rejected(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_introspection_url("ftp://example.com/schema")
        with pytest.raises(ValueError, match="http or https"):
            validate_introspection_url("data:text/plain,hello")

    def test_loopback_rejected_by_default(self):
        with pytest.raises(ValueError, match="internal or metadata"):
            validate_introspection_url("http://127.0.0.1/")

    def test_rfc1918_rejected_by_default(self):
        with pytest.raises(ValueError, match="internal or metadata"):
            validate_introspection_url("http://10.0.0.1/")

    def test_link_local_metadata_rejected(self):
        with pytest.raises(ValueError, match="internal or metadata"):
            validate_introspection_url("http://169.254.169.254/latest/meta-data/")

    def test_localhost_hostname_rejected(self):
        with pytest.raises(ValueError, match="blocked host"):
            validate_introspection_url("http://localhost:4000/graphql")

    def test_loopback_allowed_when_internal_opted_in(self):
        validate_introspection_url("http://127.0.0.1/", allow_internal=True)

    def test_rfc1918_allowed_when_internal_opted_in(self):
        validate_introspection_url("http://10.0.0.1/", allow_internal=True)

    def test_file_still_rejected_when_internal_opted_in(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_introspection_url("file:///etc/passwd", allow_internal=True)

    def test_https_public_ip_allowed(self):
        validate_introspection_url(f"https://{PUBLIC_IP}/graphql")

    def test_https_public_host_allowed_with_resolver(self):
        validate_introspection_url(
            "https://api.example.com/graphql",
            resolver=_public_resolver,
        )

    def test_hostname_resolving_to_rfc1918_rejected(self):
        with pytest.raises(ValueError, match="internal or metadata"):
            validate_introspection_url(
                "https://evil.example.com/graphql",
                resolver=_private_resolver,
            )

    def test_ipv6_loopback_rejected(self):
        with pytest.raises(ValueError, match="internal or metadata"):
            validate_introspection_url("http://[::1]/graphql")

    def test_decimal_loopback_rejected(self):
        with pytest.raises(ValueError, match="internal or metadata"):
            validate_introspection_url("http://2130706433/")


class TestSafeRedirectHandler:
    """Redirect Location is re-checked against the same policy."""

    def test_redirect_to_file_rejected(self):
        handler = SafeRedirectHandler(allow_internal=False)
        req = Request("https://93.184.216.34/graphql")
        with pytest.raises(ValueError, match="http or https"):
            handler.redirect_request(
                req, None, 302, "Found", {}, "file:///etc/passwd"
            )

    def test_redirect_to_rfc1918_rejected(self):
        handler = SafeRedirectHandler(allow_internal=False)
        req = Request("https://93.184.216.34/graphql")
        with pytest.raises(ValueError, match="internal or metadata"):
            handler.redirect_request(
                req, None, 302, "Found", {}, "http://10.0.0.1/graphql"
            )

    def test_redirect_to_loopback_rejected(self):
        handler = SafeRedirectHandler(allow_internal=False)
        req = Request("https://93.184.216.34/graphql")
        with pytest.raises(ValueError, match="internal or metadata"):
            handler.redirect_request(
                req, None, 302, "Found", {}, "http://127.0.0.1/graphql"
            )

    def test_redirect_to_public_https_allowed(self):
        handler = SafeRedirectHandler(allow_internal=False)
        req = Request("https://93.184.216.34/graphql", data=b"{}", method="POST")
        new = handler.redirect_request(
            req, None, 302, "Found", {}, "https://93.184.216.34/v2"
        )
        assert new is not None
        assert new.get_full_url() == "https://93.184.216.34/v2"

    def test_redirect_to_rfc1918_allowed_when_internal_opted_in(self):
        handler = SafeRedirectHandler(allow_internal=True)
        req = Request("http://10.0.0.1/graphql", data=b"{}", method="POST")
        new = handler.redirect_request(
            req, None, 302, "Found", {}, "http://10.0.0.1/v2"
        )
        assert new is not None
        assert new.get_full_url() == "http://10.0.0.1/v2"


class TestBuildIntrospectionOpener:
    def test_opener_omits_file_handler(self):
        opener = build_introspection_opener()
        assert not any(isinstance(h, FileHandler) for h in opener.handlers)
        assert any(isinstance(h, SafeRedirectHandler) for h in opener.handlers)


class TestIntrospectionServicePolicy:
    """Service rejects unsafe endpoints before any request."""

    def test_file_scheme_rejected_without_request(self, monkeypatch):
        monkeypatch.setattr(
            "Asgard.Forseti.GraphQL.services.introspection_service.build_introspection_opener",
            lambda **_k: (_ for _ in ()).throw(
                AssertionError("opener must not be built for file:")
            ),
        )
        with pytest.raises(ValueError, match="http or https"):
            IntrospectionService().introspect("file:///etc/passwd")

    def test_loopback_rejected_unless_allow_internal(self, monkeypatch):
        service = IntrospectionService()
        with pytest.raises(ValueError, match="internal or metadata"):
            service.introspect("http://127.0.0.1/")

        opener = _fake_opener(MINIMAL_INTROSPECTION)
        monkeypatch.setattr(
            "Asgard.Forseti.GraphQL.services.introspection_service.build_introspection_opener",
            lambda **_k: opener,
        )
        schema = service.introspect("http://127.0.0.1/", allow_internal=True)
        assert schema.query_type == "Query"
        assert opener.open.called

    def test_rfc1918_rejected_unless_allow_internal(self, monkeypatch):
        service = IntrospectionService()
        with pytest.raises(ValueError, match="internal or metadata"):
            service.introspect("http://10.0.0.1/")

        opener = _fake_opener(MINIMAL_INTROSPECTION)
        monkeypatch.setattr(
            "Asgard.Forseti.GraphQL.services.introspection_service.build_introspection_opener",
            lambda **_k: opener,
        )
        schema = service.introspect("http://10.0.0.1/graphql", allow_internal=True)
        assert schema.query_type == "Query"
        assert opener.open.called

    def test_https_public_host_allowed_mocked(self, monkeypatch):
        monkeypatch.setattr(
            "Asgard.Forseti.GraphQL.utilities._url_safety.socket.getaddrinfo",
            lambda *_a, **_k: [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", (PUBLIC_IP, 0))
            ],
        )
        opener = _fake_opener(MINIMAL_INTROSPECTION)
        monkeypatch.setattr(
            "Asgard.Forseti.GraphQL.services.introspection_service.build_introspection_opener",
            lambda **_k: opener,
        )
        schema = IntrospectionService().introspect("https://api.example.com/graphql")
        assert schema.query_type == "Query"
        assert opener.open.called
        request = opener.open.call_args[0][0]
        assert request.full_url == "https://api.example.com/graphql"

    def test_config_allow_internal_enables_loopback(self, monkeypatch):
        opener = _fake_opener(MINIMAL_INTROSPECTION)
        monkeypatch.setattr(
            "Asgard.Forseti.GraphQL.services.introspection_service.build_introspection_opener",
            lambda **_k: opener,
        )
        service = IntrospectionService(GraphQLConfig(allow_internal=True))
        schema = service.introspect("http://127.0.0.1/graphql")
        assert schema.query_type == "Query"

    def test_allow_introspection_false_still_blocks_feature(self):
        service = IntrospectionService(GraphQLConfig(allow_introspection=False))
        with pytest.raises(ValueError, match="disabled"):
            service.introspect("https://93.184.216.34/graphql")


class TestIntrospectCliFlag:
    def test_allow_internal_flag_parsed(self):
        from Asgard.Forseti.cli._parser import create_parser

        parser = create_parser()
        args = parser.parse_args([
            "graphql",
            "introspect",
            "https://api.example.com/graphql",
            "--allow-internal",
        ])
        assert args.allow_internal is True

    def test_allow_internal_flag_defaults_false(self):
        from Asgard.Forseti.cli._parser import create_parser

        parser = create_parser()
        args = parser.parse_args([
            "graphql",
            "introspect",
            "https://api.example.com/graphql",
        ])
        assert args.allow_internal is False
