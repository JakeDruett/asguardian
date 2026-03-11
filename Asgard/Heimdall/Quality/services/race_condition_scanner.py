"""
Heimdall Race Condition Detector Service

Detects race condition patterns in Python code using AST analysis.

Detects:
- thread.start() called before the thread reference is stored on self (unreliable join)
- self.attr assignment after thread.start() (thread may read stale state)
- Check-then-act patterns on shared self attributes without lock protection
"""

import ast
import os
import json
import fnmatch
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from Asgard.Heimdall.Quality.models.race_condition_models import (
    RaceConditionConfig,
    RaceConditionIssue,
    RaceConditionReport,
    RaceConditionSeverity,
    RaceConditionType,
)


# Names that indicate lock-like context managers
LOCK_CONTEXT_NAMES: Set[str] = {
    "Lock", "RLock", "Semaphore", "BoundedSemaphore",
    "Condition", "Event", "lock", "_lock", "mutex",
}


def _is_thread_call(call_node: ast.Call) -> bool:
    """Check if a Call node is a threading.Thread() or Thread() instantiation."""
    func = call_node.func
    return (
        (isinstance(func, ast.Name) and func.id == "Thread")
        or (isinstance(func, ast.Attribute) and func.attr == "Thread")
    )


def _get_call_name(call_node: ast.Call) -> Optional[str]:
    """Get the name of the function being called (e.g. 'start', 'join')."""
    if isinstance(call_node.func, ast.Attribute):
        return call_node.func.attr
    return None


def _get_call_receiver_name(call_node: ast.Call) -> Optional[str]:
    """Get the variable name the method is called on (e.g. 't' in t.start())."""
    if isinstance(call_node.func, ast.Attribute):
        if isinstance(call_node.func.value, ast.Name):
            return call_node.func.value.id
    return None


def _is_self_attr_assignment(node: ast.stmt) -> Optional[str]:
    """
    Check if a statement is a self.attr assignment.
    Returns the attribute name if it is, None otherwise.
    """
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                return target.attr
    elif isinstance(node, ast.AnnAssign):
        if (
            isinstance(node.target, ast.Attribute)
            and isinstance(node.target.value, ast.Name)
            and node.target.value.id == "self"
        ):
            return node.target.attr
    return None


def _is_self_attr_to_var(node: ast.stmt) -> Optional[Tuple[str, str]]:
    """
    Check if statement is 'self.x = var_name'.
    Returns (attr_name, var_name) if so, None otherwise.
    """
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ):
                attr_name = target.attr
                if isinstance(node.value, ast.Name):
                    return (attr_name, node.value.id)
    return None


def _has_lock_enclosure(if_node: ast.If, parent_stmts: List[ast.stmt]) -> bool:
    """
    Check if an if statement is enclosed in a with-lock block.
    Examines the parent statement list for a With block that contains this if.
    """
    for stmt in parent_stmts:
        if not isinstance(stmt, ast.With):
            continue
        for item in stmt.items:
            ctx_expr = item.context_expr
            # Check for with self.lock: / with self._lock: / with lock:
            if isinstance(ctx_expr, ast.Name) and ctx_expr.id in LOCK_CONTEXT_NAMES:
                if _contains_node(stmt, if_node):
                    return True
            elif isinstance(ctx_expr, ast.Attribute) and ctx_expr.attr in LOCK_CONTEXT_NAMES:
                if _contains_node(stmt, if_node):
                    return True
            # Check for with self.lock: / self._lock:
            elif (
                isinstance(ctx_expr, ast.Attribute)
                and isinstance(ctx_expr.value, ast.Name)
                and ctx_expr.value.id == "self"
            ):
                if _contains_node(stmt, if_node):
                    return True
    return False


def _contains_node(parent: ast.AST, target: ast.AST) -> bool:
    """Check if target node is contained anywhere within parent node."""
    for node in ast.walk(parent):
        if node is target:
            return True
    return False


def _self_attr_accessed_in_body(body: List[ast.stmt], attr_name: str) -> bool:
    """Check if self.attr_name is accessed (read or called) within a list of statements."""
    for stmt in body:
        for node in ast.walk(stmt):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id == "self"
                and node.attr == attr_name
            ):
                return True
    return False


