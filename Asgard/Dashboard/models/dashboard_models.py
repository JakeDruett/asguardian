"""
Asgard Dashboard Models

Pydantic v2 models for the web dashboard configuration and state.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DashboardConfig(BaseModel):
    """Configuration for the Asgard web dashboard server."""

    host: str = Field("localhost", description="Host address to bind the server to")
    port: int = Field(8080, description="Port to serve the dashboard on")
    project_path: str = Field(..., description="Absolute path to the project being visualised")
    open_browser: bool = Field(True, description="Whether to automatically open a browser tab on launch")
    db_path: Optional[str] = Field(
        None,
        description="Path to the directory containing Asgard SQLite databases. None uses ~/.asgard/",
    )


class IssueSummaryData(BaseModel):
    """Aggregated counts of tracked issues for display on the dashboard."""

    total: int = Field(..., description="Total number of issues across all statuses")
    open: int = Field(..., description="Number of issues with status 'open'")
    confirmed: int = Field(..., description="Number of issues with status 'confirmed'")
    critical: int = Field(..., description="Number of open/confirmed issues with critical severity")
    high: int = Field(..., description="Number of open/confirmed issues with high severity")
    medium: int = Field(..., description="Number of open/confirmed issues with medium severity")
    low: int = Field(..., description="Number of open/confirmed issues with low severity")


class RatingData(BaseModel):
    """Letter ratings across quality dimensions."""

    maintainability: str = Field(..., description="Maintainability rating (A-E)")
    reliability: str = Field(..., description="Reliability rating (A-E)")
    security: str = Field(..., description="Security rating (A-E)")
    overall: str = Field(..., description="Overall quality rating (A-E)")


class DashboardState(BaseModel):
    """Aggregated state object populated by DataCollector and consumed by HtmlRenderer."""

    project_path: str = Field(..., description="Absolute path to the project being visualised")
    last_analyzed: Optional[datetime] = Field(None, description="Timestamp of the most recent analysis snapshot")
    quality_gate_status: Optional[str] = Field(
        None,
        description="Quality gate outcome: 'passed', 'failed', or 'unknown'",
    )
    ratings: Optional[RatingData] = Field(None, description="Letter ratings from the most recent snapshot")
    issue_summary: IssueSummaryData = Field(..., description="Aggregated issue counts")
    recent_issues: List[Dict] = Field(
        default_factory=list,
        description="Serialized TrackedIssue dicts for the issues table (up to 100)",
    )
    snapshots: List[Dict] = Field(
        default_factory=list,
        description="Serialized AnalysisSnapshot dicts for the history table (up to 20)",
    )
