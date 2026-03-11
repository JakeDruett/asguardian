"""
Heimdall Resource Cleanup Scanner Service

Detects resource leaks where file handles, network connections, or collections
are opened/populated without proper cleanup, which can cause resource exhaustion
or unbounded memory growth.

Detects:
- open() calls not wrapped in a 'with' block
- socket.socket() and subprocess.Popen() calls not wrapped in a 'with' block
- Collections (list, deque) that are appended/extended but never cleared
  within the same function scope
"""

import ast
import fnmatch
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from Asgard.Heimdall.Quality.models.resource_cleanup_models import (
    ResourceCleanupConfig,
    ResourceCleanupReport,
    ResourceCleanupSeverity,
    ResourceCleanupType,
    ResourceCleanupViolation,
)


# Connection-like calls that should use context managers
CONNECTION_CALLS = {
    ("socket", "socket"),       # socket.socket()
    ("subprocess", "Popen"),    # subprocess.Popen()
    ("ssl", "wrap_socket"),     # ssl.wrap_socket()
    ("ssl", "SSLContext"),      # ssl.SSLContext()
}

# Single-name connection calls (from direct imports)
CONNECTION_NAMES = {
    "Popen",
}


def _is_open_call(node: ast.Call) -> bool:
    """Return True if this Call node is a call to open()."""
    if isinstance(node.func, ast.Name):
        return node.func.id == "open"
    if isinstance(node.func, ast.Attribute):
        # builtins.open or io.open
        return node.func.attr == "open"
    return False


def _is_connection_call(node: ast.Call) -> bool:
    """Return True if this Call is a known connection-type constructor."""
    if isinstance(node.func, ast.Attribute):
        if isinstance(node.func.value, ast.Name):
            pair = (node.func.value.id, node.func.attr)
            if pair in CONNECTION_CALLS:
                return True
    if isinstance(node.func, ast.Name):
        if node.func.id in CONNECTION_NAMES:
            return True
    return False


def _get_call_repr(node: ast.Call) -> str:
    """Get a readable representation of a call expression."""
    if isinstance(node.func, ast.Name):
        return f"{node.func.id}()"
    if isinstance(node.func, ast.Attribute):
        if isinstance(node.func.value, ast.Name):
            return f"{node.func.value.id}.{node.func.attr}()"
        return f"...{node.func.attr}()"
    return "unknown_call()"


def _get_variable_name(node: ast.Attribute) -> Optional[str]:
    """Extract variable name from an attribute access (e.g., 'obj' from obj.append)."""
    if isinstance(node.value, ast.Name):
        return node.value.id
    return None


