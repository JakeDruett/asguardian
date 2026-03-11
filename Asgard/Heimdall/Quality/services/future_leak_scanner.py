"""
Heimdall Future/Promise Leak Scanner Service

Detects futures, asyncio tasks, and threads that are created but never
properly resolved, awaited, or joined.

Detects:
- asyncio.create_task() / asyncio.ensure_future() assigned but never awaited
- executor.submit() result assigned but .result()/.exception()/.wait() never called
- concurrent.futures.Future created but never resolved
- threading.Thread started with .start() but .join() never called
"""

import ast
import os
import json
import fnmatch
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from Asgard.Heimdall.Quality.models.future_leak_models import (
    FutureLeak,
    FutureLeakConfig,
    FutureLeakReport,
    FutureLeakSeverity,
    FutureLeakType,
)


_REMEDIATION: Dict[str, str] = {
    "asyncio_task": (
        "Await the task or store a reference and await it later. "
        "Use asyncio.gather() or asyncio.shield() to manage task lifecycle."
    ),
    "executor_submit": (
        "Call .result(), .exception(), or .wait() on the returned future "
        "to check completion and handle exceptions."
    ),
    "concurrent_future": (
        "Call .result(), .exception(), or .cancel() on the future "
        "to manage its lifecycle and handle exceptions."
    ),
    "thread_not_joined": (
        "Call .join() on the thread after .start() to wait for it to complete "
        "and ensure proper resource cleanup."
    ),
}

_CONTEXT_DESCRIPTIONS: Dict[str, str] = {
    "asyncio_task": "asyncio task created but never awaited",
    "executor_submit": "executor future created but .result()/.exception()/.wait() never called",
    "concurrent_future": "concurrent.futures.Future created but never resolved",
    "thread_not_joined": "Thread started with .start() but .join() never called",
}


def _walk_without_nested_functions(node: ast.AST):
    """
    Walk AST nodes without descending into nested function or class definitions.

    This prevents cross-scope contamination when scanning a function body
    for future assignments and resolutions.
    """
    yield node
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        yield from _walk_without_nested_functions(child)


def _get_dotted_call_name(node: ast.Call) -> Optional[str]:
    """
    Extract the dotted name from a Call node's func attribute.

    Examples:
        asyncio.create_task(...)   -> 'asyncio.create_task'
        executor.submit(...)       -> 'executor.submit'
        self.pool.submit(...)      -> 'self.pool.submit'
    """
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        value = func.value
        if isinstance(value, ast.Name):
            return f"{value.id}.{func.attr}"
        if isinstance(value, ast.Attribute):
            inner = value.value
            if isinstance(inner, ast.Name):
                return f"{inner.id}.{value.attr}.{func.attr}"
    return None


def _detect_future_creation(node: ast.expr) -> Optional[str]:
    """
    Determine if an expression is a future-creating call.

    Returns the FutureLeakType string value, or None if not a future creator.
    """
    if not isinstance(node, ast.Call):
        return None

    name = _get_dotted_call_name(node)
    if name is None:
        return None

    if name in ("asyncio.create_task", "asyncio.ensure_future"):
        return FutureLeakType.ASYNCIO_TASK.value

    if name.endswith(".submit"):
        return FutureLeakType.EXECUTOR_SUBMIT.value

    if name == "concurrent.futures.Future":
        return FutureLeakType.CONCURRENT_FUTURE.value

    return None


def _detect_thread_creation(node: ast.expr) -> bool:
    """Check if an expression is a threading.Thread constructor call."""
    if not isinstance(node, ast.Call):
        return False
    name = _get_dotted_call_name(node)
    return name in ("threading.Thread", "Thread")


def _build_context_description(
    leak_type_val: str,
    current_class: Optional[str],
    current_function: Optional[str],
) -> str:
    """Build a human-readable context description for a leak."""
    base = _CONTEXT_DESCRIPTIONS.get(leak_type_val, "future/thread leak detected")
    if current_class and current_function:
        return f"{base} in '{current_class}.{current_function}'"
    elif current_function:
        return f"{base} in '{current_function}'"
    return base


