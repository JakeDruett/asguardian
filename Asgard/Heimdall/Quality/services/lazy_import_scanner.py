"""
Heimdall Lazy Import Scanner Service

Detects imports that are not at the top of the file, which violates
the coding standard that ALL imports MUST be at the top of the file.

Detects:
- Imports inside functions
- Imports inside class methods
- Imports inside conditional blocks (if/else)
- Imports inside try/except blocks
- Imports inside loops (for/while)
- Imports inside with blocks
"""

import ast
import os
import json
import fnmatch
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from collections import defaultdict

from Asgard.Heimdall.Quality.models.lazy_import_models import (
    LazyImport,
    LazyImportConfig,
    LazyImportReport,
    LazyImportSeverity,
    LazyImportType,
)


class LazyImportVisitor(ast.NodeVisitor):
    """
    AST visitor that detects imports not at module level.

    Walks the AST and identifies import statements that appear inside:
    - Functions (def)
    - Async functions (async def)
    - Class methods
    - Conditional blocks (if/elif/else)
    - Try/except blocks
    - Loops (for/while)
    - With blocks
    """

    def __init__(self, file_path: str, source_lines: List[str]):
        """
        Initialize the lazy import visitor.

        Args:
            file_path: Path to the file being analyzed
            source_lines: Source code lines for extracting import text
        """
        self.file_path = file_path
        self.source_lines = source_lines
        self.lazy_imports: List[LazyImport] = []
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        self.context_stack: List[str] = []  # Track nested contexts

    def _get_import_statement(self, node: ast.AST) -> str:
        """Extract the import statement text from source."""
        if node.lineno <= len(self.source_lines):
            line = self.source_lines[node.lineno - 1].strip()
            return line
        return ""

    def _determine_severity(self, import_type: LazyImportType) -> LazyImportSeverity:
        """Determine severity based on import type."""
        high_severity = {
            LazyImportType.FUNCTION,
            LazyImportType.METHOD,
        }
        medium_severity = {
            LazyImportType.CONDITIONAL,
            LazyImportType.TRY_EXCEPT,
        }

        if import_type in high_severity:
            return LazyImportSeverity.HIGH
        elif import_type in medium_severity:
            return LazyImportSeverity.MEDIUM
        return LazyImportSeverity.LOW

    def _get_context_description(self, import_type: LazyImportType) -> str:
        """Generate a human-readable context description."""
        descriptions = {
            LazyImportType.FUNCTION: "inside function",
            LazyImportType.METHOD: "inside class method",
            LazyImportType.CONDITIONAL: "inside conditional block (if/elif/else)",
            LazyImportType.TRY_EXCEPT: "inside try/except block",
            LazyImportType.LOOP: "inside loop (for/while)",
            LazyImportType.WITH_BLOCK: "inside with block",
        }
        base = descriptions.get(import_type, "in non-module-level scope")

        if self.current_class and self.current_function:
            return f"{base} '{self.current_class}.{self.current_function}'"
        elif self.current_function:
            return f"{base} '{self.current_function}'"
        return base

    def _record_lazy_import(self, node: ast.AST, import_type: LazyImportType) -> None:
        """Record a lazy import violation."""
        import_stmt = self._get_import_statement(node)
        severity = self._determine_severity(import_type)

        self.lazy_imports.append(LazyImport(
            file_path=self.file_path,
            line_number=node.lineno,
            import_statement=import_stmt,
            import_type=import_type,
            severity=severity,
            containing_function=self.current_function,
            containing_class=self.current_class,
            context_description=self._get_context_description(import_type),
        ))

    def _check_import_node(self, node: ast.AST) -> None:
        """Check if an import node is in a non-module-level context."""
        if not self.context_stack:
            # Module level import - this is fine
            return

        # Determine import type based on context
        current_context = self.context_stack[-1]

        if current_context == "method":
            import_type = LazyImportType.METHOD
        elif current_context == "function":
            import_type = LazyImportType.FUNCTION
        elif current_context == "conditional":
            import_type = LazyImportType.CONDITIONAL
        elif current_context == "try_except":
            import_type = LazyImportType.TRY_EXCEPT
        elif current_context == "loop":
            import_type = LazyImportType.LOOP
        elif current_context == "with_block":
            import_type = LazyImportType.WITH_BLOCK
        else:
            import_type = LazyImportType.FUNCTION

        self._record_lazy_import(node, import_type)

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import X' statements."""
        self._check_import_node(node)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from X import Y' statements."""
        self._check_import_node(node)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition to track class context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition to track function context."""
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition to track function context."""
        self._visit_function(node)

    def _visit_function(self, node) -> None:
        """Common handler for function and async function definitions."""
        old_function = self.current_function
        self.current_function = node.name

        # Determine if this is a method or function
        context = "method" if self.current_class else "function"
        self.context_stack.append(context)

        self.generic_visit(node)

        self.context_stack.pop()
        self.current_function = old_function

    def _is_type_checking_block(self, node: ast.If) -> bool:
        """Check if this is an 'if TYPE_CHECKING:' block."""
        # Check for `if TYPE_CHECKING:`
        if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
            return True
        # Check for `if typing.TYPE_CHECKING:`
        if isinstance(node.test, ast.Attribute):
            if node.test.attr == "TYPE_CHECKING":
                return True
        return False

    def visit_If(self, node: ast.If) -> None:
        """Visit if statement to track conditional context."""
        # Allow imports inside TYPE_CHECKING blocks (valid pattern for type hints)
        if self._is_type_checking_block(node):
            return  # Skip processing this block entirely

        self.context_stack.append("conditional")
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_Try(self, node: ast.Try) -> None:
        """Visit try statement to track try/except context."""
        self.context_stack.append("try_except")
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_For(self, node: ast.For) -> None:
        """Visit for loop to track loop context."""
        self.context_stack.append("loop")
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_While(self, node: ast.While) -> None:
        """Visit while loop to track loop context."""
        self.context_stack.append("loop")
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_With(self, node: ast.With) -> None:
        """Visit with statement to track with block context."""
        self.context_stack.append("with_block")
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        """Visit async with statement to track with block context."""
        self.context_stack.append("with_block")
        self.generic_visit(node)
        self.context_stack.pop()

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        """Visit async for loop to track loop context."""
        self.context_stack.append("loop")
        self.generic_visit(node)
        self.context_stack.pop()


