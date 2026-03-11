"""
Forseti Database Module - Database Schema Management

This module provides comprehensive database schema handling including:
- Schema extraction and analysis
- Schema comparison and diffing
- Migration script generation

Usage:
    from Asgard.Forseti.Database import SchemaDiffService, DatabaseConfig

    # Compare two schemas
    service = SchemaDiffService()
    result = service.diff("schema_v1.sql", "schema_v2.sql")
    print(f"Changes: {len(result.changes)}")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

# Import models
from Asgard.Forseti.Database.models import (
    DatabaseConfig,
    DatabaseSchema,
    TableDefinition,
    ColumnDefinition,
    IndexDefinition,
    ForeignKeyDefinition,
    SchemaDiffResult,
    SchemaChange,
    ChangeType,
)

# Import services
from Asgard.Forseti.Database.services import (
    SchemaAnalyzerService,
    SchemaDiffService,
    MigrationGeneratorService,
)

# Import utilities
from Asgard.Forseti.Database.utilities import (
    load_sql_file,
    save_sql_file,
    parse_create_table,
    format_column_definition,
)

__all__ = [
    # Models
    "DatabaseConfig",
    "DatabaseSchema",
    "TableDefinition",
    "ColumnDefinition",
    "IndexDefinition",
    "ForeignKeyDefinition",
    "SchemaDiffResult",
    "SchemaChange",
    "ChangeType",
    # Services
    "SchemaAnalyzerService",
    "SchemaDiffService",
    "MigrationGeneratorService",
    # Utilities
    "load_sql_file",
    "save_sql_file",
    "parse_create_table",
    "format_column_definition",
]
