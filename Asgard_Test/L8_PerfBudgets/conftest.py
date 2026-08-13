"""Fixtures for budgeted L8 performance tests."""

from pathlib import Path

import pytest
import yaml

_BUDGETS_FILE = Path(__file__).parent.parent / "L8_budgets.yaml"


@pytest.fixture(scope="session")
def l8_budgets() -> dict:
    """Parsed contents of Asgard_Test/L8_budgets.yaml."""
    with _BUDGETS_FILE.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@pytest.fixture(scope="session")
def l8_budget(l8_budgets):
    """Look up a budget in ms by dotted key, e.g. 'heimdall.taint_analyzer.single_file_ms'."""

    def _lookup(dotted_key: str) -> float:
        node = l8_budgets
        for part in dotted_key.split("."):
            assert part in node, (
                f"Budget key '{dotted_key}' not found in {_BUDGETS_FILE} "
                f"(missing segment '{part}')"
            )
            node = node[part]
        assert isinstance(node, (int, float)), (
            f"Budget '{dotted_key}' must resolve to a number, got {node!r}"
        )
        return float(node)

    return _lookup
