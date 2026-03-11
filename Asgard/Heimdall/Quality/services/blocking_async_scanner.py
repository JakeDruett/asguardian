"""
Heimdall Blocking Call in Async Context Scanner Service

Detects blocking operations used inside async functions, which stall
the event loop and degrade application throughput.

Detects:
- time.sleep() inside async def
- requests.get/post/put/delete/patch/head() inside async def
- open() (file I/O) inside async def without aiofiles
- subprocess.run/call/check_output/check_call() inside async def
- urllib.request.urlopen() inside async def
"""

import ast
import os
import json
import fnmatch
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

from Asgard.Heimdall.Quality.models.blocking_async_models import (
    BlockingAsyncConfig,
    BlockingAsyncReport,
    BlockingAsyncSeverity,
    BlockingCall,
    BlockingCallType,
)


_BLOCKING_REMEDIATION: Dict[str, str] = {
    "time_sleep": (
        "Replace time.sleep() with 'await asyncio.sleep()' to yield "
        "control back to the event loop."
    ),
    "requests_http": (
        "Replace the requests library with an async HTTP client such as "
        "aiohttp or httpx (with async transport) inside async functions."
    ),
    "open_file_io": (
        "Replace open() with 'async with aiofiles.open()' to perform "
        "non-blocking file I/O. Install aiofiles via pip."
    ),
    "subprocess_call": (
        "Replace subprocess calls with 'await asyncio.create_subprocess_exec()' "
        "or 'await asyncio.create_subprocess_shell()' for non-blocking execution."
    ),
    "urllib_call": (
        "Replace urllib.request.urlopen() with an async HTTP client such as "
        "aiohttp or httpx (with async transport) inside async functions."
    ),
}

_CONTEXT_DESCRIPTIONS: Dict[str, str] = {
    "time_sleep": "time.sleep() blocks the event loop",
    "requests_http": "requests library performs blocking HTTP I/O",
    "open_file_io": "open() performs blocking file I/O",
    "subprocess_call": "subprocess call blocks the event loop",
    "urllib_call": "urllib.request.urlopen() performs blocking HTTP I/O",
}

# HTTP methods that requests library exposes as module-level functions
_REQUESTS_HTTP_METHODS = frozenset(
    ("get", "post", "put", "delete", "patch", "head", "options", "request")
)

# Blocking subprocess functions
_SUBPROCESS_BLOCKING_FUNCS = frozenset(
    ("run", "call", "check_output", "check_call", "Popen")
)


