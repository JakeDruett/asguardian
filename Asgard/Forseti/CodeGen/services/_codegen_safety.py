"""Treat untrusted OpenAPI strings as data in generated client source."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_UNSAFE_IDENT_RE = re.compile(r"[^A-Za-z0-9_]")
_JSON_KEY_UNSAFE_RE = re.compile(r"[^A-Za-z0-9_.\-]")


def sanitize_identifier(name: str, *, fallback: str = "_unnamed") -> str:
    """Map a spec token onto ``[A-Za-z_][A-Za-z0-9_]*``. Never keeps quotes or braces."""
    text = "" if name is None else str(name)
    if _IDENT_RE.fullmatch(text):
        return text
    cleaned = _UNSAFE_IDENT_RE.sub("_", text)
    if not cleaned:
        return fallback
    if cleaned[0].isdigit():
        cleaned = f"_{cleaned}"
    if not _IDENT_RE.fullmatch(cleaned):
        return fallback
    return cleaned


def string_literal(value: str) -> str:
    """JSON-encode a string so it is a safe Python/JS/Go quoted literal."""
    return json.dumps("" if value is None else str(value))


def python_literal(value: Any) -> str:
    """Emit a Python literal for a Field default."""
    if isinstance(value, str):
        return json.dumps(value)
    return repr(value)


def escape_docstring(text: str) -> str:
    """Prevent ``\"\"\"`` breakout in generated Python docstrings."""
    return str(text).replace("\\", "\\\\").replace('"""', "'''")


def escape_block_comment(text: str) -> str:
    """Prevent ``*/`` or newline breakout in ``/* */`` / JSDoc comments."""
    return str(text).replace("*/", "* /").replace("\r", " ").replace("\n", " ")


def escape_line_comment(text: str) -> str:
    """Prevent newline injection in ``//`` comments."""
    return str(text).replace("\r", " ").replace("\n", " ")


def go_json_tag(prop_name: str) -> str:
    """Build a backtick json struct tag from a spec property name."""
    key = _JSON_KEY_UNSAFE_RE.sub("_", str(prop_name))
    return f'`json:"{key},omitempty"`'


def _path_param_names(parameters: Iterable[Any]) -> list[str]:
    names: list[str] = []
    for param in parameters:
        if getattr(param, "location", None) == "path":
            names.append(str(param.name))
    return names


def python_path_lines(path: str, parameters: Iterable[Any], indent: str = "        ") -> list[str]:
    """Assign ``path`` from a JSON string, then replace ``{param}`` placeholders."""
    lines = [f"{indent}path = {string_literal(path)}"]
    for raw in _path_param_names(parameters):
        ident = sanitize_identifier(raw)
        lines.append(
            f"{indent}path = path.replace({string_literal('{' + raw + '}')}, str({ident}))"
        )
    return lines


def ts_path_lines(path: str, parameters: Iterable[Any], indent: str = "    ") -> list[str]:
    """Assign ``path`` from JSON.stringify-equivalent data, then substitute params."""
    lines = [f"{indent}let path = {string_literal(path)};"]
    for raw in _path_param_names(parameters):
        ident = sanitize_identifier(raw)
        lines.append(
            f"{indent}path = path.split({string_literal('{' + raw + '}')}).join(String({ident}));"
        )
    return lines


def go_path_lines(
    path: str,
    parameters: Iterable[Any],
    to_camel_case_fn: Any,
    indent: str = "\t",
) -> list[str]:
    """Assign ``path`` from a quoted literal, then ``strings.Replace`` each placeholder."""
    lines = [f"{indent}path := {string_literal(path)}"]
    for raw in _path_param_names(parameters):
        go_name = sanitize_identifier(to_camel_case_fn(raw))
        lines.append(
            f"{indent}path = strings.Replace(path, {string_literal('{' + raw + '}')}, "
            f'fmt.Sprintf("%v", {go_name}), 1)'
        )
    return lines


def confine_output_path(output_dir: Path, rel_path: str) -> Path:
    """Resolve ``rel_path`` under ``output_dir``; reject empty, absolute, and ``..``."""
    if not isinstance(rel_path, str) or not rel_path or rel_path.endswith(("/", "\\")):
        raise ValueError("generated file path must stay under the output directory")
    raw = Path(rel_path)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError("generated file path must stay under the output directory")
    root = Path(output_dir).resolve()
    dest = (root / raw).resolve()
    if not dest.is_relative_to(root):
        raise ValueError("generated file path must stay under the output directory")
    return dest
