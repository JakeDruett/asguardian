# Time Series Test Fixtures

This directory contains time series data for testing Verdandi's trend analysis, anomaly detection, and statistical analysis functionality.

## Files

| File | Description | Use Case |
|------|-------------|----------|
| `latency_1hour.json` | 1 hour of latency data (1 point/minute) | Short-term trend analysis |
| `latency_24hours.json` | 24 hours of latency data (1 point/hour) | Daily pattern detection |
| `latency_anomaly.json` | Data with various anomaly patterns | Anomaly detection testing |
| `cpu_usage.json` | CPU metrics over 2 hours | System resource analysis |

## Fixture Details

### latency_1hour.json

60 data points over 1 hour at 1-minute intervals:

**Statistics:**
- Mean: 50.87ms
- Median: 47.35ms
- Std Dev: 9.42ms
- Min: 42.5ms
- Max: 82.4ms

**Notable Events:**
- Spike at 14:15 (82.4ms, 3.35 sigma deviation)
- Generally stable trend

**Expected Trend:**
- Direction: Stable
- Confidence: 85%

### latency_24hours.json

24 data points over 24 hours at 1-hour intervals:

**Daily Pattern:**
- Peak hour: 12:00 (72.5ms)
- Trough hour: 04:00 (25.8ms)
- Peak-to-trough ratio: 2.81x

**Trend Analysis:**
- Direction: Degrading
- Change: +60.5% over 24 hours
- Correlation with traffic: 0.94

**Statistics:**
- Mean: 44.56ms
- Std Dev: 14.52ms
- P95: 68.95ms
- P99: 71.64ms

### latency_anomaly.json

120 data points over 2 hours with intentional anomalies:

**Anomaly Types:**

1. **Spike** (14:10)
   - Value: 185.6ms
   - Duration: 1 minute
   - Severity: High
   - Deviation: 16.7 sigma

2. **Level Shift** (14:20-14:30)
   - Average: 88.9ms
   - Duration: 10 minutes
   - Severity: Medium
   - Deviation: 4.9 sigma

3. **Gradual Increase** (14:40-14:55)
   - Start: 52.5ms
   - End: 102.3ms
   - Duration: 15 minutes
   - Rate: +3.32ms/minute
   - Severity: High

**Baseline:**
- Mean: 48.5ms
- Std Dev: 8.2ms

### cpu_usage.json

24 data points over 2 hours at 5-minute intervals:

**Metrics Included:**
- Total CPU usage
- User space usage
- System/kernel usage
- I/O wait
- Per-core breakdown (sample)
- Load averages (1m, 5m, 15m)

**Observations:**
- Peak usage: 88.5%
- Correlation with traffic: 0.92
- User CPU dominates (application-bound)

**Expected Status:** Warning

## Usage Examples

### Trend Analysis

```python
from Asgard.Verdandi.Analysis.services.trend_analyzer import TrendAnalyzer
import json

analyzer = TrendAnalyzer()

with open("latency_24hours.json") as f:
    data = json.load(f)

values = [dp["value"] for dp in data["data_points"]]
result = analyzer.analyze(values, interval_seconds=3600)

print(f"Direction: {result.direction}")
print(f"Slope: {result.slope}")
print(f"Change: {result.change_percent}%")
print(f"Confidence: {result.confidence}")
```

### Anomaly Detection

```python
from Asgard.Verdandi.Analysis.services.anomaly_detector import AnomalyDetector

detector = AnomalyDetector(
    spike_threshold_sigma=3.0,
    level_shift_window=5,
    trend_window=10
)

with open("latency_anomaly.json") as f:
    data = json.load(f)

values = [dp["value"] for dp in data["data_points"]]
anomalies = detector.detect(values)

for a in anomalies:
    print(f"{a.type}: {a.timestamp} - {a.description}")
```

### Percentile Calculation

```python
from Asgard.Verdandi.Analysis.services.percentile_calculator import PercentileCalculator

calculator = PercentileCalculator()

with open("latency_1hour.json") as f:
    data = json.load(f)

values = [dp["value"] for dp in data["data_points"]]
result = calculator.calculate(values)

print(f"P50: {result.p50}ms")
print(f"P95: {result.p95}ms")
print(f"P99: {result.p99}ms")
print(f"Mean: {result.mean}ms")
print(f"Std Dev: {result.std_dev}ms")
```

### CPU Analysis

```python
from Asgard.Verdandi.System.services.cpu_calculator import CpuCalculator

calculator = CpuCalculator()

with open("cpu_usage.json") as f:
    data = json.load(f)

result = calculator.analyze(data["data_points"])

print(f"Average usage: {result.usage_percent}%")
print(f"Load average (1m): {result.load_average_1m}")
print(f"Status: {result.status}")
print(f"Recommendations: {result.recommendations}")
```

## Testing Scenarios

1. **Trend Detection**
   - Stable trends (latency_1hour)
   - Degrading trends (latency_24hours)
   - Slope calculation
   - Confidence scoring

2. **Anomaly Detection**
   - Point anomalies (spikes)
   - Level shifts
   - Gradual changes
   - Seasonality

3. **Statistical Analysis**
   - Percentile calculation
   - Mean/median/std dev
   - Range and variance
   - Distribution shape

4. **Pattern Recognition**
   - Daily patterns
   - Peak/trough identification
   - Correlation analysis
   - Seasonality detection

5. **System Metrics**
   - CPU utilization thresholds
   - Load average interpretation
   - I/O wait analysis
   - Bottleneck identification

## Anomaly Detection Configuration

| Parameter | Description | Default |
|-----------|-------------|---------|
| `spike_threshold_sigma` | Standard deviations for spike detection | 3.0 |
| `level_shift_window_minutes` | Window size for level shift detection | 5 |
| `level_shift_threshold_percent` | Minimum change for level shift | 30% |
| `trend_window_minutes` | Window size for trend detection | 10 |
| `trend_threshold_percent` | Minimum change for trend alert | 50% |
