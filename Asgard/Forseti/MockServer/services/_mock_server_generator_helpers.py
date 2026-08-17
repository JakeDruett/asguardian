"""
Mock Server Generator Helpers.

Code generation helper functions for MockServerGeneratorService.
"""

import json
import re

from Asgard.Forseti.CodeGen.services._codegen_safety import (
    escape_block_comment,
    escape_docstring,
    escape_line_comment,
    sanitize_identifier,
    string_literal,
)
from Asgard.Forseti.MockServer.models.mock_models import (
    MockEndpoint,
    MockServerConfig,
    MockServerDefinition,
)

_TRAILING_PARAM_RE = re.compile(r"/\{([^/{}]+)\}$")
_SAFE_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
_FLASK_PATH_RE = re.compile(r"^/[A-Za-z0-9_\-./<>]*$")
_EXPRESS_PATH_RE = re.compile(r"^/[A-Za-z0-9_\-./:]*$")


def _safe_method(endpoint: MockEndpoint) -> str:
    method = _method_str(endpoint).upper()
    if method not in _SAFE_METHODS:
        raise ValueError("unsafe HTTP method in mock spec")
    return method


def _safe_func_name(endpoint: MockEndpoint) -> str:
    return sanitize_identifier(endpoint_to_function_name(endpoint))


def _safe_flask_path(path: str) -> str:
    flask_path = path.replace("{", "<").replace("}", ">")
    if not _FLASK_PATH_RE.fullmatch(flask_path):
        raise ValueError("unsafe mock path")
    return flask_path


def _safe_status(code: object) -> int:
    text = str(code or "200")
    if not text.isdigit():
        return 200
    value = int(text)
    if value < 100 or value > 599:
        return 200
    return value


def collection_key(path: str) -> tuple[str, bool]:
    """Split a path template into (collection_base_path, has_id_param).

    `/users` -> ("/users", False); `/users/{id}` -> ("/users", True).
    Nested params beyond the trailing one keep the collection distinct per
    parent, e.g. `/users/{userId}/orders/{id}` -> ("/users/{userId}/orders", True).
    """
    match = _TRAILING_PARAM_RE.search(path)
    if match:
        return path[: match.start()], True
    return path, False


def stateful_endpoints_by_collection(
    endpoints: list[MockEndpoint],
) -> dict[str, list[MockEndpoint]]:
    """Group endpoints that look like collection CRUD (POST base / GET,PUT,DELETE {id})."""
    grouped: dict[str, list[MockEndpoint]] = {}
    for endpoint in endpoints:
        base, _has_id = collection_key(endpoint.path)
        grouped.setdefault(base, []).append(endpoint)
    return grouped


def _method_str(endpoint: MockEndpoint) -> str:
    """Endpoint HTTP method as a plain string.

    `MockEndpoint.Config.use_enum_values=True` stores `.method` as a plain
    str at validation time, but callers (and this module, historically)
    sometimes still hold an `HttpMethod` enum instance - handle both.
    """
    method = endpoint.method
    return method.value if hasattr(method, "value") else str(method)


def endpoint_to_function_name(endpoint: MockEndpoint) -> str:
    """Convert an endpoint to a valid function name."""
    if endpoint.operation_id:
        name = str(endpoint.operation_id).replace("-", "_").replace(".", "_")
        return name
    path_parts = endpoint.path.strip("/").replace("{", "").replace("}", "")
    path_parts = path_parts.replace("/", "_").replace("-", "_")
    return f"{_method_str(endpoint).lower()}_{path_parts}"


def generate_flask_route(endpoint: MockEndpoint, config: MockServerConfig) -> str:
    """Generate a single Flask route."""
    flask_path = _safe_flask_path(endpoint.path)
    func_name = _safe_func_name(endpoint)
    default_status = _safe_status(endpoint.default_response or "200")
    method_str = _safe_method(endpoint)
    response_key = f"{method_str}_{endpoint.path}_{default_status}"
    delay_code = ""
    if config.response_delay_ms > 0:
        delay_code = f"\n        time.sleep({float(config.response_delay_ms) / 1000})"
    doc = escape_docstring(
        endpoint.summary or endpoint.description or f"Mock {method_str} {endpoint.path}"
    )
    return f'''    @app.route({string_literal(flask_path)}, methods=[{string_literal(method_str)}])
    def {func_name}(**kwargs):
        """{doc}"""{delay_code}
        response_data = MOCK_RESPONSES.get({string_literal(response_key)}, {{}})
        return jsonify(response_data), {default_status}'''


