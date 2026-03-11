"""
Heimdall Coupling Analyzer Service

Analyzes Python code for coupling metrics:
- CBO (Coupling Between Objects): Count of classes this class is coupled to
- Ca (Afferent Coupling): Number of classes that depend on this class
- Ce (Efferent Coupling): Number of classes this class depends on
- I (Instability): Ce / (Ca + Ce) - ranges from 0 (stable) to 1 (unstable)

Coupling occurs when a class:
- Inherits from another class
- Uses another class as a type (parameters, return types, variables)
- Calls methods on another class
- Creates instances of another class
- Accesses attributes of another class
"""

import ast
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

from Asgard.Heimdall.OOP.models.oop_models import (
    ClassCouplingMetrics,
    CouplingLevel,
    OOPConfig,
    OOPSeverity,
)
from Asgard.Heimdall.OOP.utilities.class_utils import (
    ClassInfo,
    extract_classes_from_file,
    get_imports_from_file,
)
from Asgard.Heimdall.Quality.utilities.file_utils import scan_directory


class CouplingVisitor(ast.NodeVisitor):
    """AST visitor that detects coupling between classes."""

    def __init__(self, class_name: str, all_class_names: Set[str], imported_names: Set[str]):
        self.class_name = class_name
        self.all_class_names = all_class_names
        self.imported_names = imported_names
        self.coupled_classes: Set[str] = set()

    def _is_relevant_class(self, name: str) -> bool:
        """Check if a name refers to a relevant class."""
        # It's relevant if it's in our class list or imported
        return name in self.all_class_names or name in self.imported_names

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check inheritance coupling."""
        if node.name != self.class_name:
            # Only process the target class
            return

        # Check base classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                if self._is_relevant_class(base.id) and base.id != self.class_name:
                    self.coupled_classes.add(base.id)
            elif isinstance(base, ast.Attribute):
                if self._is_relevant_class(base.attr) and base.attr != self.class_name:
                    self.coupled_classes.add(base.attr)

        # Visit class body
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Check name references that might be class usages."""
        if self._is_relevant_class(node.id) and node.id != self.class_name:
            self.coupled_classes.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check attribute accesses that might indicate coupling."""
        # Check if accessing a class attribute (e.g., SomeClass.method)
        if isinstance(node.value, ast.Name):
            if self._is_relevant_class(node.value.id) and node.value.id != self.class_name:
                self.coupled_classes.add(node.value.id)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check class instantiation and method calls."""
        if isinstance(node.func, ast.Name):
            # Direct call like SomeClass()
            if self._is_relevant_class(node.func.id) and node.func.id != self.class_name:
                self.coupled_classes.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # Method call like obj.method() - check if obj is a class
            if isinstance(node.func.value, ast.Name):
                if self._is_relevant_class(node.func.value.id) and node.func.value.id != self.class_name:
                    self.coupled_classes.add(node.func.value.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Check type annotations for coupling."""
        self._check_annotation(node.annotation)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function annotations for coupling."""
        # Check return type
        if node.returns:
            self._check_annotation(node.returns)

        # Check parameter types
        for arg in node.args.args:
            if arg.annotation:
                self._check_annotation(arg.annotation)

        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function annotations for coupling."""
        self.visit_FunctionDef(node)

    def _check_annotation(self, annotation: ast.expr) -> None:
        """Check a type annotation for class references."""
        if isinstance(annotation, ast.Name):
            if self._is_relevant_class(annotation.id) and annotation.id != self.class_name:
                self.coupled_classes.add(annotation.id)
        elif isinstance(annotation, ast.Subscript):
            # Handle List[SomeClass], Optional[SomeClass], etc.
            self._check_annotation(annotation.value)
            if isinstance(annotation.slice, ast.Tuple):
                for elt in annotation.slice.elts:
                    self._check_annotation(elt)
            else:
                self._check_annotation(annotation.slice)
        elif isinstance(annotation, ast.Attribute):
            if self._is_relevant_class(annotation.attr) and annotation.attr != self.class_name:
                self.coupled_classes.add(annotation.attr)


class CouplingAnalyzer:
    """
    Analyzes Python code for class coupling metrics.

    Coupling Between Objects (CBO) measures how many other classes a class
    is coupled to. High coupling indicates:
    - Difficult to test in isolation
    - Changes ripple through the codebase
    - Hard to reuse independently
    """

    def __init__(self, config: Optional[OOPConfig] = None):
        """Initialize the coupling analyzer."""
        self.config = config or OOPConfig()

    def analyze(self, scan_path: Optional[Path] = None) -> List[ClassCouplingMetrics]:
        """
        Analyze coupling metrics for all classes in the path.

        Args:
            scan_path: Root path to scan. Uses config path if not provided.

        Returns:
            List of ClassCouplingMetrics for each class
        """
        path = scan_path or self.config.scan_path
        path = Path(path).resolve()

        if not path.exists():
            raise FileNotFoundError(f"Scan path does not exist: {path}")

        start_time = time.time()

        # First pass: collect all class names and file info
        all_classes: Dict[str, Dict] = {}  # class_name -> {file, line, info}
        file_classes: Dict[str, List[ClassInfo]] = {}  # file -> [ClassInfo]
        file_imports: Dict[str, Set[str]] = {}  # file -> imported names

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
                file_classes[str(file_path)] = classes

                # Get imports
                imports, from_imports = get_imports_from_file(file_path)
                imported_names = set()
                for names in from_imports.values():
                    imported_names.update(names)
                file_imports[str(file_path)] = imported_names

                for cls in classes:
                    all_classes[cls.name] = {
                        "file": str(file_path),
                        "relative": str(file_path.relative_to(path)),
                        "line": cls.line_number,
                        "info": cls,
                    }
            except (SyntaxError, Exception):
                continue

        all_class_names = set(all_classes.keys())

        # Second pass: analyze coupling for each class
        results: List[ClassCouplingMetrics] = []
        coupling_to: Dict[str, Set[str]] = {}  # class -> classes it couples to
        coupling_from: Dict[str, Set[str]] = {}  # class -> classes that couple to it

        for class_name, class_data in all_classes.items():
            file_path = Path(class_data["file"])

            try:
                source = file_path.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(source)
            except (SyntaxError, Exception):
                continue

            imported_names = file_imports.get(str(file_path), set())

            # Find the class node and analyze coupling
            visitor = CouplingVisitor(class_name, all_class_names, imported_names)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == class_name:
                    visitor.visit(node)
                    break

            coupling_to[class_name] = visitor.coupled_classes

        # Calculate afferent coupling (who depends on this class)
        for class_name in all_class_names:
            coupling_from[class_name] = set()

        for class_name, coupled_classes in coupling_to.items():
            for coupled in coupled_classes:
                if coupled in coupling_from:
                    coupling_from[coupled].add(class_name)

        # Build results
        for class_name, class_data in all_classes.items():
            ce = len(coupling_to.get(class_name, set()))  # Efferent
            ca = len(coupling_from.get(class_name, set()))  # Afferent
            cbo = ce  # CBO is typically efferent coupling

            # Calculate instability: I = Ce / (Ca + Ce)
            instability = ce / (ca + ce) if (ca + ce) > 0 else 0.0

            coupling_level = ClassCouplingMetrics.calculate_coupling_level(cbo)
            severity = ClassCouplingMetrics.calculate_severity(cbo, self.config.cbo_threshold)

            metrics = ClassCouplingMetrics(
                class_name=class_name,
                file_path=class_data["file"],
                relative_path=class_data["relative"],
                line_number=class_data["line"],
                cbo=cbo,
                afferent_coupling=ca,
                efferent_coupling=ce,
                instability=instability,
                coupled_to=coupling_to.get(class_name, set()),
                coupled_from=coupling_from.get(class_name, set()),
                coupling_level=coupling_level,
                severity=severity,
            )

            results.append(metrics)

        return results

    def analyze_file(self, file_path: Path) -> List[ClassCouplingMetrics]:
        """
        Analyze coupling metrics for a single file.

        Note: This provides limited results since afferent coupling
        requires knowledge of other files.

        Args:
            file_path: Path to the Python file

        Returns:
            List of ClassCouplingMetrics for classes in the file
        """
        path = Path(file_path).resolve()
        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {path}")

        classes = extract_classes_from_file(path)
        all_class_names = {cls.name for cls in classes}
        imports, from_imports = get_imports_from_file(path)
        imported_names = set()
        for names in from_imports.values():
            imported_names.update(names)

        try:
            source = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
        except (SyntaxError, Exception):
            return []

        results = []
        coupling_to: Dict[str, Set[str]] = {}

        for cls in classes:
            visitor = CouplingVisitor(cls.name, all_class_names, imported_names)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == cls.name:
                    visitor.visit(node)
                    break

            coupling_to[cls.name] = visitor.coupled_classes

        # Calculate afferent coupling within this file
        coupling_from: Dict[str, Set[str]] = {cls.name: set() for cls in classes}
        for class_name, coupled in coupling_to.items():
            for c in coupled:
                if c in coupling_from:
                    coupling_from[c].add(class_name)

        for cls in classes:
            ce = len(coupling_to.get(cls.name, set()))
            ca = len(coupling_from.get(cls.name, set()))
            cbo = ce

            instability = ce / (ca + ce) if (ca + ce) > 0 else 0.0
            coupling_level = ClassCouplingMetrics.calculate_coupling_level(cbo)
            severity = ClassCouplingMetrics.calculate_severity(cbo, self.config.cbo_threshold)

            metrics = ClassCouplingMetrics(
                class_name=cls.name,
                file_path=str(path),
                relative_path=path.name,
                line_number=cls.line_number,
                cbo=cbo,
                afferent_coupling=ca,
                efferent_coupling=ce,
                instability=instability,
                coupled_to=coupling_to.get(cls.name, set()),
                coupled_from=coupling_from.get(cls.name, set()),
                coupling_level=coupling_level,
                severity=severity,
            )
            results.append(metrics)

        return results
