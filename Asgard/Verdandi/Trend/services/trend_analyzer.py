"""
Trend Analyzer Service

Analyzes performance trends over time.
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Sequence, Tuple

from Asgard.Verdandi.Trend.models.trend_models import (
    TrendAnalysis,
    TrendData,
    TrendDirection,
    TrendReport,
)


class TrendAnalyzer:
    """
    Analyzer for performance trends over time.

    Provides methods to detect and analyze trends in time series data
    using linear regression and statistical analysis.

    Example:
        analyzer = TrendAnalyzer()

        # Analyze trend in latency data
        data = [TrendData(timestamp=ts, value=val) for ts, val in zip(times, values)]
        trend = analyzer.analyze(data, metric_name="api_latency")

        if trend.direction == TrendDirection.DEGRADING:
            print(f"Performance degrading: {trend.change_percent}% over period")
    """

    def __init__(
        self,
        min_data_points: int = 5,
        significance_threshold: float = 5.0,
        r_squared_threshold: float = 0.3,
    ):
        """
        Initialize the trend analyzer.

        Args:
            min_data_points: Minimum points required for analysis
            significance_threshold: Percent change to consider significant
            r_squared_threshold: R-squared threshold for confident trend
        """
        self.min_data_points = min_data_points
        self.significance_threshold = significance_threshold
        self.r_squared_threshold = r_squared_threshold

    def analyze(
        self,
        data: Sequence[TrendData],
        metric_name: str = "metric",
    ) -> TrendAnalysis:
        """
        Analyze trend in time series data.

        Args:
            data: Sequence of TrendData points
            metric_name: Name of the metric

        Returns:
            TrendAnalysis with trend information
        """
        if len(data) < self.min_data_points:
            return TrendAnalysis(
                metric_name=metric_name,
                period_start=data[0].timestamp if data else datetime.now(),
                period_end=data[-1].timestamp if data else datetime.now(),
                description="Insufficient data points for trend analysis",
            )

        # Sort by timestamp
        sorted_data = sorted(data, key=lambda d: d.timestamp)
        values = [d.value for d in sorted_data]
        timestamps = [d.timestamp for d in sorted_data]

        # Convert timestamps to numeric (seconds from start)
        t0 = timestamps[0].timestamp()
        x_values = [(t.timestamp() - t0) for t in timestamps]

        # Calculate linear regression
        slope, intercept, r_squared = self._linear_regression(x_values, values)

        # Calculate slope per day
        slope_per_day = slope * 86400  # seconds in a day

        # Calculate statistics
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)
        volatility = std_dev / mean if mean != 0 else 0

        # Calculate change
        start_value = values[0]
        end_value = values[-1]
        change_absolute = end_value - start_value
        change_percent = (
            change_absolute / abs(start_value) * 100 if start_value != 0 else 0
        )

        # Determine trend direction
        direction = self._determine_direction(
            slope, change_percent, r_squared, metric_name
        )

        # Calculate confidence
        confidence = self._calculate_confidence(r_squared, len(data), slope)

        # Check for significance
        is_significant = (
            abs(change_percent) >= self.significance_threshold
            and r_squared >= self.r_squared_threshold
        )

        # Generate description
        description = self._generate_description(
            direction, change_percent, slope_per_day, r_squared
        )

        # Calculate period duration
        period_seconds = x_values[-1] - x_values[0] if x_values else 0

        return TrendAnalysis(
            metric_name=metric_name,
            analyzed_at=datetime.now(),
            period_start=timestamps[0],
            period_end=timestamps[-1],
            data_point_count=len(data),
            direction=direction,
            slope=slope,
            slope_per_day=slope_per_day,
            intercept=intercept,
            r_squared=r_squared,
            confidence=confidence,
            start_value=start_value,
            end_value=end_value,
            change_percent=change_percent,
            change_absolute=change_absolute,
            mean=mean,
            std_dev=std_dev,
            min_value=min(values),
            max_value=max(values),
            volatility=volatility,
            is_significant=is_significant,
            description=description,
        )

    def analyze_values(
        self,
        values: Sequence[float],
        metric_name: str = "metric",
        start_time: Optional[datetime] = None,
        interval_seconds: float = 60,
    ) -> TrendAnalysis:
        """
        Analyze trend from raw values (assuming uniform intervals).

        Args:
            values: Sequence of metric values
            metric_name: Name of the metric
            start_time: Start timestamp (default: now minus duration)
            interval_seconds: Interval between data points

        Returns:
            TrendAnalysis with trend information
        """
        if not values:
            return TrendAnalysis(
                metric_name=metric_name,
                period_start=datetime.now(),
                period_end=datetime.now(),
                description="No data provided",
            )

        start_time = start_time or (
            datetime.now() - timedelta(seconds=interval_seconds * len(values))
        )

        data = [
            TrendData(
                timestamp=start_time + timedelta(seconds=i * interval_seconds),
                value=v,
            )
            for i, v in enumerate(values)
        ]

        return self.analyze(data, metric_name)

    def analyze_multiple(
        self,
        metrics: Dict[str, Sequence[TrendData]],
    ) -> Dict[str, TrendAnalysis]:
        """
        Analyze trends for multiple metrics.

        Args:
            metrics: Dictionary of metric_name to data sequence

        Returns:
            Dictionary of metric_name to TrendAnalysis
        """
        return {name: self.analyze(data, name) for name, data in metrics.items()}

    def detect_change_points(
        self,
        data: Sequence[TrendData],
        window_size: int = 10,
        threshold: float = 2.0,
    ) -> List[Tuple[datetime, float]]:
        """
        Detect points where the trend changes significantly.

        Args:
            data: Sequence of TrendData points
            window_size: Size of comparison windows
            threshold: Z-score threshold for change detection

        Returns:
            List of (timestamp, change_magnitude) tuples
        """
        if len(data) < 2 * window_size:
            return []

        sorted_data = sorted(data, key=lambda d: d.timestamp)
        values = [d.value for d in sorted_data]
        timestamps = [d.timestamp for d in sorted_data]

        change_points = []

        for i in range(window_size, len(values) - window_size):
            before = values[i - window_size : i]
            after = values[i : i + window_size]

            before_mean = sum(before) / len(before)
            after_mean = sum(after) / len(after)

            # Pooled standard deviation
            before_var = sum((x - before_mean) ** 2 for x in before) / len(before)
            after_var = sum((x - after_mean) ** 2 for x in after) / len(after)
            pooled_std = math.sqrt((before_var + after_var) / 2)

            if pooled_std > 0:
                change_magnitude = abs(after_mean - before_mean) / pooled_std
                if change_magnitude >= threshold:
                    change_points.append((timestamps[i], change_magnitude))

        return change_points

    def generate_report(
        self,
        metrics: Dict[str, Sequence[TrendData]],
    ) -> TrendReport:
        """
        Generate a comprehensive trend report.

        Args:
            metrics: Dictionary of metric_name to data sequence

        Returns:
            TrendReport with analysis for all metrics
        """
        analyses = self.analyze_multiple(metrics)

        improving = []
        degrading = []
        stable = []

        for name, analysis in analyses.items():
            if analysis.direction == TrendDirection.IMPROVING:
                improving.append(name)
            elif analysis.direction == TrendDirection.DEGRADING:
                degrading.append(name)
            else:
                stable.append(name)

        # Determine overall health
        if len(degrading) > len(improving):
            overall_health = "degrading"
        elif len(improving) > len(degrading):
            overall_health = "improving"
        else:
            overall_health = "stable"

        # Generate recommendations
        recommendations = self._generate_report_recommendations(analyses)

        # Get period from first metric
        first_analysis = list(analyses.values())[0] if analyses else None

        return TrendReport(
            generated_at=datetime.now(),
            report_period_start=(
                first_analysis.period_start if first_analysis else datetime.now()
            ),
            report_period_end=(
                first_analysis.period_end if first_analysis else datetime.now()
            ),
            metrics_analyzed=len(analyses),
            trend_analyses=list(analyses.values()),
            improving_metrics=improving,
            degrading_metrics=degrading,
            stable_metrics=stable,
            overall_health=overall_health,
            recommendations=recommendations,
        )

    def _linear_regression(
        self,
        x: Sequence[float],
        y: Sequence[float],
    ) -> Tuple[float, float, float]:
        """
        Calculate linear regression (slope, intercept, r_squared).
        """
        n = len(x)
        if n < 2:
            return 0.0, y[0] if y else 0.0, 0.0

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y))
        sum_x2 = sum(xi * xi for xi in x)
        sum_y2 = sum(yi * yi for yi in y)

        # Slope
        denom = n * sum_x2 - sum_x * sum_x
        if denom == 0:
            return 0.0, sum_y / n, 0.0

        slope = (n * sum_xy - sum_x * sum_y) / denom
        intercept = (sum_y - slope * sum_x) / n

        # R-squared
        mean_y = sum_y / n
        ss_tot = sum((yi - mean_y) ** 2 for yi in y)
        ss_res = sum((yi - (slope * xi + intercept)) ** 2 for xi, yi in zip(x, y))

        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        r_squared = max(0.0, min(1.0, r_squared))  # Clamp to [0, 1]

        return slope, intercept, r_squared

    def _determine_direction(
        self,
        slope: float,
        change_percent: float,
        r_squared: float,
        metric_name: str,
    ) -> TrendDirection:
        """Determine trend direction."""
        # If R-squared is too low, trend is uncertain
        if r_squared < self.r_squared_threshold:
            if abs(change_percent) < self.significance_threshold:
                return TrendDirection.STABLE
            return TrendDirection.UNKNOWN

        # Determine if change is significant
        if abs(change_percent) < self.significance_threshold:
            return TrendDirection.STABLE

        # For latency metrics, increase is degrading
        # For throughput metrics, increase is improving
        is_latency_metric = any(
            term in metric_name.lower()
            for term in ["latency", "duration", "time", "delay", "response"]
        )

        if is_latency_metric:
            return TrendDirection.DEGRADING if slope > 0 else TrendDirection.IMPROVING
        else:
            # Assume higher is better for other metrics
            return TrendDirection.IMPROVING if slope > 0 else TrendDirection.DEGRADING

    def _calculate_confidence(
        self,
        r_squared: float,
        data_points: int,
        slope: float,
    ) -> float:
        """Calculate confidence in trend detection."""
        # R-squared contributes to confidence
        r_confidence = r_squared

        # More data points increase confidence
        data_confidence = min(1.0, data_points / 30)

        # Combine confidences
        return (0.7 * r_confidence + 0.3 * data_confidence)

    def _generate_description(
        self,
        direction: TrendDirection,
        change_percent: float,
        slope_per_day: float,
        r_squared: float,
    ) -> str:
        """Generate human-readable trend description."""
        if direction == TrendDirection.STABLE:
            return f"Metric is stable (R2={r_squared:.2f})"
        elif direction == TrendDirection.UNKNOWN:
            return (
                f"Trend unclear due to high variability "
                f"(change={change_percent:+.1f}%, R2={r_squared:.2f})"
            )
        else:
            dir_word = "improving" if direction == TrendDirection.IMPROVING else "degrading"
            return (
                f"Metric is {dir_word}: {change_percent:+.1f}% change, "
                f"{abs(slope_per_day):.2f}/day (R2={r_squared:.2f})"
            )

    def _generate_report_recommendations(
        self,
        analyses: Dict[str, TrendAnalysis],
    ) -> List[str]:
        """Generate recommendations for trend report."""
        recommendations = []

        # Find most degrading metric
        degrading = [
            (name, a) for name, a in analyses.items()
            if a.direction == TrendDirection.DEGRADING
        ]
        if degrading:
            worst = max(degrading, key=lambda x: abs(x[1].change_percent))
            recommendations.append(
                f"Investigate '{worst[0]}': degrading by {abs(worst[1].change_percent):.1f}% "
                f"over the analysis period."
            )

        # Count critical trends
        critical_count = sum(
            1 for a in analyses.values()
            if a.is_significant and a.direction == TrendDirection.DEGRADING
        )
        if critical_count > 0:
            recommendations.append(
                f"{critical_count} metric(s) showing significant degradation. "
                f"Review recent changes and resource utilization."
            )

        # Check for high volatility
        volatile = [
            name for name, a in analyses.items()
            if a.volatility > 0.5
        ]
        if volatile:
            recommendations.append(
                f"High volatility in: {', '.join(volatile[:3])}. "
                f"Consider investigating inconsistent performance."
            )

        return recommendations
