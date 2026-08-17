"""CHC-0011: CST taint walks are depth-capped."""

from Asgard.Heimdall.Security.TaintAnalysis.engine.cst_taint_visitor import (
    _MAX_CST_WALK_DEPTH,
    _find_functions,
    _node_chain,
)


class _Node:
    def __init__(self, child=None, node_type="expression_statement"):
        self.type = node_type
        self.children = [child] if child is not None else []

    def child_by_field_name(self, name):
        if name == "object":
            return self.children[0] if self.children else None
        return None


def test_find_functions_is_iterative_on_deep_tree():
    node = _Node()
    for _ in range(400):
        node = _Node(node)
    out = []
    _find_functions(node, out)
    assert out == []


def test_node_chain_caps_depth():
    node = _Node(node_type="identifier")
    for _ in range(_MAX_CST_WALK_DEPTH + 20):
        node = _Node(node, node_type="member_expression")
    assert _node_chain(node, ctx=None) == ""
