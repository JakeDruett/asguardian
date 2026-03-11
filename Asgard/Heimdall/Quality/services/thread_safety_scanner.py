"""
Heimdall Thread Safety Scanner Service

Detects thread safety issues in Python code using AST analysis.

Detects:
- Instance attributes accessed by threading.Thread targets that are not initialized in __init__
- Shared mutable collections (list, dict, deque, set) used by thread targets without lock protection
"""

import ast
import os
import json
import fnmatch
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from Asgard.Heimdall.Quality.models.thread_safety_models import (
    ThreadSafetyConfig,
    ThreadSafetyIssue,
    ThreadSafetyIssueType,
    ThreadSafetyReport,
    ThreadSafetySeverity,
)


# Names that indicate mutable shared collections
MUTABLE_COLLECTION_NAMES: Set[str] = {
    "list", "dict", "set", "deque", "defaultdict", "OrderedDict",
    "Counter", "bytearray",
}


def _get_self_attr_assignments(method_node: ast.AST) -> Set[str]:
    """Collect all self.attr names assigned in a method body."""
    assigned: Set[str] = set()
    for node in ast.walk(method_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    assigned.add(target.attr)
        elif isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Attribute)
                and isinstance(node.target.value, ast.Name)
                and node.target.value.id == "self"
            ):
                assigned.add(node.target.attr)
    return assigned


def _get_self_attr_reads(method_node: ast.AST) -> Set[str]:
    """Collect all self.attr names read (loaded) in a method body."""
    reads: Set[str] = set()
    for node in ast.walk(method_node):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
            and isinstance(node.ctx, ast.Load)
        ):
            reads.add(node.attr)
    return reads


def _find_mutable_collection_attrs(method_node: ast.AST) -> Dict[str, int]:
    """Find self.attr assignments to mutable collections. Returns {attr_name: line_no}."""
    mutable: Dict[str, int] = {}
    for node in ast.walk(method_node):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    attr_name = target.attr
                    val = node.value
                    # Direct literal: self.x = [] or self.x = {}
                    if isinstance(val, (ast.List, ast.Dict, ast.Set)):
                        mutable[attr_name] = node.lineno
                    # Constructor call: self.x = list() / dict() / deque() etc.
                    elif isinstance(val, ast.Call):
                        func = val.func
                        if isinstance(func, ast.Name) and func.id in MUTABLE_COLLECTION_NAMES:
                            mutable[attr_name] = node.lineno
                        elif isinstance(func, ast.Attribute) and func.attr in MUTABLE_COLLECTION_NAMES:
                            mutable[attr_name] = node.lineno
    return mutable


def _find_thread_targets(class_node: ast.ClassDef) -> List[Tuple[int, str]]:
    """
    Find threading.Thread(target=self.method) calls in class.
    Returns list of (line_no, method_name).
    """
    targets: List[Tuple[int, str]] = []
    for node in ast.walk(class_node):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        is_thread_call = (
            (isinstance(func, ast.Name) and func.id == "Thread")
            or (isinstance(func, ast.Attribute) and func.attr == "Thread")
        )
        if not is_thread_call:
            continue
        for kw in node.keywords:
            if kw.arg == "target" and isinstance(kw.value, ast.Attribute):
                val = kw.value
                if isinstance(val.value, ast.Name) and val.value.id == "self":
                    targets.append((node.lineno, val.attr))
    return targets


