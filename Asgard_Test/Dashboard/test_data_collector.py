"""
Tests for Asgard Dashboard Data Collector

Unit tests for DataCollector.collect(), using unittest.mock.patch to avoid
real SQLite database access. Tests verify DashboardState construction,
correct propagation of issue counts, snapshot data, and ratings extraction.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from Asgard.Dashboard.models.dashboard_models import (
    DashboardConfig,
    DashboardState,
    IssueSummaryData,
    RatingData,
)
from Asgard.Dashboard.services.data_collector import DataCollector
from Asgard.Heimdall.Issues.models.issue_models import (
    IssueSeverity,
    IssuesSummary,
    IssueStatus,
    IssueType,
    TrackedIssue,
)
from Asgard.Reporting.History.models.history_models import AnalysisSnapshot


def _make_issues_summary(
    total_open: int = 0,
    total_confirmed: int = 0,
    total_false_positives: int = 0,
    total_wont_fix: int = 0,
    total_resolved: int = 0,
    open_by_severity: dict = None,
    project_path: str = "/project",
) -> IssuesSummary:
    """Return an IssuesSummary with controllable counts."""
    return IssuesSummary(
        total_open=total_open,
        total_confirmed=total_confirmed,
        total_false_positives=total_false_positives,
        total_wont_fix=total_wont_fix,
        total_resolved=total_resolved,
        open_by_severity=open_by_severity or {},
        project_path=project_path,
    )


def _make_tracked_issue(
    project_path: str = "/project",
    rule_id: str = "quality.lazy_imports",
    file_path: str = "/project/main.py",
    line_number: int = 10,
    severity: IssueSeverity = IssueSeverity.HIGH,
    status: IssueStatus = IssueStatus.OPEN,
) -> TrackedIssue:
    """Return a minimal TrackedIssue for mocking."""
    now = datetime.now()
    return TrackedIssue(
        issue_id="test-uuid-1234",
        rule_id=rule_id,
        issue_type=IssueType.CODE_SMELL,
        file_path=file_path,
        line_number=line_number,
        severity=severity,
        title="Test issue",
        description="A test issue",
        status=status,
        first_detected=now,
        last_seen=now,
    )


def _make_snapshot(
    project_path: str = "/project",
    quality_gate_status: str = "passed",
    ratings: dict = None,
) -> AnalysisSnapshot:
    """Return a minimal AnalysisSnapshot for mocking."""
    return AnalysisSnapshot(
        snapshot_id="snap-uuid-1234",
        project_path=project_path,
        scan_timestamp=datetime(2025, 3, 10, 12, 0, 0),
        git_commit="abc1234",
        git_branch="main",
        quality_gate_status=quality_gate_status,
        ratings=ratings if ratings is not None else {"maintainability": "A", "reliability": "B", "security": "A", "overall": "A"},
        metrics=[],
    )


def _make_config(project_path: str = "/project") -> DashboardConfig:
    """Return a DashboardConfig for the given project path."""
    return DashboardConfig(
        project_path=project_path,
        open_browser=False,
    )


class TestDataCollectorCollect:
    """Tests for DataCollector.collect()."""

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_returns_dashboard_state(self, mock_tracker_cls, mock_store_cls):
        """Test that collect() returns a DashboardState instance."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary()
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = []
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert isinstance(state, DashboardState)

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_empty_stores_zero_counts(self, mock_tracker_cls, mock_store_cls):
        """Test that empty stores produce a DashboardState with zero counts."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary()
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = []
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert state.issue_summary.total == 0
        assert state.issue_summary.open == 0
        assert state.issue_summary.confirmed == 0
        assert state.issue_summary.critical == 0

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_returns_correct_project_path(self, mock_tracker_cls, mock_store_cls):
        """Test that the returned DashboardState has the correct project_path."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary(project_path="/my/project")
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = []
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config(project_path="/my/project"))
        state = collector.collect()

        assert state.project_path == "/my/project"

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_no_history_returns_none_ratings(self, mock_tracker_cls, mock_store_cls):
        """Test that when no snapshots exist, ratings is None."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary()
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = []
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert state.ratings is None

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_no_history_returns_none_last_analyzed(self, mock_tracker_cls, mock_store_cls):
        """Test that when no snapshots exist, last_analyzed is None."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary()
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = []
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert state.last_analyzed is None

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_extracts_ratings_from_most_recent_snapshot(
        self, mock_tracker_cls, mock_store_cls
    ):
        """Test that ratings are populated from the most recent snapshot."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary()
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        snapshot = _make_snapshot(
            ratings={
                "maintainability": "A",
                "reliability": "B",
                "security": "C",
                "overall": "B",
            }
        )
        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = [snapshot]
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert state.ratings is not None
        assert state.ratings.maintainability == "A"
        assert state.ratings.reliability == "B"
        assert state.ratings.security == "C"
        assert state.ratings.overall == "B"

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_uses_first_snapshot_as_latest(self, mock_tracker_cls, mock_store_cls):
        """Test that the first element of snapshots_raw is treated as the most recent."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary()
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        newest = _make_snapshot(quality_gate_status="passed", ratings={"maintainability": "A", "reliability": "A", "security": "A", "overall": "A"})
        older = _make_snapshot(quality_gate_status="failed", ratings={"maintainability": "E", "reliability": "E", "security": "E", "overall": "E"})
        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = [newest, older]
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert state.quality_gate_status == "passed"
        assert state.ratings.overall == "A"

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_issue_summary_open_count(self, mock_tracker_cls, mock_store_cls):
        """Test that open issue count is correctly transferred to DashboardState."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary(total_open=5)
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = []
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert state.issue_summary.open == 5

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_issue_summary_total_counts_all_statuses(
        self, mock_tracker_cls, mock_store_cls
    ):
        """Test that the total count is the sum of all status counts."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary(
            total_open=2,
            total_confirmed=1,
            total_false_positives=1,
            total_wont_fix=1,
            total_resolved=3,
        )
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = []
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert state.issue_summary.total == 8

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_critical_count_from_open_by_severity(
        self, mock_tracker_cls, mock_store_cls
    ):
        """Test that critical count comes from open_by_severity dict."""
        summary = _make_issues_summary(
            total_open=3,
            open_by_severity={IssueSeverity.CRITICAL.value: 2, IssueSeverity.HIGH.value: 1},
        )
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = summary
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = []
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert state.issue_summary.critical == 2
        assert state.issue_summary.high == 1

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_recent_issues_populated_from_get_issues(
        self, mock_tracker_cls, mock_store_cls
    ):
        """Test that recent_issues is populated from get_issues() results."""
        tracked_issue = _make_tracked_issue()
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary()
        mock_tracker.get_issues.return_value = [tracked_issue]
        mock_tracker_cls.return_value = mock_tracker

        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = []
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert len(state.recent_issues) == 1
        assert state.recent_issues[0]["rule_id"] == "quality.lazy_imports"

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_snapshots_populated(self, mock_tracker_cls, mock_store_cls):
        """Test that snapshots are populated from history store."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary()
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        snapshot = _make_snapshot()
        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = [snapshot]
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert len(state.snapshots) == 1
        assert state.snapshots[0]["snapshot_id"] == "snap-uuid-1234"

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_snapshot_with_no_ratings_uses_unknown(
        self, mock_tracker_cls, mock_store_cls
    ):
        """Test that a snapshot with empty ratings dict leaves state.ratings as None."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary()
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        snapshot = _make_snapshot(ratings={})
        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = [snapshot]
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert state.ratings is None

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_last_analyzed_from_most_recent_snapshot(
        self, mock_tracker_cls, mock_store_cls
    ):
        """Test that last_analyzed is set from the first snapshot's scan_timestamp."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary()
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        ts = datetime(2025, 6, 1, 9, 0, 0)
        snapshot = _make_snapshot()
        snapshot.scan_timestamp = ts

        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = [snapshot]
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert state.last_analyzed == ts

    @patch("Asgard.Dashboard.services.data_collector.HistoryStore")
    @patch("Asgard.Dashboard.services.data_collector.IssueTracker")
    def test_collect_quality_gate_status_from_snapshot(
        self, mock_tracker_cls, mock_store_cls
    ):
        """Test that quality_gate_status is taken from the most recent snapshot."""
        mock_tracker = MagicMock()
        mock_tracker.get_summary.return_value = _make_issues_summary()
        mock_tracker.get_issues.return_value = []
        mock_tracker_cls.return_value = mock_tracker

        snapshot = _make_snapshot(quality_gate_status="failed")
        mock_store = MagicMock()
        mock_store.get_snapshots.return_value = [snapshot]
        mock_store_cls.return_value = mock_store

        collector = DataCollector(_make_config())
        state = collector.collect()

        assert state.quality_gate_status == "failed"
