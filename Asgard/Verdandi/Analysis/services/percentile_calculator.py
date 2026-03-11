"""
Percentile Calculator Service

Calculates statistical percentiles for performance metrics.
"""

import math
from typing import List, Optional, Sequence, Union

from Asgard.Verdandi.Analysis.models.analysis_models import PercentileResult


class PercentileCalculator:
    """
    Calculator for statistical percentiles.

    Provides methods to calculate common percentiles (P50, P75, P90, P95, P99, P99.9)
    as well as custom percentile values for any dataset.

    Example:
        calc = PercentileCalculator()
        result = calc.calculate([100, 150, 200, 250, 300])
        print(f"P95: {result.p95}")
    """

    def calculate(
        self,
        values: Sequence[Union[int, float]],
    ) -> PercentileResult:
        """
        Calculate standard percentiles for a dataset.

        Args:
            values: Sequence of numeric values to analyze

        Returns:
            PercentileResult containing all calculated statistics

        Raises:
            ValueError: If values is empty
        """
        if not values:
            raise ValueError("Cannot calculate percentiles for empty dataset")

        sorted_values = sorted(values)
        n = len(sorted_values)

        mean = sum(sorted_values) / n
        variance = sum((x - mean) ** 2 for x in sorted_values) / n
        std_dev = math.sqrt(variance)

        return PercentileResult(
            sample_count=n,
            min_value=float(sorted_values[0]),
            max_value=float(sorted_values[-1]),
            mean=mean,
            median=self.calculate_percentile(sorted_values, 50),
            std_dev=std_dev,
            p50=self.calculate_percentile(sorted_values, 50),
            p75=self.calculate_percentile(sorted_values, 75),
            p90=self.calculate_percentile(sorted_values, 90),
            p95=self.calculate_percentile(sorted_values, 95),
            p99=self.calculate_percentile(sorted_values, 99),
            p999=self.calculate_percentile(sorted_values, 99.9),
        )

    def calculate_percentile(
        self,
        values: Sequence[Union[int, float]],
        percentile: float,
        presorted: bool = False,
    ) -> float:
        """
        Calculate a specific percentile value.

        Uses linear interpolation between closest ranks.

        Args:
            values: Sequence of numeric values
            percentile: Percentile to calculate (0-100)
            presorted: If True, assumes values are already sorted

        Returns:
            The percentile value

        Raises:
            ValueError: If values is empty or percentile is out of range
        """
        if not values:
            raise ValueError("Cannot calculate percentile for empty dataset")
        if not 0 <= percentile <= 100:
            raise ValueError(f"Percentile must be between 0 and 100, got {percentile}")

        sorted_values = values if presorted else sorted(values)
        n = len(sorted_values)

        if n == 1:
            return float(sorted_values[0])

        rank = (percentile / 100) * (n - 1)
        lower_index = int(rank)
        upper_index = min(lower_index + 1, n - 1)
        fraction = rank - lower_index

        lower_value = sorted_values[lower_index]
        upper_value = sorted_values[upper_index]

        return float(lower_value + fraction * (upper_value - lower_value))

    def calculate_custom_percentiles(
        self,
        values: Sequence[Union[int, float]],
        percentiles: List[float],
    ) -> dict[float, float]:
        """
        Calculate multiple custom percentiles.

        Args:
            values: Sequence of numeric values
            percentiles: List of percentiles to calculate (0-100)

        Returns:
            Dictionary mapping percentile to value

        Example:
            calc.calculate_custom_percentiles([1,2,3,4,5], [10, 25, 50, 75, 90])
        """
        if not values:
            raise ValueError("Cannot calculate percentiles for empty dataset")

        sorted_values = sorted(values)
        return {
            p: self.calculate_percentile(sorted_values, p, presorted=True)
            for p in percentiles
        }

    def calculate_histogram(
        self,
        values: Sequence[Union[int, float]],
        buckets: Optional[List[float]] = None,
    ) -> dict[str, int]:
        """
        Calculate histogram bucket counts.

        Args:
            values: Sequence of numeric values
            buckets: Bucket boundaries (default: [10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000])

        Returns:
            Dictionary mapping bucket label to count
        """
        if buckets is None:
            buckets = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]

        histogram = {}
        sorted_buckets = sorted(buckets)

        for i, bucket in enumerate(sorted_buckets):
            if i == 0:
                label = f"<={bucket}"
            else:
                label = f"{sorted_buckets[i-1]}-{bucket}"
            histogram[label] = 0

        histogram[f">{sorted_buckets[-1]}"] = 0

        for value in values:
            placed = False
            for i, bucket in enumerate(sorted_buckets):
                if value <= bucket:
                    if i == 0:
                        label = f"<={bucket}"
                    else:
                        label = f"{sorted_buckets[i-1]}-{bucket}"
                    histogram[label] += 1
                    placed = True
                    break

            if not placed:
                histogram[f">{sorted_buckets[-1]}"] += 1

        return histogram
