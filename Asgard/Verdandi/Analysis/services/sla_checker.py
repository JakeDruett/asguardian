"""
SLA Checker Service

Checks Service Level Agreement compliance for performance metrics.
"""

from typing import Optional, Sequence, Union

import math

from Asgard.Verdandi.Analysis.models.analysis_models import (
    SLAConfig,
    SLAFractionResult,
    SLAResult,
    SLAStatus,
)
from Asgard.Verdandi.Analysis.services.percentile_calculator import PercentileCalculator


class SLAChecker:
    """
    Checker for Service Level Agreement (SLA) compliance.

    Validates that performance metrics meet defined SLA targets
    including response time percentiles, availability, and error rates.

    Example:
        config = SLAConfig(target_percentile=95, threshold_ms=200)
        checker = SLAChecker(config)
        result = checker.check([100, 150, 200, 250, 180])
        print(f"SLA Status: {result.status}")
    """

    def __init__(self, config: SLAConfig):
        """
        Initialize the SLA checker.

        Args:
            config: SLA configuration with thresholds
        """
        self.config = config
        self._percentile_calc = PercentileCalculator()

    def check(
        self,
        response_times_ms: Sequence[Union[int, float]],
        error_count: int = 0,
        total_requests: Optional[int] = None,
        downtime_seconds: int = 0,
        total_seconds: Optional[int] = None,
    ) -> SLAResult:
        """
        Check SLA compliance.

        Args:
            response_times_ms: Response times in milliseconds
            error_count: Number of errors
            total_requests: Total requests (defaults to len(response_times_ms))
            downtime_seconds: Seconds of downtime
            total_seconds: Total period in seconds

        Returns:
            SLAResult with compliance status and details
        """
        if not response_times_ms:
            raise ValueError("Cannot check SLA for empty dataset")

        total = total_requests or len(response_times_ms)

        percentile_value = self._percentile_calc.calculate_percentile(
            response_times_ms,
            self.config.target_percentile,
        )

        margin = ((self.config.threshold_ms - percentile_value) / self.config.threshold_ms) * 100

        availability = None
        if total_seconds and total_seconds > 0:
            uptime_seconds = total_seconds - downtime_seconds
            availability = (uptime_seconds / total_seconds) * 100

        error_rate = None
        if total > 0:
            error_rate = (error_count / total) * 100

        violations = []
        status = SLAStatus.COMPLIANT

        if not math.isfinite(percentile_value) or not math.isfinite(margin):
            violations.append("Non-finite percentile or margin; treating window as BREACHED")
            status = SLAStatus.BREACHED
        elif percentile_value > self.config.threshold_ms:
            violations.append(
                f"P{self.config.target_percentile} response time {percentile_value:.1f}ms "
                f"exceeds threshold {self.config.threshold_ms}ms"
            )
            status = SLAStatus.BREACHED
        elif margin < (100 - self.config.warning_threshold_percent):
            status = SLAStatus.WARNING

        if availability is not None and self.config.availability_target is not None:
            if availability < self.config.availability_target:
                violations.append(
                    f"Availability {availability:.2f}% below target {self.config.availability_target}%"
                )
                status = SLAStatus.BREACHED

        if error_rate is not None and self.config.error_rate_threshold is not None:
            if error_rate > self.config.error_rate_threshold:
                violations.append(
                    f"Error rate {error_rate:.2f}% exceeds threshold {self.config.error_rate_threshold}%"
                )
                status = SLAStatus.BREACHED

        return SLAResult(
            status=status,
            percentile_value=round(percentile_value, 2),
            percentile_target=self.config.target_percentile,
            threshold_ms=self.config.threshold_ms,
            margin_percent=round(margin, 2),
            availability_actual=round(availability, 2) if availability else None,
            error_rate_actual=round(error_rate, 2) if error_rate else None,
            violations=violations,
        )

    def check_fraction(
        self,
        response_times_ms: Sequence[Union[int, float]],
        threshold_ms: Optional[float] = None,
        target_fraction: float = 0.99,
    ) -> SLAFractionResult:
        """
        Threshold-fraction SLI check: fraction of events at or under a
        latency threshold, compared against a target fraction.

        This is the sanctioned mode for SLO use (DEEPTHINK_04): fractions
        aggregate across time and hosts and weight by traffic, whereas the
        percentile point targets used by :meth:`check` do not — prefer this
        method when the result feeds an SLO or error budget.

        Applies the minimum-traffic validity rule
        ``min_events = 10 / (1 - target_fraction)``: below that floor the
        window cannot statistically support the target, so the result is
        flagged ``insufficient_traffic`` (WARNING, never confidently
        compliant).

        Args:
            response_times_ms: Response times in milliseconds
            threshold_ms: Latency threshold defining a good event
                (defaults to config.threshold_ms)
            target_fraction: Required fraction of good events (0-1 exclusive
                of 1.0)

        Returns:
            SLAFractionResult with good/total counts and compliance status

        Raises:
            ValueError: If dataset is empty or target_fraction not in (0, 1)
        """
        if not response_times_ms:
            raise ValueError("Cannot check SLA for empty dataset")
        if not (0.0 < target_fraction < 1.0):
            raise ValueError("target_fraction must be in (0, 1)")

        threshold = threshold_ms if threshold_ms is not None else self.config.threshold_ms
        total = len(response_times_ms)
        good = sum(1 for t in response_times_ms if t <= threshold)
        good_fraction = good / total

        minimum_events = int(math.ceil(10.0 / (1.0 - target_fraction)))
        insufficient = total < minimum_events

        violations: list[str] = []
        if good_fraction < target_fraction:
            violations.append(
                f"Good-event fraction {good_fraction:.4f} below target "
                f"{target_fraction:.4f} at threshold {threshold}ms"
            )
            status = SLAStatus.BREACHED
        else:
            status = SLAStatus.COMPLIANT

        if insufficient:
            violations.append(
                f"Insufficient traffic: {total} events < {minimum_events} "
                f"required to validate a {target_fraction:.4f} target; "
                "lower the target, widen the window, or add synthetic probes"
            )
            if status == SLAStatus.COMPLIANT:
                status = SLAStatus.WARNING

        return SLAFractionResult(
            status=status,
            good_events=good,
            total_events=total,
            good_fraction=round(good_fraction, 6),
            target_fraction=target_fraction,
            threshold_ms=threshold,
            minimum_events_required=minimum_events,
            insufficient_traffic=insufficient,
            violations=violations,
        )

    def check_multiple_windows(
        self,
        windows: Sequence[Sequence[Union[int, float]]],
    ) -> list[SLAResult]:
        """
        Check SLA compliance across multiple time windows.

        Useful for detecting intermittent SLA breaches.

        Args:
            windows: List of response time sequences (one per window)

        Returns:
            List of SLAResult, one per window
        """
        return [self.check(window) for window in windows]

    def calculate_compliance_rate(
        self,
        results: Sequence[SLAResult],
    ) -> float:
        """
        Calculate overall SLA compliance rate.

        Args:
            results: Sequence of SLA check results

        Returns:
            Percentage of windows that were compliant (0-100)
        """
        if not results:
            return 0.0

        compliant = sum(1 for r in results if r.status == SLAStatus.COMPLIANT)
        return (compliant / len(results)) * 100
