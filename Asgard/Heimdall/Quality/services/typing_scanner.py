"""
Heimdall Typing Scanner Service

Analyzes type annotation coverage in Python code.
"""

import ast
import fnmatch
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from Asgard.Heimdall.Quality.models.typing_models import (
    AnnotationSeverity,
    AnnotationStatus,
    FileTypingStats,
    FunctionAnnotation,
    TypingConfig,
    TypingReport,
)


class TypingVisitor(ast.NodeVisitor):
    """
    AST visitor that analyzes type annotation coverage.

    Walks the AST and collects information about function/method
    type annotations, including parameters and return types.
    """

    def __init__(
        self,
        file_path: str,
        config: TypingConfig,
    ):
        """
        Initialize the typing visitor.

        Args:
            file_path: Path to the file being analyzed
            config: Configuration for typing analysis
        """
        self.file_path = file_path
        self.config = config
        self.functions: List[FunctionAnnotation] = []
        self.current_class: Optional[str] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definition to track class context."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definition to analyze annotations."""
        self._analyze_function(node, is_async=False)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition to analyze annotations."""
        self._analyze_function(node, is_async=True)
        self.generic_visit(node)

    def _analyze_function(self, node, is_async: bool) -> None:
        """Analyze a function/method for type annotations."""
        func_name = node.name
        is_method = self.current_class is not None
        is_private = func_name.startswith("_") and not func_name.startswith("__")
        is_dunder = func_name.startswith("__") and func_name.endswith("__")

        # Check exclusions
        if self.config.exclude_private and is_private:
            return
        if self.config.exclude_dunder and is_dunder:
            return

        # Count parameters and annotations
        args = node.args
        all_params = []

        # Collect all parameter names
        for arg in args.posonlyargs:
            all_params.append((arg.arg, arg.annotation))
        for arg in args.args:
            all_params.append((arg.arg, arg.annotation))
        for arg in args.kwonlyargs:
            all_params.append((arg.arg, arg.annotation))
        if args.vararg:
            all_params.append((f"*{args.vararg.arg}", args.vararg.annotation))
        if args.kwarg:
            all_params.append((f"**{args.kwarg.arg}", args.kwarg.annotation))

        # Filter out self/cls if configured
        if self.config.exclude_self_cls and is_method:
            all_params = [(name, ann) for name, ann in all_params if name not in ("self", "cls")]

        total_params = len(all_params)
        annotated_params = sum(1 for _, ann in all_params if ann is not None)
        missing_params = [name for name, ann in all_params if ann is None]

        # Check return annotation
        has_return = node.returns is not None

        # Determine annotation status
        if total_params == 0:
            if has_return or not self.config.require_return_type:
                status = AnnotationStatus.FULLY_ANNOTATED
            else:
                status = AnnotationStatus.NOT_ANNOTATED
        elif annotated_params == total_params and (has_return or not self.config.require_return_type):
            status = AnnotationStatus.FULLY_ANNOTATED
        elif annotated_params > 0 or has_return:
            status = AnnotationStatus.PARTIALLY_ANNOTATED
        else:
            status = AnnotationStatus.NOT_ANNOTATED

        # Determine severity
        if is_dunder or is_private:
            severity = AnnotationSeverity.LOW
        elif is_method and self.current_class:
            severity = AnnotationSeverity.MEDIUM
        else:
            severity = AnnotationSeverity.HIGH

        self.functions.append(FunctionAnnotation(
            file_path=self.file_path,
            line_number=node.lineno,
            function_name=func_name,
            class_name=self.current_class,
            is_async=is_async,
            is_method=is_method,
            is_private=is_private,
            is_dunder=is_dunder,
            status=status,
            severity=severity,
            total_parameters=total_params,
            annotated_parameters=annotated_params,
            has_return_annotation=has_return,
            missing_parameter_names=missing_params,
        ))


class TypingScanner:
    """
    Scans Python files for type annotation coverage.

    Calculates coverage percentage and identifies functions
    that need type annotations.

    Usage:
        scanner = TypingScanner()
        report = scanner.analyze(Path("./src"))

        print(f"Coverage: {report.coverage_percentage:.1f}%")
        for func in report.unannotated_functions:
            print(f"  {func.qualified_name}: {func.status}")
    """

    def __init__(self, config: Optional[TypingConfig] = None):
        """
        Initialize typing scanner.

        Args:
            config: Configuration for scanning. If None, uses defaults.
        """
        self.config = config or TypingConfig()

    def analyze(self, path: Path) -> TypingReport:
        """
        Analyze a file or directory for typing coverage.

        Args:
            path: Path to file or directory to analyze

        Returns:
            TypingReport with coverage statistics

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = TypingReport(
            scan_path=str(path),
            threshold=self.config.minimum_coverage,
        )

        if path.is_file():
            file_stats = self._analyze_file(path, path.parent)
            if file_stats:
                report.add_file_stats(file_stats)
            report.files_scanned = 1
        else:
            self._analyze_directory(path, report)

        # Calculate overall coverage
        report.calculate_coverage()

        # Calculate scan duration
        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()

        return report

    def _analyze_file(self, file_path: Path, root_path: Path) -> Optional[FileTypingStats]:
        """
        Analyze a single file for typing coverage.

        Args:
            file_path: Path to Python file
            root_path: Root path for calculating relative paths

        Returns:
            FileTypingStats or None if file cannot be analyzed
        """
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)

            visitor = TypingVisitor(
                file_path=str(file_path.absolute()),
                config=self.config,
            )
            visitor.visit(tree)

            if not visitor.functions:
                return None

            # Set relative paths
            try:
                relative_path = str(file_path.relative_to(root_path))
            except ValueError:
                relative_path = file_path.name

            for func in visitor.functions:
                func.relative_path = relative_path

            # Calculate file statistics
            total = len(visitor.functions)
            fully = sum(1 for f in visitor.functions if f.status == AnnotationStatus.FULLY_ANNOTATED)
            partial = sum(1 for f in visitor.functions if f.status == AnnotationStatus.PARTIALLY_ANNOTATED)
            none = sum(1 for f in visitor.functions if f.status == AnnotationStatus.NOT_ANNOTATED)

            coverage = (fully / total * 100) if total > 0 else 100.0

            return FileTypingStats(
                file_path=str(file_path.absolute()),
                relative_path=relative_path,
                total_functions=total,
                fully_annotated=fully,
                partially_annotated=partial,
                not_annotated=none,
                coverage_percentage=coverage,
                functions=visitor.functions,
            )

        except SyntaxError:
            return None
        except Exception:
            return None

    def _analyze_directory(self, directory: Path, report: TypingReport) -> None:
        """
        Analyze all Python files in a directory.

        Args:
            directory: Directory to analyze
            report: Report to add statistics to
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

                # Check exclude patterns for files
                file_path = root_path / file
                if any(self._matches_pattern(str(file_path), pattern) for pattern in self.config.exclude_patterns):
                    continue

                if not self.config.include_tests:
                    if file.startswith("test_") or file.endswith("_test.py") or "tests" in str(root_path):
                        continue

                file_stats = self._analyze_file(file_path, directory)
                files_scanned += 1

                if file_stats:
                    report.add_file_stats(file_stats)

        report.files_scanned = files_scanned

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if name matches exclude pattern."""
        return fnmatch.fnmatch(name, pattern)

    def generate_report(self, report: TypingReport, output_format: str = "text") -> str:
        """
        Generate formatted typing coverage report.

        Args:
            report: TypingReport to format
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

    def _generate_text_report(self, report: TypingReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "TYPE ANNOTATION COVERAGE REPORT",
            "=" * 60,
            "",
            f"Scan Path: {report.scan_path}",
            f"Scan Time: {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {report.scan_duration_seconds:.2f} seconds",
            f"Files Scanned: {report.files_scanned}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Functions: {report.total_functions}",
            f"Fully Annotated: {report.fully_annotated}",
            f"Partially Annotated: {report.partially_annotated}",
            f"Not Annotated: {report.not_annotated}",
            "",
            f"Coverage: {report.coverage_percentage:.1f}%",
            f"Threshold: {report.threshold:.1f}%",
            f"Status: {'PASSING' if report.is_passing else 'FAILING'}",
            "",
        ]

        if not report.is_passing:
            files_below = report.get_files_below_threshold()
            if files_below:
                lines.extend(["FILES BELOW THRESHOLD", "-" * 40])
                for f in sorted(files_below, key=lambda x: x.coverage_percentage)[:20]:
                    lines.append(f"  {f.relative_path}: {f.coverage_percentage:.1f}%")
                lines.append("")

            if report.unannotated_functions:
                lines.extend(["", "FUNCTIONS NEEDING ANNOTATIONS", "-" * 40])

                # Group by severity
                by_severity: Dict[str, List[FunctionAnnotation]] = {}
                for func in report.unannotated_functions:
                    sev = func.severity if isinstance(func.severity, str) else func.severity.value
                    if sev not in by_severity:
                        by_severity[sev] = []
                    by_severity[sev].append(func)

                for severity in ["high", "medium", "low"]:
                    funcs = by_severity.get(severity, [])
                    if funcs:
                        lines.extend(["", f"[{severity.upper()}]"])
                        for func in funcs[:30]:
                            missing = ", ".join(func.missing_parameter_names) if func.missing_parameter_names else ""
                            ret = "" if func.has_return_annotation else " (missing return)"
                            params = f" (missing: {missing})" if missing else ""
                            lines.append(f"  {func.location} {func.qualified_name}{params}{ret}")

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self, report: TypingReport) -> str:
        """Generate JSON report."""
        report_data = {
            "scan_info": {
                "scan_path": report.scan_path,
                "scanned_at": report.scanned_at.isoformat(),
                "duration_seconds": report.scan_duration_seconds,
                "files_scanned": report.files_scanned,
            },
            "summary": {
                "total_functions": report.total_functions,
                "fully_annotated": report.fully_annotated,
                "partially_annotated": report.partially_annotated,
                "not_annotated": report.not_annotated,
                "coverage_percentage": report.coverage_percentage,
                "threshold": report.threshold,
                "is_passing": report.is_passing,
            },
            "files": [
                {
                    "file_path": f.file_path,
                    "relative_path": f.relative_path,
                    "total_functions": f.total_functions,
                    "fully_annotated": f.fully_annotated,
                    "coverage_percentage": f.coverage_percentage,
                }
                for f in report.files_analyzed
            ],
            "unannotated_functions": [
                {
                    "file_path": func.file_path,
                    "line_number": func.line_number,
                    "function_name": func.function_name,
                    "class_name": func.class_name,
                    "status": func.status,
                    "severity": func.severity,
                    "total_parameters": func.total_parameters,
                    "annotated_parameters": func.annotated_parameters,
                    "has_return_annotation": func.has_return_annotation,
                    "missing_parameter_names": func.missing_parameter_names,
                }
                for func in report.unannotated_functions
            ],
        }
        return json.dumps(report_data, indent=2)

    def _generate_markdown_report(self, report: TypingReport) -> str:
        """Generate Markdown report."""
        status_emoji = "PASS" if report.is_passing else "FAIL"

        lines = [
            "# Type Annotation Coverage Report",
            "",
            f"**Scan Path:** `{report.scan_path}`",
            f"**Generated:** {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Files Scanned:** {report.files_scanned}",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Functions | {report.total_functions} |",
            f"| Fully Annotated | {report.fully_annotated} |",
            f"| Partially Annotated | {report.partially_annotated} |",
            f"| Not Annotated | {report.not_annotated} |",
            f"| **Coverage** | **{report.coverage_percentage:.1f}%** |",
            f"| Threshold | {report.threshold:.1f}% |",
            f"| Status | **{status_emoji}** |",
            "",
        ]

        if not report.is_passing:
            files_below = report.get_files_below_threshold()
            if files_below:
                lines.extend([
                    "## Files Below Threshold",
                    "",
                    "| File | Coverage |",
                    "|------|----------|",
                ])
                for f in sorted(files_below, key=lambda x: x.coverage_percentage)[:20]:
                    lines.append(f"| `{f.relative_path}` | {f.coverage_percentage:.1f}% |")
                lines.append("")

            if report.unannotated_functions:
                lines.extend([
                    "## Functions Needing Annotations",
                    "",
                ])

                for func in report.unannotated_functions[:50]:
                    missing = ", ".join(func.missing_parameter_names) if func.missing_parameter_names else "none"
                    lines.extend([
                        f"### `{func.qualified_name}` ({func.location})",
                        "",
                        f"- **Status:** {func.status}",
                        f"- **Missing params:** {missing}",
                        f"- **Has return type:** {'Yes' if func.has_return_annotation else 'No'}",
                        "",
                    ])

        return "\n".join(lines)
