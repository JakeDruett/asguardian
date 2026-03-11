"""
Heimdall Naming Convention Scanner Service

Enforces Python PEP 8 naming conventions by parsing source files with the AST
module and checking function, class, variable, and constant names.

Rules enforced:
- Functions and methods:  snake_case
- Classes:                PascalCase
- Module-level variables: snake_case
- Module-level constants: UPPER_CASE_WITH_UNDERSCORES
- Dunder methods:         exempt
- Type aliases (T, K, V): exempt
- Private members:        _ prefix variant of their type rule
"""

import ast
import fnmatch
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from Asgard.Heimdall.Quality.models.naming_models import (
    NamingConfig,
    NamingConvention,
    NamingReport,
    NamingViolation,
)

# Regex patterns for naming conventions
_RE_SNAKE_CASE = re.compile(r"^_*[a-z][a-z0-9_]*$|^_+$")
_RE_PASCAL_CASE = re.compile(r"^_*[A-Z][a-zA-Z0-9]*$")
_RE_UPPER_CASE = re.compile(r"^_*[A-Z][A-Z0-9_]*$")
# Type alias: single uppercase letter, optionally followed by digits, or common generics
_RE_TYPE_ALIAS = re.compile(r"^[A-Z][A-Z0-9]?$|^T_[A-Z]|^TypeVar")


def _is_snake_case(name: str) -> bool:
    """Return True if name follows snake_case convention."""
    return bool(_RE_SNAKE_CASE.match(name))


def _is_pascal_case(name: str) -> bool:
    """Return True if name follows PascalCase convention."""
    return bool(_RE_PASCAL_CASE.match(name))


def _is_upper_case(name: str) -> bool:
    """Return True if name follows UPPER_CASE convention."""
    return bool(_RE_UPPER_CASE.match(name))


def _is_dunder(name: str) -> bool:
    """Return True if name is a dunder (double underscore on both sides)."""
    return name.startswith("__") and name.endswith("__")


def _is_type_alias(name: str) -> bool:
    """Return True if name looks like a type alias (single uppercase letter, etc.)."""
    return bool(_RE_TYPE_ALIAS.match(name))


def _looks_like_constant(name: str) -> bool:
    """
    Determine whether a module-level assignment target looks like a constant.

    A name is treated as a constant if it is entirely uppercase (with optional
    underscores and digits), indicating an intentional constant per PEP 8.
    """
    return bool(re.match(r"^[A-Z][A-Z0-9_]*$", name))


