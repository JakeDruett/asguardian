"""Unit tests for the shared L8 budget loading/lookup helpers."""

import pytest

from Asgard_Test.L8_PerfBudgets.enforcement import (
    load_budgets,
    lookup_budget,
    suite_budget_ms,
)


class TestLookupBudget:
    def test_known_key_resolves(self):
        assert lookup_budget("heimdall.secrets_detection.single_file_ms") > 0

    def test_missing_key_raises(self):
        with pytest.raises(AssertionError, match="no.such.key"):
            lookup_budget("no.such.key")

    def test_non_numeric_leaf_raises(self):
        with pytest.raises(AssertionError, match="must resolve to a number"):
            lookup_budget("heimdall.secrets_detection")


class TestSuiteBudgets:
    def test_known_suite_uses_its_budget(self):
        suites = load_budgets()["suites"]
        assert suite_budget_ms("test_scanner_performance") == float(
            suites["test_scanner_performance"]["per_test_ms"]
        )

    def test_unknown_suite_falls_back_to_default(self):
        suites = load_budgets()["suites"]
        assert suite_budget_ms("test_not_a_real_suite") == float(
            suites["default_per_test_ms"]
        )

    def test_every_declared_suite_entry_is_well_formed(self):
        suites = load_budgets()["suites"]
        for key, entry in suites.items():
            if key == "default_per_test_ms":
                assert isinstance(entry, (int, float))
                continue
            assert isinstance(entry, dict), key
            assert isinstance(entry.get("per_test_ms"), (int, float)), key
            assert entry["per_test_ms"] > 0, key
