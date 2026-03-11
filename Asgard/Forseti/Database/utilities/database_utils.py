"""
Database Utilities - Helper functions for database schema handling.
"""

import re
from pathlib import Path
from typing import Any, Optional


def load_sql_file(file_path: Path) -> str:
    """
    Load a SQL file.

    Args:
        file_path: Path to the SQL file.

    Returns:
        SQL content string.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"SQL file not found: {file_path}")

    return file_path.read_text(encoding="utf-8")


def save_sql_file(file_path: Path, content: str) -> None:
    """
    Save SQL content to a file.

    Args:
        file_path: Path to save the file.
        content: SQL content.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")


def normalize_sql(sql: str) -> str:
    """
    Normalize SQL for comparison.

    Args:
        sql: SQL content.

    Returns:
        Normalized SQL string.
    """
    # Remove comments
    sql = re.sub(r'--[^\n]*', '', sql)
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    # Normalize whitespace
    sql = re.sub(r'\s+', ' ', sql)

    # Normalize quotes
    sql = sql.replace('`', '"')

    # Remove trailing semicolons
    sql = sql.strip().rstrip(';')

    return sql.strip()


def parse_create_table(sql: str) -> Optional[dict[str, Any]]:
    """
    Parse a CREATE TABLE statement.

    Args:
        sql: CREATE TABLE SQL statement.

    Returns:
        Dictionary with table information or None.
    """
    pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?\s*\(([^;]+)\)'
    match = re.search(pattern, sql, re.IGNORECASE | re.DOTALL)

    if not match:
        return None

    table_name = match.group(1)
    body = match.group(2)

    return {
        "name": table_name,
        "body": body,
    }


def format_column_definition(
    name: str,
    data_type: str,
    length: Optional[int] = None,
    nullable: bool = True,
    default: Optional[str] = None,
    auto_increment: bool = False,
    primary_key: bool = False,
    dialect: str = "mysql"
) -> str:
    """
    Format a column definition string.

    Args:
        name: Column name.
        data_type: Data type.
        length: Type length.
        nullable: Allow NULL.
        default: Default value.
        auto_increment: Auto-increment flag.
        primary_key: Primary key flag.
        dialect: SQL dialect.

    Returns:
        Formatted column definition.
    """
    parts = [name, data_type]

    if length is not None:
        parts[-1] = f"{data_type}({length})"

    if not nullable:
        parts.append("NOT NULL")

    if default is not None:
        parts.append(f"DEFAULT {default}")

    if auto_increment:
        if dialect == "postgresql":
            parts[1] = "SERIAL"
        else:
            parts.append("AUTO_INCREMENT")

    if primary_key:
        parts.append("PRIMARY KEY")

    return " ".join(parts)


def extract_table_names(sql: str) -> list[str]:
    """
    Extract all table names from SQL content.

    Args:
        sql: SQL content.

    Returns:
        List of table names.
    """
    tables = []

    # CREATE TABLE
    for match in re.finditer(r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?', sql, re.IGNORECASE):
        tables.append(match.group(1))

    return list(set(tables))


def get_sql_dialect(sql: str) -> str:
    """
    Detect SQL dialect from content.

    Args:
        sql: SQL content.

    Returns:
        Detected dialect (mysql, postgresql, sqlite, mssql).
    """
    sql_lower = sql.lower()

    # PostgreSQL indicators
    if "serial" in sql_lower or "::text" in sql_lower or "create sequence" in sql_lower:
        return "postgresql"

    # MySQL indicators
    if "auto_increment" in sql_lower or "engine=" in sql_lower or "charset=" in sql_lower:
        return "mysql"

    # SQLite indicators
    if "autoincrement" in sql_lower or "integer primary key" in sql_lower:
        return "sqlite"

    # MSSQL indicators
    if "identity(" in sql_lower or "[dbo]" in sql_lower:
        return "mssql"

    return "mysql"  # Default


def quote_identifier(name: str, dialect: str = "mysql") -> str:
    """
    Quote an identifier for the given dialect.

    Args:
        name: Identifier name.
        dialect: SQL dialect.

    Returns:
        Quoted identifier.
    """
    if dialect == "mysql":
        return f"`{name}`"
    elif dialect == "postgresql":
        return f'"{name}"'
    elif dialect == "mssql":
        return f"[{name}]"
    else:
        return f'"{name}"'


def parse_data_type(type_str: str) -> tuple[str, Optional[int], Optional[int]]:
    """
    Parse a data type string into components.

    Args:
        type_str: Data type string (e.g., "VARCHAR(255)", "DECIMAL(10,2)").

    Returns:
        Tuple of (base_type, length, scale).
    """
    match = re.match(r'(\w+)(?:\((\d+)(?:,(\d+))?\))?', type_str, re.IGNORECASE)
    if not match:
        return type_str.upper(), None, None

    base_type = match.group(1).upper()
    length = int(match.group(2)) if match.group(2) else None
    scale = int(match.group(3)) if match.group(3) else None

    return base_type, length, scale


def are_types_compatible(type1: str, type2: str) -> bool:
    """
    Check if two SQL types are compatible.

    Args:
        type1: First type.
        type2: Second type.

    Returns:
        True if compatible, False otherwise.
    """
    base1, _, _ = parse_data_type(type1)
    base2, _, _ = parse_data_type(type2)

    # Type families
    int_types = {"INT", "INTEGER", "BIGINT", "SMALLINT", "TINYINT", "MEDIUMINT"}
    float_types = {"FLOAT", "DOUBLE", "REAL", "DECIMAL", "NUMERIC"}
    text_types = {"VARCHAR", "CHAR", "TEXT", "TINYTEXT", "MEDIUMTEXT", "LONGTEXT"}
    date_types = {"DATE", "DATETIME", "TIMESTAMP", "TIME"}

    for family in [int_types, float_types, text_types, date_types]:
        if base1 in family and base2 in family:
            return True

    return base1 == base2
