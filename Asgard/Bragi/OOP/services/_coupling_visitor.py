"""
Heimdall Coupling Analyzer - AST Visitor

CouplingVisitor: detects coupling between classes.

Includes the RESEARCH_06 "Assignment Type Tracking" resolver (Plan 05):
``ps = PaymentService(); ps.charge()`` binds ``ps`` -> ``PaymentService`` so
receiver method calls resolve to a CBO edge.  Bindings are tracked for local
variables (``var = ClassName(...)``, ``var: ClassName``) and instance
attributes (``self.x = ClassName(...)``).  Rebinding a name to anything
unresolvable clears the binding — ambiguous receivers produce **no** edge
(precision over recall for coupling).
"""

import ast
from typing import Dict, Optional, Set


class CouplingVisitor(ast.NodeVisitor):
    """AST visitor that detects coupling between classes."""

    def __init__(self, class_name: str, all_class_names: Set[str], imported_names: Set[str]):
        self.class_name = class_name
        self.all_class_names = all_class_names
        self.imported_names = imported_names
        self.coupled_classes: Set[str] = set()
        #: Assignment-type-tracking tables (name -> bound class name).
        self._local_bindings: Dict[str, str] = {}
        self._attr_bindings: Dict[str, str] = {}

    def _is_relevant_class(self, name: str) -> bool:
        """Check if a name refers to a relevant class."""
        return name in self.all_class_names or name in self.imported_names

    def _add(self, name: str) -> None:
        if self._is_relevant_class(name) and name != self.class_name:
            self.coupled_classes.add(name)

    # ------------------------------------------------------------------
    # Assignment type tracking (Plan 05 / RESEARCH_06)
    # ------------------------------------------------------------------
    def _class_from_expr(self, node: ast.expr) -> Optional[str]:
        """Resolve an expression to a relevant class name, else None.

        Handles ``ClassName(...)``, bare ``ClassName``, and module-qualified
        ``pkg.ClassName(...)`` forms.
        """
        if isinstance(node, ast.Call):
            return self._class_from_expr(node.func)
        if isinstance(node, ast.Name):
            if self._is_relevant_class(node.id) and node.id != self.class_name:
                return node.id
            return None
        if isinstance(node, ast.Attribute):
            if self._is_relevant_class(node.attr) and node.attr != self.class_name:
                return node.attr
            return None
        return None

    def _resolve_receiver(self, node: ast.expr) -> Optional[str]:
        """Resolve a call/attribute receiver via the binding tables."""
        if isinstance(node, ast.Name):
            return self._local_bindings.get(node.id)
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id == "self":
                return self._attr_bindings.get(node.attr)
        return None

    def _record_binding(self, target: ast.expr, value: ast.expr) -> None:
        bound = self._class_from_expr(value)
        if isinstance(target, ast.Name):
            if bound is not None:
                self._local_bindings[target.id] = bound
            else:
                self._local_bindings.pop(target.id, None)
        elif isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
            if target.value.id == "self":
                if bound is not None:
                    self._attr_bindings[target.attr] = bound
                else:
                    self._attr_bindings.pop(target.attr, None)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Track ``var = ClassName(...)`` / ``self.x = ClassName(...)`` bindings."""
        for target in node.targets:
            self._record_binding(target, node.value)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check inheritance coupling."""
        if node.name != self.class_name:
            return

        for base in node.bases:
            if isinstance(base, ast.Name):
                self._add(base.id)
            elif isinstance(base, ast.Attribute):
                self._add(base.attr)

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Check name references that might be class usages."""
        self._add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Check attribute accesses that might indicate coupling."""
        if isinstance(node.value, ast.Name):
            self._add(node.value.id)
        resolved = self._resolve_receiver(node.value)
        if resolved is not None:
            self._add(resolved)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check class instantiation and method calls."""
        if isinstance(node.func, ast.Name):
            self._add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            # Module-qualified instantiation: pkg.ClassName(...)
            self._add(node.func.attr)
            if isinstance(node.func.value, ast.Name):
                self._add(node.func.value.id)
            # Receiver method call resolved via assignment tracking:
            # ps.charge() where ps was bound to PaymentService.
            resolved = self._resolve_receiver(node.func.value)
            if resolved is not None:
                self._add(resolved)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Check type annotations for coupling; annotations also bind."""
        self._check_annotation(node.annotation)
        bound = self._class_from_expr(node.annotation)
        if bound is not None:
            if isinstance(node.target, ast.Name):
                self._local_bindings[node.target.id] = bound
            elif (
                isinstance(node.target, ast.Attribute)
                and isinstance(node.target.value, ast.Name)
                and node.target.value.id == "self"
            ):
                self._attr_bindings[node.target.attr] = bound
        elif node.value is not None:
            self._record_binding(node.target, node.value)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Check function annotations for coupling; annotated params bind."""
        if node.returns:
            self._check_annotation(node.returns)
        for arg in node.args.args:
            if arg.annotation:
                self._check_annotation(arg.annotation)
                bound = self._class_from_expr(arg.annotation)
                if bound is not None:
                    self._local_bindings[arg.arg] = bound
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check async function annotations for coupling."""
        self.visit_FunctionDef(node)

    def _check_annotation(self, annotation: ast.expr) -> None:
        """Check a type annotation for class references."""
        if isinstance(annotation, ast.Name):
            self._add(annotation.id)
        elif isinstance(annotation, ast.Subscript):
            self._check_annotation(annotation.value)
            if isinstance(annotation.slice, ast.Tuple):
                for elt in annotation.slice.elts:
                    self._check_annotation(elt)
            else:
                self._check_annotation(annotation.slice)
        elif isinstance(annotation, ast.Attribute):
            self._add(annotation.attr)
