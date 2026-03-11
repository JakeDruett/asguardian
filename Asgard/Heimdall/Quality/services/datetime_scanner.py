"""
Heimdall Datetime Scanner Service

Detects deprecated and unsafe datetime usage patterns.
"""

import ast
import fnmatch
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from Asgard.Heimdall.Quality.models.datetime_models import (
    DatetimeConfig,
    DatetimeIssueType,
    DatetimeReport,
    DatetimeSeverity,
    DatetimeViolation,
    DATETIME_REMEDIATIONS,
)


class DatetimeVisitor(ast.NodeVisitor):
    """
    AST visitor that detects problematic datetime usage.

    Walks the AST and identifies:
    - datetime.utcnow() calls (deprecated in Python 3.12+)
    - datetime.now() calls without timezone argument
    - datetime.today() calls (returns naive datetime)
    - datetime.utcfromtimestamp() calls (deprecated)
    """

    def __init__(
        self,
        file_path: str,
        source_lines: List[str],
        config: DatetimeConfig,
    ):
        """
        Initialize the datetime visitor.

        Args:
            file_path: Path to the file being analyzed
            source_lines: Source code lines for extracting context
            config: Configuration for what to check
        """
        self.file_path = file_path
        self.source_lines = source_lines
        self.config = config
        self.violations: List[DatetimeViolation] = []
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        self._datetime_aliases: set = set()  # Track 'from datetime import datetime'
        self._datetime_module_aliases: Dict[str, str] = {}  # Track 'import datetime as dt'

    def _get_code_snippet(self, line_number: int) -> str:
        """Extract code at the line."""
        if line_number <= len(self.source_lines):
            return self.source_lines[line_number - 1].strip()
        return ""

    def _determine_severity(self, issue_type: DatetimeIssueType) -> DatetimeSeverity:
        """Determine severity based on issue type."""
        # Deprecated methods are high severity
        if issue_type in (DatetimeIssueType.UTCNOW, DatetimeIssueType.UTCFROMTIMESTAMP):
            return DatetimeSeverity.HIGH
        # Naive datetime is medium severity
        return DatetimeSeverity.MEDIUM

    def _record_violation(
        self,
        node: ast.AST,
        issue_type: DatetimeIssueType,
    ) -> None:
        """Record a datetime violation."""
        self.violations.append(DatetimeViolation(
            file_path=self.file_path,
            line_number=node.lineno,
            column=node.col_offset,
            code_snippet=self._get_code_snippet(node.lineno),
            issue_type=issue_type,
            severity=self._determine_severity(issue_type),
            remediation=DATETIME_REMEDIATIONS.get(issue_type, "Use timezone-aware datetime"),
            containing_function=self.current_function,
            containing_class=self.current_class,
        ))

    def visit_Import(self, node: ast.Import) -> None:
        """Track import datetime statements."""
        for alias in node.names:
            if alias.name == "datetime":
                # import datetime or import datetime as dt
                actual_name = alias.asname if alias.asname else alias.name
                self._datetime_module_aliases[actual_name] = "datetime"
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Track from datetime import datetime statements."""
        if node.module == "datetime":
            for alias in node.names:
                if alias.name == "datetime":
                    # from datetime import datetime or from datetime import datetime as dt
                    actual_name = alias.asname if alias.asname else alias.name
                    self._datetime_aliases.add(actual_name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition to track class context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition to track function context."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition to track function context."""
        old_function = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_function

    def visit_Call(self, node: ast.Call) -> None:
        """Visit function calls to detect datetime issues."""
        self._check_datetime_call(node)
        self.generic_visit(node)

    def _check_datetime_call(self, node: ast.Call) -> None:
        """Check if this is a problematic datetime call."""
        # Handle datetime.datetime.utcnow() style
        if isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr

            # Check for method calls on datetime class
            if self._is_datetime_class_call(node.func):
                self._check_datetime_method(node, attr_name)

    def _is_datetime_class_call(self, func: ast.Attribute) -> bool:
        """Check if this is a call on the datetime class."""
        # datetime.utcnow() - direct call on datetime class in scope
        if isinstance(func.value, ast.Name):
            name = func.value.id
            # Check if 'datetime' was imported directly
            if name in self._datetime_aliases:
                return True
            # Check if 'datetime.datetime' style
            if name in self._datetime_module_aliases:
                return False  # This would be datetime module, not class

        # datetime.datetime.utcnow() - module.class.method
        if isinstance(func.value, ast.Attribute):
            if isinstance(func.value.value, ast.Name):
                module_name = func.value.value.id
                class_name = func.value.attr
                if module_name in self._datetime_module_aliases and class_name == "datetime":
                    return True
                if module_name == "datetime" and class_name == "datetime":
                    return True

        return False

    def _check_datetime_method(self, node: ast.Call, method_name: str) -> None:
        """Check specific datetime method calls."""
        # Check for utcnow()
        if method_name == "utcnow" and self.config.check_utcnow:
            self._record_violation(node, DatetimeIssueType.UTCNOW)

        # Check for utcfromtimestamp()
        elif method_name == "utcfromtimestamp" and self.config.check_utcnow:
            self._record_violation(node, DatetimeIssueType.UTCFROMTIMESTAMP)

        # Check for now() without timezone
        elif method_name == "now" and self.config.check_now_no_tz:
            if not self._has_timezone_arg(node):
                self._record_violation(node, DatetimeIssueType.NOW_NO_TZ)

        # Check for today()
        elif method_name == "today" and self.config.check_today_no_tz:
            self._record_violation(node, DatetimeIssueType.TODAY_NO_TZ)

    def _has_timezone_arg(self, node: ast.Call) -> bool:
        """Check if a now() call has a timezone argument."""
        # Check positional arguments
        if node.args:
            return True

        # Check keyword arguments for 'tz'
        for keyword in node.keywords:
            if keyword.arg == "tz":
                return True

        return False


