"""
GraphQL Utilities - Helper functions for GraphQL schema handling.
"""

import re
from pathlib import Path
from typing import Any, Optional

from Asgard.Forseti.GraphQL.models.graphql_models import GraphQLSchema, GraphQLType, GraphQLTypeKind


# Built-in scalar types
BUILTIN_SCALARS = {"String", "Int", "Float", "Boolean", "ID"}

# Built-in directives
BUILTIN_DIRECTIVES = {"skip", "include", "deprecated", "specifiedBy"}


def load_schema_file(file_path: Path) -> str:
    """
    Load a GraphQL schema from a file.

    Args:
        file_path: Path to the schema file.

    Returns:
        Schema SDL string.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Schema file not found: {file_path}")

    return file_path.read_text(encoding="utf-8")


def save_schema_file(file_path: Path, sdl: str) -> None:
    """
    Save a GraphQL schema to a file.

    Args:
        file_path: Path to save the schema.
        sdl: Schema SDL string.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(sdl, encoding="utf-8")


def parse_sdl(sdl: str) -> dict[str, Any]:
    """
    Parse GraphQL SDL into a basic structure.

    This is a simplified parser for validation purposes.
    For full parsing, use the graphql-core library.

    Args:
        sdl: GraphQL SDL string.

    Returns:
        Dictionary with parsed schema elements.

    Raises:
        ValueError: If the SDL has syntax errors.
    """
    result: dict[str, Any] = {
        "types": {},
        "interfaces": {},
        "enums": {},
        "unions": {},
        "inputs": {},
        "scalars": set(),
        "directives": {},
    }

    # Remove comments
    sdl_clean = re.sub(r'#[^\n]*', '', sdl)

    # Remove string literals to avoid false matches
    sdl_clean = re.sub(r'"""[\s\S]*?"""', '""', sdl_clean)
    sdl_clean = re.sub(r'"[^"]*"', '""', sdl_clean)

    # Parse type definitions
    type_pattern = r'type\s+(\w+)(?:\s+implements\s+([^{]+))?\s*\{([^}]*)\}'
    for match in re.finditer(type_pattern, sdl_clean):
        name = match.group(1)
        implements = match.group(2)
        body = match.group(3)

        interfaces = []
        if implements:
            interfaces = [i.strip() for i in implements.split("&") if i.strip()]

        fields = _parse_fields(body)
        result["types"][name] = {
            "interfaces": interfaces,
            "fields": fields,
        }

    # Parse interfaces
    interface_pattern = r'interface\s+(\w+)\s*\{([^}]*)\}'
    for match in re.finditer(interface_pattern, sdl_clean):
        name = match.group(1)
        body = match.group(2)
        fields = _parse_fields(body)
        result["interfaces"][name] = {"fields": fields}

    # Parse enums
    enum_pattern = r'enum\s+(\w+)\s*\{([^}]*)\}'
    for match in re.finditer(enum_pattern, sdl_clean):
        name = match.group(1)
        body = match.group(2)
        values = [v.strip() for v in body.split() if v.strip() and not v.startswith("@")]
        result["enums"][name] = values

    # Parse unions
    union_pattern = r'union\s+(\w+)\s*=\s*([^{}\n]+)'
    for match in re.finditer(union_pattern, sdl_clean):
        name = match.group(1)
        types_str = match.group(2)
        types = [t.strip() for t in types_str.split("|") if t.strip()]
        result["unions"][name] = types

    # Parse inputs
    input_pattern = r'input\s+(\w+)\s*\{([^}]*)\}'
    for match in re.finditer(input_pattern, sdl_clean):
        name = match.group(1)
        body = match.group(2)
        fields = _parse_fields(body)
        result["inputs"][name] = {"fields": fields}

    # Parse scalars
    scalar_pattern = r'scalar\s+(\w+)'
    for match in re.finditer(scalar_pattern, sdl_clean):
        result["scalars"].add(match.group(1))

    # Parse directives
    directive_pattern = r'directive\s+@(\w+)(?:\([^)]*\))?\s+on\s+([A-Z_|]+)'
    for match in re.finditer(directive_pattern, sdl_clean):
        name = match.group(1)
        locations = [loc.strip() for loc in match.group(2).split("|")]
        result["directives"][name] = {"locations": locations}

    return result


def _parse_fields(body: str) -> dict[str, Any]:
    """Parse field definitions from a type body."""
    fields: dict[str, Any] = {}

    # Match field definitions
    field_pattern = r'(\w+)(?:\([^)]*\))?\s*:\s*([^\n@]+)'
    for match in re.finditer(field_pattern, body):
        name = match.group(1)
        type_str = match.group(2).strip()
        fields[name] = {"type": type_str}

    return fields


