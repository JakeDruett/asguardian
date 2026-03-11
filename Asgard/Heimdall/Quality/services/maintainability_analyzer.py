"""
Heimdall Maintainability Index Analyzer Service

Calculates comprehensive maintainability scores using Microsoft's industry-standard
Maintainability Index formula:

MI = 171 - 5.2 * ln(HV) - 0.23 * CC - 16.2 * ln(LOC) + 50 * sin(sqrt(2.4 * CM))

Where:
- HV = Halstead Volume
- CC = Cyclomatic Complexity
- LOC = Lines of Code
- CM = Comment percentage (0-100)

Maintainability Score Interpretation:
- 85-100: Excellent maintainability, easy to modify and extend
- 70-84: Good maintainability, manageable complexity
- 50-69: Moderate maintainability, some challenges expected
- 25-49: Poor maintainability, significant effort required
- 0-24: Critical maintainability, consider rewriting
"""

import ast
import fnmatch
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from Asgard.Heimdall.Quality.models.maintainability_models import (
    FileMaintainability,
    FunctionMaintainability,
    HalsteadMetrics,
    LanguageProfile,
    LanguageWeights,
    MaintainabilityConfig,
    MaintainabilityLevel,
    MaintainabilityReport,
    MaintainabilityThresholds,
)


