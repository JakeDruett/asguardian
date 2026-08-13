"""
Shared L8 budget loading and per-suite enforcement.

Two consumers:

1. ``Asgard_Test/L8_PerfBudgets/conftest.py`` re-uses :func:`lookup_budget`
   for the explicit ``l8_budget`` fixture used by the budgeted smoke tests.
2. Each ``L8_Performance`` directory's ``conftest.py`` imports
   :func:`l8_suite_budget_gate`, an autouse fixture that gates every
   pytest-benchmark test in that directory against the per-suite budgets in
   the ``suites:`` section of ``Asgard_Test/L8_budgets.yaml``.

Budget policy (documented in _Docs/Testing/L8_Perf_Budget_Policy.md):

* Budgets gate the *fastest* observed benchmark round (``stats.min``) —
  the most noise-resistant statistic on shared/varied hardware.
* Every budget carries at least 5x headroom over the maximum per-test
  timing observed on the reference run, then rounds up further. Budgets
  exist to catch order-of-magnitude regressions (accidental O(n^2),
  pathological regex, unbounded rescans), not micro-variance.
"""

from pathlib import Path

import pytest
import yaml

_BUDGETS_FILE = Path(__file__).parent.parent / "L8_budgets.yaml"
_budgets_cache = None


def load_budgets() -> dict:
    """Parsed (and cached) contents of Asgard_Test/L8_budgets.yaml."""
    global _budgets_cache
    if _budgets_cache is None:
        with _BUDGETS_FILE.open(encoding="utf-8") as fh:
            _budgets_cache = yaml.safe_load(fh)
    return _budgets_cache


def lookup_budget(dotted_key: str) -> float:
    """Look up a budget in ms by dotted key, e.g. 'heimdall.taint_analyzer.single_file_ms'."""
    node = load_budgets()
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


def suite_budget_ms(module_stem: str) -> float:
    """Per-test budget for a benchmark module, falling back to the suites default."""
    suites = load_budgets().get("suites", {})
    entry = suites.get(module_stem)
    if isinstance(entry, dict) and isinstance(entry.get("per_test_ms"), (int, float)):
        return float(entry["per_test_ms"])
    default = suites.get("default_per_test_ms")
    assert isinstance(default, (int, float)), (
        f"suites.default_per_test_ms missing/non-numeric in {_BUDGETS_FILE}"
    )
    return float(default)


@pytest.fixture(autouse=True)
def l8_suite_budget_gate(request):
    """Gate any pytest-benchmark test against its suite budget after it runs.

    Import this into an L8_Performance directory conftest to enforce the
    ``suites:`` budgets from L8_budgets.yaml on every benchmark test there.
    Non-benchmark tests are unaffected.
    """
    # Resolve the benchmark fixture during setup (not teardown): this makes
    # it a dependency of the gate, so it is still alive when the gate's
    # post-yield check runs.
    bench = (
        request.getfixturevalue("benchmark")
        if "benchmark" in request.fixturenames
        else None
    )
    yield
    if bench is None:
        return
    if getattr(bench, "disabled", False):
        return
    stats = getattr(bench, "stats", None)
    if stats is None:  # benchmark fixture requested but never invoked
        return
    observed_ms = stats.stats.min * 1000.0
    module_stem = Path(str(request.node.fspath)).stem
    budget_ms = suite_budget_ms(module_stem)
    if observed_ms > budget_ms:
        pytest.fail(
            f"L8 budget exceeded: {request.node.nodeid} fastest round took "
            f"{observed_ms:.1f} ms, budget is {budget_ms:.1f} ms "
            f"(suites.{module_stem} in {_BUDGETS_FILE})"
        )
