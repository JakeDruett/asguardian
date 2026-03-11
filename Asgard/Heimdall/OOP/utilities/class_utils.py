"""
Heimdall OOP Class Utilities

Utility functions for extracting class information from Python source code.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class ClassInfo:
    """Information about a Python class."""
    name: str
    line_number: int
    end_line: int
    base_classes: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    attributes: Set[str] = field(default_factory=set)
    method_nodes: Dict[str, ast.FunctionDef] = field(default_factory=dict)
    class_node: Optional[ast.ClassDef] = None


@dataclass
class MethodInfo:
    """Information about a method."""
    name: str
    line_number: int
    end_line: int
    parameters: List[str] = field(default_factory=list)
    called_methods: Set[str] = field(default_factory=set)
    accessed_attributes: Set[str] = field(default_factory=set)
    complexity: int = 1


class ClassExtractor(ast.NodeVisitor):
    """AST visitor that extracts class information."""

    def __init__(self):
        self.classes: List[ClassInfo] = []
        self._current_class: Optional[ClassInfo] = None

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Extract class definition."""
        # Get base classes
        base_classes = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_classes.append(base.id)
            elif isinstance(base, ast.Attribute):
                # Handle module.Class style bases
                parts = []
                current = base
                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value
                if isinstance(current, ast.Name):
                    parts.append(current.id)
                base_classes.append(".".join(reversed(parts)))

        class_info = ClassInfo(
            name=node.name,
            line_number=node.lineno,
            end_line=node.end_lineno or node.lineno,
            base_classes=base_classes,
            class_node=node,
        )

        # Save current class context
        old_class = self._current_class
        self._current_class = class_info

        # Extract methods and attributes
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                class_info.methods.append(item.name)
                class_info.method_nodes[item.name] = item
            elif isinstance(item, ast.Assign):
                # Class-level attribute assignments
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        class_info.attributes.add(target.id)
            elif isinstance(item, ast.AnnAssign):
                # Annotated assignments
                if isinstance(item.target, ast.Name):
                    class_info.attributes.add(item.target.id)

        # Extract instance attributes from __init__
        if "__init__" in class_info.method_nodes:
            init_node = class_info.method_nodes["__init__"]
            class_info.attributes.update(
                self._extract_instance_attributes(init_node)
            )

        self.classes.append(class_info)

        # Visit nested classes
        self.generic_visit(node)

        # Restore context
        self._current_class = old_class

    def _extract_instance_attributes(self, node: ast.FunctionDef) -> Set[str]:
        """Extract instance attributes from a method (self.attr assignments)."""
        attributes = set()

        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if (isinstance(target, ast.Attribute) and
                        isinstance(target.value, ast.Name) and
                        target.value.id == "self"):
                        attributes.add(target.attr)
            elif isinstance(child, ast.AnnAssign):
                if (isinstance(child.target, ast.Attribute) and
                    isinstance(child.target.value, ast.Name) and
                    child.target.value.id == "self"):
                    attributes.add(child.target.attr)

        return attributes


class MethodAnalyzer(ast.NodeVisitor):
    """AST visitor that analyzes method calls and attribute accesses."""

    def __init__(self):
        self.called_methods: Set[str] = set()
        self.accessed_attributes: Set[str] = set()
        self.external_calls: Set[str] = set()
        self.complexity = 1

    def visit_Call(self, node: ast.Call) -> None:
        """Track method calls."""
        if isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                if node.func.value.id == "self":
                    # self.method() call
                    self.called_methods.add(node.func.attr)
                else:
                    # other.method() call
                    self.external_calls.add(f"{node.func.value.id}.{node.func.attr}")
            elif isinstance(node.func.value, ast.Attribute):
                # self.attr.method() or obj.attr.method()
                self.external_calls.add(node.func.attr)
        elif isinstance(node.func, ast.Name):
            # function() call (not a method)
            self.external_calls.add(node.func.id)

        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Track attribute accesses."""
        if isinstance(node.value, ast.Name) and node.value.id == "self":
            self.accessed_attributes.add(node.attr)
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        """Count decision points for complexity."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        """Count loops for complexity."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        """Count loops for complexity."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        """Count exception handlers for complexity."""
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        """Count boolean operators for complexity."""
        self.complexity += len(node.values) - 1
        self.generic_visit(node)


class ImportExtractor(ast.NodeVisitor):
    """AST visitor that extracts import information."""

    def __init__(self):
        self.imports: Set[str] = set()          # Module names
        self.from_imports: Dict[str, Set[str]] = {}  # module -> {names}
        self.imported_names: Set[str] = set()   # All imported names

    def visit_Import(self, node: ast.Import) -> None:
        """Handle 'import X' statements."""
        for alias in node.names:
            module = alias.name
            self.imports.add(module)
            # Add the name used in code (alias or module name)
            name = alias.asname if alias.asname else module.split(".")[0]
            self.imported_names.add(name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle 'from X import Y' statements."""
        module = node.module or ""

        if module not in self.from_imports:
            self.from_imports[module] = set()

        for alias in node.names:
            if alias.name == "*":
                self.from_imports[module].add("*")
            else:
                self.from_imports[module].add(alias.name)
                name = alias.asname if alias.asname else alias.name
                self.imported_names.add(name)