class MaintainabilityVisitor(ast.NodeVisitor):
    """
    AST visitor to extract maintainability metrics from Python code.

    Analyzes:
    - Function definitions and their complexity
    - Halstead operators and operands
    - Code structure and size
    - Documentation/comment coverage
    """

    def __init__(self, file_path: str, include_halstead: bool = True, include_comments: bool = True):
        self.file_path = file_path
        self.include_halstead = include_halstead
        self.include_comments = include_comments
        self.functions: List[Dict] = []
        self.file_lines = 0
        self.file_comments = 0
        self.code_lines = 0

        # Python operators for Halstead metrics
        self.python_operators = {
            '+', '-', '*', '/', '//', '%', '**', '&', '|', '^', '~', '<<', '>>',
            '==', '!=', '<', '>', '<=', '>=', 'and', 'or', 'not', 'in', 'is',
            '=', '+=', '-=', '*=', '/=', '//=', '%=', '**=', '&=', '|=', '^=',
            '<<=', '>>=', 'if', 'else', 'elif', 'while', 'for', 'break', 'continue',
            'def', 'class', 'return', 'yield', 'import', 'from', 'as', 'try',
            'except', 'finally', 'raise', 'with', 'assert', 'del', 'pass'
        }

        # Count file-level metrics
        if include_comments:
            self._count_file_comments()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        func_data = self._analyze_function(node)
        self.functions.append(func_data)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        func_data = self._analyze_function(node)
        self.functions.append(func_data)
        self.generic_visit(node)

    def _analyze_function(self, node) -> Dict:
        """Analyze a single function for maintainability metrics."""
        # Calculate cyclomatic complexity
        complexity = self._calculate_complexity(node)

        # Calculate lines of code
        loc = getattr(node, 'end_lineno', node.lineno) - node.lineno + 1

        # Calculate Halstead metrics
        halstead_volume = 0.0
        if self.include_halstead:
            halstead = self._calculate_halstead_metrics(node)
            halstead_volume = halstead.volume

        # Calculate comment percentage
        comment_percentage = 0.0
        if self.include_comments:
            comment_percentage = self._calculate_function_comments(node)

        return {
            'name': node.name,
            'line_number': node.lineno,
            'complexity': complexity,
            'loc': loc,
            'halstead_volume': halstead_volume,
            'comment_percentage': comment_percentage
        }

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity for a node."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
            elif isinstance(child, (ast.IfExp,)):
                complexity += 1
        return complexity

    def _calculate_halstead_metrics(self, node: ast.AST) -> HalsteadMetrics:
        """Calculate Halstead complexity metrics for a node."""
        operators = set()
        operands = set()
        operator_count = 0
        operand_count = 0

        for child in ast.walk(node):
            # Operands: Names and constants
            if isinstance(child, ast.Name):
                operands.add(child.id)
                operand_count += 1
            elif isinstance(child, ast.Constant):
                operands.add(str(child.value))
                operand_count += 1

            # Operators: Binary, unary, and boolean ops
            elif isinstance(child, ast.BinOp):
                op_name = type(child.op).__name__.lower()
                operators.add(op_name)
                operator_count += 1
            elif isinstance(child, ast.UnaryOp):
                op_name = type(child.op).__name__.lower()
                operators.add(op_name)
                operator_count += 1
            elif isinstance(child, ast.BoolOp):
                op_name = type(child.op).__name__.lower()
                operators.add(op_name)
                operator_count += 1
            elif isinstance(child, ast.Compare):
                for op in child.ops:
                    op_name = type(op).__name__.lower()
                    operators.add(op_name)
                    operator_count += 1

            # Control flow operators
            elif isinstance(child, (ast.If, ast.While, ast.For)):
                op_name = type(child).__name__.lower()
                operators.add(op_name)
                operator_count += 1
            elif isinstance(child, (ast.Return, ast.Yield)):
                op_name = type(child).__name__.lower()
                operators.add(op_name)
                operator_count += 1

        return HalsteadMetrics(
            n1=len(operators),
            n2=len(operands),
            N1=operator_count,
            N2=operand_count
        )

    def _calculate_function_comments(self, node) -> float:
        """Calculate comment percentage for a function."""
        # Check for docstring
        docstring = ast.get_docstring(node)
        func_lines = getattr(node, 'end_lineno', node.lineno) - node.lineno + 1

        if docstring:
            docstring_lines = len(docstring.split('\n'))
            return min((docstring_lines / max(func_lines, 1)) * 100, 100.0)

        return 0.0

    def _count_file_comments(self) -> None:
        """Count comments and lines in the entire file."""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            self.file_lines = len(lines)
            comment_lines = 0
            code_lines = 0
            in_multiline = False

            for line in lines:
                stripped = line.strip()

                # Skip empty lines
                if not stripped:
                    continue

                # Multi-line string/docstring detection
                if '"""' in line or "'''" in line:
                    quote = '"""' if '"""' in line else "'''"
                    count = line.count(quote)
                    if count == 1:
                        in_multiline = not in_multiline
                    comment_lines += 1
                    continue

                if in_multiline:
                    comment_lines += 1
                    continue

                # Single-line comment
                if stripped.startswith('#'):
                    comment_lines += 1
                else:
                    code_lines += 1
                    # Inline comment
                    if '#' in line:
                        comment_lines += 0.5  # Partial credit

            self.file_comments = int(comment_lines)
            self.code_lines = code_lines
        except Exception:
            self.file_lines = 1
            self.file_comments = 0
            self.code_lines = 1

    def get_file_metrics(self) -> Dict:
        """Get file-level metrics."""
        # Calculate file-level complexity (average of functions)
        if self.functions:
            avg_complexity = sum(f['complexity'] for f in self.functions) / len(self.functions)
        else:
            avg_complexity = 1

        # File-level Halstead volume
        halstead_volume = 50.0  # Default value
        if self.include_halstead and self.functions:
            volumes = [f['halstead_volume'] for f in self.functions if f['halstead_volume'] > 0]
            if volumes:
                halstead_volume = sum(volumes) / len(volumes)

        # File comment percentage
        comment_percentage = 0.0
        if self.include_comments and self.file_lines > 0:
            comment_percentage = (self.file_comments / self.file_lines) * 100

        return {
            'name': os.path.basename(self.file_path),
            'line_number': 1,
            'complexity': int(avg_complexity),
            'loc': self.code_lines or self.file_lines,
            'halstead_volume': halstead_volume,
            'comment_percentage': comment_percentage,
            'total_lines': self.file_lines,
            'comment_lines': self.file_comments,
        }


