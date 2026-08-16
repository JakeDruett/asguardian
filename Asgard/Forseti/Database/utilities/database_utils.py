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
    parts = [quote_identifier(name, dialect), data_type]

    if length is not None:
        parts[-1] = f"{data_type}({length})"

    if not nullable:
        parts.append("NOT NULL")

    safe_default = sanitize_sql_default(default)
    if safe_default is not None:
        parts.append(f"DEFAULT {safe_default}")

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


_SAFE_IDENT_RE = re.compile(r"^\w+$")
_UNSAFE_DEFAULT_RE = re.compile(r";|--|/\*|[\r\n\x00]")
_SQL_NUMBER_RE = re.compile(r"^[+-]?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?$")
_SQL_STRING_RE = re.compile(r"^'(?:[^']|'')*'$")
_SQL_DEFAULT_KEYWORDS = frozenset({"NULL", "TRUE", "FALSE"})
_DEFAULT_QUOTED_RE = re.compile(r"DEFAULT\s+('(?:[^']|'')*')", re.IGNORECASE)
_DEFAULT_TOKEN_RE = re.compile(r"DEFAULT\s+([^\s,]+)", re.IGNORECASE)


def quote_identifier(name: str, dialect: str = "mysql") -> str:
    """
    Quote an identifier for the given dialect.

    Only ``\\w+`` names are accepted so stacked SQL cannot ride in an identifier.

    Args:
        name: Identifier name.
        dialect: SQL dialect.

    Returns:
        Quoted identifier.

    Raises:
        ValueError: If ``name`` is not a safe identifier.
    """
    if not isinstance(name, str) or not _SAFE_IDENT_RE.fullmatch(name):
        raise ValueError("unsafe SQL identifier")

    if dialect == "mysql":
        return f"`{name.replace('`', '``')}`"
    if dialect == "mssql":
        return f"[{name.replace(']', ']]')}]"
    return '"' + name.replace('"', '""') + '"'


def is_safe_sql_default(value: str) -> bool:
    """Return True if ``value`` is a number, NULL/TRUE/FALSE, or a plain quoted string."""
    if not isinstance(value, str) or not value or _UNSAFE_DEFAULT_RE.search(value):
        return False
    text = value.strip()
    if text.upper() in _SQL_DEFAULT_KEYWORDS:
        return True
    if _SQL_NUMBER_RE.fullmatch(text):
        return True
    return bool(_SQL_STRING_RE.fullmatch(text))


def sanitize_sql_default(value: Optional[str]) -> Optional[str]:
    """Return a safe DEFAULT literal, or None if the value must not be interpolated."""
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not is_safe_sql_default(text):
        return None
    if text.upper() in _SQL_DEFAULT_KEYWORDS:
        return text.upper()
    return text


def parse_sql_default(rest: str) -> Optional[str]:
    """Extract a DEFAULT clause from the remainder of a column definition."""
    if not rest:
        return None
    quoted = _DEFAULT_QUOTED_RE.search(rest)
    raw = quoted.group(1) if quoted else None
    if raw is None:
        token = _DEFAULT_TOKEN_RE.search(rest)
        raw = token.group(1) if token else None
    return sanitize_sql_default(raw)


def sql_for_execution(sql: Optional[str]) -> Optional[str]:
    """Return ``sql`` when it is a single statement with no comment tokens."""
    if not isinstance(sql, str):
        return None
    stripped = sql.strip()
    if not stripped or "\x00" in stripped or "--" in stripped or "/*" in stripped:
        return None
    body = stripped[:-1].rstrip() if stripped.endswith(";") else stripped
    if ";" in body:
        return None
    return stripped


def alembic_execute_source(sql: str, indent: str = "    ") -> Optional[str]:
    """Emit ``op.execute(<python-literal>)`` for a single safe SQL statement."""
    safe = sql_for_execution(sql)
    if safe is None:
        return None
    return f"{indent}op.execute({repr(safe)})"


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
