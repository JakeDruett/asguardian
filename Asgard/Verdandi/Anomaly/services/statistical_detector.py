"""
Statistical Detector Service

Provides statistical anomaly detection using z-score and IQR methods.
"""

import math
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from Asgard.Verdandi.Anomaly.models.anomaly_models import (
    AnomalyDetection,
    AnomalySeverity,
    AnomalyType,
    BaselineMetrics,
)


class StatisticalDetector:
    """
    Statistical anomaly detector using z-score and IQR methods.

    Provides methods to detect outliers and anomalies in performance data
    using statistical techniques.

    Example:
        detector = StatisticalDetector(z_threshold=3.0)

        # Detect anomalies using z-score
        anomalies = detector.detect_zscore(data, metric_name="latency")

        # Detect using IQR method
        anomalies = detector.detect_iqr(data, metric_name="latency")

        # Combined detection
        anomalies = detector.detect(data, metric_name="latency")
    """

    def __init__(
        self,
        z_threshold: float = 3.0,
        iqr_multiplier: float = 1.5,
        min_sample_size: int = 10,
    ):
        """
        Initialize the statistical detector.

        Args:
            z_threshold: Z-score threshold for anomaly detection
            iqr_multiplier: IQR multiplier for fence calculation (1.5 = standard, 3.0 = extreme)
            min_sample_size: Minimum samples required for detection
        """
        self.z_threshold = z_threshold
        self.iqr_multiplier = iqr_multiplier
        self.min_sample_size = min_sample_size

    def detect(
        self,
        values: Sequence[float],
        metric_name: str = "metric",
        timestamps: Optional[Sequence[datetime]] = None,
        method: str = "combined",
    ) -> List[AnomalyDetection]:
        """
        Detect anomalies in a dataset.

        Args:
            values: Sequence of metric values
            metric_name: Name of the metric
            timestamps: Optional timestamps for each value
            method: Detection method ("zscore", "iqr", or "combined")

        Returns:
            List of detected anomalies
        """
        if len(values) < self.min_sample_size:
            return []

        timestamps = timestamps or [
            datetime.now() for _ in range(len(values))
        ]

        if method == "zscore":
            return self.detect_zscore(values, metric_name, timestamps)
        elif method == "iqr":
            return self.detect_iqr(values, metric_name, timestamps)
        else:
            # Combined: union of both methods
            zscore_anomalies = self.detect_zscore(values, metric_name, timestamps)
            iqr_anomalies = self.detect_iqr(values, metric_name, timestamps)

            # Merge and deduplicate by timestamp
            seen_timestamps = set()
            combined = []
            for anomaly in zscore_anomalies + iqr_anomalies:
                if anomaly.data_timestamp not in seen_timestamps:
                    seen_timestamps.add(anomaly.data_timestamp)
                    combined.append(anomaly)

            return combined

    def detect_zscore(
        self,
        values: Sequence[float],
        metric_name: str = "metric",
        timestamps: Optional[Sequence[datetime]] = None,
    ) -> List[AnomalyDetection]:
        """
        Detect anomalies using z-score method.

        Args:
            values: Sequence of metric values
            metric_name: Name of the metric
            timestamps: Optional timestamps for each value

        Returns:
            List of detected anomalies
        """
        if len(values) < self.min_sample_size:
            return []

        timestamps = timestamps or [datetime.now() for _ in range(len(values))]
        mean, std_dev = self._calculate_mean_std(values)

        if std_dev == 0:
            return []  # No variation in data

        anomalies = []
        for i, (value, ts) in enumerate(zip(values, timestamps)):
            z_score = (value - mean) / std_dev

            if abs(z_score) >= self.z_threshold:
                anomaly_type = AnomalyType.SPIKE if z_score > 0 else AnomalyType.DROP
                severity = self._severity_from_zscore(z_score)

                anomalies.append(
                    AnomalyDetection(
                        detected_at=datetime.now(),
                        data_timestamp=ts,
                        anomaly_type=anomaly_type,
                        severity=severity,
                        metric_name=metric_name,
                        actual_value=value,
                        expected_value=mean,
                        deviation=abs(value - mean),
                        deviation_percent=abs(value - mean) / mean * 100 if mean != 0 else 0,
                        z_score=z_score,
                        confidence=self._confidence_from_zscore(z_score),
                        description=f"Z-score anomaly: {z_score:.2f} standard deviations from mean",
                    )
                )

        return anomalies

    def detect_iqr(
        self,
        values: Sequence[float],
        metric_name: str = "metric",
        timestamps: Optional[Sequence[datetime]] = None,
    ) -> List[AnomalyDetection]:
        """
        Detect anomalies using IQR (Interquartile Range) method.

        Args:
            values: Sequence of metric values
            metric_name: Name of the metric
            timestamps: Optional timestamps for each value

        Returns:
            List of detected anomalies
        """
        if len(values) < self.min_sample_size:
            return []

        timestamps = timestamps or [datetime.now() for _ in range(len(values))]

        q1, q3 = self._calculate_quartiles(values)
        iqr = q3 - q1
        lower_fence = q1 - self.iqr_multiplier * iqr
        upper_fence = q3 + self.iqr_multiplier * iqr
        median = self._percentile(sorted(values), 50)

        anomalies = []
        for i, (value, ts) in enumerate(zip(values, timestamps)):
            if value < lower_fence or value > upper_fence:
                anomaly_type = (
                    AnomalyType.SPIKE if value > upper_fence else AnomalyType.DROP
                )

                # Calculate how far outside the fence
                if value > upper_fence:
                    fence_distance = (value - upper_fence) / iqr if iqr > 0 else 0
                else:
                    fence_distance = (lower_fence - value) / iqr if iqr > 0 else 0

                severity = self._severity_from_iqr_distance(fence_distance)

                anomalies.append(
                    AnomalyDetection(
                        detected_at=datetime.now(),
                        data_timestamp=ts,
                        anomaly_type=anomaly_type,
                        severity=severity,
                        metric_name=metric_name,
                        actual_value=value,
                        expected_value=median,
                        deviation=abs(value - median),
                        deviation_percent=abs(value - median) / median * 100 if median != 0 else 0,
                        confidence=min(0.99, 0.5 + fence_distance * 0.1),
                        context={
                            "lower_fence": lower_fence,
                            "upper_fence": upper_fence,
                            "iqr": iqr,
                            "q1": q1,
                            "q3": q3,
                        },
                        description=f"IQR outlier: {fence_distance:.1f} IQRs beyond fence",
                    )
                )

        return anomalies

    def calculate_baseline(
        self,
        values: Sequence[float],
        metric_name: str = "metric",
        period_days: int = 7,
    ) -> BaselineMetrics:
        """
        Calculate baseline metrics from historical data.

        Args:
            values: Sequence of metric values
            metric_name: Name of the metric
            period_days: Period used for baseline (informational)

        Returns:
            BaselineMetrics with statistical properties
        """
        if not values:
            return BaselineMetrics(
                metric_name=metric_name, baseline_period_days=period_days
            )

        sorted_values = sorted(values)
        mean, std_dev = self._calculate_mean_std(values)
        q1, q3 = self._calculate_quartiles(values)
        iqr = q3 - q1

        return BaselineMetrics(
            metric_name=metric_name,
            calculated_at=datetime.now(),
            sample_count=len(values),
            baseline_period_days=period_days,
            mean=mean,
            median=self._percentile(sorted_values, 50),
            std_dev=std_dev,
            min_value=sorted_values[0],
            max_value=sorted_values[-1],
            p5=self._percentile(sorted_values, 5),
            p25=q1,
            p75=q3,
            p95=self._percentile(sorted_values, 95),
            p99=self._percentile(sorted_values, 99),
            iqr=iqr,
            lower_fence=q1 - self.iqr_multiplier * iqr,
            upper_fence=q3 + self.iqr_multiplier * iqr,
        )

    def detect_with_baseline(
        self,
        values: Sequence[float],
        baseline: BaselineMetrics,
        timestamps: Optional[Sequence[datetime]] = None,
    ) -> List[AnomalyDetection]:
        """
        Detect anomalies using a pre-calculated baseline.

        Args:
            values: Sequence of metric values to check
            baseline: Pre-calculated baseline metrics
            timestamps: Optional timestamps for each value

        Returns:
            List of detected anomalies
        """
        if not baseline.is_valid:
            return []

        timestamps = timestamps or [datetime.now() for _ in range(len(values))]
        anomalies = []

        for value, ts in zip(values, timestamps):
            # Z-score check
            z_score = (
                (value - baseline.mean) / baseline.std_dev
                if baseline.std_dev > 0
                else 0
            )

            # IQR check
            is_iqr_outlier = (
                value < baseline.lower_fence or value > baseline.upper_fence
            )

            if abs(z_score) >= self.z_threshold or is_iqr_outlier:
                anomaly_type = (
                    AnomalyType.SPIKE if value > baseline.mean else AnomalyType.DROP
                )
                severity = max(
                    self._severity_from_zscore(z_score),
                    self._severity_from_iqr_distance(
                        abs(value - baseline.median) / baseline.iqr if baseline.iqr > 0 else 0
                    ),
                )

                anomalies.append(
                    AnomalyDetection(
                        detected_at=datetime.now(),
                        data_timestamp=ts,
                        anomaly_type=anomaly_type,
                        severity=severity,
                        metric_name=baseline.metric_name,
                        actual_value=value,
                        expected_value=baseline.mean,
                        deviation=abs(value - baseline.mean),
                        deviation_percent=(
                            abs(value - baseline.mean) / baseline.mean * 100
                            if baseline.mean != 0
                            else 0
                        ),
                        z_score=z_score,
                        confidence=self._confidence_from_zscore(z_score),
                        description=f"Anomaly detected against baseline (z={z_score:.2f})",
                    )
                )

        return anomalies

    def find_change_points(
        self,
        values: Sequence[float],
        window_size: int = 10,
    ) -> List[Tuple[int, float]]:
        """
        Find potential change points in the data.

        Uses a sliding window to detect significant shifts in mean.

        Args:
            values: Sequence of metric values
            window_size: Size of comparison windows

        Returns:
            List of (index, change_magnitude) tuples
        """
        if len(values) < 2 * window_size:
            return []

        change_points = []

        for i in range(window_size, len(values) - window_size):
            before = values[i - window_size : i]
            after = values[i : i + window_size]

            before_mean = sum(before) / len(before)
            after_mean = sum(after) / len(after)

            # Calculate pooled standard deviation
            before_var = sum((x - before_mean) ** 2 for x in before) / len(before)
            after_var = sum((x - after_mean) ** 2 for x in after) / len(after)
            pooled_std = math.sqrt((before_var + after_var) / 2)

            if pooled_std > 0:
                change_magnitude = abs(after_mean - before_mean) / pooled_std

                if change_magnitude >= self.z_threshold:
                    change_points.append((i, change_magnitude))

        return change_points

    def _calculate_mean_std(
        self, values: Sequence[float]
    ) -> Tuple[float, float]:
        """Calculate mean and standard deviation."""
        n = len(values)
        if n == 0:
            return 0.0, 0.0

        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n
        std_dev = math.sqrt(variance)

        return mean, std_dev

    def _calculate_quartiles(
        self, values: Sequence[float]
    ) -> Tuple[float, float]:
        """Calculate Q1 and Q3."""
        sorted_values = sorted(values)
        q1 = self._percentile(sorted_values, 25)
        q3 = self._percentile(sorted_values, 75)
        return q1, q3

    def _percentile(
        self, sorted_values: List[float], percentile: float
    ) -> float:
        """Calculate percentile from sorted values."""
        if not sorted_values:
            return 0.0

        n = len(sorted_values)
        if n == 1:
            return sorted_values[0]

        rank = (percentile / 100) * (n - 1)
        lower_idx = int(rank)
        upper_idx = min(lower_idx + 1, n - 1)
        fraction = rank - lower_idx

        return sorted_values[lower_idx] + fraction * (
            sorted_values[upper_idx] - sorted_values[lower_idx]
        )

    def _severity_from_zscore(self, z_score: float) -> AnomalySeverity:
        """Determine severity from z-score."""
        abs_z = abs(z_score)
        if abs_z >= 5:
            return AnomalySeverity.CRITICAL
        elif abs_z >= 4:
            return AnomalySeverity.HIGH
        elif abs_z >= 3:
            return AnomalySeverity.MEDIUM
        elif abs_z >= 2:
            return AnomalySeverity.LOW
        return AnomalySeverity.INFO

    def _severity_from_iqr_distance(self, distance: float) -> AnomalySeverity:
        """Determine severity from IQR distance."""
        if distance >= 3:
            return AnomalySeverity.CRITICAL
        elif distance >= 2:
            return AnomalySeverity.HIGH
        elif distance >= 1.5:
            return AnomalySeverity.MEDIUM
        elif distance >= 1:
            return AnomalySeverity.LOW
        return AnomalySeverity.INFO

    def _confidence_from_zscore(self, z_score: float) -> float:
        """Calculate confidence from z-score."""
        # Approximate using sigmoid-like function
        abs_z = abs(z_score)
        return min(0.99, 1.0 - math.exp(-0.5 * abs_z))
