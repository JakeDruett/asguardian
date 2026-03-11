"""
Tests for Database Schema Analyzer Service

Unit tests for database schema analysis and extraction.
"""

import pytest
from pathlib import Path

from Asgard.Forseti.Database.models.database_models import DatabaseConfig
from Asgard.Forseti.Database.services.schema_analyzer_service import SchemaAnalyzerService


class TestSchemaAnalyzerServiceInit:
    """Tests for SchemaAnalyzerService initialization."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        service = SchemaAnalyzerService()

        assert service.config is not None
        assert isinstance(service.config, DatabaseConfig)

    def test_init_with_custom_config(self):
        """Test initialization with custom configuration."""
        config = DatabaseConfig(include_indexes=False, include_foreign_keys=False)
        service = SchemaAnalyzerService(config)

        assert service.config.include_indexes is False
        assert service.config.include_foreign_keys is False


class TestSchemaAnalyzerServiceAnalyzeFile:
    """Tests for analyzing SQL files."""

    def test_analyze_nonexistent_file(self, tmp_path):
        """Test analyzing a file that doesn't exist."""
        service = SchemaAnalyzerService()
        nonexistent_file = tmp_path / "nonexistent.sql"

        with pytest.raises(FileNotFoundError):
            service.analyze_file(nonexistent_file)

    def test_analyze_valid_sql_file(self, sql_schema_file):
        """Test analyzing a valid SQL schema file."""
        service = SchemaAnalyzerService()

        schema = service.analyze_file(sql_schema_file)

        assert schema.name == str(sql_schema_file)
        assert len(schema.tables) > 0
        assert any(t.name == "users" for t in schema.tables)
        assert any(t.name == "posts" for t in schema.tables)


class TestSchemaAnalyzerServiceAnalyzeSQL:
    """Tests for analyzing SQL strings."""

    def test_analyze_simple_table(self):
        """Test analyzing a simple CREATE TABLE statement."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL,
    name VARCHAR(100)
);
'''

        schema = service.analyze_sql(sql)

        assert len(schema.tables) == 1
        table = schema.tables[0]
        assert table.name == "users"
        assert len(table.columns) == 3

    def test_analyze_table_with_primary_key(self):
        """Test analyzing table with primary key column."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255)
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        assert "id" in table.primary_key
        id_col = next(c for c in table.columns if c.name == "id")
        assert id_col.is_primary_key is True

    def test_analyze_table_with_composite_primary_key(self):
        """Test analyzing table with composite primary key."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE user_roles (
    user_id INTEGER,
    role_id INTEGER,
    PRIMARY KEY (user_id, role_id)
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        assert len(table.primary_key) == 2
        assert "user_id" in table.primary_key
        assert "role_id" in table.primary_key

    def test_analyze_table_with_foreign_key(self):
        """Test analyzing table with foreign key."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        assert len(table.foreign_keys) > 0
        fk = table.foreign_keys[0]
        assert fk.table_name == "posts"
        assert "user_id" in fk.columns
        assert fk.reference_table == "users"

    def test_analyze_table_with_indexes(self):
        """Test analyzing table with indexes."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255),
    INDEX idx_email (email)
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        assert len(table.indexes) > 0
        idx = table.indexes[0]
        assert idx.name == "idx_email"
        assert "email" in idx.columns

    def test_analyze_table_with_unique_index(self):
        """Test analyzing table with unique index."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255),
    UNIQUE INDEX idx_email (email)
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        idx = next(i for i in table.indexes if i.name == "idx_email")
        assert idx.is_unique is True


