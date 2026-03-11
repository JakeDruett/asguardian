"""
SLO Models

Pydantic models for Service Level Objectives, including SLO definitions,
SLI metrics, error budgets, and burn rate analysis.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SLOType(str, Enum):
    """Type of SLO measurement."""

    AVAILABILITY = "availability"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    QUALITY = "quality"
    FRESHNESS = "freshness"


class SLOComplianceStatus(str, Enum):
    """Status of SLO compliance."""

    COMPLIANT = "compliant"
    AT_RISK = "at_risk"
    BREACHED = "breached"
    UNKNOWN = "unknown"


class SLODefinition(BaseModel):
    """
    Definition of a Service Level Objective.

    An SLO defines the target level of reliability for a service
    based on one or more SLIs.
    """

    name: str = Field(..., description="Name of the SLO")
    description: Optional[str] = Field(
        default=None, description="Human-readable description"
    )
    slo_type: SLOType = Field(..., description="Type of SLO")
    target: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Target percentage (e.g., 99.9 for 99.9% availability)",
    )
    window_days: int = Field(
        default=30, description="Rolling window in days for SLO calculation"
    )
    service_name: str = Field(..., description="Name of the service")
    labels: Dict[str, str] = Field(
        default_factory=dict, description="Additional labels/tags"
    )
    threshold_ms: Optional[float] = Field(
        default=None, description="Latency threshold for latency SLOs"
    )
    percentile: Optional[float] = Field(
        default=None, description="Target percentile for latency SLOs (e.g., 99)"
    )

    @property
    def error_budget_percent(self) -> float:
        """Calculate error budget as percentage."""
        return 100.0 - self.target


class SLIMetric(BaseModel):
    """
    A single SLI measurement.

    An SLI (Service Level Indicator) is a quantitative measure of
    some aspect of the service level.
    """

    timestamp: datetime = Field(..., description="Timestamp of the measurement")
    service_name: str = Field(..., description="Name of the service")
    slo_type: SLOType = Field(..., description="Type of SLI")
    good_events: int = Field(
        default=0, description="Number of good events (meeting SLO)"
    )
    total_events: int = Field(default=0, description="Total number of events")
    value: float = Field(
        default=0.0, description="Direct value (for non-event-based SLIs)"
    )
    labels: Dict[str, str] = Field(
        default_factory=dict, description="Additional labels/tags"
    )

    @property
    def success_rate(self) -> float:
        """Calculate success rate from good/total events."""
        if self.total_events == 0:
            return 1.0
        return self.good_events / self.total_events

    @property
    def failure_rate(self) -> float:
        """Calculate failure rate."""
        return 1.0 - self.success_rate


class ErrorBudget(BaseModel):
    """
    Error budget calculation result.

    Error budget represents the acceptable amount of downtime or errors
    within the SLO window.
    """

    slo_name: str = Field(..., description="Name of the associated SLO")
    slo_target: float = Field(..., description="SLO target percentage")
    window_days: int = Field(..., description="SLO window in days")
    calculated_at: datetime = Field(
        default_factory=datetime.now, description="Calculation timestamp"
    )
    total_events: int = Field(default=0, description="Total events in window")
    good_events: int = Field(default=0, description="Good events in window")
    bad_events: int = Field(default=0, description="Bad events in window")
    current_sli: float = Field(
        default=0.0, ge=0.0, le=100.0, description="Current SLI percentage"
    )
    allowed_failures: float = Field(
        default=0.0, description="Total allowed failures in window"
    )
    consumed_failures: int = Field(
        default=0, description="Failures consumed so far"
    )
    remaining_budget: float = Field(
        default=0.0, description="Remaining error budget (can be negative)"
    )
    budget_consumed_percent: float = Field(
        default=0.0, description="Percentage of error budget consumed"
    )
    status: SLOComplianceStatus = Field(
        default=SLOComplianceStatus.UNKNOWN, description="Compliance status"
    )
    time_remaining_days: float = Field(
        default=0.0, description="Days remaining in window"
    )
    projected_budget_at_window_end: Optional[float] = Field(
        default=None, description="Projected remaining budget at window end"
    )

    @property
    def is_budget_exhausted(self) -> bool:
        """Check if error budget is exhausted."""
        return self.remaining_budget <= 0

    @property
    def budget_remaining_percent(self) -> float:
        """Get remaining budget as percentage."""
        return max(0.0, 100.0 - self.budget_consumed_percent)


class BurnRate(BaseModel):
    """
    Burn rate analysis for error budget.

    Burn rate measures how fast the error budget is being consumed.
    A burn rate of 1.0 means budget is being consumed at exactly the
    expected rate to hit 0 at the end of the window.
    """

    calculated_at: datetime = Field(
        default_factory=datetime.now, description="Calculation timestamp"
    )
    slo_name: str = Field(..., description="Name of the associated SLO")
    window_hours: float = Field(..., description="Analysis window in hours")
    burn_rate: float = Field(
        ..., description="Current burn rate (1.0 = sustainable rate)"
    )
    burn_rate_short: Optional[float] = Field(
        default=None, description="Short-window burn rate (e.g., 1 hour)"
    )
    burn_rate_long: Optional[float] = Field(
        default=None, description="Long-window burn rate (e.g., 6 hours)"
    )
    budget_consumed_in_window: float = Field(
        default=0.0, description="Budget consumed in the analysis window"
    )
    alert_severity: str = Field(
        default="none", description="Severity of any triggered alerts"
    )
    time_to_exhaustion_hours: Optional[float] = Field(
        default=None, description="Hours until budget exhaustion at current rate"
    )
    is_critical: bool = Field(
        default=False, description="Whether burn rate is critically high"
    )
    is_warning: bool = Field(
        default=False, description="Whether burn rate is warning level"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommended actions"
    )


class SLOReport(BaseModel):
    """Comprehensive SLO compliance report."""

    generated_at: datetime = Field(
        default_factory=datetime.now, description="Report generation timestamp"
    )
    report_period_start: datetime = Field(..., description="Start of report period")
    report_period_end: datetime = Field(..., description="End of report period")
    service_name: str = Field(..., description="Name of the service")
    slo_definitions: List[SLODefinition] = Field(
        default_factory=list, description="SLO definitions evaluated"
    )
    error_budgets: List[ErrorBudget] = Field(
        default_factory=list, description="Error budget calculations"
    )
    burn_rates: List[BurnRate] = Field(
        default_factory=list, description="Burn rate analyses"
    )
    overall_compliance: SLOComplianceStatus = Field(
        default=SLOComplianceStatus.UNKNOWN, description="Overall compliance status"
    )
    slos_compliant: int = Field(default=0, description="Number of compliant SLOs")
    slos_at_risk: int = Field(default=0, description="Number of at-risk SLOs")
    slos_breached: int = Field(default=0, description="Number of breached SLOs")
    total_slos: int = Field(default=0, description="Total number of SLOs")
    critical_alerts: List[str] = Field(
        default_factory=list, description="Critical alert messages"
    )
    warnings: List[str] = Field(default_factory=list, description="Warning messages")
    recommendations: List[str] = Field(
        default_factory=list, description="Improvement recommendations"
    )

    @property
    def compliance_percentage(self) -> float:
        """Calculate percentage of SLOs in compliance."""
        if self.total_slos == 0:
            return 100.0
        return (self.slos_compliant / self.total_slos) * 100.0