def merge_schemas(schemas: list[str]) -> str:
    """
    Merge multiple GraphQL schemas into one.

    Args:
        schemas: List of SDL strings.

    Returns:
        Merged SDL string.
    """
    merged_types: dict[str, str] = {}
    merged_directives: set[str] = set()

    for sdl in schemas:
        # Extract type definitions
        type_pattern = r'((?:type|interface|enum|union|input|scalar)\s+\w+[^}]*(?:\{[^}]*\})?)'
        for match in re.finditer(type_pattern, sdl):
            type_def = match.group(1).strip()
            # Extract name
            name_match = re.match(r'(?:type|interface|enum|union|input|scalar)\s+(\w+)', type_def)
            if name_match:
                name = name_match.group(1)
                # Merge fields for types
                if name in merged_types:
                    merged_types[name] = _merge_type_definitions(merged_types[name], type_def)
                else:
                    merged_types[name] = type_def

        # Extract directive definitions
        directive_pattern = r'(directive\s+@\w+[^\n]+)'
        for match in re.finditer(directive_pattern, sdl):
            merged_directives.add(match.group(1).strip())

    # Combine into single SDL
    lines = []
    for directive in sorted(merged_directives):
        lines.append(directive)
    if merged_directives:
        lines.append("")

    for name in sorted(merged_types.keys()):
        lines.append(merged_types[name])
        lines.append("")

    return "\n".join(lines)


def _merge_type_definitions(existing: str, new: str) -> str:
    """Merge two type definitions."""
    # Extract fields from both
    existing_fields = re.search(r'\{([^}]*)\}', existing)
    new_fields = re.search(r'\{([^}]*)\}', new)

    if not existing_fields or not new_fields:
        return new

    # Combine fields
    all_fields: dict[str, str] = {}

    field_pattern = r'(\w+)(?:\([^)]*\))?\s*:\s*([^\n]+)'
    for match in re.finditer(field_pattern, existing_fields.group(1)):
        all_fields[match.group(1)] = match.group(0).strip()
    for match in re.finditer(field_pattern, new_fields.group(1)):
        all_fields[match.group(1)] = match.group(0).strip()

    # Get type header
    header_match = re.match(r'((?:type|interface|input)\s+\w+[^{]*)', existing)
    header = header_match.group(1).strip() if header_match else ""

    # Build merged definition
    fields_str = "\n  ".join(all_fields.values())
    return f"{header} {{\n  {fields_str}\n}}"


def validate_type_name(name: str) -> bool:
    """
    Validate a GraphQL type name.

    Args:
        name: Type name to validate.

    Returns:
        True if valid, False otherwise.
    """
    # Must start with letter or underscore, contain only alphanumeric and underscore
    if not re.match(r'^[_A-Za-z][_0-9A-Za-z]*$', name):
        return False

    # Cannot start with double underscore (reserved for introspection)
    if name.startswith("__"):
        return False

    return True


def is_builtin_type(name: str) -> bool:
    """
    Check if a type name is a built-in scalar.

    Args:
        name: Type name to check.

    Returns:
        True if built-in, False otherwise.
    """
    # Remove non-null and list wrappers
    clean_name = name.replace("!", "").replace("[", "").replace("]", "").strip()
    return clean_name in BUILTIN_SCALARS


def extract_base_type(type_ref: str) -> str:
    """
    Extract the base type name from a type reference.

    Args:
        type_ref: Type reference (e.g., "[User!]!").

    Returns:
        Base type name (e.g., "User").
    """
    return type_ref.replace("!", "").replace("[", "").replace("]", "").strip()


def format_type_ref(
    base_type: str,
    is_list: bool = False,
    is_non_null: bool = False,
    is_item_non_null: bool = False
) -> str:
    """
    Format a type reference string.

    Args:
        base_type: Base type name.
        is_list: Whether it's a list type.
        is_non_null: Whether the type is non-null.
        is_item_non_null: Whether list items are non-null.

    Returns:
        Formatted type reference.
    """
    result = base_type
    if is_list:
        if is_item_non_null:
            result = f"[{result}!]"
        else:
            result = f"[{result}]"
    if is_non_null:
        result = f"{result}!"
    return result


def get_all_type_references(sdl: str) -> set[str]:
    """
    Get all type references in a schema.

    Args:
        sdl: GraphQL SDL string.

    Returns:
        Set of referenced type names.
    """
    refs: set[str] = set()

    # Find all type references in field definitions
    type_ref_pattern = r':\s*\[?\s*(\w+)[\]!]*'
    for match in re.finditer(type_ref_pattern, sdl):
        refs.add(match.group(1))

    # Find type references in implements
    implements_pattern = r'implements\s+([A-Za-z_&\s]+)\s*\{'
    for match in re.finditer(implements_pattern, sdl):
        interfaces = match.group(1).split("&")
        for interface in interfaces:
            refs.add(interface.strip())

    # Find union members
    union_pattern = r'union\s+\w+\s*=\s*([^{}\n]+)'
    for match in re.finditer(union_pattern, sdl):
        members = match.group(1).split("|")
        for member in members:
            refs.add(member.strip())

    return refs


def count_fields(sdl: str) -> int:
    """
    Count the number of fields in a schema.

    Args:
        sdl: GraphQL SDL string.

    Returns:
        Number of fields.
    """
    # Remove comments and strings
    clean = re.sub(r'#[^\n]*', '', sdl)
    clean = re.sub(r'"""[\s\S]*?"""', '', clean)
    clean = re.sub(r'"[^"]*"', '', clean)

    # Count field definitions
    field_pattern = r'^\s+\w+\s*[:(]'
    return len(re.findall(field_pattern, clean, re.MULTILINE))
