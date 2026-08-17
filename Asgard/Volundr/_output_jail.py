"""Jail generated artifact paths under an operator-chosen output directory."""

from __future__ import annotations

from pathlib import Path


def confine_output_file(target_dir: str | Path, rel_path: str) -> Path:
    """Resolve ``rel_path`` under ``target_dir``; reject empty, absolute, and ``..``."""
    if not isinstance(rel_path, str) or not rel_path or rel_path.endswith(("/", "\\")):
        raise ValueError("generated file path must stay under the output directory")
    raw = Path(rel_path)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError("generated file path must stay under the output directory")
    root = Path(target_dir).resolve()
    dest = (root / raw).resolve()
    if not dest.is_relative_to(root):
        raise ValueError("generated file path must stay under the output directory")
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest
