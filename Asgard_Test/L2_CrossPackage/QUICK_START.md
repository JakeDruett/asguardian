# Quick Start Guide - L2 Cross-Package Integration Tests

## Run All L2 Tests

```bash
cd <project-root>
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/ -v
```

## Run by Integration Type

```bash
# Code Analysis → Infrastructure (Heimdall → Volundr)
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/ -m heimdall_volundr -v

# API Validation → Performance Monitoring (Forseti → Verdandi)
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/ -m forseti_verdandi -v

# UI Testing → Deployment Config (Freya → Volundr)
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/ -m freya_volundr -v

# Complete Workflows (All Packages)
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/ -m full_pipeline -v
```

## Run Specific Test File

```bash
# Heimdall-Volundr tests
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/test_heimdall_volundr_integration.py -v

# Forseti-Verdandi tests
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/test_forseti_verdandi_integration.py -v

# Freya-Volundr tests
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/test_freya_volundr_integration.py -v

# Full pipeline tests
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/test_full_pipeline_integration.py -v
```

## Run Single Test

```bash
# Quality analysis influences K8s resources
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/test_heimdall_volundr_integration.py::TestQualityReportToDeployment::test_complexity_influences_resource_allocation -v

# API endpoints influence SLA targets
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/test_forseti_verdandi_integration.py::TestAPISpecToSLAChecker::test_endpoint_count_influences_sla_targets -v

# Accessibility violations add CI/CD gates
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/test_freya_volundr_integration.py::TestAccessibilityReportToCICD::test_accessibility_violations_add_quality_gate -v

# End-to-end microservice deployment
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/test_full_pipeline_integration.py::TestCompleteDevWorkflow::test_end_to_end_microservice_deployment -v
```

## Common Options

```bash
# Skip slow tests
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/ -m "cross_package and not slow" -v

# Stop on first failure
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/ -x

# Show local variables on failure
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/ -l

# Verbose output with short traceback
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/ -v --tb=short

# Run with coverage
.venv/bin/pytest Asgard/Asgard_Test/L2_CrossPackage/ --cov=Asgard --cov-report=html
```

## Expected Output

Successful run should show:

```
L2_CrossPackage/test_heimdall_volundr_integration.py::TestQualityReportToDeployment::test_complexity_influences_resource_allocation PASSED
L2_CrossPackage/test_heimdall_volundr_integration.py::TestQualityReportToDeployment::test_file_count_influences_replicas PASSED
L2_CrossPackage/test_heimdall_volundr_integration.py::TestSecurityScanToNetworkPolicy::test_security_scan_to_strict_profile PASSED
...

======================== X passed in Y.YYs ========================
```

## Troubleshooting

### Import Errors

If you see `ModuleNotFoundError: No module named 'Asgard'`:

```bash
# Ensure you're in project root
cd <project-root>

# Ensure virtual environment is activated
source .venv/bin/activate

# Verify Asgard packages are installed
pip list | grep -i asgard
```

### Fixture Not Found

If you see `fixture 'sample_python_project' not found`:

```bash
# Ensure conftest.py exists
ls -la Asgard/Asgard_Test/L2_CrossPackage/conftest.py

# Run from correct directory
cd <project-root>
```

### Tests Fail with Missing Dependencies

```bash
# Install test dependencies
pip install pytest pyyaml

# Install Asgard packages
pip install -e Asgard/Asgard/Heimdall
pip install -e Asgard/Asgard/Forseti
pip install -e Asgard/Asgard/Volundr
pip install -e Asgard/Asgard/Freya
pip install -e Asgard/Asgard/Verdandi
```

## What Gets Tested

### 28 Integration Tests covering:

1. **Heimdall → Volundr** (7 tests)
   - Code complexity affects K8s resources
   - Security score determines pod security
   - Dependencies drive Dockerfile generation

2. **Forseti → Verdandi** (8 tests)
   - API complexity sets SLA thresholds
   - Endpoint types configure Apdex
   - Schema complexity affects monitoring

3. **Freya → Volundr** (9 tests)
   - Accessibility violations create CI/CD gates
   - WCAG levels determine pipeline strictness
   - Visual testing integrates with deployments

4. **Full Pipeline** (4 tests)
   - End-to-end microservice deployment
   - Cross-package consistency validation
   - Complete workflow integration

## Next Steps

After running tests:

1. Review generated artifacts in test output directories
2. Check test reports for detailed results
3. See [README.md](README.md) for detailed documentation
4. See [TEST_SUMMARY.md](TEST_SUMMARY.md) for implementation details
