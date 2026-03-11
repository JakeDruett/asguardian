# Statistical Validation Test Suite

## Overview

This test suite (`test_statistical_validation.py`) provides comprehensive validation of Verdandi statistical calculations against industry-standard NumPy/SciPy implementations. It ensures that Verdandi's custom statistical algorithms maintain accuracy and correctness comparable to widely-trusted scientific computing libraries.

## Purpose

Validates the mathematical accuracy of:
- Percentile calculations
- Standard deviation calculations
- Mean calculations
- Apdex score formula
- Linear regression (trend analysis)
- R-squared calculations
- Anomaly detection (z-score method)

## Test Classes

### 1. TestPercentileValidation

Validates percentile calculations against `numpy.percentile`.

**Test Coverage:**
- P50, P75, P90, P95, P99 accuracy with tolerance < 0.001
- Small datasets (5-10 items)
- Large datasets (10,000+ items)
- Uniform distribution
- Normal distribution
- Various dataset sizes (5 to 10,000 items)
- Edge cases (0th, 100th percentiles)
- Duplicate values
- Custom percentiles

**Key Tests:**
- `test_percentile_small_dataset`: 8 random values, parametrized across 5 percentiles
- `test_percentile_large_dataset`: 15,000 random values, relative error < 0.001
- `test_percentile_result_all_percentiles`: Validates all standard percentiles in one test
- `test_percentile_various_sizes`: Tests 6 different dataset sizes

### 2. TestStandardDeviationValidation

Validates standard deviation calculations against `numpy.std`.

**Test Coverage:**
- Population standard deviation (ddof=0)
- Uniform distribution
- Normal distribution with various parameters
- Identical values (std dev = 0)
- Small variance datasets
- Various dataset sizes (10 to 10,000 items)

**Key Tests:**
- `test_std_dev_normal_distribution`: Tests with mean/std pairs (100,15), (500,50), (1000,200)
- `test_std_dev_various_sizes`: Parametrized across 4 dataset sizes
- Relative error < 0.001 for all tests

### 3. TestMeanValidation

Validates mean calculations against `numpy.mean`.

**Test Coverage:**
- Large datasets (5,000+ items)
- Negative values
- Large magnitude values (millions)
- Tolerance < 0.000001

**Key Tests:**
- `test_mean_accuracy`: 5,000 random values with ultra-high precision
- `test_mean_large_values`: Values in millions range with relative error < 1e-10

### 4. TestApdexFormulaValidation

Validates Apdex score formula: `(Satisfied + Tolerating * 0.5) / Total`

**Test Coverage:**
- All satisfied responses (score = 1.0)
- All tolerating responses (score = 0.5)
- All frustrated responses (score = 0.0)
- Mixed response distributions
- Custom thresholds
- Weighted Apdex calculations
- Threshold boundary conditions
- Various threshold values (100, 500, 1000, 2000 ms)

**Key Tests:**
- `test_apdex_formula_various_distributions`: Parametrized across 10 different distributions
- `test_apdex_threshold_boundaries`: Tests exact threshold boundaries (500, 501, 2000, 2001 ms)
- Manual calculation verification for each test

### 5. TestTrendAnalysisValidation

Validates linear regression against `numpy.polyfit`.

**Test Coverage:**
- Slope calculation accuracy
- R-squared (confidence) calculation
- Positive and negative slopes
- Noisy data handling
- Perfect linear fits
- Horizontal lines (slope = 0)
- Intercept calculation
- Various dataset sizes (10 to 1,000 items)
- Trend direction detection
- Anomaly detection using z-score method

**Key Tests:**
- `test_linear_regression_slope`: Perfect linear data, tolerance < 0.000001
- `test_r_squared_perfect_fit`: Validates R² > 0.999 for perfect fit
- `test_linear_regression_noisy_data`: 4 different random seeds with relative error < 0.001
- `test_anomaly_detection_z_score`: Validates z-score anomaly detection matches expected count

### 6. TestEdgeCasesValidation

Tests boundary conditions and edge cases.

**Test Coverage:**
- Single value datasets
- Two value datasets
- Very large numbers (billions)
- Very small numbers (micro-scale)
- Mixed magnitude values (0.001 to 1,000,000)

**Key Tests:**
- `test_large_number_precision`: Values in billions with relative error < 1e-10
- `test_small_number_precision`: Values in microseconds with relative error < 1e-10
- `test_mixed_magnitude_values`: 6 orders of magnitude difference

### 7. TestPerformanceBenchmark

Performance benchmarking tests.

**Test Coverage:**
- Percentile calculation with 100,000 items (< 1.0s)
- Apdex calculation with 100,000 items (< 0.5s)
- Trend analysis with 10,000 items (< 1.0s)

## Test Statistics

### Total Test Count
- **137 individual test cases** (including parametrized variations)

