"""
L5 Compliance Tests — Forseti Spec-Violation Ground Truths.

Known-bad schema pairs (removed field, removed endpoint, destructive
migration) MUST be flagged as breaking; known-good pairs MUST pass.
Fixtures are staged into neutral temp dirs (never pytest tmp_path) so
test-context suppression heuristics cannot mute a real finding.
"""

import json
import tempfile
from pathlib import Path

from Asgard.Forseti.Compatibility import (
    CompatEngineService,
    CompatMode,
    CompatStatus,
)
from Asgard.Forseti.Database.services.schema_diff_service import SchemaDiffService

from Asgard_Test.L5_Meta.l5_fixtures import neutral_copy


def _write_neutral(name: str, data) -> str:
    path = Path(tempfile.mkdtemp(prefix="asgard-l5-")) / name
    payload = data if isinstance(data, str) else json.dumps(data)
    path.write_text(payload, encoding="utf-8")
    return str(path)


def _openapi(props: dict, paths_extra: dict | None = None) -> dict:
    paths = {"/x": {"get": {"responses": {"200": {"content": {
        "application/json": {"schema": {"type": "object", "properties": props}},
    }}}}}}
    if paths_extra:
        paths.update(paths_extra)
    return {
        "openapi": "3.0.0",
        "info": {"title": "t", "version": "1.0.0"},
        "paths": paths,
    }


class TestOpenAPIBreakingChangeCompliance:
    """Known-bad: removed response field between OpenAPI versions (CWE-439)."""

    def test_removed_field_is_breaking(self) -> None:
        old = neutral_copy("CWE-439_behavioral_change/openapi_v1.json")
        new = neutral_copy("CWE-439_behavioral_change/openapi_v2_removed_field.json")
        report = CompatEngineService().check(old, new, mode=CompatMode.BACKWARD)
        assert report.status == CompatStatus.FAILED, (
            f"Removed field must break backward compatibility, got {report.status}"
        )
        assert report.structural_breaks >= 1

    def test_removed_endpoint_is_breaking(self) -> None:
        extra = {"/y": {"get": {"responses": {"200": {"description": "ok"}}}}}
        old = _write_neutral("old.json", _openapi({"a": {"type": "string"}}, extra))
        new = _write_neutral("new.json", _openapi({"a": {"type": "string"}}))
        report = CompatEngineService().check(old, new, mode=CompatMode.BACKWARD)
        assert report.status == CompatStatus.FAILED, (
            "Removed endpoint must break backward compatibility"
        )

    def test_identical_specs_pass(self) -> None:
        spec = _openapi({"a": {"type": "string"}})
        old = _write_neutral("old.json", spec)
        new = _write_neutral("new.json", spec)
        report = CompatEngineService().check(old, new, mode=CompatMode.BACKWARD)
        assert report.status == CompatStatus.PASSED
        assert report.structural_breaks == 0


class TestDatabaseMigrationCompliance:
    """Known-bad: destructive migration dropping a column (CWE-439)."""

    def test_dropped_column_is_breaking(self) -> None:
        old = neutral_copy("CWE-439_behavioral_change/schema_v1.sql")
        new = neutral_copy(
            "CWE-439_behavioral_change/schema_v2_dropped_column.sql"
        )
        result = SchemaDiffService().diff(old, new)
        assert result.has_breaking_changes, (
            "DROP COLUMN migration must be reported as breaking"
        )

    def test_identical_schemas_not_breaking(self) -> None:
        old = neutral_copy("CWE-439_behavioral_change/schema_v1.sql")
        new = neutral_copy(
            "CWE-439_behavioral_change/schema_v1.sql", target_name="schema_v1b.sql"
        )
        result = SchemaDiffService().diff(old, new)
        assert not result.has_breaking_changes
