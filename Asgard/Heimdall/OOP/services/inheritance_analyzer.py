"""
Heimdall Inheritance Analyzer Service

Analyzes Python code for inheritance metrics:
- DIT (Depth of Inheritance Tree): Maximum path length from class to root
- NOC (Number of Children): Direct subclass count

Deep inheritance hierarchies can indicate:
- Overly complex class structures
- Potential fragile base class problems
- Difficulty understanding behavior due to inherited methods

High NOC can indicate:
- A class doing too much (god class)
- Potential for many ripple effects on changes
"""

import ast
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from Asgard.Heimdall.OOP.models.oop_models import (
    ClassInheritanceMetrics,
    OOPConfig,
    OOPSeverity,
)
from Asgard.Heimdall.OOP.utilities.class_utils import (
    ClassInfo,
    extract_classes_from_file,
)
from Asgard.Heimdall.Quality.utilities.file_utils import scan_directory


class InheritanceAnalyzer:
    """
    Analyzes Python code for class inheritance metrics.

    Depth of Inheritance Tree (DIT) measures how deep a class is in the
    inheritance hierarchy. High DIT can indicate:
    - Complex behavior inherited from many levels
    - Difficult to understand complete class behavior
    - Potential fragile base class problems

    Number of Children (NOC) measures how many classes directly inherit
    from this class. High NOC can indicate:
    - An overly general base class
    - Potential god class
    - Many classes affected by changes
    """

    def __init__(self, config: Optional[OOPConfig] = None):
        """Initialize the inheritance analyzer."""
        self.config = config or OOPConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> List[ClassInheritanceMetrics]:
        """
        Analyze inheritance metrics for all classes in the path.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            List of ClassInheritanceMetrics for each class
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        # First pass: collect all class info
        all_classes: Dict[str, Dict] = {}  # class_name -> {file, line, bases, info}

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
                classes = extract_classes_from_file(file_path)

                for cls in classes:
                    all_classes[cls.name] = {
                        "file": str(file_path),
                        "relative": str(file_path.relative_to(path)),
                        "line": cls.line_number,
                        "bases": cls.base_classes,
                        "info": cls,
                    }
            except (SyntaxError, Exception):
                continue

        # Build inheritance relationships
        # parent -> [children]
        children_map: Dict[str, List[str]] = {name: [] for name in all_classes}

        for class_name, class_data in all_classes.items():
            for base in class_data["bases"]:
                # Handle qualified names (module.Class)
                base_name = base.split(".")[-1]
                if base_name in children_map:
                    children_map[base_name].append(class_name)

        # Calculate DIT for each class
        dit_cache: Dict[str, int] = {}

        def calculate_dit(class_name: str, visited: Set[str] = None) -> int:
            """Calculate Depth of Inheritance Tree recursively."""
            if visited is None:
                visited = set()

            if class_name in dit_cache:
                return dit_cache[class_name]

            if class_name in visited:
                # Circular inheritance - shouldn't happen but handle gracefully
                return 0

            visited.add(class_name)

            if class_name not in all_classes:
                # External class (like object, Exception, etc.)
                return 0

            bases = all_classes[class_name]["bases"]
            if not bases:
                dit_cache[class_name] = 0
                return 0

            max_parent_dit = 0
            for base in bases:
                base_name = base.split(".")[-1]
                if base_name in all_classes:
                    parent_dit = calculate_dit(base_name, visited.copy())
                    max_parent_dit = max(max_parent_dit, parent_dit)

            dit = max_parent_dit + 1
            dit_cache[class_name] = dit
            return dit

        # Build results
        results: List[ClassInheritanceMetrics] = []

        for class_name, class_data in all_classes.items():
            dit = calculate_dit(class_name)
            noc = len(children_map.get(class_name, []))

            # Get all ancestors
            ancestors = []

            def collect_ancestors(name: str, collected: Set[str] = None):
                if collected is None:
                    collected = set()
                if name not in all_classes:
                    return
                for base in all_classes[name]["bases"]:
                    base_name = base.split(".")[-1]
                    if base_name not in collected:
                        collected.add(base_name)
                        ancestors.append(base_name)
                        collect_ancestors(base_name, collected)

            collect_ancestors(class_name)

            severity = ClassInheritanceMetrics.calculate_severity(
                dit, noc, self.config.dit_threshold, self.config.noc_threshold
            )

            metrics = ClassInheritanceMetrics(
                class_name=class_name,
                file_path=class_data["file"],
                relative_path=class_data["relative"],
                line_number=class_data["line"],
                dit=dit,
                noc=noc,
                base_classes=class_data["bases"],
                direct_subclasses=children_map.get(class_name, []),
                all_ancestors=ancestors,
                severity=severity,
            )

            results.append(metrics)

        return results

    def analyze_file(self, file_path: Path) -> List[ClassInheritanceMetrics]:
        """
        Analyze inheritance metrics for a single file.

        Note: DIT and NOC will be limited to classes within this file.

        Args:
            file_path: Path to the Python file

        Returns:
            List of ClassInheritanceMetrics for classes in the file
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")

        classes = extract_classes_from_file(path)
        class_names = {cls.name for cls in classes}

        # Build inheritance map for this file
        children_map: Dict[str, List[str]] = {cls.name: [] for cls in classes}

        for cls in classes:
            for base in cls.base_classes:
                base_name = base.split(".")[-1]
                if base_name in children_map:
                    children_map[base_name].append(cls.name)

        # Calculate DIT within file
        dit_cache: Dict[str, int] = {}

        def calculate_dit(class_name: str, visited: Set[str] = None) -> int:
            if visited is None:
                visited = set()

            if class_name in dit_cache:
                return dit_cache[class_name]

            if class_name in visited:
                return 0

            visited.add(class_name)

            cls_info = next((c for c in classes if c.name == class_name), None)
            if not cls_info:
                return 0

            if not cls_info.base_classes:
                dit_cache[class_name] = 0
                return 0

            max_parent_dit = 0
            for base in cls_info.base_classes:
                base_name = base.split(".")[-1]
                if base_name in class_names:
                    parent_dit = calculate_dit(base_name, visited.copy())
                    max_parent_dit = max(max_parent_dit, parent_dit)

            dit = max_parent_dit + 1
            dit_cache[class_name] = dit
            return dit

        results = []

        for cls in classes:
            dit = calculate_dit(cls.name)
            noc = len(children_map.get(cls.name, []))

            severity = ClassInheritanceMetrics.calculate_severity(
                dit, noc, self.config.dit_threshold, self.config.noc_threshold
            )

            metrics = ClassInheritanceMetrics(
                class_name=cls.name,
                file_path=str(path),
                relative_path=path.name,
                line_number=cls.line_number,
                dit=dit,
                noc=noc,
                base_classes=cls.base_classes,
                direct_subclasses=children_map.get(cls.name, []),
                all_ancestors=[],  # Would need full project scan
                severity=severity,
            )
            results.append(metrics)

        return results

    def get_inheritance_tree(self, scan_path: Optional[Path] = None) -> Dict[str, List[str]]:
        """
        Get the complete inheritance tree.

        Args:
            scan_path: Root path to scan

        Returns:
            Dictionary mapping parent classes to their children
        """
        metrics = self.analyze(scan_path)

        tree: Dict[str, List[str]] = {}
        for m in metrics:
            if m.direct_subclasses:
                tree[m.class_name] = m.direct_subclasses

        return tree

    def find_root_classes(self, scan_path: Optional[Path] = None) -> List[str]:
        """
        Find classes that have no parents in the scanned codebase.

        Args:
            scan_path: Root path to scan

        Returns:
            List of root class names
        """
        metrics = self.analyze(scan_path)

        all_class_names = {m.class_name for m in metrics}
        roots = []

        for m in metrics:
            # Check if any base class is in our codebase
            has_internal_parent = False
            for base in m.base_classes:
                base_name = base.split(".")[-1]
                if base_name in all_class_names:
                    has_internal_parent = True
                    break

            if not has_internal_parent:
                roots.append(m.class_name)

        return roots