### Parametrized Tests
- `test_percentile_small_dataset`: 5 variations (P50, P75, P90, P95, P99)
- `test_percentile_large_dataset`: 5 variations
- `test_percentile_uniform_distribution`: 7 variations (P25, P50, P75, P90, P95, P99, P99.9)
- `test_percentile_normal_distribution`: 5 variations
- `test_percentile_various_sizes`: 6 variations (sizes: 5, 10, 50, 100, 1000, 10000)
- `test_std_dev_uniform_distribution`: 5 variations (different seeds)
- `test_std_dev_normal_distribution`: 3 variations (different mean/std pairs)
- `test_std_dev_various_sizes`: 4 variations
- `test_mean_accuracy`: 3 variations
- `test_apdex_formula_various_distributions`: 10 variations
- `test_apdex_various_thresholds`: 4 variations
- `test_linear_regression_noisy_data`: 4 variations
- `test_linear_regression_various_sizes`: 5 variations

### Coverage Breakdown by Service

#### PercentileCalculator
- **47 tests** covering:
  - `calculate()` method
  - `calculate_percentile()` method
  - `calculate_custom_percentiles()` method
  - Standard deviation calculation
  - Mean calculation
  - Min/max value calculation

#### ApdexCalculator
- **25 tests** covering:
  - `calculate()` method
  - `calculate_with_weights()` method
  - Formula verification
  - Threshold handling
  - Classification boundaries

#### TrendAnalyzer
- **18 tests** covering:
  - `analyze()` method
  - `_linear_regression()` method
  - `_detect_anomalies()` method
  - Slope calculation
  - R-squared calculation
  - Trend direction detection

## Tolerance Levels

The test suite uses strict tolerance levels to ensure high accuracy:

- **Percentiles**: Absolute tolerance < 0.001 (0.1%)
- **Standard Deviation**: Relative error < 0.001 (0.1%)
- **Mean**: Absolute tolerance < 0.000001 (0.0001%)
- **Linear Regression Slope**: Absolute tolerance < 0.000001
- **R-squared**: Absolute tolerance < 0.001
- **Apdex Score**: Absolute tolerance < 0.0001

## Running the Tests

### Run all validation tests
```bash
cd <project-root>
source .venv/bin/activate
pytest Asgard/Asgard_Test/tests_Verdandi/L0_Mocked/test_statistical_validation.py -v
```

### Run specific test class
```bash
pytest Asgard/Asgard_Test/tests_Verdandi/L0_Mocked/test_statistical_validation.py::TestPercentileValidation -v
pytest Asgard/Asgard_Test/tests_Verdandi/L0_Mocked/test_statistical_validation.py::TestApdexFormulaValidation -v
pytest Asgard/Asgard_Test/tests_Verdandi/L0_Mocked/test_statistical_validation.py::TestTrendAnalysisValidation -v
```

### Run with coverage
```bash
pytest Asgard/Asgard_Test/tests_Verdandi/L0_Mocked/test_statistical_validation.py --cov=Asgard.Verdandi.Analysis.services --cov-report=html
```

### Run performance benchmarks
```bash
pytest Asgard/Asgard_Test/tests_Verdandi/L0_Mocked/test_statistical_validation.py::TestPerformanceBenchmark -v
```

## Dependencies

- `pytest`: Test framework
- `numpy`: Reference implementation for validation
- `random`: Random data generation
- `math`: Mathematical functions

## Test Data Generation

All tests use deterministic random seeds for reproducibility:
- Seeds: 42, 123, 456, 789, 999, 111, 222, 333, 777, 888
- Distribution types: Uniform, Normal (Gaussian)
- Dataset sizes: 5 to 100,000 items

## Expected Results

All tests should pass with:
- 100% pass rate
- No warnings or deprecations
- Execution time < 30 seconds for full suite
- Individual performance benchmarks meeting specified thresholds

## Integration with Hercules Test Suite

This test file is part of the Hercules L0 (unit test) suite for Asgard/Verdandi:

```bash
# Run all Verdandi L0 tests
pytest Asgard/Asgard_Test/tests_Verdandi/L0_Mocked/ -v

# Run Verdandi test coverage analysis
python Hercules/scripts/l0_test_coverage_analyzer.py --service verdandi
```

## Maintenance

### When to Update Tests

1. **Algorithm Changes**: If Verdandi calculation methods change
2. **Tolerance Adjustments**: If precision requirements change
3. **New Features**: When new statistical methods are added
4. **NumPy Updates**: If NumPy behavior changes in new versions

### Adding New Tests

Follow the existing patterns:
1. Use descriptive test names starting with `test_`
2. Include docstrings explaining what is being validated
3. Use `pytest.mark.parametrize` for multiple similar tests
4. Set random seeds for reproducibility
5. Compare against NumPy/SciPy reference implementations
6. Use appropriate tolerance levels based on precision requirements

## Known Limitations

1. **Interpolation Method**: Verdandi uses linear interpolation for percentiles, matching NumPy's default. Other interpolation methods are not tested.
2. **Population vs Sample**: Standard deviation uses population (ddof=0), not sample standard deviation.
3. **Linear Regression Only**: Trend analysis tests only validate linear regression, not polynomial or other curve fitting methods.

## References

- NumPy Percentile Documentation: https://numpy.org/doc/stable/reference/generated/numpy.percentile.html
- NumPy Polyfit Documentation: https://numpy.org/doc/stable/reference/generated/numpy.polyfit.html
- Apdex Specification: https://en.wikipedia.org/wiki/Apdex
- Linear Regression: https://en.wikipedia.org/wiki/Linear_regression
- Z-Score Anomaly Detection: https://en.wikipedia.org/wiki/Standard_score