class RaceConditionVisitor(ast.NodeVisitor):
    """
    AST visitor that detects race condition patterns.

    Analyzes method bodies for:
    - thread.start() before self reference is stored (unreliable join)
    - self.attr assignment after thread.start()
    - check-then-act patterns without lock protection
    """

    def __init__(self, file_path: str, source_lines: List[str]):
        """
        Initialize the race condition visitor.

        Args:
            file_path: Path to the file being analyzed
            source_lines: Source code lines for context
        """
        self.file_path = file_path
        self.source_lines = source_lines
        self.issues: List[RaceConditionIssue] = []
        self.current_class: Optional[str] = None
        self.current_method: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Track class context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Analyze function/method body for race conditions."""
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Analyze async function body for race conditions."""
        self._visit_function(node)

    def _visit_function(self, node) -> None:
        """Common handler for function and async function analysis."""
        old_method = self.current_method
        self.current_method = node.name
        self._analyze_method_body(node.body)
        self.generic_visit(node)
        self.current_method = old_method

    def _analyze_method_body(self, body: List[ast.stmt]) -> None:
        """
        Analyze a method body for race conditions.

        Scans for:
        1. thread.start() before self._thread = thread (START_BEFORE_STORE)
        2. self.attr = value after thread.start() (ASSIGN_AFTER_START)
        3. if self.x: self.x.do() without lock (CHECK_THEN_ACT)
        """
        # Track thread variable names and their start lines
        thread_vars: Dict[str, int] = {}  # var_name -> line where Thread() was created
        thread_started: Dict[str, int] = {}  # var_name -> line where .start() was called
        thread_stored_on_self: Set[str] = set()  # var names stored on self before start

        # First pass: find Thread() assignments and pre-start self assignments
        for stmt in body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name) and isinstance(stmt.value, ast.Call):
                        if _is_thread_call(stmt.value):
                            thread_vars[target.id] = stmt.lineno

        # Second pass: scan ordered statements for race patterns
        for i, stmt in enumerate(body):
            # Detect thread.start() calls
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                call = stmt.value
                method_name = _get_call_name(call)
                receiver = _get_call_receiver_name(call)

                if method_name == "start" and receiver and receiver in thread_vars:
                    thread_started[receiver] = stmt.lineno

                    # Check remaining statements after this start() call
                    remaining_stmts = body[i + 1:]
                    for later_stmt in remaining_stmts:
                        # Pattern 1: self._thread = thread after thread.start()
                        stored = _is_self_attr_to_var(later_stmt)
                        if stored:
                            self_attr, var_name = stored
                            if var_name == receiver:
                                self.issues.append(RaceConditionIssue(
                                    file_path=self.file_path,
                                    line_number=stmt.lineno,
                                    class_name=self.current_class,
                                    method_name=self.current_method,
                                    race_type=RaceConditionType.START_BEFORE_STORE,
                                    severity=RaceConditionSeverity.HIGH,
                                    description=(
                                        f"Thread '{receiver}' is started at line {stmt.lineno} before "
                                        f"its reference is stored as 'self.{self_attr}' at line "
                                        f"{later_stmt.lineno}. Calling join() before the assignment "
                                        f"completes is unreliable."
                                    ),
                                    remediation=(
                                        f"Store the thread reference 'self.{self_attr} = {receiver}' "
                                        f"BEFORE calling '{receiver}.start()'."
                                    ),
                                ))

                        # Pattern 2: any self.attr = value after thread.start()
                        attr_name = _is_self_attr_assignment(later_stmt)
                        if attr_name is not None:
                            # Only flag if not a thread store (already caught above)
                            stored_check = _is_self_attr_to_var(later_stmt)
                            if not stored_check or stored_check[1] != receiver:
                                self.issues.append(RaceConditionIssue(
                                    file_path=self.file_path,
                                    line_number=later_stmt.lineno,
                                    class_name=self.current_class,
                                    method_name=self.current_method,
                                    race_type=RaceConditionType.ASSIGN_AFTER_START,
                                    severity=RaceConditionSeverity.HIGH,
                                    description=(
                                        f"'self.{attr_name}' is assigned at line {later_stmt.lineno} "
                                        f"after thread '{receiver}' was started at line {stmt.lineno}. "
                                        f"The thread may read a stale or missing value of this attribute."
                                    ),
                                    remediation=(
                                        f"Set 'self.{attr_name}' BEFORE calling '{receiver}.start()', "
                                        f"or use a threading.Lock() to synchronize access."
                                    ),
                                ))

            # Pattern 3: check-then-act on self.attr without lock
            if isinstance(stmt, ast.If):
                self._check_check_then_act(stmt, body)

    def _check_check_then_act(self, if_node: ast.If, parent_body: List[ast.stmt]) -> None:
        """
        Detect check-then-act race on self attributes.

        Flags patterns like:
            if self.x:
                self.x.do_something()
        without a surrounding lock context.
        """
        test = if_node.test

        # Find the self.attr being tested
        checked_attr: Optional[str] = None

        # Pattern: if self.x:
        if (
            isinstance(test, ast.Attribute)
            and isinstance(test.value, ast.Name)
            and test.value.id == "self"
        ):
            checked_attr = test.attr

        # Pattern: if self.x is not None:
        elif isinstance(test, ast.Compare):
            left = test.left
            if (
                isinstance(left, ast.Attribute)
                and isinstance(left.value, ast.Name)
                and left.value.id == "self"
            ):
                checked_attr = left.attr

        if checked_attr is None:
            return

        # Check if the body accesses the same self.attr
        if not _self_attr_accessed_in_body(if_node.body, checked_attr):
            return

        # Check if this if is inside a lock context
        if _has_lock_enclosure(if_node, parent_body):
            return

        self.issues.append(RaceConditionIssue(
            file_path=self.file_path,
            line_number=if_node.lineno,
            class_name=self.current_class,
            method_name=self.current_method,
            race_type=RaceConditionType.CHECK_THEN_ACT,
            severity=RaceConditionSeverity.HIGH,
            description=(
                f"Check-then-act on 'self.{checked_attr}' at line {if_node.lineno} "
                f"without lock protection. Another thread may modify 'self.{checked_attr}' "
                f"between the check and the action."
            ),
            remediation=(
                f"Wrap the check and action in a 'with self._lock:' block to prevent "
                f"another thread from modifying 'self.{checked_attr}' between the check and act."
            ),
        ))


