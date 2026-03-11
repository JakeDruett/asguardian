"""
Verdandi Tracing - Distributed Trace Analysis

This module provides distributed tracing capabilities including:
- Trace parsing for OpenTelemetry/Jaeger formats
- Critical path analysis in distributed traces

Usage:
    from Asgard.Verdandi.Tracing import TraceParser, CriticalPathAnalyzer

    # Parse trace data
    parser = TraceParser()
    traces = parser.parse_otlp(trace_data)

    # Analyze critical path
    analyzer = CriticalPathAnalyzer()
    critical_path = analyzer.analyze(trace)
"""

__version__ = "1.0.0"
__author__ = "Asgard Contributors"

from Asgard.Verdandi.Tracing.models.tracing_models import (
    DistributedTrace,
    TraceSpan,
    SpanLink,
    TracingReport,
    CriticalPathResult,
)
from Asgard.Verdandi.Tracing.services.trace_parser import TraceParser
from Asgard.Verdandi.Tracing.services.critical_path_analyzer import CriticalPathAnalyzer

__all__ = [
    # Models
    "DistributedTrace",
    "TraceSpan",
    "SpanLink",
    "TracingReport",
    "CriticalPathResult",
    # Services
    "TraceParser",
    "CriticalPathAnalyzer",
]
