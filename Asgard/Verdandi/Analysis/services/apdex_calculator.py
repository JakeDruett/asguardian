"""
Apdex Calculator Service

Calculates Application Performance Index (Apdex) scores.
"""

from typing import Optional, Sequence, Union

from Asgard.Verdandi.Analysis.models.analysis_models import ApdexConfig, ApdexResult


class ApdexCalculator:
    """
    Calculator for Application Performance Index (Apdex) scores.

    Apdex measures user satisfaction based on response time:
    - Satisfied: response time <= T
    - Tolerating: T < response time <= 4T
    - Frustrated: response time > 4T

    Formula: Apdex = (Satisfied + Tolerating * 0.5) / Total

    Example:
        calc = ApdexCalculator(threshold_ms=500)
        result = calc.calculate([100, 200, 300, 600, 800, 2500])
        print(f"Apdex Score: {result.score}")
    """

    def __init__(
        self,
        threshold_ms: float = 500.0,
        frustration_multiplier: float = 4.0,
    ):
        """
        Initialize the Apdex calculator.

        Args:
            threshold_ms: Satisfied threshold T in milliseconds
            frustration_multiplier: Multiplier for frustration threshold (default 4T)
        """
        self.config = ApdexConfig(
            threshold_ms=threshold_ms,
            frustration_multiplier=frustration_multiplier,
        )

    def calculate(
        self,
        response_times_ms: Sequence[Union[int, float]],
        config: Optional[ApdexConfig] = None,
    ) -> ApdexResult:
        """
        Calculate Apdex score for a set of response times.

        Args:
            response_times_ms: Sequence of response times in milliseconds
            config: Optional config override

        Returns:
            ApdexResult with score and breakdown

        Raises:
            ValueError: If response_times_ms is empty
        """
        if not response_times_ms:
            raise ValueError("Cannot calculate Apdex for empty dataset")

        cfg = config or self.config
        threshold = cfg.threshold_ms
        frustration_threshold = cfg.frustration_threshold_ms

        satisfied = 0
        tolerating = 0
        frustrated = 0

        for time_ms in response_times_ms:
            if time_ms <= threshold:
                satisfied += 1
            elif time_ms <= frustration_threshold:
                tolerating += 1
            else:
                frustrated += 1

        total = satisfied + tolerating + frustrated
        score = (satisfied + tolerating * 0.5) / total

        return ApdexResult(
            score=round(score, 4),
            satisfied_count=satisfied,
            tolerating_count=tolerating,
            frustrated_count=frustrated,
            total_count=total,
            threshold_ms=threshold,
            rating=ApdexResult.get_rating(score),
        )

    def calculate_with_weights(
        self,
        response_times_ms: Sequence[Union[int, float]],
        weights: Sequence[Union[int, float]],
        config: Optional[ApdexConfig] = None,
    ) -> ApdexResult:
        """
        Calculate weighted Apdex score.

        Useful when different transactions have different importance.

        Args:
            response_times_ms: Sequence of response times in milliseconds
            weights: Weights for each response time (must match length)
            config: Optional config override

        Returns:
            ApdexResult with weighted score

        Raises:
            ValueError: If lengths don't match or inputs are empty
        """
        if not response_times_ms:
            raise ValueError("Cannot calculate Apdex for empty dataset")
        if len(response_times_ms) != len(weights):
            raise ValueError("Response times and weights must have same length")

        cfg = config or self.config
        threshold = cfg.threshold_ms
        frustration_threshold = cfg.frustration_threshold_ms

        satisfied_weight = 0.0
        tolerating_weight = 0.0
        frustrated_weight = 0.0
        total_weight = sum(weights)

        satisfied_count = 0
        tolerating_count = 0
        frustrated_count = 0

        for time_ms, weight in zip(response_times_ms, weights):
            if time_ms <= threshold:
                satisfied_weight += weight
                satisfied_count += 1
            elif time_ms <= frustration_threshold:
                tolerating_weight += weight
                tolerating_count += 1
            else:
                frustrated_weight += weight
                frustrated_count += 1

        score = (satisfied_weight + tolerating_weight * 0.5) / total_weight

        return ApdexResult(
            score=round(score, 4),
            satisfied_count=satisfied_count,
            tolerating_count=tolerating_count,
            frustrated_count=frustrated_count,
            total_count=len(response_times_ms),
            threshold_ms=threshold,
            rating=ApdexResult.get_rating(score),
        )

    @staticmethod
    def get_recommended_threshold(
        response_times_ms: Sequence[Union[int, float]],
        target_score: float = 0.85,
    ) -> float:
        """
        Calculate recommended threshold to achieve target Apdex score.

        Args:
            response_times_ms: Historical response times
            target_score: Desired Apdex score (default 0.85 = Good)

        Returns:
            Recommended threshold T in milliseconds
        """
        if not response_times_ms:
            return 500.0

        sorted_times = sorted(response_times_ms)
        n = len(sorted_times)

        target_satisfied = target_score * n

        if target_satisfied >= n:
            return sorted_times[-1]

        index = int(target_satisfied)
        if index >= n:
            index = n - 1

        return sorted_times[index]
