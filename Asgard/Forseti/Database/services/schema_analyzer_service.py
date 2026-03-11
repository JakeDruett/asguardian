"""
Database Schema Analyzer Service.

Extracts schema information from databases and SQL files.
"""

import re
from pathlib import Path
from typing import Any, Optional

from Asgard.Forseti.Database.models.database_models import (
    DatabaseConfig,
    DatabaseSchema,
    TableDefinition,
    ColumnDefinition,
    IndexDefinition,
    ForeignKeyDefinition,
)
from Asgard.Forseti.Database.utilities.database_utils import load_sql_file, parse_create_table


class SchemaAnalyzerService:
    """
    Service for analyzing database schemas.

    Extracts schema information from SQL files or database connections.

    Usage:
        service = SchemaAnalyzerService()
        schema = service.analyze_file("schema.sql")
        for table in schema.tables:
            print(f"Table: {table.name}")
    """

    def __init__(self, config: Optional[DatabaseConfig] = None):
        """
        Initialize the analyzer service.

        Args:
            config: Optional configuration for analysis behavior.
        """
        self.config = config or DatabaseConfig()

    def analyze_file(self, file_path: str | Path) -> DatabaseSchema:
        """
        Analyze a SQL file to extract schema information.

        Args:
            file_path: Path to the SQL file.

        Returns:
            Extracted DatabaseSchema.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"SQL file not found: {file_path}")

        sql_content = load_sql_file(file_path)
        return self.analyze_sql(sql_content, str(file_path))

    def analyze_sql(
        self,
        sql_content: str,
        source_name: Optional[str] = None
    ) -> DatabaseSchema:
        """
        Analyze SQL content to extract schema information.

        Args:
            sql_content: SQL DDL content.
            source_name: Optional source identifier.

        Returns:
            Extracted DatabaseSchema.
        """
        tables: list[TableDefinition] = []

        # Extract CREATE TABLE statements
        create_table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?\s*\(([^;]+)\)'
        for match in re.finditer(create_table_pattern, sql_content, re.IGNORECASE | re.DOTALL):
            table_name = match.group(1)
            table_body = match.group(2)

            table = self._parse_table(table_name, table_body)
            if table:
                tables.append(table)

        # Extract standalone CREATE INDEX statements
        if self.config.include_indexes:
            self._extract_standalone_indexes(sql_content, tables)

        # Extract ALTER TABLE ADD FOREIGN KEY statements
        if self.config.include_foreign_keys:
            self._extract_alter_foreign_keys(sql_content, tables)

        return DatabaseSchema(
            name=source_name,
            tables=tables,
            source=source_name,
        )

    def _parse_table(self, table_name: str, table_body: str) -> Optional[TableDefinition]:
        """Parse a CREATE TABLE body into a TableDefinition."""
        columns: list[ColumnDefinition] = []
        indexes: list[IndexDefinition] = []
        foreign_keys: list[ForeignKeyDefinition] = []
        primary_key: list[str] = []

        # Split by commas, but handle parentheses
        parts = self._split_table_body(table_body)

        for part in parts:
            part = part.strip()
            if not part:
                continue

            # Check for PRIMARY KEY
            pk_match = re.match(r'PRIMARY\s+KEY\s*\(([^)]+)\)', part, re.IGNORECASE)
            if pk_match:
                pk_cols = [c.strip().strip('`"') for c in pk_match.group(1).split(',')]
                primary_key = pk_cols
                continue

            # Check for FOREIGN KEY
            fk_match = re.match(
                r'(?:CONSTRAINT\s+[`"]?(\w+)[`"]?\s+)?FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+[`"]?(\w+)[`"]?\s*\(([^)]+)\)(?:\s+ON\s+DELETE\s+(\w+))?(?:\s+ON\s+UPDATE\s+(\w+))?',
                part, re.IGNORECASE
            )
            if fk_match:
                fk = ForeignKeyDefinition(
                    name=fk_match.group(1) or f"fk_{table_name}_{fk_match.group(3)}",
                    table_name=table_name,
                    columns=[c.strip().strip('`"') for c in fk_match.group(2).split(',')],
                    reference_table=fk_match.group(3),
                    reference_columns=[c.strip().strip('`"') for c in fk_match.group(4).split(',')],
                    on_delete=fk_match.group(5),
                    on_update=fk_match.group(6),
                )
                foreign_keys.append(fk)
                continue

            # Check for INDEX/KEY
            idx_match = re.match(
                r'(?:(UNIQUE)\s+)?(?:INDEX|KEY)\s+[`"]?(\w+)[`"]?\s*\(([^)]+)\)',
                part, re.IGNORECASE
            )
            if idx_match:
                idx = IndexDefinition(
                    name=idx_match.group(2),
                    table_name=table_name,
                    columns=[c.strip().strip('`"') for c in idx_match.group(3).split(',')],
                    is_unique=idx_match.group(1) is not None,
                )
                indexes.append(idx)
                continue

            # Check for UNIQUE
            unique_match = re.match(r'UNIQUE\s*\(([^)]+)\)', part, re.IGNORECASE)
            if unique_match:
                continue

            # Parse as column
            col = self._parse_column(part)
            if col:
                if col.is_primary_key:
                    primary_key.append(col.name)
                columns.append(col)

        return TableDefinition(
            name=table_name,
            columns=columns,
            indexes=indexes,
            foreign_keys=foreign_keys,
            primary_key=primary_key,
        )

    def _split_table_body(self, body: str) -> list[str]:
        """Split table body by commas, respecting parentheses."""
        parts = []
        current = []
        depth = 0

        for char in body:
            if char == '(':
                depth += 1
                current.append(char)
            elif char == ')':
                depth -= 1
                current.append(char)
            elif char == ',' and depth == 0:
                parts.append(''.join(current))
                current = []
            else:
                current.append(char)

        if current:
            parts.append(''.join(current))

        return parts

    def _parse_column(self, col_def: str) -> Optional[ColumnDefinition]:
        """Parse a column definition string."""
        col_def = col_def.strip()
        if not col_def:
            return None

        # Basic column pattern
        col_pattern = r'^[`"]?(\w+)[`"]?\s+(\w+)(?:\(([^)]+)\))?(.*)$'
        match = re.match(col_pattern, col_def, re.IGNORECASE)
        if not match:
            return None

        name = match.group(1)
        data_type = match.group(2).upper()
        size_str = match.group(3)
        rest = match.group(4).upper() if match.group(4) else ""

        # Parse size/precision
        length = None
        scale = None
        if size_str:
            size_parts = size_str.split(',')
            length = int(size_parts[0].strip())
            if len(size_parts) > 1:
                scale = int(size_parts[1].strip())

        # Parse modifiers
        nullable = "NOT NULL" not in rest
        is_pk = "PRIMARY KEY" in rest
        is_auto = "AUTO_INCREMENT" in rest or "SERIAL" in data_type
        is_unique = "UNIQUE" in rest

        # Parse default value
        default_value = None
        default_match = re.search(r"DEFAULT\s+([^\s,]+)", rest, re.IGNORECASE)
        if default_match:
            default_value = default_match.group(1)

        return ColumnDefinition(
            name=name,
            data_type=data_type,
            length=length,
            scale=scale,
            nullable=nullable,
            default_value=default_value,
            is_primary_key=is_pk,
            is_auto_increment=is_auto,
            is_unique=is_unique,
        )

    def _extract_standalone_indexes(
        self,
        sql_content: str,
        tables: list[TableDefinition]
    ) -> None:
        """Extract standalone CREATE INDEX statements."""
        table_map = {t.name.lower(): t for t in tables}

        idx_pattern = r'CREATE\s+(?:(UNIQUE)\s+)?INDEX\s+[`"]?(\w+)[`"]?\s+ON\s+[`"]?(\w+)[`"]?\s*\(([^)]+)\)'
        for match in re.finditer(idx_pattern, sql_content, re.IGNORECASE):
            is_unique = match.group(1) is not None
            idx_name = match.group(2)
            table_name = match.group(3)
            columns = [c.strip().strip('`"') for c in match.group(4).split(',')]

            table = table_map.get(table_name.lower())
            if table:
                table.indexes.append(IndexDefinition(
                    name=idx_name,
                    table_name=table_name,
                    columns=columns,
                    is_unique=is_unique,
                ))

    def _extract_alter_foreign_keys(
        self,
        sql_content: str,
        tables: list[TableDefinition]
    ) -> None:
        """Extract ALTER TABLE ADD FOREIGN KEY statements."""
        table_map = {t.name.lower(): t for t in tables}

        fk_pattern = r'ALTER\s+TABLE\s+[`"]?(\w+)[`"]?\s+ADD\s+(?:CONSTRAINT\s+[`"]?(\w+)[`"]?\s+)?FOREIGN\s+KEY\s*\(([^)]+)\)\s*REFERENCES\s+[`"]?(\w+)[`"]?\s*\(([^)]+)\)'
        for match in re.finditer(fk_pattern, sql_content, re.IGNORECASE):
            table_name = match.group(1)
            fk_name = match.group(2) or f"fk_{table_name}_{match.group(4)}"
            columns = [c.strip().strip('`"') for c in match.group(3).split(',')]
            ref_table = match.group(4)
            ref_cols = [c.strip().strip('`"') for c in match.group(5).split(',')]

            table = table_map.get(table_name.lower())
            if table:
                table.foreign_keys.append(ForeignKeyDefinition(
                    name=fk_name,
                    table_name=table_name,
                    columns=columns,
                    reference_table=ref_table,
                    reference_columns=ref_cols,
                ))

    def get_table_dependencies(self, schema: DatabaseSchema) -> dict[str, list[str]]:
        """
        Get table dependencies based on foreign keys.

        Args:
            schema: Database schema to analyze.

        Returns:
            Dictionary mapping table names to their dependencies.
        """
        dependencies: dict[str, list[str]] = {}

        for table in schema.tables:
            deps = []
            for fk in table.foreign_keys:
                if fk.reference_table != table.name:
                    deps.append(fk.reference_table)
            dependencies[table.name] = deps

        return dependencies

    def get_ordered_tables(self, schema: DatabaseSchema) -> list[str]:
        """
        Get tables in dependency order for creation.

        Args:
            schema: Database schema to analyze.

        Returns:
            List of table names in creation order.
        """
        dependencies = self.get_table_dependencies(schema)
        ordered: list[str] = []
        remaining = set(dependencies.keys())

        while remaining:
            # Find tables with no unresolved dependencies
            ready = []
            for table in remaining:
                deps = dependencies.get(table, [])
                if all(d in ordered or d not in remaining for d in deps):
                    ready.append(table)

            if not ready:
                # Circular dependency - just add remaining
                ordered.extend(sorted(remaining))
                break

            for table in sorted(ready):
                ordered.append(table)
                remaining.remove(table)

        return ordered
