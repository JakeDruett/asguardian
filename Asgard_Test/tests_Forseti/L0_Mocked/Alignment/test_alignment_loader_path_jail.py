"""CH-0057: Alignment EntitySource.file must stay under base_dir."""

from pathlib import Path

import pytest
import yaml

from Asgard.Forseti.Alignment.models.alignment_models import AlignmentConfig, EntitySource
from Asgard.Forseti.Alignment.services.alignment_loader_service import (
    build_ir_record,
    check_config,
    confine_source_path,
)

OPENAPI_DOC = {
    "openapi": "3.0.0",
    "info": {"title": "x", "version": "1"},
    "paths": {},
    "components": {
        "schemas": {
            "OrderResponse": {
                "type": "object",
                "properties": {"orderId": {"type": "string"}},
            }
        }
    },
}


def _spy_read_text(monkeypatch) -> list[str]:
    opened: list[str] = []

    def _spy(self, *args, **kwargs):
        opened.append(str(self))
        raise AssertionError(f"must not read {self}")

    monkeypatch.setattr(Path, "read_text", _spy)
    return opened


def test_confine_rejects_unix_absolute(tmp_path: Path):
    with pytest.raises(ValueError, match="base directory"):
        confine_source_path("/etc/passwd", str(tmp_path))


def test_confine_rejects_parent_escape(tmp_path: Path):
    with pytest.raises(ValueError, match="base directory"):
        confine_source_path("../secret.yaml", str(tmp_path))


def test_confine_keeps_relative_under_base(tmp_path: Path):
    dest = confine_source_path("schemas/openapi.yaml", str(tmp_path))
    assert dest == str((tmp_path / "schemas" / "openapi.yaml").resolve())
    assert Path(dest).is_relative_to(tmp_path.resolve())


def test_unix_absolute_passwd_is_rejected_without_read(tmp_path: Path, monkeypatch):
    opened = _spy_read_text(monkeypatch)
    with pytest.raises(ValueError, match="base directory"):
        build_ir_record(EntitySource(file="/etc/passwd"), base_dir=str(tmp_path))
    assert opened == []


def test_absolute_tmp_secret_is_rejected_without_read(tmp_path: Path, monkeypatch):
    secret = tmp_path / "secret.yaml"
    secret.write_text("LEAK: true\n", encoding="utf-8")
    jail = tmp_path / "jail"
    jail.mkdir()
    opened = _spy_read_text(monkeypatch)
    with pytest.raises(ValueError, match="base directory"):
        build_ir_record(EntitySource(file=str(secret)), base_dir=str(jail))
    assert opened == []


def test_parent_escape_is_rejected_without_read(tmp_path: Path, monkeypatch):
    secret = tmp_path / "secret.yaml"
    secret.write_text("LEAK: true\n", encoding="utf-8")
    jail = tmp_path / "jail"
    jail.mkdir()
    opened = _spy_read_text(monkeypatch)
    with pytest.raises(ValueError, match="base directory"):
        build_ir_record(EntitySource(file="../secret.yaml"), base_dir=str(jail))
    assert opened == []


def test_nested_dotdot_is_rejected(tmp_path: Path, monkeypatch):
    opened = _spy_read_text(monkeypatch)
    with pytest.raises(ValueError, match="base directory"):
        build_ir_record(EntitySource(file="schemas/../../secret.yaml"), base_dir=str(tmp_path))
    assert opened == []


def test_check_config_rejects_parent_escape(tmp_path: Path, monkeypatch):
    jail = tmp_path / "jail"
    jail.mkdir()
    config = AlignmentConfig.model_validate(
        {"entities": {"Order": {"sources": [{"file": "../secret.yaml"}]}}}
    )
    opened = _spy_read_text(monkeypatch)
    with pytest.raises(ValueError, match="base directory"):
        check_config(config, base_dir=str(jail))
    assert opened == []


def test_relative_source_still_loads(tmp_path: Path):
    schemas = tmp_path / "schemas"
    schemas.mkdir()
    (schemas / "openapi.yaml").write_text(yaml.safe_dump(OPENAPI_DOC), encoding="utf-8")
    record = build_ir_record(
        EntitySource(file="schemas/openapi.yaml", schema_name="OrderResponse"),
        base_dir=str(tmp_path),
    )
    assert record.fields
