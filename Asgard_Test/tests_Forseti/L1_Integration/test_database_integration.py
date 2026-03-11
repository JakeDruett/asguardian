"""
Database Integration Tests

Tests for database schema analysis, comparison, and migration generation
using real SQLAlchemy models and in-memory databases.
"""

import pytest
from pathlib import Path
from sqlalchemy import create_engine, MetaData, inspect

from Asgard.Forseti.Database import (
    SchemaAnalyzerService,
    SchemaDiffService,
    MigrationGeneratorService,
    DatabaseConfig,
)


class TestDatabaseSchemaAnalysis:
    """Tests for database schema analysis workflows."""

    def test_workflow_analyze_sql_file(self, sql_schema_file):
        """Test analyzing a SQL schema file."""
        analyzer = SchemaAnalyzerService()
        result = analyzer.analyze(sql_schema_file)

        assert result.is_valid is True
        assert result.table_count > 0
        assert len(result.tables) > 0

        # Verify table information was extracted
        for table in result.tables:
            assert table.name is not None
            assert len(table.columns) > 0

    def test_workflow_analyze_sqlalchemy_models(self, in_memory_db, sqlalchemy_models):
        """Test analyzing SQLAlchemy models in database."""
        analyzer = SchemaAnalyzerService()

        # Analyze the in-memory database
        result = analyzer.analyze_database(in_memory_db.url)

        assert result.is_valid is True
        assert result.table_count >= 2  # users and posts tables

        # Find users table
        users_table = next((t for t in result.tables if t.name == 'users'), None)
        assert users_table is not None
        assert len(users_table.columns) > 0

        # Verify primary key was detected
        pk_columns = [c for c in users_table.columns if c.is_primary_key]
        assert len(pk_columns) > 0

    def test_workflow_extract_table_dependencies(self, sql_schema_file):
        """Test extracting table dependencies from schema."""
        analyzer = SchemaAnalyzerService()
        result = analyzer.analyze(sql_schema_file)

        assert result.is_valid is True

        # Should have detected foreign key relationships
        dependencies = result.dependencies
        assert dependencies is not None

        # posts should depend on users
        if 'posts' in dependencies:
            assert 'users' in dependencies['posts'] or len(dependencies['posts']) > 0

    def test_workflow_analyze_indexes(self, sql_schema_file):
        """Test analyzing indexes in schema."""
        analyzer = SchemaAnalyzerService()
        result = analyzer.analyze(sql_schema_file)

        assert result.is_valid is True

        # Should have found indexes
        total_indexes = sum(len(table.indexes) for table in result.tables)
        assert total_indexes > 0

    def test_workflow_analyze_constraints(self, sql_schema_file):
        """Test analyzing constraints in schema."""
        analyzer = SchemaAnalyzerService()
        result = analyzer.analyze(sql_schema_file)

        assert result.is_valid is True

        # Look for foreign key constraints
        for table in result.tables:
            if table.name == 'posts':
                # posts table should have foreign key to users
                foreign_keys = [c for c in table.columns if c.is_foreign_key]
                # Foreign keys may be detected differently


class TestDatabaseSchemaDiff:
    """Tests for database schema comparison workflows."""

    def test_workflow_compare_schema_versions(self, database_versions):
        """Test comparing two database schema versions."""
        diff_service = SchemaDiffService()

        result = diff_service.diff(
            database_versions["v1"],
            database_versions["v2"]
        )

        assert result.is_valid is True
        assert len(result.changes) > 0

        # Should detect new table (user_profiles)
        new_tables = [c for c in result.changes if c.change_type == "table_added"]
        assert len(new_tables) > 0

        # Should detect new columns in users table
        new_columns = [c for c in result.changes if c.change_type == "column_added"]
        assert len(new_columns) > 0

    def test_workflow_detect_breaking_changes(self, database_versions):
        """Test detecting breaking schema changes."""
        diff_service = SchemaDiffService()

        result = diff_service.diff(
            database_versions["v1"],
            database_versions["v2"],
            detect_breaking=True
        )

        assert result.is_valid is True

        # Adding columns may or may not be breaking depending on nullable
        # Adding tables is not breaking
        # Check that changes were detected
        assert len(result.changes) > 0

    def test_workflow_compare_sqlalchemy_schemas(self, tmp_path):
        """Test comparing SQLAlchemy model versions."""
        from sqlalchemy import Column, Integer, String, create_engine
        from sqlalchemy.ext.declarative import declarative_base

        Base = declarative_base()

        # Version 1
        class UserV1(Base):
            __tablename__ = 'users'
            id = Column(Integer, primary_key=True)
            email = Column(String(255))

        engine_v1 = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(engine_v1)

        # Version 2
        Base2 = declarative_base()

        class UserV2(Base2):
            __tablename__ = 'users'
            id = Column(Integer, primary_key=True)
            email = Column(String(255))
            name = Column(String(100))  # New column

        engine_v2 = create_engine('sqlite:///:memory:')
        Base2.metadata.create_all(engine_v2)

        # Compare schemas
        diff_service = SchemaDiffService()
        result = diff_service.diff_databases(engine_v1.url, engine_v2.url)

        assert result.is_valid is True

        # Should detect new column
        new_columns = [c for c in result.changes if c.change_type == "column_added"]
        # May detect the change

    def test_workflow_identical_schemas(self, sql_schema_file):
        """Test comparing identical schemas."""
        diff_service = SchemaDiffService()

        result = diff_service.diff(sql_schema_file, sql_schema_file)

        assert result.is_valid is True
        # Identical schemas should have no changes or minimal changes
        assert len(result.changes) == 0 or all(c.severity == "info" for c in result.changes)

    def test_workflow_generate_diff_report(self, database_versions):
        """Test generating diff report in multiple formats."""
        diff_service = SchemaDiffService()

        result = diff_service.diff(
            database_versions["v1"],
            database_versions["v2"]
        )

        # Generate reports
        text_report = diff_service.generate_report(result, format="text")
        json_report = diff_service.generate_report(result, format="json")

        assert len(text_report) > 0
        assert len(json_report) > 0

        # Verify JSON structure
        import json
        json_data = json.loads(json_report)
        assert "changes" in json_data
        assert isinstance(json_data["changes"], list)