class RaceConditionScanner:
    """
    Scans Python files for race condition patterns.

    Detects common race conditions in multi-threaded Python code,
    particularly around threading.Thread lifecycle and shared state.

    Usage:
        scanner = RaceConditionScanner()
        report = scanner.analyze(Path("./src"))

        for issue in report.detected_issues:
            print(f"{issue.location}: {issue.description}")
    """

    def __init__(self, config: Optional[RaceConditionConfig] = None):
        """
        Initialize race condition scanner.

        Args:
            config: Configuration for scanning. If None, uses defaults.
        """
        self.config = config or RaceConditionConfig()

    def analyze(self, path: Path) -> RaceConditionReport:
        """
        Analyze a file or directory for race condition patterns.

        Args:
            path: Path to file or directory to analyze

        Returns:
            RaceConditionReport with all detected issues

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = RaceConditionReport(scan_path=str(path))

        if path.is_file():
            issues = self._analyze_file(path, path.parent)
            for issue in issues:
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

    def _analyze_file(self, file_path: Path, root_path: Path) -> List[RaceConditionIssue]:
        """Analyze a single file for race condition patterns."""
        try:
            source = file_path.read_text(encoding="utf-8")
            source_lines = source.splitlines()
            tree = ast.parse(source)

            visitor = RaceConditionVisitor(
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

    def _analyze_directory(self, directory: Path, report: RaceConditionReport) -> None:
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

    def generate_report(self, report: RaceConditionReport, output_format: str = "text") -> str:
        """
        Generate formatted race condition report.

        Args:
            report: RaceConditionReport to format
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

    def _generate_text_report(self, report: RaceConditionReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "RACE CONDITION VIOLATIONS REPORT",
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
            lines.append("By Type:")
            for race_type in RaceConditionType:
                count = report.violations_by_type.get(race_type.value, 0)
                if count > 0:
                    lines.append(f"  {race_type.value.replace('_', ' ').title()}: {count}")

            if report.most_problematic_files:
                lines.extend(["", "Most Problematic Files:", "-" * 40])
                for file_path, count in report.most_problematic_files[:5]:
                    filename = os.path.basename(file_path)
                    lines.append(f"  {filename}: {count} violations")

            lines.extend(["", "VIOLATIONS", "-" * 40])

            for race_type in RaceConditionType:
                type_issues = report.get_violations_by_type(race_type)
                if type_issues:
                    lines.extend(["", f"[{race_type.value.replace('_', ' ').upper()}]"])
                    for issue in type_issues:
                        loc = issue.qualified_location if (issue.class_name or issue.method_name) else issue.location
                        lines.append(f"  {loc}")
                        lines.append(f"    {issue.description}")
                        lines.append(f"    Fix: {issue.remediation}")
                        lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self, report: RaceConditionReport) -> str:
        """Generate JSON report."""
        issues_data = []
        for issue in report.detected_issues:
            issues_data.append({
                "file_path": issue.file_path,
                "relative_path": issue.relative_path,
                "line_number": issue.line_number,
                "class_name": issue.class_name,
                "method_name": issue.method_name,
                "race_type": issue.race_type if isinstance(issue.race_type, str) else issue.race_type.value,
                "severity": issue.severity if isinstance(issue.severity, str) else issue.severity.value,
                "description": issue.description,
                "code_snippet": issue.code_snippet,
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

    def _generate_markdown_report(self, report: RaceConditionReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Race Condition Violations Report",
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
            for race_type in RaceConditionType:
                count = report.violations_by_type.get(race_type.value, 0)
                if count > 0:
                    lines.append(f"| {race_type.value.replace('_', ' ').title()} | {count} |")

            if report.most_problematic_files:
                lines.extend(["", "## Most Problematic Files", ""])
                for file_path, count in report.most_problematic_files[:10]:
                    filename = os.path.basename(file_path)
                    lines.append(f"- `{filename}`: {count} violations")

            lines.extend(["", "## Violations", ""])

            for race_type in RaceConditionType:
                type_issues = report.get_violations_by_type(race_type)
                if type_issues:
                    lines.extend([
                        f"### {race_type.value.replace('_', ' ').title()}",
                        "",
                    ])
                    for issue in type_issues[:20]:
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
