"""
L0 Unit Tests for `forseti mock data --synthetic` (plan 06-B item 4).

Example-first is the default: schema `example`/`examples` win over
synthetic generation. `--synthetic` forces generation, ignoring
examples and defaults.
"""

import json

import pytest

from Asgard.Forseti.cli import main as cli_main

SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "example": "FROM_EXAMPLE"},
    },
    "required": ["status"],
}


@pytest.fixture()
def schema_file(tmp_path):
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    return str(path)


def _run(args, tmp_path):
    out = tmp_path / "out.json"
    rc = cli_main(args + ["--output", str(out)])
    assert rc == 0
    return json.loads(out.read_text(encoding="utf-8"))


class TestMockDataSyntheticFlag:
    def test_examples_win_by_default(self, schema_file, tmp_path):
        data = _run(["mock", "data", schema_file, "--seed", "7"], tmp_path)
        assert data["status"] == "FROM_EXAMPLE"

    def test_synthetic_forces_generation(self, schema_file, tmp_path):
        data = _run(
            ["mock", "data", schema_file, "--seed", "7", "--synthetic"], tmp_path
        )
        assert data["status"] != "FROM_EXAMPLE"
        assert isinstance(data["status"], str)

    def test_synthetic_is_deterministic_with_seed(self, schema_file, tmp_path):
        a = _run(["mock", "data", schema_file, "--seed", "7", "--synthetic"], tmp_path)
        b = _run(["mock", "data", schema_file, "--seed", "7", "--synthetic"], tmp_path)
        assert a == b
