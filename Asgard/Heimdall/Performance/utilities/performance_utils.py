"""
Heimdall Performance Utilities

Helper functions for performance analysis and profiling.
"""

import ast
import fnmatch
import re
from pathlib import Path
from typing import Dict, Generator, List, Optional, Set, Tuple


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

    def _scan_recursive(current_path: Path) -> Generator[Path, None, None]:
        try:
            for entry in current_path.iterdir():
                if is_excluded_path(entry, all_exclusions):
                    continue

                if entry.is_dir():
                    yield from _scan_recursive(entry)
                elif entry.is_file():
                    ext = entry.suffix.lower()
                    if ext in valid_extensions:
                        yield entry

        except PermissionError:
            pass

    yield from _scan_recursive(root_path)


def calculate_complexity(source_code: str) -> Dict[str, int]:
    """
    Calculate cyclomatic complexity for functions in Python code.

    Args:
        source_code: Python source code

    Returns:
        Dictionary mapping function names to complexity scores
    """
    complexity_scores: Dict[str, int] = {}

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return complexity_scores

    class ComplexityVisitor(ast.NodeVisitor):
        def __init__(self):
            self.current_function = None
            self.complexity = 1

        def visit_FunctionDef(self, node):
            old_function = self.current_function
            old_complexity = self.complexity

            self.current_function = node.name
            self.complexity = 1

            self.generic_visit(node)

            complexity_scores[self.current_function] = self.complexity

            self.current_function = old_function
            self.complexity = old_complexity

        def visit_AsyncFunctionDef(self, node):
            self.visit_FunctionDef(node)

        def visit_If(self, node):
            if self.current_function:
                self.complexity += 1
            self.generic_visit(node)

        def visit_For(self, node):
            if self.current_function:
                self.complexity += 1
            self.generic_visit(node)

        def visit_While(self, node):
            if self.current_function:
                self.complexity += 1
            self.generic_visit(node)

        def visit_ExceptHandler(self, node):
            if self.current_function:
                self.complexity += 1
            self.generic_visit(node)

        def visit_BoolOp(self, node):
            if self.current_function:
                self.complexity += len(node.values) - 1
            self.generic_visit(node)

        def visit_comprehension(self, node):
            if self.current_function:
                self.complexity += 1
            self.generic_visit(node)

        def visit_Assert(self, node):
            if self.current_function:
                self.complexity += 1
            self.generic_visit(node)

    visitor = ComplexityVisitor()
    visitor.visit(tree)

    return complexity_scores


def extract_function_info(source_code: str) -> List[Dict]:
    """
    Extract information about functions in Python code.

    Args:
        source_code: Python source code

    Returns:
        List of dictionaries with function information
    """
    functions: List[Dict] = []

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return functions

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_info = {
                "name": node.name,
                "line_start": node.lineno,
                "line_end": node.end_lineno if hasattr(node, "end_lineno") else node.lineno,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "num_args": len(node.args.args),
                "has_return": any(isinstance(child, ast.Return) for child in ast.walk(node)),
                "decorators": [_get_decorator_name(d) for d in node.decorator_list],
            }
            functions.append(func_info)

    return functions


def _get_decorator_name(decorator: ast.expr) -> str:
    """Extract the name of a decorator."""
    if isinstance(decorator, ast.Name):
        return decorator.id
    elif isinstance(decorator, ast.Attribute):
        return decorator.attr
    elif isinstance(decorator, ast.Call):
        if isinstance(decorator.func, ast.Name):
            return decorator.func.id
        elif isinstance(decorator.func, ast.Attribute):
            return decorator.func.attr
    return "unknown"


def find_loops(source_code: str) -> List[Dict]:
    """
    Find all loops in Python code.

    Args:
        source_code: Python source code

    Returns:
        List of dictionaries with loop information
    """
    loops: List[Dict] = []

    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return loops

    for node in ast.walk(tree):
        if isinstance(node, ast.For):
            loop_info = {
                "type": "for",
                "line_number": node.lineno,
                "is_nested": _is_nested_loop(tree, node),
                "has_break": any(isinstance(child, ast.Break) for child in ast.walk(node)),
                "has_continue": any(isinstance(child, ast.Continue) for child in ast.walk(node)),
            }
            loops.append(loop_info)

        elif isinstance(node, ast.While):
            loop_info = {
                "type": "while",
                "line_number": node.lineno,
                "is_nested": _is_nested_loop(tree, node),
                "has_break": any(isinstance(child, ast.Break) for child in ast.walk(node)),
                "has_continue": any(isinstance(child, ast.Continue) for child in ast.walk(node)),
            }
            loops.append(loop_info)

        elif isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            loop_info = {
                "type": "comprehension",
                "line_number": node.lineno,
                "is_nested": len(node.generators) > 1,
            }
            loops.append(loop_info)

    return loops


def _is_nested_loop(tree: ast.AST, target_node: ast.AST) -> bool:
    """Check if a loop is nested inside another loop."""
    class NestingChecker(ast.NodeVisitor):
        def __init__(self):
            self.found = False
            self.in_loop = False

        def visit_For(self, node):
            if node is target_node:
                self.found = self.in_loop
                return

            old_in_loop = self.in_loop
            self.in_loop = True
            self.generic_visit(node)
            self.in_loop = old_in_loop

        def visit_While(self, node):
            if node is target_node:
                self.found = self.in_loop
                return

            old_in_loop = self.in_loop
            self.in_loop = True
            self.generic_visit(node)
            self.in_loop = old_in_loop

    checker = NestingChecker()
    checker.visit(tree)
    return checker.found


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
