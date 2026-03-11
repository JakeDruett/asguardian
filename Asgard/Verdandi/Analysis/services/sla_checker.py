"""
SLA Checker Service

Checks Service Level Agreement compliance for performance metrics.
"""

from typing import Optional, Sequence, Union

from Asgard.Verdandi.Analysis.models.analysis_models import (
    SLAConfig,
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

        if percentile_value > self.config.threshold_ms:
            violations.append(
                f"P{self.config.target_percentile} response time {percentile_value:.1f}ms "
                f"exceeds threshold {self.config.threshold_ms}ms"
            )
            status = SLAStatus.BREACHED
        elif margin < (100 - self.config.warning_threshold_percent):
            status = SLAStatus.WARNING

        if availability is not None and self.config.availability_target:
            if availability < self.config.availability_target:
                violations.append(
                    f"Availability {availability:.2f}% below target {self.config.availability_target}%"
                )
                status = SLAStatus.BREACHED

        if error_rate is not None and self.config.error_rate_threshold:
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
            return 100.0

        compliant = sum(1 for r in results if r.status == SLAStatus.COMPLIANT)
        return (compliant / len(results)) * 100
