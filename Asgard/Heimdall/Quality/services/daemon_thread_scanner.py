"""
Heimdall Daemon Thread Monitor Service

Detects daemon thread lifecycle issues in Python code using AST analysis.

Detects:
- daemon=True threads with no join() call (uncontrolled lifecycle)
- daemon=True threads stored only in local variables (reference may be lost)
- Event.wait() patterns where only daemon threads call .set() (potential hang)
"""

import ast
import os
import json
import fnmatch
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from Asgard.Heimdall.Quality.models.daemon_thread_models import (
    DaemonThreadConfig,
    DaemonThreadIssue,
    DaemonThreadIssueType,
    DaemonThreadReport,
    DaemonThreadSeverity,
)


def _is_thread_call(call_node: ast.Call) -> bool:
    """Check if a Call node is a threading.Thread() or Thread() instantiation."""
    func = call_node.func
    return (
        (isinstance(func, ast.Name) and func.id == "Thread")
        or (isinstance(func, ast.Attribute) and func.attr == "Thread")
    )


def _is_daemon_thread_call(call_node: ast.Call) -> bool:
    """Check if Thread() call has daemon=True keyword argument."""
    if not _is_thread_call(call_node):
        return False
    for kw in call_node.keywords:
        if kw.arg == "daemon":
            # Check for True literal
            if isinstance(kw.value, ast.Constant) and kw.value.value is True:
                return True
            # Check for ast.NameConstant True (older Python)
            if isinstance(kw.value, ast.Name) and kw.value.id == "True":
                return True
    return False


def _is_event_call(call_node: ast.Call) -> bool:
    """Check if Call node is threading.Event() or Event() instantiation."""
    func = call_node.func
    return (
        (isinstance(func, ast.Name) and func.id == "Event")
        or (isinstance(func, ast.Attribute) and func.attr == "Event")
    )


def _get_method_name(call_node: ast.Call) -> Optional[str]:
    """Get the method name from a method call (e.g. 'start', 'join', 'set', 'wait')."""
    if isinstance(call_node.func, ast.Attribute):
        return call_node.func.attr
    return None


def _get_call_receiver_name(call_node: ast.Call) -> Optional[str]:
    """Get the variable name the method is called on."""
    if isinstance(call_node.func, ast.Attribute):
        if isinstance(call_node.func.value, ast.Name):
            return call_node.func.value.id
        elif (
            isinstance(call_node.func.value, ast.Attribute)
            and isinstance(call_node.func.value.value, ast.Name)
            and call_node.func.value.value.id == "self"
        ):
            return f"self.{call_node.func.value.attr}"
    return None


def _is_stored_on_self(assign_node: ast.Assign) -> bool:
    """Check if the assignment target is a self.attr (stored on instance)."""
    for target in assign_node.targets:
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        ):
            return True
    return False


def _get_local_var_name(assign_node: ast.Assign) -> Optional[str]:
    """Get the local variable name from an assignment if target is a plain Name."""
    for target in assign_node.targets:
        if isinstance(target, ast.Name):
            return target.id
    return None


class DaemonThreadInfo:
    """Holds information about a daemon thread found in code."""

    def __init__(self, var_name: str, line_number: int, stored_on_self: bool):
        self.var_name = var_name
        self.line_number = line_number
        self.stored_on_self = stored_on_self


