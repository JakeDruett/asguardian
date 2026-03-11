"""
Heimdall Cohesion Analyzer Service

Analyzes Python code for cohesion metrics:
- LCOM (Lack of Cohesion of Methods): Measures how related methods are
- LCOM4 (Henderson-Sellers variant): Alternative cohesion calculation

Low cohesion (high LCOM) indicates:
- Class is doing too many unrelated things
- Should potentially be split into multiple classes
- Methods don't work together on shared data

LCOM Calculation (Chidamber-Kemerer):
- P = pairs of methods that don't share instance variables
- Q = pairs of methods that share at least one instance variable
- LCOM = (P - Q) / max(P - Q, 0) if P > Q, else 0

LCOM4 Calculation (Henderson-Sellers):
- LCOM4 = (m - sum(mA)/a) / (m - 1)
- Where m = number of methods, a = number of attributes
- mA = number of methods accessing attribute A
"""

import ast
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from Asgard.Heimdall.OOP.models.oop_models import (
    ClassCohesionMetrics,
    CohesionLevel,
    OOPConfig,
    OOPSeverity,
)
from Asgard.Heimdall.OOP.utilities.class_utils import (
    ClassInfo,
    extract_classes_from_file,
    get_class_methods,
    get_class_attributes,
    MethodInfo,
)
from Asgard.Heimdall.Quality.utilities.file_utils import scan_directory