def _scan_function_body_for_leaks(
    func_node: ast.AST,
    file_path: str,
    current_function: Optional[str],
    current_class: Optional[str],
) -> List[FutureLeak]:
    """
    Scan a single function body for future and thread leaks.

    Uses _walk_without_nested_functions to restrict the scan to this
    function's own scope, preventing cross-scope contamination.

    Returns a list of detected FutureLeak objects.
    """
    leaks: List[FutureLeak] = []

    # future_vars: var_name -> (line_no, leak_type_string)
    future_vars: Dict[str, Tuple[int, str]] = {}

    # thread_vars: var_name -> line_no (created threads)
    thread_vars: Dict[str, int] = {}

    # started_threads: var names that had .start() called
    started_threads: Set[str] = set()

    # resolved: var names that were awaited, .result()/.join() called on
    resolved: Set[str] = set()

    for child in _walk_without_nested_functions(func_node):
        # Detect future/thread assignments
        if isinstance(child, ast.Assign):
            rhs = child.value
            leak_type_val = _detect_future_creation(rhs)
            if leak_type_val:
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        future_vars[target.id] = (child.lineno, leak_type_val)
            elif _detect_thread_creation(rhs):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        thread_vars[target.id] = child.lineno

        # Detect await expressions: await task_var or await task_var.something()
        elif isinstance(child, ast.Await):
            awaited = child.value
            if isinstance(awaited, ast.Name):
                resolved.add(awaited.id)
            elif isinstance(awaited, ast.Call):
                if isinstance(awaited.func, ast.Attribute) and isinstance(awaited.func.value, ast.Name):
                    resolved.add(awaited.func.value.id)

        # Detect .result(), .exception(), .wait(), .cancel(), .join(), .start() method calls
        elif isinstance(child, ast.Call):
            if isinstance(child.func, ast.Attribute):
                attr = child.func.attr
                obj = child.func.value
                if isinstance(obj, ast.Name):
                    if attr in ("result", "exception", "wait", "cancel", "join"):
                        resolved.add(obj.id)
                    elif attr == "start":
                        started_threads.add(obj.id)

    # Report unresolved futures
    for var_name, (line_no, leak_type_val) in future_vars.items():
        if var_name not in resolved:
            context = _build_context_description(leak_type_val, current_class, current_function)
            leaks.append(FutureLeak(
                file_path=file_path,
                line_number=line_no,
                variable_name=var_name,
                leak_type=FutureLeakType(leak_type_val),
                severity=FutureLeakSeverity.MEDIUM,
                containing_function=current_function,
                containing_class=current_class,
                context_description=context,
                remediation=_REMEDIATION.get(leak_type_val, "Ensure the future is properly resolved."),
            ))

    # Report threads that were started but never joined
    for var_name, line_no in thread_vars.items():
        if var_name in started_threads and var_name not in resolved:
            context = _build_context_description(
                FutureLeakType.THREAD_NOT_JOINED.value, current_class, current_function
            )
            leaks.append(FutureLeak(
                file_path=file_path,
                line_number=line_no,
                variable_name=var_name,
                leak_type=FutureLeakType.THREAD_NOT_JOINED,
                severity=FutureLeakSeverity.MEDIUM,
                containing_function=current_function,
                containing_class=current_class,
                context_description=context,
                remediation=_REMEDIATION["thread_not_joined"],
            ))

    return leaks


