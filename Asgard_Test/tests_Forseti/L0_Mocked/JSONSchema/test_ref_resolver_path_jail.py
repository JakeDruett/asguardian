"""CH-0059: JSON Schema $ref must stay under the schema root."""

import json
from pathlib import Path

import pytest

from Asgard.Forseti.JSONSchema.services._ref_resolver_helpers import (
    RefResolutionError,
    SchemaRegistry,
)
from Asgard.Forseti.JSONSchema.services.schema_validator_service import SchemaValidatorService


def _jail_registry(tmp_path: Path) -> tuple[SchemaRegistry, Path]:
    jail = tmp_path / "jail"
    jail.mkdir()
    main = jail / "main.json"
    main.write_text("{}")
    return SchemaRegistry({"type": "object"}, root_path=main), jail


def test_absolute_path_ref_raises_and_does_not_read(tmp_path: Path, monkeypatch):
    outside = tmp_path / "secret.json"
    outside.write_text(json.dumps({"type": "string", "const": "LEAK"}))
    registry, _jail = _jail_registry(tmp_path)
    opened: list[Path] = []

    def _spy(path: Path):
        opened.append(Path(path))
        raise AssertionError(f"must not read {path}")

    monkeypatch.setattr(
        "Asgard.Forseti.JSONSchema.utilities.jsonschema_utils.load_schema_file",
        _spy,
    )
    with pytest.raises(RefResolutionError):
        registry.resolve(str(outside), "")
    with pytest.raises(RefResolutionError):
        registry.resolve(f"file://{outside}", "")
    assert opened == []
    assert registry._external == {}


def test_unix_absolute_ref_does_not_open_host_file(tmp_path: Path, monkeypatch):
    registry, _jail = _jail_registry(tmp_path)

    def _boom(path: Path):
        raise AssertionError(f"must not read {path}")

    monkeypatch.setattr(
        "Asgard.Forseti.JSONSchema.utilities.jsonschema_utils.load_schema_file",
        _boom,
    )
    with pytest.raises(RefResolutionError):
        registry.resolve("/etc/passwd", "")
    with pytest.raises(RefResolutionError):
        registry.resolve("file:///etc/passwd", "")


def test_parent_ref_raises(tmp_path: Path):
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"type": "string"}))
    registry, _jail = _jail_registry(tmp_path)
    with pytest.raises(RefResolutionError):
        registry.resolve("../outside.json", "")
    assert registry._external == {}


def test_relative_sibling_ref_still_works(tmp_path: Path):
    (tmp_path / "name.json").write_text(json.dumps({"type": "string", "minLength": 2}))
    main = tmp_path / "main.json"
    main.write_text(json.dumps({"properties": {"name": {"$ref": "name.json"}}}))
    service = SchemaValidatorService()
    assert service.validate({"name": "ok"}, main).is_valid
    assert not service.validate({"name": "x"}, main).is_valid


@pytest.mark.parametrize(
    "ref",
    [
        "https://example.com/schema.json",
        "http://example.com/schema.json",
        "data:application/json,{}",
        "ftp://example.com/schema.json",
    ],
)
def test_remote_schemes_still_rejected(tmp_path: Path, ref: str):
    registry, _jail = _jail_registry(tmp_path)
    with pytest.raises(RefResolutionError, match="external reference"):
        registry.resolve(ref, "")


def test_file_ref_without_root_path_is_rejected():
    registry = SchemaRegistry({"type": "object"})
    with pytest.raises(RefResolutionError):
        registry.resolve("name.json", "")


def test_symlink_escape_is_rejected(tmp_path: Path, monkeypatch):
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"type": "string"}))
    registry, jail = _jail_registry(tmp_path)
    link = jail / "escape.json"
    link.symlink_to(outside)
    opened: list[Path] = []

    def _spy(path: Path):
        opened.append(Path(path))
        raise AssertionError(f"must not read {path}")

    monkeypatch.setattr(
        "Asgard.Forseti.JSONSchema.utilities.jsonschema_utils.load_schema_file",
        _spy,
    )
    with pytest.raises(RefResolutionError):
        registry.resolve("escape.json", "")
    assert opened == []
