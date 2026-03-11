"""
Heimdall Technical Debt Analyzer Service

Quantifies and prioritizes technical debt across the codebase using multiple metrics:
- Code Debt: Quality issues, complexity, maintainability
- Design Debt: Architectural issues, coupling problems
- Test Debt: Coverage gaps, test quality issues
- Documentation Debt: Missing or poor documentation
- Dependency Debt: Outdated or vulnerable dependencies

Provides ROI analysis, time horizon projections, and business impact weighting.
"""

import ast
import fnmatch
import json
import math
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from Asgard.Heimdall.Quality.models.debt_models import (
    DebtConfig,
    DebtItem,
    DebtReport,
    DebtSeverity,
    DebtType,
    EffortModels,
    InterestRates,
    ROIAnalysis,
    TimeHorizon,
    TimeProjection,
)


class ComplexityVisitor(ast.NodeVisitor):
    """
    AST visitor to analyze complexity metrics for debt calculation.

    Detects:
    - High complexity functions (cyclomatic complexity > 15)
    - Long methods (> 50 lines)
    """

    def __init__(self, complexity_threshold: int = 15, length_threshold: int = 50):
        self.complex_functions: List[Tuple[str, int, int]] = []  # (name, complexity, line)
        self.long_methods: List[Tuple[str, int, int]] = []  # (name, length, line)
        self.complexity_threshold = complexity_threshold
        self.length_threshold = length_threshold

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Visit function definitions."""
        self._analyze_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definitions."""
        self._analyze_function(node)

    def _analyze_function(self, node) -> None:
        """Analyze function for complexity and length."""
        # Calculate cyclomatic complexity
        complexity = self._calculate_complexity(node)
        if complexity > self.complexity_threshold:
            self.complex_functions.append((node.name, complexity, node.lineno))

        # Calculate method length
        method_length = getattr(node, "end_lineno", node.lineno) - node.lineno
        if method_length > self.length_threshold:
            self.long_methods.append((node.name, method_length, node.lineno))

        self.generic_visit(node)

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        return complexity


