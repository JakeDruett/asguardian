"""
Asgard Reporting Module

Provides various output formatters and report generators for analysis results,
as well as metrics history tracking and PR decoration services.

Subpackages:
- History: SQLite-backed metrics snapshot store with trend computation.
- PRDecoration: Post analysis results to GitHub PRs and GitLab MRs.
"""

from Asgard.Reporting.html_generator import HTMLReportGenerator
from Asgard.Reporting.github_formatter import GitHubActionsFormatter
from Asgard.Reporting import History
from Asgard.Reporting import PRDecoration
from Asgard.Reporting.History import (
    AnalysisSnapshot,
    HistoryStore,
    MetricSnapshot,
    MetricTrend,
    TrendDirection,
    TrendReport,
)
from Asgard.Reporting.PRDecoration import (
    GitHubDecorator,
    GitLabDecorator,
    IssueComment,
    PRDecorationConfig,
    PRDecorationResult,
    PRPlatform,
)

__all__ = [
    "HTMLReportGenerator",
    "GitHubActionsFormatter",
    # History subpackage
    "History",
    "AnalysisSnapshot",
    "HistoryStore",
    "MetricSnapshot",
    "MetricTrend",
    "TrendDirection",
    "TrendReport",
    # PRDecoration subpackage
    "PRDecoration",
    "GitHubDecorator",
    "GitLabDecorator",
    "IssueComment",
    "PRDecorationConfig",
    "PRDecorationResult",
    "PRPlatform",
]
