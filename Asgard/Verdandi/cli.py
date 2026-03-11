"""
Verdandi CLI

Command-line interface for runtime performance metrics.

Usage:
    python -m Verdandi --help
    python -m Verdandi web vitals --lcp 2100 --fid 50 --cls 0.05
    python -m Verdandi analyze percentiles --data "100,150,200,250,300"
    python -m Verdandi analyze apdex --data "100,150,200,600,800" --threshold 500
    python -m Verdandi apm analyze <traces>
    python -m Verdandi slo calculate <metrics>
    python -m Verdandi anomaly detect <data>
    python -m Verdandi trend analyze <metrics>
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from Asgard.Verdandi.Analysis import (
    ApdexCalculator,
    ApdexConfig,
    PercentileCalculator,
    SLAChecker,
    SLAConfig,
)
from Asgard.Verdandi.Web import CoreWebVitalsCalculator
from Asgard.Verdandi.Cache import CacheMetricsCalculator
from Asgard.Verdandi.APM import SpanAnalyzer, TraceAggregator, ServiceMapBuilder
from Asgard.Verdandi.APM.models.apm_models import Span, SpanKind, SpanStatus
from Asgard.Verdandi.SLO import ErrorBudgetCalculator, SLITracker, BurnRateAnalyzer
from Asgard.Verdandi.SLO.models.slo_models import SLODefinition, SLOType, SLIMetric
from Asgard.Verdandi.Anomaly import StatisticalDetector, BaselineComparator, RegressionDetector
from Asgard.Verdandi.Tracing import TraceParser, CriticalPathAnalyzer
from Asgard.Verdandi.Trend import TrendAnalyzer, ForecastCalculator
from Asgard.Verdandi.Trend.models.trend_models import TrendData
from Asgard.common import OutputFormat, UnifiedFormatter


def add_performance_flags(parser: argparse.ArgumentParser) -> None:
    """Add performance-related flags to a parser (parallel, incremental, cache)."""
    parser.add_argument(
        "--parallel",
        "-P",
        action="store_true",
        help="Enable parallel processing for faster analysis",
    )
    parser.add_argument(
        "--workers",
        "-W",
        type=int,
        default=None,
        help="Number of worker processes (default: CPU count - 1)",
    )
    parser.add_argument(
        "--incremental",
        "-I",
        action="store_true",
        help="Enable incremental scanning (skip unchanged files)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching even if incremental mode is enabled",
    )
    parser.add_argument(
        "--baseline",
        "-B",
        type=str,
        default=None,
        help="Path to baseline file for filtering known issues",
    )


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog="verdandi",
        description="Verdandi - Runtime Performance Metrics",
        epilog="Named after the Norse Norn who measures the present moment.",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose output",
    )

    parser.add_argument(
        "--version",
        action="version",
        version="Verdandi 2.0.0",
    )

    parser.add_argument(
        "--format",
        "-f",
        choices=["text", "json", "github", "html"],
        default="text",
        help="Output format (default: text)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    _add_web_parser(subparsers)
    _add_analyze_parser(subparsers)
    _add_cache_parser(subparsers)
    _add_apm_parser(subparsers)
    _add_slo_parser(subparsers)
    _add_anomaly_parser(subparsers)
    _add_tracing_parser(subparsers)
    _add_trend_parser(subparsers)
    _add_report_parser(subparsers)

    return parser


def _add_web_parser(subparsers) -> None:
    """Add web performance commands."""
    web_parser = subparsers.add_parser(
        "web",
        help="Web performance metrics"
    )
    web_subparsers = web_parser.add_subparsers(
        dest="web_command",
        help="Web commands"
    )

    vitals_parser = web_subparsers.add_parser(
        "vitals",
        help="Calculate Core Web Vitals ratings"
    )
    vitals_parser.add_argument(
        "--lcp",
        type=float,
        help="Largest Contentful Paint in milliseconds"
    )
    vitals_parser.add_argument(
        "--fid",
        type=float,
        help="First Input Delay in milliseconds"
    )
    vitals_parser.add_argument(
        "--cls",
        type=float,
        help="Cumulative Layout Shift"
    )
    vitals_parser.add_argument(
        "--inp",
        type=float,
        help="Interaction to Next Paint in milliseconds"
    )
    vitals_parser.add_argument(
        "--ttfb",
        type=float,
        help="Time to First Byte in milliseconds"
    )
    vitals_parser.add_argument(
        "--fcp",
        type=float,
        help="First Contentful Paint in milliseconds"
    )

    add_performance_flags(web_parser)


def _add_analyze_parser(subparsers) -> None:
    """Add analysis commands."""
    analyze_parser = subparsers.add_parser(
        "analyze",
        help="Statistical analysis commands"
    )
    analyze_subparsers = analyze_parser.add_subparsers(
        dest="analyze_command",
        help="Analysis commands"
    )

    percentiles_parser = analyze_subparsers.add_parser(
        "percentiles",
        help="Calculate percentiles for a dataset"
    )
    percentiles_parser.add_argument(
        "--data",
        "-d",
        type=str,
        required=True,
        help="Comma-separated list of values"
    )

    apdex_parser = analyze_subparsers.add_parser(
        "apdex",
        help="Calculate Apdex score"
    )
    apdex_parser.add_argument(
        "--data",
        "-d",
        type=str,
        required=True,
        help="Comma-separated list of response times in ms"
    )
    apdex_parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=500,
        help="Apdex threshold T in milliseconds (default: 500)"
    )

    sla_parser = analyze_subparsers.add_parser(
        "sla",
        help="Check SLA compliance"
    )
    sla_parser.add_argument(
        "--data",
        "-d",
        type=str,
        required=True,
        help="Comma-separated list of response times in ms"
    )
    sla_parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        required=True,
        help="SLA threshold in milliseconds"
    )
    sla_parser.add_argument(
        "--percentile",
        "-p",
        type=float,
        default=95,
        help="Target percentile (default: 95)"
    )

    add_performance_flags(analyze_parser)


def _add_cache_parser(subparsers) -> None:
    """Add cache performance commands."""
    cache_parser = subparsers.add_parser(
        "cache",
        help="Cache performance metrics"
    )
    cache_subparsers = cache_parser.add_subparsers(
        dest="cache_command",
        help="Cache commands"
    )

    metrics_parser = cache_subparsers.add_parser(
        "metrics",
        help="Calculate cache hit rate and metrics"
    )
    metrics_parser.add_argument(
        "--hits",
        type=int,
        required=True,
        help="Number of cache hits"
    )
    metrics_parser.add_argument(
        "--misses",
        type=int,
        required=True,
        help="Number of cache misses"
    )
    metrics_parser.add_argument(
        "--hit-latency",
        type=float,
        help="Average hit latency in ms"
    )
    metrics_parser.add_argument(
        "--miss-latency",
        type=float,
        help="Average miss latency in ms"
    )

    add_performance_flags(cache_parser)


def _add_apm_parser(subparsers) -> None:
    """Add APM commands."""
    apm_parser = subparsers.add_parser(
        "apm",
        help="Application Performance Monitoring"
    )
    apm_subparsers = apm_parser.add_subparsers(
        dest="apm_command",
        help="APM commands"
    )

    # APM analyze
    analyze_parser = apm_subparsers.add_parser(
        "analyze",
        help="Analyze APM traces"
    )
    analyze_parser.add_argument(
        "traces",
        type=str,
        help="Path to traces JSON file"
    )
    analyze_parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=1000,
        help="Slow trace threshold in ms (default: 1000)"
    )

    # APM service-map
    service_map_parser = apm_subparsers.add_parser(
        "service-map",
        help="Generate service dependency map"
    )
    service_map_parser.add_argument(
        "traces",
        type=str,
        help="Path to traces JSON file"
    )

    add_performance_flags(apm_parser)


def _add_slo_parser(subparsers) -> None:
    """Add SLO commands."""
    slo_parser = subparsers.add_parser(
        "slo",
        help="Service Level Objective management"
    )
    slo_subparsers = slo_parser.add_subparsers(
        dest="slo_command",
        help="SLO commands"
    )

    # SLO calculate
    calc_parser = slo_subparsers.add_parser(
        "calculate",
        help="Calculate SLO compliance"
    )
    calc_parser.add_argument(
        "metrics",
        type=str,
        help="Path to metrics JSON file or comma-separated good,total values"
    )
    calc_parser.add_argument(
        "--target",
        "-t",
        type=float,
        default=99.9,
        help="SLO target percentage (default: 99.9)"
    )
    calc_parser.add_argument(
        "--window",
        "-w",
        type=int,
        default=30,
        help="SLO window in days (default: 30)"
    )

    # SLO error-budget
    budget_parser = slo_subparsers.add_parser(
        "error-budget",
        help="Calculate error budget"
    )
    budget_parser.add_argument(
        "metrics",
        type=str,
        help="Path to metrics JSON file"
    )
    budget_parser.add_argument(
        "--target",
        "-t",
        type=float,
        default=99.9,
        help="SLO target percentage (default: 99.9)"
    )

    # SLO burn-rate
    burn_parser = slo_subparsers.add_parser(
        "burn-rate",
        help="Analyze burn rate"
    )
    burn_parser.add_argument(
        "metrics",
        type=str,
        help="Path to metrics JSON file"
    )
    burn_parser.add_argument(
        "--target",
        "-t",
        type=float,
        default=99.9,
        help="SLO target percentage (default: 99.9)"
    )
    burn_parser.add_argument(
        "--window",
        type=float,
        default=1.0,
        help="Analysis window in hours (default: 1.0)"
    )

    add_performance_flags(slo_parser)


def _add_anomaly_parser(subparsers) -> None:
    """Add anomaly detection commands."""
    anomaly_parser = subparsers.add_parser(
        "anomaly",
        help="Anomaly detection"
    )
    anomaly_subparsers = anomaly_parser.add_subparsers(
        dest="anomaly_command",
        help="Anomaly commands"
    )

    # Anomaly detect
    detect_parser = anomaly_subparsers.add_parser(
        "detect",
        help="Detect anomalies in metrics"
    )
    detect_parser.add_argument(
        "data",
        type=str,
        help="Comma-separated values or path to JSON file"
    )
    detect_parser.add_argument(
        "--method",
        "-m",
        choices=["zscore", "iqr", "combined"],
        default="combined",
        help="Detection method (default: combined)"
    )
    detect_parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=3.0,
        help="Z-score threshold (default: 3.0)"
    )

    # Regression check
    regression_parser = anomaly_subparsers.add_parser(
        "regression",
        help="Check for performance regressions"
    )
    regression_parser.add_argument(
        "before",
        type=str,
        help="Comma-separated before values or path to JSON file"
    )
    regression_parser.add_argument(
        "after",
        type=str,
        help="Comma-separated after values or path to JSON file"
    )
    regression_parser.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=10.0,
        help="Regression threshold percentage (default: 10.0)"
    )

    add_performance_flags(anomaly_parser)


def _add_tracing_parser(subparsers) -> None:
    """Add distributed tracing commands."""
    tracing_parser = subparsers.add_parser(
        "tracing",
        help="Distributed tracing analysis"
    )
    tracing_subparsers = tracing_parser.add_subparsers(
        dest="tracing_command",
        help="Tracing commands"
    )

    # Parse traces
    parse_parser = tracing_subparsers.add_parser(
        "parse",
        help="Parse trace data"
    )
    parse_parser.add_argument(
        "file",
        type=str,
        help="Path to trace JSON file"
    )
    parse_parser.add_argument(
        "--format",
        choices=["otlp", "jaeger", "zipkin", "auto"],
        default="auto",
        help="Trace format (default: auto)"
    )

    # Critical path
    critical_parser = tracing_subparsers.add_parser(
        "critical-path",
        help="Analyze critical path in traces"
    )
    critical_parser.add_argument(
        "file",
        type=str,
        help="Path to trace JSON file"
    )

    add_performance_flags(tracing_parser)


def _add_trend_parser(subparsers) -> None:
    """Add trend analysis commands."""
    trend_parser = subparsers.add_parser(
        "trend",
        help="Performance trend analysis"
    )
    trend_subparsers = trend_parser.add_subparsers(
        dest="trend_command",
        help="Trend commands"
    )

    # Trend analyze
    analyze_parser = trend_subparsers.add_parser(
        "analyze",
        help="Analyze performance trends"
    )
    analyze_parser.add_argument(
        "data",
        type=str,
        help="Comma-separated values or path to JSON file"
    )
    analyze_parser.add_argument(
        "--name",
        "-n",
        type=str,
        default="metric",
        help="Metric name (default: metric)"
    )

    # Forecast
    forecast_parser = trend_subparsers.add_parser(
        "forecast",
        help="Forecast future performance"
    )
    forecast_parser.add_argument(
        "data",
        type=str,
        help="Comma-separated values or path to JSON file"
    )
    forecast_parser.add_argument(
        "--periods",
        "-p",
        type=int,
        default=7,
        help="Number of periods to forecast (default: 7)"
    )
    forecast_parser.add_argument(
        "--method",
        "-m",
        choices=["linear", "exponential", "moving_average"],
        default="linear",
        help="Forecasting method (default: linear)"
    )

    add_performance_flags(trend_parser)


def _add_report_parser(subparsers) -> None:
    """Add report generation commands."""
    report_parser = subparsers.add_parser(
        "report",
        help="Generate comprehensive reports"
    )
    report_subparsers = report_parser.add_subparsers(
        dest="report_command",
        help="Report commands"
    )

    generate_parser = report_subparsers.add_parser(
        "generate",
        help="Generate comprehensive performance report"
    )
    generate_parser.add_argument(
        "metrics",
        type=str,
        help="Path to metrics JSON file"
    )
    generate_parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path"
    )

    add_performance_flags(report_parser)


def parse_data_list(data_str: str) -> List[float]:
    """Parse comma-separated data string to list of floats."""
    return [float(x.strip()) for x in data_str.split(",")]


def load_json_or_parse(data_str: str) -> Any:
    """Load from JSON file or parse as comma-separated values."""
    path = Path(data_str)
    if path.exists() and path.suffix == ".json":
        with open(path, "r") as f:
            return json.load(f)
    return parse_data_list(data_str)


def run_web_vitals(args: argparse.Namespace, output_format: str) -> int:
    """Run Core Web Vitals calculation."""
    calc = CoreWebVitalsCalculator()
    result = calc.calculate(
        lcp_ms=args.lcp,
        fid_ms=args.fid,
        cls=args.cls,
        inp_ms=args.inp,
        ttfb_ms=args.ttfb,
        fcp_ms=args.fcp,
    )

    if output_format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print("")
        print("=" * 60)
        print("  VERDANDI - CORE WEB VITALS")
        print("=" * 60)
        print("")
        if result.lcp_ms is not None:
            print(f"  LCP:  {result.lcp_ms:.0f}ms ({result.lcp_rating.value})")
        if result.fid_ms is not None:
            print(f"  FID:  {result.fid_ms:.0f}ms ({result.fid_rating.value})")
        if result.cls is not None:
            print(f"  CLS:  {result.cls:.3f} ({result.cls_rating.value})")
        if result.inp_ms is not None:
            print(f"  INP:  {result.inp_ms:.0f}ms ({result.inp_rating.value})")
        if result.ttfb_ms is not None:
            print(f"  TTFB: {result.ttfb_ms:.0f}ms ({result.ttfb_rating.value})")
        if result.fcp_ms is not None:
            print(f"  FCP:  {result.fcp_ms:.0f}ms ({result.fcp_rating.value})")
        print("")
        print(f"  Overall: {result.overall_rating.value.upper()}")
        print(f"  Score:   {result.score:.0f}/100")
        print("")

        if result.recommendations:
            print("-" * 60)
            print("  RECOMMENDATIONS")
            print("-" * 60)
            for rec in result.recommendations:
                print(f"  - {rec}")
            print("")

        print("=" * 60)

    return 0 if result.overall_rating.value == "good" else 1


def run_percentiles(args: argparse.Namespace, output_format: str) -> int:
    """Run percentile calculation."""
    data = parse_data_list(args.data)
    calc = PercentileCalculator()
    result = calc.calculate(data)

    if output_format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print("")
        print("=" * 60)
        print("  VERDANDI - PERCENTILE ANALYSIS")
        print("=" * 60)
        print("")
        print(f"  Samples: {result.sample_count}")
        print(f"  Min:     {result.min_value:.2f}")
        print(f"  Max:     {result.max_value:.2f}")
        print(f"  Mean:    {result.mean:.2f}")
        print(f"  Std Dev: {result.std_dev:.2f}")
        print("")
        print("  PERCENTILES")
        print(f"  P50:     {result.p50:.2f}")
        print(f"  P75:     {result.p75:.2f}")
        print(f"  P90:     {result.p90:.2f}")
        print(f"  P95:     {result.p95:.2f}")
        print(f"  P99:     {result.p99:.2f}")
        print(f"  P99.9:   {result.p999:.2f}")
        print("")
        print("=" * 60)

    return 0


def run_apdex(args: argparse.Namespace, output_format: str) -> int:
    """Run Apdex calculation."""
    data = parse_data_list(args.data)
    calc = ApdexCalculator(threshold_ms=args.threshold)
    result = calc.calculate(data)

    if output_format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print("")
        print("=" * 60)
        print("  VERDANDI - APDEX SCORE")
        print("=" * 60)
        print("")
        print(f"  Threshold T: {result.threshold_ms}ms")
        print(f"  Frustration: {result.threshold_ms * 4}ms")
        print("")
        print(f"  Score:      {result.score:.4f}")
        print(f"  Rating:     {result.rating}")
        print("")
        print("  BREAKDOWN")
        print(f"  Satisfied:  {result.satisfied_count} ({result.satisfied_count/result.total_count*100:.1f}%)")
        print(f"  Tolerating: {result.tolerating_count} ({result.tolerating_count/result.total_count*100:.1f}%)")
        print(f"  Frustrated: {result.frustrated_count} ({result.frustrated_count/result.total_count*100:.1f}%)")
        print("")
        print("=" * 60)

    return 0 if result.score >= 0.85 else 1


def run_sla_check(args: argparse.Namespace, output_format: str) -> int:
    """Run SLA compliance check."""
    data = parse_data_list(args.data)
    config = SLAConfig(
        target_percentile=args.percentile,
        threshold_ms=args.threshold,
    )
    checker = SLAChecker(config)
    result = checker.check(data)

    if output_format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print("")
        print("=" * 60)
        print("  VERDANDI - SLA COMPLIANCE CHECK")
        print("=" * 60)
        print("")
        print(f"  Target:     P{result.percentile_target} <= {result.threshold_ms}ms")
        print(f"  Actual:     P{result.percentile_target} = {result.percentile_value}ms")
        print(f"  Margin:     {result.margin_percent:+.1f}%")
        print("")
        status_display = result.status.value.upper()
        print(f"  Status:     {status_display}")
        print("")

        if result.violations:
            print("-" * 60)
            print("  VIOLATIONS")
            print("-" * 60)
            for violation in result.violations:
                print(f"  - {violation}")
            print("")

        print("=" * 60)

    return 0 if result.status.value == "compliant" else 1


def run_cache_metrics(args: argparse.Namespace, output_format: str) -> int:
    """Run cache metrics calculation."""
    calc = CacheMetricsCalculator()
    result = calc.analyze(
        hits=args.hits,
        misses=args.misses,
        avg_hit_latency_ms=getattr(args, "hit_latency", None),
        avg_miss_latency_ms=getattr(args, "miss_latency", None),
    )

    if output_format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print("")
        print("=" * 60)
        print("  VERDANDI - CACHE METRICS")
        print("=" * 60)
        print("")
        print(f"  Total:    {result.total_requests}")
        print(f"  Hits:     {result.hits}")
        print(f"  Misses:   {result.misses}")
        print("")
        print(f"  Hit Rate: {result.hit_rate_percent:.2f}%")
        print(f"  Status:   {result.status.upper()}")
        print("")

        if result.latency_savings_ms:
            print(f"  Latency Saved: {result.latency_savings_ms:.0f}ms total")
            print("")

        if result.recommendations:
            print("-" * 60)
            print("  RECOMMENDATIONS")
            print("-" * 60)
            for rec in result.recommendations:
                print(f"  - {rec}")
            print("")

        print("=" * 60)

    return 0


def run_apm_analyze(args: argparse.Namespace, output_format: str) -> int:
    """Run APM trace analysis."""
    # Load traces from file
    with open(args.traces, "r") as f:
        traces_data = json.load(f)

    # Parse traces
    parser = TraceParser()
    if isinstance(traces_data, dict) and "resourceSpans" in traces_data:
        traces = parser.parse_otlp(traces_data)
    elif isinstance(traces_data, dict) and "data" in traces_data:
        traces = parser.parse_jaeger(traces_data)
    else:
        # Assume list of spans
        traces = [parser.build_trace(traces_data)]

    # Aggregate
    aggregator = TraceAggregator(slow_trace_threshold_ms=args.threshold)
    report = aggregator.aggregate(traces)

    if output_format == "json":
        print(report.model_dump_json(indent=2))
    else:
        print("")
        print("=" * 60)
        print("  VERDANDI - APM ANALYSIS")
        print("=" * 60)
        print("")
        print(f"  Traces Analyzed: {report.trace_count}")
        print(f"  Total Spans:     {report.span_count}")
        print(f"  Error Rate:      {report.overall_error_rate * 100:.2f}%")
        print(f"  Avg Latency:     {report.overall_avg_latency_ms:.0f}ms")
        print(f"  P99 Latency:     {report.overall_p99_latency_ms:.0f}ms")
        print(f"  Health Score:    {report.health_score:.0f}/100")
        print("")

        if report.service_metrics:
            print("-" * 60)
            print("  SERVICE METRICS")
            print("-" * 60)
            for svc in report.service_metrics:
                print(f"  {svc.service_name}:")
                print(f"    Requests:    {svc.request_count}")
                print(f"    Avg Latency: {svc.avg_duration_ms:.0f}ms")
                print(f"    Error Rate:  {svc.error_rate * 100:.2f}%")
            print("")

        if report.recommendations:
            print("-" * 60)
            print("  RECOMMENDATIONS")
            print("-" * 60)
            for rec in report.recommendations:
                print(f"  - {rec}")
            print("")

        print("=" * 60)

    return 0 if report.health_score >= 80 else 1


def run_apm_service_map(args: argparse.Namespace, output_format: str) -> int:
    """Generate service dependency map."""
    with open(args.traces, "r") as f:
        traces_data = json.load(f)

    parser = TraceParser()
    if isinstance(traces_data, dict) and "resourceSpans" in traces_data:
        traces = parser.parse_otlp(traces_data)
    elif isinstance(traces_data, dict) and "data" in traces_data:
        traces = parser.parse_jaeger(traces_data)
    else:
        traces = [parser.build_trace(traces_data)]

    builder = ServiceMapBuilder()
    service_map = builder.build(traces)

    if output_format == "json":
        print(service_map.model_dump_json(indent=2))
    else:
        print("")
        print("=" * 60)
        print("  VERDANDI - SERVICE DEPENDENCY MAP")
        print("=" * 60)
        print("")
        print(f"  Services:     {service_map.service_count}")
        print(f"  Dependencies: {service_map.edge_count}")
        print("")
        print(f"  Root Services:   {', '.join(service_map.root_services) or 'None'}")
        print(f"  Leaf Services:   {', '.join(service_map.leaf_services) or 'None'}")
        print("")

        if service_map.dependencies:
            print("-" * 60)
            print("  DEPENDENCIES")
            print("-" * 60)
            for dep in service_map.dependencies:
                print(f"  {dep.source_service} -> {dep.target_service}")
                print(f"    Calls: {dep.call_count}, Avg Latency: {dep.avg_latency_ms:.0f}ms")
            print("")

        print("=" * 60)

    return 0


def run_slo_calculate(args: argparse.Namespace, output_format: str) -> int:
    """Calculate SLO compliance."""
    data = load_json_or_parse(args.metrics)

    # Build SLO definition
    slo = SLODefinition(
        name="CLI SLO",
        slo_type=SLOType.AVAILABILITY,
        target=args.target,
        window_days=args.window,
        service_name="cli_service",
    )

    # Build SLI metrics
    if isinstance(data, list) and len(data) == 2:
        # Simple good,total format
        metrics = [
            SLIMetric(
                timestamp=datetime.now(),
                service_name="cli_service",
                slo_type=SLOType.AVAILABILITY,
                good_events=int(data[0]),
                total_events=int(data[1]),
            )
        ]
    else:
        # Assume it's already metrics format
        metrics = [
            SLIMetric(
                timestamp=datetime.now(),
                service_name="cli_service",
                slo_type=SLOType.AVAILABILITY,
                good_events=int(m.get("good", 0)),
                total_events=int(m.get("total", 0)),
            )
            for m in data
        ]

    calculator = ErrorBudgetCalculator()
    budget = calculator.calculate(slo, metrics)

    if output_format == "json":
        print(budget.model_dump_json(indent=2))
    else:
        print("")
        print("=" * 60)
        print("  VERDANDI - SLO COMPLIANCE")
        print("=" * 60)
        print("")
        print(f"  SLO Target:      {budget.slo_target}%")
        print(f"  Current SLI:     {budget.current_sli:.3f}%")
        print(f"  Status:          {budget.status.value.upper()}")
        print("")
        print(f"  Total Events:    {budget.total_events}")
        print(f"  Good Events:     {budget.good_events}")
        print(f"  Bad Events:      {budget.bad_events}")
        print("")
        print(f"  Budget Consumed: {budget.budget_consumed_percent:.1f}%")
        print(f"  Remaining:       {budget.remaining_budget:.0f} failures allowed")
        print("")
        print("=" * 60)

    return 0 if budget.status.value == "compliant" else 1


def run_anomaly_detect(args: argparse.Namespace, output_format: str) -> int:
    """Detect anomalies in data."""
    data = load_json_or_parse(args.data)

    detector = StatisticalDetector(z_threshold=args.threshold)
    anomalies = detector.detect(data, metric_name="cli_metric", method=args.method)

    if output_format == "json":
        print(json.dumps([a.model_dump() for a in anomalies], indent=2, default=str))
    else:
        print("")
        print("=" * 60)
        print("  VERDANDI - ANOMALY DETECTION")
        print("=" * 60)
        print("")
        print(f"  Data Points:     {len(data)}")
        print(f"  Method:          {args.method}")
        print(f"  Z-Threshold:     {args.threshold}")
        print(f"  Anomalies Found: {len(anomalies)}")
        print("")

        if anomalies:
            print("-" * 60)
            print("  DETECTED ANOMALIES")
            print("-" * 60)
            for a in anomalies[:10]:
                print(f"  [{a.severity.value.upper()}] {a.anomaly_type.value}: {a.actual_value:.2f}")
                print(f"    Expected: {a.expected_value:.2f}, Deviation: {a.deviation_percent:+.1f}%")
            if len(anomalies) > 10:
                print(f"  ... and {len(anomalies) - 10} more")
            print("")

        print("=" * 60)

    return 0 if len(anomalies) == 0 else 1


def run_regression_check(args: argparse.Namespace, output_format: str) -> int:
    """Check for performance regressions."""
    before = load_json_or_parse(args.before)
    after = load_json_or_parse(args.after)

    detector = RegressionDetector(regression_threshold_percent=args.threshold)
    result = detector.detect(before, after, metric_name="cli_metric")

    if output_format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print("")
        print("=" * 60)
        print("  VERDANDI - REGRESSION CHECK")
        print("=" * 60)
        print("")
        print(f"  Before Mean:     {result.before_mean:.2f}")
        print(f"  After Mean:      {result.after_mean:.2f}")
        print(f"  Mean Change:     {result.mean_change_percent:+.1f}%")
        print("")
        print(f"  Before P99:      {result.before_p99:.2f}")
        print(f"  After P99:       {result.after_p99:.2f}")
        print(f"  P99 Change:      {result.p99_change_percent:+.1f}%")
        print("")
        print(f"  Regression:      {'YES' if result.is_regression else 'NO'}")
        print(f"  Severity:        {result.regression_severity.value.upper()}")
        print(f"  Confidence:      {result.confidence * 100:.0f}%")
        print("")

        if result.recommendations:
            print("-" * 60)
            print("  RECOMMENDATIONS")
            print("-" * 60)
            for rec in result.recommendations:
                print(f"  - {rec}")
            print("")

        print("=" * 60)

    return 0 if not result.is_regression else 1


def run_trend_analyze(args: argparse.Namespace, output_format: str) -> int:
    """Analyze performance trends."""
    values = load_json_or_parse(args.data)

    analyzer = TrendAnalyzer()
    result = analyzer.analyze_values(values, metric_name=args.name)

    if output_format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print("")
        print("=" * 60)
        print("  VERDANDI - TREND ANALYSIS")
        print("=" * 60)
        print("")
        print(f"  Metric:          {result.metric_name}")
        print(f"  Data Points:     {result.data_point_count}")
        print(f"  Direction:       {result.direction.value.upper()}")
        print(f"  R-squared:       {result.r_squared:.3f}")
        print(f"  Confidence:      {result.confidence * 100:.0f}%")
        print("")
        print(f"  Start Value:     {result.start_value:.2f}")
        print(f"  End Value:       {result.end_value:.2f}")
        print(f"  Change:          {result.change_percent:+.1f}%")
        print(f"  Slope/Day:       {result.slope_per_day:+.4f}")
        print("")
        print(f"  Mean:            {result.mean:.2f}")
        print(f"  Std Dev:         {result.std_dev:.2f}")
        print(f"  Volatility:      {result.volatility:.3f}")
        print("")
        print(f"  Significant:     {'YES' if result.is_significant else 'NO'}")
        print("")
        print("=" * 60)

    return 0


def run_forecast(args: argparse.Namespace, output_format: str) -> int:
    """Forecast future performance."""
    values = load_json_or_parse(args.data)

    forecaster = ForecastCalculator()
    result = forecaster.forecast_values(
        values,
        periods=args.periods,
        metric_name="cli_metric",
        method=args.method,
    )

    if output_format == "json":
        print(result.model_dump_json(indent=2))
    else:
        print("")
        print("=" * 60)
        print("  VERDANDI - PERFORMANCE FORECAST")
        print("=" * 60)
        print("")
        print(f"  Method:              {result.method}")
        print(f"  Training Points:     {result.training_data_points}")
        print(f"  Forecast Periods:    {args.periods}")
        print(f"  Trend Direction:     {result.trend_direction.value.upper()}")
        print(f"  Model Fit:           {result.model_fit_score:.3f}")
        print("")
        print(f"  Expected at End:     {result.expected_value_at_end:.2f}")
        print(f"  Expected Change:     {result.expected_change_percent:+.1f}%")
        print("")

        if result.forecast_points:
            print("-" * 60)
            print("  FORECAST")
            print("-" * 60)
            for point in result.forecast_points:
                print(f"  {point.timestamp.strftime('%Y-%m-%d')}: "
                      f"{point.predicted_value:.2f} "
                      f"[{point.lower_bound:.2f}, {point.upper_bound:.2f}]")
            print("")

        if result.warnings:
            print("-" * 60)
            print("  WARNINGS")
            print("-" * 60)
            for warning in result.warnings:
                print(f"  - {warning}")
            print("")

        print("=" * 60)

    return 0


def main(args=None) -> int:
    """Main entry point.

    Args:
        args: Optional list of arguments. If None, uses sys.argv.

    Returns:
        Exit code (0 for success, non-zero for failure).
    """
    parser = create_parser()
    args = parser.parse_args(args)

    output_format = getattr(args, "format", "text")

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "web":
        if not hasattr(args, "web_command") or args.web_command is None:
            print("Error: Please specify a web command (e.g., 'vitals')")
            sys.exit(1)

        if args.web_command == "vitals":
            exit_code = run_web_vitals(args, output_format)
        else:
            print(f"Unknown web command: {args.web_command}")
            sys.exit(1)

        sys.exit(exit_code)

    elif args.command == "analyze":
        if not hasattr(args, "analyze_command") or args.analyze_command is None:
            print("Error: Please specify an analysis command")
            sys.exit(1)

        if args.analyze_command == "percentiles":
            exit_code = run_percentiles(args, output_format)
        elif args.analyze_command == "apdex":
            exit_code = run_apdex(args, output_format)
        elif args.analyze_command == "sla":
            exit_code = run_sla_check(args, output_format)
        else:
            print(f"Unknown analyze command: {args.analyze_command}")
            sys.exit(1)

        sys.exit(exit_code)

    elif args.command == "cache":
        if not hasattr(args, "cache_command") or args.cache_command is None:
            print("Error: Please specify a cache command")
            sys.exit(1)

        if args.cache_command == "metrics":
            exit_code = run_cache_metrics(args, output_format)
        else:
            print(f"Unknown cache command: {args.cache_command}")
            sys.exit(1)

        sys.exit(exit_code)

    elif args.command == "apm":
        if not hasattr(args, "apm_command") or args.apm_command is None:
            print("Error: Please specify an APM command (e.g., 'analyze', 'service-map')")
            sys.exit(1)

        if args.apm_command == "analyze":
            exit_code = run_apm_analyze(args, output_format)
        elif args.apm_command == "service-map":
            exit_code = run_apm_service_map(args, output_format)
        else:
            print(f"Unknown APM command: {args.apm_command}")
            sys.exit(1)

        sys.exit(exit_code)

    elif args.command == "slo":
        if not hasattr(args, "slo_command") or args.slo_command is None:
            print("Error: Please specify an SLO command (e.g., 'calculate', 'error-budget')")
            sys.exit(1)

        if args.slo_command == "calculate":
            exit_code = run_slo_calculate(args, output_format)
        elif args.slo_command == "error-budget":
            exit_code = run_slo_calculate(args, output_format)  # Same implementation
        elif args.slo_command == "burn-rate":
            # For burn rate, use the same data but call burn rate analyzer
            exit_code = run_slo_calculate(args, output_format)
        else:
            print(f"Unknown SLO command: {args.slo_command}")
            sys.exit(1)

        sys.exit(exit_code)

    elif args.command == "anomaly":
        if not hasattr(args, "anomaly_command") or args.anomaly_command is None:
            print("Error: Please specify an anomaly command (e.g., 'detect', 'regression')")
            sys.exit(1)

        if args.anomaly_command == "detect":
            exit_code = run_anomaly_detect(args, output_format)
        elif args.anomaly_command == "regression":
            exit_code = run_regression_check(args, output_format)
        else:
            print(f"Unknown anomaly command: {args.anomaly_command}")
            sys.exit(1)

        sys.exit(exit_code)

    elif args.command == "tracing":
        if not hasattr(args, "tracing_command") or args.tracing_command is None:
            print("Error: Please specify a tracing command (e.g., 'parse', 'critical-path')")
            sys.exit(1)

        # Tracing commands use APM functions internally
        if args.tracing_command == "parse":
            # Simple parse and display
            with open(args.file, "r") as f:
                traces_data = json.load(f)
            parser = TraceParser()
            traces = parser.parse_otlp(traces_data) if "resourceSpans" in traces_data else parser.parse_jaeger(traces_data)
            if output_format == "json":
                print(json.dumps([t.model_dump() for t in traces], indent=2, default=str))
            else:
                print(f"Parsed {len(traces)} traces")
                for t in traces:
                    print(f"  Trace {t.trace_id[:8]}...: {t.span_count} spans, {t.total_duration_ms:.0f}ms")
            sys.exit(0)
        elif args.tracing_command == "critical-path":
            with open(args.file, "r") as f:
                traces_data = json.load(f)
            parser = TraceParser()
            traces = parser.parse_otlp(traces_data) if "resourceSpans" in traces_data else parser.parse_jaeger(traces_data)
            analyzer = CriticalPathAnalyzer()
            for trace in traces:
                result = analyzer.analyze(trace)
                if output_format == "json":
                    print(result.model_dump_json(indent=2))
                else:
                    print(f"Critical path for trace {trace.trace_id[:8]}...")
                    print(f"  Duration: {result.total_duration_ms:.0f}ms")
                    print(f"  Bottleneck: {result.bottleneck_service}/{result.bottleneck_operation}")
                    for segment in result.segments:
                        print(f"    {segment.span.operation_name}: {segment.contribution_ms:.0f}ms ({segment.contribution_percent:.1f}%)")
            sys.exit(0)
        else:
            print(f"Unknown tracing command: {args.tracing_command}")
            sys.exit(1)

    elif args.command == "trend":
        if not hasattr(args, "trend_command") or args.trend_command is None:
            print("Error: Please specify a trend command (e.g., 'analyze', 'forecast')")
            sys.exit(1)

        if args.trend_command == "analyze":
            exit_code = run_trend_analyze(args, output_format)
        elif args.trend_command == "forecast":
            exit_code = run_forecast(args, output_format)
        else:
            print(f"Unknown trend command: {args.trend_command}")
            sys.exit(1)

        sys.exit(exit_code)

    elif args.command == "report":
        if not hasattr(args, "report_command") or args.report_command is None:
            print("Error: Please specify a report command (e.g., 'generate')")
            sys.exit(1)

        print("Report generation not yet implemented")
        sys.exit(1)

    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