def generate_flask_route_stateful(endpoint: MockEndpoint, config: MockServerConfig) -> str:
    """Generate a single Flask route backed by the in-memory `_STORE` (WireMock-style).

    POST on a bare collection path stores the JSON body under a generated
    id; GET on `{id}` returns it (404 if absent); PUT replaces it; DELETE
    removes it (subsequent GET then 404s). Non-CRUD-shaped routes
    (methods other than GET/POST/PUT/PATCH/DELETE, or paths that aren't a
    plain collection/id pair) fall back to the static MOCK_RESPONSES path.
    """
    flask_path = _safe_flask_path(endpoint.path)
    func_name = _safe_func_name(endpoint)
    base, has_id = collection_key(endpoint.path)
    method = _safe_method(endpoint)
    base_lit = string_literal(base)
    path_lit = string_literal(flask_path)
    delay_code = ""
    if config.response_delay_ms > 0:
        delay_code = f"\n        time.sleep({config.response_delay_ms / 1000})"

    if method == "POST" and not has_id:
        return f'''    @app.route({path_lit}, methods=["POST"])
    def {func_name}(**kwargs):
        """{escape_docstring(endpoint.summary or f"Create under {endpoint.path}")}"""{delay_code}
        payload = request.get_json(silent=True) or {{}}
        new_id = str(_STORE.setdefault("_next_id", [1])[0])
        _STORE.setdefault("_next_id", [1])[0] += 1
        record = dict(payload)
        record["id"] = new_id
        _STORE.setdefault({base_lit}, {{}})[new_id] = record
        return jsonify(record), 201'''

    if method == "GET" and not has_id:
        return f'''    @app.route({path_lit}, methods=["GET"])
    def {func_name}(**kwargs):
        """{escape_docstring(endpoint.summary or f"List {endpoint.path}")}"""{delay_code}
        return jsonify(list(_STORE.get({base_lit}, {{}}).values())), 200'''

    if method == "GET" and has_id:
        return f'''    @app.route({path_lit}, methods=["GET"])
    def {func_name}(**kwargs):
        """{escape_docstring(endpoint.summary or f"Get one from {endpoint.path}")}"""{delay_code}
        item_id = str(list(kwargs.values())[-1]) if kwargs else None
        record = _STORE.get({base_lit}, {{}}).get(item_id)
        if record is None:
            return jsonify({{"error": "not found"}}), 404
        return jsonify(record), 200'''

    if method in ("PUT", "PATCH") and has_id:
        return f'''    @app.route({path_lit}, methods=[{string_literal(method)}])
    def {func_name}(**kwargs):
        """{escape_docstring(endpoint.summary or f"Update {endpoint.path}")}"""{delay_code}
        item_id = str(list(kwargs.values())[-1]) if kwargs else None
        collection = _STORE.setdefault({base_lit}, {{}})
        if item_id not in collection:
            return jsonify({{"error": "not found"}}), 404
        payload = request.get_json(silent=True) or {{}}
        record = dict(payload)
        record["id"] = item_id
        collection[item_id] = record
        return jsonify(record), 200'''

    if method == "DELETE" and has_id:
        return f'''    @app.route({path_lit}, methods=["DELETE"])
    def {func_name}(**kwargs):
        """{escape_docstring(endpoint.summary or f"Delete {endpoint.path}")}"""{delay_code}
        item_id = str(list(kwargs.values())[-1]) if kwargs else None
        collection = _STORE.setdefault({base_lit}, {{}})
        if item_id not in collection:
            return jsonify({{"error": "not found"}}), 404
        del collection[item_id]
        return "", 204'''

    # Fallback: non-CRUD-shaped route, serve the static example response.
    return generate_flask_route(endpoint, config)


