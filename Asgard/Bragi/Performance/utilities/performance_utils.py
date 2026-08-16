"""
Heimdall Performance Utilities

Helper functions for performance analysis and profiling.
"""

import fnmatch
import re
from pathlib import Path
from typing import Dict, Generator, List, Optional, Set, Tuple

from Asgard.Bragi.Performance.utilities._performance_ast_utils import (
    calculate_complexity,
    extract_function_info,
    find_loops,
)


PERFORMANCE_SCAN_EXTENSIONS: Set[str] = {
    ".py",
    ".js", ".jsx", ".ts", ".tsx",
    ".java",
    ".go",
    ".rb",
    ".php",
    ".cs",
    ".cpp", ".c", ".h",
}

DEFAULT_EXCLUDE_DIRS: Set[str] = {
    "__pycache__",
    "node_modules",
    ".git",
    ".svn",
    ".hg",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    ".next",
    "out",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".cache",
    ".idea",
    ".vscode",
    "vendor",
    "target",
}


def _inode_key(path: Path) -> Optional[Tuple[int, int]]:
    """Return (device, inode) for *path* without following a symlink."""
    try:
        stat_result = path.lstat()
    except OSError:
        return None
    return (stat_result.st_dev, stat_result.st_ino)


def _resolved_is_relative_to(path: Path, root: Path) -> bool:
    """Return True if path.resolve() is inside an already-resolved *root*."""
    try:
        return path.resolve().is_relative_to(root)
    except OSError:
        return False


def is_excluded_path(path: Path, exclude_patterns: List[str]) -> bool:
    """
    Check if a path should be excluded from scanning.

    Args:
        path: Path to check
        exclude_patterns: List of glob patterns to exclude

    Returns:
        True if the path should be excluded
    """
    path_str = str(path)
    path_name = path.name

    if path_name.startswith("."):
        return True

    for pattern in exclude_patterns:
        if fnmatch.fnmatch(path_name, pattern):
            return True
        if fnmatch.fnmatch(path_str, f"*/{pattern}/*"):
            return True
        if fnmatch.fnmatch(path_str, f"*/{pattern}"):
            return True

    if path.is_dir() and path_name in DEFAULT_EXCLUDE_DIRS:
        return True

    return False


def scan_directory_for_performance(
    root_path: Path,
    exclude_patterns: Optional[List[str]] = None,
    include_extensions: Optional[List[str]] = None,
) -> Generator[Path, None, None]:
    """
    Recursively scan a directory for files to analyze for performance issues.

    Directory and file symlinks are skipped (not followed). Recursion tracks
    directory inodes so bind-mount or hard-link cycles terminate. Only paths
    whose resolve() is inside root_path.resolve() are yielded.

    Args:
        root_path: Root directory to scan
        exclude_patterns: Additional patterns to exclude
        include_extensions: File extensions to include (None = use defaults)

    Yields:
        Paths to files that should be scanned
    """
    if exclude_patterns is None:
        exclude_patterns = []

    all_exclusions = list(DEFAULT_EXCLUDE_DIRS) + exclude_patterns

    if include_extensions:
        valid_extensions = {e if e.startswith(".") else f".{e}" for e in include_extensions}
    else:
        valid_extensions = PERFORMANCE_SCAN_EXTENSIONS

    try:
        root_resolved = root_path.resolve()
    except OSError:
        return

    visited: Set[Tuple[int, int]] = set()
    root_inode = _inode_key(root_resolved)
    if root_inode is not None:
        visited.add(root_inode)

    def _scan_recursive(current_path: Path) -> Generator[Path, None, None]:
        try:
            for entry in current_path.iterdir():
                if entry.is_symlink():
                    continue
                if is_excluded_path(entry, all_exclusions):
                    continue
                if not _resolved_is_relative_to(entry, root_resolved):
                    continue

                if entry.is_dir():
                    inode = _inode_key(entry)
                    if inode is not None:
                        if inode in visited:
                            continue
                        visited.add(inode)
                    yield from _scan_recursive(entry)
                elif entry.is_file():
                    ext = entry.suffix.lower()
                    if ext in valid_extensions:
                        yield entry

        except OSError:
            pass

    yield from _scan_recursive(root_path)


def find_line_column(content: str, match_start: int) -> Tuple[int, int]:
    """
    Convert a character offset to line and column numbers.

    Args:
        content: Full file content
        match_start: Character offset of the match

    Returns:
        Tuple of (line_number, column_number), both 1-indexed
    """
    lines = content[:match_start].split("\n")
    line_number = len(lines)
    column_number = len(lines[-1]) + 1 if lines else 1
    return line_number, column_number


def extract_code_snippet(
    lines: List[str],
    line_number: int,
    context_lines: int = 2
) -> str:
    """
    Extract a code snippet around a specific line.

    Args:
        lines: List of file lines
        line_number: Line number (1-indexed)
        context_lines: Number of context lines before and after

    Returns:
        Code snippet with context
    """
    if not lines or line_number < 1:
        return ""

    start_idx = max(0, line_number - 1 - context_lines)
    end_idx = min(len(lines), line_number + context_lines)

    snippet_lines = []
    for i in range(start_idx, end_idx):
        line_num = i + 1
        marker = ">>> " if line_num == line_number else "    "
        snippet_lines.append(f"{marker}{line_num}: {lines[i].rstrip()}")

    return "\n".join(snippet_lines)


__all__ = [
    "PERFORMANCE_SCAN_EXTENSIONS",
    "DEFAULT_EXCLUDE_DIRS",
    "is_excluded_path",
    "scan_directory_for_performance",
    "find_line_column",
    "extract_code_snippet",
    "calculate_complexity",
    "extract_function_info",
    "find_loops",
]