class CohesionAnalyzer:
    """
    Analyzes Python code for class cohesion metrics.

    Cohesion measures how closely the methods of a class are related
    to each other. High cohesion is desirable - it means the class
    has a single, well-defined purpose.

    LCOM (Lack of Cohesion of Methods):
    - 0.0 = Perfect cohesion (all methods share attributes)
    - 1.0 = No cohesion (no methods share attributes)
    """

    def __init__(self, config: Optional[OOPConfig] = None):
        """Initialize the cohesion analyzer."""
        self.config = config or OOPConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> List[ClassCohesionMetrics]:
        """
        Analyze cohesion metrics for all classes in the path.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            List of ClassCohesionMetrics for each class
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        results: List[ClassCohesionMetrics] = []

        # Build exclude patterns
        exclude_patterns = list(self.config.exclude_patterns)
        if not self.config.include_tests:
            exclude_patterns.extend(["test_", "_test.py", "tests/", "conftest.py"])

        for file_path in scan_directory(
            path,
            exclude_patterns=exclude_patterns,
            include_extensions=self.config.include_extensions,
        ):
            try:
                file_results = self._analyze_file(file_path, path)
                results.extend(file_results)
            except (SyntaxError, Exception):
                continue

        return results

    def _analyze_file(self, file_path: Path, root_path: Path) -> List[ClassCohesionMetrics]:
        """Analyze cohesion for all classes in a file."""
        classes = extract_classes_from_file(file_path)
        results = []

        for cls in classes:
            metrics = self._analyze_class(cls, file_path, root_path)
            if metrics:
                results.append(metrics)

        return results

    def _analyze_class(
        self, cls: ClassInfo, file_path: Path, root_path: Path
    ) -> Optional[ClassCohesionMetrics]:
        """Analyze cohesion for a single class."""
        # Get methods and attributes
        methods = get_class_methods(cls)
        attributes = get_class_attributes(cls)

        # Filter out special methods for cohesion calculation
        regular_methods = [m for m in methods if not m.name.startswith("_")]

        # If too few methods or attributes, cohesion is undefined
        if len(regular_methods) < 2 or len(attributes) < 1:
            lcom = 0.0
            lcom4 = 0.0
        else:
            # Build method-attribute usage matrix
            method_attr_usage: Dict[str, Set[str]] = {}

            for method in regular_methods:
                method_attr_usage[method.name] = method.accessed_attributes & attributes

            # Calculate LCOM (Chidamber-Kemerer)
            lcom = self._calculate_lcom_ck(method_attr_usage)

            # Calculate LCOM4 (Henderson-Sellers)
            lcom4 = self._calculate_lcom_hs(method_attr_usage, len(attributes))

        cohesion_level = ClassCohesionMetrics.calculate_cohesion_level(lcom)
        severity = ClassCohesionMetrics.calculate_severity(lcom, self.config.lcom_threshold)

        try:
            relative_path = str(file_path.relative_to(root_path))
        except ValueError:
            relative_path = file_path.name

        return ClassCohesionMetrics(
            class_name=cls.name,
            file_path=str(file_path),
            relative_path=relative_path,
            line_number=cls.line_number,
            lcom=lcom,
            lcom4=lcom4,
            method_count=len(methods),
            attribute_count=len(attributes),
            method_attribute_usage={
                m.name: m.accessed_attributes & attributes for m in methods
            },
            cohesion_level=cohesion_level,
            severity=severity,
        )

    def _calculate_lcom_ck(self, method_attr_usage: Dict[str, Set[str]]) -> float:
        """
        Calculate LCOM using Chidamber-Kemerer method.

        LCOM = (P - Q) if P > Q else 0
        Where:
        - P = number of method pairs that don't share any attributes
        - Q = number of method pairs that share at least one attribute

        Normalized to 0-1 range.
        """
        methods = list(method_attr_usage.keys())
        n = len(methods)

        if n < 2:
            return 0.0

        p = 0  # Pairs not sharing attributes
        q = 0  # Pairs sharing attributes

        for i in range(n):
            for j in range(i + 1, n):
                attrs_i = method_attr_usage[methods[i]]
                attrs_j = method_attr_usage[methods[j]]

                if attrs_i & attrs_j:  # Share at least one attribute
                    q += 1
                else:
                    p += 1

        total_pairs = p + q
        if total_pairs == 0:
            return 0.0

        # Normalize: LCOM = P / total_pairs
        # This gives 0 when all pairs share (good) and 1 when none share (bad)
        return p / total_pairs

    def _calculate_lcom_hs(
        self, method_attr_usage: Dict[str, Set[str]], num_attributes: int
    ) -> float:
        """
        Calculate LCOM using Henderson-Sellers method.

        LCOM4 = (m - sum(mA)/a) / (m - 1)
        Where:
        - m = number of methods
        - a = number of attributes
        - mA = number of methods accessing attribute A
        """
        m = len(method_attr_usage)
        a = num_attributes

        if m <= 1 or a == 0:
            return 0.0

        # Count how many methods access each attribute
        attr_access_count: Dict[str, int] = {}

        for method_name, accessed in method_attr_usage.items():
            for attr in accessed:
                attr_access_count[attr] = attr_access_count.get(attr, 0) + 1

        # Sum of mA for all attributes
        sum_ma = sum(attr_access_count.values())

        # LCOM4 = (m - sum_ma/a) / (m - 1)
        lcom4 = (m - sum_ma / a) / (m - 1)

        # Clamp to 0-1 range
        return max(0.0, min(1.0, lcom4))

    def analyze_file(self, file_path: Path) -> List[ClassCohesionMetrics]:
        """
        Analyze cohesion metrics for a single file.

        Args:
            file_path: Path to the Python file

        Returns:
            List of ClassCohesionMetrics for classes in the file
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")

        return self._analyze_file(path, path.parent)

    def get_low_cohesion_classes(
        self, scan_path: Optional[Path] = None, threshold: Optional[float] = None
    ) -> List[ClassCohesionMetrics]:
        """
        Get classes with low cohesion (high LCOM).

        Args:
            scan_path: Root path to scan
            threshold: LCOM threshold (default: config.lcom_threshold)

        Returns:
            List of classes with LCOM above threshold
        """
        threshold = threshold or self.config.lcom_threshold
        metrics = self.analyze(scan_path)

        return [m for m in metrics if m.lcom > threshold]

    def suggest_splits(
        self, cls_metrics: ClassCohesionMetrics
    ) -> List[Tuple[str, Set[str]]]:
        """
        Suggest how to split a low-cohesion class.

        Groups methods by shared attribute access to suggest
        potential class splits.

        Args:
            cls_metrics: Cohesion metrics for the class

        Returns:
            List of (group_name, method_set) tuples
        """
        if cls_metrics.lcom < 0.5:
            # Already reasonably cohesive
            return []

        # Build a graph of methods connected by shared attributes
        methods = list(cls_metrics.method_attribute_usage.keys())
        method_groups: List[Set[str]] = []

        for method in methods:
            attrs = cls_metrics.method_attribute_usage[method]

            # Find existing group that shares attributes
            found_group = False
            for group in method_groups:
                for existing_method in group:
                    existing_attrs = cls_metrics.method_attribute_usage[existing_method]
                    if attrs & existing_attrs:
                        group.add(method)
                        found_group = True
                        break
                if found_group:
                    break

            if not found_group:
                method_groups.append({method})

        # Merge groups that share methods
        merged = True
        while merged:
            merged = False
            for i, group_i in enumerate(method_groups):
                for j, group_j in enumerate(method_groups[i + 1:], i + 1):
                    # Check if groups share any attributes
                    attrs_i = set()
                    for m in group_i:
                        attrs_i.update(cls_metrics.method_attribute_usage[m])

                    attrs_j = set()
                    for m in group_j:
                        attrs_j.update(cls_metrics.method_attribute_usage[m])

                    if attrs_i & attrs_j:
                        method_groups[i] = group_i | group_j
                        method_groups.pop(j)
                        merged = True
                        break
                if merged:
                    break

        # Name the groups
        suggestions = []
        for idx, group in enumerate(method_groups):
            if len(group) >= 2:
                name = f"{cls_metrics.class_name}Part{idx + 1}"
                suggestions.append((name, group))

        return suggestions