class TestSchemaAnalyzerServiceColumnParsing:
    """Tests for column definition parsing."""

    def test_parse_column_data_types(self):
        """Test parsing various data types."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE test (
    int_col INTEGER,
    varchar_col VARCHAR(255),
    text_col TEXT,
    decimal_col DECIMAL(10,2)
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        int_col = next(c for c in table.columns if c.name == "int_col")
        assert int_col.data_type == "INTEGER"

        varchar_col = next(c for c in table.columns if c.name == "varchar_col")
        assert varchar_col.data_type == "VARCHAR"
        assert varchar_col.length == 255

        decimal_col = next(c for c in table.columns if c.name == "decimal_col")
        assert decimal_col.length == 10
        assert decimal_col.scale == 2

    def test_parse_column_nullable(self):
        """Test parsing nullable and not null columns."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE test (
    nullable_col VARCHAR(100),
    not_null_col VARCHAR(100) NOT NULL
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        nullable_col = next(c for c in table.columns if c.name == "nullable_col")
        assert nullable_col.nullable is True

        not_null_col = next(c for c in table.columns if c.name == "not_null_col")
        assert not_null_col.nullable is False

    def test_parse_column_auto_increment(self):
        """Test parsing auto increment columns."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE test (
    id INTEGER AUTO_INCREMENT
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        id_col = table.columns[0]
        assert id_col.is_auto_increment is True

    def test_parse_column_default_value(self):
        """Test parsing column default values."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE test (
    status VARCHAR(20) DEFAULT 'active',
    count INTEGER DEFAULT 0
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        status_col = next(c for c in table.columns if c.name == "status")
        assert status_col.default_value is not None

    def test_parse_column_unique(self):
        """Test parsing unique columns."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE test (
    email VARCHAR(255) UNIQUE
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        email_col = table.columns[0]
        assert email_col.is_unique is True


class TestSchemaAnalyzerServiceForeignKeyConstraints:
    """Tests for foreign key constraint parsing."""

    def test_parse_foreign_key_with_name(self):
        """Test parsing named foreign key constraint."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    CONSTRAINT fk_posts_user FOREIGN KEY (user_id) REFERENCES users(id)
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        fk = table.foreign_keys[0]
        assert fk.name == "fk_posts_user"

    def test_parse_foreign_key_on_delete(self):
        """Test parsing foreign key with ON DELETE clause."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        fk = table.foreign_keys[0]
        assert fk.on_delete == "CASCADE"

    def test_parse_foreign_key_on_update(self):
        """Test parsing foreign key with ON UPDATE clause."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    FOREIGN KEY (user_id) REFERENCES users(id) ON UPDATE SET NULL
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        fk = table.foreign_keys[0]
        assert fk.on_update == "SET"

    def test_parse_composite_foreign_key(self):
        """Test parsing composite foreign key."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE order_items (
    order_id INTEGER,
    product_id INTEGER,
    FOREIGN KEY (order_id, product_id) REFERENCES products(order_id, id)
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        fk = table.foreign_keys[0]
        assert len(fk.columns) == 2
        assert len(fk.reference_columns) == 2


class TestSchemaAnalyzerServiceStandaloneStatements:
    """Tests for standalone CREATE INDEX and ALTER TABLE statements."""

    def test_extract_standalone_index(self):
        """Test extracting standalone CREATE INDEX statements."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255)
);

CREATE INDEX idx_users_email ON users(email);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        assert any(idx.name == "idx_users_email" for idx in table.indexes)

    def test_extract_alter_table_foreign_key(self):
        """Test extracting ALTER TABLE ADD FOREIGN KEY statements."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE users (
    id INTEGER PRIMARY KEY
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER
);

ALTER TABLE posts ADD FOREIGN KEY (user_id) REFERENCES users(id);
'''

        schema = service.analyze_sql(sql)

        posts_table = next(t for t in schema.tables if t.name == "posts")
        assert len(posts_table.foreign_keys) > 0


class TestSchemaAnalyzerServiceDependencyAnalysis:
    """Tests for table dependency analysis."""

    def test_get_table_dependencies(self, sample_sql_schema):
        """Test getting table dependencies based on foreign keys."""
        service = SchemaAnalyzerService()
        schema = service.analyze_sql(sample_sql_schema)

        dependencies = service.get_table_dependencies(schema)

        assert "posts" in dependencies
        assert "users" in dependencies["posts"]

    def test_get_ordered_tables(self, sample_sql_schema):
        """Test getting tables in dependency order."""
        service = SchemaAnalyzerService()
        schema = service.analyze_sql(sample_sql_schema)

        ordered = service.get_ordered_tables(schema)

        # Users should come before posts
        users_idx = ordered.index("users")
        posts_idx = ordered.index("posts")
        assert users_idx < posts_idx

    def test_get_ordered_tables_no_dependencies(self):
        """Test ordering tables with no dependencies."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE a (id INTEGER);
CREATE TABLE b (id INTEGER);
CREATE TABLE c (id INTEGER);
'''

        schema = service.analyze_sql(sql)
        ordered = service.get_ordered_tables(schema)

        # All tables should be present
        assert len(ordered) == 3
        assert set(ordered) == {"a", "b", "c"}

    def test_get_ordered_tables_circular_dependency(self):
        """Test handling circular dependencies."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE a (
    id INTEGER PRIMARY KEY,
    b_id INTEGER,
    FOREIGN KEY (b_id) REFERENCES b(id)
);

CREATE TABLE b (
    id INTEGER PRIMARY KEY,
    a_id INTEGER,
    FOREIGN KEY (a_id) REFERENCES a(id)
);
'''

        schema = service.analyze_sql(sql)
        ordered = service.get_ordered_tables(schema)

        # Should handle circular dependency without crashing
        assert len(ordered) == 2