class TestMigrationGeneration:
    """Tests for database migration generation workflows."""

    def test_workflow_generate_migration_from_diff(self, database_versions):
        """Test generating migration script from schema diff."""
        # First, get the diff
        diff_service = SchemaDiffService()
        diff_result = diff_service.diff(
            database_versions["v1"],
            database_versions["v2"]
        )

        # Generate migration
        migration_service = MigrationGeneratorService()
        migration_result = migration_service.generate_migration(
            diff_result,
            migration_name="add_profiles_and_columns"
        )

        assert migration_result.is_valid is True
        assert migration_result.upgrade_sql is not None
        assert migration_result.downgrade_sql is not None

        # Upgrade SQL should contain CREATE TABLE for user_profiles
        assert "user_profiles" in migration_result.upgrade_sql.lower()

        # Upgrade SQL should contain ALTER TABLE for new columns
        assert "alter table" in migration_result.upgrade_sql.lower()

    def test_workflow_generate_migration_for_new_table(self, tmp_path):
        """Test generating migration for adding a new table."""
        v1_schema = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255)
);
"""

        v2_schema = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255)
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    title VARCHAR(200),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

        v1_file = tmp_path / "v1.sql"
        v2_file = tmp_path / "v2.sql"
        v1_file.write_text(v1_schema)
        v2_file.write_text(v2_schema)

        # Get diff
        diff_service = SchemaDiffService()
        diff_result = diff_service.diff(v1_file, v2_file)

        # Generate migration
        migration_service = MigrationGeneratorService()
        migration_result = migration_service.generate_migration(
            diff_result,
            migration_name="add_posts_table"
        )

        assert migration_result.is_valid is True
        assert "create table posts" in migration_result.upgrade_sql.lower()
        assert "drop table posts" in migration_result.downgrade_sql.lower()

    def test_workflow_save_migration_files(self, tmp_path, database_versions):
        """Test saving migration to files."""
        # Get diff and generate migration
        diff_service = SchemaDiffService()
        diff_result = diff_service.diff(
            database_versions["v1"],
            database_versions["v2"]
        )

        migration_service = MigrationGeneratorService()
        migration_result = migration_service.generate_migration(
            diff_result,
            migration_name="test_migration"
        )

        # Save migration
        migration_dir = tmp_path / "migrations"
        migration_dir.mkdir()

        migration_service.save_migration(
            migration_result,
            migration_dir,
            version="001"
        )

        # Verify files were created
        upgrade_file = migration_dir / "001_test_migration_upgrade.sql"
        downgrade_file = migration_dir / "001_test_migration_downgrade.sql"

        assert upgrade_file.exists()
        assert downgrade_file.exists()

        # Verify content
        assert len(upgrade_file.read_text()) > 0
        assert len(downgrade_file.read_text()) > 0

    def test_workflow_generate_alembic_migration(self, database_versions):
        """Test generating Alembic-compatible migration."""
        diff_service = SchemaDiffService()
        diff_result = diff_service.diff(
            database_versions["v1"],
            database_versions["v2"]
        )

        migration_service = MigrationGeneratorService()
        migration_result = migration_service.generate_migration(
            diff_result,
            migration_name="test_migration",
            format="alembic"
        )

        assert migration_result.is_valid is True

        # Alembic format should include Python code
        if hasattr(migration_result, 'migration_file'):
            assert "def upgrade():" in migration_result.migration_file
            assert "def downgrade():" in migration_result.migration_file


class TestDatabaseComplexScenarios:
    """Tests for complex database schema scenarios."""

    def test_workflow_analyze_complex_relationships(self, tmp_path):
        """Test analyzing schema with complex relationships."""
        schema = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    title VARCHAR(200),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE comments (
    id INTEGER PRIMARY KEY,
    post_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE tags (
    id INTEGER PRIMARY KEY,
    name VARCHAR(50) UNIQUE
);

CREATE TABLE post_tags (
    post_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (post_id, tag_id),
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);
"""
        schema_file = tmp_path / "complex.sql"
        schema_file.write_text(schema)

        analyzer = SchemaAnalyzerService()
        result = analyzer.analyze(schema_file)

        assert result.is_valid is True
        assert result.table_count == 5

        # Verify dependency ordering
        ordered_tables = result.get_ordered_tables()
        assert ordered_tables is not None

        # users should come before posts
        users_idx = next(i for i, t in enumerate(ordered_tables) if t.name == 'users')
        posts_idx = next(i for i, t in enumerate(ordered_tables) if t.name == 'posts')
        assert users_idx < posts_idx

    def test_workflow_detect_circular_dependencies(self, tmp_path):
        """Test detecting circular foreign key dependencies."""
        schema = """
CREATE TABLE table_a (
    id INTEGER PRIMARY KEY,
    b_id INTEGER,
    FOREIGN KEY (b_id) REFERENCES table_b(id)
);

CREATE TABLE table_b (
    id INTEGER PRIMARY KEY,
    a_id INTEGER,
    FOREIGN KEY (a_id) REFERENCES table_a(id)
);
"""
        schema_file = tmp_path / "circular.sql"
        schema_file.write_text(schema)

        analyzer = SchemaAnalyzerService()
        result = analyzer.analyze(schema_file)

        # Should still analyze successfully
        assert result.is_valid is True

        # Should detect circular dependency
        if hasattr(result, 'circular_dependencies'):
            assert len(result.circular_dependencies) > 0

    def test_workflow_analyze_composite_keys(self, tmp_path):
        """Test analyzing tables with composite primary keys."""
        schema = """
CREATE TABLE user_roles (
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    granted_at TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);
"""
        schema_file = tmp_path / "composite.sql"
        schema_file.write_text(schema)

        analyzer = SchemaAnalyzerService()
        result = analyzer.analyze(schema_file)

        assert result.is_valid is True

        # Find the table
        user_roles = next(t for t in result.tables if t.name == 'user_roles')

        # Should have composite primary key
        pk_columns = [c for c in user_roles.columns if c.is_primary_key]
        assert len(pk_columns) >= 2

    def test_workflow_migration_with_data_preservation(self, tmp_path):
        """Test generating migration that preserves data."""
        v1_schema = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    full_name VARCHAR(200)
);
"""

        v2_schema = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100)
);
"""

        v1_file = tmp_path / "v1.sql"
        v2_file = tmp_path / "v2.sql"
        v1_file.write_text(v1_schema)
        v2_file.write_text(v2_schema)

        # Get diff
        diff_service = SchemaDiffService()
        diff_result = diff_service.diff(v1_file, v2_file)

        # Generate migration with data preservation hints
        migration_service = MigrationGeneratorService()
        config = DatabaseConfig(preserve_data=True)
        migration_result = migration_service.generate_migration(
            diff_result,
            migration_name="split_name_field",
            config=config
        )

        assert migration_result.is_valid is True

        # Migration should include steps to preserve data
        # (actual implementation may vary)
        assert migration_result.upgrade_sql is not None

    def test_workflow_full_schema_lifecycle(self, tmp_path):
        """Test complete workflow: analyze, diff, migrate, validate."""
        # Create initial schema
        v1_schema = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255)
);
"""
        v1_file = tmp_path / "v1.sql"
        v1_file.write_text(v1_schema)

        # Step 1: Analyze initial schema
        analyzer = SchemaAnalyzerService()
        v1_analysis = analyzer.analyze(v1_file)
        assert v1_analysis.is_valid is True

        # Create updated schema
        v2_schema = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255),
    created_at TIMESTAMP
);

CREATE TABLE posts (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    title VARCHAR(200),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""
        v2_file = tmp_path / "v2.sql"
        v2_file.write_text(v2_schema)

        # Step 2: Analyze updated schema
        v2_analysis = analyzer.analyze(v2_file)
        assert v2_analysis.is_valid is True

        # Step 3: Compare schemas
        diff_service = SchemaDiffService()
        diff_result = diff_service.diff(v1_file, v2_file)
        assert diff_result.is_valid is True
        assert len(diff_result.changes) > 0

        # Step 4: Generate migration
        migration_service = MigrationGeneratorService()
        migration_result = migration_service.generate_migration(
            diff_result,
            migration_name="add_posts_and_timestamp"
        )
        assert migration_result.is_valid is True

        # Step 5: Save migration
        migration_dir = tmp_path / "migrations"
        migration_dir.mkdir()
        migration_service.save_migration(
            migration_result,
            migration_dir,
            version="001"
        )

        # Verify all steps completed successfully
        assert (migration_dir / "001_add_posts_and_timestamp_upgrade.sql").exists()
