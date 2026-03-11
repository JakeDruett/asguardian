# Statistical Distribution Test Fixtures

This directory contains data with known statistical distributions for validating Verdandi's statistical analysis and percentile calculation functionality.

## Files

| File | Description | Use Case |
|------|-------------|----------|
| `normal_distribution.json` | Normally distributed data (mean=50, std=10) | Basic statistics validation |
| `bimodal_distribution.json` | Two-peak distribution (cache hit/miss) | Mode detection, multimodal analysis |
| `heavy_tail.json` | Log-normal with outliers | P99 testing, outlier handling |
| `uniform_distribution.json` | Uniform distribution (10-100) | Non-normal statistics |

## Fixture Details

### normal_distribution.json

Standard normal distribution for baseline testing:

**Parameters:**
- Mean: 50.0
- Standard Deviation: 10.0
- Sample Size: 1000

**Expected Statistics:**
- Skewness: ~0 (symmetric)
- Kurtosis: ~3 (mesokurtic)

**Expected Percentiles:**
| Percentile | Value |
|------------|-------|
| P50 | 50.0 |
| P75 | 56.74 |
| P90 | 62.82 |
| P95 | 66.45 |
| P99 | 73.26 |

**Normality Tests:**
- Shapiro-Wilk: Should pass (p > 0.05)
- Anderson-Darling: Should pass

### bimodal_distribution.json

Two distinct modes representing cache behavior:

**Mode 1 (Fast - Cache Hit):**
- Mean: 25ms
- Std Dev: 5ms
- Weight: 70%

**Mode 2 (Slow - Cache Miss):**
- Mean: 80ms
- Std Dev: 10ms
- Weight: 30%

**Key Insights:**
- P50 (25.2ms) represents cache hit performance
- P75+ (77.8ms+) represents cache miss performance
- Valley location: ~50ms

**Use Case:** Testing detection of bimodal patterns in response time distributions.

### heavy_tail.json

Log-normal distribution with significant outliers:

**Parameters:**
- Mu: 3.9
- Sigma: 0.8
- Sample Size: 1000

**Key Statistics:**
- Mean: 125.8ms
- Median: 52.5ms
- P99: 2150.4ms
- P99/P50 ratio: 41x

**Outlier Analysis:**
- Values above 1 second: 12
- Values above 2 seconds: 5
- Outlier percentage: 4.5%

**SLA Impact:**
- Threshold: 500ms
- Violations: 32 (3.2%)

**Use Case:** Testing P99 calculation and outlier handling for tail latency analysis.

### uniform_distribution.json

Evenly distributed data for non-normal testing:

**Parameters:**
- Minimum: 10.0
- Maximum: 100.0
- Sample Size: 500

**Expected Statistics:**
- Mean: 55.0
- Median: 55.0
- Std Dev: 26.0
- Skewness: 0

**Theoretical Percentiles:**
| Percentile | Value |
|------------|-------|
| P50 | 55.0 |
| P75 | 77.5 |
| P90 | 91.0 |
| P95 | 95.5 |

**Use Case:** Validating statistics on non-normal distributions.

## Usage Examples

### Percentile Calculation Validation

```python
from Asgard.Verdandi.Analysis.services.percentile_calculator import PercentileCalculator
import json

calculator = PercentileCalculator()

with open("normal_distribution.json") as f:
    data = json.load(f)

result = calculator.calculate(data["data"])

# Validate against expected values
assert abs(result.p50 - 50.0) < 1.0
assert abs(result.p95 - 66.45) < 2.0
assert abs(result.mean - 50.0) < 1.0
assert abs(result.std_dev - 10.0) < 1.0
```

### Distribution Detection

```python
from Asgard.Verdandi.Analysis.services.distribution_analyzer import DistributionAnalyzer

analyzer = DistributionAnalyzer()

with open("bimodal_distribution.json") as f:
    data = json.load(f)

result = analyzer.analyze(data["data"])

print(f"Detected modes: {result.mode_count}")
print(f"Is multimodal: {result.is_multimodal}")
for mode in result.modes:
    print(f"  Mode at {mode.center}: weight {mode.weight}")
```

### Outlier Analysis

```python
from Asgard.Verdandi.Analysis.services.outlier_detector import OutlierDetector

detector = OutlierDetector(method="iqr", threshold=1.5)

with open("heavy_tail.json") as f:
    data = json.load(f)

outliers = detector.detect(data["data"])

print(f"Outlier count: {len(outliers)}")
print(f"Outlier percentage: {len(outliers) / len(data['data']) * 100:.1f}%")
print(f"Max outlier: {max(outliers)}")
```

### Normality Testing

```python
from Asgard.Verdandi.Analysis.services.normality_tester import NormalityTester

tester = NormalityTester()

with open("normal_distribution.json") as f:
    normal_data = json.load(f)

with open("bimodal_distribution.json") as f:
    bimodal_data = json.load(f)

# Normal data should pass
result = tester.test(normal_data["data"])
assert result.is_normal

# Bimodal data should fail
result = tester.test(bimodal_data["data"])
assert not result.is_normal
```

## Testing Scenarios

1. **Basic Statistics**
   - Mean, median, mode calculation
   - Standard deviation and variance
   - Range (min/max)

2. **Percentile Accuracy**
   - P50, P75, P90, P95, P99, P99.9
   - Validate against known distributions
   - Edge cases (small samples)

3. **Distribution Shape**
   - Skewness (symmetric vs asymmetric)
   - Kurtosis (tails)
   - Normality testing

4. **Multimodal Detection**
   - Single mode (normal)
   - Two modes (bimodal)
   - Mode location and weight

5. **Outlier Handling**
   - IQR-based detection
   - Z-score detection
   - Heavy tail accommodation

6. **SLA Compliance**
   - Threshold violation counting
   - Percentile-based SLA (e.g., P95 < 200ms)
   - Error rate calculation

## Distribution Characteristics

| Distribution | Mean=Median | Symmetric | Heavy Tail | Modes |
|--------------|-------------|-----------|------------|-------|
| Normal | Yes | Yes | No | 1 |
| Bimodal | No | No | No | 2 |
| Heavy Tail | No | No | Yes | 1 |
| Uniform | Yes | Yes | No | N/A |
