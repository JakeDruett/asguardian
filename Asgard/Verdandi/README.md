# Verdandi - Runtime Performance Metrics

Named after the Norse Norn who measures the present moment at the Well of Urd, Verdandi measures and calculates runtime performance metrics as they happen. Like its namesake who weaves the threads of fate in the now, Verdandi provides real-time insight into application performance.

## Overview

Verdandi is a runtime performance metrics package that calculates and analyzes performance data for web applications, databases, systems, networks, and caches. It provides statistical analysis tools including percentiles, Apdex scores, SLA compliance checking, and Core Web Vitals calculations.

## Features

- **Web Performance**: Core Web Vitals (LCP, FID, CLS, INP), navigation timing, resource timing
- **Database Metrics**: Query performance, throughput calculation, connection analysis
- **System Metrics**: Memory, CPU, I/O performance calculations
- **Network Metrics**: Latency, bandwidth, DNS timing analysis
- **Cache Performance**: Hit ratios, eviction rates, fill rates
- **Statistical Analysis**: Percentiles (P50, P75, P90, P95, P99), Apdex scores, SLA compliance, trend analysis

## Installation

```bash
pip install -e /path/to/Asgard
```

Or install directly:

```bash
cd /path/to/Asgard
pip install .
```

## Quick Start

### CLI Usage

```bash
# Core Web Vitals
python -m Verdandi web vitals --lcp 2100 --fid 50 --cls 0.05 --inp 150

# Percentile analysis
python -m Verdandi analyze percentiles --data "100,150,200,250,300,500,800,1200"

# Apdex score calculation
python -m Verdandi analyze apdex \
  --data "100,150,200,250,500,800,1000" \
  --threshold 500

# SLA compliance check
python -m Verdandi analyze sla \
  --data "100,150,200,250,300,500" \
  --threshold 300 \
  --percentile 95

# Cache metrics
python -m Verdandi cache metrics \
  --hits 850 \
  --misses 150 \
  --hit-latency 2.5 \
  --miss-latency 45.0

# JSON output for integration
python -m Verdandi analyze percentiles \
  --data "100,200,300" \
  --format json
```

### Python API Usage

```python
from Asgard.Verdandi import (
    CoreWebVitalsCalculator,
    PercentileCalculator,
    ApdexCalculator,
    SLAChecker,
    SLAConfig,
    CacheMetricsCalculator,
)

# Core Web Vitals Analysis
vitals_calc = CoreWebVitalsCalculator()
result = vitals_calc.calculate(
    lcp_ms=2100,
    fid_ms=50,
    cls=0.05,
    inp_ms=150,
    ttfb_ms=600,
    fcp_ms=1200
)

print(f"Overall Rating: {result.overall_rating.value}")
print(f"Score: {result.score}/100")
print(f"LCP: {result.lcp_rating.value} ({result.lcp_ms}ms)")
print(f"FID: {result.fid_rating.value} ({result.fid_ms}ms)")
print(f"CLS: {result.cls_rating.value} ({result.cls})")

if result.recommendations:
    print("\nRecommendations:")
    for rec in result.recommendations:
        print(f"  - {rec}")

# Percentile Calculation
response_times = [100, 150, 200, 250, 300, 400, 500, 800, 1200, 2000]
percentile_calc = PercentileCalculator()
result = percentile_calc.calculate(response_times)

print(f"P50 (Median): {result.p50}ms")
print(f"P90: {result.p90}ms")
print(f"P95: {result.p95}ms")
print(f"P99: {result.p99}ms")
print(f"Mean: {result.mean}ms")
print(f"Std Dev: {result.std_dev}ms")

# Apdex Score Calculation
apdex_calc = ApdexCalculator(threshold_ms=500)
result = apdex_calc.calculate(response_times)

print(f"Apdex Score: {result.score:.4f}")
print(f"Rating: {result.rating}")
print(f"Satisfied: {result.satisfied_count} ({result.satisfied_count/result.total_count*100:.1f}%)")
print(f"Tolerating: {result.tolerating_count}")
print(f"Frustrated: {result.frustrated_count}")

# SLA Compliance Checking
sla_config = SLAConfig(
    target_percentile=95,
    threshold_ms=300
)
sla_checker = SLAChecker(sla_config)
result = sla_checker.check(response_times)

print(f"SLA Status: {result.status.value}")
print(f"Target: P{result.percentile_target} <= {result.threshold_ms}ms")
print(f"Actual: P{result.percentile_target} = {result.percentile_value}ms")
print(f"Margin: {result.margin_percent:+.1f}%")

if not result.is_compliant:
    print("\nViolations:")
    for violation in result.violations:
        print(f"  - {violation}")

# Cache Performance Analysis
cache_calc = CacheMetricsCalculator()
result = cache_calc.analyze(
    hits=850,
    misses=150,
    avg_hit_latency_ms=2.5,
    avg_miss_latency_ms=45.0
)

print(f"Hit Rate: {result.hit_rate_percent:.2f}%")
print(f"Status: {result.status}")
print(f"Total Requests: {result.total_requests}")
print(f"Latency Saved: {result.latency_savings_ms:.0f}ms total")

if result.recommendations:
    print("\nRecommendations:")
    for rec in result.recommendations:
        print(f"  - {rec}")
```