class LazyImportScanner:
    """
    Scans Python files for lazy imports (imports not at module level).

    Detects imports inside functions, methods, conditionals, try/except blocks,
    loops, and with blocks - all of which violate the coding standard.

    Usage:
        scanner = LazyImportScanner()
        report = scanner.analyze(Path("./src"))

        for violation in report.detected_imports:
            print(f"{violation.location}: {violation.import_statement}")
    """

    def __init__(self, config: Optional[LazyImportConfig] = None):
        """
        Initialize lazy import scanner.

        Args:
            config: Configuration for scanning. If None, uses defaults.
        """
        self.config = config or LazyImportConfig()

    def analyze(self, path: Path) -> LazyImportReport:
        """
        Analyze a file or directory for lazy imports.

        Args:
            path: Path to file or directory to analyze

        Returns:
            LazyImportReport with all detected violations

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = LazyImportReport(scan_path=str(path))

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
        for violation in report.detected_imports:
            file_violation_counts[violation.file_path] += 1

        report.most_problematic_files = sorted(
            file_violation_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        return report

    def analyze_single_file(self, file_path: Path) -> LazyImportReport:
        """
        Analyze a single file for lazy imports.

        Args:
            file_path: Path to Python file

        Returns:
            LazyImportReport with detected violations
        """
        return self.analyze(file_path)

    def _analyze_file(self, file_path: Path, root_path: Path) -> List[LazyImport]:
        """
        Analyze a single file for lazy imports.

        Args:
            file_path: Path to Python file
            root_path: Root path for calculating relative paths

        Returns:
            List of detected lazy imports
        """
        try:
            source = file_path.read_text(encoding="utf-8")
            source_lines = source.splitlines()
            tree = ast.parse(source)

            visitor = LazyImportVisitor(
                file_path=str(file_path.absolute()),
                source_lines=source_lines,
            )
            visitor.visit(tree)

            # Set relative paths
            for lazy_import in visitor.lazy_imports:
                try:
                    lazy_import.relative_path = str(file_path.relative_to(root_path))
                except ValueError:
                    lazy_import.relative_path = file_path.name

            # Filter by severity
            filtered = [
                v for v in visitor.lazy_imports
                if self._severity_level(v.severity) >= self._severity_level(self.config.severity_filter)
            ]

            return filtered

        except SyntaxError:
            # Cannot parse file - skip it
            return []
        except Exception:
            # Other errors - skip file
            return []

    def _analyze_directory(self, directory: Path, report: LazyImportReport) -> None:
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
                # Check if file should be analyzed
                if not self._should_analyze_file(file):
                    continue

                # Check exclude patterns
                if any(self._matches_pattern(file, pattern) for pattern in self.config.exclude_patterns):
                    continue

                # Check test file inclusion
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
            severity = LazyImportSeverity(severity)
        levels = {
            LazyImportSeverity.LOW: 1,
            LazyImportSeverity.MEDIUM: 2,
            LazyImportSeverity.HIGH: 3,
        }
        return levels.get(severity, 1)

    def generate_report(self, report: LazyImportReport, output_format: str = "text") -> str:
        """
        Generate formatted lazy import report.

        Args:
            report: LazyImportReport to format
            output_format: Report format (text, json, markdown)

        Returns:
            Formatted report string

        Raises:
            ValueError: If output format is not supported
        """
        format_lower = output_format.lower()
        if format_lower == "json":
            return self._generate_json_report(report)
        elif format_lower == "markdown" or format_lower == "md":
            return self._generate_markdown_report(report)
        elif format_lower == "text":
            return self._generate_text_report(report)
        else:
            raise ValueError(f"Unsupported format: {output_format}. Use: text, json, markdown")

    def _generate_text_report(self, report: LazyImportReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "LAZY IMPORT VIOLATIONS REPORT",
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
            lines.extend(["By Severity:"])
            for severity in [LazyImportSeverity.HIGH, LazyImportSeverity.MEDIUM, LazyImportSeverity.LOW]:
                count = report.violations_by_severity.get(severity.value, 0)
                if count > 0:
                    lines.append(f"  {severity.value.upper()}: {count}")

            lines.extend(["", "By Type:"])
            for import_type in LazyImportType:
                count = report.violations_by_type.get(import_type.value, 0)
                if count > 0:
                    lines.append(f"  {import_type.value.replace('_', ' ').title()}: {count}")

            if report.most_problematic_files:
                lines.extend(["", "Most Problematic Files:", "-" * 40])
                for file_path, count in report.most_problematic_files[:5]:
                    filename = os.path.basename(file_path)
                    lines.append(f"  {filename}: {count} violations")

            lines.extend(["", "VIOLATIONS", "-" * 40])

            # Group by severity
            for severity in [LazyImportSeverity.HIGH, LazyImportSeverity.MEDIUM, LazyImportSeverity.LOW]:
                severity_violations = report.get_violations_by_severity(severity)
                if severity_violations:
                    lines.extend(["", f"[{severity.value.upper()}]"])
                    for violation in severity_violations:
                        lines.append(f"  {violation.location}")
                        lines.append(f"    Import: {violation.import_statement}")
                        lines.append(f"    Context: {violation.context_description}")
                        lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self, report: LazyImportReport) -> str:
        """Generate JSON report."""
        violations_data = []
        for v in report.detected_imports:
            violations_data.append({
                "file_path": v.file_path,
                "relative_path": v.relative_path,
                "line_number": v.line_number,
                "import_statement": v.import_statement,
                "import_type": v.import_type if isinstance(v.import_type, str) else v.import_type.value,
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
                {"file": file_path, "violation_count": count}
                for file_path, count in report.most_problematic_files
            ],
        }

        return json.dumps(report_data, indent=2)

    def _generate_markdown_report(self, report: LazyImportReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Lazy Import Violations Report",
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
            for severity in [LazyImportSeverity.HIGH, LazyImportSeverity.MEDIUM, LazyImportSeverity.LOW]:
                count = report.violations_by_severity.get(severity.value, 0)
                lines.append(f"| {severity.value.title()} | {count} |")

            lines.extend([
                "",
                "### By Type",
                "",
                "| Type | Count |",
                "|------|-------|",
            ])
            for import_type in LazyImportType:
                count = report.violations_by_type.get(import_type.value, 0)
                if count > 0:
                    lines.append(f"| {import_type.value.replace('_', ' ').title()} | {count} |")

            if report.most_problematic_files:
                lines.extend(["", "## Most Problematic Files", ""])
                for file_path, count in report.most_problematic_files[:10]:
                    filename = os.path.basename(file_path)
                    lines.append(f"- `{filename}`: {count} violations")

            lines.extend(["", "## Violations", ""])

            for severity in [LazyImportSeverity.HIGH, LazyImportSeverity.MEDIUM, LazyImportSeverity.LOW]:
                severity_violations = report.get_violations_by_severity(severity)
                if severity_violations:
                    lines.extend([f"### {severity.value.title()} Severity", ""])

                    for v in severity_violations[:20]:
                        filename = os.path.basename(v.file_path)
                        lines.extend([
                            f"#### `{filename}:{v.line_number}`",
                            "",
                            f"**Import:** `{v.import_statement}`",
                            "",
                            f"**Context:** {v.context_description}",
                            "",
                            f"**Remediation:** {v.remediation}",
                            "",
                        ])

        return "\n".join(lines)
