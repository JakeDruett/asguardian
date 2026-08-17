"""CH-0098 leftover: empty SLI / error-budget is not 100%."""

from Asgard.Verdandi.SLO.services.sli_tracker import SLITracker


def test_empty_sli_history_is_zero_not_perfect():
    stats = SLITracker().calculate_sli()
    assert stats["success_rate"] == 0.0
    assert stats["total_events"] == 0
