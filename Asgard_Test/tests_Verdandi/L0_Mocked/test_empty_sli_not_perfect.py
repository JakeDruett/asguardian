"""CH-0098 leftover: empty SLI / error-budget / vitals / APM is not 100%."""

from datetime import datetime

from Asgard.Verdandi.APM.services.trace_aggregator import TraceAggregator
from Asgard.Verdandi.SLO.models.slo_models import SLIMetric, SLOType
from Asgard.Verdandi.SLO.services._sli_aggregation import aggregate_by_period
from Asgard.Verdandi.SLO.services.sli_tracker import SLITracker
from Asgard.Verdandi.Web import CoreWebVitalsCalculator, VitalsRating


def test_empty_sli_history_is_zero_not_perfect():
    stats = SLITracker().calculate_sli()
    assert stats["success_rate"] == 0.0
    assert stats["total_events"] == 0


def test_zero_event_sli_window_is_zero_not_perfect():
    tracker = SLITracker()
    tracker.record(
        SLIMetric(
            timestamp=datetime.now(),
            service_name="api",
            slo_type=SLOType.AVAILABILITY,
            good_events=0,
            total_events=0,
        )
    )
    stats = tracker.calculate_sli()
    assert stats["success_rate"] == 0.0
    assert stats["total_events"] == 0


def test_zero_event_period_aggregation_is_zero_not_perfect():
    metric = SLIMetric(
        timestamp=datetime.now(),
        service_name="api",
        slo_type=SLOType.AVAILABILITY,
        good_events=0,
        total_events=0,
    )
    periods = aggregate_by_period([metric], hours=1)
    assert periods
    for period in periods.values():
        assert period["success_rate"] == 0.0


def test_empty_vitals_are_insufficient_not_perfect():
    result = CoreWebVitalsCalculator().calculate()
    assert result.overall_rating == VitalsRating.INSUFFICIENT_DATA
    assert result.score == 0.0


def test_empty_apm_traces_are_not_perfect():
    report = TraceAggregator().aggregate([])
    assert report.health_score == 0.0
    assert report.trace_count == 0
