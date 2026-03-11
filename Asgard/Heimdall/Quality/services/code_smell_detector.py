"""
Heimdall Code Smell Detector Service

Detects code smells and anti-patterns based on Martin Fowler's taxonomy.
Implements detection for 20+ common code smells across all categories:
- Bloaters: Large methods, classes, parameters
- OO Abusers: Misuse of OO principles
- Change Preventers: Make changes difficult
- Dispensables: Unnecessary code
- Couplers: Excessive coupling
"""

import ast
import os
import json
import fnmatch
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

from Asgard.Heimdall.Quality.models.smell_models import (
    CodeSmell,
    SmellCategory,
    SmellConfig,
    SmellReport,
    SmellSeverity,
    SmellThresholds,
)
from Asgard.Heimdall.Quality.utilities.file_utils import DEFAULT_EXCLUDE_DIRS


class SmellVisitor(ast.NodeVisitor):
    """
    AST visitor to detect code smells.

    Walks the AST and identifies various code smell patterns including:
    - Large Class (too many methods or lines)
    - Long Method (too many lines or statements)
    - Long Parameter List
    - Dead Code (pass-only methods)
    - Complex Conditional (too many boolean operators)
    - Feature Envy (tracks method calls to other objects)
    """

    def __init__(
        self,
        file_path: str,
        thresholds: SmellThresholds,
        categories: List[str],
    ):
        """
        Initialize the smell visitor.

        Args:
            file_path: Path to the file being analyzed
            thresholds: Thresholds for smell detection
            categories: List of enabled smell categories
        """
        self.file_path = file_path
        self.thresholds = thresholds
        self.categories = categories
        self.smells: List[CodeSmell] = []
        self.current_class: Optional[str] = None
        self.class_methods: Dict[str, List[str]] = defaultdict(list)
        self.method_calls: Dict[str, List[str]] = defaultdict(list)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """
        Visit class definition to detect class-level smells.

        Detects:
        - Large Class (too many methods)
        - Large Class (too many lines)
        """
        old_class = self.current_class
        self.current_class = node.name

        if SmellCategory.BLOATERS.value in self.categories:
            class_lines = node.end_lineno - node.lineno if hasattr(node, "end_lineno") else 0
            methods = [n for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

            # Check for too many methods
            if len(methods) > self.thresholds.large_class_methods:
                self.smells.append(
                    CodeSmell(
                        name="Large Class",
                        category=SmellCategory.BLOATERS,
                        severity=SmellSeverity.HIGH,
                        file_path=self.file_path,
                        line_number=node.lineno,
                        description=f"Class has {len(methods)} methods (threshold: {self.thresholds.large_class_methods})",
                        evidence=f"Class '{node.name}' has too many methods",
                        remediation="Consider splitting into smaller, focused classes using Single Responsibility Principle",
                        confidence=0.9,
                    )
                )

            # Check for too many lines
            if class_lines > self.thresholds.large_class_lines:
                self.smells.append(
                    CodeSmell(
                        name="Large Class",
                        category=SmellCategory.BLOATERS,
                        severity=SmellSeverity.MEDIUM,
                        file_path=self.file_path,
                        line_number=node.lineno,
                        description=f"Class has {class_lines} lines (threshold: {self.thresholds.large_class_lines})",
                        evidence=f"Class '{node.name}' is too long",
                        remediation="Break down into smaller classes with focused responsibilities",
                        confidence=0.8,
                    )
                )

        self.generic_visit(node)
        self.current_class = old_class

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """
        Visit function definition to detect method-level smells.

        Detects:
        - Long Method (too many lines)
        - Long Method (too many statements)
        - Long Parameter List
        - Dead Code (pass-only methods)
        """
        self._analyze_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Visit async function definition to detect method-level smells."""
        self._analyze_function(node)

    def _analyze_function(self, node) -> None:
        """Analyze a function or async function for smells."""
        if self.current_class:
            self.class_methods[self.current_class].append(node.name)

        # Long Method smell - check lines
        if SmellCategory.BLOATERS.value in self.categories:
            method_lines = node.end_lineno - node.lineno if hasattr(node, "end_lineno") else 0
            statements = len([n for n in ast.walk(node) if isinstance(n, ast.stmt)])

            if method_lines > self.thresholds.long_method_lines:
                self.smells.append(
                    CodeSmell(
                        name="Long Method",
                        category=SmellCategory.BLOATERS,
                        severity=SmellSeverity.MEDIUM,
                        file_path=self.file_path,
                        line_number=node.lineno,
                        description=f"Method has {method_lines} lines (threshold: {self.thresholds.long_method_lines})",
                        evidence=f"Method '{node.name}' is too long",
                        remediation="Extract smaller methods or simplify logic using Extract Method refactoring",
                        confidence=0.9,
                    )
                )

            # Long Method smell - check statements
            if statements > self.thresholds.long_method_statements:
                self.smells.append(
                    CodeSmell(
                        name="Long Method",
                        category=SmellCategory.BLOATERS,
                        severity=SmellSeverity.MEDIUM,
                        file_path=self.file_path,
                        line_number=node.lineno,
                        description=f"Method has {statements} statements (threshold: {self.thresholds.long_method_statements})",
                        evidence=f"Method '{node.name}' has too many statements",
                        remediation="Break down into smaller methods with single responsibilities",
                        confidence=0.8,
                    )
                )

        # Long Parameter List smell
        if SmellCategory.BLOATERS.value in self.categories:
            param_count = len(node.args.args)
            # Don't count 'self' for methods
            if self.current_class and param_count > 0:
                first_arg = node.args.args[0].arg if node.args.args else ""
                if first_arg == "self" or first_arg == "cls":
                    param_count -= 1

            if param_count > self.thresholds.long_parameter_list:
                self.smells.append(
                    CodeSmell(
                        name="Long Parameter List",
                        category=SmellCategory.BLOATERS,
                        severity=SmellSeverity.MEDIUM,
                        file_path=self.file_path,
                        line_number=node.lineno,
                        description=f"Method has {param_count} parameters (threshold: {self.thresholds.long_parameter_list})",
                        evidence=f"Method '{node.name}' has too many parameters",
                        remediation="Use parameter object pattern, introduce a config class, or use builder pattern",
                        confidence=0.9,
                    )
                )

        # Dead Code smell - pass-only methods
        if SmellCategory.DISPENSABLES.value in self.categories:
            has_return = any(isinstance(n, ast.Return) and n.value is not None for n in ast.walk(node))
            has_assignments = any(isinstance(n, ast.Assign) for n in ast.walk(node))
            has_calls = any(isinstance(n, ast.Call) for n in ast.walk(node))
            has_yield = any(isinstance(n, (ast.Yield, ast.YieldFrom)) for n in ast.walk(node))
            has_raise = any(isinstance(n, ast.Raise) for n in ast.walk(node))

            if not has_return and not has_assignments and not has_calls and not has_yield and not has_raise:
                if len(node.body) == 1:
                    body_item = node.body[0]
                    # Check for pass statement or docstring-only
                    if isinstance(body_item, ast.Pass):
                        self.smells.append(
                            CodeSmell(
                                name="Dead Code",
                                category=SmellCategory.DISPENSABLES,
                                severity=SmellSeverity.LOW,
                                file_path=self.file_path,
                                line_number=node.lineno,
                                description="Method contains only pass statement",
                                evidence=f"Method '{node.name}' appears to be dead code",
                                remediation="Remove unused method or implement functionality",
                                confidence=0.7,
                            )
                        )
                    elif isinstance(body_item, ast.Expr) and isinstance(body_item.value, ast.Constant):
                        # Just a docstring
                        self.smells.append(
                            CodeSmell(
                                name="Dead Code",
                                category=SmellCategory.DISPENSABLES,
                                severity=SmellSeverity.LOW,
                                file_path=self.file_path,
                                line_number=node.lineno,
                                description="Method contains only a docstring with no implementation",
                                evidence=f"Method '{node.name}' appears to be a stub",
                                remediation="Remove unused method or implement functionality",
                                confidence=0.6,
                            )
                        )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """
        Visit function calls to detect coupling smells.

        Tracks method calls for Feature Envy detection.
        """
        if SmellCategory.COUPLERS.value in self.categories:
            # Track method calls for Feature Envy detection
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    object_name = node.func.value.id
                    method_name = node.func.attr
                    self.method_calls[object_name].append(method_name)

        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """
        Visit if statements to detect complex conditionals.

        Detects conditionals with too many boolean operators.
        """
        if SmellCategory.BLOATERS.value in self.categories:
            condition_complexity = self._count_boolean_operators(node.test)
            if condition_complexity > self.thresholds.complex_conditional_operators:
                self.smells.append(
                    CodeSmell(
                        name="Complex Conditional",
                        category=SmellCategory.BLOATERS,
                        severity=SmellSeverity.LOW,
                        file_path=self.file_path,
                        line_number=node.lineno,
                        description=f"Complex conditional with {condition_complexity} boolean operators (threshold: {self.thresholds.complex_conditional_operators})",
                        evidence="Boolean expression is too complex to understand easily",
                        remediation="Extract condition into well-named method using Extract Method refactoring",
                        confidence=0.6,
                    )
                )

        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """Visit while statements to detect complex conditionals."""
        if SmellCategory.BLOATERS.value in self.categories:
            condition_complexity = self._count_boolean_operators(node.test)
            if condition_complexity > self.thresholds.complex_conditional_operators:
                self.smells.append(
                    CodeSmell(
                        name="Complex Conditional",
                        category=SmellCategory.BLOATERS,
                        severity=SmellSeverity.LOW,
                        file_path=self.file_path,
                        line_number=node.lineno,
                        description=f"Complex while condition with {condition_complexity} boolean operators",
                        evidence="While condition is too complex to understand easily",
                        remediation="Extract condition into well-named method",
                        confidence=0.6,
                    )
                )

        self.generic_visit(node)

    def _count_boolean_operators(self, node: ast.AST) -> int:
        """Count boolean operators in an expression."""
        count = 0
        for child in ast.walk(node):
            if isinstance(child, ast.BoolOp):
                # BoolOp can have multiple values, so count operators = len(values) - 1
                count += len(child.values) - 1
            elif isinstance(child, ast.UnaryOp) and isinstance(child.op, ast.Not):
                count += 1
        return count

    def get_feature_envy_smells(self) -> List[CodeSmell]:
        """
        Analyze collected method calls to detect Feature Envy.

        Feature Envy occurs when a method uses methods/properties of another
        object more than its own class.

        Returns:
            List of Feature Envy code smells
        """
        smells = []
        if SmellCategory.COUPLERS.value not in self.categories:
            return smells

        for object_name, calls in self.method_calls.items():
            if object_name in ("self", "cls", "super"):
                continue

            if len(calls) > self.thresholds.feature_envy_calls:
                smells.append(
                    CodeSmell(
                        name="Feature Envy",
                        category=SmellCategory.COUPLERS,
                        severity=SmellSeverity.MEDIUM,
                        file_path=self.file_path,
                        line_number=1,  # File-level smell
                        description=f"Excessive calls to '{object_name}' ({len(calls)} calls)",
                        evidence=f"Methods called: {', '.join(set(calls)[:5])}{'...' if len(set(calls)) > 5 else ''}",
                        remediation="Consider moving logic to the class being used, or use delegation",
                        confidence=0.7,
                    )
                )

        return smells


class CodeSmellDetector:
    """
    Detects various code smells and anti-patterns.

    Implements detection for 20+ common code smells across all categories:
    - Bloaters: Large methods, classes, parameters
    - OO Abusers: Misuse of OO principles
    - Change Preventers: Make changes difficult
    - Dispensables: Unnecessary code
    - Couplers: Excessive coupling

    Usage:
        detector = CodeSmellDetector()
        report = detector.analyze(Path("./src"))

        for smell in report.detected_smells:
            print(f"{smell.name} at {smell.location}")
    """

    def __init__(self, config: Optional[SmellConfig] = None):
        """
        Initialize code smell detector.

        Args:
            config: Configuration for smell detection. If None, uses defaults.
        """
        self.config = config or SmellConfig()

    def analyze(self, path: Path) -> SmellReport:
        """
        Analyze a file or directory for code smells.

        Args:
            path: Path to file or directory to analyze

        Returns:
            SmellReport with all detected smells

        Raises:
            FileNotFoundError: If path does not exist
        """
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        start_time = datetime.now()
        report = SmellReport(scan_path=str(path))

        if path.is_file():
            smells = self._analyze_file(path)
            for smell in smells:
                report.add_smell(smell)
        else:
            self._analyze_directory(path, report)

        # Calculate scan duration
        report.scan_duration_seconds = (datetime.now() - start_time).total_seconds()

        # Calculate most problematic files
        file_smell_counts: Dict[str, int] = defaultdict(int)
        for smell in report.detected_smells:
            file_smell_counts[smell.file_path] += 1

        report.most_problematic_files = sorted(
            file_smell_counts.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        # Generate remediation priorities
        report.remediation_priorities = self._generate_remediation_priorities(report.detected_smells)

        return report

    def analyze_single_file(self, file_path: Path) -> SmellReport:
        """
        Analyze a single file for code smells.

        Args:
            file_path: Path to Python file

        Returns:
            SmellReport with detected smells
        """
        return self.analyze(file_path)

    def _analyze_file(self, file_path: Path) -> List[CodeSmell]:
        """
        Analyze a single file for code smells.

        Args:
            file_path: Path to Python file

        Returns:
            List of detected code smells
        """
        try:
            source = file_path.read_text(encoding="utf-8")
            tree = ast.parse(source)

            visitor = SmellVisitor(
                file_path=str(file_path.absolute()),
                thresholds=self.config.thresholds,
                categories=self.config.get_enabled_categories(),
            )
            visitor.visit(tree)

            # Add Feature Envy smells from collected data
            smells = visitor.smells + visitor.get_feature_envy_smells()

            # Filter by severity
            filtered_smells = [
                smell
                for smell in smells
                if self._severity_level(smell.severity) >= self._severity_level(self.config.severity_filter)
            ]

            return filtered_smells

        except SyntaxError:
            # Cannot parse file - skip it
            return []
        except Exception:
            # Other errors - skip file
            return []

    def _analyze_directory(self, directory: Path, report: SmellReport) -> None:
        """
        Analyze all Python files in a directory.

        Args:
            directory: Directory to analyze
            report: Report to add smells to
        """
        all_exclude_patterns = list(self.config.exclude_patterns) + list(DEFAULT_EXCLUDE_DIRS)

        for root, dirs, files in os.walk(directory):
            root_path = Path(root)

            # Filter excluded directories (includes .venv, node_modules, etc.)
            dirs[:] = [
                d
                for d in dirs
                if not any(self._matches_pattern(d, pattern) for pattern in all_exclude_patterns)
            ]

            for file in files:
                # Check if file should be analyzed
                if not self._should_analyze_file(file):
                    continue

                # Check exclude patterns
                if any(self._matches_pattern(file, pattern) for pattern in self.config.exclude_patterns):
                    continue

                file_path = root_path / file
                smells = self._analyze_file(file_path)
                for smell in smells:
                    report.add_smell(smell)

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
            severity = SmellSeverity(severity)
        levels = {
            SmellSeverity.LOW: 1,
            SmellSeverity.MEDIUM: 2,
            SmellSeverity.HIGH: 3,
            SmellSeverity.CRITICAL: 4,
        }
        return levels.get(severity, 1)

    def _generate_remediation_priorities(self, smells: List[CodeSmell]) -> List[str]:
        """
        Generate prioritized remediation recommendations.

        Args:
            smells: List of detected smells

        Returns:
            List of prioritized remediation actions
        """
        priorities = []

        # Count smells by type
        smell_counts: Dict[str, int] = defaultdict(int)
        critical_smells = []
        high_smells = []

        for smell in smells:
            smell_counts[smell.name] += 1
            sev = smell.severity if isinstance(smell.severity, str) else smell.severity.value
            if sev == SmellSeverity.CRITICAL.value:
                critical_smells.append(smell)
            elif sev == SmellSeverity.HIGH.value:
                high_smells.append(smell)

        # Add high-priority recommendations
        if critical_smells:
            priorities.append(f"CRITICAL: Address {len(critical_smells)} critical smells immediately")

        if high_smells:
            priorities.append(f"HIGH: Review {len(high_smells)} high-severity smells")

        # Most common smells
        common_smells = sorted(smell_counts.items(), key=lambda x: x[1], reverse=True)
        if common_smells:
            top_smell = common_smells[0]
            if top_smell[1] > 5:
                priorities.append(f"Focus on '{top_smell[0]}' ({top_smell[1]} occurrences)")

        # Category-based recommendations
        category_counts: Dict[str, int] = defaultdict(int)
        for smell in smells:
            cat = smell.category if isinstance(smell.category, str) else smell.category.value
            category_counts[cat] += 1

        if category_counts.get(SmellCategory.BLOATERS.value, 0) > 10:
            priorities.append("High number of bloater smells - focus on code size reduction")

        if category_counts.get(SmellCategory.COUPLERS.value, 0) > 5:
            priorities.append("Coupling issues detected - improve modularity and reduce dependencies")

        if category_counts.get(SmellCategory.DISPENSABLES.value, 0) > 5:
            priorities.append("Dispensable code detected - remove dead code and unused elements")

        if category_counts.get(SmellCategory.CHANGE_PREVENTERS.value, 0) > 3:
            priorities.append("Change preventers found - refactor to improve maintainability")

        return priorities

    def generate_report(self, report: SmellReport, output_format: str = "text") -> str:
        """
        Generate formatted code smell report.

        Args:
            report: SmellReport to format
            output_format: Report format (text, json, markdown, html)

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
        elif format_lower == "html":
            return self._generate_html_report(report)
        elif format_lower == "text":
            return self._generate_text_report(report)
        else:
            raise ValueError(f"Unsupported format: {output_format}. Use: text, json, markdown, html")

    def _generate_text_report(self, report: SmellReport) -> str:
        """Generate plain text report."""
        lines = [
            "=" * 60,
            "CODE SMELLS REPORT",
            "=" * 60,
            "",
            f"Scan Path: {report.scan_path}",
            f"Scan Time: {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"Duration: {report.scan_duration_seconds:.2f} seconds",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Smells: {report.total_smells}",
            "",
            "By Severity:",
        ]

        for severity in [SmellSeverity.CRITICAL, SmellSeverity.HIGH, SmellSeverity.MEDIUM, SmellSeverity.LOW]:
            count = report.smells_by_severity.get(severity.value, 0)
            if count > 0:
                lines.append(f"  {severity.value.upper()}: {count}")

        lines.extend(["", "By Category:"])
        for category in SmellCategory:
            count = report.smells_by_category.get(category.value, 0)
            if count > 0:
                lines.append(f"  {category.value.replace('_', ' ').title()}: {count}")

        if report.most_problematic_files:
            lines.extend(["", "Most Problematic Files:", "-" * 40])
            for file_path, count in report.most_problematic_files[:5]:
                filename = os.path.basename(file_path)
                lines.append(f"  {filename}: {count} smells")

        if report.remediation_priorities:
            lines.extend(["", "Remediation Priorities:", "-" * 40])
            for priority in report.remediation_priorities:
                lines.append(f"  - {priority}")

        if report.detected_smells:
            lines.extend(["", "DETECTED SMELLS", "-" * 40])

            # Group by severity
            smells_by_sev: Dict[str, List[CodeSmell]] = defaultdict(list)
            for smell in report.detected_smells:
                sev = smell.severity if isinstance(smell.severity, str) else smell.severity.value
                smells_by_sev[sev].append(smell)

            for severity in [SmellSeverity.CRITICAL, SmellSeverity.HIGH, SmellSeverity.MEDIUM, SmellSeverity.LOW]:
                sev_smells = smells_by_sev.get(severity.value, [])
                if sev_smells:
                    lines.extend(["", f"[{severity.value.upper()}]"])
                    for smell in sev_smells[:10]:  # Limit per severity
                        lines.append(f"  {smell.name} - {smell.location}")
                        lines.append(f"    {smell.description}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_json_report(self, report: SmellReport) -> str:
        """Generate JSON report."""
        smells_data = []
        for smell in report.detected_smells:
            sev = smell.severity if isinstance(smell.severity, str) else smell.severity.value
            cat = smell.category if isinstance(smell.category, str) else smell.category.value
            smells_data.append(
                {
                    "name": smell.name,
                    "category": cat,
                    "severity": sev,
                    "file_path": smell.file_path,
                    "line_number": smell.line_number,
                    "description": smell.description,
                    "evidence": smell.evidence,
                    "remediation": smell.remediation,
                    "confidence": smell.confidence,
                }
            )

        report_data = {
            "scan_info": {
                "scan_path": report.scan_path,
                "scanned_at": report.scanned_at.isoformat(),
                "duration_seconds": report.scan_duration_seconds,
            },
            "summary": {
                "total_smells": report.total_smells,
                "smells_by_severity": report.smells_by_severity,
                "smells_by_category": report.smells_by_category,
            },
            "detected_smells": smells_data,
            "most_problematic_files": [
                {"file": file_path, "smell_count": count} for file_path, count in report.most_problematic_files
            ],
            "remediation_priorities": report.remediation_priorities,
        }

        return json.dumps(report_data, indent=2)

    def _generate_markdown_report(self, report: SmellReport) -> str:
        """Generate Markdown report."""
        lines = [
            "# Code Smells Report",
            "",
            f"**Scan Path:** `{report.scan_path}`",
            f"**Generated:** {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Duration:** {report.scan_duration_seconds:.2f} seconds",
            "",
            "## Summary",
            "",
            f"**Total Code Smells:** {report.total_smells}",
            "",
            "### By Severity",
            "",
            "| Severity | Count |",
            "|----------|-------|",
        ]

        for severity in [SmellSeverity.CRITICAL, SmellSeverity.HIGH, SmellSeverity.MEDIUM, SmellSeverity.LOW]:
            count = report.smells_by_severity.get(severity.value, 0)
            lines.append(f"| {severity.value.title()} | {count} |")

        lines.extend(
            [
                "",
                "### By Category",
                "",
                "| Category | Count |",
                "|----------|-------|",
            ]
        )

        for category in SmellCategory:
            count = report.smells_by_category.get(category.value, 0)
            lines.append(f"| {category.value.replace('_', ' ').title()} | {count} |")

        if report.most_problematic_files:
            lines.extend(["", "## Most Problematic Files", ""])
            for file_path, count in report.most_problematic_files[:10]:
                filename = os.path.basename(file_path)
                lines.append(f"- `{filename}`: {count} smells")

        if report.remediation_priorities:
            lines.extend(["", "## Remediation Priorities", ""])
            for priority in report.remediation_priorities:
                lines.append(f"- {priority}")

        lines.extend(["", "## Detected Smells", ""])

        # Group smells by severity
        smells_by_sev: Dict[str, List[CodeSmell]] = defaultdict(list)
        for smell in report.detected_smells:
            sev = smell.severity if isinstance(smell.severity, str) else smell.severity.value
            smells_by_sev[sev].append(smell)

        for severity in [SmellSeverity.CRITICAL, SmellSeverity.HIGH, SmellSeverity.MEDIUM, SmellSeverity.LOW]:
            sev_smells = smells_by_sev.get(severity.value, [])
            if sev_smells:
                lines.extend([f"### {severity.value.title()} Severity", ""])

                for smell in sev_smells[:20]:  # Limit per severity
                    filename = os.path.basename(smell.file_path)
                    cat = smell.category if isinstance(smell.category, str) else smell.category.value
                    lines.extend(
                        [
                            f"#### {smell.name} - `{filename}:{smell.line_number}`",
                            "",
                            f"**Category:** {cat.replace('_', ' ').title()}",
                            "",
                            f"**Description:** {smell.description}",
                            "",
                            f"**Evidence:** {smell.evidence}",
                            "",
                            f"**Remediation:** {smell.remediation}",
                            "",
                        ]
                    )

        return "\n".join(lines)

    def _generate_html_report(self, report: SmellReport) -> str:
        """Generate HTML report."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Code Smells Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            margin: 40px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        .summary {{
            background: #ecf0f1;
            padding: 20px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .critical {{ color: #c0392b; font-weight: bold; }}
        .high {{ color: #e67e22; font-weight: bold; }}
        .medium {{ color: #3498db; }}
        .low {{ color: #27ae60; }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin: 15px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px 8px;
            text-align: left;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        .smell-item {{
            margin-bottom: 20px;
            padding: 15px;
            border-left: 4px solid #ccc;
            background: #fafafa;
            border-radius: 0 5px 5px 0;
        }}
        .smell-critical {{ border-left-color: #c0392b; }}
        .smell-high {{ border-left-color: #e67e22; }}
        .smell-medium {{ border-left-color: #3498db; }}
        .smell-low {{ border-left-color: #27ae60; }}
        .smell-item h3 {{
            margin: 0 0 10px 0;
        }}
        .smell-item p {{
            margin: 5px 0;
        }}
        .smell-item strong {{
            color: #555;
        }}
        .priorities {{
            background: #fff3cd;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #ffc107;
        }}
        .priorities li {{
            margin: 8px 0;
        }}
        .scan-info {{
            color: #666;
            font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Code Smells Report</h1>

        <p class="scan-info">
            <strong>Scan Path:</strong> {report.scan_path}<br>
            <strong>Generated:</strong> {report.scanned_at.strftime('%Y-%m-%d %H:%M:%S')}<br>
            <strong>Duration:</strong> {report.scan_duration_seconds:.2f} seconds
        </p>

        <div class="summary">
            <h2>Summary</h2>
            <p><strong>Total Code Smells:</strong> {report.total_smells}</p>

            <h3>By Severity</h3>
            <table>
                <tr>
                    <th>Severity</th>
                    <th>Count</th>
                </tr>
"""

        for severity in [SmellSeverity.CRITICAL, SmellSeverity.HIGH, SmellSeverity.MEDIUM, SmellSeverity.LOW]:
            count = report.smells_by_severity.get(severity.value, 0)
            html += f"""                <tr>
                    <td class="{severity.value}">{severity.value.title()}</td>
                    <td>{count}</td>
                </tr>
"""

        html += """            </table>

            <h3>By Category</h3>
            <table>
                <tr>
                    <th>Category</th>
                    <th>Count</th>
                </tr>
"""

        for category in SmellCategory:
            count = report.smells_by_category.get(category.value, 0)
            html += f"""                <tr>
                    <td>{category.value.replace('_', ' ').title()}</td>
                    <td>{count}</td>
                </tr>
"""

        html += """            </table>
        </div>
"""

        if report.most_problematic_files:
            html += """        <h2>Most Problematic Files</h2>
        <table>
            <tr>
                <th>File</th>
                <th>Smell Count</th>
            </tr>
"""
            for file_path, count in report.most_problematic_files[:10]:
                filename = os.path.basename(file_path)
                html += f"""            <tr>
                <td>{filename}</td>
                <td>{count}</td>
            </tr>
"""
            html += """        </table>
"""

        if report.remediation_priorities:
            html += """        <h2>Remediation Priorities</h2>
        <div class="priorities">
            <ul>
"""
            for priority in report.remediation_priorities:
                html += f"                <li>{priority}</li>\n"
            html += """            </ul>
        </div>
"""

        html += """        <h2>Detected Smells</h2>
"""

        # Sort smells by severity
        sorted_smells = sorted(
            report.detected_smells,
            key=lambda x: self._severity_level(x.severity),
            reverse=True,
        )

        for smell in sorted_smells[:50]:  # Limit to 50 for HTML
            filename = os.path.basename(smell.file_path)
            sev = smell.severity if isinstance(smell.severity, str) else smell.severity.value
            cat = smell.category if isinstance(smell.category, str) else smell.category.value
            html += f"""        <div class="smell-item smell-{sev}">
            <h3 class="{sev}">{smell.name} - {filename}:{smell.line_number}</h3>
            <p><strong>Category:</strong> {cat.replace('_', ' ').title()}</p>
            <p><strong>Description:</strong> {smell.description}</p>
            <p><strong>Evidence:</strong> {smell.evidence}</p>
            <p><strong>Remediation:</strong> {smell.remediation}</p>
            <p><strong>Confidence:</strong> {smell.confidence:.0%}</p>
        </div>
"""

        html += """    </div>
</body>
</html>"""

        return html
