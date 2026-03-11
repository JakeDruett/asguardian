"""
Heimdall Error Handling Coverage Scanner Service

Detects functions and calls that are missing appropriate error handling,
which can cause silent failures, unhandled crashes, or hard-to-debug issues.

Detects:
- Thread target functions (threading.Thread(target=...)) that do not have
  a top-level try/except block in their body
- External calls (requests, urllib, subprocess, aiohttp) not inside a try/except
- Async functions that await external call patterns without error handling
"""

import ast
import fnmatch
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from Asgard.Heimdall.Quality.models.error_handling_models import (
    ErrorHandlingConfig,
    ErrorHandlingReport,
    ErrorHandlingSeverity,
    ErrorHandlingType,
    ErrorHandlingViolation,
)


# Module.method patterns that are external calls requiring error handling
EXTERNAL_CALL_PATTERNS: Set[tuple] = {
    # requests
    ("requests", "get"), ("requests", "post"), ("requests", "put"),
    ("requests", "delete"), ("requests", "patch"), ("requests", "head"),
    ("requests", "options"), ("requests", "request"),
    # urllib
    ("urllib", "urlopen"), ("urllib.request", "urlopen"),
    # subprocess
    ("subprocess", "run"), ("subprocess", "call"), ("subprocess", "check_call"),
    ("subprocess", "check_output"), ("subprocess", "Popen"),
    # aiohttp
    ("aiohttp", "get"), ("aiohttp", "post"), ("aiohttp", "request"),
    # httpx
    ("httpx", "get"), ("httpx", "post"), ("httpx", "put"),
    ("httpx", "delete"), ("httpx", "request"),
}

# Module names whose any attribute call counts as external
EXTERNAL_MODULES: Set[str] = {"requests", "urllib", "subprocess", "aiohttp", "httpx"}

# Session/client method names that are external calls
EXTERNAL_SESSION_METHODS: Set[str] = {
    "get", "post", "put", "delete", "patch", "head", "options", "request",
    "execute", "run", "call",
}


def _is_external_call(node: ast.Call) -> bool:
    """Return True if this call is to a known external API."""
    if not isinstance(node.func, ast.Attribute):
        return False

    attr = node.func.attr
    # Check direct module calls: requests.get(), subprocess.run()
    if isinstance(node.func.value, ast.Name):
        module = node.func.value.id
        if module in EXTERNAL_MODULES:
            return True
        if (module, attr) in EXTERNAL_CALL_PATTERNS:
            return True

    return False


def _get_call_repr(node: ast.Call) -> str:
    """Get a readable representation of a call expression."""
    if isinstance(node.func, ast.Attribute):
        if isinstance(node.func.value, ast.Name):
            return f"{node.func.value.id}.{node.func.attr}()"
        return f"...{node.func.attr}()"
    if isinstance(node.func, ast.Name):
        return f"{node.func.id}()"
    return "unknown_call()"


def _function_has_top_level_try_except(func_node: ast.AST) -> bool:
    """
    Return True if the function body has a try/except as its outermost statement.

    We look at the direct body of the function (not nested functions).
    A try/except at the top level of the function body is considered
    adequate exception handling.
    """
    body = getattr(func_node, 'body', [])
    for stmt in body:
        if isinstance(stmt, (ast.Try,)):
            # Has at least one handler (except clause)
            if getattr(stmt, 'handlers', []):
                return True
    return False


def _node_is_inside_try_except(node: ast.AST, func_body: List[ast.stmt]) -> bool:
    """
    Return True if the given node is inside any try/except in the function body.

    Uses a simple walk of the function body to check if node's line is
    covered by a try block with at least one handler.
    """
    node_line = getattr(node, 'lineno', -1)
    if node_line < 0:
        return False

    for stmt in ast.walk(ast.Module(body=func_body, type_ignores=[])):
        if not isinstance(stmt, ast.Try):
            continue
        if not getattr(stmt, 'handlers', []):
            continue
        # Check if node line falls within the try body
        try_start = getattr(stmt, 'lineno', -1)
        # End of try body is approximated by the start of the first handler
        if stmt.handlers:
            try_end = getattr(stmt.handlers[0], 'lineno', try_start + 9999)
        else:
            try_end = try_start + 9999

        if try_start <= node_line < try_end:
            return True

    return False