class DatetimeScanner:
    """
    Scans Python files for deprecated and unsafe datetime usage.

    Detects:
    - datetime.utcnow() - deprecated in Python 3.12+
    - datetime.now() without timezone argument
    - datetime.today() - returns naive datetime
    - datetime.utcfromtimestamp() - deprecated

    Usage:
        scanner = DatetimeScanner()
        report = scanner.analyze(Path("./src"))

        for violation in report.detected_violations:
            print(f"{violation.location}: {violation.issue_type}")
    """

    def __init__(self, config: Optional[DatetimeConfig] = None):
        """
        Initialize datetime scanner.

        Args:
            config: Configuration for scanning. If None, uses defaults.
        """
        self.config = config or DatetimeConfig()

    def analyze(self, path: Path) -> DatetimeReport:
        """
        Analyze a file or directory for datetime issues.

        Args:
            path: Path to file or directory to analyze

        Returns:
            DatetimeReport with all detected violations

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = DatetimeReport(scan_path=str(path))

        if path.is_file():
            violations = self._analyze_file(path, path.parent)
            for violation in violations:
                report.add_violation(violation)
            report.files_scanned = 1
        else:
            self._analyze_directory(path, report)

        # Calculate scan duration
        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()

        # Calculate most problematic files
        file_violation_counts: Dict[str, int] = defaultdict(int)
        for violation in report.detected_violations:
            file_violation_counts[violation.file_path] += 1

        report.most_problematic_files = sorted(
            file_violation_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return report

    def _is_allowed_file(self, file_path: Path) -> bool:
        """Check if file is in allowed patterns."""
        file_str = str(file_path)
        for pattern in self.config.allowed_patterns:
            if fnmatch.fnmatch(file_str, pattern):
                return True
        return False

    def _analyze_file(self, file_path: Path, root_path: Path) -> List[DatetimeViolation]:
        """
        Analyze a single file for datetime issues.

        Args:
            file_path: Path to Python file
            root_path: Root path for calculating relative paths

        Returns:
            List of detected violations
        """
        # Skip files in allowed patterns
        if self._is_allowed_file(file_path):
            return []

        try:
            source = file_path.read_text(encoding="utf-8")
            source_lines = source.splitlines()
            tree = ast.parse(source)

            visitor = DatetimeVisitor(
                file_path=str(file_path.absolute()),
                source_lines=source_lines,
                config=self.config,
            )
            visitor.visit(tree)

            # Set relative paths
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

    def _analyze_directory(self, directory: Path, report: DatetimeReport) -> None:
        """
        Analyze all Python files in a directory.

        Args:
            directory: Directory to analyze
            report: Report to add violations to
        """
        files_scanned = 0

        for root, dirs, files in os.walk(directory):
            root_path = Path(root)

            # Filter excluded directories
            dirs[:] = [
                d for d in dirs
                if not any(self._matches_pattern(d, pattern) for pattern in self.config.exclude_patterns)
            ]

            for file in files:
                if not file.endswith(".py"):
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

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if name matches exclude pattern."""
        return fnmatch.fnmatch(name, pattern)

    def generate_report(self, report: DatetimeReport, output_format: str = "text") -> str:
        """
        Generate formatted datetime report.

        Args:
            report: DatetimeReport to format
            output_format: Report format (text, json, markdown)

        Returns:
            Formatted report string
        """
        format_lower = output_format.lower()
        if format_lower == "json":
            return self._generate_json_report(report)
        elif format_lower == "markdown" or format_lower == "md":
            return self._generate_markdown_report(report)
        elif format_lower == "text":
            return self._generate_text_report(report)
        else:
            raise ValueError(f"Unsupported format: {output_format}")

    def _generate_text_report(self, report: DatetimeReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "DATETIME USAGE REPORT",
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
            lines.extend(["By Issue Type:"])
            for issue_type in DatetimeIssueType:
                count = report.violations_by_type.get(issue_type.value, 0)
                if count > 0:
                    lines.append(f"  {issue_type.value}: {count}")

            lines.extend(["", "By Severity:"])
            for severity in [DatetimeSeverity.HIGH, DatetimeSeverity.MEDIUM, DatetimeSeverity.LOW]:
                count = report.violations_by_severity.get(severity.value, 0)
                if count > 0:
                    lines.append(f"  {severity.value.upper()}: {count}")

            lines.extend(["", "VIOLATIONS", "-" * 40])

            for severity in [DatetimeSeverity.HIGH, DatetimeSeverity.MEDIUM, DatetimeSeverity.LOW]:
                severity_violations = report.get_violations_by_severity(severity)
                if severity_violations:
                    lines.extend(["", f"[{severity.value.upper()}]"])
                    for v in severity_violations:
                        lines.extend([
                            f"  {v.location}",
                            f"    Code: {v.code_snippet}",
                            f"    Issue: {v.issue_type}",
                            f"    Fix: {v.remediation}",
                            "",
                        ])

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self, report: DatetimeReport) -> str:
        """Generate JSON report."""
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
            "violations": [
                {
                    "file_path": v.file_path,
                    "relative_path": v.relative_path,
                    "line_number": v.line_number,
                    "code_snippet": v.code_snippet,
                    "issue_type": v.issue_type,
                    "severity": v.severity,
                    "remediation": v.remediation,
                    "containing_function": v.containing_function,
                    "containing_class": v.containing_class,
                }
                for v in report.detected_violations
            ],
        }
        return json.dumps(report_data, indent=2)

    def _generate_markdown_report(self, report: DatetimeReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Datetime Usage Report",
            "",
            f"**Scan Path:** `{report.scan_path}`",
            f"**Generated:** {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
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
                "### By Issue Type",
                "",
                "| Issue | Count |",
                "|-------|-------|",
            ])
            for issue_type in DatetimeIssueType:
                count = report.violations_by_type.get(issue_type.value, 0)
                if count > 0:
                    lines.append(f"| {issue_type.value} | {count} |")

            lines.extend(["", "## Violations", ""])

            for v in report.detected_violations[:50]:
                lines.extend([
                    f"### `{v.location}`",
                    "",
                    f"**Code:** `{v.code_snippet}`",
                    "",
                    f"**Issue:** {v.issue_type}",
                    "",
                    f"**Fix:** {v.remediation}",
                    "",
                ])

        return "\n".join(lines)
