"""
Asgard Reporting History - Metrics History and Trend Tracking

Provides SQLite-backed persistence of analysis snapshots and trend computation
across successive runs. Supports CI/CD integration by recording quality metrics
over time and surfacing whether the codebase is improving, stable, or degrading.

Usage:
    from Asgard.Reporting.History import HistoryStore, AnalysisSnapshot, MetricSnapshot

    store = HistoryStore()

    snapshot = AnalysisSnapshot(
        snapshot_id="<uuid>",
        project_path="./src",
        git_commit="abc1234",
        metrics=[
            MetricSnapshot(metric_name="security_score", value=85.0, unit="score"),
            MetricSnapshot(metric_name="duplication_percentage", value=2.5, unit="%"),
        ],
        quality_gate_status="passed",
        ratings={"security": "A", "reliability": "B"},
    )
    store.save_snapshot(snapshot)

    trends = store.get_trend_report("./src")
    for trend in trends.metric_trends:
        print(f"{trend.metric_name}: {trend.direction} ({trend.change_percentage:+.1f}%)")
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Reporting.History.models.history_models import (
    AnalysisSnapshot,
    MetricSnapshot,
    MetricTrend,
    TrendDirection,
    TrendReport,
)
from Asgard.Reporting.History.services.history_store import HistoryStore

__all__ = [
    "AnalysisSnapshot",
    "HistoryStore",
    "MetricSnapshot",
    "MetricTrend",
    "TrendDirection",
    "TrendReport",
]
