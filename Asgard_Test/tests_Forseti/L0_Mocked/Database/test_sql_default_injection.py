"""CH-0065: SQL DEFAULT must be a literal; migrations must not emit stacked SQL."""

from __future__ import annotations

import ast

import pytest

from Asgard.Forseti.Database.models.database_models import (
    ChangeType,
    ColumnDefinition,
    SchemaChange,
    SchemaDiffResult,
)
from Asgard.Forseti.Database.services._schema_analyzer_helpers import parse_column
from Asgard.Forseti.Database.services.migration_generator_service import MigrationGeneratorService
from Asgard.Forseti.Database.services.schema_analyzer_service import SchemaAnalyzerService
from Asgard.Forseti.Database.services.schema_diff_service import SchemaDiffService
from Asgard.Forseti.Database.utilities.database_utils import (
    format_column_definition,
    quote_identifier,
    sanitize_sql_default,
    sql_for_execution,
)

HOSTILE_DEFAULT = "1;DROP"


def _alembic_execute_args(script: str) -> list[str]:
    tree = ast.parse(script)
    args: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "execute":
            if node.args:
                args.append(ast.literal_eval(node.args[0]))
    return args


@pytest.mark.parametrize(
    "literal",
    ["0", "42", "-1", "3.14", "NULL", "TRUE", "FALSE", "true", "'active'", "''"],
)
def test_safe_literals_are_kept(literal: str):
    assert sanitize_sql_default(literal) is not None
    col = parse_column(f"status VARCHAR(20) DEFAULT {literal}")
    assert col is not None
    assert col.default_value is not None
    sql = col.to_sql()
    assert sql.startswith("`status` VARCHAR")
    assert "DEFAULT" in sql
    assert ";" not in sql
    assert "DROP" not in sql


def test_parse_column_preserves_quoted_case():
    col = parse_column("status VARCHAR(20) DEFAULT 'active'")
    assert col is not None
    assert col.default_value == "'active'"
    assert "DEFAULT 'active'" in col.to_sql()


def test_parse_rejects_stacked_default():
    col = parse_column(f"id INTEGER DEFAULT {HOSTILE_DEFAULT}")
    assert col is not None
    assert col.default_value is None
    assert HOSTILE_DEFAULT not in col.to_sql()
    assert "DROP" not in col.to_sql()


@pytest.mark.parametrize(
    "hostile",
    [
        "1;DROP",
        "1; DROP",
        "'x';DROP",
        "1--",
        "1/*",
        "1\nDROP",
        "CURRENT_TIMESTAMP",
        "NOW()",
        "(0)",
    ],
)
def test_sanitize_rejects_non_literals(hostile: str):
    assert sanitize_sql_default(hostile) is None


def test_to_sql_omits_hostile_default():
    col = ColumnDefinition(name="id", data_type="INTEGER", default_value=HOSTILE_DEFAULT)
    sql = col.to_sql()
    assert HOSTILE_DEFAULT not in sql
    assert "DEFAULT" not in sql
    assert "DROP" not in sql
    assert sql.startswith("`id` INTEGER")


def test_format_column_definition_omits_hostile_default():
    sql = format_column_definition("id", "INTEGER", default=HOSTILE_DEFAULT)
    assert HOSTILE_DEFAULT not in sql
    assert "DEFAULT" not in sql
    assert sql.startswith("`id` INTEGER")


def test_quote_identifier_dialects_and_rejects_hostile():
    assert quote_identifier("users") == "`users`"
    assert quote_identifier("users", "postgresql") == '"users"'
    assert quote_identifier("users", "mssql") == "[users]"
    with pytest.raises(ValueError):
        quote_identifier("1;DROP")
    with pytest.raises(ValueError):
        quote_identifier('users"; DROP')


def test_schema_sql_roundtrip_does_not_emit_stacked_default():
    sql = """
CREATE TABLE users (
    id INTEGER DEFAULT 1;DROP TABLE secrets
);
"""
    schema = SchemaAnalyzerService().analyze_sql(sql)
    emitted = "\n".join(table.to_sql() for table in schema.tables)
    assert HOSTILE_DEFAULT not in emitted
    assert "DROP TABLE secrets" not in emitted
    for table in schema.tables:
        for col in table.columns:
            assert col.default_value != HOSTILE_DEFAULT


def test_diff_and_sql_migration_omit_stacked_default(tmp_path):
    source = tmp_path / "v1.sql"
    target = tmp_path / "v2.sql"
    source.write_text("CREATE TABLE users (id INTEGER);\n", encoding="utf-8")
    target.write_text(
        "CREATE TABLE users (\n    id INTEGER,\n    flag INTEGER DEFAULT 0\n);\n",
        encoding="utf-8",
    )
    result = SchemaDiffService().diff(source, target)
    migration = MigrationGeneratorService().generate(result, include_rollback=False)
    assert "DEFAULT 0" in migration
    assert "`users`" in migration
    assert "`flag`" in migration

    hostile = SchemaDiffResult(
        is_identical=False,
        changes=[
            SchemaChange(
                change_type=ChangeType.ADD_COLUMN,
                table_name="users",
                object_name="id",
                migration_sql=f"ALTER TABLE users ADD COLUMN id INTEGER DEFAULT {HOSTILE_DEFAULT} TABLE secrets;",
                rollback_sql="ALTER TABLE users DROP COLUMN id;",
            )
        ],
    )
    dumped = MigrationGeneratorService().generate(hostile, include_rollback=True)
    assert "DROP TABLE secrets" not in dumped
    assert HOSTILE_DEFAULT not in dumped
    assert sql_for_execution(hostile.changes[0].migration_sql) is None


def test_alembic_does_not_embed_stacked_default():
    hostile = SchemaDiffResult(
        is_identical=False,
        changes=[
            SchemaChange(
                change_type=ChangeType.ADD_COLUMN,
                table_name="users",
                object_name="id",
                migration_sql=f"ALTER TABLE users ADD COLUMN id INTEGER DEFAULT {HOSTILE_DEFAULT} TABLE secrets;",
                rollback_sql="ALTER TABLE users DROP COLUMN id;",
            )
        ],
    )
    script = MigrationGeneratorService().generate_alembic_migration(hostile, "rev1")
    ast.parse(script)
    executed = _alembic_execute_args(script)
    assert HOSTILE_DEFAULT not in script
    assert "DROP TABLE" not in script
    assert all(";" not in stmt[:-1] if stmt.endswith(";") else ";" not in stmt for stmt in executed)
    assert all(HOSTILE_DEFAULT not in stmt for stmt in executed)


def test_alembic_emits_python_literal_for_safe_default():
    change = SchemaChange(
        change_type=ChangeType.ADD_COLUMN,
        table_name="users",
        object_name="status",
        migration_sql="ALTER TABLE `users` ADD COLUMN `status` VARCHAR(20) DEFAULT 'active';",
        rollback_sql="ALTER TABLE `users` DROP COLUMN `status`;",
    )
    result = SchemaDiffResult(is_identical=False, changes=[change])
    script = MigrationGeneratorService().generate_alembic_migration(result, "rev2")
    ast.parse(script)
    executed = _alembic_execute_args(script)
    assert any("DEFAULT 'active'" in stmt for stmt in executed)
    assert all(stmt.count(";") <= 1 for stmt in executed)
