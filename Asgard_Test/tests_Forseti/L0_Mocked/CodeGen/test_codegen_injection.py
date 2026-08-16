"""CH-0058: OpenAPI strings must not be interpolated as live generated source."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from Asgard.Forseti.CodeGen.models.codegen_models import GeneratedFile, TargetLanguage
from Asgard.Forseti.CodeGen.services._codegen_safety import sanitize_identifier
from Asgard.Forseti.CodeGen.services.golang_generator import GolangGeneratorService
from Asgard.Forseti.CodeGen.services.python_generator import PythonGeneratorService
from Asgard.Forseti.CodeGen.services.typescript_generator import TypeScriptGeneratorService

HOSTILE_PATH = "/{__import__('os')}"
HOSTILE_LITERAL = json.dumps(HOSTILE_PATH)


def _spec(*, path: str = "/pets/{petId}", operation_id: str = "listPets", **extra) -> dict:
    op = {
        "operationId": operation_id,
        "summary": extra.pop("summary", "List pets"),
        "responses": {"200": {"description": "ok"}},
    }
    if extra.get("parameters"):
        op["parameters"] = extra["parameters"]
    spec = {
        "openapi": "3.0.0",
        "info": {
            "title": extra.get("title", "Pet API"),
            "version": "1.0.0",
            "description": extra.get("description", "Pets"),
        },
        "paths": {path: {"get": op}},
        "components": {
            "schemas": {
                extra.get("schema_name", "Pet"): {
                    "type": "object",
                    "description": extra.get("schema_description", "A pet"),
                    "properties": {
                        "id": {"type": "integer"},
                        "name": {"type": "string"},
                    },
                }
            }
        },
    }
    return spec


def _write_spec(tmp_path: Path, spec: dict) -> Path:
    spec_file = tmp_path / "api.json"
    spec_file.write_text(json.dumps(spec), encoding="utf-8")
    return spec_file


def _generated_file(result, name: str) -> str:
    for file in result.generated_files:
        if file.path == name:
            return file.content
    raise AssertionError(f"{name} not in {[f.path for f in result.generated_files]}")


def test_python_hostile_path_is_not_a_live_fstring(tmp_path: Path):
    spec_file = _write_spec(tmp_path, _spec(path=HOSTILE_PATH, operation_id="getThing"))
    result = PythonGeneratorService().generate(spec_file)
    client = _generated_file(result, "client.py")

    assert f"path = f{HOSTILE_LITERAL}" not in client
    assert 'path = f"' not in client
    assert f"path = {HOSTILE_LITERAL}" in client
    assert "{__import__('os')}" in client

    tree = ast.parse(client)
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            dumped = ast.dump(node)
            assert "__import__" not in dumped


def test_python_hostile_path_is_data_not_executed(tmp_path: Path):
    spec_file = _write_spec(tmp_path, _spec(path=HOSTILE_PATH, operation_id="getThing"))
    client = _generated_file(PythonGeneratorService().generate(spec_file), "client.py")
    assign = next(
        node
        for node in ast.walk(ast.parse(client))
        if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "path" for t in node.targets)
        and isinstance(node.value, ast.Constant)
    )
    assert assign.value.value == HOSTILE_PATH
    ns: dict = {}
    exec(f"path = {HOSTILE_LITERAL}", ns)
    assert ns["path"] == HOSTILE_PATH


def test_typescript_path_is_json_string_not_template(tmp_path: Path):
    hostile = "/x`${process.exit()}`"
    spec_file = _write_spec(tmp_path, _spec(path=hostile, operation_id="getThing"))
    client = _generated_file(TypeScriptGeneratorService().generate(spec_file), "client.ts")

    assert "const path = `" not in client
    assert f"let path = {json.dumps(hostile)};" in client
    path_assign = next(line for line in client.splitlines() if line.strip().startswith("let path = "))
    assert path_assign.strip().startswith('let path = "')
    assert not path_assign.strip().startswith("let path = `")


def test_golang_path_is_quoted_data(tmp_path: Path):
    hostile = '/x"{__import__}"'
    spec_file = _write_spec(tmp_path, _spec(path=hostile, operation_id="getThing"))
    client = _generated_file(GolangGeneratorService().generate(spec_file), "client.go")

    assert f'path := "{hostile}"' not in client
    assert f"path := {json.dumps(hostile)}" in client
    assert "fmt.Sprintf(\"" + hostile not in client


def test_hyphenated_operation_id_is_sanitized(tmp_path: Path):
    spec_file = _write_spec(tmp_path, _spec(path="/pets", operation_id="list-pets"))
    py = _generated_file(PythonGeneratorService().generate(spec_file), "client.py")
    ts = _generated_file(TypeScriptGeneratorService().generate(spec_file), "client.ts")
    go = _generated_file(GolangGeneratorService().generate(spec_file), "client.go")

    ast.parse(py)
    assert "def list_pets(" in py
    assert "async listPets(" in ts
    assert "func (c *Client) ListPets(" in go
    for content in (py, ts, go):
        assert "def list-pets" not in content
        assert "async list-pets" not in content


def test_comment_breakout_is_escaped(tmp_path: Path):
    spec_file = _write_spec(
        tmp_path,
        _spec(
            path="/pets",
            operation_id="listPets",
            summary='ok """ import os; #',
            schema_description="end */ process.exit() /*",
            title='API """ breakout',
        ),
    )
    py_result = PythonGeneratorService().generate(spec_file)
    py_models = _generated_file(py_result, "models.py")
    py_client = _generated_file(py_result, "client.py")
    ts = _generated_file(TypeScriptGeneratorService().generate(spec_file), "types.ts")
    go = _generated_file(GolangGeneratorService().generate(spec_file), "models.go")

    ast.parse(py_models)
    ast.parse(py_client)
    assert '""" import os' not in py_client
    assert "*/ process.exit()" not in ts
    assert "\npackage " not in go.split("package ", 1)[0]


