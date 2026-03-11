# Verdandi L1 Integration Tests

This directory contains comprehensive L1 integration tests for the Verdandi performance metrics package. These tests validate complete workflows by testing multiple components together without mocking internal services.

## Test Files

### 1. conftest.py
Provides comprehensive test fixtures including:
- **Web Vitals Data**: Good, poor, mixed, needs-improvement, and partial performance metrics
- **Database Query Metrics**: Fast queries, slow queries, mixed performance, and queries by type
- **Time Series Data**: Improving, degrading, stable, and anomalous performance trends
- **Statistical Distributions**: Bimodal, uniform, and normal-like distributions
- **Configuration Fixtures**: SLA configs (strict/lenient) and Apdex configs (standard/strict)
- **Multi-Window Data**: Multiple time windows for SLA compliance monitoring

### 2. test_web_vitals_integration.py
Tests the complete Web Vitals workflow:
- Loading sample performance timing data
- Calculating all Core Web Vitals (LCP, FID, CLS, INP, TTFB, FCP)
- Validating threshold classifications (good/needs-improvement/poor)
- Generating performance reports and recommendations
- Testing boundary conditions for all metrics
- Validating score calculations and overall ratings

**Test Classes:**
- `TestWebVitalsIntegration`: 25 comprehensive integration tests

**Key Scenarios:**
- All good performance (100/100 score)
- All poor performance with recommendations
- Mixed performance ratings
- Partial metrics (only some vitals available)
- Threshold boundary testing
- Extreme and minimal values

### 3. test_database_metrics_integration.py
Tests the complete Database Metrics workflow:
- Processing sample query timing data
- Calculating comprehensive database metrics (P50, P95, P99, etc.)
- Identifying performance bottlenecks
- Validating recommendations for optimization
- Analyzing queries by type (SELECT, INSERT, UPDATE, DELETE)
- Calculating index usage rates and scan rates

**Test Classes:**
- `TestDatabaseMetricsIntegration`: 22 comprehensive integration tests

**Key Scenarios:**
- Fast queries with optimal performance
- Slow queries with high scan rates
- Mixed fast/slow query patterns
- Query type statistics and breakdowns
- Index usage analysis
- Custom slow query thresholds
- Large dataset analysis (1000+ queries)

### 4. test_analysis_integration.py
Tests the complete Statistical Analysis workflow:
- Loading historical metrics data
- Calculating percentiles over time windows
- Performing trend analysis (improving/degrading/stable)
- Checking SLA compliance
- Validating aggregation results
- Calculating Apdex scores

**Test Classes:**
- `TestPercentileAnalysisIntegration`: 5 tests for percentile calculations
- `TestTrendAnalysisIntegration`: 7 tests for trend detection
- `TestSLAComplianceIntegration`: 8 tests for SLA monitoring
- `TestApdexCalculationIntegration`: 4 tests for Apdex scoring
- `TestAggregationIntegration`: 4 tests for metric aggregation
- `TestEndToEndAnalysisWorkflow`: 3 end-to-end workflow tests

**Key Scenarios:**
- Percentile calculation with various distributions
- Trend detection (improving, degrading, stable)
- Anomaly detection in time series
- SLA compliance checking with violations
- Multi-window SLA monitoring
- Apdex score calculation (excellent to poor)
- Metric aggregation with histograms
- Complete performance analysis workflows

### 5. test_cli_integration.py
Tests the complete CLI command workflow:
- Running Verdandi CLI commands with sample data
- Validating output format (JSON, text)
- Testing all subcommands work correctly
- Verifying exit codes
- Ensuring output consistency

**Test Classes:**
- `TestCLIParserIntegration`: 7 tests for argument parsing
- `TestCLIDataParsingIntegration`: 4 tests for data parsing utilities
- `TestCLIWebVitalsIntegration`: 5 tests for web vitals CLI
- `TestCLIPercentilesIntegration`: 3 tests for percentiles CLI
- `TestCLIApdexIntegration`: 4 tests for Apdex CLI
- `TestCLISLAIntegration`: 4 tests for SLA CLI
- `TestCLICacheMetricsIntegration`: 4 tests for cache metrics CLI
- `TestCLIEndToEndIntegration`: 5 end-to-end CLI workflow tests