class FutureLeakVisitor(ast.NodeVisitor):
    """
    AST visitor that detects future and thread leaks.

    For each function definition encountered, scans its body (without
    descending into nested functions) to find futures, tasks, and threads
    that are never properly resolved, awaited, or joined.
    """

    def __init__(self, file_path: str, source_lines: List[str]):
        """
        Initialize the future leak visitor.

        Args:
            file_path: Path to the file being analyzed
            source_lines: Source code lines (unused but kept for API consistency)
        """
        self.file_path = file_path
        self.source_lines = source_lines
        self.leaks: List[FutureLeak] = []
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition to track class context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit sync function definition."""
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self._visit_function(node)

    def _visit_function(self, node) -> None:
        """Common handler for function and async function definitions."""
        old_function = self.current_function
        self.current_function = node.name

        leaks = _scan_function_body_for_leaks(
            node,
            self.file_path,
            self.current_function,
            self.current_class,
        )
        self.leaks.extend(leaks)

        # Continue traversal to handle nested functions
        self.generic_visit(node)
        self.current_function = old_function


class FutureLeakScanner:
    """
    Scans Python files for future/promise leaks.

    Detects asyncio tasks, executor futures, concurrent.futures objects, and
    threads that are created but never properly resolved, awaited, or joined.

    Usage:
        scanner = FutureLeakScanner()
        report = scanner.analyze(Path("./src"))

        for leak in report.detected_leaks:
            print(f"{leak.location}: {leak.variable_name} - {leak.context_description}")
    """

    def __init__(self, config: Optional[FutureLeakConfig] = None):
        """
        Initialize the future leak scanner.

        Args:
            config: Configuration for scanning. If None, uses defaults.
        """
        self.config = config or FutureLeakConfig()

    def analyze(self, path: Path) -> FutureLeakReport:
        """
        Analyze a file or directory for future/promise leaks.

        Args:
            path: Path to file or directory to analyze

        Returns:
            FutureLeakReport with all detected violations

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = FutureLeakReport(scan_path=str(path))

        if path.is_file():
            leaks = self._analyze_file(path, path.parent)
            for leak in leaks:
                report.add_violation(leak)
            report.files_scanned = 1
        else:
            self._analyze_directory(path, report)

        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()

        file_violation_counts: Dict[str, int] = defaultdict(int)
        for leak in report.detected_leaks:
            file_violation_counts[leak.file_path] += 1

        report.most_problematic_files = sorted(
            file_violation_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return report

    def _analyze_file(self, file_path: Path, root_path: Path) -> List[FutureLeak]:
        """
        Analyze a single file for future/promise leaks.

        Args:
            file_path: Path to Python file
            root_path: Root path for calculating relative paths

        Returns:
            List of detected future leaks
        """
        try:
            source = file_path.read_text(encoding="utf-8")
            source_lines = source.splitlines()
            tree = ast.parse(source)

            visitor = FutureLeakVisitor(
                file_path=str(file_path.absolute()),
                source_lines=source_lines,
            )
            visitor.visit(tree)

            for leak in visitor.leaks:
                try:
                    leak.relative_path = str(file_path.relative_to(root_path))
                except ValueError:
                    leak.relative_path = file_path.name

            return visitor.leaks

        except SyntaxError:
            return []
        except Exception:
            return []

    def _analyze_directory(self, directory: Path, report: FutureLeakReport) -> None:
        """
        Analyze all Python files in a directory.

        Args:
            directory: Directory to analyze
            report: Report to add violations to
        """
        files_scanned = 0

        for root, dirs, files in os.walk(directory):
            root_path = Path(root)

            dirs[:] = [
                d for d in dirs
                if not any(self._matches_pattern(d, pattern) for pattern in self.config.exclude_patterns)
            ]

            for file in files:
                if not self._should_analyze_file(file):
                    continue

                if any(self._matches_pattern(file, pattern) for pattern in self.config.exclude_patterns):
                    continue

                if not self.config.include_tests:
                    if file.startswith("test_") or file.endswith("_test.py") or "tests" in str(root_path):
                        continue

                file_path = root_path / file
                leaks = self._analyze_file(file_path, directory)
                files_scanned += 1

                for leak in leaks:
                    report.add_violation(leak)

        report.files_scanned = files_scanned

    def _should_analyze_file(self, filename: str) -> bool:
        """Check if file should be analyzed based on extension."""
        if self.config.include_extensions:
            return any(filename.endswith(ext) for ext in self.config.include_extensions)
        return filename.endswith(".py")

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if name matches exclude pattern."""
        return fnmatch.fnmatch(name, pattern)

    def generate_report(self, report: FutureLeakReport, output_format: str = "text") -> str:
        """
        Generate a formatted future leak report.

        Args:
            report: FutureLeakReport to format
            output_format: Report format (text, json, markdown)

        Returns:
            Formatted report string

        Raises:
            ValueError: If output format is not supported
        """
        format_lower = output_format.lower()
        if format_lower == "json":
            return self._generate_json_report(report)
        elif format_lower in ("markdown", "md"):
            return self._generate_markdown_report(report)
        elif format_lower == "text":
            return self._generate_text_report(report)
        else:
            raise ValueError(f"Unsupported format: {output_format}. Use: text, json, markdown")

    def _generate_text_report(self, report: FutureLeakReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "FUTURE/PROMISE LEAK VIOLATIONS REPORT",
            "=" * 60,
            "",
            f"Scan Path: {report.scan_path}",
            f"Scan Time: {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {report.scan_duration_seconds:.2f} seconds",
            f"Files Scanned: {report.files_scanned}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Violations: {report.total_violations}",
            f"Compliant: {'Yes' if report.is_compliant else 'No'}",
            "",
        ]

        if report.has_violations:
            lines.extend(["By Type:"])
            for leak_type in FutureLeakType:
                count = report.violations_by_type.get(leak_type.value, 0)
                if count > 0:
                    lines.append(f"  {leak_type.value.replace('_', ' ').title()}: {count}")

            if report.most_problematic_files:
                lines.extend(["", "Most Problematic Files:", "-" * 40])
                for file_path, count in report.most_problematic_files[:5]:
                    filename = os.path.basename(file_path)
                    lines.append(f"  {filename}: {count} violations")

            lines.extend(["", "VIOLATIONS", "-" * 40])

            for leak in report.detected_leaks:
                filename = os.path.basename(leak.file_path)
                lines.append(f"  {filename}:{leak.line_number}")
                lines.append(f"    Variable:     {leak.variable_name}")
                lines.append(f"    Type:         {leak.leak_type}")
                lines.append(f"    Context:      {leak.context_description}")
                lines.append(f"    Remediation:  {leak.remediation}")
                lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self, report: FutureLeakReport) -> str:
        """Generate JSON report."""
        violations_data = []
        for v in report.detected_leaks:
            violations_data.append({
                "file_path": v.file_path,
                "relative_path": v.relative_path,
                "line_number": v.line_number,
                "variable_name": v.variable_name,
                "leak_type": v.leak_type if isinstance(v.leak_type, str) else v.leak_type.value,
                "severity": v.severity if isinstance(v.severity, str) else v.severity.value,
                "containing_function": v.containing_function,
                "containing_class": v.containing_class,
                "context_description": v.context_description,
                "remediation": v.remediation,
            })

        report_data = {
            "scan_info": {
                "scan_path": report.scan_path,
                "scanned_at": report.scanned_at.isoformat(),
                "duration_seconds": report.scan_duration_seconds,
                "files_scanned": report.files_scanned,
            },
            "summary": {
                "total_violations": report.total_violations,
                "is_compliant": report.is_compliant,
                "violations_by_type": report.violations_by_type,
                "violations_by_severity": report.violations_by_severity,
            },
            "violations": violations_data,
            "most_problematic_files": [
                {"file": file_path, "violation_count": count}
                for file_path, count in report.most_problematic_files
            ],
        }
        return json.dumps(report_data, indent=2)

    def _generate_markdown_report(self, report: FutureLeakReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Future/Promise Leak Violations Report",
            "",
            f"**Scan Path:** `{report.scan_path}`",
            f"**Generated:** {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {report.scan_duration_seconds:.2f} seconds",
            f"**Files Scanned:** {report.files_scanned}",
            "",
            "## Summary",
            "",
            f"**Total Violations:** {report.total_violations}",
            f"**Compliant:** {'Yes' if report.is_compliant else 'No'}",
            "",
        ]

        if report.has_violations:
            lines.extend([
                "### By Type",
                "",
                "| Type | Count |",
                "|------|-------|",
            ])
            for leak_type in FutureLeakType:
                count = report.violations_by_type.get(leak_type.value, 0)
                if count > 0:
                    lines.append(f"| {leak_type.value.replace('_', ' ').title()} | {count} |")

            if report.most_problematic_files:
                lines.extend(["", "## Most Problematic Files", ""])
                for file_path, count in report.most_problematic_files[:10]:
                    filename = os.path.basename(file_path)
                    lines.append(f"- `{filename}`: {count} violations")

            lines.extend(["", "## Violations", ""])

            for v in report.detected_leaks[:50]:
                filename = os.path.basename(v.file_path)
                lines.extend([
                    f"#### `{filename}:{v.line_number}` - `{v.variable_name}`",
                    "",
                    f"**Type:** {v.leak_type}",
                    "",
                    f"**Context:** {v.context_description}",
                    "",
                    f"**Remediation:** {v.remediation}",
                    "",
                ])

        return "\n".join(lines)
