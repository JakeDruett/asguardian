"""Fixtures for budgeted L8 performance tests."""

import pytest

from Asgard_Test.L8_PerfBudgets.enforcement import load_budgets, lookup_budget


@pytest.fixture(scope="session")
def l8_budgets() -> dict:
    """Parsed contents of Asgard_Test/L8_budgets.yaml."""
    return load_budgets()


@pytest.fixture(scope="session")
def l8_budget():
    """Look up a budget in ms by dotted key, e.g. 'heimdall.taint_analyzer.single_file_ms'."""
    return lookup_budget