**Key Scenarios:**
- CLI argument parsing for all commands
- Text output format validation
- JSON output format validation
- Exit code verification (0 for success, 1 for failures)
- Multiple command consistency
- Error handling with invalid data

## Running the Tests

### Run all L1 integration tests:
```bash
pytest Asgard/Asgard_Test/tests_Verdandi/L1_Integration/ -v
```

### Run specific test file:
```bash
pytest Asgard/Asgard_Test/tests_Verdandi/L1_Integration/test_web_vitals_integration.py -v
```

### Run specific test class:
```bash
pytest Asgard/Asgard_Test/tests_Verdandi/L1_Integration/test_analysis_integration.py::TestTrendAnalysisIntegration -v
```

### Run specific test:
```bash
pytest Asgard/Asgard_Test/tests_Verdandi/L1_Integration/test_database_metrics_integration.py::TestDatabaseMetricsIntegration::test_database_workflow_mixed_queries -v
```

### Run with coverage:
```bash
pytest Asgard/Asgard_Test/tests_Verdandi/L1_Integration/ --cov=Asgard.Verdandi --cov-report=html
```

## Test Coverage

These integration tests provide comprehensive coverage of:

### Web Module
- Core Web Vitals Calculator
- All 6 metrics (LCP, FID, CLS, INP, TTFB, FCP)
- Rating classifications
- Score calculations
- Recommendation generation

### Database Module
- Query Metrics Calculator
- Percentile calculations
- Query type analysis
- Index usage tracking
- Scan rate analysis
- Performance recommendations

### Analysis Module
- Percentile Calculator
- Trend Analyzer
- SLA Checker
- Apdex Calculator
- Aggregation Service

### CLI Module
- All CLI commands
- Argument parsing
- Output formatting (text/JSON)
- Error handling
- Exit codes

## Integration Test Principles

These L1 tests follow integration testing best practices:

1. **No Mocking**: Tests use real Verdandi components without mocking internal services
2. **Realistic Data**: Fixtures use realistic performance data patterns
3. **Complete Workflows**: Tests validate end-to-end workflows, not isolated units
4. **Multiple Scenarios**: Each workflow tests good, poor, and edge case scenarios
5. **Output Validation**: Tests verify both data correctness and output formats
6. **Cross-Component**: Tests validate interactions between multiple components

## Test Data Patterns

### Performance Categories
- **Good**: Metrics within optimal thresholds
- **Needs Improvement**: Metrics in warning range
- **Poor**: Metrics exceeding acceptable thresholds
- **Mixed**: Combination of good and poor metrics

### Time Series Patterns
- **Improving**: Decreasing response times over time
- **Degrading**: Increasing response times over time
- **Stable**: Consistent performance with minor variations
- **Anomalous**: Normal performance with outlier spikes

### Statistical Distributions
- **Bimodal**: Two distinct performance peaks
- **Uniform**: Evenly distributed values
- **Normal-like**: Bell curve approximation

## Expected Results

All tests should pass with:
- ✓ Correct metric calculations
- ✓ Accurate threshold classifications
- ✓ Appropriate recommendations
- ✓ Valid JSON output
- ✓ Formatted text output
- ✓ Correct exit codes
- ✓ Consistent results across multiple runs

## Test Statistics

- **Total Test Files**: 4 (plus conftest.py)
- **Total Test Classes**: 18
- **Total Test Methods**: 80+
- **Total Fixtures**: 30+
- **Lines of Test Code**: ~2,000

## Related Documentation

- [Verdandi Package Documentation](../../Asgard/Verdandi/README.md)
- [L0 Unit Tests](../L0_Mocked/README.md)
- [Test Coverage Matrix](../../../reports/coverage_matrix.md)