## Submodules

### Web Module

Core Web Vitals and web performance metrics calculation.

**Services:**
- `CoreWebVitalsCalculator`: Calculate LCP, FID, CLS, INP, TTFB, FCP ratings
- `NavigationTiming`: Navigation timing analysis
- `ResourceTiming`: Resource loading analysis

**Key Metrics:**
- **LCP** (Largest Contentful Paint): Good < 2.5s, Needs Improvement < 4s, Poor >= 4s
- **FID** (First Input Delay): Good < 100ms, Needs Improvement < 300ms, Poor >= 300ms
- **CLS** (Cumulative Layout Shift): Good < 0.1, Needs Improvement < 0.25, Poor >= 0.25
- **INP** (Interaction to Next Paint): Good < 200ms, Needs Improvement < 500ms, Poor >= 500ms
- **TTFB** (Time to First Byte): Good < 800ms, Needs Improvement < 1800ms, Poor >= 1800ms
- **FCP** (First Contentful Paint): Good < 1.8s, Needs Improvement < 3s, Poor >= 3s

### Database Module

Database performance metrics and analysis.

**Services:**
- `QueryMetrics`: Query performance calculation
- `ThroughputCalculator`: Database throughput analysis
- `ConnectionAnalyzer`: Connection pool metrics

**Key Metrics:**
- Query execution time percentiles
- Queries per second
- Connection pool utilization
- Slow query detection

### System Module

System resource performance metrics.

**Services:**
- `MemoryCalculator`: Memory usage metrics
- `CPUCalculator`: CPU utilization calculation
- `IOCalculator`: I/O performance metrics

**Key Metrics:**
- Memory usage percentage
- CPU utilization
- I/O wait time
- Process metrics

### Network Module

Network performance metrics and latency calculation.

**Services:**
- `LatencyCalculator`: Network latency analysis
- `BandwidthCalculator`: Bandwidth utilization
- `DNSCalculator`: DNS resolution timing

**Key Metrics:**
- Round-trip time
- Bandwidth usage
- DNS lookup time
- Connection establishment time

### Cache Module

Cache performance analysis and optimization recommendations.

**Services:**
- `CacheMetricsCalculator`: Hit rate and performance calculation
- `EvictionAnalyzer`: Cache eviction pattern analysis

**Key Metrics:**
- Hit rate percentage
- Miss rate percentage
- Latency savings
- Fill rate
- Eviction rate

### Analysis Module

Statistical analysis and SLA compliance tools.

**Services:**
- `PercentileCalculator`: Calculate P50, P75, P90, P95, P99, P99.9
- `ApdexCalculator`: Application Performance Index calculation
- `SLAChecker`: SLA compliance verification
- `TrendAnalyzer`: Trend detection and forecasting
- `AggregationService`: Data aggregation utilities

**Key Features:**
- Percentile calculation with outlier detection
- Apdex scoring (Satisfied, Tolerating, Frustrated)
- SLA compliance with violation tracking
- Statistical analysis (mean, median, std dev)

## CLI Commands Reference

| Command | Description | Example |
|---------|-------------|---------|
| `web vitals` | Calculate Core Web Vitals | `python -m Verdandi web vitals --lcp 2100 --fid 50 --cls 0.05` |
| `analyze percentiles` | Calculate percentiles | `python -m Verdandi analyze percentiles --data "100,200,300"` |
| `analyze apdex` | Calculate Apdex score | `python -m Verdandi analyze apdex --data "100,200" --threshold 500` |
| `analyze sla` | Check SLA compliance | `python -m Verdandi analyze sla --data "100,200" --threshold 300` |
| `cache metrics` | Calculate cache metrics | `python -m Verdandi cache metrics --hits 850 --misses 150` |

## Configuration Options

### Common Options

- `--format, -f`: Output format (text, json) - default: text
- `--verbose, -v`: Verbose output

### Web Vitals Options