def extract_classes_from_source(source: str) -> List[ClassInfo]:
    """
    Extract class information from Python source code.

    Args:
        source: Python source code string

    Returns:
        List of ClassInfo objects
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    extractor = ClassExtractor()
    extractor.visit(tree)
    return extractor.classes


def extract_classes_from_file(file_path: Path) -> List[ClassInfo]:
    """
    Extract class information from a Python file.

    Args:
        file_path: Path to Python file

    Returns:
        List of ClassInfo objects
    """
    try:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        return extract_classes_from_source(source)
    except (IOError, OSError):
        return []


def get_class_methods(class_info: ClassInfo) -> List[MethodInfo]:
    """
    Get detailed method information for a class.

    Args:
        class_info: ClassInfo object

    Returns:
        List of MethodInfo objects
    """
    methods = []

    for name, node in class_info.method_nodes.items():
        analyzer = MethodAnalyzer()
        analyzer.visit(node)

        # Get parameters (excluding self)
        params = []
        for arg in node.args.args:
            if arg.arg != "self":
                params.append(arg.arg)

        method_info = MethodInfo(
            name=name,
            line_number=node.lineno,
            end_line=node.end_lineno or node.lineno,
            parameters=params,
            called_methods=analyzer.called_methods,
            accessed_attributes=analyzer.accessed_attributes,
            complexity=analyzer.complexity,
        )
        methods.append(method_info)

    return methods


def get_class_attributes(class_info: ClassInfo) -> Set[str]:
    """
    Get all attributes (class and instance) for a class.

    Args:
        class_info: ClassInfo object

    Returns:
        Set of attribute names
    """
    return class_info.attributes.copy()


def get_method_calls(method_node: ast.FunctionDef) -> Tuple[Set[str], Set[str]]:
    """
    Get method calls from a method.

    Args:
        method_node: AST node for the method

    Returns:
        Tuple of (self_calls, external_calls)
    """
    analyzer = MethodAnalyzer()
    analyzer.visit(method_node)
    return analyzer.called_methods, analyzer.external_calls


def get_attribute_accesses(method_node: ast.FunctionDef) -> Set[str]:
    """
    Get attribute accesses from a method.

    Args:
        method_node: AST node for the method

    Returns:
        Set of accessed attribute names
    """
    analyzer = MethodAnalyzer()
    analyzer.visit(method_node)
    return analyzer.accessed_attributes


def get_imports_from_source(source: str) -> Tuple[Set[str], Dict[str, Set[str]]]:
    """
    Extract import information from source code.

    Args:
        source: Python source code

    Returns:
        Tuple of (imports, from_imports)
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set(), {}

    extractor = ImportExtractor()
    extractor.visit(tree)
    return extractor.imports, extractor.from_imports


def get_imports_from_file(file_path: Path) -> Tuple[Set[str], Dict[str, Set[str]]]:
    """
    Extract import information from a file.

    Args:
        file_path: Path to Python file

    Returns:
        Tuple of (imports, from_imports)
    """
    try:
        source = file_path.read_text(encoding="utf-8", errors="ignore")
        return get_imports_from_source(source)
    except (IOError, OSError):
        return set(), {}


def find_class_usages(source: str, class_name: str) -> List[int]:
    """
    Find line numbers where a class is used.

    Args:
        source: Python source code
        class_name: Name of the class to find

    Returns:
        List of line numbers where class is referenced
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    usages = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == class_name:
            usages.append(node.lineno)
        elif isinstance(node, ast.Attribute) and node.attr == class_name:
            usages.append(node.lineno)

    return sorted(set(usages))
