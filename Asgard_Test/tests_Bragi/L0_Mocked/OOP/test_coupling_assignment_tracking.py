"""Assignment-type-tracking resolver tests for the coupling visitor (Plan 05).

RESEARCH_06 "Assignment Type Tracking": ``ps = PaymentService(); ps.charge()``
binds ``ps`` so the receiver call resolves to a CBO edge; ambiguous receivers
produce no edge (precision over recall).
"""
import ast

from Asgard.Bragi.OOP.services._coupling_visitor import CouplingVisitor


def _couples(source: str, class_name: str, all_classes, imported=frozenset()):
    tree = ast.parse(source)
    visitor = CouplingVisitor(class_name, set(all_classes), set(imported))
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            visitor.visit(node)
            break
    return visitor.coupled_classes


def test_local_binding_resolves_receiver_call():
    src = (
        "class Checkout:\n"
        "    def run(self):\n"
        "        ps = PaymentService()\n"
        "        ps.charge()\n"
    )
    assert "PaymentService" in _couples(src, "Checkout", {"Checkout", "PaymentService"})


def test_module_qualified_instantiation_counts():
    """pkg.PaymentService() was previously invisible to the visitor."""
    src = (
        "class Checkout:\n"
        "    def run(self):\n"
        "        svc = payments.PaymentService()\n"
        "        svc.charge()\n"
    )
    assert "PaymentService" in _couples(
        src, "Checkout", {"Checkout"}, imported={"PaymentService"}
    )


def test_self_attribute_binding_resolves_across_methods():
    src = (
        "class Checkout:\n"
        "    def __init__(self):\n"
        "        self.ps = PaymentService()\n"
        "    def run(self):\n"
        "        self.ps.charge()\n"
    )
    assert "PaymentService" in _couples(src, "Checkout", {"Checkout", "PaymentService"})


def test_annotated_parameter_binds_receiver():
    src = (
        "class Checkout:\n"
        "    def run(self, ps: PaymentService):\n"
        "        ps.charge()\n"
    )
    assert "PaymentService" in _couples(src, "Checkout", {"Checkout", "PaymentService"})


def test_rebinding_to_unknown_clears_binding():
    """Ambiguous receiver -> the stale class must not leak an edge via the
    binding table (the original instantiation edge is still legitimate)."""
    src = (
        "class Checkout:\n"
        "    def run(self):\n"
        "        ps = unknown_factory()\n"
        "        ps.charge()\n"
    )
    couples = _couples(src, "Checkout", {"Checkout", "PaymentService"})
    assert "PaymentService" not in couples


def test_unbound_receiver_produces_no_edge():
    src = (
        "class Checkout:\n"
        "    def run(self, thing):\n"
        "        thing.charge()\n"
    )
    assert _couples(src, "Checkout", {"Checkout", "PaymentService"}) == set()


def test_self_binding_never_couples_own_class():
    src = (
        "class Checkout:\n"
        "    def clone(self):\n"
        "        c = Checkout()\n"
        "        c.run()\n"
        "    def run(self):\n"
        "        pass\n"
    )
    assert _couples(src, "Checkout", {"Checkout"}) == set()


def test_existing_behaviour_preserved_inheritance_and_annotations():
    src = (
        "class Checkout(BaseHandler):\n"
        "    def total(self) -> Money:\n"
        "        return Money()\n"
    )
    couples = _couples(src, "Checkout", {"Checkout", "BaseHandler", "Money"})
    assert couples == {"BaseHandler", "Money"}
