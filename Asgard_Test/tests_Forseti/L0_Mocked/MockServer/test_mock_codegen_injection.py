"""CHC-0002: untrusted OpenAPI tokens must not break out of generated mock source."""

import ast

import pytest

from Asgard.Forseti.MockServer.models._mock_base_models import HttpMethod, MockResponse, MockServerConfig
from Asgard.Forseti.MockServer.models.mock_models import MockEndpoint
from Asgard.Forseti.MockServer.services._mock_server_generator_helpers import (
    generate_express_route,
    generate_fastapi_route,
    generate_flask_route,
)


def _endpoint(**kwargs) -> MockEndpoint:
    defaults = dict(
        path="/users",
        method=HttpMethod.GET,
        operation_id="listUsers",
        summary="List users",
        responses={"200": MockResponse(status_code=200, body={})},
    )
    defaults.update(kwargs)
    return MockEndpoint(**defaults)


def test_quote_in_path_is_rejected():
    ep = _endpoint(path='/x"{os.system}')
    with pytest.raises(ValueError, match="unsafe mock path"):
        generate_flask_route(ep, MockServerConfig())


def test_newline_summary_does_not_break_docstring():
    ep = _endpoint(summary='end"""\nimport os')
    src = generate_flask_route(ep, MockServerConfig())
    tree = ast.parse("from flask import Flask, jsonify\napp=Flask('t')\nclass _G:\n" + src)
    funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    assert funcs
    assert not any(isinstance(stmt, (ast.Import, ast.ImportFrom)) for stmt in funcs[0].body)


def test_hostile_operation_id_is_sanitized_identifier():
    ep = _endpoint(operation_id="list;import os")
    src = generate_flask_route(ep, MockServerConfig())
    tree = ast.parse("from flask import Flask, jsonify\napp=Flask('t')\nclass _G:\n" + src)
    funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    assert funcs
    assert funcs[0].isidentifier()
    assert ";" not in funcs[0]


def test_fastapi_path_is_json_literal():
    ep = _endpoint(path="/pets/{petId}")
    src = generate_fastapi_route(ep, MockServerConfig())
    ast.parse("app=type('A',(),{})()\nMOCK_RESPONSES={}\n" + src.replace("@app.get", "@lambda x: x\n#"))
    assert '"/pets/{petId}"' in src


def test_express_quote_in_path_is_rejected():
    ep = _endpoint(path="/x';process.exit(1);//")
    with pytest.raises(ValueError, match="unsafe mock path"):
        generate_express_route(ep, MockServerConfig())