class NamingConventionScanner:
    """
    Scans Python source files for PEP 8 naming convention violations.

    Checks functions, methods, classes, module-level variables, and constants.
    Dunder methods and type aliases are exempt from checking.

    Usage:
        scanner = NamingConventionScanner()
        report = scanner.scan(Path("./src"))

        print(f"Total violations: {report.total_violations}")
        for file_path, violations in report.file_results.items():
            for v in violations:
                print(f"  {v.file_path}:{v.line_number} {v.element_name}")
    """

    def __init__(self, config: Optional[NamingConfig] = None):
        """
        Initialize the naming convention scanner.

        Args:
            config: Configuration for the scanner. If None, uses defaults.
        """
        self.config = config or NamingConfig()

    def scan(self, scan_path: Path) -> NamingReport:
        """
        Scan a directory for naming convention violations.

        Args:
            scan_path: Path to directory to analyze

        Returns:
            NamingReport with all violations found

        Raises:
            FileNotFoundError: If scan_path does not exist
        """
        if not scan_path.exists():
            raise FileNotFoundError(f"Path does not exist: {scan_path}")

        start_time = datetime.now()
        report = NamingReport(scan_path=str(scan_path))

        for root, dirs, files in os.walk(scan_path):
            root_path = Path(root)

            dirs[:] = [
                d for d in dirs
                if not any(self._matches_pattern(d, p) for p in self.config.exclude_patterns)
            ]

            for file in files:
                if not self._should_analyze_file(file):
                    continue

                file_path = root_path / file
                try:
                    violations = self._analyze_file(file_path)
                    for violation in violations:
                        report.add_violation(violation)
                except Exception:
                    pass

        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()

        return report

    def _analyze_file(self, file_path: Path) -> List[NamingViolation]:
        """Analyze a single file for naming violations."""
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
        except (SyntaxError, Exception):
            return []

        violations: List[NamingViolation] = []
        str_path = str(file_path)

        # Check top-level and nested definitions
        self._check_module(tree, str_path, violations)

        return violations

    def _check_module(
        self, tree: ast.AST, file_path: str, violations: List[NamingViolation]
    ) -> None:
        """Check all definitions in a module AST."""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self.config.check_functions:
                    self._check_function(node, file_path, violations, in_class=False)
            elif isinstance(node, ast.ClassDef):
                if self.config.check_classes:
                    self._check_class(node, file_path, violations)
            elif isinstance(node, ast.Assign):
                self._check_module_assignment(node, file_path, violations)
            elif isinstance(node, ast.AnnAssign):
                self._check_ann_assignment(node, file_path, violations)

    def _check_function(
        self,
        node: ast.FunctionDef,
        file_path: str,
        violations: List[NamingViolation],
        in_class: bool = False,
    ) -> None:
        """Check a function or method name for snake_case compliance."""
        name = node.name

        if _is_dunder(name):
            return

        if name in self.config.allow_list:
            return

        if not _is_snake_case(name):
            element_type = "method" if in_class else "function"
            violations.append(NamingViolation(
                file_path=file_path,
                line_number=node.lineno,
                element_type=element_type,
                element_name=name,
                expected_convention=NamingConvention.SNAKE_CASE,
                description=(
                    f"{element_type.capitalize()} '{name}' does not follow snake_case convention"
                ),
            ))

        # Recurse into nested functions
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self.config.check_functions:
                    self._check_function(child, file_path, violations, in_class=in_class)

    def _check_class(
        self, node: ast.ClassDef, file_path: str, violations: List[NamingViolation]
    ) -> None:
        """Check a class name for PascalCase compliance and its methods."""
        name = node.name

        if name in self.config.allow_list:
            return

        if not _is_pascal_case(name):
            violations.append(NamingViolation(
                file_path=file_path,
                line_number=node.lineno,
                element_type="class",
                element_name=name,
                expected_convention=NamingConvention.PASCAL_CASE,
                description=f"Class '{name}' does not follow PascalCase convention",
            ))

        # Check methods inside the class
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if self.config.check_functions:
                    self._check_function(child, file_path, violations, in_class=True)
            elif isinstance(child, ast.ClassDef):
                if self.config.check_classes:
                    self._check_class(child, file_path, violations)

    def _check_module_assignment(
        self, node: ast.Assign, file_path: str, violations: List[NamingViolation]
    ) -> None:
        """Check module-level assignment targets for naming compliance."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                self._check_assignment_name(
                    target.id, target.lineno if hasattr(target, 'lineno') else node.lineno,
                    file_path, violations
                )

    def _check_ann_assignment(
        self, node: ast.AnnAssign, file_path: str, violations: List[NamingViolation]
    ) -> None:
        """Check annotated module-level assignment targets for naming compliance."""
        target = node.target
        if isinstance(target, ast.Name):
            self._check_assignment_name(
                target.id, target.lineno if hasattr(target, 'lineno') else node.lineno,
                file_path, violations
            )

    def _check_assignment_name(
        self,
        name: str,
        line_number: int,
        file_path: str,
        violations: List[NamingViolation],
    ) -> None:
        """Check a single assignment target name against naming rules."""
        if name in self.config.allow_list:
            return

        if _is_dunder(name):
            return

        if _is_type_alias(name):
            return

        # Determine if this looks like a constant (all uppercase)
        if _looks_like_constant(name):
            if self.config.check_constants and not _is_upper_case(name):
                violations.append(NamingViolation(
                    file_path=file_path,
                    line_number=line_number,
                    element_type="constant",
                    element_name=name,
                    expected_convention=NamingConvention.UPPER_CASE,
                    description=f"Constant '{name}' does not follow UPPER_CASE convention",
                ))
        else:
            if self.config.check_variables and not _is_snake_case(name):
                violations.append(NamingViolation(
                    file_path=file_path,
                    line_number=line_number,
                    element_type="variable",
                    element_name=name,
                    expected_convention=NamingConvention.SNAKE_CASE,
                    description=f"Variable '{name}' does not follow snake_case convention",
                ))

    def _should_analyze_file(self, filename: str) -> bool:
        """Determine whether a file should be analyzed."""
        has_valid_ext = any(filename.endswith(ext) for ext in self.config.include_extensions)
        if not has_valid_ext:
            return False

        if any(self._matches_pattern(filename, p) for p in self.config.exclude_patterns):
            return False

        if not self.config.include_tests:
            if filename.startswith("test_") or filename.endswith("_test.py"):
                return False

        return True

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if a name matches an exclude glob pattern."""
        return fnmatch.fnmatch(name, pattern)

    def generate_report(self, report: NamingReport, output_format: str = "text") -> str:
        """
        Generate a formatted naming violations report string.

        Args:
            report: NamingReport to format
            output_format: Output format (text, json, markdown)

        Returns:
            Formatted report string

        Raises:
            ValueError: If output_format is not supported
        """
        format_lower = output_format.lower()
        if format_lower == "json":
            return self._generate_json_report(report)
        elif format_lower in ("markdown", "md"):
            return self._generate_markdown_report(report)
        elif format_lower == "text":
            return self._generate_text_report(report)
        else:
            raise ValueError(
                f"Unsupported format: {output_format}. Use: text, json, markdown"
            )

    def _generate_text_report(self, report: NamingReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "NAMING CONVENTION REPORT",
            "=" * 60,
            "",
            f"Scan Path: {report.scan_path}",
            f"Scan Time: {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {report.scan_duration_seconds:.2f} seconds",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Violations: {report.total_violations}",
            f"Files With Violations: {report.files_with_violations}",
            "",
        ]

        if report.violations_by_type:
            lines.append("Violations by Type:")
            for element_type, count in sorted(report.violations_by_type.items()):
                lines.append(f"  {element_type}: {count}")
            lines.append("")

        if report.has_violations:
            lines.extend(["VIOLATIONS", "-" * 40, ""])
            for file_path, violations in sorted(report.file_results.items()):
                if not violations:
                    continue
                lines.append(f"  {file_path}")
                for v in sorted(violations, key=lambda x: x.line_number):
                    lines.append(f"    Line {v.line_number:4d}: [{v.element_type}] {v.element_name}")
                    lines.append(f"             {v.description}")
                lines.append("")
        else:
            lines.extend(["No naming violations found.", ""])

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self, report: NamingReport) -> str:
        """Generate JSON report."""
        def serialize_violation(v: NamingViolation) -> Dict:
            return {
                "file_path": v.file_path,
                "line_number": v.line_number,
                "element_type": v.element_type,
                "element_name": v.element_name,
                "expected_convention": v.expected_convention,
                "description": v.description,
            }

        output = {
            "scan_info": {
                "scan_path": report.scan_path,
                "scanned_at": report.scanned_at.isoformat(),
                "duration_seconds": report.scan_duration_seconds,
            },
            "summary": {
                "total_violations": report.total_violations,
                "files_with_violations": report.files_with_violations,
                "violations_by_type": report.violations_by_type,
            },
            "file_results": {
                file_path: [serialize_violation(v) for v in violations]
                for file_path, violations in sorted(report.file_results.items())
                if violations
            },
        }

        return json.dumps(output, indent=2)

    def _generate_markdown_report(self, report: NamingReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Naming Convention Report",
            "",
            f"**Scan Path:** `{report.scan_path}`",
            f"**Generated:** {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {report.scan_duration_seconds:.2f} seconds",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Violations | {report.total_violations} |",
            f"| Files With Violations | {report.files_with_violations} |",
            "",
        ]

        if report.has_violations:
            lines.extend(["## Violations", ""])
            for file_path, violations in sorted(report.file_results.items()):
                if not violations:
                    continue
                lines.extend([f"### `{file_path}`", ""])
                for v in sorted(violations, key=lambda x: x.line_number):
                    lines.append(
                        f"- Line {v.line_number}: `{v.element_name}` "
                        f"[{v.element_type}] - {v.description}"
                    )
                lines.append("")
        else:
            lines.extend(["No naming violations found.", ""])

        return "\n".join(lines)
