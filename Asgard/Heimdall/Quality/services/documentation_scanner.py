"""
Heimdall Documentation Scanner Service

Analyzes Python source files for comment density and public API documentation
coverage. Counts comment lines (single-line # comments, multi-line docstrings),
detects undocumented public functions and classes, and produces per-file and
summary-level reports.
"""

import ast
import fnmatch
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from Asgard.Heimdall.Quality.models.documentation_models import (
    ClassDocumentation,
    DocumentationConfig,
    DocumentationReport,
    FileDocumentation,
    FunctionDocumentation,
)


class DocumentationScanner:
    """
    Analyzes Python source files for comment density and public API documentation.

    Counts comment lines (single-line # comments and docstrings), calculates
    comment density, identifies undocumented public functions and classes, and
    produces per-file and project-level coverage reports.

    Usage:
        scanner = DocumentationScanner()
        report = scanner.scan(Path("./src"))

        print(f"Comment density: {report.overall_comment_density:.1f}%")
        print(f"API coverage: {report.overall_api_coverage:.1f}%")
        print(f"Undocumented APIs: {report.undocumented_apis}")
    """

    def __init__(self, config: Optional[DocumentationConfig] = None):
        """
        Initialize the documentation scanner.

        Args:
            config: Configuration for the scanner. If None, uses defaults.
        """
        self.config = config or DocumentationConfig()

    def scan(self, scan_path: Path) -> DocumentationReport:
        """
        Scan a directory for documentation coverage and comment density.

        Args:
            scan_path: Path to directory to analyze

        Returns:
            DocumentationReport with per-file and summary results

        Raises:
            FileNotFoundError: If scan_path does not exist
        """
        if not scan_path.exists():
            raise FileNotFoundError(f"Path does not exist: {scan_path}")

        start_time = datetime.now()
        report = DocumentationReport(scan_path=str(scan_path))

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
                    file_result = self._analyze_file(file_path)
                    if file_result is not None:
                        report.file_results.append(file_result)
                        report.total_files += 1
                        report.total_public_apis += file_result.total_public_apis
                        report.undocumented_apis += file_result.undocumented_count
                except Exception:
                    pass

        # Calculate aggregate metrics
        if report.file_results:
            total_non_blank = sum(
                f.total_lines - f.blank_lines for f in report.file_results
            )
            total_comment = sum(f.comment_lines for f in report.file_results)
            if total_non_blank > 0:
                report.overall_comment_density = (total_comment / total_non_blank) * 100.0

            if report.total_public_apis > 0:
                documented = report.total_public_apis - report.undocumented_apis
                report.overall_api_coverage = (documented / report.total_public_apis) * 100.0

        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()

        return report

    def _analyze_file(self, file_path: Path) -> Optional[FileDocumentation]:
        """Analyze a single Python file for documentation metrics."""
        try:
            source = file_path.read_text(encoding="utf-8")
        except Exception:
            return None

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return None

        # Count line types
        total_lines, code_lines, comment_lines, blank_lines = self._count_lines(source)

        # Calculate comment density
        non_blank = total_lines - blank_lines
        comment_density = (comment_lines / non_blank * 100.0) if non_blank > 0 else 0.0

        # Gather function and class documentation
        functions, classes = self._extract_documentation(tree, str(file_path))

        # Calculate undocumented count
        undocumented = 0
        for func in functions:
            if func.is_public and not func.has_docstring:
                undocumented += 1
        for cls in classes:
            if cls.is_public and not cls.has_docstring:
                undocumented += 1
            for method in cls.methods:
                if method.is_public and not method.has_docstring:
                    undocumented += 1

        # Calculate public API coverage
        total_public = sum(1 for f in functions if f.is_public)
        total_public += sum(1 for c in classes if c.is_public)
        total_public += sum(
            sum(1 for m in c.methods if m.is_public)
            for c in classes
        )

        if total_public > 0:
            documented_count = total_public - undocumented
            coverage = (documented_count / total_public) * 100.0
        else:
            coverage = 100.0

        return FileDocumentation(
            path=str(file_path),
            total_lines=total_lines,
            code_lines=code_lines,
            comment_lines=comment_lines,
            blank_lines=blank_lines,
            comment_density=round(comment_density, 2),
            public_api_coverage=round(coverage, 2),
            undocumented_count=undocumented,
            functions=functions,
            classes=classes,
        )

    def _count_lines(self, source: str) -> Tuple[int, int, int, int]:
        """
        Count total, code, comment, and blank lines in source text.

        Returns:
            Tuple of (total_lines, code_lines, comment_lines, blank_lines)
        """
        lines = source.splitlines()
        total_lines = len(lines)
        blank_lines = 0
        comment_lines = 0
        code_lines = 0
        in_multiline = False
        multiline_quote = ""

        for line in lines:
            stripped = line.strip()

            if not stripped:
                blank_lines += 1
                continue

            # Multi-line string/docstring tracking
            if in_multiline:
                comment_lines += 1
                if multiline_quote in stripped:
                    count = stripped.count(multiline_quote)
                    # Odd number of quotes means we exit the multiline
                    if count % 2 == 1:
                        in_multiline = False
                        multiline_quote = ""
                continue

            # Detect start of multi-line strings
            for quote in ('"""', "'''"):
                if quote in stripped:
                    count = stripped.count(quote)
                    if count % 2 == 1:
                        # Odd occurrences: entering a multiline
                        in_multiline = True
                        multiline_quote = quote
                    comment_lines += 1
                    break
            else:
                if stripped.startswith("#"):
                    comment_lines += 1
                else:
                    code_lines += 1
                    # Inline comment contributes fractionally (counted as code primarily)

        return total_lines, code_lines, comment_lines, blank_lines

    def _extract_documentation(
        self, tree: ast.AST, file_path: str
    ) -> Tuple[List[FunctionDocumentation], List[ClassDocumentation]]:
        """
        Extract function and class documentation status from an AST.

        Returns:
            Tuple of (top_level_functions, classes)
        """
        top_level_functions: List[FunctionDocumentation] = []
        classes: List[ClassDocumentation] = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_doc = self._analyze_function_node(node)
                top_level_functions.append(func_doc)
            elif isinstance(node, ast.ClassDef):
                class_doc = self._analyze_class_node(node)
                classes.append(class_doc)

        return top_level_functions, classes

    def _analyze_function_node(self, node: ast.FunctionDef) -> FunctionDocumentation:
        """Analyze a function or method AST node for documentation."""
        docstring = ast.get_docstring(node)
        is_dunder = node.name.startswith("__") and node.name.endswith("__")
        is_private = node.name.startswith("_") and not is_dunder
        is_public = not is_private and not is_dunder

        docstring_lines = 0
        if docstring:
            docstring_lines = len(docstring.splitlines())

        return FunctionDocumentation(
            name=node.name,
            line_number=node.lineno,
            has_docstring=docstring is not None,
            is_public=is_public,
            docstring_lines=docstring_lines,
        )

    def _analyze_class_node(self, node: ast.ClassDef) -> ClassDocumentation:
        """Analyze a class AST node for documentation, including its methods."""
        docstring = ast.get_docstring(node)
        is_private = node.name.startswith("_")
        is_public = not is_private

        docstring_lines = 0
        if docstring:
            docstring_lines = len(docstring.splitlines())

        methods: List[FunctionDocumentation] = []
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_doc = self._analyze_function_node(child)
                methods.append(method_doc)

        return ClassDocumentation(
            name=node.name,
            line_number=node.lineno,
            has_docstring=docstring is not None,
            is_public=is_public,
            docstring_lines=docstring_lines,
            methods=methods,
        )

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

    def generate_report(self, report: DocumentationReport, output_format: str = "text") -> str:
        """
        Generate a formatted documentation report string.

        Args:
            report: DocumentationReport to format
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

    def _generate_text_report(self, report: DocumentationReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "DOCUMENTATION COVERAGE REPORT",
            "=" * 60,
            "",
            f"Scan Path: {report.scan_path}",
            f"Scan Time: {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {report.scan_duration_seconds:.2f} seconds",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Files: {report.total_files}",
            f"Comment Density: {report.overall_comment_density:.1f}%",
            f"API Documentation Coverage: {report.overall_api_coverage:.1f}%",
            f"Total Public APIs: {report.total_public_apis}",
            f"Undocumented APIs: {report.undocumented_apis}",
            "",
        ]

        problem_files = [
            f for f in report.file_results
            if f.comment_density < 10.0 or f.public_api_coverage < 70.0
        ]

        if problem_files:
            lines.extend(["FILES WITH ISSUES", "-" * 40, ""])
            for f in sorted(problem_files, key=lambda x: x.public_api_coverage):
                lines.append(f"  {f.path}")
                lines.append(f"    Comment density: {f.comment_density:.1f}% | API coverage: {f.public_api_coverage:.1f}% | Undocumented: {f.undocumented_count}")
                lines.append("")
        else:
            lines.extend(["All files meet documentation thresholds.", ""])

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self, report: DocumentationReport) -> str:
        """Generate JSON report."""
        def serialize_function(func: FunctionDocumentation) -> Dict:
            return {
                "name": func.name,
                "line_number": func.line_number,
                "has_docstring": func.has_docstring,
                "is_public": func.is_public,
                "docstring_lines": func.docstring_lines,
            }

        def serialize_class(cls: ClassDocumentation) -> Dict:
            return {
                "name": cls.name,
                "line_number": cls.line_number,
                "has_docstring": cls.has_docstring,
                "is_public": cls.is_public,
                "docstring_lines": cls.docstring_lines,
                "methods": [serialize_function(m) for m in cls.methods],
            }

        def serialize_file(f: FileDocumentation) -> Dict:
            return {
                "path": f.path,
                "total_lines": f.total_lines,
                "code_lines": f.code_lines,
                "comment_lines": f.comment_lines,
                "blank_lines": f.blank_lines,
                "comment_density": f.comment_density,
                "public_api_coverage": f.public_api_coverage,
                "undocumented_count": f.undocumented_count,
                "functions": [serialize_function(fn) for fn in f.functions],
                "classes": [serialize_class(c) for c in f.classes],
            }

        output = {
            "scan_info": {
                "scan_path": report.scan_path,
                "scanned_at": report.scanned_at.isoformat(),
                "duration_seconds": report.scan_duration_seconds,
            },
            "summary": {
                "total_files": report.total_files,
                "overall_comment_density": report.overall_comment_density,
                "overall_api_coverage": report.overall_api_coverage,
                "total_public_apis": report.total_public_apis,
                "undocumented_apis": report.undocumented_apis,
            },
            "file_results": [serialize_file(f) for f in report.file_results],
        }

        return json.dumps(output, indent=2)

    def _generate_markdown_report(self, report: DocumentationReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Documentation Coverage Report",
            "",
            f"**Scan Path:** `{report.scan_path}`",
            f"**Generated:** {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {report.scan_duration_seconds:.2f} seconds",
            "",
            "## Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Total Files | {report.total_files} |",
            f"| Comment Density | {report.overall_comment_density:.1f}% |",
            f"| API Documentation Coverage | {report.overall_api_coverage:.1f}% |",
            f"| Total Public APIs | {report.total_public_apis} |",
            f"| Undocumented APIs | {report.undocumented_apis} |",
            "",
        ]

        problem_files = [
            f for f in report.file_results
            if f.comment_density < 10.0 or f.public_api_coverage < 70.0
        ]

        if problem_files:
            lines.extend(["## Files With Issues", ""])
            for f in sorted(problem_files, key=lambda x: x.public_api_coverage):
                lines.extend([
                    f"### `{f.path}`",
                    f"- **Comment Density:** {f.comment_density:.1f}%",
                    f"- **API Coverage:** {f.public_api_coverage:.1f}%",
                    f"- **Undocumented APIs:** {f.undocumented_count}",
                    "",
                ])
        else:
            lines.extend(["All files meet documentation thresholds.", ""])

        return "\n".join(lines)
