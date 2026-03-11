"""
Heimdall Library Usage Scanner Service

Detects forbidden library imports that should use wrapper libraries instead.
"""

import ast
import fnmatch
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from Asgard.Heimdall.Quality.models.library_usage_models import (
    ForbiddenImportConfig,
    ForbiddenImportReport,
    ForbiddenImportSeverity,
    ForbiddenImportViolation,
)


class ForbiddenImportVisitor(ast.NodeVisitor):
    """
    AST visitor that detects forbidden library imports.

    Walks the AST and identifies import statements for modules that
    should be using wrapper libraries instead.
    """

    def __init__(
        self,
        file_path: str,
        source_lines: List[str],
        forbidden_modules: Dict[str, str],
        default_severity: ForbiddenImportSeverity,
    ):
        """
        Initialize the forbidden import visitor.

        Args:
            file_path: Path to the file being analyzed
            source_lines: Source code lines for extracting context
            forbidden_modules: Mapping of forbidden module names to remediation
            default_severity: Default severity for violations
        """
        self.file_path = file_path
        self.source_lines = source_lines
        self.forbidden_modules = forbidden_modules
        self.default_severity = default_severity
        self.violations: List[ForbiddenImportViolation] = []

    def _get_code_snippet(self, line_number: int, context: int = 2) -> str:
        """Extract code snippet around the line."""
        start = max(0, line_number - context - 1)
        end = min(len(self.source_lines), line_number + context)
        lines = self.source_lines[start:end]
        return "\n".join(lines)

    def _get_import_statement(self, node: ast.AST) -> str:
        """Extract the import statement text from source."""
        if node.lineno <= len(self.source_lines):
            line = self.source_lines[node.lineno - 1].strip()
            return line
        return ""

    def _check_module_forbidden(self, module_name: str) -> Optional[str]:
        """
        Check if a module name is forbidden.

        Returns the remediation message if forbidden, None otherwise.
        """
        if not module_name:
            return None

        # Check exact match
        if module_name in self.forbidden_modules:
            return self.forbidden_modules[module_name]

        # Check if it's a submodule of a forbidden module
        for forbidden, remediation in self.forbidden_modules.items():
            if module_name.startswith(f"{forbidden}."):
                return remediation

        return None

    def _record_violation(
        self,
        node: ast.AST,
        module_name: str,
        remediation: str,
    ) -> None:
        """Record a forbidden import violation."""
        self.violations.append(ForbiddenImportViolation(
            file_path=self.file_path,
            line_number=node.lineno,
            column=node.col_offset,
            import_statement=self._get_import_statement(node),
            module_name=module_name,
            severity=self.default_severity,
            remediation=remediation,
            code_snippet=self._get_code_snippet(node.lineno),
        ))

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import X' statements."""
        for alias in node.names:
            module_name = alias.name
            remediation = self._check_module_forbidden(module_name)
            if remediation:
                self._record_violation(node, module_name, remediation)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from X import Y' statements."""
        if node.module:
            remediation = self._check_module_forbidden(node.module)
            if remediation:
                self._record_violation(node, node.module, remediation)
        self.generic_visit(node)


class LibraryUsageScanner:
    """
    Scans Python files for forbidden library imports.

    Detects imports of libraries that should be using wrapper libraries
    instead of direct imports.

    Usage:
        scanner = LibraryUsageScanner()
        report = scanner.analyze(Path("./src"))

        for violation in report.detected_violations:
            print(f"{violation.location}: {violation.module_name}")
    """

    def __init__(self, config: Optional[ForbiddenImportConfig] = None):
        """
        Initialize library usage scanner.

        Args:
            config: Configuration for scanning. If None, uses defaults.
        """
        self.config = config or ForbiddenImportConfig()

    def analyze(self, path: Path) -> ForbiddenImportReport:
        """
        Analyze a file or directory for forbidden imports.

        Args:
            path: Path to file or directory to analyze

        Returns:
            ForbiddenImportReport with all detected violations

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = ForbiddenImportReport(scan_path=str(path))

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

    def _is_allowed_path(self, file_path: Path) -> bool:
        """Check if file is in an allowed path (wrapper implementations)."""
        file_str = str(file_path)
        for pattern in self.config.allowed_paths:
            if fnmatch.fnmatch(file_str, pattern):
                return True
        return False

    def _analyze_file(self, file_path: Path, root_path: Path) -> List[ForbiddenImportViolation]:
        """
        Analyze a single file for forbidden imports.

        Args:
            file_path: Path to Python file
            root_path: Root path for calculating relative paths

        Returns:
            List of detected violations
        """
        # Skip files in allowed paths
        if self._is_allowed_path(file_path):
            return []

        try:
            source = file_path.read_text(encoding="utf-8")
            source_lines = source.splitlines()
            tree = ast.parse(source)

            visitor = ForbiddenImportVisitor(
                file_path=str(file_path.absolute()),
                source_lines=source_lines,
                forbidden_modules=self.config.forbidden_modules,
                default_severity=self.config.severity,
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

    def _analyze_directory(self, directory: Path, report: ForbiddenImportReport) -> None:
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
                if not file.endswith(".py"):
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

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if name matches exclude pattern."""
        return fnmatch.fnmatch(name, pattern)

    def generate_report(self, report: ForbiddenImportReport, output_format: str = "text") -> str:
        """
        Generate formatted forbidden import report.

        Args:
            report: ForbiddenImportReport to format
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

    def _generate_text_report(self, report: ForbiddenImportReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "FORBIDDEN IMPORTS REPORT",
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
            lines.extend(["Forbidden Modules Found:"])
            for module, count in sorted(report.violations_by_module.items()):
                lines.append(f"  {module}: {count}")

            if report.most_problematic_files:
                lines.extend(["", "Most Problematic Files:", "-" * 40])
                for file_path, count in report.most_problematic_files[:5]:
                    filename = os.path.basename(file_path)
                    lines.append(f"  {filename}: {count} violations")

            lines.extend(["", "VIOLATIONS", "-" * 40])

            for violation in report.detected_violations:
                lines.extend([
                    "",
                    f"[{violation.severity.upper()}] {violation.location}",
                    f"  Module: {violation.module_name}",
                    f"  Import: {violation.import_statement}",
                    f"  Remediation: {violation.remediation}",
                ])

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self, report: ForbiddenImportReport) -> str:
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
                "violations_by_module": report.violations_by_module,
                "violations_by_severity": report.violations_by_severity,
            },
            "violations": [
                {
                    "file_path": v.file_path,
                    "relative_path": v.relative_path,
                    "line_number": v.line_number,
                    "module_name": v.module_name,
                    "import_statement": v.import_statement,
                    "severity": v.severity,
                    "remediation": v.remediation,
                }
                for v in report.detected_violations
            ],
        }
        return json.dumps(report_data, indent=2)

    def _generate_markdown_report(self, report: ForbiddenImportReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Forbidden Imports Report",
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
                "### Forbidden Modules",
                "",
                "| Module | Count |",
                "|--------|-------|",
            ])
            for module, count in sorted(report.violations_by_module.items()):
                lines.append(f"| {module} | {count} |")

            lines.extend(["", "## Violations", ""])

            for v in report.detected_violations[:50]:
                lines.extend([
                    f"### `{v.location}`",
                    "",
                    f"**Module:** `{v.module_name}`",
                    "",
                    f"**Import:** `{v.import_statement}`",
                    "",
                    f"**Remediation:** {v.remediation}",
                    "",
                ])

        return "\n".join(lines)