class BlockingAsyncVisitor(ast.NodeVisitor):
    """
    AST visitor that detects blocking calls inside async functions.

    Uses a context stack to track whether the current node is inside an
    async function definition. Only flags blocking calls when the innermost
    enclosing function is an async def.

    Sync functions nested inside async functions are correctly excluded:
    the context stack records the most recent function type, so a sync
    inner function suppresses detection until its scope ends.
    """

    def __init__(self, file_path: str, source_lines: List[str]):
        """
        Initialize the blocking async visitor.

        Args:
            file_path: Path to the file being analyzed
            source_lines: Source code lines for extracting call text
        """
        self.file_path = file_path
        self.source_lines = source_lines
        self.violations: List[BlockingCall] = []
        self.context_stack: List[bool] = []  # True = async function, False = sync function
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None

    def _in_async_context(self) -> bool:
        """Return True if the innermost enclosing function is async."""
        return bool(self.context_stack) and self.context_stack[-1]

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition to track class context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit sync function - push False onto context stack."""
        old_function = self.current_function
        self.current_function = node.name
        self.context_stack.append(False)
        self.generic_visit(node)
        self.context_stack.pop()
        self.current_function = old_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function - push True onto context stack."""
        old_function = self.current_function
        self.current_function = node.name
        self.context_stack.append(True)
        self.generic_visit(node)
        self.context_stack.pop()
        self.current_function = old_function

    def visit_Call(self, node: ast.Call) -> None:
        """Visit a function call - check for blocking patterns if in async context."""
        if self._in_async_context():
            blocking_type = self._detect_blocking_call(node)
            if blocking_type:
                self._record_violation(node, blocking_type)
        self.generic_visit(node)

    def _detect_blocking_call(self, node: ast.Call) -> Optional[str]:
        """
        Determine if a Call node represents a blocking operation.

        Returns the BlockingCallType string value, or None if not blocking.
        """
        func = node.func

        # Direct name calls: open()
        if isinstance(func, ast.Name):
            if func.id == "open":
                return BlockingCallType.OPEN_FILE_IO.value

        if not isinstance(func, ast.Attribute):
            return None

        attr = func.attr
        value = func.value

        # Single-level attribute: module.function(...)
        if isinstance(value, ast.Name):
            module = value.id

            # time.sleep
            if module == "time" and attr == "sleep":
                return BlockingCallType.TIME_SLEEP.value

            # requests.get/post/put/delete/patch/head/options/request
            if module == "requests" and attr in _REQUESTS_HTTP_METHODS:
                return BlockingCallType.REQUESTS_HTTP.value

            # subprocess.run/call/check_output/check_call/Popen
            if module == "subprocess" and attr in _SUBPROCESS_BLOCKING_FUNCS:
                return BlockingCallType.SUBPROCESS_CALL.value

            # request.urlopen (from urllib import request)
            if module == "request" and attr == "urlopen":
                return BlockingCallType.URLLIB_CALL.value

        # Two-level attribute: package.module.function(...)
        if isinstance(value, ast.Attribute):
            inner = value.value
            if isinstance(inner, ast.Name):
                # urllib.request.urlopen
                if inner.id == "urllib" and value.attr == "request" and attr == "urlopen":
                    return BlockingCallType.URLLIB_CALL.value

        return None

    def _get_call_expression(self, node: ast.Call) -> str:
        """Extract the source line containing the blocking call."""
        if node.lineno <= len(self.source_lines):
            return self.source_lines[node.lineno - 1].strip()
        return ""

    def _get_context_description(self, blocking_type_val: str) -> str:
        """Build a human-readable context description for the blocking call."""
        base = _CONTEXT_DESCRIPTIONS.get(blocking_type_val, "blocking call in async function")
        if self.current_class and self.current_function:
            return f"{base} in async '{self.current_class}.{self.current_function}'"
        elif self.current_function:
            return f"{base} in async '{self.current_function}'"
        return base

    def _record_violation(self, node: ast.Call, blocking_type_val: str) -> None:
        """Record a blocking call violation."""
        call_expr = self._get_call_expression(node)
        context = self._get_context_description(blocking_type_val)
        remediation = _BLOCKING_REMEDIATION.get(
            blocking_type_val, "Use async-safe alternatives instead of blocking calls."
        )

        self.violations.append(BlockingCall(
            file_path=self.file_path,
            line_number=node.lineno,
            call_expression=call_expr,
            blocking_type=BlockingCallType(blocking_type_val),
            severity=BlockingAsyncSeverity.HIGH,
            containing_function=self.current_function,
            containing_class=self.current_class,
            context_description=context,
            remediation=remediation,
        ))


