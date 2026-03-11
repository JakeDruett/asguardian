# Web Vitals Test Fixtures

This directory contains Core Web Vitals and related performance data for testing Verdandi's web performance analysis functionality.

## Files

| File | Description | Use Case |
|------|-------------|----------|
| `good_performance.json` | All metrics in "good" range | Baseline testing, score validation |
| `poor_performance.json` | All metrics in "poor" range | Recommendation generation testing |
| `mixed_performance.json` | Realistic mixed performance | Real-world scenario testing |
| `navigation_timing.json` | Navigation Timing API data | Page load breakdown analysis |
| `resource_timing.json` | Resource Timing API data | Resource optimization analysis |

## Core Web Vitals Thresholds

| Metric | Good | Needs Improvement | Poor |
|--------|------|-------------------|------|
| LCP (Largest Contentful Paint) | < 2500ms | 2500-4000ms | > 4000ms |
| FID (First Input Delay) | < 100ms | 100-300ms | > 300ms |
| CLS (Cumulative Layout Shift) | < 0.1 | 0.1-0.25 | > 0.25 |
| INP (Interaction to Next Paint) | < 200ms | 200-500ms | > 500ms |
| TTFB (Time to First Byte) | < 800ms | 800-1800ms | > 1800ms |
| FCP (First Contentful Paint) | < 1800ms | 1800-3000ms | > 3000ms |

## Fixture Details

### good_performance.json

All metrics well within "good" thresholds:
- LCP: 1200ms (good < 2500ms)
- FID: 45ms (good < 100ms)
- CLS: 0.02 (good < 0.1)
- INP: 120ms (good < 200ms)
- TTFB: 180ms (good < 800ms)
- FCP: 850ms (good < 1800ms)

**Expected Score:** 95/100

### poor_performance.json

All metrics in "poor" range with detailed breakdown:
- LCP: 6500ms with image optimization issues
- FID: 450ms with long JavaScript tasks
- CLS: 0.42 with layout shift breakdown
- INP: 750ms with slow event handlers
- TTFB: 2800ms with server-side issues
- FCP: 4200ms with render-blocking resources

**Expected Score:** 15/100

Includes `issue_breakdown` with:
- LCP element analysis
- Long task identification
- Layout shift attribution

### mixed_performance.json

Realistic mixed data with:
- Field data (28-day collection)
- Lab data (Lighthouse)
- Hourly sample aggregation
- Week-over-week comparison
- Competitor benchmarking

**Expected Score:** 62/100

### navigation_timing.json

Navigation Timing API data including:
- DNS lookup timing
- TCP connection timing
- SSL handshake timing
- TTFB breakdown
- DOM processing time
- Waterfall visualization data
- Cache analysis (first vs repeat visit)

### resource_timing.json

Resource Timing API data including:
- Individual resource entries
- By-type aggregation (script, css, img, font)
- Largest resources identification
- Slowest resources identification
- Render-blocking resource detection
- Cache hit rate analysis

## Usage Examples

### Vitals Calculation

```python
from Asgard.Verdandi.Web.services.vitals_calculator import VitalsCalculator
import json

calculator = VitalsCalculator()

with open("good_performance.json") as f:
    data = json.load(f)

result = calculator.calculate(
    lcp_ms=data["metrics"]["lcp_ms"],
    fid_ms=data["metrics"]["fid_ms"],
    cls=data["metrics"]["cls"],
    inp_ms=data["metrics"]["inp_ms"],
    ttfb_ms=data["metrics"]["ttfb_ms"],
    fcp_ms=data["metrics"]["fcp_ms"]
)

assert result.overall_rating == "good"
assert result.score >= 90
```

### Navigation Timing Analysis

```python
from Asgard.Verdandi.Web.services.navigation_timing import NavigationTimingAnalyzer

analyzer = NavigationTimingAnalyzer()

with open("navigation_timing.json") as f:
    data = json.load(f)

result = analyzer.analyze(data["entries"][0])

print(f"TTFB: {result.ttfb_ms}ms")
print(f"Bottleneck: {result.bottleneck}")
print(f"Recommendations: {result.recommendations}")
```

### Resource Timing Analysis

```python
from Asgard.Verdandi.Web.services.resource_timing import ResourceTimingAnalyzer

analyzer = ResourceTimingAnalyzer()

with open("resource_timing.json") as f:
    data = json.load(f)

result = analyzer.analyze(data["resources"])

print(f"Total transfer: {result.total_transfer_bytes} bytes")
print(f"Blocking resources: {result.blocking_resources}")
print(f"Cache hit rate: {result.cache_hit_rate}")
```

## Testing Scenarios

1. **Rating Calculation**: Verify correct rating for each metric
2. **Score Calculation**: Validate overall score algorithm
3. **Recommendation Generation**: Check appropriate recommendations
4. **Threshold Handling**: Test boundary conditions
5. **Percentile Calculation**: Validate p75 calculations for CrUX-style data
6. **Trend Analysis**: Compare samples over time
7. **Resource Optimization**: Identify optimization opportunities
