"""
Database Models - Pydantic models for database schema handling.

These models represent database schema structures and diff results.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChangeType(str, Enum):
    """Types of schema changes."""
    ADD_TABLE = "add_table"
    DROP_TABLE = "drop_table"
    ADD_COLUMN = "add_column"
    DROP_COLUMN = "drop_column"
    MODIFY_COLUMN = "modify_column"
    ADD_INDEX = "add_index"
    DROP_INDEX = "drop_index"
    ADD_FOREIGN_KEY = "add_foreign_key"
    DROP_FOREIGN_KEY = "drop_foreign_key"
    ADD_CONSTRAINT = "add_constraint"
    DROP_CONSTRAINT = "drop_constraint"
    RENAME_TABLE = "rename_table"
    RENAME_COLUMN = "rename_column"


class ColumnType(str, Enum):
    """Common SQL column types."""
    INTEGER = "INTEGER"
    BIGINT = "BIGINT"
    SMALLINT = "SMALLINT"
    DECIMAL = "DECIMAL"
    NUMERIC = "NUMERIC"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    REAL = "REAL"
    VARCHAR = "VARCHAR"
    CHAR = "CHAR"
    TEXT = "TEXT"
    BOOLEAN = "BOOLEAN"
    DATE = "DATE"
    TIME = "TIME"
    DATETIME = "DATETIME"
    TIMESTAMP = "TIMESTAMP"
    BLOB = "BLOB"
    JSON = "JSON"
    UUID = "UUID"


class DatabaseConfig(BaseModel):
    """Configuration for database schema operations."""

    dialect: str = Field(
        default="mysql",
        description="SQL dialect (mysql, postgresql, sqlite, etc.)"
    )
    include_indexes: bool = Field(
        default=True,
        description="Include indexes in schema analysis"
    )
    include_foreign_keys: bool = Field(
        default=True,
        description="Include foreign keys in schema analysis"
    )
    include_constraints: bool = Field(
        default=True,
        description="Include constraints in schema analysis"
    )
    case_sensitive: bool = Field(
        default=False,
        description="Case-sensitive comparison of identifiers"
    )
    ignore_whitespace: bool = Field(
        default=True,
        description="Ignore whitespace differences"
    )


class ColumnDefinition(BaseModel):
    """Database column definition."""

    name: str = Field(description="Column name")
    data_type: str = Field(description="Column data type")
    length: Optional[int] = Field(default=None, description="Type length/precision")
    scale: Optional[int] = Field(default=None, description="Decimal scale")
    nullable: bool = Field(default=True, description="Allow NULL values")
    default_value: Optional[str] = Field(default=None, description="Default value")
    is_primary_key: bool = Field(default=False, description="Primary key flag")
    is_auto_increment: bool = Field(default=False, description="Auto-increment flag")
    is_unique: bool = Field(default=False, description="Unique constraint flag")
    comment: Optional[str] = Field(default=None, description="Column comment")
    collation: Optional[str] = Field(default=None, description="Column collation")

    def to_sql(self, dialect: str = "mysql") -> str:
        """Generate SQL column definition."""
        parts = [self.name, self.data_type]

        if self.length is not None:
            if self.scale is not None:
                parts[-1] = f"{self.data_type}({self.length},{self.scale})"
            else:
                parts[-1] = f"{self.data_type}({self.length})"

        if not self.nullable:
            parts.append("NOT NULL")

        if self.default_value is not None:
            parts.append(f"DEFAULT {self.default_value}")

        if self.is_auto_increment:
            if dialect == "postgresql":
                parts[1] = "SERIAL"
            else:
                parts.append("AUTO_INCREMENT")

        if self.is_primary_key:
            parts.append("PRIMARY KEY")

        if self.is_unique and not self.is_primary_key:
            parts.append("UNIQUE")

        return " ".join(parts)


class IndexDefinition(BaseModel):
    """Database index definition."""

    name: str = Field(description="Index name")
    table_name: str = Field(description="Table name")
    columns: list[str] = Field(description="Indexed columns")
    is_unique: bool = Field(default=False, description="Unique index flag")
    is_primary: bool = Field(default=False, description="Primary key index flag")
    index_type: Optional[str] = Field(default=None, description="Index type (BTREE, HASH, etc.)")

    def to_sql(self, dialect: str = "mysql") -> str:
        """Generate SQL index creation statement."""
        unique = "UNIQUE " if self.is_unique else ""
        columns = ", ".join(self.columns)
        return f"CREATE {unique}INDEX {self.name} ON {self.table_name} ({columns})"


class ForeignKeyDefinition(BaseModel):
    """Database foreign key definition."""

    name: str = Field(description="Constraint name")
    table_name: str = Field(description="Source table name")
    columns: list[str] = Field(description="Source columns")
    reference_table: str = Field(description="Referenced table")
    reference_columns: list[str] = Field(description="Referenced columns")
    on_delete: Optional[str] = Field(default=None, description="ON DELETE action")
    on_update: Optional[str] = Field(default=None, description="ON UPDATE action")

    def to_sql(self, dialect: str = "mysql") -> str:
        """Generate SQL foreign key constraint."""
        cols = ", ".join(self.columns)
        refs = ", ".join(self.reference_columns)
        sql = f"CONSTRAINT {self.name} FOREIGN KEY ({cols}) REFERENCES {self.reference_table} ({refs})"
        if self.on_delete:
            sql += f" ON DELETE {self.on_delete}"
        if self.on_update:
            sql += f" ON UPDATE {self.on_update}"
        return sql


class ConstraintDefinition(BaseModel):
    """Database constraint definition."""

    name: str = Field(description="Constraint name")
    table_name: str = Field(description="Table name")
    constraint_type: str = Field(description="Constraint type (CHECK, UNIQUE, etc.)")
    definition: str = Field(description="Constraint definition")
    columns: list[str] = Field(default_factory=list, description="Affected columns")


class TableDefinition(BaseModel):
    """Database table definition."""

    name: str = Field(description="Table name")
    schema_name: Optional[str] = Field(default=None, description="Schema/database name")
    columns: list[ColumnDefinition] = Field(
        default_factory=list,
        description="Table columns"
    )
    indexes: list[IndexDefinition] = Field(
        default_factory=list,
        description="Table indexes"
    )
    foreign_keys: list[ForeignKeyDefinition] = Field(
        default_factory=list,
        description="Foreign key constraints"
    )
    constraints: list[ConstraintDefinition] = Field(
        default_factory=list,
        description="Other constraints"
    )
    primary_key: list[str] = Field(
        default_factory=list,
        description="Primary key columns"
    )
    engine: Optional[str] = Field(default=None, description="Storage engine")
    charset: Optional[str] = Field(default=None, description="Character set")
    collation: Optional[str] = Field(default=None, description="Collation")
    comment: Optional[str] = Field(default=None, description="Table comment")

    def get_column(self, name: str) -> Optional[ColumnDefinition]:
        """Get a column by name."""
        for col in self.columns:
            if col.name == name:
                return col
        return None

    def to_sql(self, dialect: str = "mysql") -> str:
        """Generate CREATE TABLE statement."""
        lines = [f"CREATE TABLE {self.name} ("]

        # Columns
        col_defs = []
        for col in self.columns:
            col_def = f"  {col.to_sql(dialect)}"
            col_defs.append(col_def)

        # Primary key (if not inline)
        if self.primary_key and len(self.primary_key) > 1:
            pk_cols = ", ".join(self.primary_key)
            col_defs.append(f"  PRIMARY KEY ({pk_cols})")

        # Foreign keys
        for fk in self.foreign_keys:
            col_defs.append(f"  {fk.to_sql(dialect)}")

        lines.append(",\n".join(col_defs))
        lines.append(")")

        # Table options
        options = []
        if self.engine:
            options.append(f"ENGINE={self.engine}")
        if self.charset:
            options.append(f"DEFAULT CHARSET={self.charset}")
        if options:
            lines[-1] += " " + " ".join(options)

        return "\n".join(lines)


class DatabaseSchema(BaseModel):
    """Complete database schema."""

    name: Optional[str] = Field(default=None, description="Database/schema name")
    tables: list[TableDefinition] = Field(
        default_factory=list,
        description="All tables"
    )
    extracted_at: datetime = Field(
        default_factory=datetime.now,
        description="Extraction timestamp"
    )
    source: Optional[str] = Field(
        default=None,
        description="Source (connection string or file)"
    )

    @property
    def table_count(self) -> int:
        """Return the number of tables."""
        return len(self.tables)

    def get_table(self, name: str) -> Optional[TableDefinition]:
        """Get a table by name."""
        for table in self.tables:
            if table.name == name:
                return table
        return None

    def get_all_foreign_keys(self) -> list[ForeignKeyDefinition]:
        """Get all foreign keys across all tables."""
        fks = []
        for table in self.tables:
            fks.extend(table.foreign_keys)
        return fks


class SchemaChange(BaseModel):
    """Represents a single schema change."""

    change_type: ChangeType = Field(description="Type of change")
    table_name: str = Field(description="Affected table")
    object_name: Optional[str] = Field(
        default=None,
        description="Affected object (column, index, etc.)"
    )
    old_definition: Optional[str] = Field(
        default=None,
        description="Old definition"
    )
    new_definition: Optional[str] = Field(
        default=None,
        description="New definition"
    )
    migration_sql: Optional[str] = Field(
        default=None,
        description="SQL to apply the change"
    )
    rollback_sql: Optional[str] = Field(
        default=None,
        description="SQL to rollback the change"
    )

    class Config:
        use_enum_values = True


class SchemaDiffResult(BaseModel):
    """Result of schema comparison."""

    source_schema: Optional[str] = Field(
        default=None,
        description="Source schema identifier"
    )
    target_schema: Optional[str] = Field(
        default=None,
        description="Target schema identifier"
    )
    is_identical: bool = Field(
        description="Whether schemas are identical"
    )
    changes: list[SchemaChange] = Field(
        default_factory=list,
        description="List of changes"
    )
    added_tables: list[str] = Field(
        default_factory=list,
        description="Tables added in target"
    )
    dropped_tables: list[str] = Field(
        default_factory=list,
        description="Tables removed in target"
    )
    modified_tables: list[str] = Field(
        default_factory=list,
        description="Tables modified in target"
    )
    compared_at: datetime = Field(
        default_factory=datetime.now,
        description="Comparison timestamp"
    )
    comparison_time_ms: float = Field(
        default=0.0,
        description="Time taken to compare"
    )

    @property
    def change_count(self) -> int:
        """Return the total number of changes."""
        return len(self.changes)

    @property
    def has_breaking_changes(self) -> bool:
        """Check if there are breaking changes."""
        breaking_types = {ChangeType.DROP_TABLE, ChangeType.DROP_COLUMN}
        return any(c.change_type in breaking_types for c in self.changes)