class ResourceCleanupVisitor(ast.NodeVisitor):
    """
    AST visitor that detects resource cleanup violations.

    Walks the AST and identifies:
    - open() and connection calls outside 'with' blocks
    - Collections appended/extended without being cleared in the same scope
    """

    def __init__(self, file_path: str, source_lines: List[str]):
        """
        Initialize the resource cleanup visitor.

        Args:
            file_path: Path to the file being analyzed
            source_lines: Source code lines for extracting code text
        """
        self.file_path = file_path
        self.source_lines = source_lines
        self.violations: List[ResourceCleanupViolation] = []
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        # Stack tracks context types: "with", "function", "method", "class"
        self.context_stack: List[str] = []

    def _get_code_snippet(self, node: ast.AST) -> str:
        """Extract the code snippet from source."""
        if hasattr(node, 'lineno') and node.lineno <= len(self.source_lines):
            return self.source_lines[node.lineno - 1].strip()
        return ""

    def _in_with_block(self) -> bool:
        """Return True if currently inside a 'with' or 'async with' block."""
        return "with" in self.context_stack

    def _in_try_finally_with_close(self, node: ast.AST) -> bool:
        """Placeholder: detecting try/finally close() patterns requires deeper analysis."""
        return False

    def _record_violation(
        self,
        node: ast.AST,
        cleanup_type: ResourceCleanupType,
        resource_name: Optional[str],
        remediation: str,
        severity: ResourceCleanupSeverity = ResourceCleanupSeverity.MEDIUM,
    ) -> None:
        """Record a resource cleanup violation."""
        code_snippet = self._get_code_snippet(node)

        context_parts = []
        if self.current_class:
            context_parts.append(f"class {self.current_class}")
        if self.current_function:
            context_parts.append(f"function {self.current_function}")
        context = f"in {', '.join(context_parts)}" if context_parts else "at module level"

        type_labels = {
            ResourceCleanupType.FILE_OPEN_NO_WITH: "File opened outside 'with' block",
            ResourceCleanupType.CONNECTION_NO_WITH: "Connection opened outside 'with' block",
            ResourceCleanupType.COLLECTION_NO_CLEAR: "Collection grows unbounded without clear()",
        }
        context_description = f"{type_labels.get(cleanup_type, 'Resource leak')} {context}"

        self.violations.append(ResourceCleanupViolation(
            file_path=self.file_path,
            line_number=getattr(node, 'lineno', 0),
            column=getattr(node, 'col_offset', 0),
            code_snippet=code_snippet,
            resource_name=resource_name,
            cleanup_type=cleanup_type,
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
        self.context_stack.append("class")
        self.generic_visit(node)
        self.context_stack.pop()
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition."""
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition."""
        self._visit_function(node)

    def _visit_function(self, node) -> None:
        """Common handler for function and async function definitions."""
        old_function = self.current_function
        self.current_function = node.name
        context = "method" if self.current_class else "function"
        self.context_stack.append(context)

        # Analyze collection usage within this function body
        self._check_collection_usage(node)

        self.generic_visit(node)

        self.context_stack.pop()
        self.current_function = old_function

    def visit_With(self, node: ast.With) -> None:
        """Track 'with' block context."""
        self.context_stack.append("with")
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        """Track 'async with' block context."""
        self.context_stack.append("with")
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_Call(self, node: ast.Call) -> None:
        """Visit call nodes to detect open() and connection calls outside with blocks."""
        if not self._in_with_block():
            if _is_open_call(node):
                self._record_violation(
                    node,
                    ResourceCleanupType.FILE_OPEN_NO_WITH,
                    resource_name="file",
                    remediation=(
                        "Use 'with open(...) as f:' to ensure the file is closed automatically."
                    ),
                    severity=ResourceCleanupSeverity.HIGH,
                )
            elif _is_connection_call(node):
                call_repr = _get_call_repr(node)
                self._record_violation(
                    node,
                    ResourceCleanupType.CONNECTION_NO_WITH,
                    resource_name=call_repr,
                    remediation=(
                        f"Use 'with {call_repr} as conn:' or call .close() in a finally block."
                    ),
                    severity=ResourceCleanupSeverity.HIGH,
                )

        self.generic_visit(node)

    def _check_collection_usage(self, func_node: ast.AST) -> None:
        """
        Analyze a function body for collections that are appended/extended
        but never cleared within that scope.
        """
        # Collect variable names that have append/extend called
        appended_vars: Dict[str, int] = {}  # varname -> first_line
        cleared_vars: Set[str] = set()

        for node in ast.walk(func_node):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute):
                continue

            attr = node.func.attr
            var_name = _get_variable_name(node.func)
            if var_name is None:
                continue

            if attr in ("append", "extend"):
                if var_name not in appended_vars:
                    appended_vars[var_name] = getattr(node, 'lineno', 0)
            elif attr == "clear":
                cleared_vars.add(var_name)

        for var_name, first_line in appended_vars.items():
            if var_name not in cleared_vars:
                # Find the node at that line to record the violation
                self._record_collection_violation(func_node, var_name, first_line)

    def _record_collection_violation(
        self, func_node: ast.AST, var_name: str, first_line: int
    ) -> None:
        """Record a collection-no-clear violation."""
        code_snippet = ""
        if first_line and first_line <= len(self.source_lines):
            code_snippet = self.source_lines[first_line - 1].strip()

        context_parts = []
        if self.current_class:
            context_parts.append(f"class {self.current_class}")
        if self.current_function:
            context_parts.append(f"function {self.current_function}")
        context = f"in {', '.join(context_parts)}" if context_parts else "at module level"

        self.violations.append(ResourceCleanupViolation(
            file_path=self.file_path,
            line_number=first_line,
            column=0,
            code_snippet=code_snippet,
            resource_name=var_name,
            cleanup_type=ResourceCleanupType.COLLECTION_NO_CLEAR,
            severity=ResourceCleanupSeverity.MEDIUM,
            containing_function=self.current_function,
            containing_class=self.current_class,
            context_description=(
                f"Collection '{var_name}' is appended/extended but never cleared {context}"
            ),
            remediation=(
                f"Call '{var_name}.clear()' when the collection is no longer needed, "
                "or use a bounded data structure."
            ),
        ))


class ResourceCleanupScanner:
    """
    Scans Python files for resource cleanup violations.

    Detects open() and connection calls outside 'with' blocks, and collections
    that grow unbounded without being cleared.

    Usage:
        scanner = ResourceCleanupScanner()
        report = scanner.analyze(Path("./src"))

        for violation in report.detected_violations:
            print(f"{violation.location}: {violation.context_description}")
    """

    def __init__(self, config: Optional[ResourceCleanupConfig] = None):
        """
        Initialize resource cleanup scanner.

        Args:
            config: Configuration for scanning. If None, uses defaults.
        """
        self.config = config or ResourceCleanupConfig()

    def analyze(self, path: Path) -> ResourceCleanupReport:
        """
        Analyze a file or directory for resource cleanup violations.

        Args:
            path: Path to file or directory to analyze

        Returns:
            ResourceCleanupReport with all detected violations

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = ResourceCleanupReport(scan_path=str(path))

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
    ) -> List[ResourceCleanupViolation]:
        """
        Analyze a single Python file for resource cleanup violations.

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

            visitor = ResourceCleanupVisitor(
                file_path=str(file_path.absolute()),
                source_lines=source_lines,
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

    def _analyze_directory(self, directory: Path, report: ResourceCleanupReport) -> None:
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
            severity = ResourceCleanupSeverity(severity)
        levels = {
            ResourceCleanupSeverity.LOW: 1,
            ResourceCleanupSeverity.MEDIUM: 2,
            ResourceCleanupSeverity.HIGH: 3,
        }
        return levels.get(severity, 1)

    def generate_report(self, report: ResourceCleanupReport, output_format: str = "text") -> str:
        """
        Generate formatted resource cleanup report.

        Args:
            report: ResourceCleanupReport to format
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

    def _generate_text_report(self, report: ResourceCleanupReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 70,
            "RESOURCE CLEANUP VIOLATIONS REPORT",
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
                ResourceCleanupSeverity.HIGH,
                ResourceCleanupSeverity.MEDIUM,
                ResourceCleanupSeverity.LOW,
            ]:
                count = report.violations_by_severity.get(severity.value, 0)
                if count > 0:
                    lines.append(f"  {severity.value.upper()}: {count}")

            lines.extend(["", "By Type:"])
            for cleanup_type in ResourceCleanupType:
                count = report.violations_by_type.get(cleanup_type.value, 0)
                if count > 0:
                    lines.append(f"  {cleanup_type.value.replace('_', ' ').title()}: {count}")

            if report.most_problematic_files:
                lines.extend(["", "Most Problematic Files:", "-" * 40])
                for file_path, count in report.most_problematic_files[:5]:
                    filename = os.path.basename(file_path)
                    lines.append(f"  {filename}: {count} violations")

            lines.extend(["", "VIOLATIONS", "-" * 40])

            for severity in [
                ResourceCleanupSeverity.HIGH,
                ResourceCleanupSeverity.MEDIUM,
                ResourceCleanupSeverity.LOW,
            ]:
                severity_violations = report.get_violations_by_severity(severity)
                if severity_violations:
                    lines.extend(["", f"[{severity.value.upper()}]"])
                    for v in severity_violations:
                        lines.append(f"  {v.location}")
                        lines.append(f"    Code: {v.code_snippet}")
                        if v.resource_name:
                            lines.append(f"    Resource: {v.resource_name}")
                        lines.append(f"    Context: {v.context_description}")
                        lines.append(f"    Fix: {v.remediation}")
                        lines.append("")

        lines.append("=" * 70)
        return "\n".join(lines)

    def _generate_json_report(self, report: ResourceCleanupReport) -> str:
        """Generate JSON report."""
        violations_data = []
        for v in report.detected_violations:
            violations_data.append({
                "file_path": v.file_path,
                "relative_path": v.relative_path,
                "line_number": v.line_number,
                "column": v.column,
                "code_snippet": v.code_snippet,
                "resource_name": v.resource_name,
                "cleanup_type": v.cleanup_type if isinstance(v.cleanup_type, str) else v.cleanup_type.value,
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

    def _generate_markdown_report(self, report: ResourceCleanupReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Resource Cleanup Violations Report",
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
                ResourceCleanupSeverity.HIGH,
                ResourceCleanupSeverity.MEDIUM,
                ResourceCleanupSeverity.LOW,
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
            for cleanup_type in ResourceCleanupType:
                count = report.violations_by_type.get(cleanup_type.value, 0)
                if count > 0:
                    lines.append(f"| {cleanup_type.value.replace('_', ' ').title()} | {count} |")

            if report.most_problematic_files:
                lines.extend(["", "## Most Problematic Files", ""])
                for file_path, count in report.most_problematic_files[:10]:
                    filename = os.path.basename(file_path)
                    lines.append(f"- `{filename}`: {count} violations")

            lines.extend(["", "## Violations", ""])

            for severity in [
                ResourceCleanupSeverity.HIGH,
                ResourceCleanupSeverity.MEDIUM,
                ResourceCleanupSeverity.LOW,
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
                        if v.resource_name:
                            lines.append(f"**Resource:** `{v.resource_name}`")
                        lines.extend([
                            "",
                            f"**Context:** {v.context_description}",
                            "",
                            f"**Remediation:** {v.remediation}",
                            "",
                        ])

        return "\n".join(lines)