class DaemonThreadVisitor(ast.NodeVisitor):
    """
    AST visitor that detects daemon thread lifecycle issues.

    Analyzes function/method bodies for:
    - Daemon threads stored in local variables only (reference may be lost)
    - Daemon threads with no join() call in the same scope
    - Event.wait() patterns with only daemon thread callers for .set()
    """

    def __init__(self, file_path: str, source_lines: List[str]):
        """
        Initialize the daemon thread visitor.

        Args:
            file_path: Path to the file being analyzed
            source_lines: Source code lines for context
        """
        self.file_path = file_path
        self.source_lines = source_lines
        self.issues: List[DaemonThreadIssue] = []
        self.current_class: Optional[str] = None
        self.current_method: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Analyze function/method for daemon thread issues."""
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Analyze async function for daemon thread issues."""
        self._visit_function(node)

    def _visit_function(self, node) -> None:
        """Common handler for function and async function analysis."""
        old_method = self.current_method
        self.current_method = node.name
        self._analyze_scope(node.body)
        self.generic_visit(node)
        self.current_method = old_method

    def _analyze_scope(self, body: List[ast.stmt]) -> None:
        """
        Analyze a scope (function body) for daemon thread lifecycle issues.

        Collects all daemon thread assignments, then checks:
        1. Whether each is stored in a local var only (MEDIUM)
        2. Whether each has a .join() call in scope (LOW if missing)
        3. Whether Event objects are waited on by non-daemon code (MEDIUM)
        """
        # Track daemon thread info: var_name -> DaemonThreadInfo
        daemon_threads: Dict[str, DaemonThreadInfo] = {}

        # Track all join() calls in scope: set of var names joined
        joined_vars: Set[str] = set()

        # Track event variables
        event_vars: Set[str] = set()
        event_set_callers: Dict[str, List[str]] = defaultdict(list)  # event_var -> [caller thread targets]
        event_waited: Set[str] = set()

        # Collect daemon threads and joined vars
        for stmt in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(stmt, ast.Assign):
                if isinstance(stmt.value, ast.Call):
                    if _is_daemon_thread_call(stmt.value):
                        stored_on_self = _is_stored_on_self(stmt)
                        local_name = _get_local_var_name(stmt)
                        var_name = local_name if not stored_on_self else None
                        if stored_on_self:
                            # self.t = Thread(daemon=True) - get attr name
                            for target in stmt.targets:
                                if (
                                    isinstance(target, ast.Attribute)
                                    and isinstance(target.value, ast.Name)
                                    and target.value.id == "self"
                                ):
                                    var_name = f"self.{target.attr}"
                        if var_name:
                            daemon_threads[var_name] = DaemonThreadInfo(
                                var_name=var_name,
                                line_number=stmt.lineno,
                                stored_on_self=stored_on_self,
                            )

                    elif _is_event_call(stmt.value):
                        local_name = _get_local_var_name(stmt)
                        if local_name:
                            event_vars.add(local_name)
                        for target in stmt.targets:
                            if (
                                isinstance(target, ast.Attribute)
                                and isinstance(target.value, ast.Name)
                                and target.value.id == "self"
                            ):
                                event_vars.add(f"self.{target.attr}")

            elif isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                method = _get_method_name(call)
                receiver = _get_call_receiver_name(call)
                if method == "join" and receiver:
                    joined_vars.add(receiver)
                elif method == "wait" and receiver:
                    event_waited.add(receiver)

        # Generate issues for daemon threads
        for var_name, info in daemon_threads.items():
            # Issue 1: stored in local variable only (MEDIUM)
            if not info.stored_on_self:
                self.issues.append(DaemonThreadIssue(
                    file_path=self.file_path,
                    line_number=info.line_number,
                    class_name=self.current_class,
                    method_name=self.current_method,
                    issue_type=DaemonThreadIssueType.LOCAL_VAR_ONLY,
                    severity=DaemonThreadSeverity.MEDIUM,
                    description=(
                        f"Daemon thread '{var_name}' is stored only in a local variable. "
                        f"The reference may be lost when the function returns, making it "
                        f"impossible to join or monitor the thread."
                    ),
                    thread_variable=var_name,
                    remediation=(
                        f"Store the daemon thread as an instance attribute (e.g., 'self._thread = {var_name}') "
                        f"to maintain a reference for monitoring and graceful shutdown."
                    ),
                ))

            # Issue 2: no join() call found in scope (LOW)
            if var_name not in joined_vars:
                self.issues.append(DaemonThreadIssue(
                    file_path=self.file_path,
                    line_number=info.line_number,
                    class_name=self.current_class,
                    method_name=self.current_method,
                    issue_type=DaemonThreadIssueType.NO_JOIN,
                    severity=DaemonThreadSeverity.LOW,
                    description=(
                        f"Daemon thread '{var_name}' has no join() call in scope. "
                        f"The thread will be silently killed when the main thread exits. "
                        f"Errors or incomplete work in the daemon thread may go undetected."
                    ),
                    thread_variable=var_name,
                    remediation=(
                        f"Add a health check mechanism or call '{var_name}.join(timeout=...)' "
                        f"with a timeout to detect if the daemon thread has terminated unexpectedly."
                    ),
                ))

        # Issue 3: Event.wait() where only daemon threads could call .set()
        # Heuristic: if we see Event.wait() in non-daemon code and daemon threads exist in scope
        if event_waited and daemon_threads:
            for event_var in event_waited:
                self.issues.append(DaemonThreadIssue(
                    file_path=self.file_path,
                    line_number=0,
                    class_name=self.current_class,
                    method_name=self.current_method,
                    issue_type=DaemonThreadIssueType.EVENT_SET_BY_DAEMON,
                    severity=DaemonThreadSeverity.MEDIUM,
                    description=(
                        f"Event '{event_var}' is waited on in a scope that also contains daemon "
                        f"threads. If only daemon threads call '{event_var}.set()', the wait "
                        f"may never complete if the daemon is killed before setting the event."
                    ),
                    thread_variable=event_var,
                    remediation=(
                        f"Ensure non-daemon code is responsible for calling '{event_var}.set()', "
                        f"or use Event.wait(timeout=...) to prevent indefinite blocking."
                    ),
                ))


