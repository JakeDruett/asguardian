"""
Trend Analyzer Service

Analyzes performance trends over time.
"""

import math
from typing import Sequence, Tuple, Union

from Asgard.Verdandi.Analysis.models.analysis_models import TrendDirection, TrendResult


class TrendAnalyzer:
    """
    Analyzer for performance metric trends.

    Detects improving, stable, or degrading trends in time series data
    using linear regression and statistical analysis.

    Example:
        analyzer = TrendAnalyzer()
        result = analyzer.analyze([100, 105, 110, 115, 120])
        print(f"Trend: {result.direction}")
    """

    def __init__(
        self,
        stability_threshold: float = 0.05,
        confidence_threshold: float = 0.7,
    ):
        """
        Initialize the trend analyzer.

        Args:
            stability_threshold: Percentage change below which trend is "stable"
            confidence_threshold: Minimum R-squared to trust trend direction
        """
        self.stability_threshold = stability_threshold
        self.confidence_threshold = confidence_threshold

    def analyze(
        self,
        values: Sequence[Union[int, float]],
        period_seconds: int = 3600,
        lower_is_better: bool = True,
    ) -> TrendResult:
        """
        Analyze trend in a time series.

        Args:
            values: Sequence of metric values (chronological order)
            period_seconds: Time period the values span
            lower_is_better: If True, decreasing values = improving

        Returns:
            TrendResult with trend direction and statistics
        """
        if len(values) < 2:
            raise ValueError("Need at least 2 data points for trend analysis")

        slope, r_squared = self._linear_regression(values)

        baseline = values[0]
        current = values[-1]
        change_percent = ((current - baseline) / baseline) * 100 if baseline != 0 else 0

        if abs(change_percent) < self.stability_threshold * 100:
            direction = TrendDirection.STABLE
        elif r_squared < self.confidence_threshold:
            direction = TrendDirection.STABLE
        else:
            if lower_is_better:
                direction = TrendDirection.IMPROVING if slope < 0 else TrendDirection.DEGRADING
            else:
                direction = TrendDirection.IMPROVING if slope > 0 else TrendDirection.DEGRADING

        anomalies = self._detect_anomalies(values)

        return TrendResult(
            direction=direction,
            slope=round(slope, 6),
            change_percent=round(change_percent, 2),
            confidence=round(r_squared, 4),
            data_points=len(values),
            period_seconds=period_seconds,
            baseline_value=float(baseline),
            current_value=float(current),
            anomalies_detected=len(anomalies),
        )

    def _linear_regression(
        self,
        values: Sequence[Union[int, float]],
    ) -> Tuple[float, float]:
        """
        Calculate linear regression slope and R-squared.

        Args:
            values: Sequence of values

        Returns:
            Tuple of (slope, r_squared)
        """
        n = len(values)
        x = list(range(n))
        y = list(values)

        x_mean = sum(x) / n
        y_mean = sum(y) / n

        numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0, 0.0

        slope = numerator / denominator

        y_pred = [slope * x[i] + (y_mean - slope * x_mean) for i in range(n)]
        ss_res = sum((y[i] - y_pred[i]) ** 2 for i in range(n))
        ss_tot = sum((y[i] - y_mean) ** 2 for i in range(n))

        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0

        return slope, max(0.0, r_squared)

    def _detect_anomalies(
        self,
        values: Sequence[Union[int, float]],
        std_threshold: float = 2.0,
    ) -> list[int]:
        """
        Detect anomalies using z-score method.

        Args:
            values: Sequence of values
            std_threshold: Number of standard deviations for anomaly

        Returns:
            List of indices where anomalies were detected
        """
        n = len(values)
        if n < 3:
            return []

        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n
        std_dev = math.sqrt(variance)

        if std_dev == 0:
            return []

        anomalies = []
        for i, value in enumerate(values):
            z_score = abs((value - mean) / std_dev)
            if z_score > std_threshold:
                anomalies.append(i)

        return anomalies

    def compare_periods(
        self,
        baseline_values: Sequence[Union[int, float]],
        current_values: Sequence[Union[int, float]],
        lower_is_better: bool = True,
    ) -> TrendResult:
        """
        Compare two time periods to detect performance changes.

        Args:
            baseline_values: Values from baseline period
            current_values: Values from current period
            lower_is_better: If True, lower values = better performance

        Returns:
            TrendResult comparing the two periods
        """
        baseline_mean = sum(baseline_values) / len(baseline_values)
        current_mean = sum(current_values) / len(current_values)

        change_percent = ((current_mean - baseline_mean) / baseline_mean) * 100 if baseline_mean != 0 else 0

        if abs(change_percent) < self.stability_threshold * 100:
            direction = TrendDirection.STABLE
        elif lower_is_better:
            direction = TrendDirection.IMPROVING if change_percent < 0 else TrendDirection.DEGRADING
        else:
            direction = TrendDirection.IMPROVING if change_percent > 0 else TrendDirection.DEGRADING

        return TrendResult(
            direction=direction,
            slope=0.0,
            change_percent=round(change_percent, 2),
            confidence=1.0,
            data_points=len(baseline_values) + len(current_values),
            period_seconds=0,
            baseline_value=baseline_mean,
            current_value=current_mean,
            anomalies_detected=0,
        )
