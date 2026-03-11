# Verdandi L0 Unit Tests

## Overview
This directory contains comprehensive L0 (unit) tests for the Verdandi performance metrics analysis module.

## Test Coverage Summary

### Created Test Files (7 files, 216 tests)

1. **test_analysis_models.py** - 36 tests
   - PercentileResult model
   - ApdexConfig and ApdexResult models
   - SLAConfig and SLAResult models
   - AggregationConfig and AggregationResult models
   - TrendResult model
   - Enum validations

2. **test_percentile_calculator.py** - 40 tests
   - Basic calculator functionality
   - All percentile calculations (P50, P75, P90, P95, P99, P99.9)
   - Statistical measures (mean, std dev, range)
   - Custom percentile calculations
   - Histogram generation
   - Edge cases (large datasets, negative values, etc.)

3. **test_anomaly_models.py** - 22 tests
   - AnomalyDetection model
   - BaselineMetrics model
   - BaselineComparison model
   - RegressionResult model
   - AnomalyReport model
   - Enum validations

4. **test_statistical_detector.py** - 39 tests
   - Z-score anomaly detection
   - IQR anomaly detection
   - Combined detection methods
   - Baseline calculation
   - Detection with baseline
   - Change point detection
   - Edge cases

5. **test_slo_models.py** - 24 tests
   - SLODefinition model
   - SLIMetric model
   - ErrorBudget model
   - BurnRate model
   - SLOReport model
   - Enum validations

6. **test_error_budget_calculator.py** - 30 tests
   - Basic error budget calculations
   - Status determination (COMPLIANT, AT_RISK, BREACHED)
   - Multi-window calculations
   - Daily budget calculations
   - Period-specific calculations
   - Edge cases

7. **test_apdex_calculator.py** - 25 tests
   - Basic Apdex score calculations
   - Classification (Satisfied/Tolerating/Frustrated)
   - Rating classifications (Excellent to Unacceptable)
   - Custom threshold configurations
   - Boundary testing
   - Real-world scenarios

### Supporting Files

- **conftest.py** - Shared pytest fixtures
- **TEST_COVERAGE_SUMMARY.md** - Detailed coverage documentation
- **README.md** - This file

## Running the Tests

### Run All Verdandi Tests
```bash
cd Asgard_Test
pytest L0_unit/verdandi/ -v
```

### Run Specific Test File
```bash
pytest L0_unit/verdandi/test_percentile_calculator.py -v
```

### Run with Coverage Report
```bash
pytest L0_unit/verdandi/ --cov=Asgard.Verdandi --cov-report=html
```

### Run Specific Test Class
```bash
pytest L0_unit/verdandi/test_analysis_models.py::TestPercentileResult -v
```

### Run Specific Test Method
```bash
pytest L0_unit/verdandi/test_percentile_calculator.py::TestPercentileCalculations::test_percentile_calculation_p95 -v
```

### Run with Verbose Output
```bash
pytest L0_unit/verdandi/ -vv
```

### Run in Parallel (Fast)
```bash
pytest L0_unit/verdandi/ -n auto
```

## Test Statistics

- **Total Test Files**: 7
- **Total Test Methods**: 216
- **Total Test Classes**: 62
- **Average Tests per File**: 31
- **Test Execution Time**: ~0.3 seconds (all tests)
- **Pass Rate**: 100%

## Coverage by Module

| Module | Models Tested | Services Tested | Test Count |
|--------|---------------|-----------------|------------|
| Analysis | 7 models | PercentileCalculator, ApdexCalculator | 76 |
| Anomaly | 5 models | StatisticalDetector | 61 |
| SLO | 5 models | ErrorBudgetCalculator | 54 |
| **Total** | **17 models** | **3 services** | **216** |

## Test Quality Characteristics

### Independent Tests
- Each test can run in complete isolation
- No shared state between tests
- No test dependencies

### Fast Execution
- All tests execute in < 100ms per test
- Total suite runs in < 1 second
- Suitable for CI/CD pipelines

### Comprehensive Coverage
- Happy path scenarios
- Edge cases and boundary conditions
- Error handling and validation
- Performance characteristics

### Clear Test Names
- Descriptive test names following pattern: `test_<component>_<scenario>`
- Easy to understand what failed from test name alone

## Not Yet Covered

### Modules Requiring Tests
1. **APM Module** (SpanAnalyzer, TraceAggregator, ServiceMapBuilder)
2. **Cache Module** (CacheMetricsCalculator, EvictionAnalyzer)
3. **Database Module** (ConnectionAnalyzer, QueryMetrics, ThroughputCalculator)
4. **Network Module** (BandwidthCalculator, LatencyCalculator, DNSCalculator)
5. **System Module** (CPUCalculator, MemoryCalculator, IOCalculator)
6. **Tracing Module** (TraceParser, CriticalPathAnalyzer)
7. **Trend Module** (TrendAnalyzer, ForecastCalculator)
8. **Web Module** (VitalsCalculator, NavigationTiming, ResourceTiming)

### Additional Analysis Services
- AggregationService
- SLAChecker
- TrendAnalyzer (in Analysis module)

### Additional Anomaly Services
- BaselineComparator
- RegressionDetector

### Additional SLO Services
- BurnRateAnalyzer
- SLITracker

### CLI Tests
- Command handlers
- Argument parsing
- Output formatting

See `TEST_COVERAGE_SUMMARY.md` for detailed coverage information and recommendations.

## Fixtures Available

The `conftest.py` file provides shared fixtures:

- `sample_response_times` - Sample response times for testing
- `sample_response_times_with_outliers` - Data with outliers
- `current_timestamp` - Current datetime
- `timestamp_range_30_days` - 30 days of timestamps
- `timestamp_range_7_days` - 7 days of timestamps
- `large_dataset` - 10,000 value dataset
- `normal_distribution_data` - Normally distributed data
- `bimodal_distribution_data` - Bimodal distribution (cache hits/misses)
- `uniform_distribution_data` - Uniformly distributed data

## Best Practices Demonstrated

1. **Test Organization**
   - One test file per source file
   - Test classes group related tests
   - Clear test method naming

2. **Assertion Patterns**
   - Specific assertions (not just `assert True`)
   - Appropriate use of pytest.raises for exceptions
   - Validation of multiple aspects per test

3. **Edge Case Testing**
   - Empty datasets
   - Single values
   - Very large datasets
   - Negative values
   - Boundary conditions

4. **Pydantic Model Testing**
   - Field validation
   - Default values
   - Property calculations
   - Constraint validation

5. **Service Testing**
   - Initialization
   - Core functionality
   - Error handling
   - Configuration options

## Contributing New Tests

When adding new tests:

1. Follow existing naming conventions
2. Add to appropriate test file or create new one
3. Include docstrings explaining what is tested
4. Test both success and failure cases
5. Include edge cases
6. Update this README and TEST_COVERAGE_SUMMARY.md

## Continuous Integration

These tests are designed for CI/CD:
- Fast execution (< 1 second total)
- No external dependencies
- Deterministic results
- Clear failure messages
- Suitable for pre-commit hooks

## License

Part of the Asgard project.