def generate_flask_routes(server_def: MockServerDefinition, config: MockServerConfig) -> str:
    """Generate Flask routes file."""
    routes = []
    for endpoint in server_def.endpoints:
        if config.stateful:
            route_code = generate_flask_route_stateful(endpoint, config)
        else:
            route_code = generate_flask_route(endpoint, config)
        routes.append(route_code)
    routes_str = "\n\n".join(routes)
    store_init = '\n_STORE: dict = {}  # WireMock-style in-memory resource store (--stateful)\n' if config.stateful else ""
    return f'''"""
API Routes for {escape_docstring(server_def.title)}
"""

import time
from flask import Flask, jsonify, request
from mock_data import MOCK_RESPONSES
{store_init}

def register_routes(app: Flask):
    """Register all mock routes with the Flask app."""

{routes_str}
'''


def generate_flask_main(server_def: MockServerDefinition, config: MockServerConfig) -> str:
    """Generate Flask main server file."""
    cors_import = "from flask_cors import CORS" if config.enable_cors else ""
    cors_init = "CORS(app)" if config.enable_cors else ""
    return f'''"""
{escape_docstring(server_def.title)} - Mock Server
Generated by Forseti MockServer

Local-only mock: binds {escape_docstring(str(config.host))} with debug disabled. Not for network exposure.

{escape_docstring(server_def.description or "")}
"""

from flask import Flask, jsonify
{cors_import}
from routes import register_routes

app = Flask(__name__)
{cors_init}

# Register all routes
register_routes(app)


@app.errorhandler(404)
def not_found(e):
    return jsonify({{"error": "Not found"}}), 404


@app.errorhandler(500)
def server_error(e):
    return jsonify({{"error": "Internal server error"}}), 500


if __name__ == "__main__":
    app.run(
        host={string_literal(str(config.host))},
        port={int(config.port)},
        debug=False
    )
'''


def generate_response_data(server_def: MockServerDefinition) -> str:
    """Generate Python mock data file."""
    mock_data = {}
    for endpoint in server_def.endpoints:
        for status_code, response in endpoint.responses.items():
            response_key = f"{_method_str(endpoint)}_{endpoint.path}_{status_code}"
            mock_data[response_key] = response.body
    data_json = json.dumps(mock_data, indent=4, default=str)
    return f'''"""
Mock response data for {escape_docstring(server_def.title)}
"""

MOCK_RESPONSES = {data_json}
'''


def generate_fastapi_route(endpoint: MockEndpoint, config: MockServerConfig) -> str:
    """Generate a single FastAPI route."""
    method_str = _safe_method(endpoint)
    method_lower = method_str.lower()
    func_name = _safe_func_name(endpoint)
    default_status = _safe_status(endpoint.default_response or "200")
    response_key = f"{method_str}_{endpoint.path}_{default_status}"
    delay_code = ""
    if config.response_delay_ms > 0:
        delay_code = f"\n    time.sleep({float(config.response_delay_ms) / 1000})"
    doc = escape_docstring(
        endpoint.summary or endpoint.description or f"Mock {method_str} {endpoint.path}"
    )
    return f'''@app.{method_lower}({string_literal(endpoint.path)})
async def {func_name}():{delay_code}
    """{doc}"""
    return MOCK_RESPONSES.get({string_literal(response_key)}, {{}})'''


def generate_express_route(endpoint: MockEndpoint, config: MockServerConfig) -> str:
    """Generate a single Express.js route."""
    express_path = endpoint.path
    for param in endpoint.path_parameters:
        express_path = express_path.replace(f"{{{param.name}}}", f":{sanitize_identifier(param.name)}")
    if not _EXPRESS_PATH_RE.fullmatch(express_path):
        raise ValueError("unsafe mock path")
    method_str = _safe_method(endpoint)
    method_lower = method_str.lower()
    default_status = _safe_status(endpoint.default_response or "200")
    response_key = f"{method_str}_{endpoint.path}_{default_status}"
    delay_code = ""
    if config.response_delay_ms > 0:
        delay_code = f'''
    await new Promise(resolve => setTimeout(resolve, {float(config.response_delay_ms)}));'''
    comment = escape_line_comment(
        endpoint.summary or f"{method_str} {endpoint.path}"
    )
    return f'''// {comment}
app.{method_lower}({string_literal(express_path)}, {"async " if delay_code else ""}(req, res) => {{{delay_code}
    const response = mockData[{string_literal(response_key)}] || {{}};
    res.status({default_status}).json(response);
}});'''