class MaintainabilityAnalyzer:
    """
    Calculates maintainability index using Microsoft's formula.

    The Maintainability Index provides an objective measure of how easy code
    is to understand, modify, and maintain. Higher scores indicate better
    maintainability.

    Usage:
        analyzer = MaintainabilityAnalyzer()
        report = analyzer.analyze(Path("./src"))

        print(f"Overall MI: {report.overall_index:.2f}")
        for file in report.file_results:
            if file.maintainability_level in ["poor", "critical"]:
                print(f"  {file.filename}: {file.maintainability_index:.2f}")
    """

    def __init__(self, config: Optional[MaintainabilityConfig] = None):
        """
        Initialize maintainability analyzer.

        Args:
            config: Configuration for analysis. If None, uses defaults.
        """
        self.config = config or MaintainabilityConfig()
        self.thresholds = self.config.thresholds
        self.weights = self.config.get_language_weights()

    def analyze(self, path: Path) -> MaintainabilityReport:
        """
        Analyze a directory for maintainability.

        Args:
            path: Path to directory to analyze

        Returns:
            MaintainabilityReport with complete analysis

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = MaintainabilityReport(scan_path=str(path))

        # Analyze all files
        for root, dirs, files in os.walk(path):
            root_path = Path(root)

            # Filter excluded directories
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
                    if file_result:
                        report.add_file_result(file_result)
                except Exception:
                    pass  # Skip files that can't be analyzed

        # Calculate overall metrics
        if report.file_results:
            all_indices = [f.maintainability_index for f in report.file_results]
            report.overall_index = sum(all_indices) / len(all_indices)
            report.average_index = report.overall_index
            report.overall_level = self._get_maintainability_level(report.overall_index)

            # Collect worst functions
            all_functions = []
            for file_result in report.file_results:
                all_functions.extend(file_result.functions)

            all_functions.sort(key=lambda f: f.maintainability_index)
            report.worst_functions = all_functions[:20]

        # Generate improvement priorities
        report.improvement_priorities = self._generate_improvement_priorities(report)

        # Finalize
        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()

        return report

    def analyze_single_file(self, file_path: Path) -> Optional[FileMaintainability]:
        """
        Analyze a single file for maintainability.

        Args:
            file_path: Path to Python file

        Returns:
            FileMaintainability result or None if analysis fails
        """
        return self._analyze_file(file_path)

    def _analyze_file(self, file_path: Path) -> Optional[FileMaintainability]:
        """Analyze a single file."""
        try:
            source = file_path.read_text(encoding='utf-8')
            tree = ast.parse(source)

            visitor = MaintainabilityVisitor(
                str(file_path),
                include_halstead=self.config.include_halstead,
                include_comments=self.config.include_comments
            )
            visitor.visit(tree)

            # Analyze individual functions
            functions = []
            for func_data in visitor.functions:
                func_result = self._calculate_maintainability(func_data, str(file_path))
                functions.append(func_result)

            # Get file-level metrics
            file_metrics = visitor.get_file_metrics()

            # Calculate file-level maintainability
            if functions:
                avg_mi = sum(f.maintainability_index for f in functions) / len(functions)
            else:
                # Use file-level calculation if no functions
                file_result = self._calculate_maintainability(file_metrics, str(file_path))
                avg_mi = file_result.maintainability_index

            return FileMaintainability(
                file_path=str(file_path),
                maintainability_index=avg_mi,
                maintainability_level=self._get_maintainability_level(avg_mi),
                total_lines=file_metrics.get('total_lines', visitor.file_lines),
                code_lines=file_metrics.get('loc', visitor.code_lines),
                comment_lines=file_metrics.get('comment_lines', visitor.file_comments),
                comment_percentage=file_metrics.get('comment_percentage', 0),
                function_count=len(functions),
                average_function_mi=avg_mi,
                functions=functions,
            )

        except SyntaxError:
            return None
        except Exception:
            return None

    def _calculate_maintainability(self, metrics_data: Dict, file_path: str) -> FunctionMaintainability:
        """Calculate maintainability index for given metrics."""
        # Extract metrics
        cyclomatic_complexity = metrics_data.get('complexity', 1)
        lines_of_code = max(metrics_data.get('loc', 1), 1)
        halstead_volume = max(metrics_data.get('halstead_volume', 20), 1)
        comment_percentage = max(metrics_data.get('comment_percentage', 0), 0.1)

        # Get weights
        complexity_weight = self.weights.complexity_weight
        volume_weight = self.weights.volume_weight
        loc_weight = self.weights.loc_weight
        comment_factor = self.weights.comment_factor

        # Calculate component scores
        complexity_score = complexity_weight * cyclomatic_complexity
        volume_score = volume_weight * math.log(halstead_volume)
        loc_score = loc_weight * math.log(lines_of_code)
        comment_score = comment_factor * math.sin(math.sqrt(2.4 * comment_percentage))

        # Microsoft's maintainability index formula
        maintainability_index = 171 - volume_score - complexity_score - loc_score + comment_score

        # Normalize to 0-100 range
        maintainability_index = max(0, min(100, maintainability_index))

        # Determine level and recommendations
        level = self._get_maintainability_level(maintainability_index)
        recommendations = self._generate_recommendations(
            maintainability_index, cyclomatic_complexity, lines_of_code,
            halstead_volume, comment_percentage
        )

        return FunctionMaintainability(
            name=metrics_data.get('name', 'unknown'),
            file_path=file_path,
            line_number=metrics_data.get('line_number', 1),
            maintainability_index=maintainability_index,
            cyclomatic_complexity=cyclomatic_complexity,
            lines_of_code=lines_of_code,
            halstead_volume=halstead_volume,
            comment_percentage=comment_percentage,
            complexity_score=complexity_score,
            volume_score=volume_score,
            loc_score=loc_score,
            comment_score=comment_score,
            maintainability_level=level,
            recommendations=recommendations,
        )

    def _get_maintainability_level(self, index: float) -> MaintainabilityLevel:
        """Determine maintainability level based on index."""
        if index >= self.thresholds.excellent:
            return MaintainabilityLevel.EXCELLENT
        elif index >= self.thresholds.good:
            return MaintainabilityLevel.GOOD
        elif index >= self.thresholds.moderate:
            return MaintainabilityLevel.MODERATE
        elif index >= self.thresholds.poor:
            return MaintainabilityLevel.POOR
        else:
            return MaintainabilityLevel.CRITICAL

    def _generate_recommendations(self, index: float, complexity: int, loc: int,
                                   volume: float, comment_pct: float) -> List[str]:
        """Generate specific recommendations for improvement."""
        recommendations = []

        if index < 25:
            recommendations.append("CRITICAL: Major refactoring required - consider rewriting")
        elif index < 50:
            recommendations.append("Significant improvement needed - plan refactoring effort")
        elif index < 70:
            recommendations.append("Some improvements recommended for long-term maintainability")

        if complexity > 15:
            recommendations.append(f"Reduce cyclomatic complexity ({complexity} > 15): extract helper functions")

        if complexity > 25:
            recommendations.append(f"Very high complexity ({complexity}): break into smaller units")

        if loc > 50:
            recommendations.append(f"Consider breaking down large function ({loc} lines)")

        if loc > 100:
            recommendations.append(f"Function too long ({loc} lines): extract logical sections")

        if comment_pct < 10:
            recommendations.append("Add documentation: docstrings and inline comments")

        if comment_pct < 5:
            recommendations.append("Minimal documentation - add comprehensive docstrings")

        if volume > 1000:
            recommendations.append("High Halstead volume: simplify algorithms, reduce operator density")

        if volume > 2000:
            recommendations.append("Very high volume: significant algorithm simplification needed")

        return recommendations

    def _generate_improvement_priorities(self, report: MaintainabilityReport) -> List[str]:
        """Generate project-wide improvement priorities."""
        priorities = []

        # Critical issues
        critical_count = report.critical_count
        if critical_count > 0:
            priorities.append(f"URGENT: {critical_count} files with critical maintainability")

        poor_count = report.poor_count
        if poor_count > 0:
            priorities.append(f"Address {poor_count} poorly maintainable files")

        # Function-level issues
        all_functions = []
        for file_result in report.file_results:
            all_functions.extend(file_result.functions)

        common_issues = {
            'high_complexity': sum(1 for f in all_functions if f.cyclomatic_complexity > 15),
            'very_high_complexity': sum(1 for f in all_functions if f.cyclomatic_complexity > 25),
            'long_functions': sum(1 for f in all_functions if f.lines_of_code > 50),
            'very_long_functions': sum(1 for f in all_functions if f.lines_of_code > 100),
            'poor_documentation': sum(1 for f in all_functions if f.comment_percentage < 10),
        }

        if common_issues['very_high_complexity'] > 0:
            priorities.append(f"Critical: {common_issues['very_high_complexity']} functions with complexity > 25")

        if common_issues['high_complexity'] > 10:
            priorities.append(f"High complexity: {common_issues['high_complexity']} functions need refactoring")

        if common_issues['very_long_functions'] > 0:
            priorities.append(f"Very long functions: {common_issues['very_long_functions']} exceed 100 lines")

        if common_issues['long_functions'] > 10:
            priorities.append(f"Long functions: {common_issues['long_functions']} exceed 50 lines")

        if common_issues['poor_documentation'] > 20:
            priorities.append(f"Documentation debt: {common_issues['poor_documentation']} underdocumented functions")

        # Overall assessment
        if report.overall_index >= 85:
            priorities.append("Excellent maintainability - maintain current standards")
        elif report.overall_index >= 70:
            priorities.append("Good maintainability - focus on targeted improvements")
        elif report.overall_index >= 50:
            priorities.append("Moderate maintainability - allocate resources for improvement")
        else:
            priorities.append("Poor overall maintainability - prioritize major refactoring")

        return priorities

    def _should_analyze_file(self, filename: str) -> bool:
        """Check if file should be analyzed based on extension and patterns."""
        # Check extension
        has_valid_ext = any(filename.endswith(ext) for ext in self.config.include_extensions)
        if not has_valid_ext:
            return False

        # Check exclude patterns
        if any(self._matches_pattern(filename, p) for p in self.config.exclude_patterns):
            return False

        # Check test inclusion
        if not self.config.include_tests:
            if filename.startswith("test_") or filename.endswith("_test.py"):
                return False

        return True

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if name matches exclude pattern."""
        return fnmatch.fnmatch(name, pattern)

    def generate_report(self, report: MaintainabilityReport, output_format: str = "text") -> str:
        """
        Generate formatted maintainability report.

        Args:
            report: MaintainabilityReport to format
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

    def _generate_text_report(self, report: MaintainabilityReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "MAINTAINABILITY INDEX REPORT",
            "=" * 60,
            "",
            f"Scan Path: {report.scan_path}",
            f"Scan Time: {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {report.scan_duration_seconds:.2f} seconds",
            "",
            "SUMMARY",
            "-" * 40,
            f"Overall MI: {report.overall_index:.2f} ({report.overall_level})",
            f"Total Files: {report.total_files}",
            f"Total Functions: {report.total_functions}",
            f"Lines of Code: {report.total_lines_of_code:,}",
            "",
            "Files by Level:",
        ]

        for level in MaintainabilityLevel:
            count = report.files_by_level.get(level.value, 0)
            if count > 0:
                lines.append(f"  {level.value.title()}: {count}")

        if report.improvement_priorities:
            lines.extend(["", "Improvement Priorities:", "-" * 40])
            for priority in report.improvement_priorities:
                lines.append(f"  - {priority}")

        if report.worst_functions:
            lines.extend(["", "LOWEST MAINTAINABILITY FUNCTIONS", "-" * 40])
            for i, func in enumerate(report.worst_functions[:10], 1):
                level = func.maintainability_level
                lines.extend([
                    f"{i}. {func.name} - MI: {func.maintainability_index:.2f} ({level})",
                    f"   Location: {func.location}",
                    f"   Complexity: {func.cyclomatic_complexity} | LOC: {func.lines_of_code}",
                ])
                if func.recommendations:
                    lines.append(f"   Recommendation: {func.recommendations[0]}")
                lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)

    def _generate_json_report(self, report: MaintainabilityReport) -> str:
        """Generate JSON report."""
        def serialize_function(func: FunctionMaintainability) -> Dict:
            return {
                "name": func.name,
                "file_path": func.file_path,
                "line_number": func.line_number,
                "maintainability_index": func.maintainability_index,
                "maintainability_level": func.maintainability_level,
                "cyclomatic_complexity": func.cyclomatic_complexity,
                "lines_of_code": func.lines_of_code,
                "halstead_volume": func.halstead_volume,
                "comment_percentage": func.comment_percentage,
                "recommendations": func.recommendations,
            }

        def serialize_file(file_result: FileMaintainability) -> Dict:
            return {
                "file_path": file_result.file_path,
                "maintainability_index": file_result.maintainability_index,
                "maintainability_level": file_result.maintainability_level,
                "total_lines": file_result.total_lines,
                "code_lines": file_result.code_lines,
                "comment_lines": file_result.comment_lines,
                "function_count": file_result.function_count,
                "functions": [serialize_function(f) for f in file_result.functions],
            }

        output = {
            "scan_info": {
                "scan_path": report.scan_path,
                "scanned_at": report.scanned_at.isoformat(),
                "duration_seconds": report.scan_duration_seconds,
            },
            "summary": {
                "overall_index": report.overall_index,
                "overall_level": report.overall_level,
                "total_files": report.total_files,
                "total_functions": report.total_functions,
                "total_lines_of_code": report.total_lines_of_code,
                "files_by_level": report.files_by_level,
                "functions_by_level": report.functions_by_level,
            },
            "file_results": [serialize_file(f) for f in report.file_results],
            "worst_functions": [serialize_function(f) for f in report.worst_functions[:20]],
            "improvement_priorities": report.improvement_priorities,
        }

        return json.dumps(output, indent=2)

    def _generate_markdown_report(self, report: MaintainabilityReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Maintainability Index Report",
            "",
            f"**Scan Path:** `{report.scan_path}`",
            f"**Generated:** {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {report.scan_duration_seconds:.2f} seconds",
            "",
            "## Summary",
            "",
            f"**Overall Maintainability Index:** {report.overall_index:.2f} ({report.overall_level})",
            f"**Total Files:** {report.total_files}",
            f"**Total Functions:** {report.total_functions}",
            f"**Lines of Code:** {report.total_lines_of_code:,}",
            "",
            "### Files by Maintainability Level",
            "",
            "| Level | Count |",
            "|-------|-------|",
        ]

        for level in MaintainabilityLevel:
            count = report.files_by_level.get(level.value, 0)
            lines.append(f"| {level.value.title()} | {count} |")

        if report.improvement_priorities:
            lines.extend(["", "## Improvement Priorities", ""])
            for priority in report.improvement_priorities:
                lines.append(f"- {priority}")

        if report.worst_functions:
            lines.extend(["", "## Lowest Maintainability Functions", ""])

            for func in report.worst_functions[:15]:
                level = func.maintainability_level
                lines.extend([
                    f"### {func.name}",
                    f"- **Location:** `{func.location}`",
                    f"- **MI:** {func.maintainability_index:.2f} ({level})",
                    f"- **Complexity:** {func.cyclomatic_complexity}",
                    f"- **Lines:** {func.lines_of_code}",
                    f"- **Comment %:** {func.comment_percentage:.1f}%",
                    "",
                ])

                if func.recommendations:
                    lines.append("**Recommendations:**")
                    for rec in func.recommendations[:3]:
                        lines.append(f"- {rec}")
                    lines.append("")

        return "\n".join(lines)