class ThreadTargetCollector(ast.NodeVisitor):
    """
    First-pass visitor that collects all function names referenced as
    threading.Thread(target=...) targets.
    """

    def __init__(self):
        self.thread_targets: Set[str] = set()

    def visit_Call(self, node: ast.Call) -> None:
        """Detect threading.Thread(target=func_name) patterns."""
        is_thread_call = False

        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "Thread":
                if isinstance(node.func.value, ast.Name) and node.func.value.id == "threading":
                    is_thread_call = True
        elif isinstance(node.func, ast.Name):
            if node.func.id == "Thread":
                is_thread_call = True

        if is_thread_call:
            # Look for target= keyword argument
            for kw in node.keywords:
                if kw.arg == "target":
                    if isinstance(kw.value, ast.Name):
                        self.thread_targets.add(kw.value.id)
                    elif isinstance(kw.value, ast.Attribute):
                        self.thread_targets.add(kw.value.attr)

        self.generic_visit(node)


class ErrorHandlingVisitor(ast.NodeVisitor):
    """
    AST visitor that detects missing error handling around external calls
    and thread target functions.
    """

    def __init__(
        self,
        file_path: str,
        source_lines: List[str],
        thread_targets: Set[str],
    ):
        """
        Initialize the error handling visitor.

        Args:
            file_path: Path to the file being analyzed
            source_lines: Source code lines for extracting code text
            thread_targets: Set of function names used as threading.Thread targets
        """
        self.file_path = file_path
        self.source_lines = source_lines
        self.thread_targets = thread_targets
        self.violations: List[ErrorHandlingViolation] = []
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        # Stack to track whether we are inside a try/except block
        self.in_try_except: int = 0
        self.is_async_function: bool = False

    def _get_code_snippet(self, node: ast.AST) -> str:
        """Extract the code snippet from source."""
        if hasattr(node, 'lineno') and node.lineno <= len(self.source_lines):
            return self.source_lines[node.lineno - 1].strip()
        return ""

    def _record_violation(
        self,
        node: ast.AST,
        handling_type: ErrorHandlingType,
        severity: ErrorHandlingSeverity,
        function_name: Optional[str],
        call_expression: Optional[str],
        context_description: str,
        remediation: str,
    ) -> None:
        """Record an error handling violation."""
        code_snippet = self._get_code_snippet(node)

        self.violations.append(ErrorHandlingViolation(
            file_path=self.file_path,
            line_number=getattr(node, 'lineno', 0),
            column=getattr(node, 'col_offset', 0),
            code_snippet=code_snippet,
            function_name=function_name,
            call_expression=call_expression,
            handling_type=handling_type,
            severity=severity,
            containing_function=self.current_function,
            containing_class=self.current_class,
            context_description=context_description,
            remediation=remediation,
        ))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition to track class context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self._visit_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self._visit_function(node, is_async=True)

    def _visit_function(self, node, is_async: bool) -> None:
        """Common handler for function and async function definitions."""
        old_function = self.current_function
        old_is_async = self.is_async_function
        self.current_function = node.name
        self.is_async_function = is_async

        # Check if this function is a thread target without top-level try/except
        if node.name in self.thread_targets:
            if not _function_has_top_level_try_except(node):
                context_parts = []
                if self.current_class:
                    context_parts.append(f"class {self.current_class}")
                context = f"in {', '.join(context_parts)}" if context_parts else "at module level"

                self._record_violation(
                    node,
                    handling_type=ErrorHandlingType.THREAD_TARGET_NO_EXCEPTION_HANDLING,
                    severity=ErrorHandlingSeverity.HIGH,
                    function_name=node.name,
                    call_expression=None,
                    context_description=(
                        f"Thread target function '{node.name}' has no top-level try/except {context}. "
                        "Unhandled exceptions in threads terminate silently."
                    ),
                    remediation=(
                        f"Wrap the body of '{node.name}' in a try/except block to catch and handle "
                        "all exceptions, preventing silent thread failure."
                    ),
                )

        self.generic_visit(node)

        self.current_function = old_function
        self.is_async_function = old_is_async

    def visit_Try(self, node: ast.Try) -> None:
        """Track entry into try/except blocks."""
        if node.handlers:
            self.in_try_except += 1
            self.generic_visit(node)
            self.in_try_except -= 1
        else:
            self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Detect external calls not inside try/except."""
        if self.in_try_except == 0 and _is_external_call(node):
            call_repr = _get_call_repr(node)
            context_parts = []
            if self.current_class:
                context_parts.append(f"class {self.current_class}")
            if self.current_function:
                context_parts.append(f"function {self.current_function}")
            context = f"in {', '.join(context_parts)}" if context_parts else "at module level"

            if self.is_async_function:
                handling_type = ErrorHandlingType.ASYNC_EXTERNAL_NO_HANDLING
                description = (
                    f"Async external call '{call_repr}' not protected by try/except {context}"
                )
            else:
                handling_type = ErrorHandlingType.UNPROTECTED_EXTERNAL_CALL
                description = (
                    f"External call '{call_repr}' not protected by try/except {context}"
                )

            self._record_violation(
                node,
                handling_type=handling_type,
                severity=ErrorHandlingSeverity.MEDIUM,
                function_name=self.current_function,
                call_expression=call_repr,
                context_description=description,
                remediation=(
                    f"Wrap '{call_repr}' in a try/except block to handle network errors, "
                    "timeouts, and other potential exceptions."
                ),
            )

        self.generic_visit(node)


class ErrorHandlingScanner:
    """
    Scans Python files for missing error handling around external calls
    and thread target functions.

    Usage:
        scanner = ErrorHandlingScanner()
        report = scanner.analyze(Path("./src"))

        for violation in report.detected_violations:
            print(f"{violation.location}: {violation.context_description}")
    """

    def __init__(self, config: Optional[ErrorHandlingConfig] = None):
        """
        Initialize error handling scanner.

        Args:
            config: Configuration for scanning. If None, uses defaults.
        """
        self.config = config or ErrorHandlingConfig()

    def analyze(self, path: Path) -> ErrorHandlingReport:
        """
        Analyze a file or directory for error handling violations.

        Args:
            path: Path to file or directory to analyze

        Returns:
            ErrorHandlingReport with all detected violations

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = ErrorHandlingReport(scan_path=str(path))

        if path.is_file():
            violations = self._analyze_file(path, path.parent)
            for violation in violations:
                report.add_violation(violation)
            report.files_scanned = 1
        else:
            self._analyze_directory(path, report)

        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()

        file_violation_counts: Dict[str, int] = defaultdict(int)
        for violation in report.detected_violations:
            file_violation_counts[violation.file_path] += 1

        report.most_problematic_files = sorted(
            file_violation_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return report

    def _analyze_file(
        self, file_path: Path, root_path: Path
    ) -> List[ErrorHandlingViolation]:
        """
        Analyze a single Python file for error handling violations.

        Args:
            file_path: Path to Python file
            root_path: Root path for calculating relative paths

        Returns:
            List of detected violations
        """
        try:
            source = file_path.read_text(encoding="utf-8")
            source_lines = source.splitlines()
            tree = ast.parse(source)

            # First pass: collect thread targets
            target_collector = ThreadTargetCollector()
            target_collector.visit(tree)

            # Second pass: check error handling
            visitor = ErrorHandlingVisitor(
                file_path=str(file_path.absolute()),
                source_lines=source_lines,
                thread_targets=target_collector.thread_targets,
            )
            visitor.visit(tree)

            for violation in visitor.violations:
                try:
                    violation.relative_path = str(file_path.relative_to(root_path))
                except ValueError:
                    violation.relative_path = file_path.name

            filtered = [
                v for v in visitor.violations
                if self._severity_level(v.severity) >= self._severity_level(self.config.severity_filter)
            ]

            return filtered

        except SyntaxError:
            return []
        except Exception:
            return []

    def _analyze_directory(self, directory: Path, report: ErrorHandlingReport) -> None:
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
                if not any(self._matches_pattern(d, p) for p in self.config.exclude_patterns)
            ]

            for file in files:
                if not self._should_analyze_file(file):
                    continue

                if any(self._matches_pattern(file, p) for p in self.config.exclude_patterns):
                    continue

                if not self.config.include_tests:
                    if file.startswith("test_") or file.endswith("_test.py") or "tests" in str(root_path):
                        continue

                file_path = root_path / file
                violations = self._analyze_file(file_path, directory)
                files_scanned += 1

                for violation in violations:
                    report.add_violation(violation)

        report.files_scanned = files_scanned

    def _should_analyze_file(self, filename: str) -> bool:
        """Check if file should be analyzed based on extension."""
        if self.config.include_extensions:
            return any(filename.endswith(ext) for ext in self.config.include_extensions)
        return filename.endswith(".py")

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if name matches exclude pattern."""
        return fnmatch.fnmatch(name, pattern)

    def _severity_level(self, severity) -> int:
        """Convert severity to numeric level for comparison."""
        if isinstance(severity, str):
            severity = ErrorHandlingSeverity(severity)
        levels = {
            ErrorHandlingSeverity.LOW: 1,
            ErrorHandlingSeverity.MEDIUM: 2,
            ErrorHandlingSeverity.HIGH: 3,
        }
        return levels.get(severity, 1)

    def generate_report(self, report: ErrorHandlingReport, output_format: str = "text") -> str:
        """
        Generate formatted error handling report.

        Args:
            report: ErrorHandlingReport to format
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

    def _generate_text_report(self, report: ErrorHandlingReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 70,
            "ERROR HANDLING COVERAGE VIOLATIONS REPORT",
            "=" * 70,
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
            lines.append("By Severity:")
            for severity in [
                ErrorHandlingSeverity.HIGH,
                ErrorHandlingSeverity.MEDIUM,
                ErrorHandlingSeverity.LOW,
            ]:
                count = report.violations_by_severity.get(severity.value, 0)
                if count > 0:
                    lines.append(f"  {severity.value.upper()}: {count}")

            lines.extend(["", "By Type:"])
            for handling_type in ErrorHandlingType:
                count = report.violations_by_type.get(handling_type.value, 0)
                if count > 0:
                    lines.append(f"  {handling_type.value.replace('_', ' ').title()}: {count}")

            if report.most_problematic_files:
                lines.extend(["", "Most Problematic Files:", "-" * 40])
                for file_path, count in report.most_problematic_files[:5]:
                    filename = os.path.basename(file_path)
                    lines.append(f"  {filename}: {count} violations")

            lines.extend(["", "VIOLATIONS", "-" * 40])

            for severity in [
                ErrorHandlingSeverity.HIGH,
                ErrorHandlingSeverity.MEDIUM,
                ErrorHandlingSeverity.LOW,
            ]:
                severity_violations = report.get_violations_by_severity(severity)
                if severity_violations:
                    lines.extend(["", f"[{severity.value.upper()}]"])
                    for v in severity_violations:
                        lines.append(f"  {v.location}")
                        lines.append(f"    Code: {v.code_snippet}")
                        if v.function_name:
                            lines.append(f"    Function: {v.function_name}")
                        if v.call_expression:
                            lines.append(f"    Call: {v.call_expression}")
                        lines.append(f"    Context: {v.context_description}")
                        lines.append(f"    Fix: {v.remediation}")
                        lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def _generate_json_report(self, report: ErrorHandlingReport) -> str:
        """Generate JSON report."""
        violations_data = []
        for v in report.detected_violations:
            violations_data.append({
                "file_path": v.file_path,
                "relative_path": v.relative_path,
                "line_number": v.line_number,
                "column": v.column,
                "code_snippet": v.code_snippet,
                "function_name": v.function_name,
                "call_expression": v.call_expression,
                "handling_type": v.handling_type if isinstance(v.handling_type, str) else v.handling_type.value,
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
                "violations_by_severity": report.violations_by_severity,
                "violations_by_type": report.violations_by_type,
            },
            "violations": violations_data,
            "most_problematic_files": [
                {"file": fp, "violation_count": count}
                for fp, count in report.most_problematic_files
            ],
        }

        return json.dumps(report_data, indent=2)

    def _generate_markdown_report(self, report: ErrorHandlingReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Error Handling Coverage Violations Report",
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
                "### By Severity",
                "",
                "| Severity | Count |",
                "|----------|-------|",
            ])
            for severity in [
                ErrorHandlingSeverity.HIGH,
                ErrorHandlingSeverity.MEDIUM,
                ErrorHandlingSeverity.LOW,
            ]:
                count = report.violations_by_severity.get(severity.value, 0)
                lines.append(f"| {severity.value.title()} | {count} |")

            lines.extend([
                "",
                "### By Type",
                "",
                "| Type | Count |",
                "|------|-------|",
            ])
            for handling_type in ErrorHandlingType:
                count = report.violations_by_type.get(handling_type.value, 0)
                if count > 0:
                    lines.append(f"| {handling_type.value.replace('_', ' ').title()} | {count} |")

            if report.most_problematic_files:
                lines.extend(["", "## Most Problematic Files", ""])
                for file_path, count in report.most_problematic_files[:10]:
                    filename = os.path.basename(file_path)
                    lines.append(f"- `{filename}`: {count} violations")

            lines.extend(["", "## Violations", ""])

            for severity in [
                ErrorHandlingSeverity.HIGH,
                ErrorHandlingSeverity.MEDIUM,
                ErrorHandlingSeverity.LOW,
            ]:
                severity_violations = report.get_violations_by_severity(severity)
                if severity_violations:
                    lines.extend([f"### {severity.value.title()} Severity", ""])
                    for v in severity_violations[:20]:
                        filename = os.path.basename(v.file_path)
                        lines.extend([
                            f"#### `{filename}:{v.line_number}`",
                            "",
                            f"**Code:** `{v.code_snippet}`",
                            "",
                        ])
                        if v.function_name:
                            lines.append(f"**Function:** `{v.function_name}`")
                        if v.call_expression:
                            lines.append(f"**Call:** `{v.call_expression}`")
                        lines.extend([
                            "",
                            f"**Context:** {v.context_description}",
                            "",
                            f"**Remediation:** {v.remediation}",
                            "",
                        ])

        return "\n".join(lines)