class BlockingAsyncScanner:
    """
    Scans Python files for blocking calls inside async functions.

    Detects time.sleep, requests HTTP calls, open(), subprocess calls,
    and urllib calls that are used inside async def functions, where they
    block the event loop rather than yielding control.

    Usage:
        scanner = BlockingAsyncScanner()
        report = scanner.analyze(Path("./src"))

        for call in report.detected_calls:
            print(f"{call.location}: {call.call_expression}")
    """

    def __init__(self, config: Optional[BlockingAsyncConfig] = None):
        """
        Initialize the blocking async scanner.

        Args:
            config: Configuration for scanning. If None, uses defaults.
        """
        self.config = config or BlockingAsyncConfig()

    def analyze(self, path: Path) -> BlockingAsyncReport:
        """
        Analyze a file or directory for blocking calls inside async functions.

        Args:
            path: Path to file or directory to analyze

        Returns:
            BlockingAsyncReport with all detected violations

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = BlockingAsyncReport(scan_path=str(path))

        if path.is_file():
            violations = self._analyze_file(path, path.parent)
            for violation in violations:
                report.add_violation(violation)
            report.files_scanned = 1
        else:
            self._analyze_directory(path, report)

        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()

        file_violation_counts: Dict[str, int] = defaultdict(int)
        for call in report.detected_calls:
            file_violation_counts[call.file_path] += 1

        report.most_problematic_files = sorted(
            file_violation_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return report

    def _analyze_file(self, file_path: Path, root_path: Path) -> List[BlockingCall]:
        """
        Analyze a single file for blocking calls in async functions.

        Args:
            file_path: Path to Python file
            root_path: Root path for calculating relative paths

        Returns:
            List of detected BlockingCall violations
        """
        try:
            source = file_path.read_text(encoding="utf-8")
            source_lines = source.splitlines()
            tree = ast.parse(source)

            visitor = BlockingAsyncVisitor(
                file_path=str(file_path.absolute()),
                source_lines=source_lines,
            )
            visitor.visit(tree)

            for violation in visitor.violations:
                try:
                    violation.relative_path = str(file_path.relative_to(root_path))
                except ValueError:
                    violation.relative_path = file_path.name

            return visitor.violations

        except SyntaxError:
            return []
        except Exception:
            return []

    def _analyze_directory(self, directory: Path, report: BlockingAsyncReport) -> None:
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

    def generate_report(self, report: BlockingAsyncReport, output_format: str = "text") -> str:
        """
        Generate a formatted blocking-in-async report.

        Args:
            report: BlockingAsyncReport to format
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

    def _generate_text_report(self, report: BlockingAsyncReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "BLOCKING CALL IN ASYNC CONTEXT REPORT",
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
            for blocking_type in BlockingCallType:
                count = report.violations_by_type.get(blocking_type.value, 0)
                if count > 0:
                    lines.append(f"  {blocking_type.value.replace('_', ' ').title()}: {count}")

            if report.most_problematic_files:
                lines.extend(["", "Most Problematic Files:", "-" * 40])
                for file_path, count in report.most_problematic_files[:5]:
                    filename = os.path.basename(file_path)
                    lines.append(f"  {filename}: {count} violations")

            lines.extend(["", "VIOLATIONS", "-" * 40])

            for call in report.detected_calls:
                filename = os.path.basename(call.file_path)
                lines.append(f"  {filename}:{call.line_number}")
                lines.append(f"    Call:         {call.call_expression}")
                lines.append(f"    Type:         {call.blocking_type}")
                lines.append(f"    Context:      {call.context_description}")
                lines.append(f"    Remediation:  {call.remediation}")
                lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self, report: BlockingAsyncReport) -> str:
        """Generate JSON report."""
        violations_data = []
        for v in report.detected_calls:
            violations_data.append({
                "file_path": v.file_path,
                "relative_path": v.relative_path,
                "line_number": v.line_number,
                "call_expression": v.call_expression,
                "blocking_type": v.blocking_type if isinstance(v.blocking_type, str) else v.blocking_type.value,
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

    def _generate_markdown_report(self, report: BlockingAsyncReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Blocking Call in Async Context Report",
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
            for blocking_type in BlockingCallType:
                count = report.violations_by_type.get(blocking_type.value, 0)
                if count > 0:
                    lines.append(f"| {blocking_type.value.replace('_', ' ').title()} | {count} |")

            if report.most_problematic_files:
                lines.extend(["", "## Most Problematic Files", ""])
                for file_path, count in report.most_problematic_files[:10]:
                    filename = os.path.basename(file_path)
                    lines.append(f"- `{filename}`: {count} violations")

            lines.extend(["", "## Violations", ""])

            for v in report.detected_calls[:50]:
                filename = os.path.basename(v.file_path)
                lines.extend([
                    f"#### `{filename}:{v.line_number}`",
                    "",
                    f"**Call:** `{v.call_expression}`",
                    "",
                    f"**Type:** {v.blocking_type}",
                    "",
                    f"**Context:** {v.context_description}",
                    "",
                    f"**Remediation:** {v.remediation}",
                    "",
                ])

        return "\n".join(lines)
