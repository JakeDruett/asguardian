"""
Freya-Verdandi Integration Tests

Tests for cross-package integration between Freya (frontend performance /
accessibility auditing) and Verdandi (SLA / SLO accounting). Scenarios:

1. Freya's page-load timings feed Verdandi's SLA checker: fast pages are
   compliant, regressed pages breach.
2. Freya's accessibility pass/fail counts feed Verdandi's error-budget
   calculator as good/bad events against a quality SLO.

Freya data comes from the deterministic fake-page harness
(Asgard_Test/_fixtures/freya_harness.py) — no live browser, no network.
"""

from datetime import datetime, timedelta

import pytest

from Asgard.Verdandi.Analysis import SLAChecker, SLAConfig
from Asgard.Verdandi.SLO import (
    ErrorBudgetCalculator,
    SLIMetric,
    SLOComplianceStatus,
    SLODefinition,
)
from Asgard_Test._fixtures.freya_harness import (
    accessible_page_spec,
    canned_page_load_timings,
    canned_slow_page_load_timings,
    inaccessible_page_spec,
    run_accessibility_scan,
)


def _timings_as_samples(timings: dict) -> list:
    """Treat each page-load milestone as a latency sample for SLA checking."""
    return [
        timings["ttfb_ms"],
        timings["first_contentful_paint_ms"],
        timings["dom_content_loaded_ms"],
        timings["load_event_ms"],
        timings["largest_contentful_paint_ms"],
    ]


def _a11y_slo() -> SLODefinition:
    return SLODefinition(
        name="pages-pass-a11y-checks",
        slo_type="quality",
        target=99.0,
        window_days=30,
        service_name="storefront-web",
    )


def _metrics_from_a11y_report(report) -> list:
    """Each executed check is an event; a violation is a bad event."""
    total = max(report.total_checks, 1)
    good = min(report.passed_checks, total)
    return [
        SLIMetric(
            timestamp=datetime.now() - timedelta(hours=1),
            service_name="storefront-web",
            slo_type="quality",
            good_events=good,
            total_events=total,
        )
    ]


@pytest.mark.cross_package
@pytest.mark.freya_verdandi
class TestPageLoadTimingsFeedSLA:
    def test_fast_page_meets_load_time_sla(self):
        checker = SLAChecker(SLAConfig(target_percentile=95.0, threshold_ms=3000.0))
        result = checker.check(_timings_as_samples(canned_page_load_timings()))

        assert result.margin_percent > 0
        status = getattr(result.status, "value", result.status)
        assert status == "compliant", (
            f"fast canned timings must meet a 3s SLA, got {status}"
        )

    def test_regressed_page_breaches_load_time_sla(self):
        checker = SLAChecker(SLAConfig(target_percentile=95.0, threshold_ms=3000.0))
        result = checker.check(_timings_as_samples(canned_slow_page_load_timings()))

        assert result.margin_percent < 0
        status = getattr(result.status, "value", result.status)
        assert status == "breached", (
            f"regressed canned timings must breach a 3s SLA, got {status}"
        )

    def test_sla_margin_orders_fast_before_slow(self):
        """Worse frontend timings must never report a better SLA margin."""
        checker = SLAChecker(SLAConfig(target_percentile=95.0, threshold_ms=3000.0))
        fast = checker.check(_timings_as_samples(canned_page_load_timings()))
        slow = checker.check(_timings_as_samples(canned_slow_page_load_timings()))

        assert fast.percentile_value < slow.percentile_value
        assert fast.margin_percent > slow.margin_percent


@pytest.mark.cross_package
@pytest.mark.freya_verdandi
class TestAccessibilityResultsFeedErrorBudget:
    def test_clean_page_keeps_quality_budget_compliant(self):
        report = run_accessibility_scan(accessible_page_spec())
        assert report.total_violations == 0

        budget = ErrorBudgetCalculator().calculate(
            _a11y_slo(), _metrics_from_a11y_report(report)
        )

        assert budget.bad_events == 0
        assert budget.status in (SLOComplianceStatus.COMPLIANT, "compliant"), (
            f"clean audit must not consume error budget, got {budget.status}"
        )

    def test_violating_page_consumes_quality_budget(self):
        report = run_accessibility_scan(inaccessible_page_spec())
        assert report.total_violations > 0, (
            "inaccessible fixture page must produce violations"
        )

        budget = ErrorBudgetCalculator().calculate(
            _a11y_slo(), _metrics_from_a11y_report(report)
        )

        assert budget.bad_events > 0
        assert budget.status in (
            SLOComplianceStatus.BREACHED,
            SLOComplianceStatus.AT_RISK,
            "breached",
            "at_risk",
        ), f"failing audit must consume error budget, got {budget.status}"

    def test_bad_events_match_violation_count_exactly(self):
        """The SLI must reflect Freya's findings 1:1 — nothing muted."""
        report = run_accessibility_scan(inaccessible_page_spec())
        budget = ErrorBudgetCalculator().calculate(
            _a11y_slo(), _metrics_from_a11y_report(report)
        )
        assert budget.bad_events == report.total_violations