class TechnicalDebtAnalyzer:
    """
    Analyzes and quantifies technical debt using multiple dimensions.

    Debt Categories:
    - Code: Complexity, quality issues, maintainability problems
    - Design: Architectural issues, coupling, abstraction debt
    - Test: Coverage gaps, test quality, missing test types
    - Documentation: Missing/outdated/poor quality docs
    - Dependencies: Outdated, vulnerable, or unused dependencies

    Usage:
        analyzer = TechnicalDebtAnalyzer()
        report = analyzer.analyze(Path("./src"))

        print(f"Total debt: {report.total_debt_hours} hours")
        for item in report.prioritized_items[:10]:
            print(f"{item.description}: {item.effort_hours}h")
    """

    def __init__(self, config: Optional[DebtConfig] = None):
        """
        Initialize technical debt analyzer.

        Args:
            config: Configuration for debt analysis. If None, uses defaults.
        """
        self.config = config or DebtConfig()

    def analyze(self, path: Path) -> DebtReport:
        """
        Analyze a directory for technical debt.

        Args:
            path: Path to directory to analyze

        Returns:
            DebtReport with complete debt analysis

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = DebtReport(scan_path=str(path))

        enabled_types = self.config.get_enabled_debt_types()

        # Analyze different types of debt
        if DebtType.CODE.value in enabled_types:
            self._analyze_code_debt(path, report)

        if DebtType.DESIGN.value in enabled_types:
            self._analyze_design_debt(path, report)

        if DebtType.TEST.value in enabled_types:
            self._analyze_test_debt(path, report)

        if DebtType.DOCUMENTATION.value in enabled_types:
            self._analyze_documentation_debt(path, report)

        if DebtType.DEPENDENCIES.value in enabled_types:
            self._analyze_dependency_debt(path, report)

        # Calculate metrics
        report.total_lines_of_code = self._count_lines_of_code(path)
        if report.total_lines_of_code > 0:
            report.debt_ratio = report.total_debt_hours / report.total_lines_of_code * 1000

        # Prioritize items by ROI
        report.prioritized_items = self._prioritize_debt_items(report.debt_items)

        # Calculate ROI analysis
        report.roi_analysis = self._calculate_roi_analysis(report.debt_items)

        # Time horizon projections
        report.time_projection = self._calculate_time_projection(report.debt_items)

        # Calculate most indebted files
        report.most_indebted_files = self._calculate_most_indebted_files(report.debt_items)

        # Generate remediation priorities
        report.remediation_priorities = self._generate_remediation_priorities(report)

        # Finalize
        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()

        return report

    def analyze_single_file(self, file_path: Path) -> DebtReport:
        """
        Analyze a single file for technical debt.

        Args:
            file_path: Path to Python file

        Returns:
            DebtReport with detected debt
        """
        return self.analyze(file_path)

    def _analyze_code_debt(self, path: Path, report: DebtReport) -> None:
        """Analyze code quality debt."""
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
                    items = self._analyze_file_complexity(file_path)
                    for item in items:
                        report.add_debt_item(item)
                except Exception:
                    pass  # Skip files that can't be analyzed

    def _analyze_file_complexity(self, file_path: Path) -> List[DebtItem]:
        """Analyze complexity-related debt in a file."""
        debt_items = []

        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)

            visitor = ComplexityVisitor()
            visitor.visit(tree)

            # High complexity functions
            for func_name, complexity, line_no in visitor.complex_functions:
                severity = DebtSeverity.CRITICAL if complexity > 30 else DebtSeverity.HIGH
                effort = self.config.effort_models.complexity_reduction_factor * complexity

                debt_items.append(DebtItem(
                    debt_type=DebtType.CODE,
                    file_path=str(file_path.absolute()),
                    line_number=line_no,
                    description=f"High complexity function '{func_name}' (complexity: {complexity})",
                    severity=severity,
                    effort_hours=effort,
                    business_impact=self._get_business_impact(str(file_path)),
                    interest_rate=self.config.interest_rates.high_complexity,
                    remediation_strategy="Break down into smaller functions, reduce nesting, extract helper methods",
                ))

            # Long methods
            for func_name, length, line_no in visitor.long_methods:
                effort = self.config.effort_models.refactoring_log_factor * math.log(length)

                debt_items.append(DebtItem(
                    debt_type=DebtType.CODE,
                    file_path=str(file_path.absolute()),
                    line_number=line_no,
                    description=f"Long method '{func_name}' ({length} lines)",
                    severity=DebtSeverity.MEDIUM,
                    effort_hours=effort,
                    business_impact=self._get_business_impact(str(file_path)),
                    interest_rate=self.config.interest_rates.high_complexity * 0.5,
                    remediation_strategy="Extract methods, simplify logic, apply single responsibility",
                ))

        except SyntaxError:
            pass  # Skip files with syntax errors
        except Exception:
            pass

        return debt_items

    def _analyze_design_debt(self, path: Path, report: DebtReport) -> None:
        """Analyze architectural/design debt."""
        dependency_map = self._build_dependency_map(path)

        for file_path, dependencies in dependency_map.items():
            if len(dependencies) > 10:  # High coupling threshold
                effort = math.log(len(dependencies)) * 3

                severity = DebtSeverity.HIGH if len(dependencies) > 15 else DebtSeverity.MEDIUM

                report.add_debt_item(DebtItem(
                    debt_type=DebtType.DESIGN,
                    file_path=file_path,
                    line_number=1,
                    description=f"High coupling: {len(dependencies)} dependencies",
                    severity=severity,
                    effort_hours=effort,
                    business_impact=self._get_business_impact(file_path),
                    interest_rate=self.config.interest_rates.design_issues,
                    remediation_strategy="Reduce dependencies, apply dependency inversion, use interfaces",
                ))

    def _analyze_test_debt(self, path: Path, report: DebtReport) -> None:
        """Analyze test coverage debt."""
        python_files = []
        test_files = set()

        for root, dirs, files in os.walk(path):
            # Filter excluded directories
            dirs[:] = [
                d for d in dirs
                if not any(self._matches_pattern(d, p) for p in self.config.exclude_patterns)
            ]

            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    if "test" in file.lower() or file.startswith("test_"):
                        test_files.add(file_path)
                    else:
                        python_files.append(file_path)

        for file_path in python_files:
            # Check if test file exists
            base_name = os.path.basename(file_path)
            test_variants = [
                f"test_{base_name}",
                base_name.replace(".py", "_test.py"),
            ]

            has_tests = any(
                variant in os.path.basename(tf) for tf in test_files for variant in test_variants
            )

            if not has_tests:
                loc = self._count_file_lines(file_path)
                if loc == 0:
                    continue

                effort = self.config.effort_models.test_coverage_factor * loc
                severity = DebtSeverity.HIGH if loc > 100 else DebtSeverity.MEDIUM

                report.add_debt_item(DebtItem(
                    debt_type=DebtType.TEST,
                    file_path=file_path,
                    line_number=1,
                    description=f"No test coverage found ({loc} lines)",
                    severity=severity,
                    effort_hours=effort,
                    business_impact=self._get_business_impact(file_path),
                    interest_rate=self.config.interest_rates.no_tests,
                    remediation_strategy="Write unit tests for public functions and critical paths",
                ))

    def _analyze_documentation_debt(self, path: Path, report: DebtReport) -> None:
        """Analyze documentation debt."""
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
                    undocumented = self._find_undocumented_functions(file_path)

                    if undocumented:
                        effort = self.config.effort_models.documentation_factor * len(undocumented)
                        severity = DebtSeverity.MEDIUM if len(undocumented) > 5 else DebtSeverity.LOW

                        report.add_debt_item(DebtItem(
                            debt_type=DebtType.DOCUMENTATION,
                            file_path=str(file_path.absolute()),
                            line_number=undocumented[0][1] if undocumented else 1,
                            description=f"{len(undocumented)} undocumented public functions",
                            severity=severity,
                            effort_hours=effort,
                            business_impact=self._get_business_impact(str(file_path)),
                            interest_rate=self.config.interest_rates.poor_docs,
                            remediation_strategy="Add docstrings to public functions following project standards",
                        ))
                except Exception:
                    pass

    def _analyze_dependency_debt(self, path: Path, report: DebtReport) -> None:
        """Analyze dependency-related debt."""
        req_files = ["requirements.txt", "setup.py", "pyproject.toml"]

        for req_file in req_files:
            req_path = path / req_file
            if req_path.exists():
                report.add_debt_item(DebtItem(
                    debt_type=DebtType.DEPENDENCIES,
                    file_path=str(req_path.absolute()),
                    line_number=1,
                    description="Dependencies may need security updates (run pip-audit or safety)",
                    severity=DebtSeverity.MEDIUM,
                    effort_hours=self.config.effort_models.dependency_update_hours,
                    business_impact=0.7,  # Security is important
                    interest_rate=self.config.interest_rates.outdated_deps,
                    remediation_strategy="Run security audit, update vulnerable packages, review changelogs",
                ))
                break  # Only add once

    def _prioritize_debt_items(self, debt_items: List[DebtItem]) -> List[DebtItem]:
        """Prioritize debt items by ROI."""
        return sorted(debt_items, key=lambda item: item.priority_score, reverse=True)

    def _calculate_roi_analysis(self, debt_items: List[DebtItem]) -> ROIAnalysis:
        """Calculate ROI analysis for debt remediation."""
        if not debt_items:
            return ROIAnalysis()

        total_effort = sum(item.effort_hours for item in debt_items)
        total_benefit = sum(item.business_impact * item.interest_rate for item in debt_items)

        roi_by_type: Dict[str, float] = {}
        for debt_type in DebtType:
            type_items = [item for item in debt_items if item.debt_type == debt_type.value]
            if type_items:
                type_effort = sum(item.effort_hours for item in type_items)
                type_benefit = sum(item.business_impact * item.interest_rate for item in type_items)
                roi_by_type[debt_type.value] = type_benefit / max(type_effort, 0.1)

        overall_roi = total_benefit / max(total_effort, 0.1)

        # Estimate payback period (simplified)
        if overall_roi > 0:
            payback_months = 1 / overall_roi * 3  # Rough estimate
        else:
            payback_months = float("inf")

        return ROIAnalysis(
            overall_roi=overall_roi,
            roi_by_type=roi_by_type,
            payback_period_months=min(payback_months, 999),
            total_effort_hours=total_effort,
            total_benefit=total_benefit,
        )

    def _calculate_time_projection(self, debt_items: List[DebtItem]) -> TimeProjection:
        """Calculate debt growth projections."""
        if not debt_items:
            return TimeProjection()

        current_debt = sum(item.effort_hours for item in debt_items)

        # Calculate quarters based on time horizon
        horizon = self.config.time_horizon
        if isinstance(horizon, str):
            horizon = TimeHorizon(horizon)

        quarters = {
            TimeHorizon.SPRINT: 0.2,  # ~2 weeks
            TimeHorizon.QUARTER: 1.0,
            TimeHorizon.YEAR: 4.0,
        }.get(horizon, 1.0)

        # Project debt growth with compound interest
        projected_debt = 0.0
        for item in debt_items:
            growth_factor = (1 + item.interest_rate) ** quarters
            projected_debt += item.effort_hours * growth_factor

        growth_pct = ((projected_debt - current_debt) / max(current_debt, 1)) * 100

        return TimeProjection(
            current_debt_hours=current_debt,
            projected_debt_hours=projected_debt,
            growth_percentage=growth_pct,
            time_horizon=horizon if isinstance(horizon, str) else horizon.value,
        )

    def _calculate_most_indebted_files(self, debt_items: List[DebtItem]) -> List[Tuple[str, float]]:
        """Calculate files with most debt."""
        file_debt: Dict[str, float] = {}
        for item in debt_items:
            file_debt[item.file_path] = file_debt.get(item.file_path, 0.0) + item.effort_hours

        return sorted(file_debt.items(), key=lambda x: x[1], reverse=True)[:10]

    def _generate_remediation_priorities(self, report: DebtReport) -> List[str]:
        """Generate prioritized remediation recommendations."""
        priorities = []

        # Critical items
        critical_count = report.critical_count
        if critical_count > 0:
            priorities.append(f"CRITICAL: Address {critical_count} critical debt items immediately")

        # High items
        high_count = report.high_count
        if high_count > 0:
            priorities.append(f"HIGH: Review {high_count} high-severity debt items")

        # Type-specific recommendations
        for debt_type, hours in sorted(report.debt_by_type.items(), key=lambda x: x[1], reverse=True):
            if hours > 20:
                priorities.append(f"Focus on {debt_type} debt ({hours:.1f} hours)")

        # ROI recommendation
        if report.roi_analysis.overall_roi > 0.1:
            priorities.append(f"High ROI opportunity: payback in ~{report.roi_analysis.payback_period_months:.1f} months")

        # Growth warning
        if report.time_projection.growth_percentage > 20:
            priorities.append(f"Warning: Debt growing {report.time_projection.growth_percentage:.1f}% per {report.time_projection.time_horizon}")

        return priorities

    def _get_business_impact(self, file_path: str) -> float:
        """Get business impact weight for a file."""
        # Use custom weights if provided
        for pattern, weight in self.config.business_value_weights.items():
            if pattern in file_path:
                return weight

        # Default heuristics
        if "core" in file_path.lower() or "main" in file_path.lower():
            return 0.9
        elif "util" in file_path.lower() or "helper" in file_path.lower():
            return 0.3
        elif "test" in file_path.lower():
            return 0.1
        else:
            return 0.5

    def _count_lines_of_code(self, path: Path) -> int:
        """Count total lines of code in project."""
        total_lines = 0
        for root, dirs, files in os.walk(path):
            # Filter excluded directories
            dirs[:] = [
                d for d in dirs
                if not any(self._matches_pattern(d, p) for p in self.config.exclude_patterns)
            ]

            for file in files:
                if self._should_analyze_file(file):
                    file_path = os.path.join(root, file)
                    total_lines += self._count_file_lines(file_path)
        return total_lines

    def _count_file_lines(self, file_path: str) -> int:
        """Count non-empty lines in a file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return len([line for line in f if line.strip()])
        except Exception:
            return 0

    def _build_dependency_map(self, path: Path) -> Dict[str, List[str]]:
        """Build map of file dependencies."""
        dependency_map: Dict[str, List[str]] = {}

        for root, dirs, files in os.walk(path):
            # Filter excluded directories
            dirs[:] = [
                d for d in dirs
                if not any(self._matches_pattern(d, p) for p in self.config.exclude_patterns)
            ]

            for file in files:
                if not self._should_analyze_file(file):
                    continue

                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        source = f.read()

                    tree = ast.parse(source)
                    dependencies = []

                    for node in ast.walk(tree):
                        if isinstance(node, ast.Import):
                            for alias in node.names:
                                dependencies.append(alias.name)
                        elif isinstance(node, ast.ImportFrom):
                            if node.module:
                                dependencies.append(node.module)

                    dependency_map[file_path] = dependencies
                except Exception:
                    dependency_map[file_path] = []

        return dependency_map

    def _find_undocumented_functions(self, file_path: Path) -> List[Tuple[str, int]]:
        """Find public functions without docstrings."""
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)
            undocumented = []

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Skip private functions
                    if node.name.startswith("_"):
                        continue

                    # Check for docstring
                    if not ast.get_docstring(node):
                        undocumented.append((node.name, node.lineno))

            return undocumented
        except Exception:
            return []

    def _should_analyze_file(self, filename: str) -> bool:
        """Check if file should be analyzed based on extension."""
        if self.config.include_extensions:
            return any(filename.endswith(ext) for ext in self.config.include_extensions)
        return filename.endswith(".py")

    def _matches_pattern(self, name: str, pattern: str) -> bool:
        """Check if name matches exclude pattern."""
        return fnmatch.fnmatch(name, pattern)

    def generate_report(self, report: DebtReport, output_format: str = "text") -> str:
        """
        Generate formatted technical debt report.

        Args:
            report: DebtReport to format
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

    def _generate_text_report(self, report: DebtReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "TECHNICAL DEBT REPORT",
            "=" * 60,
            "",
            f"Scan Path: {report.scan_path}",
            f"Scan Time: {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {report.scan_duration_seconds:.2f} seconds",
            f"Lines of Code: {report.total_lines_of_code:,}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Debt: {report.total_debt_hours:.1f} hours",
            f"Debt Ratio: {report.debt_ratio:.2f} hours per 1K LOC",
            "",
            "By Type:",
        ]

        for debt_type in DebtType:
            hours = report.debt_by_type.get(debt_type.value, 0)
            if hours > 0:
                lines.append(f"  {debt_type.value.title()}: {hours:.1f} hours")

        lines.extend(["", "By Severity:"])
        for severity in [DebtSeverity.CRITICAL, DebtSeverity.HIGH, DebtSeverity.MEDIUM, DebtSeverity.LOW]:
            count = report.debt_by_severity.get(severity.value, 0)
            if count > 0:
                lines.append(f"  {severity.value.upper()}: {count} items")

        if report.most_indebted_files:
            lines.extend(["", "Most Indebted Files:", "-" * 40])
            for file_path, hours in report.most_indebted_files[:5]:
                filename = os.path.basename(file_path)
                lines.append(f"  {filename}: {hours:.1f} hours")

        if report.remediation_priorities:
            lines.extend(["", "Remediation Priorities:", "-" * 40])
            for priority in report.remediation_priorities:
                lines.append(f"  - {priority}")

        if report.prioritized_items:
            lines.extend(["", "TOP PRIORITY ITEMS", "-" * 40])
            for i, item in enumerate(report.prioritized_items[:10], 1):
                lines.extend([
                    f"{i}. {item.description}",
                    f"   Location: {item.location}",
                    f"   Effort: {item.effort_hours:.1f}h | Impact: {item.business_impact:.2f}",
                    f"   Strategy: {item.remediation_strategy}",
                    "",
                ])

        lines.extend([
            "ROI ANALYSIS",
            "-" * 40,
            f"Overall ROI: {report.roi_analysis.overall_roi:.2f}",
            f"Payback Period: {report.roi_analysis.payback_period_months:.1f} months",
            "",
            "TIME PROJECTION",
            "-" * 40,
            f"Current Debt: {report.time_projection.current_debt_hours:.1f} hours",
            f"Projected ({report.time_projection.time_horizon}): {report.time_projection.projected_debt_hours:.1f} hours",
            f"Growth: {report.time_projection.growth_percentage:.1f}%",
            "",
            "=" * 60,
        ])

        return "\n".join(lines)

    def _generate_json_report(self, report: DebtReport) -> str:
        """Generate JSON report."""
        output = {
            "scan_info": {
                "scan_path": report.scan_path,
                "scanned_at": report.scanned_at.isoformat(),
                "duration_seconds": report.scan_duration_seconds,
                "lines_of_code": report.total_lines_of_code,
            },
            "summary": {
                "total_debt_hours": report.total_debt_hours,
                "debt_ratio": report.debt_ratio,
                "debt_by_type": report.debt_by_type,
                "debt_by_severity": report.debt_by_severity,
            },
            "roi_analysis": {
                "overall_roi": report.roi_analysis.overall_roi,
                "roi_by_type": report.roi_analysis.roi_by_type,
                "payback_period_months": report.roi_analysis.payback_period_months,
                "total_effort_hours": report.roi_analysis.total_effort_hours,
            },
            "time_projection": {
                "current_debt_hours": report.time_projection.current_debt_hours,
                "projected_debt_hours": report.time_projection.projected_debt_hours,
                "growth_percentage": report.time_projection.growth_percentage,
                "time_horizon": report.time_projection.time_horizon,
            },
            "debt_items": [
                {
                    "debt_type": item.debt_type,
                    "file_path": item.file_path,
                    "line_number": item.line_number,
                    "description": item.description,
                    "severity": item.severity,
                    "effort_hours": item.effort_hours,
                    "business_impact": item.business_impact,
                    "interest_rate": item.interest_rate,
                    "remediation_strategy": item.remediation_strategy,
                }
                for item in report.prioritized_items[:50]
            ],
            "most_indebted_files": [
                {"file": path, "debt_hours": hours}
                for path, hours in report.most_indebted_files
            ],
            "remediation_priorities": report.remediation_priorities,
        }

        return json.dumps(output, indent=2)

    def _generate_markdown_report(self, report: DebtReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Technical Debt Report",
            "",
            f"**Scan Path:** `{report.scan_path}`",
            f"**Generated:** {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {report.scan_duration_seconds:.2f} seconds",
            f"**Lines of Code:** {report.total_lines_of_code:,}",
            "",
            "## Summary",
            "",
            f"**Total Debt:** {report.total_debt_hours:.1f} hours",
            f"**Debt Ratio:** {report.debt_ratio:.2f} hours per 1K LOC",
            "",
            "### By Type",
            "",
            "| Type | Hours |",
            "|------|-------|",
        ]

        for debt_type in DebtType:
            hours = report.debt_by_type.get(debt_type.value, 0)
            lines.append(f"| {debt_type.value.title()} | {hours:.1f} |")

        lines.extend([
            "",
            "### By Severity",
            "",
            "| Severity | Count |",
            "|----------|-------|",
        ])

        for severity in [DebtSeverity.CRITICAL, DebtSeverity.HIGH, DebtSeverity.MEDIUM, DebtSeverity.LOW]:
            count = report.debt_by_severity.get(severity.value, 0)
            lines.append(f"| {severity.value.title()} | {count} |")

        if report.most_indebted_files:
            lines.extend(["", "## Most Indebted Files", ""])
            for file_path, hours in report.most_indebted_files[:10]:
                filename = os.path.basename(file_path)
                lines.append(f"- `{filename}`: {hours:.1f} hours")

        if report.remediation_priorities:
            lines.extend(["", "## Remediation Priorities", ""])
            for priority in report.remediation_priorities:
                lines.append(f"- {priority}")

        lines.extend([
            "",
            "## ROI Analysis",
            "",
            f"- **Overall ROI:** {report.roi_analysis.overall_roi:.2f}",
            f"- **Payback Period:** {report.roi_analysis.payback_period_months:.1f} months",
            f"- **Total Effort:** {report.roi_analysis.total_effort_hours:.1f} hours",
            "",
            "## Time Projection",
            "",
            f"- **Current Debt:** {report.time_projection.current_debt_hours:.1f} hours",
            f"- **Projected ({report.time_projection.time_horizon}):** {report.time_projection.projected_debt_hours:.1f} hours",
            f"- **Growth:** {report.time_projection.growth_percentage:.1f}%",
            "",
        ])

        if report.prioritized_items:
            lines.extend(["## Top Priority Items", ""])
            for i, item in enumerate(report.prioritized_items[:10], 1):
                lines.extend([
                    f"### {i}. {item.description}",
                    "",
                    f"- **Location:** `{item.location}`",
                    f"- **Type:** {item.debt_type}",
                    f"- **Severity:** {item.severity}",
                    f"- **Effort:** {item.effort_hours:.1f} hours",
                    f"- **Strategy:** {item.remediation_strategy}",
                    "",
                ])

        return "\n".join(lines)
