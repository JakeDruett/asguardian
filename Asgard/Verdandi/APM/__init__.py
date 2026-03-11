"""
Verdandi APM - Application Performance Monitoring

This module provides APM capabilities including:
- Span analysis for individual operations
- Trace aggregation for service-level metrics
- Service dependency map generation

Usage:
    from Asgard.Verdandi.APM import SpanAnalyzer, TraceAggregator, ServiceMapBuilder

    # Analyze spans
    analyzer = SpanAnalyzer()
    analysis = analyzer.analyze(spans)

    # Aggregate traces
    aggregator = TraceAggregator()
    service_metrics = aggregator.aggregate(traces)

    # Build service map
    builder = ServiceMapBuilder()
    service_map = builder.build(traces)
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Verdandi.APM.models.apm_models import (
    Span,
    SpanKind,
    SpanStatus,
    Trace,
    ServiceMetrics,
    ServiceDependency,
    ServiceMap,
    APMReport,
    SpanAnalysis,
)
from Asgard.Verdandi.APM.services.span_analyzer import SpanAnalyzer
from Asgard.Verdandi.APM.services.trace_aggregator import TraceAggregator
from Asgard.Verdandi.APM.services.service_map_builder import ServiceMapBuilder

__all__ = [
    # Models
    "Span",
    "SpanKind",
    "SpanStatus",
    "Trace",
    "ServiceMetrics",
    "ServiceDependency",
    "ServiceMap",
    "APMReport",
    "SpanAnalysis",
    # Services
    "SpanAnalyzer",
    "TraceAggregator",
    "ServiceMapBuilder",
]