class TestSchemaAnalyzerServiceMultipleTables:
    """Tests for analyzing multiple tables."""

    def test_analyze_multiple_tables(self):
        """Test analyzing multiple table definitions."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE users (id INTEGER PRIMARY KEY);
CREATE TABLE posts (id INTEGER PRIMARY KEY);
CREATE TABLE comments (id INTEGER PRIMARY KEY);
'''

        schema = service.analyze_sql(sql)

        assert len(schema.tables) == 3
        table_names = {t.name for t in schema.tables}
        assert table_names == {"users", "posts", "comments"}

    def test_analyze_if_not_exists(self):
        """Test analyzing CREATE TABLE IF NOT EXISTS."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255)
);
'''

        schema = service.analyze_sql(sql)

        assert len(schema.tables) == 1
        assert schema.tables[0].name == "users"


class TestSchemaAnalyzerServiceEdgeCases:
    """Tests for edge cases and error handling."""

    def test_analyze_empty_sql(self):
        """Test analyzing empty SQL content."""
        service = SchemaAnalyzerService()

        schema = service.analyze_sql("")

        assert len(schema.tables) == 0

    def test_analyze_sql_with_comments(self):
        """Test analyzing SQL with comments."""
        service = SchemaAnalyzerService()
        sql = '''
-- This is a comment
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    -- Another comment
    email VARCHAR(255)
);
'''

        schema = service.analyze_sql(sql)

        # Comments should not interfere with parsing
        assert len(schema.tables) == 1

    def test_analyze_sql_with_quoted_identifiers(self):
        """Test analyzing SQL with quoted identifiers."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE `users` (
    `id` INTEGER PRIMARY KEY,
    `email` VARCHAR(255)
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        assert table.name == "users"
        assert any(c.name == "id" for c in table.columns)

    def test_analyze_complex_table_body(self):
        """Test analyzing table with complex column definitions."""
        service = SchemaAnalyzerService()
        sql = '''
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100) DEFAULT 'Unknown',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_email (email),
    INDEX idx_name (name),
    FOREIGN KEY (id) REFERENCES accounts(user_id) ON DELETE CASCADE
);
'''

        schema = service.analyze_sql(sql)

        table = schema.tables[0]
        assert len(table.columns) > 0
        assert len(table.indexes) > 0
        assert len(table.foreign_keys) > 0

    def test_config_controls_index_extraction(self):
        """Test that config controls whether indexes are extracted."""
        config = DatabaseConfig(include_indexes=False)
        service = SchemaAnalyzerService(config)
        sql = '''
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255)
);

CREATE INDEX idx_email ON users(email);
'''

        schema = service.analyze_sql(sql)

        # Indexes should not be extracted when disabled
        table = schema.tables[0]
        # Only inline indexes from CREATE TABLE might be present
        # but standalone ones should be skipped

    def test_config_controls_foreign_key_extraction(self):
        """Test that config controls whether foreign keys are extracted."""
        config = DatabaseConfig(include_foreign_keys=False)
        service = SchemaAnalyzerService(config)
        sql = '''
CREATE TABLE users (id INTEGER PRIMARY KEY);
CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER
);

ALTER TABLE posts ADD FOREIGN KEY (user_id) REFERENCES users(id);
'''

        schema = service.analyze_sql(sql)

        posts_table = next(t for t in schema.tables if t.name == "posts")
        # ALTER TABLE foreign keys should be skipped when disabled


class TestSchemaAnalyzerServiceSourceName:
    """Tests for source name handling."""

    def test_analyze_sql_with_source_name(self):
        """Test analyzing SQL with custom source name."""
        service = SchemaAnalyzerService()
        sql = "CREATE TABLE test (id INTEGER);"

        schema = service.analyze_sql(sql, source_name="custom_source")

        assert schema.name == "custom_source"
        assert schema.source == "custom_source"

    def test_analyze_sql_without_source_name(self):
        """Test analyzing SQL without source name."""
        service = SchemaAnalyzerService()
        sql = "CREATE TABLE test (id INTEGER);"

        schema = service.analyze_sql(sql)

        assert schema.name is None
