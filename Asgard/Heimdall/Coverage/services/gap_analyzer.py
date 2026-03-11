"""
Heimdall Gap Analyzer Service

Analyzes test coverage gaps in the codebase.
"""

import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from Asgard.Heimdall.Coverage.models.coverage_models import (
    ClassCoverage,
    CoverageConfig,
    CoverageGap,
    CoverageMetrics,
    CoverageSeverity,
    MethodInfo,
    MethodType,
)
from Asgard.Heimdall.Coverage.utilities.method_extractor import (
    extract_methods,
    extract_classes_with_methods,
    find_test_methods,
)
from Asgard.Heimdall.Quality.utilities.file_utils import scan_directory


class GapAnalyzer:
    """
    Analyzes test coverage gaps in Python code.

    Identifies:
    - Uncovered methods
    - Partially covered classes
    - Complex code without tests
    - Critical paths without coverage
    """

    def __init__(self, config: Optional[CoverageConfig] = None):
        """Initialize the gap analyzer."""
        self.config = config or CoverageConfig()

    def analyze(
        self,
        scan_path: Optional[Path] = None,
        test_path: Optional[Path] = None
    ) -> tuple:
        """
        Analyze test coverage gaps.

        Args:
            scan_path: Root path to scan for source code
            test_path: Path to test files

        Returns:
            Tuple of (gaps, metrics, class_coverage)
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        # Find test paths
        test_paths = self._find_test_paths(path, test_path)

        # Collect source methods
        source_methods = self._collect_source_methods(path)

        # Collect test methods
        test_methods = self._collect_test_methods(test_paths)

        # Analyze coverage
        gaps, metrics = self._analyze_gaps(source_methods, test_methods)

        # Analyze class coverage
        class_coverage = self._analyze_class_coverage(path, test_methods)

        return gaps, metrics, class_coverage

    def _find_test_paths(
        self,
        scan_path: Path,
        test_path: Optional[Path]
    ) -> List[Path]:
        """Find all test directories."""
        test_paths = list(self.config.test_paths)

        if test_path:
            test_paths.append(test_path)

        # Auto-detect test directories
        for pattern in ["tests", "test", "Tests", "Test"]:
            potential = scan_path / pattern
            if potential.exists() and potential not in test_paths:
                test_paths.append(potential)

        return test_paths

    def _collect_source_methods(self, path: Path) -> List[MethodInfo]:
        """Collect all source methods."""
        methods = []

        # Build exclude patterns - exclude test files
        exclude_patterns = list(self.config.exclude_patterns)
        exclude_patterns.extend(["test_", "_test.py", "tests/", "conftest.py"])

        for file_path in scan_directory(
            path,
            exclude_patterns=exclude_patterns,
            include_extensions=self.config.include_extensions,
        ):
            try:
                source = file_path.read_text(encoding="utf-8", errors="ignore")
                file_methods = extract_methods(source, str(file_path))

                # Filter based on config
                for method in file_methods:
                    if not self.config.include_private and method.method_type == MethodType.PRIVATE:
                        continue
                    if not self.config.include_dunder and method.method_type == MethodType.DUNDER:
                        continue
                    methods.append(method)

            except (SyntaxError, Exception):
                continue

        return methods

    def _collect_test_methods(self, test_paths: List[Path]) -> List[MethodInfo]:
        """Collect all test methods."""
        methods = []

        for test_path in test_paths:
            if not test_path.exists():
                continue

            for file_path in scan_directory(
                test_path,
                exclude_patterns=self.config.exclude_patterns,
                include_extensions=[".py"],
            ):
                try:
                    source = file_path.read_text(encoding="utf-8", errors="ignore")
                    test_methods = find_test_methods(source, str(file_path))
                    methods.extend(test_methods)
                except (SyntaxError, Exception):
                    continue

        return methods

    def _analyze_gaps(
        self,
        source_methods: List[MethodInfo],
        test_methods: List[MethodInfo]
    ) -> tuple:
        """Analyze coverage gaps between source and test methods."""
        gaps = []
        metrics = CoverageMetrics()

        # Build test name lookup
        test_names = self._build_test_name_set(test_methods)

        metrics.total_methods = len(source_methods)
        covered_count = 0

        for method in source_methods:
            # Check if method has tests
            is_covered = self._is_method_covered(method, test_names)

            if is_covered:
                covered_count += 1
            else:
                # Create gap
                gap = self._create_gap(method)
                gaps.append(gap)

            # Track branches
            if method.has_branches:
                metrics.total_branches += method.branch_count

        metrics.covered_methods = covered_count

        return gaps, metrics

    def _build_test_name_set(self, test_methods: List[MethodInfo]) -> Set[str]:
        """Build a set of normalized test names."""
        names = set()

        for method in test_methods:
            # Store the full name
            names.add(method.name.lower())

            # Extract what might be tested from the name
            # test_foo_bar -> foo_bar
            if method.name.startswith("test_"):
                tested = method.name[5:].lower()
                names.add(tested)

        return names

    def _is_method_covered(
        self,
        method: MethodInfo,
        test_names: Set[str]
    ) -> bool:
        """Check if a method appears to be covered by tests."""
        method_name = method.name.lower()
        full_name = method.full_name.lower().replace(".", "_")

        # Check various test naming patterns
        patterns = [
            f"test_{method_name}",
            f"test_{full_name}",
            method_name,
            full_name,
        ]

        for pattern in patterns:
            if pattern in test_names:
                return True

        return False

    def _create_gap(self, method: MethodInfo) -> CoverageGap:
        """Create a coverage gap for an uncovered method."""
        severity = self._calculate_severity(method)

        gap_type = "uncovered"
        message = f"Method '{method.full_name}' has no test coverage"

        details = []
        if method.complexity > 5:
            details.append(f"High complexity: {method.complexity}")
        if method.has_branches:
            details.append(f"Has {method.branch_count} branches")
        if method.parameter_count > 3:
            details.append(f"Has {method.parameter_count} parameters")

        return CoverageGap(
            method=method,
            gap_type=gap_type,
            severity=severity,
            message=message,
            details="; ".join(details) if details else "",
        )

    def _calculate_severity(self, method: MethodInfo) -> CoverageSeverity:
        """Calculate severity based on method characteristics."""
        score = 0

        # Complexity adds to severity
        if method.complexity > 10:
            score += 3
        elif method.complexity > 5:
            score += 2
        elif method.complexity > 2:
            score += 1

        # Branches add risk
        if method.branch_count > 5:
            score += 2
        elif method.branch_count > 2:
            score += 1

        # Public methods are more important
        if method.method_type == MethodType.PUBLIC:
            score += 1

        # Async methods are often critical
        if method.is_async:
            score += 1

        # Determine severity
        if score >= 5:
            return CoverageSeverity.CRITICAL
        elif score >= 3:
            return CoverageSeverity.HIGH
        elif score >= 2:
            return CoverageSeverity.MODERATE
        else:
            return CoverageSeverity.LOW

    def _analyze_class_coverage(
        self,
        path: Path,
        test_methods: List[MethodInfo]
    ) -> List[ClassCoverage]:
        """Analyze coverage at the class level."""
        class_coverage = []
        test_names = self._build_test_name_set(test_methods)

        # Build exclude patterns
        exclude_patterns = list(self.config.exclude_patterns)
        exclude_patterns.extend(["test_", "_test.py", "tests/"])

        for file_path in scan_directory(
            path,
            exclude_patterns=exclude_patterns,
            include_extensions=self.config.include_extensions,
        ):
            try:
                source = file_path.read_text(encoding="utf-8", errors="ignore")
                classes = extract_classes_with_methods(source, str(file_path))

                for class_name, methods in classes.items():
                    # Filter methods
                    filtered = [
                        m for m in methods
                        if (self.config.include_private or m.method_type != MethodType.PRIVATE)
                        and (self.config.include_dunder or m.method_type != MethodType.DUNDER)
                    ]

                    if not filtered:
                        continue

                    covered = [
                        m for m in filtered
                        if self._is_method_covered(m, test_names)
                    ]

                    uncovered = [
                        m.name for m in filtered
                        if not self._is_method_covered(m, test_names)
                    ]

                    coverage_pct = (len(covered) / len(filtered)) * 100 if filtered else 100

                    class_coverage.append(ClassCoverage(
                        class_name=class_name,
                        file_path=str(file_path),
                        total_methods=len(filtered),
                        covered_methods=len(covered),
                        uncovered_methods=uncovered,
                        coverage_percent=coverage_pct,
                    ))

            except (SyntaxError, Exception):
                continue

        return class_coverage

    def get_critical_gaps(
        self,
        scan_path: Optional[Path] = None
    ) -> List[CoverageGap]:
        """
        Get only critical and high severity gaps.

        Args:
            scan_path: Root path to scan

        Returns:
            List of critical coverage gaps
        """
        gaps, _, _ = self.analyze(scan_path)

        return [
            g for g in gaps
            if g.severity in (CoverageSeverity.CRITICAL, CoverageSeverity.HIGH)
        ]

    def get_uncovered_classes(
        self,
        scan_path: Optional[Path] = None,
        threshold: float = 50.0
    ) -> List[ClassCoverage]:
        """
        Get classes with coverage below threshold.

        Args:
            scan_path: Root path to scan
            threshold: Minimum coverage percentage

        Returns:
            List of poorly covered classes
        """
        _, _, class_coverage = self.analyze(scan_path)

        return [
            c for c in class_coverage
            if c.coverage_percent < threshold
        ]