@pytest.mark.parametrize(
    "service_cls, rel, language",
    [
        (PythonGeneratorService, "../x.py", TargetLanguage.PYTHON),
        (TypeScriptGeneratorService, "../x.ts", TargetLanguage.TYPESCRIPT),
        (GolangGeneratorService, "../x.go", TargetLanguage.GOLANG),
    ],
)
def test_write_files_rejects_parent_path(tmp_path: Path, service_cls, rel, language):
    out = tmp_path / "out"
    out.mkdir()
    files = [
        GeneratedFile(path=rel, content="x", language=language, file_type="client"),
    ]
    with pytest.raises(ValueError, match="output directory"):
        service_cls()._write_files(files, out)
    assert not (tmp_path / "x.py").exists()
    assert not (tmp_path / "x.ts").exists()
    assert not (tmp_path / "x.go").exists()


@pytest.mark.parametrize("service_cls", [PythonGeneratorService, TypeScriptGeneratorService, GolangGeneratorService])
def test_write_files_rejects_absolute_path(tmp_path: Path, service_cls):
    out = tmp_path / "out"
    out.mkdir()
    files = [
        GeneratedFile(
            path="/tmp/codegen_escape.py",
            content="x",
            language=TargetLanguage.PYTHON,
            file_type="client",
        ),
    ]
    with pytest.raises(ValueError, match="output directory"):
        service_cls()._write_files(files, out)


def test_write_files_keeps_relative_client(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    files = [
        GeneratedFile(path="client.py", content="ok", language=TargetLanguage.PYTHON, file_type="client"),
    ]
    PythonGeneratorService()._write_files(files, out)
    assert (out / "client.py").read_text(encoding="utf-8") == "ok"


def test_existing_pet_spec_still_generates(tmp_path: Path):
    spec_file = _write_spec(
        tmp_path,
        _spec(
            path="/pets/{petId}",
            operation_id="getPet",
            parameters=[{"name": "petId", "in": "path", "required": True, "schema": {"type": "string"}}],
        ),
    )
    py = PythonGeneratorService().generate(spec_file)
    ts = TypeScriptGeneratorService().generate(spec_file)
    go = GolangGeneratorService().generate(spec_file)

    assert py.success and ts.success and go.success
    py_client = _generated_file(py, "client.py")
    ast.parse(py_client)
    assert 'path = "/pets/{petId}"' in py_client
    assert 'path.replace("{petId}"' in py_client
    ts_client = _generated_file(ts, "client.ts")
    assert 'let path = "/pets/{petId}";' in ts_client
    go_client = _generated_file(go, "client.go")
    assert 'path := "/pets/{petId}"' in go_client
    assert "strings.Replace" in go_client


def test_sanitize_identifier_strips_braces_and_quotes():
    cleaned = sanitize_identifier("{__import__('os')}")
    assert cleaned.isidentifier()
    assert "{" not in cleaned
    assert "}" not in cleaned
    assert "'" not in cleaned
    assert '"' not in cleaned
    assert sanitize_identifier("list-pets") == "list_pets"
    assert sanitize_identifier("Pet") == "Pet"