class DaemonThreadScanner:
    """
    Scans Python files for daemon thread lifecycle issues.

    Detects patterns that can lead to silent failures or resource leaks
    in daemon thread usage.

    Usage:
        scanner = DaemonThreadScanner()
        report = scanner.analyze(Path("./src"))

        for issue in report.detected_issues:
            print(f"{issue.location}: {issue.description}")
    """

    def __init__(self, config: Optional[DaemonThreadConfig] = None):
        """
        Initialize daemon thread scanner.

        Args:
            config: Configuration for scanning. If None, uses defaults.
        """
        self.config = config or DaemonThreadConfig()

    def analyze(self, path: Path) -> DaemonThreadReport:
        """
        Analyze a file or directory for daemon thread lifecycle issues.

        Args:
            path: Path to file or directory to analyze

        Returns:
            DaemonThreadReport with all detected issues

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = DaemonThreadReport(scan_path=str(path))

        if path.is_file():
            issues = self._analyze_file(path, path.parent)
            for issue in issues:
                if self._meets_severity_filter(issue.severity):
                    report.add_violation(issue)
            report.files_scanned = 1
        else:
            self._analyze_directory(path, report)

        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()

        file_violation_counts: Dict[str, int] = defaultdict(int)
        for issue in report.detected_issues:
            file_violation_counts[issue.file_path] += 1

        report.most_problematic_files = sorted(
            file_violation_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return report

    def _analyze_file(self, file_path: Path, root_path: Path) -> List[DaemonThreadIssue]:
        """Analyze a single file for daemon thread issues."""
        try:
            source = file_path.read_text(encoding="utf-8")
            source_lines = source.splitlines()
            tree = ast.parse(source)

            visitor = DaemonThreadVisitor(
                file_path=str(file_path.absolute()),
                source_lines=source_lines,
            )
            visitor.visit(tree)

            for issue in visitor.issues:
                try:
                    issue.relative_path = str(file_path.relative_to(root_path))
                except ValueError:
                    issue.relative_path = file_path.name

            return visitor.issues

        except SyntaxError:
            return []
        except Exception:
            return []

    def _analyze_directory(self, directory: Path, report: DaemonThreadReport) -> None:
        """Analyze all Python files in a directory."""
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
                issues = self._analyze_file(file_path, directory)
                files_scanned += 1

                for issue in issues:
                    if self._meets_severity_filter(issue.severity):
                        report.add_violation(issue)

        report.files_scanned = files_scanned

    def _should_analyze_file(self, filename: str) -> bool:
        """Check if file should be analyzed based on extension."""
        if self.config.include_extensions:
            return any(filename.endswith(ext) for ext in self.config.include_extensions)
        return filename.endswith(".py")

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if name matches exclude pattern."""
        return fnmatch.fnmatch(name, pattern)

    def _meets_severity_filter(self, severity) -> bool:
        """Check if severity meets the configured filter."""
        return self._severity_level(severity) >= self._severity_level(self.config.severity_filter)

    def _severity_level(self, severity) -> int:
        """Convert severity to numeric level for comparison."""
        if isinstance(severity, str):
            severity = DaemonThreadSeverity(severity)
        levels = {
            DaemonThreadSeverity.LOW: 1,
            DaemonThreadSeverity.MEDIUM: 2,
        }
        return levels.get(severity, 1)

    def generate_report(self, report: DaemonThreadReport, output_format: str = "text") -> str:
        """
        Generate formatted daemon thread report.

        Args:
            report: DaemonThreadReport to format
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

    def _generate_text_report(self, report: DaemonThreadReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "DAEMON THREAD LIFECYCLE REPORT",
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
            lines.append("By Severity:")
            for severity in [DaemonThreadSeverity.MEDIUM, DaemonThreadSeverity.LOW]:
                count = report.violations_by_severity.get(severity.value, 0)
                if count > 0:
                    lines.append(f"  {severity.value.upper()}: {count}")

            lines.extend(["", "By Type:"])
            for issue_type in DaemonThreadIssueType:
                count = report.violations_by_type.get(issue_type.value, 0)
                if count > 0:
                    lines.append(f"  {issue_type.value.replace('_', ' ').title()}: {count}")

            if report.most_problematic_files:
                lines.extend(["", "Most Problematic Files:", "-" * 40])
                for file_path, count in report.most_problematic_files[:5]:
                    filename = os.path.basename(file_path)
                    lines.append(f"  {filename}: {count} violations")

            lines.extend(["", "VIOLATIONS", "-" * 40])

            for severity in [DaemonThreadSeverity.MEDIUM, DaemonThreadSeverity.LOW]:
                severity_issues = report.get_violations_by_severity(severity)
                if severity_issues:
                    lines.extend(["", f"[{severity.value.upper()}]"])
                    for issue in severity_issues:
                        loc = issue.qualified_location if (issue.class_name or issue.method_name) else issue.location
                        lines.append(f"  {loc}")
                        lines.append(f"    {issue.description}")
                        lines.append(f"    Fix: {issue.remediation}")
                        lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self, report: DaemonThreadReport) -> str:
        """Generate JSON report."""
        issues_data = []
        for issue in report.detected_issues:
            issues_data.append({
                "file_path": issue.file_path,
                "relative_path": issue.relative_path,
                "line_number": issue.line_number,
                "class_name": issue.class_name,
                "method_name": issue.method_name,
                "issue_type": issue.issue_type if isinstance(issue.issue_type, str) else issue.issue_type.value,
                "severity": issue.severity if isinstance(issue.severity, str) else issue.severity.value,
                "description": issue.description,
                "thread_variable": issue.thread_variable,
                "remediation": issue.remediation,
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
            "violations": issues_data,
            "most_problematic_files": [
                {"file": file_path, "violation_count": count}
                for file_path, count in report.most_problematic_files
            ],
        }

        return json.dumps(report_data, indent=2)

    def _generate_markdown_report(self, report: DaemonThreadReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Daemon Thread Lifecycle Report",
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
            for severity in [DaemonThreadSeverity.MEDIUM, DaemonThreadSeverity.LOW]:
                count = report.violations_by_severity.get(severity.value, 0)
                lines.append(f"| {severity.value.title()} | {count} |")

            lines.extend([
                "",
                "### By Type",
                "",
                "| Type | Count |",
                "|------|-------|",
            ])
            for issue_type in DaemonThreadIssueType:
                count = report.violations_by_type.get(issue_type.value, 0)
                if count > 0:
                    lines.append(f"| {issue_type.value.replace('_', ' ').title()} | {count} |")

            if report.most_problematic_files:
                lines.extend(["", "## Most Problematic Files", ""])
                for file_path, count in report.most_problematic_files[:10]:
                    filename = os.path.basename(file_path)
                    lines.append(f"- `{filename}`: {count} violations")

            lines.extend(["", "## Violations", ""])

            for severity in [DaemonThreadSeverity.MEDIUM, DaemonThreadSeverity.LOW]:
                severity_issues = report.get_violations_by_severity(severity)
                if severity_issues:
                    lines.extend([f"### {severity.value.title()} Severity", ""])
                    for issue in severity_issues[:20]:
                        filename = os.path.basename(issue.file_path)
                        location_str = issue.qualified_location if (issue.class_name or issue.method_name) else issue.location
                        lines.extend([
                            f"#### `{filename}:{issue.line_number}`",
                            "",
                            f"**Location:** {location_str}",
                            "",
                            f"**Issue:** {issue.description}",
                            "",
                            f"**Remediation:** {issue.remediation}",
                            "",
                        ])

        return "\n".join(lines)