- `--lcp`: Largest Contentful Paint in milliseconds
- `--fid`: First Input Delay in milliseconds
- `--cls`: Cumulative Layout Shift
- `--inp`: Interaction to Next Paint in milliseconds
- `--ttfb`: Time to First Byte in milliseconds
- `--fcp`: First Contentful Paint in milliseconds

### Analysis Options

- `--data, -d`: Comma-separated list of values
- `--threshold, -t`: Threshold value in milliseconds
- `--percentile, -p`: Target percentile (default: 95)

### Cache Options

- `--hits`: Number of cache hits
- `--misses`: Number of cache misses
- `--hit-latency`: Average hit latency in milliseconds
- `--miss-latency`: Average miss latency in milliseconds

## Understanding the Metrics

### Apdex Score

The Application Performance Index (Apdex) is an industry standard for measuring application performance satisfaction:

- **Score Range**: 0.0 to 1.0
- **Rating Scale**:
  - Excellent: 0.94 - 1.00
  - Good: 0.85 - 0.93
  - Fair: 0.70 - 0.84
  - Poor: 0.50 - 0.69
  - Unacceptable: 0.00 - 0.49

**Categories:**
- **Satisfied**: Response time <= T (threshold)
- **Tolerating**: T < Response time <= 4T
- **Frustrated**: Response time > 4T

**Formula**: `Apdex = (Satisfied + (Tolerating / 2)) / Total`

### Percentiles

Percentiles represent the value below which a given percentage of observations fall:

- **P50 (Median)**: 50% of requests are faster than this
- **P90**: 90% of requests are faster than this
- **P95**: Commonly used for SLAs
- **P99**: Captures worst-case performance for most users
- **P99.9**: Captures outliers

### SLA Compliance

SLA compliance checks verify that performance meets agreed-upon service levels:

- **Target**: Specific percentile (e.g., P95) must be below threshold
- **Status**: Compliant, Warning, or Violation
- **Margin**: How far above/below threshold the actual value is

## Troubleshooting

### Common Issues

**Issue: "Invalid data format"**
- Ensure data is comma-separated numbers
- Remove spaces unless quoted
- Use decimal point (not comma) for floats

**Issue: "Insufficient data points"**
- Provide at least 10 data points for percentiles
- Need at least 1 data point for Apdex
- More data points = more accurate results

**Issue: "Threshold too low/high"**
- Apdex threshold should match user expectations (typically 200-1000ms)
- SLA threshold should be realistic for your application
- Consider P95 or P99 when setting thresholds

### Performance Tips

- Use JSON output for integration with monitoring systems
- Calculate percentiles on aggregated data, not real-time
- Cache percentile calculations for historical data
- Use Apdex for user-facing applications
- Set SLA thresholds based on business requirements

## Integration with Monitoring

```python
# Example: Integration with Prometheus/Grafana
from Asgard.Verdandi import PercentileCalculator, ApdexCalculator

def calculate_metrics(response_times: list):
    # Calculate percentiles
    percentile_calc = PercentileCalculator()
    percentiles = percentile_calc.calculate(response_times)

    # Calculate Apdex
    apdex_calc = ApdexCalculator(threshold_ms=500)
    apdex = apdex_calc.calculate(response_times)

    # Export to Prometheus format
    metrics = {
        'http_response_time_p50': percentiles.p50,
        'http_response_time_p95': percentiles.p95,
        'http_response_time_p99': percentiles.p99,
        'http_apdex_score': apdex.score,
    }

    return metrics
```

## Output Formats

### Text Output
Human-readable format with tables and formatting:
```
  VERDANDI - CORE WEB VITALS

  LCP:  2100ms (needs-improvement)
  FID:  50ms (good)
  CLS:  0.050 (good)

  Overall: NEEDS-IMPROVEMENT
  Score:   75/100
```

### JSON Output
Machine-readable format for integration:
```json
{
  "lcp_ms": 2100,
  "lcp_rating": "needs-improvement",
  "fid_ms": 50,
  "fid_rating": "good",
  "cls": 0.05,
  "cls_rating": "good",
  "overall_rating": "needs-improvement",
  "score": 75,
  "recommendations": ["Optimize LCP by reducing server response time"]
}
```

## Best Practices

1. **Set Realistic Thresholds**: Base thresholds on actual user expectations
2. **Use Percentiles**: P95 or P99 for SLAs, not averages
3. **Monitor Trends**: Track metrics over time, not just snapshots
4. **Segment Data**: Calculate metrics per endpoint, region, or user type
5. **Alert Appropriately**: Alert on SLA violations, not every fluctuation
6. **Core Web Vitals**: Monitor LCP, FID, CLS for all user-facing pages
7. **Cache Optimization**: Aim for 80%+ hit rate for most caches

## Version

Version: 1.0.0

## Author

Asgard Contributors