class ThreadSafetyVisitor(ast.NodeVisitor):
    """
    AST visitor that detects thread safety issues.

    Analyzes each ClassDef for:
    - Attributes accessed by thread targets not initialized in __init__
    - Shared mutable collections used by thread targets
    """

    def __init__(self, file_path: str, source_lines: List[str]):
        """
        Initialize the thread safety visitor.

        Args:
            file_path: Path to the file being analyzed
            source_lines: Source code lines for extracting snippets
        """
        self.file_path = file_path
        self.source_lines = source_lines
        self.issues: List[ThreadSafetyIssue] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Analyze each class for thread safety issues."""
        self._analyze_class(node)
        self.generic_visit(node)

    def _analyze_class(self, class_node: ast.ClassDef) -> None:
        """Perform thread safety analysis on a single class."""
        class_name = class_node.name

        # Collect methods by name
        methods: Dict[str, ast.FunctionDef] = {}
        for item in class_node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods[item.name] = item

        # Find threading.Thread targets in this class
        thread_targets = _find_thread_targets(class_node)
        if not thread_targets:
            return

        # Collect attrs initialized in __init__
        init_attrs: Set[str] = set()
        if "__init__" in methods:
            init_attrs = _get_self_attr_assignments(methods["__init__"])

        # Collect all mutable collection assignments (across all methods)
        all_mutable_attrs: Dict[str, int] = {}
        for method_name, method_node in methods.items():
            found = _find_mutable_collection_attrs(method_node)
            for attr, line in found.items():
                if attr not in all_mutable_attrs:
                    all_mutable_attrs[attr] = line

        # For each thread target method, check attribute access
        for thread_line, target_method_name in thread_targets:
            if target_method_name not in methods:
                continue

            target_method = methods[target_method_name]
            attrs_read = _get_self_attr_reads(target_method)

            for attr_name in attrs_read:
                if attr_name not in init_attrs:
                    # Attribute read by thread target but not initialized in __init__
                    if attr_name in all_mutable_attrs:
                        # Shared mutable collection - MEDIUM
                        self.issues.append(ThreadSafetyIssue(
                            file_path=self.file_path,
                            line_number=all_mutable_attrs[attr_name],
                            class_name=class_name,
                            issue_type=ThreadSafetyIssueType.SHARED_MUTABLE_COLLECTION,
                            severity=ThreadSafetySeverity.MEDIUM,
                            description=(
                                f"Shared mutable collection 'self.{attr_name}' is accessed "
                                f"by thread target '{target_method_name}' without lock protection"
                            ),
                            attribute_name=attr_name,
                            thread_target_method=target_method_name,
                            remediation=(
                                f"Protect 'self.{attr_name}' with a threading.Lock(). "
                                f"Initialize it in __init__ and acquire the lock before access."
                            ),
                        ))
                    else:
                        # Attribute not initialized in __init__ - HIGH
                        self.issues.append(ThreadSafetyIssue(
                            file_path=self.file_path,
                            line_number=thread_line,
                            class_name=class_name,
                            issue_type=ThreadSafetyIssueType.UNINITIALIZED_ATTR,
                            severity=ThreadSafetySeverity.HIGH,
                            description=(
                                f"Thread target '{target_method_name}' accesses 'self.{attr_name}' "
                                f"which is not initialized in __init__. Thread may run before "
                                f"attribute is set."
                            ),
                            attribute_name=attr_name,
                            thread_target_method=target_method_name,
                            remediation=(
                                f"Initialize 'self.{attr_name}' in __init__ before starting threads. "
                                f"This ensures the attribute exists when the thread begins execution."
                            ),
                        ))


class ThreadSafetyScanner:
    """
    Scans Python files for thread safety issues.

    Detects patterns that can cause race conditions or crashes in
    multi-threaded code, particularly around threading.Thread usage.

    Usage:
        scanner = ThreadSafetyScanner()
        report = scanner.analyze(Path("./src"))

        for issue in report.detected_issues:
            print(f"{issue.location}: {issue.description}")
    """

    def __init__(self, config: Optional[ThreadSafetyConfig] = None):
        """
        Initialize thread safety scanner.

        Args:
            config: Configuration for scanning. If None, uses defaults.
        """
        self.config = config or ThreadSafetyConfig()

    def analyze(self, path: Path) -> ThreadSafetyReport:
        """
        Analyze a file or directory for thread safety issues.

        Args:
            path: Path to file or directory to analyze

        Returns:
            ThreadSafetyReport with all detected issues

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = ThreadSafetyReport(scan_path=str(path))

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

    def _analyze_file(self, file_path: Path, root_path: Path) -> List[ThreadSafetyIssue]:
        """Analyze a single file for thread safety issues."""
        try:
            source = file_path.read_text(encoding="utf-8")
            source_lines = source.splitlines()
            tree = ast.parse(source)

            visitor = ThreadSafetyVisitor(
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

    def _analyze_directory(self, directory: Path, report: ThreadSafetyReport) -> None:
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
            severity = ThreadSafetySeverity(severity)
        levels = {
            ThreadSafetySeverity.MEDIUM: 1,
            ThreadSafetySeverity.HIGH: 2,
        }
        return levels.get(severity, 1)

    def generate_report(self, report: ThreadSafetyReport, output_format: str = "text") -> str:
        """
        Generate formatted thread safety report.

        Args:
            report: ThreadSafetyReport to format
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

    def _generate_text_report(self, report: ThreadSafetyReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "THREAD SAFETY VIOLATIONS REPORT",
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
            for severity in [ThreadSafetySeverity.HIGH, ThreadSafetySeverity.MEDIUM]:
                count = report.violations_by_severity.get(severity.value, 0)
                if count > 0:
                    lines.append(f"  {severity.value.upper()}: {count}")

            lines.extend(["", "By Type:"])
            for issue_type in ThreadSafetyIssueType:
                count = report.violations_by_type.get(issue_type.value, 0)
                if count > 0:
                    lines.append(f"  {issue_type.value.replace('_', ' ').title()}: {count}")

            if report.most_problematic_files:
                lines.extend(["", "Most Problematic Files:", "-" * 40])
                for file_path, count in report.most_problematic_files[:5]:
                    filename = os.path.basename(file_path)
                    lines.append(f"  {filename}: {count} violations")

            lines.extend(["", "VIOLATIONS", "-" * 40])

            for severity in [ThreadSafetySeverity.HIGH, ThreadSafetySeverity.MEDIUM]:
                severity_issues = report.get_violations_by_severity(severity)
                if severity_issues:
                    lines.extend(["", f"[{severity.value.upper()}]"])
                    for issue in severity_issues:
                        lines.append(f"  {issue.location} ({issue.class_name})")
                        lines.append(f"    {issue.description}")
                        lines.append(f"    Fix: {issue.remediation}")
                        lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self, report: ThreadSafetyReport) -> str:
        """Generate JSON report."""
        issues_data = []
        for issue in report.detected_issues:
            issues_data.append({
                "file_path": issue.file_path,
                "relative_path": issue.relative_path,
                "line_number": issue.line_number,
                "class_name": issue.class_name,
                "issue_type": issue.issue_type if isinstance(issue.issue_type, str) else issue.issue_type.value,
                "severity": issue.severity if isinstance(issue.severity, str) else issue.severity.value,
                "description": issue.description,
                "attribute_name": issue.attribute_name,
                "thread_target_method": issue.thread_target_method,
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

    def _generate_markdown_report(self, report: ThreadSafetyReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Thread Safety Violations Report",
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
            for severity in [ThreadSafetySeverity.HIGH, ThreadSafetySeverity.MEDIUM]:
                count = report.violations_by_severity.get(severity.value, 0)
                lines.append(f"| {severity.value.title()} | {count} |")

            lines.extend([
                "",
                "### By Type",
                "",
                "| Type | Count |",
                "|------|-------|",
            ])
            for issue_type in ThreadSafetyIssueType:
                count = report.violations_by_type.get(issue_type.value, 0)
                if count > 0:
                    lines.append(f"| {issue_type.value.replace('_', ' ').title()} | {count} |")

            if report.most_problematic_files:
                lines.extend(["", "## Most Problematic Files", ""])
                for file_path, count in report.most_problematic_files[:10]:
                    filename = os.path.basename(file_path)
                    lines.append(f"- `{filename}`: {count} violations")

            lines.extend(["", "## Violations", ""])

            for severity in [ThreadSafetySeverity.HIGH, ThreadSafetySeverity.MEDIUM]:
                severity_issues = report.get_violations_by_severity(severity)
                if severity_issues:
                    lines.extend([f"### {severity.value.title()} Severity", ""])
                    for issue in severity_issues[:20]:
                        filename = os.path.basename(issue.file_path)
                        lines.extend([
                            f"#### `{filename}:{issue.line_number}` ({issue.class_name})",
                            "",
                            f"**Issue:** {issue.description}",
                            "",
                            f"**Remediation:** {issue.remediation}",
                            "",
                        ])

        return "\n".join(lines)
