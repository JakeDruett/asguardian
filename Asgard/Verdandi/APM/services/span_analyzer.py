"""
Span Analyzer Service

Analyzes individual spans for performance characteristics and issues.
"""

import math
from typing import Dict, List, Optional, Sequence

from Asgard.Verdandi.APM.models.apm_models import (
    Span,
    SpanAnalysis,
    SpanStatus,
)


class SpanAnalyzer:
    """
    Analyzer for individual spans in distributed traces.

    Provides methods to analyze span performance, identify slow spans,
    calculate self-time, and generate recommendations.

    Example:
        analyzer = SpanAnalyzer(slow_threshold_ms=100)
        analysis = analyzer.analyze(span, child_spans)
        print(f"Self time: {analysis.self_time_ms}ms")
    """

    def __init__(
        self,
        slow_threshold_ms: float = 100.0,
        error_weight: float = 2.0,
    ):
        """
        Initialize the span analyzer.

        Args:
            slow_threshold_ms: Threshold above which a span is considered slow
            error_weight: Weight multiplier for errors in scoring
        """
        self.slow_threshold_ms = slow_threshold_ms
        self.error_weight = error_weight

    def analyze(
        self,
        span: Span,
        child_spans: Optional[List[Span]] = None,
    ) -> SpanAnalysis:
        """
        Analyze a single span.

        Args:
            span: The span to analyze
            child_spans: List of child spans (if known)

        Returns:
            SpanAnalysis with performance metrics and recommendations
        """
        child_spans = child_spans or []
        child_count = len(child_spans)
        total_child_duration = sum(cs.duration_ms for cs in child_spans)

        # Calculate self-time (time spent in span itself, excluding children)
        # This is simplified - actual implementation would need to handle overlapping spans
        self_time_ms = max(0.0, span.duration_ms - total_child_duration)

        is_slow = span.duration_ms > self.slow_threshold_ms
        slowness_factor = (
            span.duration_ms / self.slow_threshold_ms
            if self.slow_threshold_ms > 0
            else 1.0
        )
        is_error = span.status == SpanStatus.ERROR

        recommendations = self._generate_recommendations(
            span, is_slow, slowness_factor, is_error, self_time_ms, child_count
        )

        return SpanAnalysis(
            span=span,
            is_slow=is_slow,
            slowness_factor=slowness_factor,
            is_error=is_error,
            child_count=child_count,
            total_child_duration_ms=total_child_duration,
            self_time_ms=self_time_ms,
            recommendations=recommendations,
        )

    def analyze_batch(
        self,
        spans: Sequence[Span],
        spans_by_parent: Optional[Dict[str, List[Span]]] = None,
    ) -> List[SpanAnalysis]:
        """
        Analyze a batch of spans.

        Args:
            spans: List of spans to analyze
            spans_by_parent: Optional mapping of parent_span_id to child spans

        Returns:
            List of SpanAnalysis objects
        """
        if spans_by_parent is None:
            spans_by_parent = self._build_parent_map(spans)

        results = []
        for span in spans:
            child_spans = spans_by_parent.get(span.span_id, [])
            results.append(self.analyze(span, child_spans))
        return results

    def find_slow_spans(
        self,
        spans: Sequence[Span],
        threshold_ms: Optional[float] = None,
    ) -> List[Span]:
        """
        Find spans that exceed the slowness threshold.

        Args:
            spans: Spans to check
            threshold_ms: Custom threshold (uses default if not provided)

        Returns:
            List of slow spans sorted by duration (slowest first)
        """
        threshold = threshold_ms or self.slow_threshold_ms
        slow_spans = [s for s in spans if s.duration_ms > threshold]
        return sorted(slow_spans, key=lambda s: s.duration_ms, reverse=True)

    def find_error_spans(self, spans: Sequence[Span]) -> List[Span]:
        """
        Find spans with errors.

        Args:
            spans: Spans to check

        Returns:
            List of spans with error status
        """
        return [s for s in spans if s.status == SpanStatus.ERROR]

    def calculate_percentiles(
        self,
        spans: Sequence[Span],
    ) -> Dict[str, float]:
        """
        Calculate duration percentiles for a set of spans.

        Args:
            spans: Spans to analyze

        Returns:
            Dictionary with percentile values (p50, p75, p90, p95, p99)
        """
        if not spans:
            return {"p50": 0.0, "p75": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}

        durations = sorted([s.duration_ms for s in spans])
        return {
            "p50": self._percentile(durations, 50),
            "p75": self._percentile(durations, 75),
            "p90": self._percentile(durations, 90),
            "p95": self._percentile(durations, 95),
            "p99": self._percentile(durations, 99),
        }

    def calculate_statistics(
        self,
        spans: Sequence[Span],
    ) -> Dict[str, float]:
        """
        Calculate basic statistics for a set of spans.

        Args:
            spans: Spans to analyze

        Returns:
            Dictionary with statistical values
        """
        if not spans:
            return {
                "count": 0,
                "total_ms": 0.0,
                "mean_ms": 0.0,
                "min_ms": 0.0,
                "max_ms": 0.0,
                "std_dev_ms": 0.0,
            }

        durations = [s.duration_ms for s in spans]
        count = len(durations)
        total = sum(durations)
        mean = total / count
        min_val = min(durations)
        max_val = max(durations)

        variance = sum((d - mean) ** 2 for d in durations) / count
        std_dev = math.sqrt(variance)

        return {
            "count": count,
            "total_ms": total,
            "mean_ms": mean,
            "min_ms": min_val,
            "max_ms": max_val,
            "std_dev_ms": std_dev,
        }

    def group_by_operation(
        self,
        spans: Sequence[Span],
    ) -> Dict[str, List[Span]]:
        """
        Group spans by operation name.

        Args:
            spans: Spans to group

        Returns:
            Dictionary mapping operation name to list of spans
        """
        result: Dict[str, List[Span]] = {}
        for span in spans:
            if span.operation_name not in result:
                result[span.operation_name] = []
            result[span.operation_name].append(span)
        return result

    def group_by_service(
        self,
        spans: Sequence[Span],
    ) -> Dict[str, List[Span]]:
        """
        Group spans by service name.

        Args:
            spans: Spans to group

        Returns:
            Dictionary mapping service name to list of spans
        """
        result: Dict[str, List[Span]] = {}
        for span in spans:
            if span.service_name not in result:
                result[span.service_name] = []
            result[span.service_name].append(span)
        return result

    def _build_parent_map(
        self,
        spans: Sequence[Span],
    ) -> Dict[str, List[Span]]:
        """Build mapping of parent span IDs to child spans."""
        parent_map: Dict[str, List[Span]] = {}
        for span in spans:
            if span.parent_span_id:
                if span.parent_span_id not in parent_map:
                    parent_map[span.parent_span_id] = []
                parent_map[span.parent_span_id].append(span)
        return parent_map

    def _percentile(
        self,
        sorted_values: List[float],
        percentile: float,
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

    def _generate_recommendations(
        self,
        span: Span,
        is_slow: bool,
        slowness_factor: float,
        is_error: bool,
        self_time_ms: float,
        child_count: int,
    ) -> List[str]:
        """Generate recommendations based on span analysis."""
        recommendations = []

        if is_error:
            recommendations.append(
                f"Span '{span.operation_name}' has error status. "
                f"Error: {span.error_message or 'Unknown error'}"
            )

        if is_slow:
            if slowness_factor > 5:
                recommendations.append(
                    f"CRITICAL: Span '{span.operation_name}' is {slowness_factor:.1f}x "
                    f"slower than threshold ({span.duration_ms:.0f}ms vs {self.slow_threshold_ms}ms)"
                )
            elif slowness_factor > 2:
                recommendations.append(
                    f"Span '{span.operation_name}' is {slowness_factor:.1f}x "
                    f"slower than threshold"
                )

        if child_count > 0 and self_time_ms > span.duration_ms * 0.8:
            recommendations.append(
                f"Span '{span.operation_name}' has high self-time ({self_time_ms:.0f}ms) "
                f"despite having {child_count} child spans"
            )

        if child_count > 10:
            recommendations.append(
                f"Span '{span.operation_name}' has many child spans ({child_count}). "
                f"Consider batching operations"
            )

        return recommendations
