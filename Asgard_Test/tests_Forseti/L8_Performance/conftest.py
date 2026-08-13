"""Budget gating for this directory's pytest-benchmark suites.

Re-exports the autouse `l8_suite_budget_gate` fixture, which fails any
benchmark test whose fastest round exceeds its per-suite budget in
Asgard_Test/L8_budgets.yaml (see the `suites:` section).
"""

from Asgard_Test.L8_PerfBudgets.enforcement import l8_suite_budget_gate  # noqa: F401
