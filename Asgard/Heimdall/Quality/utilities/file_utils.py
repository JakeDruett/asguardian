"""
Heimdall Quality File Utilities

Helper functions for file discovery, path filtering, and line counting.
"""

import fnmatch
from pathlib import Path
from typing import Generator, List, Optional, Set


# Common code file extensions to analyze
CODE_EXTENSIONS: Set[str] = {
    # Python
    ".py",
    # JavaScript/TypeScript
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    # Web
    ".html", ".css", ".scss", ".sass", ".less",
    # Data/Config
    ".json", ".yaml", ".yml", ".toml",
    # Shell
    ".sh", ".bash", ".zsh", ".ps1",
    # Java/Kotlin
    ".java", ".kt", ".kts",
    # C/C++
    ".c", ".h", ".cpp", ".hpp", ".cc",
    # C#
    ".cs",
    # Go
    ".go",
    # Rust
    ".rs",
    # Ruby
    ".rb",
    # PHP
    ".php",
    # Swift
    ".swift",
    # SQL
    ".sql",
    # Lua
    ".lua",
    # R
    ".r", ".R",
    # Dart
    ".dart",
    # Vue/Svelte
    ".vue", ".svelte",
}

# Directories to always exclude
DEFAULT_EXCLUDE_DIRS: Set[str] = {
    "__pycache__",
    "node_modules",
    ".git",
    ".svn",
    ".hg",
    ".venv",
    "venv",
    "env",
    ".env",
    "build",
    "dist",
    ".next",
    "out",
    "coverage",
    ".pytest_cache",
    ".mypy_cache",
    ".tox",
    "eggs",
    ".eggs",
    "*.egg-info",
    ".cache",
    ".idea",
    ".vscode",
    "vendor",
    "target",
    "bin",
    "obj",
    ".gradle",
    ".terraform",
}

# File patterns to always exclude
DEFAULT_EXCLUDE_FILES: Set[str] = {
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "*.generated.*",
    "*.auto.*",
    "*.bundle.js",
    "*.chunk.js",
}


def is_excluded_path(path: Path, exclude_patterns: List[str]) -> bool:
    """
    Check if a path should be excluded based on patterns.

    Args:
        path: The path to check
        exclude_patterns: List of glob patterns to exclude

    Returns:
        True if the path should be excluded
    """
    path_str = str(path)
    path_name = path.name

    # Check if path starts with a dot (hidden files/dirs)
    if path_name.startswith("."):
        return True

    # Check against exclude patterns
    for pattern in exclude_patterns:
        if fnmatch.fnmatch(path_name, pattern):
            return True
        if fnmatch.fnmatch(path_str, f"*/{pattern}/*"):
            return True
        if fnmatch.fnmatch(path_str, f"*/{pattern}"):
            return True

    # Check against default exclusions
    if path.is_dir():
        if path_name in DEFAULT_EXCLUDE_DIRS:
            return True
        for pattern in DEFAULT_EXCLUDE_DIRS:
            if fnmatch.fnmatch(path_name, pattern):
                return True
    else:
        for pattern in DEFAULT_EXCLUDE_FILES:
            if fnmatch.fnmatch(path_name, pattern):
                return True

    return False


def get_file_extension(path: Path) -> str:
    """
    Get the file extension including the dot.

    Args:
        path: The file path

    Returns:
        The file extension (e.g., ".py")
    """
    return path.suffix.lower()


def is_code_file(path: Path, include_extensions: Optional[List[str]] = None) -> bool:
    """
    Check if a file is a code file that should be analyzed.

    Args:
        path: The file path
        include_extensions: Optional list of extensions to include (overrides defaults)

    Returns:
        True if the file should be analyzed
    """
    if not path.is_file():
        return False

    ext = get_file_extension(path)

    if include_extensions:
        # Normalize extensions to include dot
        normalized = {e if e.startswith(".") else f".{e}" for e in include_extensions}
        return ext in normalized

    return ext in CODE_EXTENSIONS


def count_lines(file_path: Path) -> int:
    """
    Count the number of lines in a file.

    Args:
        file_path: Path to the file

    Returns:
        Number of lines in the file

    Raises:
        IOError: If the file cannot be read
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return sum(1 for _ in f)
    except (IOError, OSError) as e:
        raise IOError(f"Failed to read file {file_path}: {e}")


def scan_directory(
    root_path: Path,
    exclude_patterns: Optional[List[str]] = None,
    include_extensions: Optional[List[str]] = None,
) -> Generator[Path, None, None]:
    """
    Recursively scan a directory for code files.

    Args:
        root_path: The root directory to scan
        exclude_patterns: Additional patterns to exclude
        include_extensions: File extensions to include (None = use defaults)

    Yields:
        Paths to code files that should be analyzed
    """
    if exclude_patterns is None:
        exclude_patterns = []

    # Combine with default exclusions
    all_exclusions = list(DEFAULT_EXCLUDE_DIRS) + exclude_patterns

    def _scan_recursive(current_path: Path) -> Generator[Path, None, None]:
        try:
            for entry in current_path.iterdir():
                # Skip excluded paths
                if is_excluded_path(entry, all_exclusions):
                    continue

                if entry.is_dir():
                    # Recurse into subdirectories
                    yield from _scan_recursive(entry)
                elif is_code_file(entry, include_extensions):
                    yield entry
        except PermissionError:
            # Skip directories we don't have permission to read
            pass

    yield from _scan_recursive(root_path)
